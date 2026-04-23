from __future__ import annotations
import argparse, json, os, hashlib
from agent.config import AgentConfig
from agent.llm import LLM
from agent.tools import ToolRegistry
from agent.memory import Memory
from agent.logging import TraceLogger
from harness.tools_harness import load_harness_tools
from agent.react import run_react
from agent.planner import run_plan_execute
from agent.tot import bounded_tot_best_thought

def _state_id(seed: int, task: str) -> str:
    h = hashlib.sha256(f"{seed}:{task}".encode("utf-8")).hexdigest()[:10]
    return f"s{seed}-{h}"

def build_llm(backend: str, cfg: AgentConfig):
    return LLM(backend=backend, timeout_s=cfg.llm_timeout_s)

def run_task(task: str, backend: str, mode: str, trace_path: str, seed: int) -> dict:
    cfg = AgentConfig(seed=seed)
    llm = build_llm(backend, cfg)

    reg = ToolRegistry()
    load_harness_tools(registry=reg, seed=seed)
    mem = Memory()

    # Clear trace file to avoid accumulating previous runs
    open(trace_path, "w").close()
    
    logger = TraceLogger(path=trace_path, state_id=_state_id(seed, task))

    if mode == "react":
        return run_react(llm, task, reg, mem, logger, cfg)

    if mode == "plan":
        return run_plan_execute(llm, task, reg, mem, logger, cfg)

    if mode == "tot":
        # In ToT mode, we use ToT to pick a best thought, then return it as final (baseline).
        # Students will improve by mapping best thought -> tool/final actions.
        best = bounded_tot_best_thought(llm, task, cfg.tot_node_budget, cfg.tot_branching, seed)
        logger.log({"mode":"tot","step":1,"action":{"type":"final","answer":best.thought,"confidence":best.score},"obs":"","scratch_hash":"tot"})
        return {"final": best.thought, "confidence": best.score, "steps": 1, "mode": "tot"}

    if mode == "reflect":
        # reflect mode = react + reflection already built-in in run_react; keep alias
        return run_react(llm, task, reg, mem, logger, cfg) | {"mode":"reflect"}

    raise ValueError("mode must be one of: react, plan, reflect, tot")

def run_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--backend", choices=["ollama","groq"], default="ollama")
    ap.add_argument("--mode", choices=["react","plan","reflect","tot"], default="react")
    ap.add_argument("--trace", default="trace.jsonl")
    ap.add_argument("--seed", type=int, default=123)
    args = ap.parse_args()

    res = run_task(args.task, args.backend, args.mode, args.trace, args.seed)
    print(json.dumps(res, ensure_ascii=False))
