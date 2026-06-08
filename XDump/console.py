"""Copy pasted from another project"""
import queue
import threading
import subprocess

class Styles:
    NORMAL = 0
    ERROR = 1
    SUCCESS = 2
    DEEP = 3


class ConsoleWindow:
    # Mapping von Namen zu cmd-Farbcodes
    COLOR_MAP = {
        "black": "0", "blue": "1", "green": "2", "cyan": "3",
        "red": "4", "magenta": "5", "yellow": "6", "white": "7",
        "gray": "8", "bright_blue": "9", "bright_green": "A",
        "bright_cyan": "B", "bright_red": "C", "bright_magenta": "D",
        "bright_yellow": "E", "bright_white": "F"
    }

    def __init__(self, title: str, *, streaming = False, style: tuple[str, str] = None):
        self.title = title
        self._queue = queue.Queue()

        color_cmd = ""
        if style is not None:
            fg, bg = style
            fg_code = self.COLOR_MAP.get((fg or "white").lower(),  "F")
            bg_code = self.COLOR_MAP.get((bg or "black").lower(), "0")
            color_cmd = f"os.system('color {bg_code}{fg_code}')"

        self._streaming = streaming
        
        reader = """
while True:
    ch = sys.stdin.read(1)
    if not ch:
        break
    sys.stdout.write(ch)
    sys.stdout.flush()
""" if streaming else """
for line in sys.stdin:
    sys.stdout.write(line)
    sys.stdout.flush()
"""
        
        self._proc = subprocess.Popen(
            ["python", "-u", "-c", f"""
import sys, os, ctypes
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
ctypes.windll.kernel32.SetConsoleMode(
    ctypes.windll.kernel32.GetStdHandle(-11), 7
)
os.system('title {title}')
{color_cmd}
{reader}
"""],
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            text=True,
            encoding="utf-8"
        )
        self._thread = threading.Thread(target=self._writer, daemon=True)
        self._thread.start()
    
    def _writer(self):
        while True:
            line = self._queue.get()
            if line is None:
                break
            try:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
            except Exception:
                break
    
    def print(self, *args, sep=" ", end="\n"):
        self._queue.put(sep.join(str(a) for a in args) + end)
        
    def close(self):
        self._queue.put(None)
        self._proc.terminate()


class ConsoleManger:
    """Verwaltet mehrere Konsolen und schließt sie automatisch."""
    
    def __init__(self):
        self._consoles: dict[str, ConsoleWindow] = {}
        # Beim Beenden alle schließen
        import atexit
        atexit.register(self.close_all)
    
    def open(self, name: str, title: str = None, *, streaming: bool = False, foreground: str = None, background: str = None) -> ConsoleWindow:
        c = ConsoleWindow(title or name, streaming=streaming, style=(foreground, background))
        self._consoles[name] = c
        return c
    
    def __getitem__(self, name: str) -> ConsoleWindow:
        return self._consoles[name]
    
    def close_all(self):
        for c in self._consoles.values():
            c.close()