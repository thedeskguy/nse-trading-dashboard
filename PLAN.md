# Project Roadmap — NSE Trading Dashboard (Next.js SaaS)

## Status Legend
- `[x]` Done
- `[~]` In progress / stuck
- `[ ]` Not started

---

## Phase 0–2: Foundation ✅
- [x] Project scaffold (Next.js 16 + Tailwind v4)
- [x] Supabase project setup
- [x] Basic routing and page structure (`/login`, `/signup`, `/dashboard`, `/auth`)

---

## Phase 3: Real Supabase Auth `[x]` ✅
- [x] Login page wired to Supabase (`email + password`)
- [x] Signup page wired to Supabase
- [x] Google OAuth flow
- [x] Session nonce / PKCE handling (`/auth/callback` route)
- [x] Redirect after login → `/dashboard` (honours `?next=` param)
- [x] Auth guard on protected routes (middleware + dashboard layout server check)

> **Supabase project URL:** `https://ufjbjzobbndahlzhrxk.supabase.co`

---

## Phase 4: Stock Analysis Dashboard `[x]` ✅
- [x] Candlestick price chart (lightweight-charts v5)
- [x] Signal card (BUY / HOLD / SELL + confidence %)
- [x] Fundamentals panel (PE, ROE, D/E, growth)
- [x] ML prediction signal
- [x] Live index overview on dashboard home (NIFTY/BANKNIFTY/SENSEX)
- [x] TopBar search wired to navigate to stock analysis page

---

## Phase 5: Options Dashboard `[x]` ✅
- [x] Options chain table (CE/PE columns, ATM highlighted, OI/LTP/IV/Volume)
- [x] PCR card (put-call ratio + sentiment signal + max pain)
- [x] OI Tornado chart (Recharts horizontal bar, CE left / PE right, ATM highlighted)
- [x] Trade recommendations (intraday + positional, strike/expiry/SL/target/capital)
- [x] Symbol switcher (NIFTY / BANKNIFTY / MIDCPNIFTY)
- [x] Expiry picker with 1-min auto-refresh

---

## Phase 6: Payments + Subscription Gate `[x]` ✅
- [x] Razorpay checkout integration (UpgradeModal with monthly/annual plan picker)
- [x] Subscription plans (free tier / pro — monthly ₹499, annual ₹3,999)
- [x] Paywall enforcement on Options Dashboard (PaywallGate component)
- [x] Settings page shows live plan status + renewal date + upgrade CTA
- [x] Backend `GET /payments/subscription-status` endpoint
- [x] Razorpay webhook processes `subscription.activated/charged/cancelled`
- [x] Supabase `subscriptions` table migration (`docs/migrations/001_subscriptions.sql`)

---

## Phase 7: Single-Session Enforcement `[x]` ✅
- [x] Detect concurrent sessions (Supabase Realtime subscription on `user_sessions`)
- [x] Force logout of older session on new login (SessionWatcher signs out + redirects to `/login?reason=signed-in-elsewhere`)
- [x] Verification flow (amber banner shown on login page after kick)
- [x] Supabase `user_sessions` table migration (`docs/migrations/002_user_sessions.sql`)

---

## Phase 8: Scanner Page `[x]` ✅
- [x] Nifty 50 batch signal scan (GET /api/v1/market/scan, asyncio parallel, 10-min cache)
- [x] Table of all 50 stocks with signal + confidence bar + day change %
- [x] Filter by signal type (ALL / BUY / HOLD / SELL with counts)
- [x] Sortable columns (Company, Price, Day %, Confidence)
- [x] Click-through to individual stock page

---

## Phase 9: Polish + Lighthouse `[x]` ✅
- [x] Performance audit (Lighthouse score ≥ 90 — 96 accessibility, 100 best practices, 100 SEO)
- [x] Accessibility fixes (contrast: text-primary → text-blue-400, text-white/40 → text-white/60)
- [x] Mobile responsiveness pass (MobileNav bottom bar, responsive padding, scanner overflow-x-auto)
- [x] Loading states + error boundaries (/dashboard/error.tsx App Router boundary)

---

## Phase 10: Production Deploy `[x]` ✅
- [x] Backend on Render (free tier, auto-deploys from main)
- [x] Frontend on Vercel (free tier, auto-deploys from main)
- [x] Environment variables configured
- [x] Domain + SSL (Render: nse-trading-dashboard.onrender.com, Vercel: nse-trading-dashboard.vercel.app)

---

## Phase 11: Engineering Audit Backlog `[ ]`

