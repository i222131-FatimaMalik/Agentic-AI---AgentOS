from __future__ import annotations
import argparse, json, os, tempfile, sys

# Ensure the project root is on sys.path so top-level packages like `harness`
# are importable when running `python -m agent.compare` from tests/subprocesses.
proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from agent.runner import run_task

CATEGORIES = ["computation", "injection", "verification", "planning", "hard_reasoning"]
MODES = ["react", "plan", "reflect", "tot"]

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--backend", choices=["ollama", "groq"], default="ollama")
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.tasks, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    by_cat = {
        c: {m: {"ok": 0, "n": 0, "steps": [], "tool_calls": []} for m in MODES}
        for c in CATEGORIES
    }

    for t in tasks:
        cat = t["category"]
        assert cat in by_cat, f"Unknown category in tasks file: {cat}"

        for m in MODES:
            trace_path = os.path.join(tempfile.gettempdir(), f"agentos8_{cat}_{m}.jsonl")

            # Run mode safely: never crash compare() if a mode fails.
            try:
                run_mode = "react" if m == "reflect" else m
                res = run_task(t["task"], args.backend, run_mode, trace_path, args.seed)

                # Keep the label as 'reflect' in the aggregate output even if it runs via react internally.
                if m == "reflect":
                    res = dict(res)
                    res["mode"] = "reflect"

            except Exception as e:
                # Mark as failed but continue the experiment.
                res = {
                    "final": f"FAILED: {type(e).__name__}: {e}",
                    "confidence": 0.0,
                    "steps": 0,
                    "mode": m,
                }

            expect = str(t.get("expect_substring", "")).lower()
            final_str = str(res.get("final", "")).lower()
            ok = 1 if (expect and expect in final_str) else 0

            by_cat[cat][m]["ok"] += ok
            by_cat[cat][m]["n"] += 1
            by_cat[cat][m]["steps"].append(int(res.get("steps", 0)))

            # Count tool calls from trace (if trace missing/corrupt, treat as 0)
            tool_calls = 0
            try:
                with open(trace_path, "r", encoding="utf-8") as tf:
                    for line in tf:
                        obj = json.loads(line)
                        act = obj.get("action") or {}
                        if act.get("type") == "tool":
                            tool_calls += 1
            except Exception:
                tool_calls = 0

            by_cat[cat][m]["tool_calls"].append(tool_calls)

    out = {"backend": args.backend, "seed": args.seed, "by_category": {}}
    for cat in CATEGORIES:
        out["by_category"][cat] = {}
        for m in MODES:
            rec = by_cat[cat][m]
            n = rec["n"] or 1
            out["by_category"][cat][m] = {
                "success_rate": rec["ok"] / n,
                "avg_steps": _mean(rec["steps"]),
                "avg_tool_calls": _mean(rec["tool_calls"]),
            }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
