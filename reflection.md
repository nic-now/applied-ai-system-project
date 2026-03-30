# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Core actions: add user/pet/tasks, schedule plan (e.g. walk) and display
- Initial UML design: First UML included four classes (Owner, Pet, Schedule, Task), with adequate relationships and variables for each class.
- Owner (in charge of owner's information e.g. name, availability), Pet (in charge of pet's information, e.g. name and description), Schedule (holds dates and planned tasks, in charge of overviewing schedules), Task (in charging of task information, e.g. description, priority, completed, ect.)

**b. Design changes**

- Design did change during implementation.
- For example, relationship from pet to task was added, so that task can be associated with a specific pet too (since an owner might have multiple pets)
- Safeguards were also added based on recommendations by Claude Code (e.g. check time_available_mins)

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- Scheduler cosiders time and priority constraints
- How did you decide which constraints mattered most?
- 

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

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
