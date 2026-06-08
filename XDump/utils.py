import re
from time import time, sleep
from collections.abc import Callable
from typing import Any

def cast_value(value, typ):
    """Helper for command arugment parsing"""
    if typ is bool:
        if isinstance(value, str):
            return value.lower() not in ('false', '0', 'no', 'n', '')
        return bool(value)
    return typ(value)

print_chat = lambda chat, prefix = "", suffix = "": print(prefix +
    f"- \033[1m{chat["name"]}\033[0m [{chat["username"]}] | \033[2m[{chat["id"]}]\033[0m {'G+' if chat["isGroupchat"] else ''} {suffix}\n" +
    f"    {chat['lastMessage']} (\033[2m{chat['lastMessageTime']}\033[0m)"
)
"""Helper function for printing a `TwitterDM` object"""

error_print = lambda exc, *args, **kwargs: print(f"[\033[31m!\033[0m] \033[1mError: {exc}\033[0m", *args, **kwargs)

class CommandInvokeException(Exception):
    pass

def wait_for(l: Callable[[], Any | None], timeout: int = 15):
    """Helper for waiting until `l: function` returns anything but `None`.
    
    If `timeout` is reached, a `TimeoutError` is thrown.
    """
    start = time()
    while (res := l()) == None:
        sleep(0.2)
        if time() - start > timeout:
            break
    else:
        return res
    
    raise TimeoutError()


re__block = re.compile("`[^`]*`")
re__argument = re.compile("`([^`]*)`: (.*)")
re__no_color = re.compile(r"\x1b\[[0-9;]*m")

def colorize(text):
    """Basically a MD-like formatter for strings."""
    # Format `keywords`
    keywords: list[str] = set(re__block.findall(text))
    for keyword in keywords:
        text = text.replace(keyword, f"\033[48;5;238m\033[38;5;255m {keyword.strip("`")} \033[0m")
    return text

def uncolorize(text):
    """Removes all formatting from `colorize()`"""
    return re__no_color.sub("", text)