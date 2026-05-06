# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Falcon is a Gmail triage pipeline that automates email labelling and cleanup. The pipeline has three phases: fetch (Gmail API) → classify (rule engine + optional LLM) → act (label/trash/archive). Rules are Python expressions stored in SQLite; LLM classification uses a provider-agnostic client supporting Ollama and Google Gemini.

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

# Run email cleanup (num_days defaults to 2, key is encryption passphrase, use_llm=1 enables LLM)
python cleanup.py [num_days] [key] [use_llm: 1|0]
```

## Architecture

**Pipeline flow:**
```
cleanup.py → fetch (falcon.py) → for each email:
  Phase 1: rule-based labelling (evaluate_clause on label rules)
  Phase 2: LLM labelling (labeller.py → classify_emails → AI/* labels)
  Phase 3: apply label changes (actions.py → Gmail API)
  Phase 4: delete rules (should_delete_email → trash if matched)
→ consolidate_spam()
```

**Module responsibilities:**

| Module | Knows about | Does NOT know about |
|---|---|---|
| `falcon.py` | Gmail API, email parsing | Labels, rules, LLM |
| `labeller.py` | LLM client, taxonomy, prompts | Gmail API, actions |
| `actions.py` | Gmail API (mutations only) | Rules, LLM, classification |
| `cleanup.py` | Pipeline ordering, CLI args | LLM internals, Gmail API details |
| `llm/` | LLM providers, JSON parsing | Email domain, taxonomy |

**Entry points:**
- `cleanup.py` — Main pipeline. Fetches Gmail messages, runs rule + LLM labelling, applies label changes, trashes matched emails.
- `manage.py` — CLI for syncing rules between `data/rules.csv` and SQLite DB.

**Core modules:**
- `falcon.py` — `FalconClient` (Gmail API wrapper via `google_py_apis`) and `process_gmail_dic` (raw Gmail → structured dict). `iterate_gmail_messages` is the shared iterator.
- `cleanup.py:evaluate_clause` — Evaluates rule queries as Python expressions with `eval()`, injecting email context variables (`sender`, `labels`, `tags`, `timediff`, `content`, etc.).
- `labeller.py` — Loads taxonomy from `data/labels.yaml`, batches emails, calls LLM client, returns `{email_id: [labels]}`. Main entry: `classify_emails()`.
- `actions.py` — `apply_label_changes()`, `trash_email()`, `consolidate_spam()`. All Gmail mutations go here.
- `llm/` — `LLMClient` abstract base, `OllamaLLMClient`, `GoogleAILLMClient`, `get_llm_client(config)` factory.
- `db/` — SQLAlchemy models + helper. Single SQLite DB at `data/db.sqlite`.
- `params.py` — Global paths and config. Loads `data/emails.json` at import time.
- `util.py` — Logging (via `viper-python`), text cleaning.

**Data files:**
- `config/config.yaml` — Runtime config (not committed; copy from `config/config.example.yaml`).
- `data/labels.yaml` — LLM label taxonomy (16 categories with descriptions and attention tiers).
- `data/prompts/labelling.txt` — LLM prompt template with `{taxonomy}` and `{emails}` placeholders.
- `data/rules.csv` — Rule definitions (type, query, order, apply_to, args).
- `data/emails.json` — Map of email addresses to Gmail query filters.
- `config/desktop_credentials.json` — OAuth client credentials (not committed).

## Key Design Decisions

- Rules use raw `eval()` with local variables — rule queries are arbitrary Python expressions, not a DSL.
- LLM labels are namespaced under `AI/` (e.g. `AI/PERSONAL`, `AI/OTP`) so rule expressions can reference them: `'ai/personal' in labels`.
- Token encryption: Gmail tokens in `gmail_tokens/` are encrypted with a passphrase provided at runtime.
- The `google_py_apis` package (PyPI) handles Gmail API auth/calls.
- Logging goes to `logs/falcon.log` via `viper-python`'s custom logger.
- All module imports must be at the top of files — no local/deferred imports.
