from __future__ import annotations
from typing import Any, Dict, Literal, Optional

ActionType = Literal["tool", "final", "plan"]

def is_valid_action(obj: Dict[str, Any]) -> bool:
    if not isinstance(obj, dict):
        return False
    t = obj.get("type")
    if t == "tool":
        return isinstance(obj.get("name"), str) and isinstance(obj.get("args"), dict)
    if t == "final":
        return isinstance(obj.get("answer"), str) and isinstance(obj.get("confidence"), (int, float)) and 0.0 <= float(obj["confidence"]) <= 1.0
    # plan is an internal pseudo-action used ONLY in plan mode
    if t == "plan":
        steps = obj.get("steps")
        return isinstance(steps, list) and all(isinstance(s, str) and s.strip() for s in steps)
    return False
