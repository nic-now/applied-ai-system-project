#test pawpal
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pawpal_system import Owner, Pet, Task, Schedule


# --- Helpers ---

def make_task(name="Walk", duration=30, priority=1):
    return Task(name=name, category="walk", duration_mins=duration, priority=priority, frequency="daily")

def make_pet(name="Mochi"):
    return Pet(name=name, species="Dog", breed="Shiba Inu")

def make_owner(time=60):
    return Owner(name="Jane", time_available_mins=time)


# Task Completion: Verify that calling mark_complete() actually changes the task's status.

def test_mark_complete_sets_completed_true():
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True

def test_reset_sets_completed_false():
    task = make_task()
    task.mark_complete()
    task.reset()
    assert task.completed is False


# Task Addition: Verify that adding a task to a Pet increases that pet's task count.

def test_add_task_increases_pet_task_count():
    pet = make_pet()
    assert len(pet.tasks) == 0
    pet.add_task(make_task("Walk"))
    pet.add_task(make_task("Feeding"))
    assert len(pet.tasks) == 2

def test_add_task_stamps_pet_name():
    pet = make_pet("Luna")
    task = make_task("Brushing")
    pet.add_task(task)
    assert task.pet_name == "Luna"


# Schedule respects time budget: tasks that don't fit should be skipped.

def test_schedule_does_not_exceed_time_budget():
    owner = make_owner(time=40)
    pet = make_pet()
    pet.add_task(make_task("Walk", duration=30, priority=1))
    pet.add_task(make_task("Feeding", duration=15, priority=2))  # won't fit
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    assert schedule.total_duration() <= 40

def test_schedule_skips_tasks_that_dont_fit():
    owner = make_owner(time=30)
    pet = make_pet()
    pet.add_task(make_task("Walk", duration=30, priority=1))
    pet.add_task(make_task("Grooming", duration=20, priority=2))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    assert len(schedule.skipped_tasks) == 1
    assert schedule.skipped_tasks[0].name == "Grooming"


# Schedule prioritises by priority value: priority 1 beats priority 5 when time is scarce.

def test_schedule_prefers_higher_priority_tasks():
    owner = make_owner(time=30)
    pet = make_pet()
    pet.add_task(make_task("Low priority", duration=30, priority=5))
    pet.add_task(make_task("High priority", duration=30, priority=1))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    assert schedule.planned_tasks[0].name == "High priority"
    assert schedule.skipped_tasks[0].name == "Low priority"


# Owner time budget guard: Owner rejects zero or negative time.

def test_owner_rejects_zero_time():
    with pytest.raises(ValueError):
        Owner(name="Bad", time_available_mins=0)

def test_owner_rejects_negative_time():
    with pytest.raises(ValueError):
        Owner(name="Bad", time_available_mins=-10)


# Sorting Correctness: Verify tasks are returned in chronological order.

def test_sort_by_time_returns_chronological_order():
    owner = make_owner(time=120)
    pet = make_pet()
    pet.add_task(Task(name="Evening Walk", category="walk", duration_mins=30, priority=1, frequency="daily", due_time="18:00"))
    pet.add_task(Task(name="Morning Meds", category="meds", duration_mins=10, priority=1, frequency="daily", due_time="08:00"))
    pet.add_task(Task(name="Noon Feeding", category="feeding", duration_mins=15, priority=1, frequency="daily", due_time="12:00"))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    sorted_tasks = schedule.sort_by_time()
    times = [t.due_time for t in sorted_tasks]
    assert times == ["08:00", "12:00", "18:00"]

def test_sort_by_time_tasks_without_due_time_go_last():
    owner = make_owner(time=120)
    pet = make_pet()
    pet.add_task(Task(name="Walk", category="walk", duration_mins=30, priority=1, frequency="daily", due_time="09:00"))
    pet.add_task(Task(name="Grooming", category="grooming", duration_mins=20, priority=2, frequency="daily"))  # no due_time
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    sorted_tasks = schedule.sort_by_time()
    assert sorted_tasks[0].name == "Walk"
    assert sorted_tasks[-1].due_time == ""


# Recurrence Logic: Confirm that marking a daily task complete creates a new task for the following day.

def test_daily_task_renewal_creates_next_day_task():
    from datetime import date, timedelta
    owner = make_owner(time=60)
    pet = make_pet()
    today = date.today()
    task = Task(name="Walk", category="walk", duration_mins=30, priority=1, frequency="daily", due_date=today)
    pet.add_task(task)
    owner.add_pet(pet)
    schedule = Schedule(owner)
    renewed = schedule.mark_task_complete("Walk", "Mochi")
    assert renewed is not None
    assert renewed.due_date == today + timedelta(days=1)
    assert renewed.name == "Walk"
    assert renewed.completed is False

