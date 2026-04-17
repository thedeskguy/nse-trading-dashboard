"""
Tests for the stock-page backend changes:
- VALID_COMBOS includes 1m interval
- fetch_stock_data validates interval/period combos
- score_fundamentals returns the expected shape
"""

import sys
import unittest

sys.path.insert(0, ".")


class ValidCombosTest(unittest.TestCase):
    def test_1m_interval_supported(self):
        from tools.fetch_stock_data import VALID_COMBOS
        self.assertIn("1m", VALID_COMBOS)
        self.assertIn("1d", VALID_COMBOS["1m"])
        self.assertIn("5d", VALID_COMBOS["1m"])

    def test_10y_and_max_available_for_daily(self):
        from tools.fetch_stock_data import VALID_COMBOS
        self.assertIn("10y", VALID_COMBOS["1d"])
        self.assertIn("max", VALID_COMBOS["1d"])

    def test_invalid_combo_rejected(self):
        from tools.fetch_stock_data import fetch_ohlcv
        with self.assertRaises(ValueError):
            fetch_ohlcv("RELIANCE.NS", interval="1m", period="1y")
        with self.assertRaises(ValueError):
            fetch_ohlcv("RELIANCE.NS", interval="bogus", period="1mo")


class AngelFallbackTest(unittest.TestCase):
    """Long periods must skip Angel One (only ~3-month history) and go to yfinance."""

    def test_long_period_bypasses_angel(self):
        from unittest.mock import patch
        import pandas as pd
        from tools import fetch_stock_data as mod

        sample_df = pd.DataFrame({
            "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [100],
        }, index=pd.DatetimeIndex(["2020-01-01"]))

        angel_calls = {"n": 0}
        def fake_angel(*a, **kw):
            angel_calls["n"] += 1
            return sample_df

        def fake_yf(ticker, interval, period, auto_adjust=True):
            return sample_df

        with patch.object(mod, "_fetch_yfinance", side_effect=fake_yf):
            with patch("tools.fetch_angel_ohlcv.fetch_angel_ohlcv", side_effect=fake_angel):
                for long_period in ("1y", "2y", "5y", "10y", "max"):
                    mod.fetch_ohlcv("RELIANCE.NS", interval="1d", period=long_period)
        self.assertEqual(angel_calls["n"], 0, "Angel must not be called for long periods")

    def test_short_period_still_tries_angel(self):
        from unittest.mock import patch
        import pandas as pd
        from tools import fetch_stock_data as mod

        sample_df = pd.DataFrame({
            "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [100],
        }, index=pd.DatetimeIndex(["2020-01-01"]))

        angel_calls = {"n": 0}
        def fake_angel(*a, **kw):
            angel_calls["n"] += 1
            return sample_df

        with patch("tools.fetch_angel_ohlcv.fetch_angel_ohlcv", side_effect=fake_angel):
            mod.fetch_ohlcv("RELIANCE.NS", interval="1d", period="3mo")
        self.assertEqual(angel_calls["n"], 1, "Angel should be the first choice for short periods")


class ScreenerFallbackTest(unittest.TestCase):
    """If the /consolidated/ page returns 200 but has empty number spans
    (small caps like KRISHANA that only file standalone), the scraper must
    fall back to the standalone URL instead of returning an empty dict."""

    def test_empty_consolidated_falls_back_to_standalone(self):
        from unittest.mock import patch
        from tools import fetch_fundamentals as mod

        empty_consolidated = (
            '<html><body>'
            '<ul id="top-ratios">'
            '<li><span class="name">Stock P/E</span>'
            '<span class="value"><span class="number"></span></span></li>'
            '<li><span class="name">ROE</span>'
            '<span class="value"><span class="number"></span></span></li>'
            '</ul></body></html>'
        )
        populated_standalone = (
            '<html><body>'
            '<ul id="top-ratios">'
            '<li><span class="name">Stock P/E</span>'
            '<span class="value"><span class="number">20.5</span></span></li>'
            '<li><span class="name">ROE</span>'
            '<span class="value"><span class="number">38.2</span></span></li>'
            '<li><span class="name">Market Cap</span>'
            '<span class="value">Rs<span class="number">3,697</span>Cr</span></li>'
            '</ul></body></html>'
        )

        calls = []

        class FakeResp:
            def __init__(self, text): self.status_code = 200; self.text = text

        def fake_get(url, **kw):
            calls.append(url)
            if 'consolidated' in url:
                return FakeResp(empty_consolidated)
            return FakeResp(populated_standalone)

        with patch('curl_cffi.requests.get', side_effect=fake_get):
            result = mod._fetch_screener('KRISHANA.NS')

        # Both URLs must have been tried — the empty consolidated triggers the fallback.
        self.assertTrue(any('consolidated' in u for u in calls))
        self.assertTrue(any('consolidated' not in u and 'KRISHANA' in u for u in calls))
        # Standalone numbers must have been parsed.
        self.assertEqual(result['pe_trailing'], 20.5)
        self.assertAlmostEqual(result['roe'], 0.382, places=3)


class FundamentalsScoringTest(unittest.TestCase):
    def test_score_shape(self):
        from tools.fetch_fundamentals import score_fundamentals
        data = {
            "pe_trailing": 18,
            "roe": 0.22,
            "debt_to_equity": 25,
            "revenue_growth": 0.15,
            "profit_margin": 0.14,
            "recommendation": "buy",
            "target_price": 110,
        }
        out = score_fundamentals(data, current_price=100)
        self.assertIn("score", out)
        self.assertIn("grade", out)
        self.assertIn("breakdown", out)
        self.assertIsInstance(out["score"], int)
        self.assertIn(out["grade"], {"Strong", "Fair", "Weak"})
        # Strong fundamentals → expect at least a Fair grade.
        self.assertGreaterEqual(out["score"], 45)

    def test_handles_missing_fields(self):
        from tools.fetch_fundamentals import score_fundamentals
        out = score_fundamentals({}, current_price=None)
        self.assertEqual(out["grade"], "Weak")
        for key, item in out["breakdown"].items():
            self.assertIn("points", item)
            self.assertIn("max", item)
            self.assertIn("label", item)


if __name__ == "__main__":
    unittest.main()
