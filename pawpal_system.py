from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


@dataclass
class Task:
    """Represents a single pet care activity."""
    name: str
    category: str           # e.g. "walk", "feeding", "meds", "grooming"
    duration_mins: int
    priority: int           # 1 = highest priority, 5 = lowest priority
    frequency: str          # e.g. "daily", "weekly", "as needed"
    pet_name: str = ""               # stamped when added to a Pet
    completed: bool = False
    due_time: str = ""               # time of day e.g. "08:00"
    due_date: Optional[date] = None  # calendar date for renewal tracking
    mandatory: bool = False          # if True, always scheduled first regardless of budget

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
        """Register a pet under this owner. Raises ValueError if a pet with that name already exists."""
        if self._find_pet(pet.name) is not None:
            raise ValueError(f"A pet named '{pet.name}' already exists. Use a unique name.")
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
        """Select and order tasks within the owner's time budget.

        Improvements applied:
        1. Mandatory tasks are always scheduled first, regardless of budget.
        2. Tasks with a due_date set in the future (past today) are filtered out.
        3. Tie-breaking by duration (shortest first) fits more tasks into the budget.
        4. A gap-filling pass schedules any skipped tasks that fit remaining time.
        """
        self.planned_tasks = []
        self.skipped_tasks = []

        # improvement 2: filter out tasks not yet due (None due_date = always eligible)
        all_pending = [
            t for t in self.owner.get_pending_tasks()
            if t.due_date is None or t.due_date <= self.date
        ]

        # improvement 1: split into mandatory and optional
        mandatory = [t for t in all_pending if t.mandatory]
        optional  = [t for t in all_pending if not t.mandatory]

        # improvement 3: sort optional by (priority asc, duration asc) for tie-breaking
        optional = sorted(optional, key=lambda t: (t.priority, t.duration_mins))

        time_remaining = self.owner.time_available_mins

        # schedule mandatory tasks first — warn if they overrun the budget
        for task in mandatory:
            self.planned_tasks.append(task)
            time_remaining -= task.duration_mins
        if time_remaining < 0:
            print(f"WARNING: Mandatory tasks exceed time budget by {abs(time_remaining)} min.")

        # greedy pass over optional tasks
        for task in optional:
            if task.duration_mins <= time_remaining:
                self.planned_tasks.append(task)
                time_remaining -= task.duration_mins
            else:
                self.skipped_tasks.append(task)

        # improvement 4: gap-filling pass — try skipped tasks in the leftover time
        still_skipped = []
        for task in self.skipped_tasks:
            if task.duration_mins <= time_remaining:
                self.planned_tasks.append(task)
                time_remaining -= task.duration_mins
            else:
                still_skipped.append(task)
        self.skipped_tasks = still_skipped

        return self

    def mark_task_complete(self, task_name: str, pet_name: str) -> Optional[Task]:
        """Mark a task complete and auto-create the next occurrence for daily/weekly tasks.
        Returns the new Task if one was created, otherwise None."""
        # find the pet
        pet = self.owner._find_pet(pet_name)
        if pet is None:
            raise ValueError(f"Pet '{pet_name}' not found.")

        # find the task on that pet
        task = pet._find_task(task_name)
        if task is None:
            raise ValueError(f"Task '{task_name}' not found on {pet_name}.")

        task.mark_complete()

        # calculate next due_date using timedelta based on frequency
        if task.frequency == "daily":
            next_date = (task.due_date or date.today()) + timedelta(days=1)
        elif task.frequency == "weekly":
            next_date = (task.due_date or date.today()) + timedelta(weeks=1)
        else:
            return None  # "as needed" tasks don't auto-renew

        # create a fresh copy for the next occurrence
        renewed = Task(
            name=task.name,
            category=task.category,
            duration_mins=task.duration_mins,
            priority=task.priority,
            frequency=task.frequency,
            due_time=task.due_time,
            due_date=next_date,
        )
        pet.add_task(renewed)  # stamps pet_name automatically
        return renewed

    def detect_conflicts(self) -> List[str]:
        """Check planned tasks for scheduling conflicts (same due_time slot).
        Returns a list of warning strings — never raises, never crashes."""
        warnings = []

        # group tasks by due_time; skip tasks with no time set
        time_slots: dict = {}
        for task in self.planned_tasks:
            if not task.due_time:
                continue
            time_slots.setdefault(task.due_time, []).append(task)

        # any slot with more than one task is a conflict
        for time, tasks in time_slots.items():
            if len(tasks) > 1:
                names = ", ".join(f"{t.pet_name}: {t.name}" for t in tasks)
                warnings.append(f"WARNING: Conflict at {time} — {names}")

        return warnings

    def sort_by_time(self) -> List[Task]:
        """Return planned tasks sorted by due_time (HH:MM string).
        Tasks with no due_time set are placed at the end."""
        # lambda extracts due_time for comparison; "99:99" pushes empty strings to the end
        return sorted(self.planned_tasks, key=lambda t: t.due_time if t.due_time else "99:99")

    def filter_by_pet(self, pet_name: str) -> List[Task]:
        """Return all owner tasks belonging to a specific pet."""
        return [t for t in self.owner.get_all_tasks() if t.pet_name == pet_name]

    def filter_by_status(self, completed: bool) -> List[Task]:
        """Return all owner tasks matching the given completion status."""
        return [t for t in self.owner.get_all_tasks() if t.completed == completed]

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
