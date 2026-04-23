import json, os, tempfile
import agent.compare as cmp
import agent.runner as runner_mod

class StubLLM:
    def __init__(self):
        self.i = 0
    def complete(self, prompt: str) -> str:
        # Simple deterministic behavior: if prompt asks plan -> plan; if asks tot -> candidates/score; else tool->calc->final
        if "Create a plan of EXACTLY" in prompt:
            return '{"type":"plan","steps":["use calc","verify","final answer","double-check"]}'
        if "__tot_candidates__" in prompt:
            return '{"type":"tool","name":"__tot_candidates__","args":{"candidates":["A","B","C"]}}'
        if "__tot_score__" in prompt:
            # score B best
            score = 0.2
            if "THOUGHT:" in prompt and "\nB" in prompt:
                score = 0.95
            return '{"type":"tool","name":"__tot_score__","args":{"score":%.2f}}' % score
        # default react/plan execution:
        if '"name":"calc"' in prompt:
            return '{"type":"final","answer":"5","confidence":0.9}'
        return '{"type":"tool","name":"calc","args":{"expression":"2+3"}}'

def test_compare_outputs_by_category(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_mod, "build_llm", lambda backend, cfg: StubLLM())
    out = tmp_path / "compare.json"
    tasks = tmp_path / "tasks.json"
    tasks.write_text('[{"id":"x","category":"computation","task":"Compute 2+3","expect_substring":"5"}]', encoding="utf-8")

    # run compare main
    import subprocess, sys
    p = subprocess.run([sys.executable, "-m", "agent.compare", "--tasks", str(tasks), "--backend", "ollama", "--seed", "1", "--out", str(out)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert p.returncode == 0, p.stderr.decode("utf-8", errors="ignore")

    obj = json.loads(out.read_text(encoding="utf-8"))
    assert "by_category" in obj
    assert "computation" in obj["by_category"]
    assert "react" in obj["by_category"]["computation"]
