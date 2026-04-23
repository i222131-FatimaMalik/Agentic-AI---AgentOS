import json, os, tempfile
from agent.runner import run_task, build_llm
import agent.runner as runner_mod

class StubLLM:
    def __init__(self, script):
        self.script = script
        self.i = 0
    def complete(self, prompt: str) -> str:
        out = self.script[self.i]
        self.i = min(self.i + 1, len(self.script)-1)
        return out

def test_trace_has_required_fields(monkeypatch):
    # Always call calc then final
    script = [
        'TEXT {"type":"tool","name":"calc","args":{"expression":"2+3"}}',
        '{"type":"final","answer":"5","confidence":0.9}'
    ]
    monkeypatch.setattr(runner_mod, "build_llm", lambda backend, cfg: StubLLM(script))

    trace = os.path.join(tempfile.gettempdir(), "agentos8_trace_test.jsonl")
    if os.path.exists(trace):
        os.remove(trace)

    res = run_task("compute 2+3", "ollama", "react", trace, 123)
    assert "final" in res and res["final"] == "5"

    lines = open(trace, "r", encoding="utf-8").read().strip().splitlines()
    assert len(lines) >= 1
    obj = json.loads(lines[0])
    for k in ["mode","step","action","obs","scratch_hash","state_id"]:
        assert k in obj, f"missing field {k} in trace record"
