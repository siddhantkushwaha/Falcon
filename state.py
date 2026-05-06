import json
from pathlib import Path

import params

STATE_FILE = Path(params.data_dir) / "history_ids.json"


def load_processed_ids(email: str) -> set[str]:
    try:
        data = json.loads(STATE_FILE.read_text())
        return set(data.get(email, []))
    except Exception:
        return set()


def mark_processed(email: str, mail_id: str) -> None:
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        data = {}
    ids = set(data.get(email, []))
    ids.add(mail_id)
    data[email] = list(ids)
    STATE_FILE.write_text(json.dumps(data, indent=2))
