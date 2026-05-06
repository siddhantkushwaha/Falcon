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
        ├─ Phase 1: Rule-based labelling
        │     └─ evaluate Python expressions → add/remove labels
        │
        ├─ Phase 2: LLM labelling (labeller.py)
        │     └─ classify_emails() → AI/* labels (e.g. AI/PERSONAL, AI/OTP)
        │
        ├─ Phase 3: Apply changes (actions.py)
        │     └─ apply_label_changes() → Gmail API calls
        │
        └─ Phase 4: Delete rules
              └─ should_delete_email() → trash if matched
```

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

Edit `config/config.yaml` to set your LLM provider (`ollama` or `google`) and model.

### Data files

```bash
cp data/emails_template.json data/emails.json   # add email → Gmail query mappings
cp data/rules_sample.csv data/rules.csv          # edit rules to your needs
python manage.py --update_rules                  # push rules to SQLite DB
```

### Run

```bash
# Process emails from the last 2 days
python cleanup.py

# Last N days, with encryption key, with LLM enabled
python cleanup.py [num_days] [key] [1]
```

## LLM classification

When LLM is enabled (`python cleanup.py 2 mykey 1`), each email is classified against the label taxonomy in `data/labels.yaml`. Results are applied as nested Gmail labels under `AI/` (e.g. `AI/PERSONAL`, `AI/PROMOTIONAL`).

Configure the provider in `config/config.yaml`:

```yaml
llm:
  provider: "ollama"   # or "google"
  model:
    ollama: "phi3"
    google: "gemini-2.0-flash"
```

For Google Gemini, set `GOOGLE_AI_API_KEY` in your environment.

## Rules

Rules live in `data/rules.csv` (synced to SQLite via `manage.py`). Each rule is a Python expression evaluated in email context.

**Rule types:**
- `blacklist` — move to trash if expression is true
- `whitelist` — never trash (overrides blacklist)
- `label:+<NAME>` — add label
- `label:-<NAME>` — remove label

**Context variables available in expressions:**

| Variable | Description |
|---|---|
| `sender`, `sender_alias`, `sender_domain` | Parsed sender address |
| `subject`, `snippet`, `text`, `content` | Email text fields |
| `labels` | Current Gmail label names (lowercase) |
| `tags` | Computed tags, e.g. `unsubscribe` |
| `timediff` | Age of email in seconds |
| `minute`, `hour`, `day`, `week`, `month`, `year` | Time constants |

**Example rules:**

```
whitelist  → 'starred' in labels
label:+unsubscribe → 'unsubscribe' in tags
label:-important → True
blacklist  → timediff > day and 'unsubscribe' in labels and not any(i in labels for i in ['ai/actionable', 'ai/personal'])
```

The blacklist rule above protects emails the LLM flagged as personal or actionable, even if they have an unsubscribe header.

## File structure

| Path | Role |
|---|---|
| `cleanup.py` | CLI entry point — orchestrates the pipeline |
| `falcon.py` | Gmail API wrapper + email parser |
| `labeller.py` | LLM classification orchestrator |
| `actions.py` | Gmail mutations (label, trash, spam) |
| `llm/` | Provider-agnostic LLM client package |
| `manage.py` | CLI to sync rules between CSV and SQLite |
| `rules_util.py` | Rule import/export helpers |
| `db/` | SQLAlchemy models + DB helper |
| `params.py` | Global paths |
| `util.py` | Logging and text utilities |
| `config/config.yaml` | Runtime config (not committed — copy from example) |
| `config/config.example.yaml` | Config template |
| `data/labels.yaml` | LLM label taxonomy |
| `data/prompts/labelling.txt` | LLM prompt template |
| `data/rules.csv` | Rule definitions (edit this, then run manage.py) |
| `data/emails.json` | Email address → Gmail query mapping |

## Commands

```bash
python manage.py --update_rules   # CSV → SQLite
python manage.py --dump_rules     # SQLite → CSV
python cleanup.py [days] [key] [use_llm: 1|0]
```

## License

See `LICENSE`.
