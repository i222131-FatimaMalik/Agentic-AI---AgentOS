from __future__ import annotations
import json, time, hashlib
from dataclasses import dataclass
from typing import Any, Dict

def state_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:16]

@dataclass
class TraceLogger:
    path: str
    state_id: str
    _first_log: bool = True

    def log(self, rec: Dict[str, Any]) -> None:
        r = dict(rec)
        r.setdefault("ts", time.time())
        r.setdefault("state_id", self.state_id)
        # Use write mode for first log to overwrite, then append for subsequent logs
        mode = "w" if self._first_log else "a"
        with open(self.path, mode, encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        self._first_log = False
