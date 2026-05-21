# Options Page Redesign — Design Spec
**Date:** 2026-04-18  
**Status:** Approved

## Problem

The options page currently has four concrete issues visible in production:

1. **Cold empty state** — when the Render backend is cold-starting, all three cards simultaneously show "Data unavailable" with no explanation or retry affordance.
2. **Confusing header** — the spot price falls back to a lone "—" in the flex row when data hasn't loaded, making the header look broken.
3. **Wasted 3-col grid** — the third column (PCRCard) shows PCR + Max Pain in a large card; this information is important but doesn't deserve a full equal-weight column alongside the actual trade recommendations.
4. **Thin trade cards** — the current TradeCard already surfaces most data but buries confidence and risk:reward ratio.

## Chosen Design: Layout A + Rich Cards (Y)

### Layout changes (`options/[symbol]/page.tsx`)

**Header row** (unchanged structure, fixed rendering):
- Symbol switcher pills | divider | spot price (mono) + signal badge | `ml-auto` DataFreshness + Refresh icon
- Spot shows a `Skeleton` while loading; shows "—" only when not loading AND data is null (already correct, no change needed)
- DataFreshness already returns `null` when `updatedAt` is falsy — confirmed in component code

**Offline/error banner** (new — conditional):
- Rendered only when `recError === true`
- Content: amber/red strip — "⚡ Backend is cold-starting (~30s on free tier)" + `[↺ Retry]` button
- Retry calls `refetch()` on both `useOptionsChain` and `useOptionsRecommend`
- Placed immediately below the header row, above the expiry picker

**Expiry picker** — no change

**Stats strip** (new component: `StatsStrip`):
- Replaces the PCR card's position; rendered as a horizontal row of 5 chips
- Chips: `PCR` (colored green/red/amber by value) | `Max Pain` | `Sentiment` | `Call OI` | `Put OI`
- Source: `recData.pcr`, `recData.max_pain`, `recData.pcr.signal`, computed from chain OI sums
- Shows skeleton chips while loading; hidden entirely on error (banner already tells the story)

**Recommendations grid** — 2 columns (was 3):
- `<TradeCard style="intraday" />` | `<TradeCard style="positional" />`
- PCRCard removed from this row

**Tabs** (OI Tornado | Options Chain | Payoff Diagram) — no change

---

### Enhanced TradeCard (`components/options/TradeCard.tsx`)

Add to the existing card (all data already available in `rec` and `data`):

1. **Confidence badge** — top-right of card header: `data.confidence` as a `%` number, colored by value (≥60 green, 40–59 amber, <40 red)
2. **Risk:Reward visual bar** — below the SL/Target/Premium 3-col grid:
   - Label: `Risk:Reward · 1:X` where X = `rec.target_pct / rec.sl_pct` rounded to 1dp
   - Two stacked thin bars: red bar width = `sl_pct / (sl_pct + target_pct) * 100%`, green bar = remainder
3. No other structural changes — existing Premium / SL% / Target% / Capital / Max P&L / IV / OI rows stay

---

### New `StatsStrip` component (`components/options/StatsStrip.tsx`)

```
Props: { data: RecommendResponse }

Renders a flex row of chips:
  PCR: data.pcr.pcr  →  green if >1.2, red if <0.8, amber otherwise
  Max Pain: data.max_pain  →  shows ₹ formatted value
  Sentiment: data.pcr.signal  →  text, colored same as PCR
  Call OI / Put OI: summed from chain data (passed as optional prop)
```

StatsStrip is only rendered when `recData` is present (not loading, not error).

---

### PCRCard component

Keep the file — don't delete it. Just stop importing/using it in the page. It may be repurposed later.

---

## Files to change

| File | Change |
|------|--------|
| `frontend/src/app/dashboard/options/[symbol]/page.tsx` | Wire StatsStrip, 2-col grid, offline banner, remove PCRCard import |
| `frontend/src/components/options/TradeCard.tsx` | Add confidence badge + risk:reward bar |
| `frontend/src/components/options/StatsStrip.tsx` | **New file** — 5-chip horizontal stats strip |

## Files NOT changed

- `PCRCard.tsx` — kept, just not used in page
- `OITornadoChart.tsx`, `OptionsChainTable.tsx`, `PayoffChart.tsx` — no change
- Backend — no change

## Verification

1. `npx tsc --noEmit` passes with zero errors
2. Load `/dashboard/options/NIFTY` while backend is online → stats strip shows PCR/Max Pain, 2 trade cards side-by-side with confidence % and risk:reward bar, no PCR card
3. Kill backend / wait for cold start → offline banner appears with Retry; clicking Retry re-fetches both queries
4. DataFreshness shows correctly once data loads; no stray "—" in header
