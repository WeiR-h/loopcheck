"""One browser worker at a time across the original demo and connected projects."""
from contextlib import contextmanager
import threading
import time

_slot = threading.Lock()

@contextmanager
def browser_slot(cancelled=lambda: False):
    deadline = time.monotonic() + 120
    while not _slot.acquire(timeout=.1):
        if cancelled(): raise ValueError('Cancelled while waiting for browser')
        if time.monotonic() >= deadline: raise ValueError('Browser queue deadline exceeded (120s)')
    try:
        if cancelled(): raise ValueError('Cancelled before browser launch')
        yield
    finally:
        _slot.release()
