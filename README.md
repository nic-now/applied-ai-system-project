# PawPal+ — AI-Powered Pet Care Scheduler

> CodePath Applied AI — Final Project

**Loom walkthrough:** *[LINK]*

---

## Base Project

**Original project:** PawPal+

PawPal+ is a Streamlit web app that helps a busy pet owner plan and track daily care tasks for their pets. 
- The original system lets users register an owner, add pets, add care tasks (with name, category, duration, priority, and frequency), and generates a greedy priority-based schedule that fits within the owner's daily time budget. 
- It also handled mandatory tasks, conflict detection, and a Streamlit UI.

---

## Final Version: What's New

The final version adds an **AI Schedule Advisor**, an agentic workflow that analyzes the generated schedule, identifies care gaps, and suggests specific improvements. This feature is fully integrated into the Streamlit UI (step 5 of app).

The schedule advisor follows the same multi-step pipeline as Week 9 Tinker (BugHound) agent:

```
PLAN → ANALYZE → SUGGEST → EVALUATE → REFLECT
```

Every step is logged so the intermediate reasoning is visible in the UI's "Agent execution trace" panel.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)              │
│  Steps 1-4: Owner / Pet / Task / Schedule (existing) │
│  Step 5: AI Advisor button → ScheduleAdvisorAgent    │
└─────────────────────────┬────────────────────────────┘
                          │ Schedule object
                          ▼
┌──────────────────────────────────────────────────────┐
│           ScheduleAdvisorAgent  (ai_advisor.py)      │
│                                                      │
│  PLAN     build serialisable context dict            │
│  ANALYZE  identify issues (LLM or heuristics)        │
│  SUGGEST  propose improvements (LLM or heuristics)   │
│  EVALUATE score quality 0-100 (heuristic, reliable)  │
│  REFLECT  assemble result + log trace                │
└──────┬───────────────────────────┬───────────────────┘
       │ GEMINI_API_KEY set        │ no key / API error
       ▼                           ▼
┌─────────────┐           ┌────────────────┐
│ GeminiClient│           │  MockClient    │
│ (API key)   │           │  (heuristics)  │
└─────────────┘           └────────────────┘
       │
       ▼
  System prompt + user prompt → JSON response
  Parsed into issues / suggestions lists

┌──────────────────────────────────────────────────────┐
│                  Test Suite  (pytest)                │
│  test_pawpal.py  — scheduling logic (19 tests)       │
│                  — advisor heuristics (8 tests)      │
│                  — evaluation harness (1 harness)    │
└──────────────────────────────────────────────────────┘
```

The class diagram (PNG) can be seen in [assets/class-diagram.png](assets/class-diagram.png).

---

## Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/nic-now/applied-ai-system-project.git
cd applied-ai-system-final
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Add Gemini API key

The AI Advisor works offline with heuristics (no key needed) but can also work with an API key. To enable Gemini AI analysis:

```bash
cp .env.example .env
# then open .env and paste your GEMINI_API_KEY
```

### 5. Run the app

```bash
streamlit run app.py
```

### 6. Run tests

```bash
python -m pytest
# AI advisor tests only:
python -m pytest tests/test_pawpal.py -v -k "advisor"
```

---

## Sample Interactions

### Example 1: Well-covered schedule (Excellent)

**Input:** Jane, 120 min budget. Mochi (Dog). Tasks: Morning Walk 30 min pri 1, Feeding 15 min pri 2, Meds 10 min pri 1 mandatory.

**AI Advisor output:**
```
Schedule Quality: Excellent — 100/100
"Schedule covers all essential care areas — great job!"

No issues found.
Suggestion (Low): Consider adding enrichment activities such as puzzle toys or training sessions.
```

---

### Example 2: Missing feeding (Fair)

**Input:** Jane, 60 min budget. Mochi (Dog). Tasks: Morning Walk 30 min pri 1.

**AI Advisor output:**
```
Schedule Quality: Fair — 75/100
"Schedule is missing some important care elements."

🔴 High — No feeding task scheduled — regular meals are the most critical pet care need.
🟠 Medium — Mochi is a dog with no feeding scheduled.

