import os
import json


CHECKPOINT_FILE = './dump/checkpoint.json'
CHECKPOINT_CACHE = None

class _Operation:
    __slots__ = ('v',)
    def __init__(self, v):
        self.v = v
class _Append(_Operation):
    ...
class _Add(_Operation):
    ...

def append(v):
    return _Append(v)
def add(v):
    return _Add(v)

def _load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {}


def load_checkpoint():
    global CHECKPOINT_CACHE
    if CHECKPOINT_CACHE is None:
        CHECKPOINT_CACHE = _load_checkpoint()
    return CHECKPOINT_CACHE
    
def checkpoint_set(**kwargs):
    checkpoint = load_checkpoint()
    for key, value in kwargs.items():
        if isinstance(value, _Operation):
            try:
                if isinstance(value, _Append):
                    checkpoint[key].append(value.v)
                elif isinstance(value, _Add):
                    checkpoint[key] += value.v
            # Fallback in case checkpoint[key] doesn't exist yet
            except KeyError as exc:
                print(key, exc)
                if not key in checkpoint:
                    if isinstance(value, _Add):
                        if isinstance(value.v, (list, tuple, set)):
                            checkpoint[key] = value.v.__class__((value.v,))
                        else:
                            checkpoint[key] = value.v
                    elif isinstance(value, _Append):
                        checkpoint[key] = [value.v]
                    else: raise
                else: raise
        else:
            checkpoint[key] = value
        
    save_checkpoint(checkpoint)

def checkpoint_get(key: str, default=None):
    checkpoint = load_checkpoint()
    return checkpoint.get(key, default)

def save_checkpoint(data):
    tmp_file = CHECKPOINT_FILE + ".tmp"

    with open(tmp_file, 'w') as f:
        json.dump(data, f)

    os.replace(tmp_file, CHECKPOINT_FILE)