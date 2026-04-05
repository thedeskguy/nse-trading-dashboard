"""
ML price direction predictor.
Trains a Random Forest on technical indicator features derived from
the existing compute_all() DataFrame and predicts next-day direction.

No paid APIs. Only scikit-learn (free, open-source).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


FEATURE_COLS = [
    "rsi",
    "macd_hist",
    "bb_pct",
    "ema9_dist",
    "ema21_dist",
    "ema50_dist",
    "ema200_dist",
    "atr_pct",
    "vol_change",
    "ret_1d",
    "ret_5d",
    "obv_slope",
]


def _obv_slope_series(obv: pd.Series, window: int = 10) -> pd.Series:
    """Rolling linear-regression slope of OBV over `window` bars."""
    slopes = [np.nan] * len(obv)
    obv_vals = obv.values
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    for i in range(window - 1, len(obv_vals)):
        y = obv_vals[i - window + 1 : i + 1].astype(float)
        if np.isnan(y).any():
            continue
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        # Normalise by mean OBV so slope is scale-independent
        ref = abs(y_mean) if y_mean != 0 else 1.0
        slopes[i] = slope / ref
    return pd.Series(slopes, index=obv.index)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer ML features from an indicator-enriched DataFrame
    (output of compute_all()).  Returns a new DataFrame with
    FEATURE_COLS columns plus a binary 'target' column
    (1 = next day close > today close, 0 = down or flat).
    """
    feat = pd.DataFrame(index=df.index)

    # ── Raw indicators ────────────────────────────────────────────────────────
    feat["rsi"]       = df.get("RSI_14")
    feat["macd_hist"] = df.get("MACD_hist")
    feat["bb_pct"]    = df.get("BB_pct")

    # ── EMA distances (normalised to price) ───────────────────────────────────
    close = df["Close"]
    for col, key in [
        ("ema9_dist",   "EMA_9"),
        ("ema21_dist",  "EMA_21"),
        ("ema50_dist",  "EMA_50"),
        ("ema200_dist", "EMA_200"),
    ]:
        ema = df.get(key)
        if ema is not None:
            feat[col] = (close - ema) / close.replace(0, np.nan)
        else:
            feat[col] = np.nan

    # ── ATR as % of price ─────────────────────────────────────────────────────
    atr = df.get("ATR_14")
    feat["atr_pct"] = (atr / close.replace(0, np.nan)) if atr is not None else np.nan

    # ── Volume change vs 10-day average ──────────────────────────────────────
    vol = df["Volume"]
    vol_ma = vol.rolling(10).mean()
    feat["vol_change"] = (vol / vol_ma.replace(0, np.nan)) - 1

    # ── Price returns ─────────────────────────────────────────────────────────
    feat["ret_1d"] = close.pct_change(1)
    feat["ret_5d"] = close.pct_change(5)

    # ── OBV slope ─────────────────────────────────────────────────────────────
    obv = df.get("OBV")
    feat["obv_slope"] = _obv_slope_series(obv) if obv is not None else np.nan

    # ── Target: 1 if next-day close is higher ────────────────────────────────
    feat["target"] = (close.shift(-1) > close).astype(int)

    return feat


def train_and_predict(df: pd.DataFrame) -> dict:
    """
    Train a RandomForest on the full historical DataFrame and return
    a prediction for the *latest* bar (next-day direction).

    Requires the DataFrame to have been produced by compute_all()
    on daily interval with at least 120 rows (preferably 500+).

    Returns:
        {
            "direction":          "UP" | "DOWN",
            "probability":        float,       # P(UP), 0–1
            "accuracy":           float,       # test-set accuracy, 0–1
            "feature_importance": dict,        # feature → importance
            "train_samples":      int,
            "test_samples":       int,
            "error":              str | None,  # set only on failure
        }
    """
    # ── Build features ────────────────────────────────────────────────────────
    feat = build_features(df)

    # Drop the last row from training (target is unknown — it's tomorrow)
    train_feat = feat.iloc[:-1].copy()
    predict_row = feat.iloc[[-1]].copy()

    # Drop rows with any NaN in features or target
    train_feat = train_feat.dropna(subset=FEATURE_COLS + ["target"])

    if len(train_feat) < 60:
        return {
            "direction": None,
            "probability": None,
            "accuracy": None,
            "feature_importance": {},
            "train_samples": 0,
            "test_samples": 0,
            "error": f"Not enough clean training rows ({len(train_feat)}). Need ≥ 60. Use daily interval with period ≥ 6mo.",
        }

    X = train_feat[FEATURE_COLS].values
    y = train_feat["target"].values.astype(int)

    # ── Time-ordered 80/20 split (no shuffle — avoids leakage) ───────────────
    split = int(len(X) * 0.80)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # ── Train ─────────────────────────────────────────────────────────────────
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))

    # ── Predict latest bar ────────────────────────────────────────────────────
    pred_X = predict_row[FEATURE_COLS].values.copy()
    # Fill any NaN in prediction row with column means from training set
    col_means = train_feat[FEATURE_COLS].mean().values
    nan_mask = np.isnan(pred_X[0])
    pred_X[0][nan_mask] = col_means[nan_mask]

    prob_up = float(model.predict_proba(pred_X)[0][1])
    direction = "UP" if prob_up >= 0.5 else "DOWN"
    probability = prob_up if direction == "UP" else (1 - prob_up)

    # ── Feature importance ────────────────────────────────────────────────────
    importance = {
        col: round(float(imp), 4)
        for col, imp in zip(FEATURE_COLS, model.feature_importances_)
    }

    return {
        "direction":          direction,
        "probability":        round(probability, 3),
        "accuracy":           round(accuracy, 3),
        "feature_importance": importance,
        "train_samples":      len(X_train),
        "test_samples":       len(X_test),
        "error":              None,
    }
