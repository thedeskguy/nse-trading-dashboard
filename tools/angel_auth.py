"""
Angel One SmartAPI — authentication singleton.
Logs in once per process, reuses the session token, re-logs on expiry.
"""

import os
import base64
import binascii
import pyotp
from dotenv import load_dotenv

_obj = None


def _normalize_totp_secret(secret: str) -> str:
    """
    Accept either base32 or UUID/hex format TOTP secret.
    Angel One sometimes provides the key as a UUID-style hex string
    (e.g. d67a64e3-fd0c-4400-ac22-50bb83e55fba).
    pyotp requires base32, so convert if needed.
    """
    cleaned = secret.replace("-", "").replace(" ", "").upper()

    # Try interpreting as base32 first
    try:
        base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))
        return cleaned
    except Exception:
        pass

    # Treat as hex → convert to base32
    try:
        raw_bytes = binascii.unhexlify(cleaned)
        return base64.b32encode(raw_bytes).decode().rstrip("=")
    except Exception:
        # Last resort — return as-is and let pyotp error naturally
        return cleaned


def _login():
    try:
        from SmartApi import SmartConnect
    except ImportError:
        raise ImportError("smartapi-python is not installed. Run: pip install smartapi-python")

    load_dotenv()

    api_key    = os.environ.get("ANGEL_API_KEY")
    client_id  = os.environ.get("ANGEL_CLIENT_ID")
    mpin       = os.environ.get("ANGEL_MPIN")
    totp_raw   = os.environ.get("ANGEL_TOTP_SECRET")

    if not all([api_key, client_id, mpin, totp_raw]):
        missing = [k for k, v in {
            "ANGEL_API_KEY": api_key,
            "ANGEL_CLIENT_ID": client_id,
            "ANGEL_MPIN": mpin,
            "ANGEL_TOTP_SECRET": totp_raw,
        }.items() if not v]
        raise EnvironmentError(f"Missing credentials in .env: {missing}")

    totp_secret = _normalize_totp_secret(totp_raw)
    totp_code   = pyotp.TOTP(totp_secret).now()

    obj = SmartConnect(api_key=api_key)
    resp = obj.generateSession(client_id, mpin, totp_code)

    if not resp or resp.get("status") is False:
        raise ConnectionError(
            f"Angel One login failed: {resp.get('message', 'Unknown error')}. "
            "Check CLIENT_ID, MPIN, and TOTP_SECRET in .env."
        )

    return obj


def get_session() -> "SmartConnect":
    """Return the cached SmartConnect session, logging in if needed."""
    global _obj
    if _obj is None:
        _obj = _login()
    return _obj


def reset_session() -> None:
    """Force re-login on next call (use after token expiry errors)."""
    global _obj
    _obj = None


if __name__ == "__main__":
    s = get_session()
    print("Login OK:", s)
