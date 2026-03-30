#testing ground
from pawpal_system import Owner, Pet, Task, Schedule


#create owner and 3 pets
owner = Owner(name="Yoda", time_available_mins=90)

dog = Pet(name="Mochi", species="Dog", breed="Shiba Inu")
cat = Pet(name="Luna", species="Cat", breed="Tabby")

owner.add_pet(dog)
owner.add_pet(cat)

#add 3 tasks with different times to pets
dog.add_task(Task(name="Morning Walk",   category="walk",     duration_mins=30, priority=1, frequency="daily"))
dog.add_task(Task(name="Breakfast",      category="feeding",  duration_mins=10, priority=1, frequency="daily"))
dog.add_task(Task(name="Flea Treatment", category="meds",     duration_mins=5,  priority=2, frequency="weekly"))

cat.add_task(Task(name="Feeding",        category="feeding",  duration_mins=10, priority=1, frequency="daily"))
cat.add_task(Task(name="Brushing",       category="grooming", duration_mins=15, priority=3, frequency="weekly"))
cat.add_task(Task(name="Playtime",       category="enrichment", duration_mins=20, priority=4, frequency="daily"))

#print schedule to terminal
schedule = Schedule(owner=owner)
schedule.generate()
print(schedule.display())
