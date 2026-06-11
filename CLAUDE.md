# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack NSE trading SaaS. It has three layers:
- **Streamlit app** (root) — original data/signal engine; Python + Plotly. Test with `streamlit run <file> --server.headless true` after significant changes.
- **FastAPI backend** (`backend/`) — REST API serving the Next.js frontend. Deployed on Render.
- **Next.js frontend** (`frontend/`) — React SaaS UI with Supabase auth + Razorpay payments.

## Code Quality

After editing any Python file, always run `python -c "import py_compile; py_compile.compile('<filename>', doraise=True)"` to catch syntax errors and undefined variables before presenting the result.

## Domain-Specific Notes

When working with financial data (mutual funds, trading), always verify date alignment and reference date consistency across data sources before assuming calculations are correct.

# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution.

## The WAT Architecture

**Layer 1: Workflows (`workflows/`)** — Markdown SOPs defining objectives, required inputs, which tools to use, expected outputs, and edge case handling.

**Layer 2: Agents (you)** — Read the relevant workflow, run tools in sequence, handle failures, ask clarifying questions. Never attempt execution directly when a tool exists for it.

**Layer 3: Tools (`tools/`)** — Python scripts for deterministic execution: API calls, data transformations, file operations. Credentials go in `.env`.

## Operating Rules

1. **Check `tools/` before writing anything new.** Only create scripts when nothing exists for the task.
2. **On errors:** read the full trace, fix and retest (check before rerunning if the script makes paid API calls), then update the workflow with what you learned (rate limits, quirks, better endpoints).
3. **Keep workflows current.** Update them as you learn better methods or encounter constraints. Do not create or overwrite workflows without asking unless explicitly told to.
4. **Update README on major additions.** Whenever a new dashboard, tool, workflow, or significant feature is added to the codebase, update `README.md` to reflect it — new sections, updated file structure, usage instructions, and any new dependencies or API requirements.

## Git Workflow (single branch)

`main` is the only long-lived branch — it is what deploys (Render backend, Vercel frontend).

- Small changes: commit directly to `main`.
- Larger features: short-lived `feature/<name>` branch off `main` → PR → merge → **delete the branch immediately**. No `develop`, no long-running branches.

**CI runs on every push and PR to `main`:**
- Backend: ruff lint + syntax check + pytest
- Frontend: tsc type-check + eslint + next build

**Before pushing to main:**
- [ ] `pytest tests/` passes (backend)
- [ ] `npm test` passes (frontend, when frontend changed)
- [ ] No TypeScript errors (`npx tsc --noEmit`, when frontend changed)
- [ ] No lint errors

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # if exists
cp .env.example .env              # then fill in API keys
cd frontend && cp .env.example .env.local  # fill in Supabase keys
```

## File Structure

```
# Streamlit data/signal layer (root)
dashboard.py          # Main Streamlit entry point (equities)
equity_scanner.py     # Nifty 100 equity scanner
pages/
  index_options.py    # Index Options page (NIFTY / BANKNIFTY / MIDCPNIFTY)
  about.py
tools/                # WAT Layer 3 — Python scripts (deterministic execution)
workflows/            # WAT Layer 1 — Markdown SOPs
tests/                # Unit tests (pytest)

# FastAPI backend
backend/
  main.py             # FastAPI app entry point
  config.py / deps.py
  routers/            # market, options, analysis, payments, health
  services/           # angel_session, cache, serializers
  requirements.txt    # Backend-specific deps
  .env                # Backend secrets

# Next.js SaaS frontend
frontend/
  src/app/            # Next.js App Router pages
  src/components/     # React components
  CLAUDE.md / AGENTS.md  # Frontend-specific agent rules

# Docs & config
docs/
  SYSTEM_GUIDE.md     # Full system guide (Streamlit layer)
  tutorial.md         # Personal walkthrough / explainer
PLAN.md               # SaaS roadmap (Phases 0–10)
README.md             # Public project overview
render.yaml           # Render deploy config (starts backend)
.streamlit/           # Streamlit config (dark theme, headless)
.tmp/                 # Temporary cache files — disposable
.env / .env.example   # Root API keys (Streamlit layer)
```

## Key Architecture Notes

- **Stock search** uses NSE's public equity CSV (`archives.nseindia.com/content/equities/EQUITY_L.csv`) for full company names. Cached for 24h.
- **Options chain** uses Angel One instrument master (`margincalculator.angelbroking.com`) for token lookup. Cached for 1h.
- **OI chart** requires `yaxis=dict(range=[-0.5, n-0.5])` fix due to Plotly 6 parsing numeric-string category labels as numbers.
- **Plotly price charts** use `type="category"` x-axis with string date labels (via `_x_labels()`) to eliminate weekend/holiday gaps.
- The app runs as a single Streamlit multi-page app — `dashboard.py` is the entry point, Index Options is under `pages/`.

The Streamlit layer outputs are local (charts, signals). The SaaS layer deploys backend to Render and frontend to Vercel.
