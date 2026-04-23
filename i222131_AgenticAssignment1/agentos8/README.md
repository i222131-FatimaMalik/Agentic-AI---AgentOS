# AGENTOS-8 Starter Package (Framework-Free Agentic AI)

This repository is the **starter code + public tests** for the AGENTOS-8 assignment.

You will implement a robust agentic system in **pure Python** (no LangChain / agent frameworks) supporting:
- **ReAct** (tool-using loop)
- **Plan & Execute**
- **Reflection repair**
- **Bounded Tree-of-Thought (ToT)**
- Structured **JSONL trace logging**
- A **per-category framework comparison** runner

> Public tests are intentionally demanding. They simulate 2026-style failures (prompt injection, flaky tools, malformed model outputs).

---

## 1) Setup

### Option A: Just run tests (recommended)
Use Python 3.12+.

```bash
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

pip install -U pip
pip install -e .
pip install pytest
```

Run public tests:

```bash
pytest
```

### Option B: Run the agent with a real LLM
You may use **Ollama** or **Groq**.

#### Ollama
Install Ollama and pull any model you like. Example:

```bash
ollama pull qwen2.5:1.5b
```

Run:

```bash
python run_agent.py --task "Compute (27+53)*(12-7)" --backend ollama --mode react --trace trace.jsonl --seed 123
```

Environment variables (optional):
- `OLLAMA_MODEL` (default: `qwen2.5:1.5b`)

#### Groq
Set:
- `GROQ_API_KEY`
- `GROQ_MODEL` (optional)

Run:

```bash
python run_agent.py --task "..." --backend groq --mode react --trace trace.jsonl --seed 123
```

---

## 2) Running the framework comparison experiment

```bash
python -m agent.compare --tasks harness/tasks_public.json --backend ollama --seed 123 --out compare.json
```

This produces `compare.json` with per-category metrics.

---

## 3) Notes on public tests
Public tests **do not require** a real LLM API key.
They monkeypatch the LLM with deterministic stubs to test your architecture.

Hidden tests (used by the instructor) are harder and include randomized cases.

Good luck build a system, not a prompt. 😉
