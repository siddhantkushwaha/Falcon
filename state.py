import json
from datetime import datetime
from pathlib import Path

import params

STATE_FILE = Path(params.data_dir) / "history_ids.json"


def load_last_run(email: str) -> datetime | None:
    try:
        data = json.loads(STATE_FILE.read_text())
        raw = data.get(email)
        if raw is None:
            return None
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def save_last_run(email: str, dt: datetime) -> None:
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        data = {}
    data[email] = dt.isoformat()
    STATE_FILE.write_text(json.dumps(data, indent=2))
