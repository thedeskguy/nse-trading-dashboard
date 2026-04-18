"""NSE market-hours utility.

NSE equity segment: Monday–Friday, 09:15–15:30 IST.
Pre-open session runs 09:00–09:15 but data doesn't change significantly,
so we treat 09:15 as the open.
"""
from datetime import datetime, time, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))
_OPEN  = time(9, 15)
_CLOSE = time(15, 30)


def is_market_open(now: datetime | None = None) -> bool:
    """Return True if NSE is currently in its regular trading session."""
    if now is None:
        now = datetime.now(_IST)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=_IST)
    else:
        now = now.astimezone(_IST)

    if now.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    return _OPEN <= now.time() <= _CLOSE


def adaptive_ttl(base_ttl: int) -> int:
    """Return `base_ttl` when market is open; 30 min when closed (data is stale anyway)."""
    return base_ttl if is_market_open() else 1800
