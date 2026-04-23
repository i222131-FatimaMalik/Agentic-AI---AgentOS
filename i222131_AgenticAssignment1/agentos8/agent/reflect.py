from __future__ import annotations
from agent.prompts import build_reflection_prompt
from agent.utils import extract_first_json, safe_json_loads
from agent.protocol import is_valid_action

def repair_action(llm, task: str, last_output: str, error: str) -> dict:
    prompt = build_reflection_prompt(task, last_output, error)
    raw = llm.complete(prompt)
    js = safe_json_loads(extract_first_json(raw))
    if not is_valid_action(js) or js.get("type") == "plan":
        raise ValueError("Reflection did not return a valid tool/final action")
    return js
