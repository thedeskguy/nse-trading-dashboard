import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

# threading.Lock is intentional here: callers always use asyncio.to_thread(), so this
# function runs inside a thread-pool thread, not the event loop. The lock prevents a
# race where two simultaneous cache-misses both attempt a TOTP-based Angel One login
# and invalidate each other's sessions. asyncio.Lock would be wrong here (different thread).
_lock = threading.Lock()


def get_angel_session():
    from tools.angel_auth import get_session
    with _lock:
        return get_session()
