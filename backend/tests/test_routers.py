"""
FastAPI router tests using TestClient.
External API calls (Angel One, yfinance, Supabase) are patched out.
JWT auth is bypassed via dependency override.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Stub heavy optional deps before importing the app
for mod in ["sentry_sdk", "razorpay"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from main import app
from deps import verify_supabase_jwt

FAKE_USER = {"user_id": "test-uid-123", "email": "test@example.com"}


@pytest.fixture(autouse=True)
def override_auth():
    """Replace JWT verification with a no-op returning a fake user."""
    app.dependency_overrides[verify_supabase_jwt] = lambda: FAKE_USER
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Market status
# ---------------------------------------------------------------------------

def test_market_status(client):
    r = client.get("/api/v1/market/status")
    assert r.status_code == 200
    data = r.json()
    assert "is_open" in data
    assert isinstance(data["is_open"], bool)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_signal_rejects_invalid_ticker(client):
    r = client.get("/api/v1/market/signal", params={"ticker": "../../etc/passwd"})
    assert r.status_code == 422


def test_signal_rejects_empty_ticker(client):
    r = client.get("/api/v1/market/signal", params={"ticker": ""})
    assert r.status_code == 422


def test_signal_rejects_bad_interval(client):
    r = client.get(
        "/api/v1/market/signal",
        params={"ticker": "RELIANCE.NS", "interval": "999y"},
    )
    assert r.status_code == 422


def test_options_chain_rejects_bad_symbol(client):
    r = client.get("/api/v1/options/chain", params={"symbol": "INVALIDINDEX"})
    assert r.status_code == 422


def test_options_chain_accepts_valid_symbol(client):
    """Accepted by validation layer; 503 expected when upstream is unavailable in test."""
    with patch("routers.options.cached", new_callable=AsyncMock, side_effect=Exception("no upstream")):
        r = client.get("/api/v1/options/chain", params={"symbol": "NIFTY"})
    assert r.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Auth guard (dependency override removed → must fail with 401/403)
# ---------------------------------------------------------------------------

def test_auth_guard_blocks_unauthenticated():
    """Without the override, a request without a token must be rejected."""
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/v1/market/status")
    assert r.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# Payments — subscription-status
# ---------------------------------------------------------------------------

def test_subscription_status_no_supabase(client):
    """When Supabase env vars are absent the endpoint should return free plan."""
    with patch("routers.payments.get_settings") as mock_settings:
        s = MagicMock()
        s.SUPABASE_URL = None
        s.SUPABASE_SERVICE_ROLE_KEY = None
        mock_settings.return_value = s
        r = client.get("/api/v1/payments/subscription-status")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "free"
    assert body["status"] == "inactive"


# ---------------------------------------------------------------------------
# Webhook — no Razorpay secret configured → skips HMAC, returns 200
# ---------------------------------------------------------------------------

def test_webhook_no_secret_accepts_payload(client):
    """When RAZORPAY_WEBHOOK_SECRET is unset the endpoint skips HMAC and returns 200."""
    payload = b'{"event":"unknown","payload":{}}'

    with patch("routers.payments.get_settings") as mock_settings:
        s = MagicMock()
        s.SUPABASE_URL = None
        s.SUPABASE_SERVICE_ROLE_KEY = None
        s.RAZORPAY_WEBHOOK_SECRET = None
        mock_settings.return_value = s

        r = client.post(
            "/api/v1/payments/webhook",
            content=payload,
            headers={"x-razorpay-signature": "ignored"},
        )

    assert r.status_code == 200
    assert r.json()["received"] is True
