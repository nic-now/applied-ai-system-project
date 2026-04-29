"""
PawPal+ Schedule Advisor Agent
Multi-step agentic workflow: PLAN -> ANALYZE -> SUGGEST -> EVALUATE -> REFLECT

Follows the same architecture as class tinker (Week9):
- GeminiClient wraps the Google Gemini API (same interface as tinker, uses GeminiClient)
- MockClient provides offline heuristic fallback (no API key required)
- ScheduleAdvisorAgent orchestrates the multi-step pipeline
- Every step is logged so intermediate reasoning is observable
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ── Prompt loader (mirrors previous class prompts/ directory pattern) ─────────────

def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory next to this file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", f"{name}.txt")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.warning("Prompt file not found: %s — using empty string fallback", path)
        return ""


# ── LLM client abstractions (mirrors previous class MockClient / GeminiClient) ───

class MockClient:
    """
    Offline fallback — heuristic rule-based analysis with no API call.
    Used when GEMINI_API_KEY is not set or when the API call fails.
    Intentionally mirrors previous class MockClient role.
    """

    def complete(self, _system_prompt: str, _user_prompt: str) -> str:
        """Not used directly — MockClient uses analyze/suggest/evaluate methods instead."""
        return "[]"

    def analyze(self, context: Dict) -> List[Dict]:
        issues = []
        planned   = context.get("planned_tasks", [])
        skipped   = context.get("skipped_tasks", [])
        pets      = context.get("pets", [])
        total_min = context.get("total_planned_mins", 0)

        # Per-pet checks — mirrors how walk check already worked
        for pet in pets:
            pet_name  = pet["name"]
            pet_tasks = [t for t in planned if t.get("pet_name") == pet_name]
            pet_cats  = {t["category"] for t in pet_tasks}

            # Only flag missing feeding if the pet has at least one task scheduled
            if pet_tasks and "feeding" not in pet_cats:
                issues.append({
                    "type": "Missing task", "severity": "High",
                    "msg": f"{pet_name} has no feeding task scheduled — regular meals are essential."
                })

            if pet.get("species", "").lower() == "dog" and "walk" not in pet_cats:
                issues.append({
                    "type": "Missing task", "severity": "Medium",
                    "msg": f"{pet_name} is a dog with no walk scheduled — dogs need daily exercise."
                })

        if not planned:
            issues.append({
                "type": "Empty schedule", "severity": "High",
                "msg": "No tasks were scheduled. Check your time budget or add more tasks."
            })

        high_skipped = [t for t in skipped if t.get("priority", 5) <= 2]
        if high_skipped:
            names = ", ".join(t["name"] for t in high_skipped)
            issues.append({
                "type": "Budget overrun", "severity": "Medium",
                "msg": f"High-priority tasks skipped due to time constraints: {names}."
            })

        if 0 < total_min < 30 and planned:
            issues.append({
                "type": "Low activity", "severity": "Low",
                "msg": f"Only {total_min} min of care scheduled — pets benefit from more consistent daily attention."
            })

        return issues

    def suggest(self, context: Dict, issues: List[Dict]) -> List[Dict]:
        suggestions = []
        seen = set()

        for issue in issues:
            itype = issue["type"]
            imsg  = issue["msg"].lower()

            if "feeding" in imsg:
                pet_name = issue["msg"].split()[0]
                key = f"feeding_{pet_name}"
                if key not in seen:
                    seen.add(key)
                    suggestions.append({
                        "action": f"Add a 'Feeding' task for {pet_name} with priority 1 and mark it Mandatory",
                        "reason": "Regular feeding is the most critical pet care task and should never be skipped.",
                        "priority": "High"
                    })
            elif "walk" in imsg and "walk" not in seen:
                seen.add("walk")
                pet_name = issue["msg"].split()[0]
                suggestions.append({
                    "action": f"Add a 30-minute walk for {pet_name}",
                    "reason": "Daily walks support dogs' physical health, mental stimulation, and behaviour.",
                    "priority": "Medium"
                })
            elif itype == "Budget overrun" and "budget" not in seen:
                seen.add("budget")
                suggestions.append({
                    "action": "Increase your daily time budget or shorten lower-priority task durations",
                    "reason": "High-priority tasks are being skipped due to insufficient time.",
                    "priority": "High"
                })
            elif itype == "Empty schedule" and "empty" not in seen:
                seen.add("empty")
                suggestions.append({
                    "action": "Add at least one task per pet and set a time budget above 15 minutes",
                    "reason": "An empty schedule means your pet is receiving no tracked care today.",
                    "priority": "High"
                })
            elif itype == "Low activity" and "activity" not in seen:
                seen.add("activity")
                suggestions.append({
                    "action": "Aim for at least 60 minutes of total daily care",
                    "reason": "Consistent daily routines support pets' physical and emotional wellbeing.",
                    "priority": "Low"
                })

        if not suggestions:
            suggestions.append({
                "action": "Consider adding enrichment activities such as puzzle toys/feeders or training sessions",
                "reason": "Mental stimulation reduces stress, can reduce cognitive decline in older animals, strenghtens bonding, and prevents boredom-related behavioural issues.",
                "priority": "Low"
            })

        return suggestions

    def evaluate(self, context: Dict, issues: List[Dict]) -> Dict:
        score = 100
        for issue in issues:
            if issue["severity"] == "High":
                score -= 30
            elif issue["severity"] == "Medium":
                score -= 15
            else:
                score -= 5
        score = max(0, score)

        if score >= 80:
            level, summary = "Excellent", "Schedule covers all essential care areas — great job!"
        elif score >= 60:
            level, summary = "Good",      "Schedule is solid but has a few areas to improve."
        elif score >= 40:
            level, summary = "Fair",      "Schedule is missing some important care elements."
        else:
            level, summary = "Poor",      "Schedule needs significant improvements for your pet's wellbeing."

        return {"score": score, "level": level, "summary": summary}


class GeminiClient:
    """
    Google Gemini API client
    Uses system + user prompt separation and returns text to be parsed as JSON.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash", temperature: float = 0.2):
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai package not installed. Run: pip install google-genai")

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")

        self.client      = genai.Client(api_key=api_key)
        self._types      = types
        self.model_name  = model_name
        self.temperature = temperature

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a system + user prompt to Gemini and return the raw text response."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=self._types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=self.temperature
                )
            )
            return response.text or ""
        except Exception as e:
            logging.error("Gemini API error: %s", e)
            return ""

    def _parse_json_array(self, raw: str) -> Optional[list]:
        """
        Parse a JSON array from an LLM response.
        Handles cases where the model wraps output in markdown code fences.
        Mirrors previous class (BugHound) JSON parsing strategy.
        """
        if not raw:
            return None
        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Try extracting from ```json ... ``` fences
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try finding the first [ ... ] block
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def analyze(self, context: Dict) -> Optional[List[Dict]]:
        user   = _load_prompt("analyzer_user").replace("{{CONTEXT}}", json.dumps(context, indent=2))
        raw    = self.complete(_load_prompt("analyzer_system"), user)
        result = self._parse_json_array(raw)
        return result if isinstance(result, list) else None

    def suggest(self, context: Dict, issues: List[Dict]) -> Optional[List[Dict]]:
        user = (
            _load_prompt("suggester_user")
            .replace("{{CONTEXT}}", json.dumps(context, indent=2))
            .replace("{{ISSUES}}", json.dumps(issues, indent=2))
        )
        raw    = self.complete(_load_prompt("suggester_system"), user)
        result = self._parse_json_array(raw)
        return result if isinstance(result, list) else None


