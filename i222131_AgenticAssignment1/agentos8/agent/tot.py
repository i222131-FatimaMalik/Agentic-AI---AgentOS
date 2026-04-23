from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import random
from agent.prompts import build_tot_propose_prompt, build_tot_score_prompt
from agent.utils import extract_first_json, safe_json_loads

@dataclass
class ToTNode:
    thought: str
    score: float

def _tot_candidates(llm, task: str, parent: str, k: int) -> List[str]:
    raw = llm.complete(build_tot_propose_prompt(task, parent, k))
    js = safe_json_loads(extract_first_json(raw))
    # accept the pseudo-tool candidates structure
    cands = (js.get("args") or {}).get("candidates") if isinstance(js, dict) else None
    if not isinstance(cands, list) or len(cands) != k:
        raise ValueError("ToT did not return required candidates")
    return [str(c) for c in cands]

def _tot_score(llm, task: str, thought: str) -> float:
    raw = llm.complete(build_tot_score_prompt(task, thought))
    js = safe_json_loads(extract_first_json(raw))
    score = (js.get("args") or {}).get("score")
    if not isinstance(score, (int, float)):
        raise ValueError("ToT score missing")
    s = float(score)
    return max(0.0, min(1.0, s))

def bounded_tot_best_thought(llm, task: str, node_budget: int, branching: int, seed: int) -> ToTNode:
    rng = random.Random(seed)
    best = ToTNode(thought="(start)", score=0.0)
    frontier: List[ToTNode] = [best]
    budget = node_budget

    while budget > 0:
        # expand the current best
        frontier.sort(key=lambda n: n.score, reverse=True)
        parent = frontier[0].thought
        k = branching
        cands = _tot_candidates(llm, task, parent, k)
        for th in cands:
            sc = _tot_score(llm, task, th)
            node = ToTNode(thought=th, score=sc)
            frontier.append(node)
            if sc > best.score:
                best = node
            budget -= 1
            if budget <= 0:
                break

    return best
