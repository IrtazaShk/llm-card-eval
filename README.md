# LLM Card Eval

A structured eval pipeline for AI-generated greeting card output — text and visual. Built this to get hands-on with rubric design, LLM-as-judge scoring, and regression tracking for multimodal AI output, since most eval write-ups I found online only covered text.

> Text evals can run offline with mock responses without need of any API Key. Vision evals use the free Gemini API (real calls, real scores).

---

## What's in here

| Capability | File |
|---|---|
| Eval rubric design (text) | `evals/rubrics/card_rubric.py` |
| LLM-as-judge scoring (text) | `evals/judges/llm_judge.py` |
| **Vision/multimodal judge** | `evals/judges/vision_judge.py` |
| Batch eval runner (text) | `evals/runners/run_evals.py` |
| **Vision eval runner** | `evals/runners/run_vision_evals.py` |
| Regression tracking | `reports/regression_tracker.py` |
| Sample card outputs | `tests/fixtures/sample_outputs.json` |
| Sample card images | `tests/fixtures/images/` |

---

## Quickstart

```bash
# Install deps
pip install -r requirements.txt

# Run text evals (mock mode, no API key needed)
python evals/runners/run_evals.py

# View regression report
python reports/regression_tracker.py

# Run vision evals (needs a free Gemini key — see below)
python evals/runners/run_vision_evals.py
```

### Setting up the vision eval

1. Grab a free API key from [aistudio.google.com](https://aistudio.google.com)
2. Copy the example env file and add your key:
```bash
   cp .env.example .env
```
   Then open `.env` and replace the placeholder with your real `GEMINI_API_KEY`.
3. Drop 3 card images into `tests/fixtures/images/` named `birthday_card.jpg`, `sympathy_card.jpg`, `wedding_card.jpg`
4. Run the vision runner above

The free tier caps at 5 requests/minute, so the judge sleeps ~13s between calls — a full run of 3 images takes about 2 minutes.

---

## Architecture

**Text pipeline:**
```
User prompt → AI Model (LLM) → Card text output
                                      ↓
                              Eval Runner
                            /     |      \
                     Rubric   LLM Judge  Regex checks
                       ↓         ↓           ↓
                            Score aggregator
                                  ↓
                         Regression tracker
                                  ↓
                        Pass / Warn / Fail report
```

**Vision pipeline:**
```
Rendered card image → Vision Judge (Gemini)
                              ↓
            aesthetic_quality / style_coherence / occasion_match
                              ↓
                   Vision average score → Pass / Warn / Fail
```

The two run independently right now. Plugging the vision score into the overall weighted total instead of keeping it separate is the next thing I want to add.

---

## Rubric dimensions

### Text rubric

| Dimension | Weight | What it checks |
|---|---|---|
| Prompt fidelity | 30% | Did the card match the user's request? |
| Text accuracy | 25% | Is the text grammatically correct and appropriate? |
| Tone consistency | 25% | Does tone match the occasion (birthday, sympathy, etc.)? |
| Style coherence | 20% | Is the visual/aesthetic description internally consistent? |

### Vision rubric (multimodal)

| Dimension | What it checks |
|---|---|
| Aesthetic quality | Composition, balance, whitespace, overall polish |
| Style coherence | Do colour palette, imagery, and typography form one unified design? |
| Occasion match | Does the visual mood actually fit the occasion? (a cheerful palette on a sympathy card should score low here) |

---

## Regression tracking

Scores are saved to `reports/scores_history.json` after every text eval run. The file tracks 7 runs with consistent scores across all fixtures. The tracker compares each dimension to the previous run and flags:

- 🟢 `PASS` — within threshold
- 🟡 `WARN` — dropped > 5 points
- 🔴 `FAIL` — dropped > 15 points or absolute score below 60

---

## A note on the sympathy card fixture

It's deliberately a failure case — tone opens sympathetic, drifts cheerful by the closing line. The eval catches it (`tone_consistency` scores 38/100) even though the grammar and prompt fidelity are both fine. That's the actual point of running evals instead of spot-checking output: a generic "is this text okay" check would pass it. You can see this consistently flagged across all 7 runs in `reports/scores_history.json`.
