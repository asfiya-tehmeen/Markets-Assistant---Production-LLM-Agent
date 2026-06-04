"""Evaluation harness + CI regression gate for the Markets Assistant agent.

Runs every case in ``golden_set.jsonl`` through the real agent (in-process, no HTTP server) and
scores the structured response with deterministic checks (see ``scoring.py``). Prints a per-case
result and a category breakdown, writes a JSON report, and exits non-zero when the overall pass
rate falls below ``--threshold`` so it can gate CI.

Usage:
    python eval/run_eval.py                      # full set, default threshold 0.85
    python eval/run_eval.py --threshold 0.9      # stricter gate
    python eval/run_eval.py --ids price-btc,kb-spread
    python eval/run_eval.py --max 5 --report eval/report.json

Requires the same env the app needs (GROQ_API_KEY etc.). Redis/Postgres are optional — the agent
degrades gracefully without them and the knowledge base self-seeds on first query.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make the backend package and this eval/ dir importable regardless of how the script is
# invoked (``python eval/run_eval.py`` or ``python -m eval.run_eval`` from the repo root).
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_HERE))

from scoring import score_case  # noqa: E402

_GOLDEN_DEFAULT = _ROOT / "eval" / "golden_set.jsonl"


def _load_cases(path: Path) -> list[dict]:
    cases = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{i}: invalid JSON — {exc}")
    return cases


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the Markets Assistant eval gate.")
    p.add_argument("--golden", type=Path, default=_GOLDEN_DEFAULT, help="Path to golden_set.jsonl")
    p.add_argument("--threshold", type=float, default=0.85,
                   help="Minimum pass rate (0..1) required for exit 0.")
    p.add_argument("--ids", type=str, default="", help="Comma-separated case ids to run (subset).")
    p.add_argument("--max", type=int, default=0, help="Run at most N cases (0 = all).")
    p.add_argument("--report", type=Path, default=None, help="Write a JSON report to this path.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.golden)

    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",") if s.strip()}
        cases = [c for c in cases if c["id"] in wanted]
    if args.max > 0:
        cases = cases[: args.max]
    if not cases:
        raise SystemExit("No cases to run.")

    # Imported here so --help / arg errors don't pay the LLM-client init cost.
    from app.agent.graph import run_agent

    results = []
    print(f"Running {len(cases)} eval cases (threshold {args.threshold:.0%})\n")
    for case in cases:
        started = time.perf_counter()
        try:
            response = run_agent(case["question"])
            failures = score_case(case.get("expect", {}), response)
        except Exception as exc:  # an exception is itself a failure, never a crash
            response = {"error": str(exc)}
            failures = [f"agent raised: {exc}"]
        elapsed = round((time.perf_counter() - started) * 1000)

        passed = not failures
        results.append({
            "id": case["id"], "category": case.get("category", "uncategorised"),
            "passed": passed, "failures": failures, "latency_ms": elapsed,
            "verdict": response.get("verdict"),
            "tools": (response.get("meta") or {}).get("tools_called"),
        })
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {case['id']:<22} {elapsed:>6}ms  verdict={response.get('verdict')}")
        for f in failures:
            print(f"         - {f}")

    total = len(results)
    passed_n = sum(r["passed"] for r in results)
    pass_rate = passed_n / total

    # Per-category breakdown.
    cats: dict[str, list[bool]] = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r["passed"])
    print("\nBy category:")
    for cat in sorted(cats):
        oks = cats[cat]
        print(f"  {cat:<16} {sum(oks)}/{len(oks)}")

    print(f"\nOverall: {passed_n}/{total} passed ({pass_rate:.1%}) — "
          f"gate threshold {args.threshold:.0%}")

    if args.report:
        report = {
            "total": total, "passed": passed_n, "pass_rate": round(pass_rate, 4),
            "threshold": args.threshold, "gate_passed": pass_rate >= args.threshold,
            "results": results,
        }
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written to {args.report}")

    if pass_rate < args.threshold:
        print("\nGATE FAILED: pass rate below threshold.")
        return 1
    print("\nGATE PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
