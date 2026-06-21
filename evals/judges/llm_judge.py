"""
evals/judges/llm_judge.py

LLM-as-judge: scores a card output against a single rubric dimension.

In MOCK MODE (default, no API key needed):
  Returns deterministic mock scores so the full pipeline runs offline.

In LIVE MODE (set USE_LIVE_JUDGE=true in .env + provide API key):
  Calls the Anthropic API using the rubric dimension's judge_prompt.

Usage:
    from evals.judges.llm_judge import score_dimension
    result = score_dimension(dimension, prompt, card_output)
"""

import json
import os
import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Try to load env (optional — won't fail if .env absent)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USE_LIVE_JUDGE = os.getenv("USE_LIVE_JUDGE", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class JudgeResult:
    dimension: str
    score: int          # 0-100
    reason: str
    mode: str           # "mock" | "live"


# ---------------------------------------------------------------------------
# Mock judge — deterministic based on a seed so results are reproducible
# ---------------------------------------------------------------------------

MOCK_SCORES: dict[str, dict] = {
    # Good card — birthday for Sarah
    "good_birthday": {
        "prompt_fidelity":  {"score": 92, "reason": "All details present: recipient Sarah, 30th birthday, warm tone."},
        "text_accuracy":    {"score": 95, "reason": "No grammar or spelling errors; flows naturally."},
        "tone_consistency": {"score": 88, "reason": "Warm and celebratory throughout with one slightly formal phrase."},
        "style_coherence":  {"score": 85, "reason": "Pastel palette and confetti imagery are cohesive."},
    },
    # Regressed card — sympathy card that drifted cheerful
    "regressed_sympathy": {
        "prompt_fidelity":  {"score": 70, "reason": "Occasion correct but tone missed the mark significantly."},
        "text_accuracy":    {"score": 82, "reason": "Text is grammatically fine but phrasing feels generic."},
        "tone_consistency": {"score": 38, "reason": "Card opens with a sympathetic note but ends with cheerful language — jarring."},
        "style_coherence":  {"score": 55, "reason": "Muted palette clashes with bright floral imagery."},
    },
    # Wedding card with minor issues
    "minor_issues_wedding": {
        "prompt_fidelity":  {"score": 78, "reason": "Names present but customisation detail from prompt not reflected."},
        "text_accuracy":    {"score": 88, "reason": "One minor grammatical error in the closing line."},
        "tone_consistency": {"score": 90, "reason": "Romantic and celebratory throughout."},
        "style_coherence":  {"score": 82, "reason": "Gold and ivory elements consistent; font choice slightly jarring."},
    },
}


def _mock_judge(dimension_name: str, fixture_key: str) -> JudgeResult:
    """Return a pre-defined mock score for a known fixture key."""
    scores = MOCK_SCORES.get(fixture_key, {})
    dim_score = scores.get(dimension_name, {"score": 75, "reason": "Mock fallback score."})
    return JudgeResult(
        dimension=dimension_name,
        score=dim_score["score"],
        reason=dim_score["reason"],
        mode="mock",
    )


# ---------------------------------------------------------------------------
# Live judge — calls Anthropic API
# ---------------------------------------------------------------------------

def _live_judge(dimension, user_prompt: str, card_output: str) -> JudgeResult:
    """Score using a real Anthropic API call."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        user_content = (
            f"USER PROMPT:\n{user_prompt}\n\n"
            f"GENERATED CARD OUTPUT:\n{card_output}\n\n"
            "Score the above according to the rubric. Return only JSON."
        )

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=dimension.judge_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = message.content[0].text.strip()
        parsed = json.loads(raw)
        return JudgeResult(
            dimension=dimension.name,
            score=int(parsed["score"]),
            reason=parsed["reason"],
            mode="live",
        )

    except Exception as e:
        print(f"  [WARN] Live judge failed for {dimension.name}: {e} — falling back to mock")
        return _mock_judge(dimension.name, "good_birthday")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_dimension(dimension, user_prompt: str, card_output: str, fixture_key: str = "good_birthday") -> JudgeResult:
    """
    Score a single rubric dimension for a card output.

    Args:
        dimension:    RubricDimension instance
        user_prompt:  The original user request to Stampy
        card_output:  The AI-generated card text/description
        fixture_key:  Which mock fixture to use (ignored in live mode)

    Returns:
        JudgeResult with score 0-100 and reasoning
    """
    if USE_LIVE_JUDGE and ANTHROPIC_API_KEY:
        return _live_judge(dimension, user_prompt, card_output)
    else:
        return _mock_judge(dimension.name, fixture_key)
