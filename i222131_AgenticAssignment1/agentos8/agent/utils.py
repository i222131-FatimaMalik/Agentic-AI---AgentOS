from __future__ import annotations
import json

def extract_first_json(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No '{' found for JSON start")

    depth = 0
    in_str = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1]

    raise ValueError("JSON object not balanced")

def safe_json_loads(s: str):
    return json.loads(s)
