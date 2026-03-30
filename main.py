#testing ground
import sys
sys.stdout.reconfigure(encoding="utf-8")  # allow emojis in Windows terminal

from pawpal_system import Owner, Pet, Task, Schedule
from datetime import date


#create owner and 3 pets
owner = Owner(name="Yoda", time_available_mins=90)

dog = Pet(name="Mochi", species="Dog", breed="Shiba Inu")
cat = Pet(name="Luna", species="Cat", breed="Tabby")
bird = Pet(name="Kiwi", species="Bird", breed="")
owner.add_pet(dog)
owner.add_pet(cat)
owner.add_pet(bird)

# add tasks OUT OF ORDER by due_time to demonstrate sort_by_time()
dog.add_task(Task(name="Morning Walk",   category="walk",       duration_mins=30, priority=1, frequency="daily",  due_time="07:00"))
dog.add_task(Task(name="Flea Treatment", category="meds",       duration_mins=5,  priority=2, frequency="weekly", due_time="19:00"))
dog.add_task(Task(name="Breakfast",      category="feeding",    duration_mins=10, priority=1, frequency="daily",  due_time="08:00"))

cat.add_task(Task(name="Feeding",        category="feeding",    duration_mins=10, priority=1, frequency="daily",  due_time="08:30"))
cat.add_task(Task(name="Playtime",       category="enrichment", duration_mins=20, priority=4, frequency="daily",  due_time="17:00"))
cat.add_task(Task(name="Brushing",       category="grooming",   duration_mins=15, priority=3, frequency="weekly", due_time="18:00"))

bird.add_task(Task(name="Kiwi Feed",     category="feeding",    duration_mins=5,  priority=1, frequency="daily",  due_time="08:00"))  # intentional conflict with Mochi: Breakfast

# mandatory task — always scheduled first regardless of priority or budget
dog.add_task(Task(name="Insulin Injection", category="meds", duration_mins=5, priority=1, frequency="daily", due_time="07:30", mandatory=True))

# future-dated task — should be filtered out of today's schedule
cat.add_task(Task(name="Vet Checkup", category="meds", duration_mins=60, priority=2, frequency="as needed", due_date=date(2026, 4, 15)))

# mark one task complete to demo filter_by_status()
dog.tasks[0].mark_complete()

#print schedule to terminal
schedule = Schedule(owner=owner)
schedule.generate()
print(schedule.display())

# sort planned tasks chronologically by due_time
print("\n--- Sorted by time ---")
for task in schedule.sort_by_time():
    print(f"  {task.due_time}  {task.pet_name}: {task.name}")

# filter tasks by pet name
print("\n--- Luna's tasks only ---")
for task in schedule.filter_by_pet("Luna"):
    print(f"  {task}")

# filter by completion status
print("\n--- Completed tasks ---")
for task in schedule.filter_by_status(completed=True):
    print(f"  {task}")

print("\n--- Pending tasks ---")
for task in schedule.filter_by_status(completed=False):
    print(f"  {task}")

# detect scheduling conflicts (same due_time slot)
print("\n--- Conflict detection ---")
conflicts = schedule.detect_conflicts()
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts found.")

# mark a daily task complete — should auto-create next occurrence
print("\n--- Marking 'Breakfast' complete ---")
renewed = schedule.mark_task_complete("Breakfast", "Mochi")
if renewed:
    print(f"  Renewed task created: {renewed.name} due {renewed.due_date}")
