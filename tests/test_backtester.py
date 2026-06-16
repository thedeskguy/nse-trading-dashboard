"""
Tests for tools/backtester.py:
- result shape (strategy echo, description, benchmark, new stats)
- stats math on hand-built fixtures
- ML strategy: insufficient-history error, determinism, signal validity
"""

import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, ".")


def synthetic_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """Deterministic random-walk OHLCV with a DatetimeIndex of n business days."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.015, n)
    close = 100 * np.cumprod(1 + rets)
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.003, n)),
            "High": close * (1 + np.abs(rng.normal(0, 0.006, n))),
            "Low": close * (1 - np.abs(rng.normal(0, 0.006, n))),
            "Close": close,
            "Volume": rng.integers(1_000_00, 5_000_00, n).astype(float),
        },
        index=dates,
    )


def enriched(n: int, seed: int = 42) -> pd.DataFrame:
    from tools.compute_indicators import compute_all
    return compute_all(synthetic_ohlcv(n, seed))


class IndicatorResultShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.backtester import run_backtest
        cls.result = run_backtest(enriched(260), strategy="indicator")

    def test_strategy_fields(self):
        self.assertEqual(self.result["strategy"], "indicator")
        self.assertIn("indicator signal", self.result["strategy_description"])
        self.assertIsNone(self.result["error"])

    def test_equity_curve_has_benchmark_starting_at_100(self):
        curve = self.result["equity_curve"]
        self.assertGreater(len(curve), 0)
        self.assertEqual(curve[0]["benchmark"], 100.0)
        for point in curve[:5]:
            self.assertIn("date", point)
            self.assertIn("equity", point)
            self.assertIn("benchmark", point)

    def test_new_stats_present(self):
        stats = self.result["stats"]
        for key in (
            "sharpe_ratio", "profit_factor", "exposure_pct",
            "avg_hold_days", "buy_hold_return_pct",
        ):
            self.assertIn(key, stats)

    def test_buy_hold_matches_benchmark_end(self):
        curve = self.result["equity_curve"]
        expected = curve[-1]["benchmark"] - 100.0
        self.assertAlmostEqual(
            self.result["stats"]["buy_hold_return_pct"], expected, places=1
        )


class StatsMathTest(unittest.TestCase):
    def test_compute_stats_on_fixture(self):
        from tools.backtester import _compute_stats
        trades = [
            {"date_entry": "2024-01-01", "date_exit": "2024-01-11",
             "entry_price": 100.0, "exit_price": 110.0, "pnl_pct": 10.0},
            {"date_entry": "2024-02-01", "date_exit": "2024-02-06",
             "entry_price": 100.0, "exit_price": 95.0, "pnl_pct": -5.0},
        ]
        equity_curve = [
            {"date": "2024-01-01", "equity": 100.0, "benchmark": 100.0},
            {"date": "2024-01-11", "equity": 110.0, "benchmark": 105.0},
            {"date": "2024-02-06", "equity": 104.5, "benchmark": 102.0},
        ]
        stats = _compute_stats(
            trades=trades, equity_curve=equity_curve,
            final_equity=104.5, bars_long=10, n_signal_bars=20,
            buy_hold_return_pct=2.0,
        )
        self.assertEqual(stats["num_trades"], 2)
        self.assertEqual(stats["win_rate"], 0.5)
        self.assertAlmostEqual(stats["total_return_pct"], 4.5)
        self.assertAlmostEqual(stats["profit_factor"], 2.0)   # 10 / 5
        self.assertAlmostEqual(stats["exposure_pct"], 50.0)   # 10 / 20
        self.assertAlmostEqual(stats["avg_hold_days"], 7.5)   # (10 + 5) / 2
        self.assertAlmostEqual(stats["buy_hold_return_pct"], 2.0)

    def test_profit_factor_null_when_no_losses(self):
        from tools.backtester import _compute_stats
        trades = [{"date_entry": "2024-01-01", "date_exit": "2024-01-08",
                   "entry_price": 100.0, "exit_price": 108.0, "pnl_pct": 8.0}]
        stats = _compute_stats(
            trades=trades,
            equity_curve=[{"date": "2024-01-01", "equity": 100.0, "benchmark": 100.0},
                          {"date": "2024-01-08", "equity": 108.0, "benchmark": 101.0}],
            final_equity=108.0, bars_long=5, n_signal_bars=10,
            buy_hold_return_pct=1.0,
        )
        self.assertIsNone(stats["profit_factor"])

    def test_empty_trades_stats(self):
        from tools.backtester import _compute_stats
        stats = _compute_stats(
            trades=[], equity_curve=[], final_equity=100.0,
            bars_long=0, n_signal_bars=0, buy_hold_return_pct=0.0,
        )
        self.assertEqual(stats["num_trades"], 0)
        self.assertEqual(stats["win_rate"], 0.0)
        self.assertEqual(stats["sharpe_ratio"], 0.0)
        self.assertIsNone(stats["profit_factor"])

    def test_sharpe_and_drawdown_numeric(self):
        from tools.backtester import _compute_stats
        equity_curve = [
            {"date": "2024-01-01", "equity": 100.0, "benchmark": 100.0},
            {"date": "2024-01-02", "equity": 105.0, "benchmark": 101.0},
            {"date": "2024-01-03", "equity": 102.0, "benchmark": 102.0},
            {"date": "2024-01-04", "equity": 108.0, "benchmark": 103.0},
        ]
        stats = _compute_stats(
            trades=[], equity_curve=equity_curve, final_equity=108.0,
            bars_long=4, n_signal_bars=4, buy_hold_return_pct=3.0,
        )
        # Daily returns: +5%, -2.857%, +5.882% → mean/std × √252, rounded to 2dp
        rets = [0.05, -2.0 / 70.0, 6.0 / 102.0]
        import numpy as np
        expected_sharpe = round(float(np.mean(rets) / np.std(rets) * np.sqrt(252)), 2)
        self.assertAlmostEqual(stats["sharpe_ratio"], expected_sharpe, places=2)
        # Peak 105 → trough 102 = -2.857%
        self.assertAlmostEqual(stats["max_drawdown_pct"], -2.86, places=2)


class ShortHistoryTest(unittest.TestCase):
    def test_indicator_short_df_returns_empty_shape(self):
        from tools.backtester import run_backtest
        result = run_backtest(enriched(30), strategy="indicator")
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["stats"]["num_trades"], 0)
        self.assertEqual(result["strategy"], "indicator")

    def test_unknown_strategy_raises(self):
        from tools.backtester import run_backtest
        with self.assertRaises(ValueError):
            run_backtest(enriched(260), strategy="quantum")


class MLStrategyTest(unittest.TestCase):
    def test_insufficient_history_returns_error(self):
        from tools.backtester import ML_WARMUP, RETRAIN_EVERY, run_backtest
        n_short = ML_WARMUP + RETRAIN_EVERY - 1
        result = run_backtest(enriched(n_short), strategy="ml")
        self.assertIsNotNone(result["error"])
        self.assertIn("ML backtest", result["error"])
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["strategy"], "ml")

    def test_ml_backtest_runs_and_is_deterministic(self):
        from tools.backtester import run_backtest
        df = enriched(300)
        r1 = run_backtest(df, strategy="ml")
        r2 = run_backtest(df, strategy="ml")
        self.assertIsNone(r1["error"])
        self.assertEqual(r1["strategy"], "ml")
        self.assertIn("RandomForest", r1["strategy_description"])
        self.assertGreater(len(r1["equity_curve"]), 0)
        self.assertEqual(r1["trades"], r2["trades"])              # random_state=42
        self.assertEqual(r1["equity_curve"], r2["equity_curve"])

    def test_ml_signals_cover_all_post_warmup_bars(self):
        from tools.backtester import ML_WARMUP, _ml_signals
        df = enriched(300)
        signals = _ml_signals(df, ML_WARMUP)
        self.assertEqual(len(signals), len(df) - ML_WARMUP)
        self.assertTrue(set(signals) <= {"BUY", "SELL", "HOLD"})

    def test_single_class_window_emits_hold(self):
        from unittest.mock import patch

        from tools.backtester import ML_WARMUP, _ml_signals

        class OneClassModel:
            classes_ = [1]

            def fit(self, X, y):
                return self

            def predict_proba(self, X):  # pragma: no cover — must not be called
                raise AssertionError("predict_proba should not be called for one-class model")

        df = enriched(150)
        with patch("sklearn.ensemble.RandomForestClassifier", return_value=OneClassModel()):
            signals = _ml_signals(df, ML_WARMUP)
        self.assertTrue(all(s == "HOLD" for s in signals))


class AtrEmaHelpersTest(unittest.TestCase):
    """TDD tests for the v2 indicator helpers _atr and _ema."""

    def _df(self, highs, lows, closes):
        idx = pd.date_range("2025-01-01", periods=len(closes), freq="D")
        return pd.DataFrame({"High": highs, "Low": lows, "Close": closes}, index=idx)

    def test_atr_is_positive_and_aligned(self):
        from tools.backtester import _atr
        n = 30
        closes = list(np.linspace(100, 130, n))
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        atr = _atr(self._df(highs, lows, closes), period=14)
        self.assertEqual(len(atr), n)
        self.assertGreater(atr[20], 0)
        self.assertTrue(np.isfinite(atr[20]))

    def test_ema_tracks_level(self):
        from tools.backtester import _ema
        closes = np.array([10.0] * 50)
        ema = _ema(closes, 200)
        self.assertEqual(len(ema), 50)
        self.assertAlmostEqual(ema[-1], 10.0, places=6)


if __name__ == "__main__":
    unittest.main()


# ── Task 2: _simulate v2 state machine ───────────────────────────────────────
from tools.backtester import _simulate


def _const_atr(n, val=10.0):
    return np.array([val] * n, dtype=float)


def _sim_dates(n):
    return pd.date_range("2025-01-01", periods=n, freq="D").strftime("%Y-%m-%d").tolist()


def test_trend_filter_blocks_counter_trend_buy():
    closes = np.array([100.0, 100.0, 100.0])
    ema = np.array([110.0, 110.0, 110.0])      # price below trend
    out = _simulate(_sim_dates(3), closes, _const_atr(3), ema, ["HOLD", "BUY", "HOLD"])
    assert out["trades"] == []
    assert out["open_position"] is None


def test_stop_loss_exit():
    closes = np.array([100.0, 95.0, 79.0])     # stop = 100-2*10 = 80; 79 < 80
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_sim_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert len(out["trades"]) == 1
    assert out["trades"][0]["exit_reason"] == "stop"
    assert out["open_position"] is None


def test_take_profit_exit_hits_1to3():
    closes = np.array([100.0, 130.0, 160.0])   # target = 100 + 3*20 = 160
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_sim_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert len(out["trades"]) == 1
    t = out["trades"][0]
    assert t["exit_reason"] == "target"
    assert round(t["r_multiple"], 1) == 3.0


def test_trailing_stop_exit_locks_gain():
    closes = np.array([100.0, 150.0, 124.0])   # trail=150-2.5*10=125; 124<=125, >initial stop 80
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_sim_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert len(out["trades"]) == 1
    t = out["trades"][0]
    assert t["exit_reason"] == "trail"
    assert t["pnl_pct"] > 0


def test_sell_signal_exit():
    closes = np.array([100.0, 105.0, 108.0])   # between stop and target
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_sim_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "SELL"])
    assert len(out["trades"]) == 1
    assert out["trades"][0]["exit_reason"] == "signal"


def test_open_position_reported_when_ending_long():
    closes = np.array([100.0, 105.0, 108.0])
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_sim_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert out["trades"] == []
    op = out["open_position"]
    assert op is not None
    assert op["entry_price"] == 100.0
    assert op["current_price"] == 108.0
    assert round(op["unrealized_pnl_pct"], 1) == 8.0
    assert op["stop"] == 80.0 and op["target"] == 160.0


def test_position_sizing_scales_with_stop_distance():
    closes = np.array([100.0, 110.0])
    ema = np.array([90.0, 90.0])
    tight = _simulate(_sim_dates(2), closes, _const_atr(2, 2.5), ema, ["BUY", "SELL"])
    wide = _simulate(_sim_dates(2), closes, _const_atr(2, 25.0), ema, ["BUY", "SELL"])
    assert tight["equity_curve"][-1]["equity"] > wide["equity_curve"][-1]["equity"]


# ── Task 3: richer metrics in _compute_stats ─────────────────────────────────
from tools.backtester import _compute_stats as _compute_stats_v2


def test_richer_metrics_present_and_sane():
    trades = [
        {"date_entry": "2025-01-01", "date_exit": "2025-01-05", "pnl_pct": 5.0},
        {"date_entry": "2025-01-06", "date_exit": "2025-01-08", "pnl_pct": -2.0},
        {"date_entry": "2025-01-09", "date_exit": "2025-01-12", "pnl_pct": -1.0},
    ]
    curve = [{"date": f"2025-01-{d:02d}", "equity": e, "benchmark": 100.0}
             for d, e in zip(range(1, 7), [100, 102, 105, 103, 104, 108])]
    s = _compute_stats_v2(trades, curve, final_equity=108.0, bars_long=4,
                          n_signal_bars=6, buy_hold_return_pct=8.0)
    assert s["best_trade_pct"] == 5.0
    assert s["worst_trade_pct"] == -2.0
    assert s["max_consecutive_losses"] == 2
    assert "cagr_pct" in s and "sortino_ratio" in s and "calmar_ratio" in s
    assert s["cagr_pct"] > 0
