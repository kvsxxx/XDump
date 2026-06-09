"""
Twitter DM Scraper:

DMs müssen vorher entsperrt werden.
"""
from __future__ import annotations


from XDump.utils import *
from XDump.blob import Downloader
from XDump.console import Styles
from XDump.checkpoint import checkpoint_set, checkpoint_get, append, add

import os
import re
import json
import shutil
from datetime import datetime
from inspect import signature
from DrissionPage import ChromiumPage
from zlib import compress as zcompress
from sys import _getframe as sys__getframe
from typing import TypedDict, TYPE_CHECKING, get_type_hints
from DrissionPage.errors import PageDisconnectedError, JavaScriptError

if TYPE_CHECKING:
    from inspect import Parameter
    from collections.abc import Callable
    from DrissionPage.items import ChromiumElement

chrome: ChromiumPage = None
"""Globales Chrome Element"""
TWITTER_USERNAME = None
"""Username der bei `whoami` ausgeführt wird"""
CACHING = True
"""Ob wir userlist cachen oder nicht"""
DEBUG_CONSOLE = None
"""Global für Debug Console"""

def debug(*args, style=Styles.NORMAL, **kwargs):
    """Funktion für debug print"""
    if not DEBUG_CONSOLE:
        return
    
    if style is not None:
        args = list(args)
        if style == Styles.NORMAL:
            args[0] = f"[\033[34m.\033[0m] {args[0]}"
        elif style == Styles.SUCCESS:
            args[0] = f"[\033[32m+\033[0m] {args[0]}"
        elif style == Styles.ERROR:
            args[0] = f"[\033[31m!\033[0m] {args[0]}"
        elif style == Styles.DEEP:
            args[0] = f"\033[2m{args[0]}"
            args[-1] = args[-1] + "\033[0m"

    frame = sys__getframe(1)
    trace = []
    while frame:
        name = frame.f_code.co_name
        if name == "<module>":
            name = "main"
        trace.append(name)
        frame = frame.f_back
    trace.reverse()
    trace = ' -> '.join(trace)

    DEBUG_CONSOLE.print(f"\033[2;1m[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]\033[22m", trace, "\033[22m")
    DEBUG_CONSOLE.print(*args, **kwargs)
    DEBUG_CONSOLE.print()

class ChatCache:
    """Object für Chatcache"""
    _chats: dict[str, TwitterDM] = {}
    def add(self, chat: TwitterDM):
        """Fügt ein Chat der Liste hinzu"""
        if not CACHING:
            return chat
        
        if not chat['isGroupchat']:
            self._chats[chat['id'].split(':')[1]] = chat
            self._chats[chat["username"].removeprefix("@").lower()] = chat
            
        self._chats[chat['id']] = chat
        
        return chat
    def concat(self, chats: list[TwitterDM]):
        """Fügt eine Liste von Chats hinzu"""
        for c in chats:
            self.add(c)
        return chats
    def unique(self):
        """Eine Liste von allen Chat ohne Dopplung durch key-injection"""
        return list({id(v): v for v in self._chats.values()}.values())
    def __getitem__(self, key):
        if key.startswith("@"):
            key = key.removeprefix("@")
        return self._chats.get(key.lower())

chat_cache = ChatCache()
"""Der Chatcache von allen Chats, die einmal gefetcht wurden"""
    
# =================================== Für Chat ====================================
get_username = lambda: chrome.run_js("return document.querySelector('*[data-testid=\"dm-conversation-panel\"]').querySelector('li:has(img[alt=\"user avatar\"])').querySelector('div > div > div').children[2].innerText").strip()
"""Gibt den Username vom Twitteruser zurück"""
get_panel: ChromiumElement = lambda: chrome.run_js("return document.querySelector('*[data-testid=\"dm-conversation-panel\"]')")
"""Fetcht DM-Conversation-Panel für DM Dup"""
get_scrollbar: ChromiumElement = lambda: chrome.run_js("return document.querySelector('[data-testid=\"dm-message-list\"] > .scrollbar-thin-custom')")
"""Fetcht die Scrollbar vom DM Ding"""
# =================================================================================

# ================================== Für Users =====================================
class TwitterDM(TypedDict):
    """Objekt die ein Twitter DM + User repräsemntiert"""
    id: str
    href: str
    avatar: str
    avatars: list[str]
    name: str
    username: str
    lastMessage: str
    lastMessageTime: str
    isGroupchat: bool
