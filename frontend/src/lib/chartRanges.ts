// Interval + period combos mirror backend VALID_COMBOS (tools/fetch_stock_data.py).
// Keep them in sync — the backend will 404 on invalid combos.

export const INTERVALS = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"] as const;
export type Interval = (typeof INTERVALS)[number];

export const PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"] as const;
export type Period = (typeof PERIODS)[number];

export const INTERVAL_LABELS: Record<Interval, string> = {
  "1m": "1 min",
  "5m": "5 min",
  "15m": "15 min",
  "30m": "30 min",
  "1h": "1 hour",
  "1d": "1 day",
  "1wk": "1 week",
  "1mo": "1 month",
};

export const PERIOD_LABELS: Record<Period, string> = {
  "1d": "1D",
  "5d": "5D",
  "1mo": "1M",
  "3mo": "3M",
  "6mo": "6M",
  "1y": "1Y",
  "2y": "2Y",
  "5y": "5Y",
  "10y": "10Y",
  "max": "MAX",
};

export const VALID_COMBOS: Record<Interval, Period[]> = {
  "1m": ["1d", "5d"],
  "5m": ["1d", "5d", "1mo"],
  "15m": ["1d", "5d", "1mo", "3mo"],
  "30m": ["1d", "5d", "1mo", "3mo"],
  "1h": ["1d", "5d", "1mo", "3mo", "6mo"],
  "1d": ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
  "1wk": ["3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
  "1mo": ["1y", "2y", "5y", "10y", "max"],
};

export const INTRADAY = new Set<Interval>(["1m", "5m", "15m", "30m", "1h"]);

/** Coerce an arbitrary period to one that's valid for the given interval. */
export function coercePeriod(interval: Interval, period: Period): Period {
  const valid = VALID_COMBOS[interval];
  if (valid.includes(period)) return period;
  // Pick the longest valid period (usually the most informative default).
  return valid[valid.length - 1];
}
