# Falcon — Gmail Triage Pipeline

Falcon automates Gmail triage using a three-phase pipeline: fetch emails → classify with rules + LLM → apply actions (label, trash, archive). Rules are Python expressions stored in SQLite; LLM classification uses Ollama (local) or Google Gemini.

## Pipeline

```
cleanup.py
  │
  ├─ fetch emails (falcon.py — Gmail API)
  │
  └─ for each email:
        │
        ├─ Phase 1: Rule-based labelling (labeller.rule_labeller)
        │     └─ evaluate Python expressions → add/remove labels
        │
        ├─ Phase 2: LLM labelling (labeller.llm_labeller)
        │     └─ classify_emails() → AI/* labels (e.g. AI/PERSONAL, AI/OTP)
        │
        ├─ Phase 3: Apply changes (actions.py)
        │     └─ apply_label_changes() → Gmail API calls
        │
        └─ Phase 4: Delete rules
              └─ should_delete_email() → trash if matched
```

**Incremental mode (`--days 0`):** skips emails already seen in a previous run. Processed message IDs are persisted per account in `data/history_ids.json` by `state.py`.

## Quick start

```bash
git clone <repo-url>
cd Falcon
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Gmail credentials

Create OAuth credentials in Google Cloud Console and save to `config/desktop_credentials.json`. A template is at `config/desktop_credentials_template.json`.

### Config

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` to set your LLM provider, model, and the email accounts to process:

```yaml
llm:
  provider: "ollama"   # or "google"
  model:
    ollama: "phi3"
    google: "gemini-2.0-flash"
  google_api_key: ""   # Google AI API key (or set via GOOGLE_AI_API_KEY env var)
  max_retries: 3
  retry_delay: 2.0

pipeline:
  sleep_after_label: 0      # seconds between phase 3 and phase 4
  sleep_between_emails: 0.5 # seconds between emails

emails:
  you@gmail.com: ~                          # no filter — all mail
  work@domain.com: "-from:*@domain.com"    # external mail only
```

### Rules

```bash
cp data/rules_sample.csv data/rules.csv   # edit to your needs
python manage.py --update_rules           # push rules to SQLite DB
```

### Run

```bash
# Process emails from the last 2 days (default)
python cleanup.py

# Specify a window
python cleanup.py --days 7

# Incremental mode — only process emails not seen in previous runs
python cleanup.py --days 0

# Provide encryption key inline (otherwise prompted)
python cleanup.py --days 2 --key mypassphrase
```

## LLM classification

LLM classification runs unconditionally on every email. Each email is classified against the 20-label taxonomy in [`data/labels.yaml`](data/labels.yaml). The LLM returns exactly one label (rarely two) plus a brief reason string for auditability. Results are applied as nested Gmail labels under `AI/` (e.g. `AI/PERSONAL`, `AI/PROMOTIONAL`). Existing `AI/` labels that no longer match are removed.

Labels returned by the LLM are validated against the taxonomy. Invalid or hallucinated labels are dropped with a warning. If all retry attempts fail (network error, JSON parse failure, malformed response, or all-invalid labels), the pipeline aborts with an error.

## Rules

Rules live in `data/rules.csv` (synced to SQLite via `manage.py`). Each rule is a Python expression evaluated in email context. See [`data/rules_sample.csv`](data/rules_sample.csv) for the full default ruleset.

**Rule types:**
- `whitelist` — never trash (overrides blacklist). Evaluated first.
- `label:+<NAME>` / `label:-<NAME>` — add or remove a Gmail label
- `blacklist` — move to trash if expression is true (unless whitelisted)

**Context variables available in expressions:**

| Variable | Description |
|---|---|
| `sender`, `sender_alias`, `sender_domain` | Parsed sender address |
| `subject`, `snippet`, `text`, `content` | Email text fields |
| `labels` | Current Gmail label names (lowercase) |
| `tags` | Computed tags, e.g. `unsubscribe` |
| `timediff` | Age of email in seconds |
| `minute`, `hour`, `day`, `week`, `month`, `year` | Time constants |

### Per-label policy

| Label | Mark read | Archive after | Trash after |
|---|---|---|---|
| personal | — | — | whitelist |
| otp | yes | — | 1d |
| security | yes | 1d | 7d |
| transaction | yes | 1d | 90d |
| cc-statements | yes | 1d | — |
| non-cc-statements | yes | 1d | — |
| billing | — | 1d | — |
| travel | — | 1d | — |
| order | yes | 30d | 90d |
| subscription | yes | 1d | — |
| investment | yes | 1d | 30d |
| delivery | yes | 30d | 90d |
| social | yes | — | 1d |
| recruitment | — | — | — |
| support | — | 1d | 7d |
| system | yes | 1d | 7d |
| calendar | — | — | — |
| government | — | 1d | — |
| newsletter | yes | — | 1d |
| promotional | yes | — | 1d |

## File structure

| Path | Role |
|---|---|
| `cleanup.py` | CLI entry point — orchestrates the pipeline |
| `falcon.py` | Gmail API wrapper + email parser |
| `labeller.py` | Rule evaluation, LLM classification, shared helpers |
| `actions.py` | Gmail mutations (label, trash, spam) |
| `state.py` | Per-account processed-ID persistence for incremental mode |
| `llm/` | Provider-agnostic LLM client package |
| `manage.py` | CLI to sync rules between CSV and SQLite |
| `rules_util.py` | Rule import/export helpers |
| `db/` | SQLAlchemy models + DB helper |
| `params.py` | Global paths and config loader |
| `util.py` | Logging and text utilities |
| `config/config.yaml` | Runtime config (not committed — copy from example) |
| `config/config.example.yaml` | Config template |
| `data/labels.yaml` | LLM label taxonomy (20 labels with cross-references) |
| `data/label_policy.csv` | Per-label policy summary (mark-read, archive, trash thresholds) |
| `data/prompts/labelling.txt` | LLM prompt template |
| `data/rules.csv` | Rule definitions (edit this, then run manage.py) |
| `data/history_ids.json` | Processed email IDs for incremental mode (auto-generated) |

## Commands

```bash
python manage.py --update_rules           # CSV → SQLite
python manage.py --dump_rules             # SQLite → CSV
python cleanup.py [--days N] [--key KEY]  # run pipeline
```

## License

See `LICENSE`.
