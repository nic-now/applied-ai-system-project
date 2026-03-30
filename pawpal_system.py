from dataclasses import dataclass, field
from datetime import date
from typing import List


@dataclass
class Task:
    name: str
    category: str          # e.g. "walk", "feeding", "meds", "grooming"
    duration_mins: int
    priority: int          # 1 = highest priority, 5 = lowest priority
    pet_name: str = ""     # which pet this task belongs to
    completed: bool = False


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet, stamping pet_name on the task."""
        pass

    def remove_task(self, task_name: str) -> None:
        """Remove a task by name."""
        pass


class Owner:
    def __init__(self, name: str, time_available_mins: int):
        if time_available_mins <= 0:
            raise ValueError("time_available_mins must be greater than 0")
        self.name = name
        self.time_available_mins = time_available_mins  # daily time budget in minutes
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        pass

    def get_all_tasks(self) -> List[Task]:
        """Return all tasks across all pets."""
        pass


class Schedule:
    def __init__(self, owner: Owner, schedule_date: date = None):
        self.owner = owner
        self.date = schedule_date or date.today()
        self.planned_tasks: List[Task] = []

    def generate(self) -> "Schedule":
        """Select and order tasks within the owner's time budget, sorted by priority.
        Priority approach: greedy by priority/ sort by priority/add tasks until time runs out"""
        pass

    def total_duration(self) -> int:
        """Return total minutes of all planned tasks."""
        pass

    def display(self) -> str:
        """Return a human-readable summary of the schedule."""
        pass
