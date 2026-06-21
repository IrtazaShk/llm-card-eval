"""
reports/regression_tracker.py

Reads scores_history.json and prints a trend report showing how each
fixture + dimension has moved across all eval runs.

Run:
    python reports/regression_tracker.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HISTORY_PATH = ROOT / "reports" / "scores_history.json"

DIMENSIONS = ["prompt_fidelity", "text_accuracy", "tone_consistency", "style_coherence"]


def load_history():
    if not HISTORY_PATH.exists():
        print("No history found. Run the eval runner first:")
        print("  python evals/runners/run_evals.py")
        sys.exit(0)
    with open(HISTORY_PATH) as f:
        return json.load(f)


def delta_arrow(delta: float) -> str:
    if delta > 5:   return f"↑{delta:+.0f}"
    if delta < -5:  return f"↓{delta:+.0f}"
    return "  —  "


def print_trend_table(history: list[dict]) -> None:
    """Print a table of scores per fixture × dimension across runs."""
    # Collect all fixture IDs (preserve order from first run)
    fixture_ids = []
    for run in history:
        for result in run.get("results", []):
            if result["fixture_id"] not in fixture_ids:
                fixture_ids.append(result["fixture_id"])

    run_labels = [r["run_timestamp"][:16].replace("T", " ") for r in history]

    for fid in fixture_ids:
        # Get label from any run
        label = fid
        for run in history:
            for r in run.get("results", []):
                if r["fixture_id"] == fid:
                    label = r["label"]
                    break

        print(f"\n{'─'*70}")
        print(f"  {label}")
        print(f"{'─'*70}")

        header = f"  {'Dimension':<24}" + "".join(f"  Run {i+1:>2}" for i in range(len(history)))
        print(header)

        for dim in DIMENSIONS:
            row = f"  {dim:<24}"
            prev_score = None
            for run in history:
                score = None
                for r in run.get("results", []):
                    if r["fixture_id"] == fid:
                        score = r["dimension_scores"].get(dim)
                        break

                if score is None:
                    row += "      —"
                else:
                    flag = ""
                    if prev_score is not None:
                        delta = score - prev_score
                        if delta <= -15:  flag = " ❌"
                        elif delta <= -5: flag = " ⚠️"
                        elif delta >= 5:  flag = " 📈"
                    row += f"    {score:>3}{flag}"
                    prev_score = score

            print(row)

        # Overall row
        row = f"  {'OVERALL':<24}"
        prev_overall = None
        for run in history:
            overall = None
            for r in run.get("results", []):
                if r["fixture_id"] == fid:
                    overall = r["overall_score"]
                    break
            if overall is None:
                row += "      —"
            else:
                flag = ""
                if prev_overall is not None:
                    delta = overall - prev_overall
                    if delta <= -15:  flag = " ❌"
                    elif delta <= -5: flag = " ⚠️"
                    elif delta >= 5:  flag = " 📈"
                row += f"  {overall:>5.1f}{flag}"
                prev_overall = overall
        print(f"  {'─'*24}")
        print(row)


def print_regression_summary(history: list[dict]) -> None:
    """Surface any dimension that regressed in the most recent run."""
    if len(history) < 2:
        print("\n  Only one run in history — nothing to compare yet.")
        return

    prev_run = history[-2]
    curr_run = history[-1]

    prev_map: dict[str, dict] = {}
    for r in prev_run.get("results", []):
        prev_map[r["fixture_id"]] = r

    print(f"\n{'='*70}")
    print("  REGRESSIONS IN LATEST RUN")
    print(f"{'='*70}")

    found = False
    for r in curr_run.get("results", []):
        fid = r["fixture_id"]
        if fid not in prev_map:
            continue
        for dim in DIMENSIONS:
            curr_score = r["dimension_scores"].get(dim, 100)
            prev_score = prev_map[fid]["dimension_scores"].get(dim, 100)
            delta = curr_score - prev_score
            if delta <= -15:
                print(f"  ❌ HARD REGRESSION  {fid} / {dim}: {prev_score} → {curr_score}")
                found = True
            elif delta <= -5:
                print(f"  ⚠️  SOFT REGRESSION  {fid} / {dim}: {prev_score} → {curr_score}")
                found = True

    if not found:
        print("  ✅ No regressions in latest run.")


def main():
    history = load_history()
    total_runs = len(history)

    print(f"\n{'🃏 '*20}")
    print(f"  STAMPY EVAL REGRESSION TRACKER  ({total_runs} run{'s' if total_runs != 1 else ''} in history)")
    print(f"{'🃏 '*20}")

    print_trend_table(history)
    print_regression_summary(history)
    print()


if __name__ == "__main__":
    main()
