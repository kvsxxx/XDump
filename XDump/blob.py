from __future__ import annotations

import os
import struct
import asyncio
from io import BytesIO
from hashlib import sha256
from base64 import b64decode
from typing import TYPE_CHECKING, TypedDict, NotRequired
from concurrent.futures import ThreadPoolExecutor

if TYPE_CHECKING:
    from DrissionPage.items import ChromiumElement
    from DrissionPage import ChromiumPage
    from DrissionPage._units.listener import DataPacket

class FileMatch(TypedDict):
    elem: ChromiumElement
    """The corresponding element"""
    confidence: float
    """How confident we are, that this is the correct element. Percantage between `0` and `1`"""
    type: str
    """Mostly `voicemessage` or `audio_file`"""
    filename: NotRequired[str]
    """The filename of the audio file. Not present when `type='audio_file'`"""

def get_m4a_duration(data: bytearray):
    """Returns the m4a duration (for twitter voicemessages).
    
    Ima be honest I made claudeai do this bruh im too lazy for ts
    """
    with BytesIO(data) as f:
        # Wir bestimmen die Dateigröße, um die Grenze der Suche zu kennen
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)

        def find_mdhd_recursive(limit):
            """Durchsucht den Baum bis zu einer bestimmten Grenze."""
            while f.tell() < limit:
                # Atom-Header lesen (Größe 4 Byte, Typ 4 Byte)
                header = f.read(8)
                if len(header) < 8: break
                size, atom_type = struct.unpack(">I4s", header)
                
                # Größe 1 bedeutet: Extended Size (selten bei M4A, aber sicherheitshalber)
                if size == 1:
                    size = struct.unpack(">Q", f.read(8))[0] - 16
                
                # --- WENN WIR DEN TREFFER HABEN ---
                if atom_type == b'mdhd':
                    version = struct.unpack("B", f.read(1))[0]
                    f.seek(3, 1) # Flags überspringen
                    
                    if version == 1: # 64-bit Modus
                        f.seek(16, 1) # Creation/Modification time überspringen
                        timescale = struct.unpack(">I", f.read(4))[0]
                        duration = struct.unpack(">Q", f.read(8))[0]
                    else: # 32-bit Modus
                        f.seek(8, 1) # Creation/Modification time überspringen
                        timescale = struct.unpack(">I", f.read(4))[0]
                        duration = struct.unpack(">I", f.read(4))[0]
                    return duration / timescale
                
                # --- WENN ES EIN CONTAINER IST, TAUCHEN WIR AB ---
                container_atoms = [b'moov', b'trak', b'mdia', b'minf', b'stbl']
                if atom_type in container_atoms:
                    # Tauche tiefer (limit ist aktuelle position + atomgröße)
                    result = find_mdhd_recursive(f.tell() + size - 8)
                    if result is not None:
                        return result
                else:
                    # Normaler Block: Einfach überspringen
                    if size > 8:
                        f.seek(size - 8, 1)
            return None

        return find_mdhd_recursive(file_size)


def blob_to_file_direct(chrome, file: BlobFile):
    """Used on the page while dumping.
    
    Fetches `file` on the webpage and writes it with `file.save()`
    """
    uid = file._blobname.replace('-', '')  # eindeutige ID
    
    chrome.run_js(f"""
        window._blob_{uid}_ready = false;
        window._blob_{uid}_error = null;
        window._blob_{uid}_b64 = null;
        fetch(arguments[0])
            .then(r => {{
                window._blob_{uid}_ct = r.headers.get('content-type') || '';
                return r.arrayBuffer()
            }})
            .then(buf => {{
                const bytes = new Uint8Array(buf);
                let binary = '';
                const chunkSize = 8192;
                for (let i = 0; i < bytes.length; i += chunkSize) {{
                    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
                }}
                window._blob_{uid}_b64 = btoa(binary);
                window._blob_{uid}_ready = true;
            }})
            .catch(e => {{ window._blob_{uid}_error = e.toString(); window._blob_{uid}_ready = true; }})
    """, file.url)
    
    for _ in range(600):
        if chrome.run_js(f"return window._blob_{uid}_ready === true"):
            break
        chrome.wait(0.05)
    
    error = chrome.run_js(f"return window._blob_{uid}_error")
    if error:
        print(f"Blob error: {error}")
        chrome.run_js(f"delete window._blob_{uid}_ready; delete window._blob_{uid}_b64; delete window._blob_{uid}_error;")
        return None
    
    chunks = []
    offset = 0
    chunk_size = 500_000
    while True:
        chunk = chrome.run_js(f"return window._blob_{uid}_b64?.substring({offset}, {offset + chunk_size})")
        if not chunk:
            break
        chunks.append(chunk)
        offset += chunk_size
        if len(chunk) < chunk_size:
            break
    
    
    ct = chrome.run_js(f"return window._blob_{uid}_ct") or ''
    file._ext_from_headers({'content-type': ct})
    chrome.run_js(f"delete window._blob_{uid}_ready; delete window._blob_{uid}_b64; delete window._blob_{uid}_error;")
    
    if not chunks:
        # print("chunks are empty")
        return None
    
    b64 = ''.join(chunks)
    file.save(b64)
    
    return True


