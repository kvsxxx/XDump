
import os
import json


CHECKPOINT_FILE = './dump/checkpoint.json'

class _Append:
    __slots__ = ('v',)
    def __init__(self, v):
        self.v = v

def append(v):
    return _Append(v)

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {'done_ids': [], 'current_index': 0, 'users': []}

def checkpoint_set(**kwargs):
    for key, value in kwargs.items():
        checkpoint = load_checkpoint()
        if isinstance(value, _Append):
            checkpoint[key].append(value.v)
        else:
            checkpoint[key] = value
        
        save_checkpoint(checkpoint)
def checkpoint_get(key: str, default=None):
    checkpoint = load_checkpoint()
    return checkpoint.get(key, default)

def save_checkpoint(data):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f)