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
    return Owner(name="Nicole", time_available_mins=time)


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
