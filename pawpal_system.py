from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Task:
    """Represents a single pet care activity."""
    name: str
    category: str           # e.g. "walk", "feeding", "meds", "grooming"
    duration_mins: int
    priority: int           # 1 = highest priority, 5 = lowest priority
    frequency: str          # e.g. "daily", "weekly", "as needed"
    pet_name: str = ""      # stamped when added to a Pet
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def reset(self) -> None:
        """Reset completion status (e.g. start of a new day)."""
        self.completed = False

    def __str__(self) -> str:
        status = "done" if self.completed else "pending"
        return f"[{self.priority}] {self.name} ({self.duration_mins}min, {self.frequency}) — {status}"


@dataclass
class Pet:
    """Stores pet details and owns a list of care tasks."""
    name: str
    species: str
    breed: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task, stamping this pet's name onto the task."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        """Remove a task by name. Raises ValueError if not found."""
        match = self._find_task(task_name)
        if match is None:
            raise ValueError(f"Task '{task_name}' not found for {self.name}")
        self.tasks.remove(match)

    def get_pending_tasks(self) -> List[Task]:
        """Return only tasks not yet completed."""
        return [t for t in self.tasks if not t.completed]

    def _find_task(self, task_name: str) -> Optional[Task]:
        """Return the Task with a matching name, or None."""
        return next((t for t in self.tasks if t.name == task_name), None)

    def __str__(self) -> str:
        return f"{self.name} ({self.species}, {self.breed}) — {len(self.tasks)} tasks"


class Owner:
    """Manages multiple pets and provides unified access to all their tasks."""

    def __init__(self, name: str, time_available_mins: int):
        if time_available_mins <= 0:
            raise ValueError("time_available_mins must be greater than 0")
        self.name = name
        self.time_available_mins = time_available_mins  # daily time budget in minutes
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name. Raises ValueError if not found."""
        match = self._find_pet(pet_name)
        if match is None:
            raise ValueError(f"Pet '{pet_name}' not found for owner {self.name}")
        self.pets.remove(match)

    def get_all_tasks(self) -> List[Task]:
        """Return all tasks across all pets as a flat list."""
        return [task for pet in self.pets for task in pet.tasks]

    def get_pending_tasks(self) -> List[Task]:
        """Return only incomplete tasks across all pets."""
        return [task for pet in self.pets for task in pet.get_pending_tasks()]

    def _find_pet(self, pet_name: str) -> Optional[Pet]:
        """Return the Pet with a matching name, or None."""
        return next((p for p in self.pets if p.name == pet_name), None)

    def __str__(self) -> str:
        return f"{self.name} — {len(self.pets)} pet(s), {self.time_available_mins}min available"


class Schedule:
    """The brain: retrieves, organises, and plans tasks within the owner's time budget."""

    def __init__(self, owner: Owner, schedule_date: date = None):
        self.owner = owner
        self.date = schedule_date or date.today()
        self.planned_tasks: List[Task] = []
        self.skipped_tasks: List[Task] = []  # tasks that didn't fit in the time budget

    def generate(self) -> "Schedule":
        """Greedily select tasks sorted by priority (1=highest) within the time budget."""
        self.planned_tasks = []
        self.skipped_tasks = []

        # sort ascending: priority 1 comes first
        pending = sorted(self.owner.get_pending_tasks(), key=lambda t: t.priority)

        time_remaining = self.owner.time_available_mins
        for task in pending:
            if task.duration_mins <= time_remaining:
                self.planned_tasks.append(task)
                time_remaining -= task.duration_mins
            else:
                self.skipped_tasks.append(task)

        return self

    def total_duration(self) -> int:
        """Return total minutes of all planned tasks."""
        return sum(t.duration_mins for t in self.planned_tasks)

    def display(self) -> str:
        """Return a human-readable summary of the schedule."""
        if not self.planned_tasks:
            return f"No tasks scheduled for {self.date}."

        lines = [f"Schedule for {self.owner.name} — {self.date}",
                 f"Time budget: {self.owner.time_available_mins}min | Planned: {self.total_duration()}min",
                 "-" * 40]

        for task in self.planned_tasks:
            lines.append(f"  [{task.priority}] {task.pet_name}: {task.name} "
                         f"({task.duration_mins}min, {task.frequency})")

        if self.skipped_tasks:
            lines.append(f"\nSkipped ({len(self.skipped_tasks)} tasks didn't fit):")
            for task in self.skipped_tasks:
                lines.append(f"  - {task.pet_name}: {task.name} ({task.duration_mins}min)")

        return "\n".join(lines)