class GroupchatMember(TypedDict):
    """Objekt das einen Twitteruser repräsentiert"""
    avatar: str
    name: str
    status: str | None
    url: str


js__getChatScrollInfo = """
    const container = document.querySelector('[data-testid="dm-message-list"] > .scrollbar-thin-custom');
    const scrollTop = container.scrollTop;
    const containerHeight = container.clientHeight;
    const lis = [...document.querySelectorAll('ul > li')];
    const visible = lis.filter(li => {
        const rect = li.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        return rect.top >= containerRect.top && rect.bottom <= containerRect.bottom;
    });
    const firstTop = visible.length ? visible[0].getBoundingClientRect().top - container.getBoundingClientRect().top + scrollTop : null;
    console.log(visible);
    return {
        anchorTop: firstTop,
        visibleCount: visible.length,
        containerHeight: containerHeight,
        scrollTop: scrollTop,
        messageID: visible.length ? visible.find(li => li.querySelector('[data-testid^="message-"]'))
            ?.querySelector('[data-testid^="message-"]')
            ?.getAttribute("data-testid") 
        : null
    };
"""
"""JS Code um zu die oberste Message des aktuellen dump part zu fetchen."""

js__getMyUsername = '(document.querySelector(\'[data-testid^="UserAvatar-Container-"]\')?.getAttribute("data-testid")?.slice(21))'
"""JS Code, der den aktuellen Benutzernamen fetcht.
!!KEIN RETURN!!

```
chrome.run_js(f"const username = {js_getMyUsername};")
```
"""

js__parse_chat_data = """
    const avatars = [...el.querySelectorAll('[alt="user avatar"]')].map(c => c.src);
    const id = el.dataset.testid.replace('dm-conversation-item-', '');
    const isGroupchat = id.startsWith("g");
    
    const ariaData = el.getAttribute("aria-description")?.split(", ")
    let chatName, username, lastMessage, lastMessageTime
    // Default Case, [chatName], [username], [lastMessage], [lastMessageTime]
    if (ariaData.length >= 4) {
        chatName = ariaData[0];
        username = ariaData[1];
        lastMessage = ariaData[2];
        lastMessageTime = ariaData[3];
    } 
    // Chat with oneself, username is excluded so indicies are shifted
    else if (ariaData.length >= 3) {
        chatName = ariaData[0];
        const myusername = """+js__getMyUsername+""";
        
        // Chat with oneself
        if (!ariaData.join(' ').includes("@")) {
            username = myusername;
            lastMessage = ariaData[1];
            lastMessageTime = ariaData[2];
        // Wahrscheinlich Chat mit 'You sent a file'
        } else {
            chatName = ariaData[0];
            username = ariaData[1];
            lastMessageTime = ariaData[2];
            lastMessage = el.querySelector('div').children[1].children[1].children[0].innerText;
        }
    }
    // Safety-fallback, in case ariaData is not provided?
    else {
        username = undefined;
        chatName = el.querySelector('div').children[1].children[0].children[0].innerText;
        lastMessage = el.querySelector('div').children[1].children[1].children[0].innerText;
        lastMessageTime = el.querySelector('div').children[1].children[0].children[1].innerText;
    }
    
    
    return ({
        id: id,
        href: el.querySelector('a')?.href,
        avatar: avatars[0],
        avatars: avatars,
        name: chatName,
        username: username.replace("@", "").trim(),
        lastMessage: lastMessage,
        lastMessageTime: lastMessageTime,
        isGroupchat: isGroupchat
    })
"""
"""Javascript Code für das parsen von einer Variable `el`

Gibt am Ende `return ({...})` zurück

```
x = chrome.run_js(f\"\"\"
    const el = document.querySelector('x');
    {js__parse_chat_data}
\"\"\")

>>> x
{"id": ..., "href": ..., ...}
```
"""

get_visible_conversation_items: Callable[[], list[TwitterDM]] = lambda: chat_cache.concat(chrome.run_js("""
        return [...document.querySelectorAll('[data-testid^="dm-conversation-item-"]')]
            .map(el => {
                """+js__parse_chat_data+"""
            });
    """))
"""Fetcht alle DM Chats"""
get_chat_data: Callable[[ChromiumElement], TwitterDM | None] = lambda elem: chat_cache.add(chrome.run_js(f"const el = arguments[0]; {js__parse_chat_data}", elem)) if elem else None
"""Nimmt Chatdaten. Falls der passed Chat None ist, wird None zurückgegeben"""

