"""
evals/runners/run_evals.py

Orchestrates the full eval pipeline:
  1. Loads card output fixtures
  2. Scores each against every rubric dimension (via LLM judge)
  3. Computes weighted overall score
  4. Saves results to reports/scores_history.json
  5. Prints a formatted report to stdout

Run:
    python evals/runners/run_evals.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make project root importable regardless of where we run from
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from evals.rubrics.card_rubric import CARD_RUBRIC, weighted_score
from evals.judges.llm_judge import score_dimension

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_PATH  = ROOT / "tests" / "fixtures" / "sample_outputs.json"
HISTORY_PATH   = ROOT / "reports" / "scores_history.json"

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
WARN_THRESHOLD  = 70   # Score below this → WARN
FAIL_THRESHOLD  = 55   # Score below this → FAIL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fixtures() -> list[dict]:
    with open(FIXTURES_PATH) as f:
        return json.load(f)


def load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return []


def save_history(history: list[dict]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def status_label(score: float) -> str:
    if score >= WARN_THRESHOLD:
        return "PASS"
    elif score >= FAIL_THRESHOLD:
        return "WARN"
    else:
        return "FAIL"


def status_icon(label: str) -> str:
    return {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[label]


# ---------------------------------------------------------------------------
# Core eval loop
# ---------------------------------------------------------------------------

def eval_fixture(fixture: dict) -> dict:
    """Run all rubric dimensions against one fixture. Returns scored result."""
    fid        = fixture["id"]
    label      = fixture["label"]
    prompt     = fixture["user_prompt"]
    output_obj = fixture["card_output"]

    # Combine message + visual description for judge context
    card_text = (
        f"CARD MESSAGE:\n{output_obj['message']}\n\n"
        f"VISUAL DESCRIPTION:\n{output_obj['visual_description']}"
    )

    print(f"\n{'='*60}")
    print(f"  Evaluating: {label}")
    print(f"{'='*60}")

    dimension_scores = {}
    dimension_reasons = {}

    for dim in CARD_RUBRIC:
        result = score_dimension(dim, prompt, card_text, fixture_key=fid)
        dimension_scores[dim.name] = result.score
        dimension_reasons[dim.name] = result.reason
        status = status_label(result.score)
        icon   = status_icon(status)
        print(f"  {icon} {dim.name:<22} {result.score:>3}/100   {result.reason}")

    overall = weighted_score(dimension_scores, CARD_RUBRIC)
    overall_status = status_label(overall)
    overall_icon   = status_icon(overall_status)

    print(f"\n  {overall_icon} OVERALL WEIGHTED SCORE:  {overall:.1f}/100  [{overall_status}]")

    return {
        "fixture_id":        fid,
        "label":             label,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "dimension_scores":  dimension_scores,
        "dimension_reasons": dimension_reasons,
        "overall_score":     round(overall, 2),
        "status":            overall_status,
    }


# ---------------------------------------------------------------------------
# Regression check
# ---------------------------------------------------------------------------

def check_regressions(current_run: list[dict], history: list[dict]) -> None:
    """Compare current run to last run and flag regressions."""
    if not history:
        print("\n  [INFO] No previous run found — regression check skipped.")
        return

    # Build lookup of last run by fixture_id
    last_run_results = {}
    for run in reversed(history):
        for result in run.get("results", []):
            fid = result["fixture_id"]
            if fid not in last_run_results:
                last_run_results[fid] = result

    print(f"\n{'='*60}")
    print("  REGRESSION CHECK vs previous run")
    print(f"{'='*60}")

    regressions_found = False

    for result in current_run:
        fid = result["fixture_id"]
        if fid not in last_run_results:
            print(f"  [NEW]  {fid} — no previous data to compare")
            continue

        prev = last_run_results[fid]
        for dim_name, curr_score in result["dimension_scores"].items():
            prev_score = prev["dimension_scores"].get(dim_name, curr_score)
            delta = curr_score - prev_score

            if delta <= -15:
                print(f"  ❌ REGRESSION  {fid} / {dim_name}: {prev_score} → {curr_score}  (Δ {delta})")
                regressions_found = True
            elif delta <= -5:
                print(f"  ⚠️  DEGRADED   {fid} / {dim_name}: {prev_score} → {curr_score}  (Δ {delta})")
                regressions_found = True
            elif delta >= 5:
                print(f"  📈 IMPROVED   {fid} / {dim_name}: {prev_score} → {curr_score}  (Δ +{delta})")

    if not regressions_found:
        print("  ✅ No regressions detected.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("\n" + "🃏 " * 20)
    print("  STAMPY AI EVAL RUNNER")
    mode = "LIVE (Anthropic API)" if os.getenv("USE_LIVE_JUDGE") == "true" else "MOCK (offline)"
    print(f"  Mode: {mode}")
    print("🃏 " * 20)

    fixtures    = load_fixtures()
    history     = load_history()
    current_run = []

    for fixture in fixtures:
        result = eval_fixture(fixture)
        current_run.append(result)

    check_regressions(current_run, history)

    # Persist
    history.append({
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "results": current_run,
    })
    save_history(history)

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for r in current_run:
        icon = status_icon(r["status"])
        print(f"  {icon} {r['label']:<45} {r['overall_score']:>5.1f}/100")

    print(f"\n  Results saved → {HISTORY_PATH.relative_to(ROOT)}")
    print()


if __name__ == "__main__":
    main()
