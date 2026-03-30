import streamlit as st
from pawpal_system import Owner, Pet, Task, Schedule

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# --- Step 2: Application Memory ---
# st.session_state is a dict that survives reruns — initialise keys once here
if "owner" not in st.session_state:
    st.session_state.owner = None      # set when the owner form is saved

if "pets" not in st.session_state:
    st.session_state.pets = []         # list of Pet objects

if "schedule" not in st.session_state:
    st.session_state.schedule = None   # set after generate is clicked


# --- Step 3: Owner Form → wired to Owner class ---
st.subheader("1. Owner Info")
with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Yoda")
    time_budget = st.slider("Time available today (minutes)", min_value=10, max_value=240, value=60, step=5)
    saved = st.form_submit_button("Save Owner")

if saved:
    # calls Owner.__init__ — guard raises ValueError if time_budget <= 0
    st.session_state.owner = Owner(name=owner_name, time_available_mins=time_budget)
    st.success(f"Owner saved: {owner_name}, {time_budget} min available")

st.divider()


# --- Step 3: Pet Form → wired to Owner.add_pet() ---
st.subheader("2. Add a Pet")
with st.form("pet_form"):
    pet_name = st.text_input("Pet name", value="Mochi")
    species  = st.selectbox("Species", ["Dog", "Cat", "Other"])
    breed    = st.text_input("Breed", value="Shiba Inu")
    add_pet  = st.form_submit_button("Add Pet")

if add_pet:
    if st.session_state.owner is None:
        st.warning("Save an owner first.")
    else:
        pet = Pet(name=pet_name, species=species, breed=breed)
        st.session_state.owner.add_pet(pet)      # Owner.add_pet() from Phase 2
        st.session_state.pets.append(pet)        # keep a reference for the task form
        st.success(f"Added pet: {pet_name}")

# show current pets
if st.session_state.pets:
    st.write("Your pets:", [str(p) for p in st.session_state.pets])

st.divider()


# --- Step 3: Task Form → wired to Pet.add_task() and Task dataclass ---
st.subheader("3. Add a Task")
with st.form("task_form"):
    pet_options  = [p.name for p in st.session_state.pets]
    selected_pet = st.selectbox("Assign to pet", pet_options if pet_options else ["(no pets yet)"])
    task_name    = st.text_input("Task name", value="Morning Walk")
    category     = st.selectbox("Category", ["walk", "feeding", "meds", "grooming", "enrichment"])
    duration     = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=30)
    priority     = st.selectbox("Priority (1=highest)", [1, 2, 3, 4, 5])
    frequency    = st.selectbox("Frequency", ["daily", "weekly", "as needed"])
    add_task     = st.form_submit_button("Add Task")

if add_task:
    if not st.session_state.pets:
        st.warning("Add a pet first.")
    else:
        # find the chosen Pet object and call Pet.add_task() — stamps pet_name automatically
        pet_obj = next(p for p in st.session_state.pets if p.name == selected_pet)
        task = Task(name=task_name, category=category,
                    duration_mins=int(duration), priority=priority, frequency=frequency)
        pet_obj.add_task(task)                   # Pet.add_task() stamps pet_name on the task
        st.success(f"Added task '{task_name}' to {selected_pet}")

# show all current tasks across all pets
all_tasks = st.session_state.owner.get_all_tasks() if st.session_state.owner else []
if all_tasks:
    st.write("All tasks:")
    st.table([{"pet": t.pet_name, "task": t.name, "mins": t.duration_mins,
               "priority": t.priority, "frequency": t.frequency} for t in all_tasks])

st.divider()


# --- Step 3: Generate Schedule → wired to Schedule.generate() ---
st.subheader("4. Today's Schedule")
if st.button("Generate Schedule"):
    if st.session_state.owner is None:
        st.warning("Save an owner first.")
    elif not all_tasks:
        st.warning("Add at least one task first.")
    else:
        # Schedule.generate() runs the greedy priority scheduler from Phase 2
        schedule = Schedule(owner=st.session_state.owner)
        schedule.generate()
        st.session_state.schedule = schedule

# display the result
if st.session_state.schedule:
    sched = st.session_state.schedule
    st.success(f"Planned {len(sched.planned_tasks)} tasks — {sched.total_duration()} min total")
    for task in sched.planned_tasks:
        st.checkbox(f"[{task.priority}] {task.pet_name}: {task.name} ({task.duration_mins} min)", key=task.name)
    if sched.skipped_tasks:
        st.warning(f"Skipped (didn't fit): {', '.join(t.name for t in sched.skipped_tasks)}")
