"""
evals/runners/run_vision_evals.py
Runs the multimodal vision eval across all card images in
tests/fixtures/images/. Requires GEMINI_API_KEY from the .env file
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from evals.judges.vision_judge import score_image

IMAGES_DIR = ROOT / "tests" / "fixtures" / "images"

IMAGE_FIXTURES = {
    "birthday_card.jpg": (
        "birthday",
        "A warm birthday card with sunflowers for someone who loves travel",
    ),
    "sympathy_card.jpg": (
        "sympathy",
        "A gentle, comforting sympathy card for someone who lost a parent",
    ),
    "wedding_card.jpg": (
        "wedding",
        "A heartfelt wedding card for a couple who loves hiking and the outdoors",
    ),
}


def status_label(score: float) -> str:
    if score >= 70:
        return "PASS"
    elif score >= 55:
        return "WARN"
    return "FAIL"


def status_icon(label: str) -> str:
    return {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[label]


def main():
    print("\n" + "🎨 " * 20)
    print("  STAMPY VISION EVAL RUNNER (multimodal)")
    print("🎨 " * 20)

    if not IMAGES_DIR.exists() or not any(IMAGES_DIR.iterdir()):
        print(f"\n  No images found in {IMAGES_DIR.relative_to(ROOT)}")
        print("  Add birthday_card.jpg, sympathy_card.jpg, wedding_card.jpg to that folder.")
        return

    for filename, (occasion, prompt) in IMAGE_FIXTURES.items():
        image_path = IMAGES_DIR / filename
        if not image_path.exists():
            print(f"\n  [SKIP] {filename} not found")
            continue

        print(f"\n{'='*60}")
        print(f"  Evaluating: {filename}  (occasion: {occasion})")
        print(f"{'='*60}")

        results = score_image(str(image_path), occasion, prompt)

        scores = []
        for r in results:
            status = status_label(r.score)
            icon = status_icon(status)
            print(f"  {icon} {r.dimension:<20} {r.score:>3}/100   {r.reason}")
            if r.mode == "live":
                scores.append(r.score)

        if scores:
            avg = sum(scores) / len(scores)
            overall_status = status_label(avg)
            icon = status_icon(overall_status)
            print(f"\n  {icon} VISION AVERAGE SCORE: {avg:.1f}/100  [{overall_status}]")

    print()


if __name__ == "__main__":
    main()