Captured from a full-stack audit (2026-04-17). Tackle in priority order whenever picking this up — P0s are blockers for a real prod launch, P1s will bite once traffic grows, P2s are polish.

### P0 — security / correctness blockers
- [ ] **Gate the unverified-JWT fallback in `backend/deps.py`.** Currently `_decode_unverified()` is used silently when `SUPABASE_URL` is unset or JWKS fetch fails. Require an explicit `ALLOW_UNVERIFIED_JWT=1` env var and refuse to start otherwise, so a misconfigured Railway deploy can't auth any well-formed token.
- [ ] **Audit secrets in git history.** Run `git log --all -- .env backend/.env` and confirm no Angel MPIN, Razorpay secret, or Supabase service role was ever committed. Rotate anything that shows up.
- [ ] **Move cache off process-local `dict`.** `backend/services/cache.py` is in-memory and unbounded. On Railway with >1 replica (or after a restart) every replica re-hammers Angel One and re-runs TOTP login. Swap to Redis (Railway 1-click) or at least add an LRU cap + disk-backed cache for the Angel instrument master.

### P1 — architectural gaps that will bite soon
- [ ] **Add rate limiting on backend endpoints.** No `slowapi` or custom limiter anywhere. Prioritize `/api/v1/analysis/ml-predict` (trains a RandomForest on cache miss), `/api/v1/options/chain`, `/api/v1/market/ohlcv` — all fan out to Angel One and can DoS our own upstream.
- [ ] **Wire Sentry + structured logging.** Zero observability today; `except Exception: raise HTTPException(503)` swallows detail in every router. Add Sentry in `backend/main.py` lifespan and a JSON logger.
- [ ] **Validate `symbol` / `ticker` params.** Routers pass raw `Query(...)` strings to yfinance, screener, Angel. Add `StringConstraints(pattern=r"^[A-Z0-9._-]{1,25}$")` on every ticker query param.
- [ ] **Verify CORS config.** `backend/main.py` uses `allow_credentials=True`. Confirm `settings.CORS_ORIGINS` in prod is the exact Vercel domains — never `*`.
- [ ] **Make the app market-hours aware.** Nothing checks IST / NSE session times; the frontend polls Angel at 3 a.m. IST burning the daily session. Add `is_market_open()` and lengthen react-query `staleTime` when closed.
- [ ] **Razorpay webhook idempotency.** HMAC is verified, but there's no replay check. Store processed `event.id` in Supabase with a unique constraint.
- [ ] **Persist historical OHLCV.** `/analysis/ml-predict` re-downloads and re-trains on every cache miss. Add a `price_history` table + nightly backfill.
- [x] **Decide Streamlit layer's fate.** Kept as internal dev tool only — not public-facing. `dashboard.py` / `pages/` remain for local signal/data testing without needing auth. Next.js SaaS is the product.
- [x] **Decide if backend JWT verification should consult `user_sessions`.** Client-side kick (Phase 7) is sufficient. Server-side enforcement would add a DB query to every API request for a marginal gain (1-hour JWT expiry window). Left as-is.

### P2 — nice-to-haves
- [x] Add `backend/tests/` with FastAPI `TestClient` router tests (10 tests: health, market status, input validation, auth guard, payments, webhook).
- [x] Add `mypy` to CI for the payments codebase (`mypy routers/payments.py --ignore-missing-imports`).
- [x] Show "data from N minutes ago" staleness indicators in the dashboard UI (`DataFreshness` component on scanner, options, stock pages).
- [x] Drop unused Alpha Vantage slot in `backend/config.py` — was never added; confirmed absent.
- [x] **Free beta launch**: PaywallGate bypassed (pass-through), settings page updated, landing page pricing replaced with free beta card.
- [x] WebSocket live quotes (`/api/v1/ws/quote/{ticker}` + `useWebSocketQuote` hook). WS price supersedes cached signal price on stock pages. Angel One token-based feed deferred to v2 (requires instrument master mapping).
- [x] Document (or refactor) the `threading.Lock` in `backend/services/angel_session.py` — lock is correct (called via `asyncio.to_thread`); explanation comment added.
- [x] Verify Vercel prod sets `NEXT_PUBLIC_API_URL` — added console.warn in `client.ts` when localhost is used in production; `.env.example` updated with Render URL hint.
- [x] Add a circuit-breaker around yfinance for 429 storms (`backend/services/circuit_breaker.py`, wired into `tools/fetch_stock_data._fetch_yfinance`).