def get_current_chat_data() -> TwitterDM | None:
    """Liest Chat-Daten für den aktuellen ausgewählten Chat aus"""
    return get_chat_data(chrome.run_js('return document.querySelector(\'[data-selected="true"]\')'))

def get_my_username() -> str:
    """Funktion um den aktuellen Username zu fetchen und als `@username` zurückzugeben (oder None)."""
    try:
        name = chrome.run_js(f"return {js__getMyUsername}")
        if name is not None:
            return "@" + name
    except JavaScriptError as exc:
        error_print(exc)
    return None

def get_groupchat_members() -> list[GroupchatMember]:
    """Gets groupchat members of currently selected groupchat"""
    
    chrome.run_js("document.querySelector('[data-testid=\"dm-conversation-header\"] .cursor-pointer').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));")
    close_button = wait_for(lambda: chrome.run_js('return document.querySelector(\'[role="dialog"]\')?.querySelector(".scrollbar-thin-custom button")'))
    
    # chrome.run_js("document.getElementById(\"radix-:rg:\").querySelector('.scrollbar-thin-custom')")
    
    # members[0] ist `null` falls es der "Mitglied hinzufügen" Button ist. Rausfiltern?
    members = chrome.run_js("""
        const container = arguments[0];
        container.scrollIntoView();
        // TODO: Durchscrollen bis unten für die Member
        
        let nullMembers = 0;
        const memberCount = container.children[0].children[0].innerText;
        return [...container.children[0].children[1].children].map(member => {
            const url = member.children[0].href;
            if (!url) {
                nullMembers++;
                return null;
            }
            
            return {
                avatar: member.querySelector('[alt=\"user avatar\"]').src,
                name: member.children[0].children[1].innerText,
                status: member.children[0].children[2]?.innerText,
                url: url,
            };
        // Nullmembers rausholen
        }).slice(nullMembers);
    """, wait_for(lambda: chrome.run_js("""return document.querySelector(\'[role="dialog"][data-state="open"]\').querySelector("div > div > div.relative.flex.w-full.flex-col.gap-6.p-4 > div > div.flex.w-full.flex-col.gap-6 > div.mt-4.w-full")""")))
    
    # Dialog schließen
    chrome.run_js("arguments[0].click()", close_button)
    wait_for(lambda: chrome.run_js("""return document.querySelectorAll('[role="dialog"][data-state="open"]').length == 0 ? true : null"""))
    return members

def _scroll_to_message(scrollbar, target_id):
    """Scrollt nach oben bis die Ziel-Message im DOM sichtbar ist."""
    clean_id = target_id.replace('message-', '')
    for _ in range(500):
        found = chrome.run_js(f"""
            return !!document.querySelector('[data-testid="message-{clean_id}"]')
        """)
        if found:
            return True
        chrome.run_js("arguments[0].scrollTop -= 200", scrollbar)
        chrome.wait(0.1)
    return False

# ======================================================================================================================