Suggestion (High): Add a 'Feeding' task with priority 1 and mark it Mandatory.
Suggestion (Medium): Add a 30-minute walk for Mochi.
```

---

### Example 3: Empty schedule (Poor)

**Input:** Jane, 10 min budget. Mochi (Dog). Tasks: Morning Walk 60 min pri 1 (won't fit).

**AI Advisor output:**
```
Schedule Quality: Poor — 40/100
"Schedule needs significant improvements for your pet's wellbeing."

🔴 High — No tasks were scheduled. Check your time budget or add more tasks.
🟠 Medium — Mochi is a dog with no walk scheduled.
🟠 Medium — High-priority tasks skipped due to time constraints: Morning Walk.

Suggestion (High): Add at least one task per pet and set a time budget above 15 minutes.
```

---

## Design Decisions

**Why a multi-step pipeline instead of one big prompt?**
- Breaking the workflow into PLAN → ANALYZE → SUGGEST → EVALUATE → REFLECT makes each step's output observable in the trace log. 
- This mirrors (Week 9) previous example architecture and makes it easy to see where the agent's reasoning went wrong if results are unexpected.

**Why heuristic fallback?**
- LLMs can return malformed JSON or empty responses.
- Having a deterministic MockClient means the advisor always produces output, and the scoring step always uses heuristics so quality scores are consistent and testable.

**Why is EVALUATE always heuristic?**
- A score derived from counting issue severity is reproducible and predictable. 
- If the evaluate step used the LLM, the same schedule could get 70/100 one run and 85/100 the next, making tests meaningless.

**Why greedy scheduling?**
- The original scheduling algorithm was kept intentionally simple. 
- The AI Advisor handles a 'smarter' layer by flagging when the greedy result is suboptimal.

---

## Reliability & Guardrails

Two mechanisms keep the advisor from breaking:


**Evaluation harness:** `test_evaluate_harness` runs three scenarios (full schedule, missing feeding, empty schedule) and checks scores land in the right range. Because the EVALUATE step is always heuristic, scores are deterministic and the test results are reproducible.


**Guardrails in place:**
- The quality score is always heuristic , not LLM-generated, so it can't be inflated by a hallucinating model
- The fallback to MockClient means the app never crashes or returns nothing, even on API failure
- Issue severity is constrained to a fixed enum (`High / Medium / Low`) so the model called can't invent new categories
---

## Testing Summary

```
python -m pytest -v
```

| Test group | Tests | Notes |
|---|---|---|
| Scheduling logic | 19 | Time budget, priority, recurrence, conflicts |
| Advisor heuristics | 8 | MockClient analyze/suggest/evaluate |
| Evaluation harness | 1 | Runs 3 scenarios, prints pass/fail + scores |
| **Total** | **28** | All pass in heuristic mode (no API key needed) |


**What worked:** The heuristic rules correctly catch the most common care gaps (missing feeding, missing dog walk, empty schedule). The five-step log trace made it easy to debug which step was producing unexpected output.

**What didn't:** The Gemini model occasionally wraps JSON in markdown code fences despite the system prompt saying not to. The `_parse_json_array` fallback parser handles this in most cases, but very unusual formatting can still cause a fallback to heuristics.

**Confidence level: 4/5** — Core scheduling and advisor heuristics are well covered. AI-mode responses are tested manually rather than automatically because LLM output is non-deterministic.

---

## Reflection

- The main thing this project taught me is that building around the AI call can be harder than the AI call itself. Writing the fallback (MockClient here) first forced me to think clearly about what the agent actually needed to do, it meant the app had to work end to end before ever toucheing the API.

- The main limitation is that the Schedule advisor only sees what's in the schedule. It doesn't know the pet's age, health, or history, so suggestions are general. Adding a short pet profile to the context would make them much more useful.

---

## Overview of File Structure

```
applied-ai-system-final/
├── app.py                  # Streamlit UI (Steps 1-5)
├── pawpal_system.py        # Core classes: Owner, Pet, Task, Schedule
├── ai_advisor.py           # AI Advisor agent (new — Module 5)
├── main.py                 # CLI demo script
├── requirements.txt
├── .env.example            # Copy to .env and add GEMINI_API_KEY
├── tests/
│   └── test_pawpal.py      # pytest suite (scheduling + advisor)
├── assets/
│   └── class-diagram.png  # Class diagram 
├── model_card.md           # Reflection
└── README.md
```