### Open questions (answer before starting the P0/P1 work)
1. Is `SUPABASE_URL` set in Railway prod? Decides whether the deps.py fallback is live right now.
2. Angel One plan — free tier only, or paid? Sets the urgency on Redis.
3. How many Railway replicas run the backend? If >1, cache fan-out is already happening.
4. Is Sentry already provisioned (DSN waiting), or do we need a new account?
5. Streamlit roadmap — deprecate, keep as internal tool, or productize separately?
6. Should backend JWT verification block revoked sessions via `user_sessions`, or is Phase 7's client-side kick enough?

---

## Phase 11: Engineering Audit Backlog `[ ]`

Captured from a full-stack audit (2026-04-17). Tackle in priority order whenever picking this up — P0s are blockers for a real prod launch, P1s will bite once traffic grows, P2s are polish.

### P0 — security / correctness blockers
- [ ] **Gate the unverified-JWT fallback in `backend/deps.py`.** Currently `_decode_unverified()` is used silently when `SUPABASE_URL` is unset or JWKS fetch fails. Require an explicit `ALLOW_UNVERIFIED_JWT=1` env var and refuse to start otherwise, so a misconfigured Railway deploy can't auth any well-formed token.
- [ ] **Audit secrets in git history.** Run `git log --all -- .env backend/.env` and confirm no Angel MPIN, Razorpay secret, or Supabase service role was ever committed. Rotate anything that shows up.
- [ ] **Move cache off process-local `dict`.** `backend/services/cache.py` is in-memory and unbounded. On Railway with >1 replica (or after a restart) every replica re-hammers Angel One and re-runs TOTP login. Swap to Redis (Railway 1-click) or at least add an LRU cap + disk-backed cache for the Angel instrument master.

### P1 — architectural gaps that will bite soon
- [ ] **Add rate limiting on backend endpoints.** No `slowapi` or custom limiter anywhere. Prioritize `/api/v1/analysis/ml-predict` (trains a RandomForest on cache miss), `/api/v1/options/chain`, `/api/v1/market/ohlcv` — all fan out to Angel One and can DoS our own upstream.
- [ ] **Wire Sentry + structured logging.** Zero observability today; `except Exception: raise HTTPException(503)` swallows detail in every router. Add Sentry in `backend/main.py` lifespan and a JSON logger.
- [ ] **Validate `symbol` / `ticker` params.** Routers pass raw `Query(...)` strings to yfinance, screener, Angel. Add `StringConstraints(pattern=r"^[A-Z0-9._-]{1,25}$")` on every ticker query param.
- [ ] **Verify CORS config.** `backend/main.py` uses `allow_credentials=True`. Confirm `settings.CORS_ORIGINS` in prod is the exact Vercel domains — never `*`.
- [ ] **Make the app market-hours aware.** Nothing checks IST / NSE session times; the frontend polls Angel at 3 a.m. IST burning the daily session. Add `is_market_open()` and lengthen react-query `staleTime` when closed.
- [ ] **Razorpay webhook idempotency.** HMAC is verified, but there's no replay check. Store processed `event.id` in Supabase with a unique constraint.
- [ ] **Persist historical OHLCV.** `/analysis/ml-predict` re-downloads and re-trains on every cache miss. Add a `price_history` table + nightly backfill.
- [ ] **Decide Streamlit layer's fate.** Root `dashboard.py` / `pages/` and `backend/routers/` both consume `tools/`. Document in PLAN whether Streamlit is a dev harness, internal tool, or parallel product — otherwise logic will drift.
- [ ] **Decide if backend JWT verification should consult `user_sessions`.** Currently a revoked tab can still hit the API until the JWT expires; Phase 7 only enforces single-session on the client.