def dump_current_chat(convo: TwitterDM, include_messages: bool = True, include_blobs: bool = True, include_files: bool = True):
    """Dumps the currently selected chat."""
    checkpoint_set(current_chat_started_at=time())
    
    if convo['username'] == None:
        convo['username'] = convo['id']
        clean_username = convo['id'].replace(":", "_")
    else:
        # Wir entfernen "@" von username
        clean_username = convo['username'] if not convo['isGroupchat'] else convo['name']
   
    dump_path = "./dump/" + (inside_dump_dir := clean_username + "_" + convo['id'].replace(":", "_"))
    """Wo der dump gespeichert wird."""
    dump_start = 0
    """Mit welchem Dump wir starten"""
    last_message_id = None
    """Die MessageID von der letzten gedumpten Message, brauchen wir für resuming"""
    current_chat_id = None
    """Chat ID die zuletzt gedumpt wurde."""

    # Wir testen dump path ob schon ein dump existiert, und ob da etwas drinnen ist
    if (dump_path_exists := os.path.exists(dump_path)) and len(files := os.listdir(dump_path)) != 0:
        if (current_chat_id := checkpoint_get('current_chat_id') is not None):
            prompt_text = "[D]elete current data, [c]ontinue or [a]bort? [D/c/a] "
            prompt_options = {"D", "c", "a"}
        else:
            prompt_text = "Delete current data? [Y/n] "
            prompt_options = {"Y", "n"}
            
        while (n := input(prompt_text)) not in prompt_options:
            pass
        
        # Löschen und von neu anfangen
        if n in {"D", "Y"}:
            shutil.rmtree(dump_path + "/", ignore_errors=True)
        # Resume from checkpoint
        elif "c" in prompt_options:
            last_message_id = checkpoint_get('last_message_id')
            current_chat_id = checkpoint_get('current_chat_id')
            dump_start = checkpoint_get('last_dump_index')
            checkpoint_set(current_chat_messages=0)
        # Abort
        else:
            return print("Aborted.")
    
    os.makedirs(dump_path, exist_ok=True)

    panel = get_panel()
    scrollbar = get_scrollbar()
    
    # Falls wir Groupchat haben, extrahieren wir erstmal die Member
    # Aus irgendeinem Grund macht das hier probleme
    if convo['isGroupchat']:
        convo['members'] = get_groupchat_members()
        # Hier müssen wir irgendwie sichergehen, das wir bis ganz nach unten scrollen können, aus irgendeinem Grund scrollt er wieder hoch
        chrome.run_js("arguments[0].scrollTop = 9999999999", get_scrollbar())

    downloader = Downloader(chrome, dump_path)
    
    # Falls resume geht
    if last_message_id and current_chat_id == convo['id']:
        print(f"resuming from message {last_message_id}")
        _scroll_to_message(scrollbar, last_message_id)
    # Ansonsten bis ganz nach unten scrollen zum sichergehen
    else:
        chrome.run_js("arguments[0].scrollTop = 9999999999", scrollbar)
    
    checkpoint_set(current_dump_path=inside_dump_dir, current_chat_name=convo['name'], current_chat_id=convo['id'])
    for i in range(dump_start, 10000):
        # Falls wir von "neu" anfangen
        if True:
            # Normale Dateien runterladen
            if include_files:
                downloader.files()
            # Blobs runterladen
            if include_blobs:
                downloader.blobs()
            
            # Chat dumpen
            if include_messages:    
                # Wir dumpen das gute Ding
                panel = get_panel()
                scrollbar = get_scrollbar()
                
                html = panel.html
                with open(f'{dump_path}/panel{i}.dump', 'wb') as f:
                    compressed = zcompress(html.encode("utf-8"))
                    f.write(compressed)
        
        info = chrome.run_js(js__getChatScrollInfo)
        
        debug("js__getChatScrollInfo", info)
        if info.get('messageID'):
            checkpoint_set(
                last_message_id=info['messageID'],
                last_dump_index=i,
                current_chat_id=convo['id'],
            )
            
        visible_count = info['visibleCount']
        checkpoint_set(current_chat_messages=add(visible_count), total_messages_dumped=add(visible_count))
        
        if info['scrollTop'] == 0:
            print("Fertig.")
            break

        if visible_count == 1:
            # Riesige Nachricht – um halbe Containerhöhe scrollen
            target = info['scrollTop'] - (info['containerHeight'] // 2)
        else:
            # Normal – bis Anchor unten
            target = info['anchorTop'] - info['containerHeight']

        target = max(0, target)
        chrome.run_js(
            "arguments[0].scrollTop = arguments[1]",
            scrollbar,
            target
        )

        # Warten bis neue Nachrichten geladen
        prev_len = len(panel.html)
        for _ in range(200):
            if len(get_panel().html) != prev_len:
                break
            chrome.wait(0.05)

    with open(f"{dump_path}/info.json", "w") as f:
        f.write(json.dumps(convo))
    
    checkpoint_set(
        current_chat_id=None, 
        current_dump_path=None, 
        current_chat_name=None
    )
    
    print("Fertig mit chat.")    


OLD_TO_NEW = -1
"""Dumps chats form oldest to newest."""
NEW_TO_OLD = +1
"""Dumps chats from newest to oldest."""

def iter_conversations(c, order=OLD_TO_NEW, with_checkpoint=True):
    """A generator that yields through all chats. 
    
    Ordered by the `order` param: `NEW_TO_OLD(+1)` or `OLD_TO_NEW(-1)`.
    
    If `with_checkpoint` is set, the `dump/checkpoint.json` done_ids will be skipped.
    """
    if with_checkpoint:
        done_ids = set(checkpoint_get('done_ids', []))
    else:
        done_ids = set()

    seen_ids = set()
    no_new_count = 0
    chat_pos = len(done_ids)
    """For marking the position of the current chat in dumplist"""


    inbox_scrollbar = chrome.run_js("return document.querySelector('[data-testid=\"dm-inbox-panel\"] .scrollbar-thin-custom')")
    if inbox_scrollbar is None:
        raise CommandInvokeException(f"It seems like you're not currently on /i/chat! (You're on {chrome.url})")

    # If OLD_TO_NEW, we'll scroll down to the bottom first
    if order == OLD_TO_NEW:
        debug("Scrolling to bottom first...")
        while True:
            prev_top = c.run_js("return arguments[0].scrollTop", inbox_scrollbar)
            c.run_js("arguments[0].scrollTop += 9999999", inbox_scrollbar)
            for _ in range(100):
                new_top = c.run_js("return arguments[0].scrollTop", inbox_scrollbar)
                if new_top != prev_top:
                    break
                c.wait(0.05)
            if new_top == prev_top:
                debug("Reached bottom of inbox")
                break
    
    debug("Entering while loop")
    # As long as we find more chats
    while True:
        debug("Start while, getting `visible_conversation_items()`")
        items = get_visible_conversation_items()
        new_found = False

        for dm in (reversed(items) if order==OLD_TO_NEW else items):
            debug("Item", dm)
            if dm['id'] not in seen_ids and dm['id'] not in done_ids:
                debug("Item", dm['id'], "not in seen_ids and", dm['id'], "not in done_ids")
                seen_ids.add(dm['id'])
                new_found = True
                debug("Adding chat_position to item")
                
                dm |= {"position": chat_pos, "order": order}
                debug("Yielding this item")
                yield dm
                # Increasing chat position
                chat_pos += 1
            else:
                debug("Item", dm['id'], "already seen, we skipping this")
                print("skipping", dm)

        if not new_found:
            debug("Nothing new found, increasing no_new_count")
            no_new_count += 1
            if no_new_count >= 3:
                debug("no_new_count is >= 3")
                print("No new conversations.")
                break
        else:
            debug("Something was found, setting no_new_count=0")
            no_new_count = 0

        # Scroll inbox runter
        debug("Scrolling down")
        prev_top = c.run_js("return arguments[0].scrollTop", inbox_scrollbar)
        debug("prev_top", prev_top, style=Styles.DEEP)
        scroll_by = 400 * order
        c.run_js(f"arguments[0].scrollTop += {scroll_by}", inbox_scrollbar)
        debug("Scrolled by", scroll_by)

        for _ in range(100):
            new_top = c.run_js("return arguments[0].scrollTop", inbox_scrollbar)
            if new_top != prev_top:
                break
            c.wait(0.05)

        if new_top == prev_top:
            debug("new_top == prev_top, i guess we done")
            break


# ============================= Python MISC =========================================
class Command:
    """Used for console commands in here"""
    _main: 'Main'
    
    def __init__(self, function: Callable, call_by: list[str], hidden: bool = False):
        self.function = function
        self.name: str = call_by[0]
        description = (function.__doc__ or "[No Description]").lstrip()
        
        short, longer_part, arg_description = ["", "", ""]
        sla = '\n'.join([x.strip() for x in description.split("\n")]).split("\n\n")
        try:
            short = sla[0].strip()
            longer_part = sla[1].strip()
            if len(sla) == 2:
                if re__argument.search(longer_part):
                    arg_description = longer_part
                    longer_part = ""
            elif len(sla) == 3:
                arg_description = sla[2].strip()
        except IndexError as exc:
            pass
        
        self.full_description = colorize((short + " " + longer_part).replace("\n", " "))
        self.description = short
        self.arguments = {name: colorize(description) for name, description in re__argument.findall(arg_description)}
        
        self.alias: list[str] = call_by[1:]
        
        
        # ============================ Help related things =========================================
        self.hidden = hidden
        self.required_params: list[Parameter] = []
        self.optional_params: list[Parameter] = []
        if hidden:
            self.params: list[Parameter] = []
        else:
            self.params: list[Parameter] = [param for param in list(signature(function).parameters.values())[1:]]
            for param in self.params:
                if param.default is param.empty:
                    self.required_params.append(param)
                else:
                    self.optional_params.append(param)
    
    def pretty_descriptions(self, long: bool = False, *, limit: int = 48) -> list[str]:
        """A 'prettified' description, where each line has a maximum of `limit` characters"""
        description = self.full_description if long else self.description
        
        descriptionLeft = description
        descriptions = [description]
        while len(descriptions[-1]) > limit:
            descriptions[-1] = ' '.join(descriptions[-1][:limit].split(" ")[:-1])
            descriptions.append(descriptionLeft := descriptionLeft.removeprefix(descriptions[-1]))
        return descriptions
    
    def pretty_params(self, optionals = False):
        """A list of `pretty-formated` parameters"""
        return [
            f"{(f'(\033[2m{c.annotation}\033[0m) ') if c.annotation is not c.empty else ''}{c.name}" + (f"[={c.default}]" if optionals and c.default is not c.empty else "") 
                for c in (self.required_params if optionals == False else self.params)
        ]
    
    def __call__(self, *args, **kwargs):
        """Calls the funcction callback in `self.function` and passes `self._main` as the first argument added."""
        self.function(self._main, *args, **kwargs)

def command(*invoke_by, hidden=False) -> Callable[[Callable], Command]:
    """A decorator to mark a command in the `Main` object, returns a `Command` object.
    
    ```py
    class Main:
        @command("name", "alias1", "alias2")
        def my_command(self, arg1: str):
            ...
    ```
    
    If `hidden=True`, then the command will not show up in the `help` command.
    """
    def process(function):
        return Command(function, invoke_by, hidden)
    return process


class Main:
    """The main object, with all the commands in it."""
    commands: dict[str, Command] = {}
    
    def __new__(cls):
        # We will prevent multiple instances of the Main object 
        if hasattr(cls, '_instance'):
            return cls._instance
        
        self = super().__new__(cls)
        self.commands = {}
        
        # This handles the commands
        for name, obj in cls.__dict__.items():
            if not (isinstance(obj, Command)):
                continue
            
            obj._main = self
            self.commands[obj.name] = obj
            for alias in obj.alias:
                self.commands[alias] = obj

        return self
    def get_chrome(self):
        """Returns the main chrome instance and checks if it's still connected, if not, recreates the object."""
        global chrome, actions
        try:
            chrome.run_js("console.log('are we still alive?')")
        except (PageDisconnectedError, AttributeError):
            chrome = ChromiumPage()
            if chrome.url == "chrome://newtab/":
                chrome.get("https://x.com")
                chrome.wait.doc_loaded()

        return chrome

    def process(self, cmd: str):
        """Processes a raw command input string."""
        cmd = cmd.strip()
        args = [m.strip('"') for m in re.findall(r'"[^"]*"|\S+', cmd)]
        if len(args) == 0:
            return
        cmd = args.pop(0).lower()
        
        if (command := self.commands.get(cmd)) is None:
            return print(f"command '{cmd}' not found. See `help` for more information.")
        
        try:
            hints = get_type_hints(command.function)
            newargs = []
            for a,p in zip(args, command.params):
                if (argname := p.name) in hints and not isinstance(a, (hint := hints[argname])):
                    try:
                        newargs.append(cast_value(a, hint))
                    except ValueError as exc:
                        error_print(f"Unable to cast arg {argname}='{a}' to {hint}:")
                        print("\t", str(exc).capitalize())
                        return False
                else:
                    newargs.append(a)
            
            return command(*newargs)
        # Probably an issue with the arguments
        except TypeError as exc:
            s = signature(command.function)
            
            required_params = command.required_params
            
            if len(args) > len(required_params):
                error_print(f"Too many arguments: ", end="")
            elif len(args) < len(required_params):
                error_print(f"Missing arguments: ", end="")
            else:
                raise
            
            print(f"`{cmd}` takes {len(required_params)} argument{'s' if len(required_params) > 1 else ''}, but {len(args)} {'were' if len(args) != 1 else 'was'} given")
            for i, c in enumerate(command.pretty_params()):
                if i < len(args):
                    print(f"- {c}", f'[={newargs[i]}]')
                else:
                    print(f"- \033[31m[!] {uncolorize(c)}\033[0m")
        # Issue with the command
        except CommandInvokeException as exc:
            error_print(exc)
    
    
    #region ========================================== COMMANDS ============================================
    @command("move", "cd")
    def click_chat(self, into: str):
        """Goes into chat. `into` should ideally be a (Group)chat ID. If caching is enabled, you can use @ and target user ids.
        
        
        `into`: A groupchat ID in format `{userid}-{recipientid}` or `@username` or `receipientid`
        """
        chrome = self.get_chrome()

        if "-" in into:
            into = into.replace('-', ':')
        
        if ":" not in into and not into.startswith('g') and not CACHING:
            raise CommandInvokeException("You have to specify a full id (`from:to`)")
        chat: ChromiumElement = chrome.run_js(f'return document.querySelector(\'[data-testid="dm-conversation-item-{into}"]\')')
        if chat is None: 
            if CACHING and (chat := chat_cache[into]) is None:
                raise CommandInvokeException(f"The chat `{into}` is neither currently visible nor in cache")
            chrome.get(chat['href'])
        else:
            chat.click()
        
        chrome.wait.doc_loaded()
        print("Bet!")
        
    @command("login")
    def login(self):
        """Opens the login page for you"""
        chrome = self.get_chrome()
        chrome.get("https://x.com/login")
    
    @command("me", "whoami", "username")
    def me(self):
        """Fetches your @"""
        chrome = self.get_chrome()
        global TWITTER_USERNAME
        
        print(TWITTER_USERNAME := wait_for(get_my_username))
    
    @command("members")
    def gc_members(self):
        """Fetches all gc members in currently selected gc"""
        chrome = self.get_chrome()
        current_chat = get_current_chat_data()
        if not current_chat:
            raise CommandInvokeException("You have no chat selected.")
        if not current_chat['isGroupchat']:
            raise CommandInvokeException("This is not a groupchat.")
        
        members = get_groupchat_members()
        for member in members:
            print(member['name'], member.get('status', ""))
    
    @command("clear", "cls")
    def clear(self):
        """Clears the console lol"""
        os.system("clear")
    
    @command("q", "quit", "exit", "bye")
    def byebye(self):
        "Exit."
        chrome.quit()
        exit()
    
    @command("test")
    def test(self, a: bool, b: int, c: float):
        print(a, b, c)
    
        
    @command("cache", hidden=True)
    def show_cache(self):
        for c in chat_cache.unique():
            print_chat(c, "", "\033[2m[CACHED]\033[0m")
    
    @command("chats", "cs", "ls")
    def get_chats(self):
        """Iterates through all chats"""
        chrome = self.get_chrome()
        
        for chat in iter_conversations(chrome, False):
            print_chat(chat)
    
    @command("current", "c")
    def current_chat(self):
        """Information about the currently selected chat"""
        chrome = self.get_chrome()
        current = get_current_chat_data()
        
        if current is None:
            return print("No chat selected")
        
        print_chat(current)
    
    @command("?", "help")
    def show_help(self, query: str = None):
        """Shows you this help screen.
        
        If `query` is provided, the help for `query` command will be shown with more details.
        
        `query`: The name of the command or of the alias
        """
        
        # Help for all commands
        if query is None:
            commands = set(self.commands.values())
            
            bar = "=" * 20 + f" [{len(commands)} commands] " + "=" * 50
            print(bar)
            for command in commands:
                if command.hidden:
                    continue
                
                commandName = command.name.ljust(8)
                
                descriptions = command.pretty_descriptions()
                description = descriptions.pop(0).ljust(50)
                
                print(
                    "> \033[1;4m" + commandName + "\033[0m  ",
                    description, 
                    f"[{', '.join([f"\033[2m{a}\033[0m" for a in command.alias])}]" if command.alias else "",
                    ''.join(['\n' + ' ' * (len(commandName) + 4) + " |" + desc for desc in descriptions])
                )
            print("=" * len(bar))
        else:
            command = self.commands.get(query.strip().lower())
            if command is None:
                raise CommandInvokeException(f"Command `{query}` does not exist")

            print("=" * 15 + f"[\033[1m{command.name.upper()}\033[0m]" + "=" * 40)
            print(f"{'\n'.join(command.pretty_descriptions(True, limit=80))}")
            
            if len(command.params) > 0 or len(command.alias) > 0:
                print()
                if len(command.params) > 0:
                    print(f"\033[1mArguments\033[0m")
                    for i, param in enumerate(command.pretty_params(True)):
                        print(param)
                        _param = command.params[i]
                        if (descp := command.arguments.get(_param.name)):
                            print(f"    {descp}")
                    print()
                if len(command.alias) > 0:
                    print(f"\033[1mAlias\033[0m: {', '.join([f'\033[2m{a}\033[0m' for a in command.alias])}")
            
    @command("debug", hidden=True)
    def debug_window(self, text: str = None):
        global DEBUG_CONSOLE
        if DEBUG_CONSOLE is None:
            from XDump.console import ConsoleWindow
            DEBUG_CONSOLE = ConsoleWindow("Debug")
        if text is not None:
            debug(text, style=Styles.NORMAL)
    
    
    @command("dumpall", "da")
    def dump_all(self, new_to_old: bool = False):
        """Dumps every chat seen in dm list from the top to the bottom.
        
        If `new_to_old` is not set, then the scraper will first scroll all the way down
        to the bottom, to the oldest chat and start dumping from there.
        
        `new_to_old`: Whether the chats should be dumped from top to bottom (newest to oldest chat)
        """
        chrome = self.get_chrome()
        while not '/chat' in chrome.url:
            input("Bitte auf richtige URL gehen: ")

        
        os.makedirs("dump", exist_ok=True)
        checkpoint_set(started_at=time())
        # Verwendung:
        for n_chat, conv in enumerate(iter_conversations(chrome, NEW_TO_OLD if new_to_old else OLD_TO_NEW)):
            print(f"Chat: {conv['name']} ({conv['id']}), Groupchat: {conv['isGroupchat']}")
            checkpoint_set(last_update=time())
            checkpoint_set(total_chats=n_chat)
            
            prev_url = chrome.url
            chrome.listen.set_targets("blob:")
            chrome.listen.start()
            debug("Startet network listener")

            chrome.run_js(f"""
                [...document.querySelectorAll('[data-testid^="dm-conversation-item-"]')]
                    .find(el => el.dataset.testid === 'dm-conversation-item-{conv["id"]}')
                    ?.querySelector('a')
                    ?.click()
            """)
            debug("Moved into chat, waiting for url change")

            # Warten bis URL sich ändert
            for _ in range(200):
                if chrome.url != prev_url:
                    break
                chrome.wait(0.05)
            debug("URL changed, waiting for chat to be visible")

            # Warten bis erste Message sichtbar
            for _ in range(200):
                msg = chrome.run_js("return !!document.querySelector('[data-testid^=\"message-text-\"]')")
                if msg:
                    break
                chrome.wait(0.05)
            debug("Starting to dump...")
            
            debug("[dump_current_chat]", Styles.DEEP)
            # Wir haben geladen, jetzt dumpen wir den chat
            info = dump_current_chat(conv)
            
            chrome.listen.stop()
            debug("Finished dumping current chat, saving checkpoint", Styles.SUCCESS)
            
            # Checkpoint speichern
            checkpoint_set(done_ids=append(conv['id']))
            debug("Saved checkpoint")
        
        checkpoint_set(done=True)
        
    
    @command("dump", "dc", "single")
    def dump_single(self):
        """Dumps the currently opened dm chat"""
        chrome = self.get_chrome()
        
        
        # Get current chat
        data = get_current_chat_data()
        if not data:
            raise CommandInvokeException("Please select a chat first")
        
        input("[Enter] to dump '" + data["name"] + "'")
        
        chrome.listen.set_targets("blob:")
        chrome.listen.start()
        chrome.get(data['href'])
        wait_for(lambda: chrome.run_js("""return document.querySelector('[data-testid="dm-message-list]')"""))
        
        dump_current_chat(data, True, True, True)
        chrome.listen.stop()
        
    #endregion
    def banner(self):
        print("""
                d8b                                  
               88P                                  
              d88                                   
?88,  88P d888888  ?88   d8P  88bd8b,d88b ?88,.d88b,
 `?8bd8P'd8P' ?88  d88   88   88P'`?8P'?8b`?88'  ?88
 d8P?8b, 88b  ,88b ?8(  d88  d88  d88  88P  88b  d8P
d8P' `?8b`?88P'`88b`?88P'?8bd88' d88'  88b  888888P'
                                            88P'    
                   \033[1;5;4m[by @kvsxxx]\033[0m             d88      
                                           ?8P      
        """)
        

main = Main()
main.banner()

while True:
    print("XDump", end="")
    if TWITTER_USERNAME:
        print(f":\033[2m{TWITTER_USERNAME}\033[0m")
    main.process(input(" > "))
    print()