class BlobFile:
    """Object representing a Blob Object that is processed"""
    def __init__(self, url: str, path: str = None):
        self.url: str | None = url
        """Die Url des Blobs"""
        self.finalname: str = None
        """Der finale Dateiname des Blobs"""
        self.elem: ChromiumElement = None
        """Das Webelement der Message, auf das dieses Blob korrespondiert"""
        self.type: str = None
        """Der Typ des Blobs. Meistens `audio`"""
        self.specific_type: str = None
        """Spezieller Typ, z.b. `voicemessage` in `type=audio`"""
        self.hash: bytes = None
        """Hash vom Inhalt"""
        self.body: bytearray = None
        """Body"""
        self.ext: str = None
        """Die Dateiextension"""
        self.length: int = None
        """Größe von self.body"""

        
        self._blobname = self.url.split('/')[-1]
        """Raw Blobname ohne Extension"""
        
        self.directory = path + ("/" if not path.endswith('/') else "")
        """Directory, in welchem Ordner die Datei liegt"""

    @property
    def blobname(self):
        """Der 'rohe' Filename vom Blob (blob:https://x.com/{blobname})"""
        return self._blobname + (f".{self.ext}" if self.ext else "")

    @property
    def filepath(self):
        """Filepath (`self.directory` + `self.filename` or `self.blobname`)"""
        return self.directory + (
            self.finalname if self.finalname else self.blobname
        )

    def _ext_from_headers(self, headers):
        """Sets file-extension from HTTP headers"""
        content_type = headers.get('content-type', '')
        # z.b. "audio/x-m4a" → "x-m4a"
        #      "video/mp4"    → "mp4"
        #      "image/jpeg"   → "jpeg"
        if '/' in content_type:
            ext = content_type.split('/')[1].split(';')[0].strip()
            self.ext = ext
        else:
            self.ext = 'bin'
        
    @classmethod
    def from_packet(cls, packet: DataPacket, location: str = None):
        """Ceates Object with `DrissionPage.DataPacket`"""
        self = cls(packet.url, location)
        self._ext_from_headers(packet.response.headers)
        self.save(packet.response.raw_body)
        
        return self
        
    def save(self, b64: str = None):
        """Writes this file into `self.filepath`. If b64 is provided, then this will be used"""
        if b64 is not None:
            self.body = b64decode(b64)
        
        with open(self.filepath, 'wb') as f:
            f.write(self.body)
        
        self.length = len(self.body)
        self.hash = sha256(self.body).hexdigest()
        
    def rename(self, newname):
        """Renames this file and sets `self.finalname` to `newname`"""
        os.rename(self.filepath, self.directory + newname)
        self.finalname = newname
                

