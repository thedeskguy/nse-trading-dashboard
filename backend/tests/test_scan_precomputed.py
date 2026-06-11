# backend/tests/test_scan_precomputed.py
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))             # repo root

from fastapi.testclient import TestClient

import main
from deps import verify_supabase_jwt
import routers.market as market
from tools import price_store


def test_scan_returns_precomputed_when_market_closed(monkeypatch):
    main.app.dependency_overrides[verify_supabase_jwt] = lambda: {"user_id": "u1", "email": "t@t.t"}
    try:
        monkeypatch.setattr(market, "is_market_open", lambda: False)
        payload = [{"ticker": "RELIANCE.NS", "name": "Reliance", "signal": "BUY",
                    "confidence": 80, "last_price": 2900.0, "change_pct": 1.2}]
        monkeypatch.setattr(
            price_store, "get_scan",
            lambda idx: {"payload": payload,
                         "computed_at": datetime.now(timezone.utc).isoformat()},
        )
        # TestClient without context manager: lifespan (Angel warm-up) is skipped
        client = TestClient(main.app)
        res = client.get("/api/v1/market/scan?index=NIFTY50")
        assert res.status_code == 200
        body = res.json()
        assert body["precomputed"] is True
        assert body["stocks"] == payload
        assert body["index"] == "NIFTY50"
    finally:
        main.app.dependency_overrides.clear()
