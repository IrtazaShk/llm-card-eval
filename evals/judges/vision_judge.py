"""
evals/judges/vision_judge.py

Multimodal LLM-as-judge: scores an ACTUAL CARD IMAGE using Gemini Vision.
Uses the new `google-genai` SDK (the old google-generativeai is deprecated).

Requires GEMINI_API_KEY in .env. Get a free key at https://aistudio.google.com
"""

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

_client = None
if GEMINI_API_KEY:
    _client = genai.Client(api_key=GEMINI_API_KEY)


@dataclass
class VisionJudgeResult:
    dimension: str
    score: int
    reason: str
    mode: str  # "live" | "error"


VISION_DIMENSIONS = {
    "aesthetic_quality": (
        "Score AESTHETIC QUALITY from 0 to 100. Consider composition, balance, "
        "use of whitespace, and overall visual polish. "
        "90-100: Professional, polished, well-composed. "
        "70-89: Good but minor composition issues. "
        "50-69: Noticeably rough or unbalanced. "
        "0-49: Poor composition, looks unfinished or cluttered."
    ),
    "style_coherence": (
        "Score STYLE COHERENCE from 0 to 100. Do the colour palette, imagery, "
        "typography style, and layout all feel like they belong to one unified design? "
        "90-100: Fully cohesive single aesthetic. "
        "70-89: Mostly coherent, one element slightly out of place. "
        "50-69: Visible clash between style elements. "
        "0-49: Disjointed, looks like multiple unrelated styles combined."
    ),
    "occasion_match": (
        "Score OCCASION MATCH from 0 to 100. Does the visual design (colours, "
        "imagery, mood) appropriately match the stated occasion? "
        "90-100: Visual mood perfectly fits the occasion. "
        "70-89: Mostly fits, minor mismatch. "
        "50-69: Visual tone partially mismatched to occasion. "
        "0-49: Visual mood actively contradicts the occasion (e.g. cheerful colours for a sympathy card)."
    ),
}


def _build_prompt(dimension_key: str, occasion: str, user_prompt: str) -> str:
    instructions = VISION_DIMENSIONS[dimension_key]
    return (
        f"You are scoring a greeting card image for a quality eval system.\n\n"
        f"Occasion: {occasion}\n"
        f"Original user request: {user_prompt}\n\n"
        f"{instructions}\n\n"
        f'Return ONLY a JSON object on one line: {{"score": <int>, "reason": "<one sentence>"}}\n'
        f"No markdown, no code fences, no extra text."
    )


def _extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()
    return json.loads(cleaned)


def _guess_mime(image_path: str) -> str:
    ext = Path(image_path).suffix.lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def score_image_dimension(image_path: str, dimension_key: str, occasion: str, user_prompt: str) -> VisionJudgeResult:
    if not GEMINI_API_KEY or _client is None:
        return VisionJudgeResult(
            dimension=dimension_key,
            score=0,
            reason="GEMINI_API_KEY not set — add it to .env to run live vision evals.",
            mode="error",
        )

    if not Path(image_path).exists():
        return VisionJudgeResult(
            dimension=dimension_key,
            score=0,
            reason=f"Image not found at {image_path}",
            mode="error",
        )

    try:
        prompt = _build_prompt(dimension_key, occasion, user_prompt)
        image_bytes = Path(image_path).read_bytes()

        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=_guess_mime(image_path)),
                prompt,
            ],
        )

        parsed = _extract_json(response.text)

        return VisionJudgeResult(
            dimension=dimension_key,
            score=int(parsed["score"]),
            reason=parsed["reason"],
            mode="live",
        )

    except Exception as e:
        return VisionJudgeResult(
            dimension=dimension_key,
            score=0,
            reason=f"Vision judge error: {e}",
            mode="error",
        )


def score_image(image_path: str, occasion: str, user_prompt: str) -> list[VisionJudgeResult]:
    results = []
    for i, dim_key in enumerate(VISION_DIMENSIONS):
        if i > 0:
            time.sleep(13)  # free tier: there is a limit of 5 requests/min, so 12s delay between calls is safe
        result = score_image_dimension(image_path, dim_key, occasion, user_prompt)
        results.append(result)
    return results


if __name__ == "__main__":
    test_image = "tests/fixtures/images/birthday_card.jpg"
    results = score_image(
        image_path=test_image,
        occasion="birthday",
        user_prompt="A warm birthday card with sunflowers for someone who loves travel",
    )
    for r in results:
        print(f"{r.dimension}: {r.score}/100 — {r.reason} [{r.mode}]")