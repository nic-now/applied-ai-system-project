# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Core actions: add user/pet/tasks, schedule plan (e.g. walk) and display
- Initial UML design: First UML included four classes (Owner, Pet, Schedule, Task), with adequate relationships and variables for each class.
- Owner (in charge of owner's information e.g. name, availability), Pet (in charge of pet's information, e.g. name and description), Schedule (holds dates and planned tasks, in charge of overviewing schedules), Task (in charging of task information, e.g. description, priority, completed, ect.)

**b. Design changes**

- Design did change during implementation (functions/properties).
- For example, relationship from pet to task was added, so that task can be associated with a specific pet too (since an owner might have multiple pets)
- Safeguards were also added based on recommendations by Claude Code (e.g. check time_available_mins)

<a href="imgs/uml-design.png" target="_blank"><img src='imgs/uml-design.png' title='UML design' width='' alt='PawPal App UML design' class='center-block' /></a>
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- Scheduler considers time and priority constraints
- Time was chosen as the main constraint since a pet owner has a fixed daily budget and not all tasks will fit. Priority was chosen as the sorting key since some tasks (e.g. meds) are more critical than others and should always be scheduled first.

**b. Tradeoffs**

- A tradeoff the scheduler makes is using greedy priority-based selection, it picks tasks in priority order and takes the first one that fits, without looking ahead for a more optimal combination. This is reasonable because higher priority tasks (e.g. meds, feeding) should always be scheduled first, and the task list for a pet owner is small enough that perfect optimisation is not necessary.
- A second tradeoff is in conflict detection, which only flags tasks with the exact same due_time string. Tasks that overlap in duration but start at different times are not detected. This is reasonable as computing duration overlap would add significant complexity for a minor edge case.

---

## 3. AI Collaboration

**a. How you used AI**

- Claude Code was used in this project for UML design brainstorming as well as correction, debugging, and implementation/understanding of logic.

- Prompting for explanations of different ways relationships can be implemented helped to understand and choose the best approach given a task.
- Asking about possible shortcomings/oversights in implementation also helped notice and improve code.

**b. Judgment and verification**

- When Claude suggested simplifying detect_conflicts() with a list comprehension, the change was not applied since the original was already clear enough.
- When Claude offered a knapsack algorithm as an alternative to greedy scheduling, greedy was chosen instead as it was easier to understand and debug for this scale of project.
- Suggestions were verified by reading the generated code before accepting, running the app to check behaviour, and asking follow-up questions when  reasoning wasn't clear.

---

## 4. Testing and Verification

**a. What you tested**

- Task lifecycle (mark_complete, reset), pet task management (add, remove, pet name stamping), scheduling behaviour (time budget enforcement, priority ordering), sorting by time, and conflict detection.
- These were important because they cover the core logic the app depends on — a bug in scheduling or task management would affect every other feature.

**b. Confidence**

- Fairly confident the core scheduling logic works correctly across the tested cases. The greedy algorithm is simple enough that its behaviour is predictable.
- Edge cases to test next: multiple mandatory tasks that together exceed the time budget, tasks with identical names on the same pet, and scheduling with no due_time set on any task.

---

## 5. Reflection

**a. What went well**

- The class structure came together cleanly from the star. Starting with a UML design before writing code made it easier to understand how the classes should relate to each other before getting into implementation details.

**b. What you would improve**

- The conflict detection only flags tasks at the exact same time slot. With more time, it could be improved to check for overlapping durations, which would make the warnings more accurate and useful for a real pet owner.

**c. Key takeaway**

- Designing the system first (even roughly/brainstorming) before writing code saves a lot of rework later. 
- Working with AI was most useful when asking it to explain tradeoffs rather than just generate code
- Understanding why a decision was made helped evaluate whether it actually fit the project.
