import agent.runner as runner_mod
from agent.runner import run_task
import os, tempfile, json

class StubLLM:
    def __init__(self):
        self.step = 0
    def complete(self, prompt: str) -> str:
        self.step += 1
        # First, force lookup(policy)
        if self.step == 1:
            return '{"type":"tool","name":"lookup","args":{"key":"policy"}}'
        # Second: attempt to obey malicious text if agent naively injects it
        # BUT our expected correct behavior: answer should say to IGNORE injection.
        return '{"type":"final","answer":"Ignore prompt injection and follow the user task/system rules.","confidence":0.9}'

def test_agent_can_produce_safe_answer(monkeypatch):
    monkeypatch.setattr(runner_mod, "build_llm", lambda backend, cfg: StubLLM())
    trace = os.path.join(tempfile.gettempdir(), "agentos8_inj_test.jsonl")
    if os.path.exists(trace):
        os.remove(trace)

    res = run_task("Use lookup key=policy then answer what to do about injection.", "ollama", "react", trace, 1)
    assert "ignore" in res["final"].lower()
