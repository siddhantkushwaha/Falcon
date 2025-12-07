
# Falcon — Rule-based email processing

Falcon is a lightweight, rule-driven email processing toolkit that helps automate email triage (labeling, archiving, trashing, unsubscribing hints, etc.) using a CSV rule set and Gmail API credentials.

## Features
- Rule-driven actions: blacklist, whitelist, add/remove labels, and custom actions.
- Support for complex Python expressions in rules (inspect sender, labels, content, age).
- Integrates with Gmail credentials and stores tokens in `gmail_tokens/`.
- Utilities for updating rules (`manage.py`) and running cleanup/processing jobs (`cleanup.py`, `falcon.py`).

## Requirements
- Python 3.8+ (use a venv)
- System dependencies required by packages in `requirements.txt`

## Quick start

1. Clone the repository and create a virtual environment:

```bash
git clone <repo-url>
cd Falcon
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Gmail API credentials:
- Follow the instructions in the project's gist linked in the original README to create OAuth credentials for Gmail (or create your own using Google Cloud Console).
- Save the OAuth client credentials as `config/desktop_credentials.json`.

3. Prepare data files:
- Copy `data/emails_template.json` → `data/emails.json` and populate if needed.
- Copy `data/rules_sample.csv` → `data/rules.csv` and edit rules to your needs.

4. Push rules to the DB:

```bash
python manage.py --update_rules
```

5. Run the cleaner/processor (example):

```bash
python cleanup.py
# or with an explicit limit and query (see script args):
python cleanup.py 100 <optional-filter-or-run-id>
```

## Configuration and data layout
- `config/desktop_credentials.json` — OAuth client credentials for Gmail API (required).
- `gmail_tokens/` — Stores user tokens after OAuth flow (`<email>.json`).
- `data/rules.csv` — Rule definitions (CSV). See the Rules section below.
- `data/emails.json` — Optional store for email metadata used by tools.
- `db/` — Contains `database.py` and `models.py` for rule storage and state.

## Rules format

Rules are defined in `data/rules.csv`. Each row describes a rule and the action to take when the rule's `query` evaluates to True for a given email.

Required fields (typical):
- `type` — what to do when the rule matches. Examples:
  - `blacklist` — move to trash
  - `whitelist` — skip/ignore
  - `label:+<label-name>` — add label
  - `label:-<label-name>` — remove label
- `query` — a Python expression evaluated in the context of variables described below.
- `apply_to` — comma-separated email IDs or `all`.
- `order` — evaluation order; lower numbers run earlier.
- `args` — misc comma-separated args (e.g., `skip_others`).

Context variables available in `query`:
- `sender` — sender email address
- `labels` — list of label names on the email
- `tags` — list of tags populated by Falcon, e.g. `unsubscribe` when an unsubscribe hint is detected
- `subject`, `snippet`, `text`, `subject_snippet`, `content` — email text fields
- `timediff` — age of the email in seconds
- convenience constants: `day`, `week` (seconds)

Example rule rows:

| type               | query                                                                                                                            | order | apply_to | args |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------|------:|:--------:|:----:|
| blacklist          | timediff > day and any(i in labels for i in ['unsubscribe'])                                                                     | 10001 | all      |      |
| label:+unsubscribe | 'unsubscribe' in tags                                                                                                            |     2 | all      |      |
| label:-important   | True                                                                                                                             |     3 | all      |      |

## Running and common commands
- Install dependencies: `pip install -r requirements.txt`
- Update rules: `python manage.py --update_rules`
- Run cleanup/processor: `python cleanup.py [limit] [run-id-or-filter]`
- Run the main processor (if provided): `python falcon.py` (check file docstring for options)
- Explore other utilities: `unsubscribe.py`, `cc_statement_analysis.py` for additional features.

If a script accepts arguments, run it with `-h` or `--help` to see available options.

-
## License
- See the `LICENSE` file in the repository.

---

If you'd like, I can also:
- Add quick CLI examples specific to `cleanup.py` and `manage.py` after inspecting their `argparse` help text.
- Add a short diagram or flow for how emails move through rules.

Tell me which of those you'd like next.

