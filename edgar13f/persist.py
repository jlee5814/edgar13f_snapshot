from __future__ import annotations

import csv
import json
from typing import Dict, Iterable
from pathlib import Path


def write_csv(path: str, rows: Iterable[Dict]) -> int:
    rows = list(rows)
    headers = [
        "cik", "manager_name", "period_end",
        "issuer_name", "cusip", "value_usd_thousands",
        "shares", "share_type", "put_call", "discretion",
        "voting_sole", "voting_shared", "voting_none",
    ]
    p = Path(path)
    # Ensure parent directory exists (e.g., "data/")
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        count = 0
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in headers})
            count += 1
    return count


def write_json(path: str, obj: Dict) -> None:
    p = Path(path)
    # Ensure parent directory exists
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
