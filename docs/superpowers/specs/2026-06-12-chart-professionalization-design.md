# Chart Professionalization — Design Spec

**Date:** 2026-06-12
**Scope:** `frontend/src/components/trading-chart/` only. No backend changes, no new dependencies.
**Goal:** Close the visual and functional gap between TradeDash's chart and TradingView: famous indicators with real settings, volume, professional legends, panel polish, and persistence.

## Background (current behaviour)

- 11 indicators (EMA, Supertrend, RSI, MACD, Stochastic, ADX, BB, ATR, OBV, VWAP, Volume Profile) defined in `lib/indicators.ts` with numeric-only `defaultParams`/`paramLabels`.
- Settings UI (`IndicatorSearch.tsx`) renders bare number inputs; colors are hardcoded in `ChartCore.tsx` (`emaColor()`, per-indicator literals) and `SubChartPane.tsx` (`COLORS`).
- No volume histogram. OHLC tooltip is empty until hover. Overlay labels are plain grey text with no values or controls.
- RSI/Stochastic levels are hardcoded price lines with `title` + `axisLabelVisible: true`, producing duplicate axis badges (the "70 / 70.00" collision).
- Nothing persists — `useIndicators` is plain `useState`.
- Every pane renders its own TradingView watermark logo (two+ logos on screen).

---

## 1. Settings model (foundation)

### Field schema

`lib/types.ts` and `lib/indicators.ts` move from `defaultParams: Record<string, number>` to a typed schema:

```ts
type Source = 'close' | 'open' | 'high' | 'low' | 'hl2' | 'hlc3' | 'ohlc4'

type FieldDef =
  | { kind: 'int' | 'float'; key: string; label: string; default: number; min: number; max: number; step?: number }
  | { kind: 'level';         key: string; label: string; default: number; min: number; max: number }  // dashed reference line in panel
  | { kind: 'source';        key: string; label: string; default: Source }
  | { kind: 'color';         key: string; label: string; default: string }   // one per rendered line
  | { kind: 'width';         key: string; label: string; default: 1 | 2 | 3 }

interface IndicatorDef {
  id: IndicatorId
  name: string
  category: IndicatorCategory
  type: 'overlay' | 'panel'
  fields: FieldDef[]
}
```

### Active-indicator state

```ts
interface ActiveIndicator {
  instanceId: string                            // `${id}-${input values joined}` — inputs only
  indicatorId: IndicatorId
  inputs: Record<string, number | Source>       // int/float/level/source fields → recompute on change
  style: Record<string, string | number>        // color/width fields → applyOptions on change, NO recompute
  hidden: boolean                               // legend eye toggle → series.applyOptions({ visible })
}
```

Key rule: **`instanceId` derives from `inputs` only.** Changing a color or width must not recreate the instance (today `updateParams` regenerates the id for any change). `useIndicators` exposes `updateInputs`, `updateStyle`, `toggleHidden` instead of one `updateParams`.

Current hardcoded colors become the schema defaults (e.g. EMA default color stays period-keyed via `emaColor()` used as the default when adding; BB keeps `#42a5f5`/`#78909c`; MACD keeps `#2962ff`/`#ff6d00` + histogram green/red pair).

### Settings panel

`IndicatorSearch.tsx`'s inline settings panel renders generically from `fields`:
- `int`/`float`/`level` → number input with min/max clamping on Apply.
- `source` → `<select>` with the seven sources.
- `color` → native `<input type="color">` plus a 8-swatch preset row (the palette already in use: `#f7c948 #2196f3 #26c6da #ff7043 #e040fb #26a69a #ef5350 #ff6d00`).
- `width` → three-button segmented control (1px/2px/3px).
Apply submits inputs (recompute) and style (live) separately so color tweaks feel instant.

### Persistence

`useIndicators` hydrates from `localStorage["tradedash.chart.v2"]` and writes on every change:

```ts
{ version: 2, volumeVisible: boolean, indicators: Array<{ indicatorId, inputs, style, hidden }> }
```

Hydration validation: drop entries whose `indicatorId` isn't in `INDICATOR_MAP`; for each field, fall back to the schema default when the stored value is missing, wrong-typed, or out of min/max range; cap panel indicators at `MAX_PANEL_INDICATORS`; wrap `JSON.parse` so corrupt data resets to defaults silently. Settings are global (apply to every ticker), like TradingView's layout memory.

---

## 2. New indicators: SMA, WMA, HMA

Added to `lib/computeIndicators.ts` and the registry (category TREND, type overlay):

| Indicator | Defaults | Fields |
|---|---|---|
| SMA | period 20, source close | period (int 1–500), source, color, width |
| WMA | period 20, source close | period (int 1–500), source, color, width |
| HMA | period 9, source close | period (int 2–500), source, color, width |

HMA = `WMA(2·WMA(src, n/2) − WMA(src, n), floor(√n))` (round n/2 down, standard Hull formula).

### Source support

New helper `sourceValues(candles, source): number[]` (hl2 = (H+L)/2, hlc3 = (H+L+C)/3, ohlc4 = (O+H+L+C)/4). Source-aware indicators: **SMA, EMA, WMA, HMA, RSI, BB, MACD** (matching TradingView). The compute functions for EMA/RSI/BB/MACD gain an optional trailing `source: Source = 'close'` parameter — existing call sites and tests remain valid. Supertrend, ADX, ATR, Stochastic, OBV, VWAP, Volume Profile are inherently H/L/C/V-based and get no source field.

