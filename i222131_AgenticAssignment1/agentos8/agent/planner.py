from __future__ import annotations
import json, time
from typing import Any, Dict, List
from agent.prompts import build_plan_prompt, build_react_prompt
from agent.utils import extract_first_json, safe_json_loads
from agent.protocol import is_valid_action
from agent.safety import sanitize_observation
from agent.reflect import repair_action

def _get_plan(llm, task: str, n_steps: int) -> List[str]:
    raw = llm.complete(build_plan_prompt(task, n_steps))
    js = safe_json_loads(extract_first_json(raw))
    if not is_valid_action(js) or js.get("type") != "plan" or len(js["steps"]) != n_steps:
        raise ValueError("Planner did not return a valid plan of required length")
    return [s.strip() for s in js["steps"]]

def run_plan_execute(llm, task: str, registry, memory, logger, cfg) -> Dict[str, Any]:
    scratch = ""
    tool_names = registry.list_names()

    plan = _get_plan(llm, task, cfg.plan_steps)
    replans = 0
    step_counter = 0

    for i, step_text in enumerate(plan, 1):
        # Use the same JSON tool/final protocol during execution via ReAct-style prompts
        # but include the current plan step in the task context.
        subtask = f"{task}\n\nCURRENT PLAN STEP ({i}/{len(plan)}): {step_text}"
        while True:
            step_counter += 1
            if step_counter > cfg.max_steps:
                return {"final": "FAILED: max_steps exceeded", "confidence": 0.0, "steps": cfg.max_steps, "mode": "plan"}

            mem_snip = json.dumps(memory.recent(4), ensure_ascii=False)
            prompt = build_react_prompt(subtask, tool_names, scratch, mem_snip)
            raw = llm.complete(prompt)

            try:
                js = safe_json_loads(extract_first_json(raw))
                if not is_valid_action(js) or js.get("type") in ("plan",):
                    raise ValueError("Invalid action schema in plan execution")
            except Exception as e:
                js = repair_action(llm, subtask, raw, str(e))

            if js["type"] == "final":
                logger.log({"mode":"plan","step":step_counter,"action":js,"obs":"","scratch_hash":__import__("agent.logging").logging.state_hash(scratch)})
                return {"final": js["answer"], "confidence": float(js["confidence"]), "steps": step_counter, "mode": "plan"}

            try:
                obs = registry.run(js["name"], js["args"])
            except Exception as e:
                obs = f"[tool_error] {type(e).__name__}: {e}"

            obs_safe = sanitize_observation(obs)
            scratch += f"\nPLANSTEP {i}\nACTION={json.dumps(js, ensure_ascii=False)}\nOBS={obs_safe}\n"
            memory.add({"plan_step": i, "action": js, "obs": obs_safe})
            logger.log({"mode":"plan","step":step_counter,"action":js,"obs":obs,"scratch_hash":__import__("agent.logging").logging.state_hash(scratch)})

            # If we hit a tool error, allow a single replan for the whole task
            if obs.startswith("[tool_error]") and replans < cfg.max_replans:
                replans += 1
                plan = _get_plan(llm, task + "\n\nNOTE: previous plan encountered tool error; revise.", cfg.plan_steps)
                break  # restart outer loop with new plan
            # Otherwise continue within this plan step until it moves forward (model decides)
            # This loop intentionally doesn't force "one tool per plan step".