def test_as_needed_task_does_not_renew():
    owner = make_owner(time=60)
    pet = make_pet()
    task = Task(name="Vet Visit", category="meds", duration_mins=60, priority=1, frequency="as needed")
    pet.add_task(task)
    owner.add_pet(pet)
    schedule = Schedule(owner)
    renewed = schedule.mark_task_complete("Vet Visit", "Mochi")
    assert renewed is None
    # Only the original (now completed) task should exist — no extra copy added
    assert len(pet.tasks) == 1

def test_renewed_task_excluded_from_todays_schedule():
    from datetime import date
    owner = make_owner(time=60)
    pet = make_pet()
    today = date.today()
    task = Task(name="Walk", category="walk", duration_mins=30, priority=1, frequency="daily", due_date=today)
    pet.add_task(task)
    owner.add_pet(pet)
    schedule = Schedule(owner)
    schedule.mark_task_complete("Walk", "Mochi")
    # Regenerate — renewed task is due tomorrow, so it should not appear today
    schedule.generate()
    planned_names = [t.name for t in schedule.planned_tasks]
    assert "Walk" not in planned_names


# Conflict Detection: Verify that the Scheduler flags duplicate times.

def test_conflict_detected_for_same_due_time():
    owner = make_owner(time=120)
    pet = make_pet()
    pet.add_task(Task(name="Meds", category="meds", duration_mins=10, priority=1, frequency="daily", due_time="08:00"))
    pet.add_task(Task(name="Feeding", category="feeding", duration_mins=15, priority=2, frequency="daily", due_time="08:00"))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    warnings = schedule.detect_conflicts()
    assert len(warnings) == 1
    assert "08:00" in warnings[0]

def test_no_conflict_for_different_times():
    owner = make_owner(time=120)
    pet = make_pet()
    pet.add_task(Task(name="Meds", category="meds", duration_mins=10, priority=1, frequency="daily", due_time="08:00"))
    pet.add_task(Task(name="Feeding", category="feeding", duration_mins=15, priority=2, frequency="daily", due_time="12:00"))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    assert schedule.detect_conflicts() == []

def test_no_conflict_for_tasks_without_due_time():
    owner = make_owner(time=120)
    pet = make_pet()
    # Two tasks with no due_time — should NOT be flagged as a conflict
    pet.add_task(Task(name="Walk", category="walk", duration_mins=30, priority=1, frequency="daily"))
    pet.add_task(Task(name="Grooming", category="grooming", duration_mins=20, priority=2, frequency="daily"))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    assert schedule.detect_conflicts() == []


# Happy Path: All tasks fit — nothing skipped, all tasks planned.

def test_all_tasks_planned_when_budget_is_sufficient():
    owner = make_owner(time=120)
    pet = make_pet()
    pet.add_task(make_task("Walk", duration=30, priority=1))
    pet.add_task(make_task("Feeding", duration=15, priority=2))
    pet.add_task(make_task("Meds", duration=10, priority=3))
    owner.add_pet(pet)
    schedule = Schedule(owner).generate()
    assert len(schedule.skipped_tasks) == 0
    assert len(schedule.planned_tasks) == 3


# Weekly Recurrence: Confirm that marking a weekly task complete creates a task 7 days out.

def test_weekly_task_renewal_creates_task_seven_days_out():
    from datetime import date, timedelta
    owner = make_owner(time=60)
    pet = make_pet()
    today = date.today()
    task = Task(name="Bath", category="grooming", duration_mins=30, priority=2, frequency="weekly", due_date=today)
    pet.add_task(task)
    owner.add_pet(pet)
    schedule = Schedule(owner)
    renewed = schedule.mark_task_complete("Bath", "Mochi")
    assert renewed is not None
    assert renewed.due_date == today + timedelta(weeks=1)


# Remove guards: remove_task and remove_pet raise ValueError when the name is not found.

def test_remove_task_raises_for_missing_task():
    pet = make_pet()
    pet.add_task(make_task("Walk"))
    with pytest.raises(ValueError):
        pet.remove_task("Nonexistent Task")

def test_remove_pet_raises_for_missing_pet():
    owner = make_owner()
    owner.add_pet(make_pet("Mochi"))
    with pytest.raises(ValueError):
        owner.remove_pet("Ghost")