class BlobWorker:
    """A worker for downloading a blob."""
    
    file: BlobFile
    """Currently processing file."""
    def __init__(self, parent, worker_id=0):
        self.parent: BlobDownloader = parent
        """The downloader that initiated us."""
        self.worker_id = worker_id
        """Our ID, just for print purposes."""
        
    def clear(self):
        """Säubert alle Attribute von diesem Worker"""
        self.file = None
        
    async def work(self):
        """Das wirkliche 'Arbeiten'. Läuft solange im Loop bis Worker getötet wird."""
        loop = asyncio.get_running_loop()
        
        while True:
            self.clear()
            
            data = await self.parent.blob_queue.get()
            # Instructed kill through poison
            if data is None:
                break
            
            location = f'{self.parent.ddir}/assets/'
            
            # Falls wir aus packet bauen konnten
            if (packet := data.get('packet')):
                print("we can use the data packet", data)
                self.file = BlobFile.from_packet(packet, location)
            # Ansonsten download
            else:
                print("new download blob", data['url'])
                self.file = BlobFile(data['url'], location)
                
                result = await loop.run_in_executor(
                    self.parent._executor,
                    lambda: blob_to_file_direct(self.parent.chrome, self.file)
                )
                if result is None:
                    async with self.parent.lock:
                        self.parent.processed.add(self.file.url)
                    continue
            
            if await self.is_submitted():
                continue
            
            await self._process_saved_blob()
            print(f"[Worker {self.worker_id}] Processed {self.file.url}")



    async def is_submitted(self):
        """Guckt nach ob die Datei schon in `submitted` existiert per Hash"""
        async with self.parent.lock:
            if self.file.hash in self.parent.submitted:
                os.remove(self.file.filepath)
                # self.parent.processed.add(self.file.url)
                return True
            
            self.parent.submitted.add(self.file.hash)
        return False
    
    async def _process_saved_blob(self):
        """Sobald Blob runtergeladen wurde verarbeiten wir weiter.
        
        We search for the webelement that corresponds to the current blob file.
        For example if we have a x-m4a file, we can guess that it's probably a voicemessage.
        Then we will check for a voicemessage with an approx length in the current panel 
        dump that fits the best. Ima be honest, we're basically "guessing" which element fits,
        it's a matter of "what fits best for x".
        """
        loop = asyncio.get_running_loop()

        # Wir schauen welches Webelement dazu passt
        found: ChromiumElement | None = await loop.run_in_executor(
            self.parent._executor,
            lambda u=self.file.url: self.parent.chrome.run_js(f"""
                const file = document.querySelector('[src="{u}"]')
                file?.setAttribute("grabbed", "grabbed")
                return file;
            """)
        )
        """The message webelement that DEFINETLY corresponds to the current Blobfile."""

        if found is not None:
            self.file.elem = found
        else:
            self.file_matches = []
            """An array that holds """
            
            file_duration = get_m4a_duration(self.file.body) if self.file.ext == "x-m4a" else None
            audio_elements = await loop.run_in_executor(
                self.parent._executor,
                lambda: self.parent.chrome.run_js(
                    """return [...document.querySelectorAll('[data-icon="icon-play"]')].map(c => c.parentElement.parentElement)"""
                )
            )

            for audio_element in audio_elements:
                if audio_element.child_count == 3:
                    if self.file.ext == "x-m4a" and file_duration is not None:
                        length = audio_element.children()[2].text
                        twitter__total_seconds = sum([float(a) * 60 ** n for n, a in enumerate(reversed(length.split(":")))])
                        self.file_matches.append({
                            "elem": audio_element,
                            "confidence": 1 - abs(1 - file_duration / twitter__total_seconds),
                            "type": "voice_message",
                        })
                elif audio_element.child_count == 2:
                    name, size = self.parent.chrome._run_js(
                        "const data = arguments[0].children[1]; return [data.children[0].textContent, data.children[1].textContent]",
                        audio_element
                    )
                    _size = size.strip().upper().split()
                    size_num, size_unit = float(_size[0]), _size[1]
                    if size_unit == "GB":   size_num *= 1000**3
                    elif size_unit == "MB": size_num *= 1000**2
                    elif size_unit == "KB": size_num *= 1000
                    if name.endswith(self.file.ext):
                        async with self.parent.lock:
                            self.file_matches.append({
                                "elem": audio_element,
                                "confidence": 1 - abs(1 - size_num / self.file.length),
                                "filename": name,
                                "type": "audio_file"
                            })
                else:
                    print("Bruh idk", audio_element)

                await loop.run_in_executor(
                    self.parent._executor,
                    lambda ae=audio_element: self.parent.chrome.run_js("arguments[0].setAttribute('type', 'audio')", ae)
                )
        
        self.finish()

        async with self.parent.lock:
            self.parent.downloaded += 1
            self.parent.processed.add(self.file.url)

        print(f"Downloaded {self.parent.downloaded}/{len(self.parent.submitted)}")
    
    def finish(self):
        """This gets called to clean up basically. Renames the file to the filename present in the best match of self.file_matches."""
        # Wenn wir sicher sind welches Element
        if self.file.elem:
            self.file.finalname = self.file.blobname
            self.parent.chrome.run_js(
                f"arguments[0].outerHTML = arguments[0].outerHTML.replace('{self.file.url}', '{f'./dump/___/assets/{self.file.blobname}'}')",
                self.file.elem
            )
        # File confidentialities ausrechnen
        else:
            if not self.file_matches:
                return print("Keine filematches!")
            
            best_matching = max(self.file_matches, key=lambda data: data['confidence'])
            
            self.file.rename(best_matching.get("filename", "voicemessage_" + self.file.blobname))
            self.file.specific_type = best_matching.get("type", "unknown")
            self.file.elem = best_matching['elem']
            
            self.parent.chrome.run_js(f"""
                arguments[0].setAttribute("filename", "{self.file.finalname}");
                arguments[0].setAttribute('grabbed', 'grabbed');
                arguments[0].setAttribute('stype', '{self.file.specific_type}');
            """, self.file.elem)
            
        
