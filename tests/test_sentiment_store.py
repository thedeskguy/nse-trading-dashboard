import tools.sentiment_store as ss
from tools.sentiment_store import readout_to_row


def _readout():
    return {"score": -39.9, "label": "Bearish", "confidence": 80,
            "article_count": 25, "insufficient": False,
            "top_headlines": [{"title": "x", "sentiment": -0.9}],
            "scored_by": "finbert"}


def test_readout_to_row_maps_fields():
    row = readout_to_row("stock", "RELIANCE", _readout(), "2026-06-14")
    assert row["scope"] == "stock"
    assert row["key"] == "RELIANCE"
    assert row["as_of_date"] == "2026-06-14"
    assert row["label"] == "Bearish"
    assert row["score"] == -39.9
    assert row["article_count"] == 25
    assert row["insufficient"] is False
    assert row["scored_by"] == "finbert"
    assert isinstance(row["top_headlines"], list)


class _FakeQuery:
    def __init__(self, data):
        self._data = data
        self.captured = {}

    def upsert(self, rows, on_conflict=None):
        self.captured["rows"] = rows
        self.captured["on_conflict"] = on_conflict
        return self

    def select(self, *a):
        return self

    def eq(self, *a):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        class R:
            data = self._data
        return R()


class _FakeClient:
    def __init__(self, data=None):
        self.q = _FakeQuery(data or [])

    def table(self, name):
        return self.q


def test_upsert_snapshot_calls_upsert(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(ss, "_client", lambda: fake)
    ss.upsert_snapshot("market", "india", _readout(), "2026-06-14")
    assert fake.q.captured["on_conflict"] == "scope,key,as_of_date"
    assert fake.q.captured["rows"][0]["key"] == "india"


def test_get_snapshot_returns_readout(monkeypatch):
    row = readout_to_row("stock", "RELIANCE", _readout(), "2026-06-14")
    fake = _FakeClient([row])
    monkeypatch.setattr(ss, "_client", lambda: fake)
    monkeypatch.setattr(ss, "is_configured", lambda: True)
    r = ss.get_snapshot("stock", "RELIANCE")
    assert r["label"] == "Bearish"
    assert r["scored_by"] == "finbert"
    assert set(r) >= {"score", "label", "confidence", "article_count",
                      "insufficient", "top_headlines", "scored_by"}


def test_get_snapshot_none_when_not_configured(monkeypatch):
    monkeypatch.setattr(ss, "is_configured", lambda: False)
    assert ss.get_snapshot("stock", "RELIANCE") is None


def test_get_snapshot_none_on_miss(monkeypatch):
    monkeypatch.setattr(ss, "_client", lambda: _FakeClient([]))
    monkeypatch.setattr(ss, "is_configured", lambda: True)
    assert ss.get_snapshot("stock", "NOPE") is None
