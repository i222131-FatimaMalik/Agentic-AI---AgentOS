from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class Memory:
    episodic: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, event: Dict[str, Any]) -> None:
        self.episodic.append(event)

    def recent(self, k: int = 6) -> List[Dict[str, Any]]:
        return self.episodic[-k:]
