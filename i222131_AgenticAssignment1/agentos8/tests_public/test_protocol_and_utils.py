import pytest
from agent.protocol import is_valid_action
from agent.utils import extract_first_json, safe_json_loads

def test_extract_first_json_with_wrapping_text():
    txt = 'Sure! Here is the JSON: {"type":"tool","name":"calc","args":{"expression":"2+2"}} Thanks!'
    js = safe_json_loads(extract_first_json(txt))
    assert js["type"] == "tool" and js["name"] == "calc"

def test_protocol_accepts_only_tool_final_plan():
    assert is_valid_action({"type":"tool","name":"calc","args":{"expression":"1+1"}})
    assert is_valid_action({"type":"final","answer":"ok","confidence":0.5})
    assert is_valid_action({"type":"plan","steps":["a","b","c","d"]})
    assert not is_valid_action({"type":"tool","name":"calc"})
    assert not is_valid_action({"type":"final","answer":"x","confidence":2.0})