# ── Main agent ───────────────────────────────────────────────────────────────

class ScheduleAdvisorAgent:
    """
    Multi-step agentic advisor for PawPal+ schedules.

    Pipeline steps (observable intermediate reasoning):
      PLAN     — build serialisable context from the Schedule object
      ANALYZE  — identify issues (Gemini LLM or heuristics)
      SUGGEST  — propose actionable improvements (Gemini LLM or heuristics)
      EVALUATE — score schedule quality 0-100 (heuristic for reliability)
      REFLECT  — assemble and return the final result

    Falls back to MockClient automatically when no API key is set or on API failure.
    """

    def __init__(self):
        self.logs: List[Dict] = []
        self.client           = self._init_client()

    def _init_client(self):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        try:
            return GeminiClient()
        except (ValueError, ImportError) as e:
            logging.warning("No Gemini API key — using heuristic mode. (%s)", e)
            return MockClient()

    def _log(self, step: str, message: str) -> None:
        entry = {"step": step, "message": message}
        self.logs.append(entry)
        logging.info("[%s] %s", step, message)

    def _build_context(self, schedule) -> Dict:
        """Serialise a Schedule object into a plain dict for the LLM."""
        planned = [
            {
                "name":          t.name,
                "category":      t.category,
                "duration_mins": t.duration_mins,
                "priority":      t.priority,
                "pet_name":      t.pet_name,
                "mandatory":     t.mandatory,
                "frequency":     t.frequency,
            }
            for t in schedule.planned_tasks
        ]
        skipped = [
            {
                "name":          t.name,
                "category":      t.category,
                "duration_mins": t.duration_mins,
                "priority":      t.priority,
                "pet_name":      t.pet_name,
            }
            for t in schedule.skipped_tasks
        ]
        pets = [
            {"name": p.name, "species": p.species, "breed": p.breed}
            for p in schedule.owner.pets
        ]
        return {
            "owner_name":         schedule.owner.name,
            "time_budget_mins":   schedule.owner.time_available_mins,
            "total_planned_mins": schedule.total_duration(),
            "planned_tasks":      planned,
            "skipped_tasks":      skipped,
            "pets":               pets,
            "date":               str(schedule.date),
        }

    def run(self, schedule) -> Dict[str, Any]:
        """
        Run the full advisor pipeline against a Schedule object.

        Returns:
          issues       — list of dicts {type, severity, msg}
          suggestions  — list of dicts {action, reason, priority}
          quality      — dict {score, level, summary}
          logs         — agent execution trace [{step, message}, ...]
          mode         — 'Gemini AI' or 'Heuristic'
        """
        self.logs = []
        mock = MockClient()

        # ── PLAN ─────────────────────────────────────────────────────────────
        self._log("PLAN", f"Starting analysis for {schedule.owner.name}'s schedule on {schedule.date}")
        context = self._build_context(schedule)
        self._log("PLAN", (
            f"{len(context['planned_tasks'])} task(s) planned | "
            f"{len(context['skipped_tasks'])} skipped | "
            f"{context['total_planned_mins']}/{context['time_budget_mins']} min used"
        ))

        issues      = []
        suggestions = []
        mode        = "Heuristic"

        # ── ANALYZE ───────────────────────────────────────────────────────────
        self._log("ANALYZE", "Scanning schedule for issues...")
        if isinstance(self.client, GeminiClient):
            result = self.client.analyze(context)
            if result is not None:
                issues = result
                mode   = "Gemini AI"
                self._log("ANALYZE", f"Gemini found {len(issues)} issue(s)")
            else:
                self._log("ANALYZE", "Gemini returned no valid JSON — falling back to heuristics")
                issues = mock.analyze(context)
        else:
            issues = mock.analyze(context)
            self._log("ANALYZE", f"Heuristic found {len(issues)} issue(s)")

        # ── SUGGEST ───────────────────────────────────────────────────────────
        self._log("SUGGEST", "Generating improvement suggestions...")
        if isinstance(self.client, GeminiClient) and mode == "Gemini AI":
            result = self.client.suggest(context, issues)
            if result is not None:
                suggestions = result
                self._log("SUGGEST", f"Gemini generated {len(suggestions)} suggestion(s)")
            else:
                self._log("SUGGEST", "Gemini returned no valid JSON — falling back to heuristics")
                suggestions = mock.suggest(context, issues)
        else:
            suggestions = mock.suggest(context, issues)
            self._log("SUGGEST", f"Heuristic generated {len(suggestions)} suggestion(s)")

        # ── EVALUATE ──────────────────────────────────────────────────────────
        # Always use heuristic scoring for reliability (consistent, testable)
        self._log("EVALUATE", "Scoring schedule quality...")
        quality = mock.evaluate(context, issues)
        self._log("EVALUATE", f"Score: {quality['score']}/100 ({quality['level']})")

        # ── REFLECT ───────────────────────────────────────────────────────────
        self._log("REFLECT", (
            f"Analysis complete — {len(issues)} issue(s), "
            f"{len(suggestions)} suggestion(s), "
            f"score {quality['score']}/100"
        ))

        return {
            "issues":      issues,
            "suggestions": suggestions,
            "quality":     quality,
            "logs":        self.logs,
            "mode":        mode,
        }