class BlobDownloader:
    """An object to handle blob downloads"""
    def __init__(self, chrome, ddir):
        self.ddir = ddir
        """The base dump directory"""
        self.chrome: ChromiumPage = chrome
        
        os.makedirs(f'{ddir}/assets', exist_ok=True)
        self.processed = set()
        """Alle URLs die wir schon durchhaben"""
        self.seen = set()
        """Alle blob URLs die wir je gesehen haben"""
        self.submitted = set()
        """Alle Hashes von Dateien die wir mal in die Queue gepackt haben"""
        self.downloaded = 0
        self.lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=8)

    def __call__(self, *args, **kwargs):
        """Does the work."""
        return self.process_packets(*args, **kwargs)
    
    def process_packets(self):
        """Main function that handles everything"""
        asyncio.run(self._run())

    async def _run(self):
        """Underlying async "main" function."""
        self.blob_queue: asyncio.Queue = asyncio.Queue()
        
        await asyncio.gather(
            self._blob_producer(),
            *[BlobWorker(self, i).work() for i in range(6)],
        )
        self._executor.shutdown(wait=False)
        self._executor = ThreadPoolExecutor(max_workers=8)

    async def _blob_producer(self):
        """The handler that produces the queue with blobs and fills accordingly."""
        loop = asyncio.get_running_loop()
        queue = self.blob_queue

        def generator_thread():
            """The actual queue packet generator"""
            # We step through each network request
            for packet in self.chrome.listen.steps(timeout=3):
                # We filter out anything that's not a blob
                if not packet.url.startswith('blob:'):
                    continue
                # We filter out anything that we've already seen somewhere
                if packet.url in self.seen:
                    continue
                
                self.seen.add(packet.url)
                # We can reuse the request to skip a repetetive full blob download
                if packet.response._is_base64_body and packet.response._raw_body:
                    asyncio.run_coroutine_threadsafe(queue.put({'packet': packet}), loop).result()
                # We just add the url and redownload
                else:
                    asyncio.run_coroutine_threadsafe(queue.put({'url': packet.url}), loop).result()
            
            # Poison pills, lässt die Arbeiter wissen, dass keine neuen Blobs mehr kommen
            for _ in range(6):
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        await loop.run_in_executor(self._executor, generator_thread)

    def __del__(self):
        self._executor.shutdown(wait=False)
        
        
        
class FileDownloader:
    def __init__(self, chrome, ddir):
        self.chrome = chrome
        self.ddir = ddir
        os.makedirs(f'{ddir}/assets', exist_ok=True)
        self.seen_files = set()

    def __call__(self, *args, **kwargs):
        self.handle_files(*args, **kwargs)    

    def handle_files(self):
        """Basically the `main` function."""
        files: list[ChromiumElement] = self.chrome.run_js(
            """return document.querySelectorAll(`[data-icon="icon-document"]`)"""
        )
        download_dir = os.path.abspath(self.ddir + "\\assets") + "\\"
        self.chrome.set.download_path(download_dir)

        for file in files:
            message_id = self.chrome.run_js("""
                let elem = arguments[0];
                let target = undefined;
                let maxRuns = 10;
                while (target == undefined && (maxRuns--) > 0) {
                    target = elem.querySelector("[data-testid^='message-']");
                    elem = elem.parentNode;
                }
                return target?.getAttribute("data-testid");
            """, file)

            if message_id is None:
                continue
            if message_id in self.seen_files:
                continue
            
            file.click()
            self.seen_files.add(message_id)

            self.chrome.run_js(f"""
                const a = document.querySelector("[data-testid='{message_id}']");
                a?.setAttribute('type', 'file');
                a?.setAttribute('grabbed', 'grabbed');
            """, file)

            # Doesnt work lol
            # timeout = 0
            # while len(os.listdir(download_dir)) == files_before and timeout < 100:
            #     sleep(0.05)
            #     timeout += 1

            # if timeout >= 100:
            #     print(f"Timeout bei {message_id}")
            #     continue

            # all_files = os.listdir(download_dir)
            # filename = max(
            #     all_files,
            #     key=lambda f: os.path.getctime(os.path.join(download_dir, f))
            # )

            # file.set.attr("filename", filename)
            # print(f"+ {filename}")
            
            
class Downloader:
    def __init__(self, chrome, ddir):
        self.blobs = BlobDownloader(chrome, ddir)
        """The Blob handler that, when called, downloads all currently present blobs."""
        self.files = FileDownloader(chrome, ddir)
        """File handler, same thing as blob handler basically."""