# =============================================================================
# AI Advisor Tests (heuristic mode — no API key required)
# Mirrors previous class code for reliability harness pattern (Mod 5)
# All tests use MockClient so they run offline and deterministically
# =============================================================================

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ai_advisor import ScheduleAdvisorAgent, MockClient


def make_schedule_with_tasks(tasks, time=120):
    """Helper: build an Owner + Schedule with the given Task list already generated."""
    owner = make_owner(time=time)
    pet   = make_pet()
    for t in tasks:
        pet.add_task(t)
    owner.add_pet(pet)
    sched = Schedule(owner)
    sched.generate()
    return sched


# --- MockClient unit tests ---

def test_advisor_mock_flags_missing_feeding():
    """A schedule with no feeding task should trigger a High-severity issue."""
    mock = MockClient()
    context = {
        "planned_tasks": [{"name": "Walk", "category": "walk", "duration_mins": 30,
                           "priority": 1, "pet_name": "Mochi", "mandatory": False, "frequency": "daily"}],
        "skipped_tasks": [],
        "pets": [{"name": "Mochi", "species": "Dog", "breed": "Shiba Inu"}],
        "total_planned_mins": 30,
        "time_budget_mins": 120,
    }
    issues = mock.analyze(context)
    types_ = [i["type"] for i in issues]
    assert "Missing task" in types_
    high = [i for i in issues if i["severity"] == "High"]
    assert any("feeding" in i["msg"].lower() for i in high)


def test_advisor_mock_flags_dog_missing_walk():
    """A dog with no walk task should trigger a Medium-severity issue."""
    mock = MockClient()
    context = {
        "planned_tasks": [{"name": "Feeding", "category": "feeding", "duration_mins": 10,
                           "priority": 1, "pet_name": "Mochi", "mandatory": False, "frequency": "daily"}],
        "skipped_tasks": [],
        "pets": [{"name": "Mochi", "species": "Dog", "breed": "Shiba Inu"}],
        "total_planned_mins": 10,
        "time_budget_mins": 120,
    }
    issues = mock.analyze(context)
    medium = [i for i in issues if i["severity"] == "Medium"]
    assert any("walk" in i["msg"].lower() for i in medium)


def test_advisor_mock_flags_empty_schedule():
    """An empty schedule should trigger a High-severity 'Empty schedule' issue."""
    mock = MockClient()
    context = {
        "planned_tasks": [],
        "skipped_tasks": [],
        "pets": [{"name": "Mochi", "species": "Dog", "breed": "Shiba Inu"}],
        "total_planned_mins": 0,
        "time_budget_mins": 60,
    }
    issues = mock.analyze(context)
    assert any(i["type"] == "Empty schedule" for i in issues)


def test_advisor_mock_score_poor_for_high_severity_issues():
    """Multiple High-severity issues should produce a Poor quality score."""
    mock = MockClient()
    issues = [
        {"type": "Missing task",   "severity": "High",   "msg": "No feeding"},
        {"type": "Empty schedule", "severity": "High",   "msg": "No tasks"},
        {"type": "Low activity",   "severity": "Medium", "msg": "Too little time"},
    ]
    quality = mock.evaluate({}, issues)
    assert quality["score"] <= 39
    assert quality["level"] == "Poor"


def test_advisor_mock_score_excellent_for_no_issues():
    """Zero issues should produce a score of 100 and Excellent level."""
    mock = MockClient()
    quality = mock.evaluate({}, [])
    assert quality["score"] == 100
    assert quality["level"] == "Excellent"


def test_advisor_mock_flags_feeding_per_pet_not_globally():
    """If pet A has feeding but pet B doesn't, only pet B should be flagged — not 100/100."""
    mock = MockClient()
    context = {
        "planned_tasks": [
            {"name": "Walk",    "category": "walk",    "duration_mins": 30, "priority": 1,
             "pet_name": "Mochi", "mandatory": False, "frequency": "daily"},
            {"name": "Feeding", "category": "feeding", "duration_mins": 10, "priority": 1,
             "pet_name": "Mochi", "mandatory": True,  "frequency": "daily"},
            {"name": "Walk",    "category": "walk",    "duration_mins": 20, "priority": 1,
             "pet_name": "Luna",  "mandatory": False,  "frequency": "daily"},
        ],
        "skipped_tasks": [],
        "pets": [
            {"name": "Mochi", "species": "Dog", "breed": "Shiba Inu"},
            {"name": "Luna",  "species": "Dog", "breed": "Labrador"},
        ],
        "total_planned_mins": 60,
        "time_budget_mins": 120,
    }
    issues = mock.analyze(context)
    feeding_issues = [i for i in issues if "feeding" in i["msg"].lower()]
    assert len(feeding_issues) == 1
    assert "Luna" in feeding_issues[0]["msg"]
    assert "Mochi" not in feeding_issues[0]["msg"]
    quality = mock.evaluate(context, issues)
    assert quality["score"] < 100


