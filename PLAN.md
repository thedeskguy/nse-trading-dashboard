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

## Phase 8: Scanner Page `[ ]`
- [ ] Nifty 50 batch signal scan
- [ ] Table of all 50 stocks with signal + confidence
- [ ] Filter / sort by signal type

---

## Phase 9: Polish + Lighthouse `[ ]`
- [ ] Performance audit (Lighthouse score ≥ 90)
- [ ] Accessibility fixes
- [ ] Mobile responsiveness pass
- [ ] Loading states + error boundaries

---

## Phase 10: Production Deploy `[ ]`
- [ ] Backend on Railway
- [ ] Frontend on Vercel
- [ ] Environment variables configured
- [ ] Domain + SSL

---

## Notes
- Phase 3 complete. Auth guard is live (middleware + server layout). Google OAuth + email/password both wired.
- Python/Streamlit backend (`dashboard.py`, `pages/index_options.py`) is the data source for Phases 4–5.
