"""
evals/rubrics/card_rubric.py

Defines the evaluation rubric for Stampy AI greeting card output.
Each dimension has a weight, scoring criteria, and example anchors.

This rubric is used by:
  - The LLM-as-judge (llm_judge.py) for AI-scored dimensions
  - The rule-based checks in run_evals.py for deterministic dimensions
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RubricDimension:
    """A single scoring dimension in the rubric."""
    name: str
    weight: float           # Weights must sum to 1.0 across all dimensions
    description: str
    scoring_guide: dict     # score_band -> what it means
    judge_prompt: str       # Injected into LLM judge for this dimension
    deterministic: bool = False  # True = rule-based, False = LLM-scored


# ---------------------------------------------------------------------------
# Rubric definition
# ---------------------------------------------------------------------------

CARD_RUBRIC: list[RubricDimension] = [

    RubricDimension(
        name="prompt_fidelity",
        weight=0.30,
        description="Did the generated card faithfully fulfil the user's request?",
        scoring_guide={
            "90-100": "All key details present: recipient name, occasion, requested tone, any specifics mentioned.",
            "70-89":  "Most details present; one minor omission or slight drift from request.",
            "50-69":  "Core occasion correct but meaningful details missing or substituted.",
            "0-49":   "Card does not match the request in a material way.",
        },
        judge_prompt=(
            "You are evaluating an AI-generated greeting card against the original user prompt.\n"
            "Score PROMPT FIDELITY from 0 to 100.\n\n"
            "Rubric:\n"
            "  90-100: All key details honoured — recipient, occasion, tone, any specifics.\n"
            "  70-89:  Minor omission or slight tone drift.\n"
            "  50-69:  Core occasion correct but notable detail missing.\n"
            "  0-49:   Card materially fails to match the request.\n\n"
            "Return ONLY a JSON object: {{\"score\": <int>, \"reason\": \"<one sentence>\"}}"
        ),
    ),

    RubricDimension(
        name="text_accuracy",
        weight=0.25,
        description="Is the card text grammatically correct, appropriately spelled, and suitable to send?",
        scoring_guide={
            "90-100": "No grammar/spelling errors. Text reads naturally and is appropriate for the recipient.",
            "70-89":  "One minor error or slightly awkward phrasing.",
            "50-69":  "Multiple errors or one significant awkward passage.",
            "0-49":   "Contains errors that would embarrass the sender.",
        },
        judge_prompt=(
            "You are evaluating the text quality of an AI-generated greeting card.\n"
            "Score TEXT ACCURACY from 0 to 100.\n\n"
            "Rubric:\n"
            "  90-100: No grammar/spelling errors; text reads naturally and is appropriate to send.\n"
            "  70-89:  One minor error or mildly awkward phrase.\n"
            "  50-69:  Multiple errors or one passage that reads poorly.\n"
            "  0-49:   Errors that would embarrass a real sender.\n\n"
            "Return ONLY a JSON object: {{\"score\": <int>, \"reason\": \"<one sentence>\"}}"
        ),
    ),

    RubricDimension(
        name="tone_consistency",
        weight=0.25,
        description="Does the tone match the occasion throughout? (Birthday ≠ Sympathy ≠ Wedding etc.)",
        scoring_guide={
            "90-100": "Tone is perfectly calibrated to the occasion and sustained throughout.",
            "70-89":  "Tone correct overall; brief lapse or single off-note phrase.",
            "50-69":  "Partially correct tone with noticeable inconsistency.",
            "0-49":   "Tone is mismatched or shifts in a way that undermines the card.",
        },
        judge_prompt=(
            "You are evaluating whether an AI-generated greeting card maintains the right tone for its occasion.\n"
            "Score TONE CONSISTENCY from 0 to 100.\n\n"
            "Rubric:\n"
            "  90-100: Tone perfectly matches occasion (e.g. warm + celebratory for birthday) and is sustained.\n"
            "  70-89:  Correct overall tone with one brief off-note.\n"
            "  50-69:  Noticeable tonal inconsistency.\n"
            "  0-49:   Tone mismatched or shifts inappropriately.\n\n"
            "Return ONLY a JSON object: {{\"score\": <int>, \"reason\": \"<one sentence>\"}}"
        ),
    ),

    RubricDimension(
        name="style_coherence",
        weight=0.20,
        description=(
            "Is the described visual/aesthetic style internally consistent? "
            "(colour palette, imagery, layout cues should all fit together)"
        ),
        scoring_guide={
            "90-100": "Visual elements form a coherent, intentional aesthetic.",
            "70-89":  "Mostly coherent; one element feels slightly out of place.",
            "50-69":  "Mix of styles that clash or feel arbitrary.",
            "0-49":   "Visual description is incoherent or contradictory.",
        },
        judge_prompt=(
            "You are evaluating the visual/aesthetic coherence of an AI-generated greeting card description.\n"
            "Score STYLE COHERENCE from 0 to 100.\n\n"
            "Rubric:\n"
            "  90-100: Colour palette, imagery, and layout cues form a unified aesthetic.\n"
            "  70-89:  Mostly coherent; one element slightly out of place.\n"
            "  50-69:  Clashing or arbitrary mix of styles.\n"
            "  0-49:   Visual description is incoherent or self-contradictory.\n\n"
            "Return ONLY a JSON object: {{\"score\": <int>, \"reason\": \"<one sentence>\"}}"
        ),
    ),
]


def validate_rubric(rubric: list[RubricDimension]) -> None:
    """Sanity-check that weights sum to 1.0."""
    total = sum(d.weight for d in rubric)
    assert abs(total - 1.0) < 0.001, f"Rubric weights sum to {total}, expected 1.0"


def weighted_score(dimension_scores: dict[str, float], rubric: list[RubricDimension]) -> float:
    """
    Compute the overall weighted score from individual dimension scores.

    Args:
        dimension_scores: {"dimension_name": raw_score_0_to_100, ...}
        rubric: the rubric definitions (for weights)

    Returns:
        Weighted score 0-100
    """
    weight_map = {d.name: d.weight for d in rubric}
    return sum(dimension_scores[d] * weight_map[d] for d in dimension_scores if d in weight_map)


validate_rubric(CARD_RUBRIC)
