# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Falcon is a Gmail triage pipeline that automates email labelling and cleanup. The pipeline has three phases: fetch (Gmail API) → classify (rule engine + LLM) → act (label/trash/archive). Rules are Python expressions stored in SQLite; LLM classification uses a provider-agnostic client supporting Ollama and Google Gemini.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Config (copy and edit)
cp config/config.example.yaml config/config.yaml

# Push rules from CSV to SQLite
python manage.py --update_rules

# Dump rules from SQLite to CSV
python manage.py --dump_rules

# Run email cleanup (--days defaults to 2; --days 0 = incremental mode; --key prompted if omitted)
python cleanup.py [--days N] [--key KEY]
```

## Architecture

**Pipeline flow:**
```
cleanup.py → fetch (falcon.py) → for each email:
  Phase 1: rule-based labelling (labeller.rule_labeller)
  Phase 2: LLM labelling (labeller.llm_labeller → AI/* labels)
  Phase 3: apply label changes (actions.py → Gmail API)
  Phase 4: delete rules (should_delete_email → trash if matched)
→ consolidate_spam()
```

**Incremental mode (`--days 0`):** processed message IDs are saved to `data/history_ids.json` via `state.py`. On subsequent runs, already-seen IDs skip phases 1–3 but still re-evaluate delete rules.

**Module responsibilities:**

| Module | Knows about | Does NOT know about |
|---|---|---|
| `falcon.py` | Gmail API, email parsing | Labels, rules, LLM |
| `labeller.py` | Rule eval, LLM client, taxonomy, prompts | Gmail API, actions |
| `actions.py` | Gmail API (mutations only) | Rules, LLM, classification |
| `cleanup.py` | Pipeline ordering, CLI args | LLM internals, Gmail API details |
| `state.py` | Processed-ID persistence | Pipeline, Gmail |
| `llm/` | LLM providers, JSON parsing | Email domain, taxonomy |

**Entry points:**
- `cleanup.py` — Main pipeline. Fetches Gmail messages, runs rule + LLM labelling, applies label changes, trashes matched emails.
- `manage.py` — CLI for syncing rules between `data/rules.csv` and SQLite DB.

**Core modules:**
- `falcon.py` — `FalconClient` (Gmail API wrapper via `google_py_apis`) and `process_gmail_dic` (raw Gmail → structured dict). `iterate_gmail_messages` is the shared iterator.
- `labeller.py` — Owns all classification logic: `evaluate_clause` (rule eval with `eval()`), `rule_labeller` (label rules → add/remove lists), `llm_labeller` (LLM → AI/* labels), and shared helpers (`get_label_names`, `compute_tags`).
- `actions.py` — `apply_label_changes()`, `trash_email()`, `consolidate_spam()`. All Gmail mutations go here.
- `state.py` — `load_processed_ids(email)` / `mark_processed(email, mail_id)`. Persists sets of processed message IDs per account in `data/history_ids.json`.
- `llm/` — `LLMClient` abstract base, `OllamaLLMClient`, `GoogleAILLMClient`, `get_llm_client(config)` factory.
- `db/` — SQLAlchemy models + helper. Single SQLite DB at `data/db.sqlite`.
- `params.py` — Global paths. Loads `config/config.yaml` and exposes `emails` dict (account → Gmail query).
- `util.py` — Logging (via `viper-python`), text cleaning.

**Data files:**
- `config/config.yaml` — Runtime config (not committed; copy from `config/config.example.yaml`). Contains LLM settings and the `emails` map (account → Gmail query).
- `data/labels.yaml` — LLM label taxonomy (16 categories with descriptions and attention tiers).
- `data/prompts/labelling.txt` — LLM prompt template with `{taxonomy}` and `{emails}` placeholders.
- `data/rules.csv` — Rule definitions (type, query, order, apply_to, args).
- `data/history_ids.json` — Per-account sets of processed message IDs (auto-generated; used by incremental mode).
- `config/desktop_credentials.json` — OAuth client credentials (not committed).

## Key Design Decisions

- Rules use raw `eval()` with local variables — rule queries are arbitrary Python expressions, not a DSL.
- LLM classification runs unconditionally on every email (no opt-in flag). Existing `AI/` labels that no longer match are removed.
- LLM labels are namespaced under `AI/` (e.g. `AI/PERSONAL`, `AI/OTP`) so rule expressions can reference them: `'ai/personal' in labels`.
- Incremental mode (`--days 0`) skips phases 1–3 for already-processed IDs but always re-evaluates delete rules, so new blacklist rules can still catch old mail.
- Token encryption: Gmail tokens in `gmail_tokens/` are encrypted with a passphrase provided at runtime.
- The `google_py_apis` package (PyPI) handles Gmail API auth/calls.
- Logging goes to `logs/falcon.log` via `viper-python`'s custom logger.
- All module imports must be at the top of files — no local/deferred imports.