### P2 — nice-to-haves
- [ ] Add `backend/tests/` with FastAPI `TestClient` router tests (CI runs `pytest` but the dir doesn't exist).
- [ ] Add `mypy` to CI for the payments codebase.
- [ ] WebSocket live quotes via Angel One's feed (replace polling).
- [ ] Show "data from N minutes ago" staleness indicators in the dashboard UI.
- [ ] Document (or refactor) the `threading.Lock` in `backend/services/angel_session.py` inside an async app.
- [ ] Verify Vercel prod sets `NEXT_PUBLIC_API_URL` — default is `http://localhost:8000`.
- [ ] Drop unused Alpha Vantage slot in `backend/config.py`.
- [ ] Add a circuit-breaker around yfinance for 429 storms.

### Open questions (answer before starting the P0/P1 work)
1. Is `SUPABASE_URL` set in Railway prod? Decides whether the deps.py fallback is live right now.
2. Angel One plan — free tier only, or paid? Sets the urgency on Redis.
3. How many Railway replicas run the backend? If >1, cache fan-out is already happening.
4. Is Sentry already provisioned (DSN waiting), or do we need a new account?
5. Streamlit roadmap — deprecate, keep as internal tool, or productize separately?
6. Should backend JWT verification block revoked sessions via `user_sessions`, or is Phase 7's client-side kick enough?

---

---

## Phase 12: Expanded Scanner — Nifty 100 / 200 / 500 `[ ]`
- [ ] Backend: Add stock lists for Nifty 100, 200, 500 (NSE CSV or hardcoded lists in `backend/routers/market.py`)
- [ ] Backend: `GET /api/v1/market/scan?index=NIFTY50|NIFTY100|NIFTY200|NIFTY500` — same parallel asyncio pattern as existing scan, 10-min cache per index
- [ ] Frontend: Index selector pills (NIFTY 50 / 100 / 200 / 500) above scanner table in `frontend/src/app/dashboard/scanner/page.tsx`
- [ ] Frontend: Pass selected index as query param to `useScanner(index)` hook

---

## Phase 13: Multi-timeframe Confluence `[ ]`
- [ ] Backend: Add `timeframe` param to `/api/v1/analysis/signal?ticker=X&timeframe=1d|1wk|1mo` — yfinance already supports these intervals
- [ ] Backend: New endpoint `GET /api/v1/analysis/confluence?ticker=X` returns signal for all 3 timeframes in one response
- [ ] Frontend: `ConfluenceGrid` component — 3×6 heatmap (rows: 1D / 1W / 1M, cols: RSI / MACD / BB / EMA / Volume / Stoch), cell color = buy/hold/sell
- [ ] Frontend: Add confluence tab to stock detail page (`frontend/src/app/dashboard/stocks/[ticker]/page.tsx`)
- [ ] Strength score: count of timeframes agreeing on same direction, shown as "Confluence: Strong BUY (3/3)"

---

## Phase 14: Options Payoff Diagram `[ ]`
- [ ] Frontend-only (uses existing chain data): `PayoffChart` component using Recharts line chart
- [ ] Strategy builder UI: pick legs (long call / long put / bull call spread / bear put spread / iron condor), auto-fill strikes near ATM from chain data
- [ ] Compute P&L at expiry across range of underlying prices: `pnl[price] = Σ(leg.payoff(price) × lot_size) − net_premium_paid`
- [ ] Annotate: breakeven points, max profit, max loss
- [ ] Add "Payoff" tab to options page (`frontend/src/app/dashboard/options/[symbol]/page.tsx`) alongside OI Tornado / Chain tabs

---

## Phase 15: Backtesting Engine `[ ]`
- [ ] Backend: `GET /api/v1/analysis/backtest?ticker=X&strategy=ml_signal&period=1y` — replay daily signals on historical OHLCV, compute per-trade P&L
- [ ] Requires: `price_history` Supabase table (see Phase 11 P1) or on-demand yfinance historical pull
- [ ] Return: list of trades (date, signal, entry, exit, pnl%), aggregate stats (win rate, avg gain, avg loss)
- [ ] Frontend: Backtest tab on stock page — equity curve line chart + summary cards (win rate, total return, # trades)

---

## Phase 16: Real-time Trade Tracker / P&L `[ ]`
- [ ] Supabase: `user_trades` table — `(id, user_id, ticker, side, qty, entry_price, entry_at, exit_price, exit_at, status)`
- [ ] Backend: `POST /api/v1/trades`, `GET /api/v1/trades`, `PUT /api/v1/trades/{id}/close`
- [ ] Frontend: Trade log UI — open positions with live P&L via WebSocket quote feed, closed trades with realized P&L
- [ ] Portfolio summary card: total invested, current value, unrealized P&L, realized P&L
- [ ] Add "Trades" nav item in Sidebar + MobileNav

---

## Phase 17: Chart Drawing Tools `[ ]`
- [ ] Lightweight-charts v5 (already installed) supports `ISeriesPrimitive` plugins for overlays
- [ ] Implement: trendline draw (click-drag two points), horizontal support/resistance line, Fibonacci retracement
- [ ] Toolbar above chart on stock page with draw/select/erase toggle buttons
- [ ] Persist drawings in localStorage keyed by ticker (opt: Supabase for cross-device sync)
- [ ] Changes confined to `frontend/src/app/dashboard/stocks/[ticker]/page.tsx` + chart component

---

## Notes
- Phase 3 complete. Auth guard is live (middleware + server layout). Google OAuth + email/password both wired.
- Python/Streamlit backend (`dashboard.py`, `pages/index_options.py`) is the data source for Phases 4–5.
