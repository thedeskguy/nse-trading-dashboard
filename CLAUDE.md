# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # if exists
cp .env.example .env              # then fill in API keys
```

## File Structure

```
.tmp/           # Temporary/intermediate files — regenerated as needed, disposable
tools/          # Python scripts (deterministic execution)
workflows/      # Markdown SOPs
.env            # API keys and secrets (never commit)
credentials.json, token.json  # Google OAuth (gitignored)
```

Deliverables go to cloud services (Google Sheets, Slides, etc.). Local files are processing intermediates only.
