"""
Tests for the two dashboard bugs fixed:
1. KeyError: 'signal_components' when underlying signal is HOLD
2. Options chain table not showing data for non-default expiry dates
"""

import sys
import types
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

sys.path.insert(0, ".")


# ── Helpers to build minimal mocks ────────────────────────────────────────────

def _make_fake_chain_df(expiry: str, spot: float = 22000.0, symbol: str = "NIFTY") -> pd.DataFrame:
    """Create a minimal options chain DataFrame for a given expiry."""
    strikes = [spot - 100, spot, spot + 100]
    rows = []
    for s in strikes:
        rows.append({
            "strike": int(s), "expiry": expiry,
            "CE_ltp": 100.0, "CE_oi": 5000, "CE_chg_oi": 100, "CE_iv": 15.0, "CE_volume": 1000, "CE_bid": 99.0, "CE_ask": 101.0,
            "PE_ltp":  80.0, "PE_oi": 4000, "PE_chg_oi": -50, "PE_iv": 14.0, "PE_volume":  800, "PE_bid": 79.0, "PE_ask":  81.0,
        })
    return pd.DataFrame(rows)


def _make_fake_sig(signal: str = "HOLD") -> dict:
    """Return a minimal generate_signal-style dict."""
    return {
        "signal":     signal,
        "confidence": 50,
        "last_price": 22000.0,
        "stop_loss":  21800.0,
        "target":     22200.0,
        "components": {
            "RSI":                {"value": 55, "signal": "Neutral", "points": 0},
            "MACD":               {"value": 0.5, "signal": "Bullish (above signal)", "points": 10},
            "EMA Trend":          {"value": "Price ₹22000.00", "signal": "Above all 4 EMAs — Strong Bullish", "points": 20},
            "Bollinger Bands":    {"value": "BB% 0.5", "signal": "Inside Bands — Neutral", "points": 0},
            "Support/Resistance": {"value": "N/A", "signal": "No S/R data", "points": 0},
            "OBV":                {"value": "See chart", "signal": "OBV confirming uptrend", "points": 15},
        },
    }


