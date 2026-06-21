# Stampy AI Eval Demo

A structured LLM evaluation system for greeting card AI output — built to demonstrate rubric design, LLM-as-judge scoring, and regression tracking. Matches the HeartStamp stack (LangChain-style evals, Python).

> **No API key required.** Runs fully offline with mock LLM responses. Swap in a real `API_KEY` to use live judges.

---

## What this demos

| Capability | File |
|---|---|
| Eval rubric design | `evals/rubrics/card_rubric.py` |
| LLM-as-judge scoring | `evals/judges/llm_judge.py` |
| Batch eval runner | `evals/runners/run_evals.py` |
| Regression tracking | `reports/regression_tracker.py` |
| Sample card outputs | `tests/fixtures/sample_outputs.json` |

---

## Quickstart

```bash
# Install deps
pip install -r requirements.txt

# Run evals (mock mode, no API key needed)
python evals/runners/run_evals.py

# View regression report
python reports/regression_tracker.py
```

---

## Architecture

```
User prompt → Stampy (LLM) → Card output
                                    ↓
                            Eval Runner
                          /     |      \
                   Rubric   LLM Judge  Regex checks
                     ↓         ↓           ↓
                          Score aggregator
                                ↓
                       Regression tracker
                                ↓
                      Pass / Warn / FAIL report
```

---

## Rubric dimensions

| Dimension | Weight | What it checks |
|---|---|---|
| Prompt fidelity | 30% | Did the card match the user's request? |
| Text accuracy | 25% | Is the text grammatically correct and appropriate? |
| Tone consistency | 25% | Does tone match the occasion (birthday, sympathy, etc.)? |
| Style coherence | 20% | Is the visual/aesthetic description internally consistent? |

---

## Regression tracking

Scores are saved to `reports/scores_history.json` after every run. The tracker compares each dimension to the previous run and flags:

- 🟢 `PASS` — within threshold  
- 🟡 `WARN` — dropped > 5 points  
- 🔴 `FAIL` — dropped > 15 points or absolute score below 60
