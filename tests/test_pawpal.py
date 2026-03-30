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
