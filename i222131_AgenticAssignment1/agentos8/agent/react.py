from __future__ import annotations
import json, time
from typing import Any, Dict

from agent.prompts import build_react_prompt
from agent.utils import extract_first_json, safe_json_loads
from agent.protocol import is_valid_action
from agent.safety import sanitize_observation
from agent.reflect import repair_action


def parse_or_repair_action(llm, task: str, raw, cfg) -> dict:
    """
    Robustly obtain a valid action dict from the model output.
    Accepts raw output as str OR dict (some repair functions may return dict).
    """
    last_err = None
    cur = raw

    for _ in range(getattr(cfg, "reflection_max_rounds", 3)):
        # If repair_action returned a dict, validate directly
        if isinstance(cur, dict):
            js = cur
            if js.get("type") == "plan":
                last_err = "Plan action not allowed in react mode"
            elif is_valid_action(js):
                return js
            else:
                last_err = "Invalid action schema"
        else:
            # Assume string-like
            try:
                js_str = extract_first_json(str(cur))
                js = safe_json_loads(js_str)

                if js.get("type") == "plan":
                    last_err = "Plan action not allowed in react mode"
                elif is_valid_action(js):
                    return js
                else:
                    last_err = "Invalid action schema"
            except Exception as e:
                last_err = f"Parse error: {type(e).__name__}: {e}"

        # Ask reflection module to rewrite into a valid JSON action (may return str or dict)
        cur = repair_action(llm, task, cur, last_err)

    raise ValueError(f"Could not repair action: {last_err}")


def run_react(llm, task: str, registry, memory, logger, cfg) -> Dict[str, Any]:
    scratch = ""
    tool_names = registry.list_names()
    is_math_task = any(char in task for char in "+-*/()0123456789") and "compute" in task.lower()

    for step in range(1, cfg.max_steps + 1):
        mem_snip = json.dumps(memory.recent(4), ensure_ascii=False)
        prompt = build_react_prompt(task, tool_names, scratch, mem_snip)

        raw = llm.complete(prompt)

        # Always end up with a valid action dict (tool or final)
        try:
            js = parse_or_repair_action(llm, task, raw, cfg)
        except Exception as e:
            fail = {"type": "final", "answer": f"FAILED: {type(e).__name__}: {e}", "confidence": 0.0}
            logger.log({
                "mode": "react",
                "step": step,
                "action": fail,
                "obs": "",
                "scratch_hash": __import__("agent.logging").logging.state_hash(scratch),
            })
            return {"final": fail["answer"], "confidence": 0.0, "steps": step, "mode": "react"}

        # Force tool usage for math tasks
        if is_math_task and js["type"] == "final" and step == 1:
            error_msg = "Math computation tasks must use the calc tool. Do not give final answers without using tools."
            try:
                repaired = repair_action(llm, task, json.dumps(js), error_msg)
                if repaired and isinstance(repaired, dict) and repaired.get("type") == "tool" and repaired.get("name") == "calc":
                    js = repaired
                else:
                    # Force calc tool
                    expr = task.replace("Compute ", "").strip()
                    js = {"type": "tool", "name": "calc", "args": {"expression": expr}}
            except Exception:
                # Force calc
                expr = task.replace("Compute ", "").strip()
                js = {"type": "tool", "name": "calc", "args": {"expression": expr}}

        if js["type"] == "final":
            logger.log({
                "mode": "react",
                "step": step,
                "action": js,
                "obs": "",
                "scratch_hash": __import__("agent.logging").logging.state_hash(scratch),
            })
            return {"final": js["answer"], "confidence": float(js["confidence"]), "steps": step, "mode": "react"}

        # Tool validation: reject hallucinated tool names
        if js.get("type") == "tool":
            tool_name = js.get("name")
            if tool_name not in tool_names:
                # Tool doesn't exist - trigger reflection to fix the hallucination
                error_msg = f"Tool '{tool_name}' does not exist. Valid tools: {', '.join(tool_names)}"
                try:
                    js = repair_action(llm, task, json.dumps(js), error_msg)
                except Exception as e:
                    obs = f"[tool_error] Hallucinated tool '{tool_name}' and repair failed: {e}"
                    logger.log({
                        "mode": "react",
                        "step": step,
                        "action": {"type": "tool", "name": tool_name, "args": {}},
                        "obs": obs,
                        "scratch_hash": __import__("agent.logging").logging.state_hash(scratch),
                    })
                    scratch += f"\nSTEP {step}\nACTION=Tool error: {error_msg}\nOBS={obs}\n"
                    continue

        # Arg format repair: fix common mistake argument formats
        if js.get("type") == "tool" and js.get("name") == "calc":
            args = js.get("args", {})
            # Convert common wrong formats to correct format
            if "expr" in args and "expression" not in args:
                args["expression"] = args.pop("expr")
            elif "number1" in args and "number2" in args:
                # Convert {number1, number2, operation} format to expression
                n1 = args.get("number1", "0")
                n2 = args.get("number2", "0")
                op = args.get("operation", "+")
                args["expression"] = f"{n1}{op}{n2}"
                del args["number1"]
                del args["number2"]
                if "operation" in args:
                    del args["operation"]
            js["args"] = args

        # tool execution
        t0 = time.time()
        try:
            obs = registry.run(js["name"], js["args"])
        except Exception as e:
            obs = f"[tool_error] {type(e).__name__}: {e}"
        tool_ms = int((time.time() - t0) * 1000)

        obs_safe = sanitize_observation(obs)

        scratch += (
            f"\nSTEP {step}\n"
            f"ACTION={json.dumps(js, ensure_ascii=False)}\n"
            f"OBS={obs_safe}\n"
        )
        memory.add({"step": step, "action": js, "obs": obs_safe})

        logger.log({
            "mode": "react",
            "step": step,
            "action": js,
            "obs": obs,
            "tool_ms": tool_ms,
            "scratch_hash": __import__("agent.logging").logging.state_hash(scratch),
        })

        # For math tasks, if calc was used, return the result immediately
        if is_math_task and js["name"] == "calc" and not obs.startswith("[tool_error]"):
            return {"final": obs, "confidence": 0.95, "steps": step, "mode": "react"}

    return {"final": "FAILED: max_steps exceeded", "confidence": 0.0, "steps": cfg.max_steps, "mode": "react"}