---

## 3. Volume histogram (built-in, not a registry indicator)

In `ChartCore.tsx`: a `HistogramSeries` on its own price scale (`priceScaleId: 'volume'`, `scaleMargins: { top: 0.8, bottom: 0 }`), colored by candle direction at 50 % opacity (`#26a69a80` / `#ef535080`), `lastValueVisible: false`, `priceLineVisible: false`. Volume is a built-in with its own legend row ("Vol 1.52M", value formatted K/M/Cr) and eye toggle; its visibility is part of the persisted state (`volumeVisible`, default true). It does not count against the panel limit and does not appear in the indicator search list.

---

## 4. Legends

### `ChartLegend.tsx` (new component, rendered inside ChartCore's overlay layer)

- **OHLC row:** colored `O H L C` labels + absolute and % change, **initialized to the last candle** (not blank), updates on crosshair move via DOM refs (same perf pattern as the existing tooltip). Fixes the cramped spacing in the current implementation.
- **Volume row:** "Vol" + formatted value (last bar / hovered bar), eye toggle.
- **One row per overlay instance:** `{NAME} {key inputs} {source if not close}` + live value(s) rendered in the line's color (multi-line indicators show each line's value in its own color, e.g. BB upper/mid/lower). On row hover, three icon buttons appear: 👁 eye (toggle `hidden`), ⚙ gear (opens IndicatorSearch with this instance's settings expanded), ✕ (remove). Rows are pointer-enabled; the rest of the legend layer stays `pointer-events-none`.
- Hidden instances render the row at 40 % opacity with values omitted.

`ChartCore` keeps a map `instanceId → ISeriesApi[]` so the eye toggle and style changes call `series.applyOptions(...)` without rebuilding the chart. (The current implementation rebuilds the whole chart when indicators change; that behaviour stays for **input** changes only.)

### Panel headers (`SubChartPane.tsx`)

Header becomes: name + inputs + live colored value readout(s) (crosshair-following), plus the same eye/gear/✕ buttons. The gear callback routes to the same IndicatorSearch-open-with-settings flow.

---

## 5. Panel polish

- **Overbought/oversold band:** RSI gets `overbought` (default 70, level field) and `oversold` (default 30); Stochastic gets 80/20. The band between the two levels is filled with a translucent tint using a `BaselineSeries`: constant data at the overbought level, `baseValue: { type: 'price', price: oversold }`, top fill ~10 % alpha of the indicator color, line invisible, not on the autoscale (`autoscaleInfoProvider` returning null so it never distorts the scale).
- **Label collision fix:** level price lines keep the dashed line but set `axisLabelVisible: false` and no `title` (the band + scale ticks make the level obvious; the series' own `lastValueVisible` badge remains the single axis label). ADX keeps its 25 line, same fix.
- Level lines re-read from `inputs`, so editing 70→80 moves both the line and the band.

---

## 6. Chrome cleanup

- `attributionLogo: false` in every `createChart` layout (main + panels). A single footer line in `RangeSelector`'s row, right-aligned: "Powered by [TradingView Lightweight Charts](https://www.tradingview.com/lightweight-charts/)" — keeps the project license-compliant with one attribution instead of N logos.
- Main chart `localization.priceFormatter`: `₹` + `toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })`. Panels keep plain numeric formatting (RSI 70.00, OBV in K/M/Cr via custom formatter).
- Container stays `#131722`; the wrapper in `index.tsx` aligns with app cards: `rounded-2xl border border-border` (replacing the one-off `rounded-lg border-[#2a2e39]`).

---

## 7. Error handling

- Hydration: corrupt/foreign localStorage → silent reset to defaults (no crash, no alert).
- Compute functions keep their existing "too few candles → empty result" contracts; legends show "—" for missing values.
- Unknown stored field keys are ignored; missing keys fall back to schema defaults (forward/backward compatible across future schema additions).

## 8. Testing

- **`computeIndicators.test.ts`** (existing file, existing style): SMA/WMA/HMA against hand-computed fixtures (e.g. SMA(3) of [1..5] = [2,3,4]; WMA(3) of [1..5] = [2.33…, 3.33…, 4.33…]; HMA known sequence); `sourceValues` for all seven sources; EMA/RSI with `source: 'hl2'` differs from `'close'` on an asymmetric fixture; all existing tests pass unchanged.
- **`useIndicators` tests (new):** add → persist → re-mount hydrates identical state; corrupt JSON resets; unknown indicator dropped; out-of-range input clamped to default; `updateStyle` preserves `instanceId`; `updateInputs` regenerates it; panel cap enforced on hydrate.
- **`ChartLegend` tests (new, Testing Library):** renders OHLC from last candle; renders a row per overlay with formatted inputs; eye click calls `toggleHidden`; ✕ calls remove; hidden row dims.
- Chart rendering itself (lightweight-charts canvas) stays manually verified — no canvas snapshot tests.

## Out of scope

- New panel indicators (CCI, MFI, Ichimoku, etc.) — the schema makes them cheap later.
- Drawing tools, alerts, replay, symbol compare, layouts per ticker.
- Countdown-to-candle-close and session clock.
- Mobile-specific chart toolbar redesign.

## Rollout

Single feature branch `feature/chart-professionalization` → PR → merge → delete branch. Update `README.md` chart section.
