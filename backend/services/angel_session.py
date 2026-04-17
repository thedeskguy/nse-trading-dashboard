import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

_lock = threading.Lock()


def get_angel_session():
    from tools.angel_auth import get_session
    with _lock:
        return get_session()