def test_advisor_mock_suggests_add_feeding_when_missing():
    """MockClient.suggest should recommend adding a feeding task when it's absent."""
    mock = MockClient()
    issues = [{"type": "Missing task", "severity": "High",
               "msg": "Mochi has no feeding task scheduled — regular meals are essential."}]
    suggestions = mock.suggest({}, issues)
    assert any("feeding" in s["action"].lower() for s in suggestions)


# --- ScheduleAdvisorAgent integration tests (heuristic mode) ---

def test_advisor_agent_runs_full_pipeline():
    """ScheduleAdvisorAgent.run() should return all required keys."""
    sched  = make_schedule_with_tasks([make_task("Walk", 30, 1), make_task("Feeding", 15, 2)])
    agent  = ScheduleAdvisorAgent()
    result = agent.run(sched)
    assert "issues"      in result
    assert "suggestions" in result
    assert "quality"     in result
    assert "logs"        in result
    assert "mode"        in result


def test_advisor_agent_logs_all_five_steps():
    """Execution trace must contain entries for all five pipeline steps."""
    sched  = make_schedule_with_tasks([make_task("Walk", 30, 1)])
    agent  = ScheduleAdvisorAgent()
    result = agent.run(sched)
    steps  = {entry["step"] for entry in result["logs"]}
    assert steps >= {"PLAN", "ANALYZE", "SUGGEST", "EVALUATE", "REFLECT"}


def test_advisor_agent_quality_score_in_range():
    """Quality score must always be an integer between 0 and 100."""
    sched  = make_schedule_with_tasks([make_task("Walk", 30, 1)])
    agent  = ScheduleAdvisorAgent()
    result = agent.run(sched)
    score  = result["quality"]["score"]
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_advisor_agent_detects_issue_on_empty_schedule():
    """Agent should flag issues when the schedule has no planned tasks."""
    owner = make_owner(time=5)   # tiny budget — nothing fits
    pet   = make_pet()
    pet.add_task(make_task("Walk", 60, 1))
    owner.add_pet(pet)
    sched  = Schedule(owner)
    sched.generate()
    agent  = ScheduleAdvisorAgent()
    result = agent.run(sched)
    assert len(result["issues"]) > 0


# --- Evaluation harness: run all advisor scenarios and print a summary ---
# Run with: python -m pytest tests/test_pawpal.py -v -k "advisor"

EVAL_CASES = [
    {
        "label": "Complete schedule (walk + feeding)",
        "tasks": [make_task("Walk", 30, 1), Task(name="Feeding", category="feeding",
                   duration_mins=15, priority=2, frequency="daily")],
        "time":  120,
        "expect_max_issues": 1,
    },
    {
        "label": "Missing feeding only",
        "tasks": [make_task("Walk", 30, 1)],
        "time":  60,
        "expect_max_issues": 2,
    },
    {
        "label": "Empty schedule (budget too small)",
        "tasks": [make_task("Walk", 90, 1)],
        "time":  10,
        "expect_max_issues": 3,
    },
]


def test_evaluation_harness_summary(capsys):
    """
    Evaluation harness: runs the advisor on multiple scenarios and prints a
    pass/fail summary with confidence scores. Mirrors the reliability harness
    described in the CodePath Module 5 rubric.
    """
    passed = 0
    total  = len(EVAL_CASES)

    for case in EVAL_CASES:
        owner = make_owner(time=case["time"])
        pet   = make_pet()
        for t in case["tasks"]:
            pet.add_task(t)
        owner.add_pet(pet)
        sched  = Schedule(owner)
        sched.generate()
        agent  = ScheduleAdvisorAgent()
        result = agent.run(sched)

        n_issues = len(result["issues"])
        score    = result["quality"]["score"]
        ok       = n_issues <= case["expect_max_issues"]
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {case['label']} — {n_issues} issue(s), score {score}/100")

    print(f"\n  Evaluation harness: {passed}/{total} cases passed")
    assert passed == total, f"Only {passed}/{total} evaluation cases passed"
