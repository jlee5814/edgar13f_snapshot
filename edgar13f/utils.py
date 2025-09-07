import time
import logging
from typing import Dict

DEFAULT_UA = "JB-13F-Snapshot/0.1 (contact: you@example.com)"

def sec_headers(user_agent: str | None = None) -> Dict[str, str]:
    return {"User-Agent": user_agent or DEFAULT_UA}

def polite_sleep(seconds: float = 0.5) -> None:
    if seconds > 0:
        time.sleep(seconds)

def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=level,
    )
