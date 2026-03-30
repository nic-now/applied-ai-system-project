import streamlit as st
from pawpal_system import Owner, Pet, Task, Schedule, CATEGORY_EMOJI, PRIORITY_EMOJI

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
    time_budget = st.number_input("Time available today (minutes)", min_value=10, max_value=480, value=60, step=5)
    st.caption(f"{int(time_budget) // 60}h {int(time_budget) % 60}m")
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
        try:
            pet = Pet(name=pet_name, species=species, breed=breed)
            st.session_state.owner.add_pet(pet)      # Owner.add_pet() from Phase 2
            st.session_state.pets.append(pet)
            st.success(f"Added pet: {pet_name}")
        except ValueError as e:
            st.error(str(e))

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
    PRESET_CATEGORIES = ["walk", "feeding", "meds", "grooming", "enrichment", "other (type below)"]
    cat_choice   = st.selectbox("Category", PRESET_CATEGORIES)
    custom_cat   = st.text_input("Custom category (only if 'other' selected)", value="")
    category     = custom_cat if cat_choice == "other (type below)" else cat_choice
    duration     = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=30)
    priority     = st.selectbox("Priority (1=highest)", [1, 2, 3, 4, 5])
    frequency    = st.selectbox("Frequency", ["daily", "weekly", "as needed"])
    due_time     = st.text_input("Due time (optional, HH:MM)", value="")
    mandatory    = st.checkbox("Mandatory (always schedule this task first, e.g. medications)")
    add_task     = st.form_submit_button("Add Task")

if add_task:
    if not st.session_state.pets:
        st.warning("Add a pet first.")
    else:
        # find the chosen Pet object and call Pet.add_task() — stamps pet_name automatically
        pet_obj = next(p for p in st.session_state.pets if p.name == selected_pet)
        task = Task(name=task_name, category=category,
                    duration_mins=int(duration), priority=priority,
                    frequency=frequency, due_time=due_time, mandatory=mandatory)
        pet_obj.add_task(task)
        label = " (mandatory)" if mandatory else ""
        st.success(f"Added task '{task_name}' to {selected_pet}{label}")

# show all current tasks across all pets
all_tasks = st.session_state.owner.get_all_tasks() if st.session_state.owner else []
if all_tasks:
    st.write("All tasks:")
    st.table([{
        "":          CATEGORY_EMOJI.get(t.category, "📋"),
        "pet":       t.pet_name,
        "task":      t.name,
        "mins":      t.duration_mins,
        "priority":  PRIORITY_EMOJI.get(t.priority, "⚪"),
        "frequency": t.frequency,
        "mandatory": "YES" if t.mandatory else "",
    } for t in all_tasks])

    # --- task removal ---
    with st.form("remove_task_form"):
        task_options   = [f"{t.pet_name}: {t.name}" for t in all_tasks]
        task_to_remove = st.selectbox("Remove a task", task_options)
        remove_btn     = st.form_submit_button("Remove Task")

    if remove_btn:
        # parse pet name and task name back from the label
        pet_label, task_label = task_to_remove.split(": ", 1)
        pet_obj = next(p for p in st.session_state.pets if p.name == pet_label)
        try:
            pet_obj.remove_task(task_label)   # Pet.remove_task() raises ValueError if not found
            st.success(f"Removed '{task_label}' from {pet_label}")
            st.session_state.schedule = None  # invalidate schedule after change
        except ValueError as e:
            st.error(str(e))

st.divider()


# --- Step 3: Generate Schedule → wired to Schedule.generate() ---
st.subheader("4. Today's Schedule")
if st.button("Generate Schedule"):
    if st.session_state.owner is None:
        st.warning("Save an owner first.")
    elif not all_tasks:
        st.warning("Add at least one task first.")
    else:
        schedule = Schedule(owner=st.session_state.owner)
        schedule.generate()
        st.session_state.schedule = schedule

# display the result
if st.session_state.schedule:
    sched = st.session_state.schedule

    # --- conflict warnings — shown at the top so they're hard to miss ---
    conflicts = sched.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            st.warning(f"Scheduling conflict: {warning}")

    # --- summary banner ---
    st.success(f"Planned {len(sched.planned_tasks)} tasks — {sched.total_duration()} min"
               f" of {sched.owner.time_available_mins} min available")

    # --- planned tasks sorted by due_time ---
    st.markdown("**Planned tasks** (sorted by time):")

    sorted_tasks = sched.sort_by_time()
    for task in sorted_tasks:
        time_label     = f"{task.due_time} " if task.due_time else ""
        mandatory_label = " MANDATORY" if task.mandatory else ""
        pri_emoji      = PRIORITY_EMOJI.get(task.priority, "⚪")
        cat_emoji      = CATEGORY_EMOJI.get(task.category, "📋")
        st.checkbox(
            f"{pri_emoji} {cat_emoji} {time_label}{task.pet_name}: {task.name}"
            f" ({task.duration_mins} min){mandatory_label}",
            key=f"task_{task.name}_{task.pet_name}"
        )

    # --- skipped tasks ---
    if sched.skipped_tasks:
        st.markdown("**Skipped tasks** (did not fit in time budget):")
        st.table([{"pet": t.pet_name, "task": t.name, "mins": t.duration_mins,
                   "priority": t.priority} for t in sched.skipped_tasks])
