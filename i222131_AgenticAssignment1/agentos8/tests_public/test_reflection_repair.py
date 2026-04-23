import os, tempfile
import agent.runner as runner_mod
from agent.runner import run_task

class StubLLM:
    def __init__(self):
        self.calls = 0
    def complete(self, prompt: str) -> str:
        self.calls += 1
        # First output is invalid JSON (forces reflection)
        if self.calls == 1:
            return "I think you should call calc. {bad json"
        # Reflection prompt: return corrected tool call
        if "previous output was invalid" in prompt.lower() or "last_output" in prompt.lower() or "ERROR:" in prompt:
            return '{"type":"tool","name":"calc","args":{"expression":"10+5"}}'
        # After tool obs, finish
        return '{"type":"final","answer":"15","confidence":0.8}'

def test_reflection_is_used(monkeypatch):
    monkeypatch.setattr(runner_mod, "build_llm", lambda backend, cfg: StubLLM())
    trace = os.path.join(tempfile.gettempdir(), "agentos8_reflect_test.jsonl")
    if os.path.exists(trace):
        os.remove(trace)
    res = run_task("Compute 10+5", "ollama", "react", trace, 7)
    assert res["final"] == "15"