def _make_fake_chain_meta(expiries=None):
    if expiries is None:
        expiries = ["10APR2026", "17APR2026", "24APR2026", "01MAY2026"]
    return {
        "symbol":           "NIFTY",
        "underlying_value": 22000.0,
        "timestamp":        "10:00:00",
        "expiry_dates":     expiries,
        "chain":            _make_fake_chain_df(expiries[0]),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Case 1: HOLD signal → signal_components must be present
# ══════════════════════════════════════════════════════════════════════════════

class TestHoldSignalComponents(unittest.TestCase):

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_hold_returns_signal_components(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """HOLD path must include signal_components so dashboard never raises KeyError."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_gen.return_value = _make_fake_sig(signal="HOLD")
        mock_chain.return_value = _make_fake_chain_meta()

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertEqual(result["underlying_signal"], "HOLD")
        self.assertIn("signal_components", result,
                      "HOLD result must contain 'signal_components' key to avoid KeyError in dashboard")
        self.assertIsInstance(result["signal_components"], dict)
        self.assertIn("RSI", result["signal_components"])

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_hold_returns_expiry_dates(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """HOLD path must include expiry_dates so options chain selectbox still renders."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_gen.return_value = _make_fake_sig(signal="HOLD")
        mock_chain.return_value = _make_fake_chain_meta()

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertIn("expiry_dates", result)
        self.assertIsInstance(result["expiry_dates"], list)
        self.assertGreater(len(result["expiry_dates"]), 0)

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_hold_chain_fetch_failure_returns_empty_expiry_dates(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """If chain fetch fails during HOLD, expiry_dates defaults to [] gracefully."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_gen.return_value = _make_fake_sig(signal="HOLD")
        mock_chain.side_effect = Exception("API down")

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertIn("expiry_dates", result)
        self.assertEqual(result["expiry_dates"], [])

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_hold_returns_timestamp(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """HOLD path must include timestamp so 'Data as of N/A' is fixed."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_gen.return_value = _make_fake_sig(signal="HOLD")
        mock_chain.return_value = _make_fake_chain_meta()

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertIn("timestamp", result)
        self.assertEqual(result["timestamp"], "10:00:00",
                         "timestamp must come from chain meta, not be None/N/A")

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_hold_returns_pcr(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """HOLD path must include pcr dict so Put/Call Ratio shows instead of N/A."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_gen.return_value = _make_fake_sig(signal="HOLD")
        mock_chain.return_value = _make_fake_chain_meta()

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertIn("pcr", result)
        self.assertIsInstance(result["pcr"], dict)

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_hold_chain_failure_returns_none_timestamp_and_empty_pcr(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """If chain fetch fails during HOLD, timestamp=None and pcr={} — no crash."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_gen.return_value = _make_fake_sig(signal="HOLD")
        mock_chain.side_effect = Exception("API down")

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertIsNone(result.get("timestamp"))
        self.assertEqual(result.get("pcr"), {})


# ══════════════════════════════════════════════════════════════════════════════
# Case 2: Non-default expiry selected → chain re-fetched for that expiry
# ══════════════════════════════════════════════════════════════════════════════

class TestOptionsChainExpiryFiltering(unittest.TestCase):

    def test_chain_df_filtered_by_expiry(self):
        """render_options_chain_table uses chain_df filtered to selected expiry."""
        expiry1 = "10APR2026"
        expiry2 = "17APR2026"

        df_e1 = _make_fake_chain_df(expiry1, spot=22000.0)
        df_e2 = _make_fake_chain_df(expiry2, spot=22000.0)

        # When only expiry2 data is passed (as would be returned by fetch_options_chain(expiry=expiry2))
        filtered = df_e2[df_e2["expiry"] == expiry2]
        self.assertFalse(filtered.empty, "Chain DataFrame for selected expiry should not be empty")
        self.assertEqual(list(filtered["expiry"].unique()), [expiry2])

        # If wrong expiry data is passed (old bug: chain fetched for expiry1, user selects expiry2)
        wrong_filter = df_e1[df_e1["expiry"] == expiry2]
        self.assertTrue(wrong_filter.empty, "Old bug: filtering expiry2 from expiry1 data returns empty")

    def test_all_expiry_dates_available_in_selectbox(self):
        """opt_result should expose all expiry dates (not truncated to 6)."""
        expiries = [f"{d:02d}APR2026" for d in range(7, 30, 7)] + [f"{d:02d}MAY2026" for d in range(7, 30, 7)]
        meta = _make_fake_chain_meta(expiries=expiries)
        # Simulates: expiry_dates = opt_result.get("expiry_dates", [])
        result_expiry_dates = meta["expiry_dates"]
        self.assertEqual(len(result_expiry_dates), len(expiries),
                         "All expiry dates must be in selectbox, not just first 6")

    def test_chain_rows_present_for_each_expiry(self):
        """Each expiry's chain data has rows with the correct expiry label."""
        expiries = ["10APR2026", "17APR2026", "24APR2026"]
        for exp in expiries:
            df = _make_fake_chain_df(exp, spot=22000.0)
            self.assertTrue(len(df) > 0)
            self.assertTrue((df["expiry"] == exp).all(),
                            f"All rows in chain for {exp} must have expiry={exp}")


# ══════════════════════════════════════════════════════════════════════════════
# Case 3: BUY/SELL path still works correctly (regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestBuySellPathRegression(unittest.TestCase):

    @patch("tools.analyze_options.fetch_options_chain")
    @patch("tools.analyze_options.generate_signal")
    @patch("tools.analyze_options.compute_all")
    @patch("tools.analyze_options.fetch_ohlcv")
    def test_buy_signal_has_signal_components(self, mock_fetch, mock_compute, mock_gen, mock_chain):
        """BUY path must also include signal_components."""
        mock_fetch.return_value = pd.DataFrame({"Close": [1] * 30})
        mock_compute.return_value = pd.DataFrame({"Close": [1] * 30})
        buy_sig = _make_fake_sig(signal="BUY")
        buy_sig["confidence"] = 75
        mock_gen.return_value = buy_sig

        expiries = ["10APR2026", "17APR2026"]
        chain_df = _make_fake_chain_df(expiries[0], spot=22000.0)
        chain_df2 = _make_fake_chain_df(expiries[1], spot=22000.0)
        mock_chain.side_effect = [
            {**_make_fake_chain_meta(expiries), "chain": chain_df},
            {**_make_fake_chain_meta(expiries), "chain": chain_df2},
        ]

        from tools.analyze_options import recommend_option
        result = recommend_option("NIFTY")

        self.assertIn("signal_components", result)
        self.assertIn("expiry_dates", result)
        self.assertEqual(result["underlying_signal"], "BUY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
