# GEMINI.md

High-signal engineering guidelines optimized for the Gemini CLI agent. These instructions supplement the core mandates and should be followed to ensure high-quality, maintainable, and idiomatic code changes.

## 1. Research & Verification First
**Never guess. Verify assumptions through empirical observation.**

- **Bug Fixes:** Always reproduce the issue with a failing test or script BEFORE applying a fix. Verification of the fix is mandatory.
- **Environment Awareness:** Be aware that this is a bind-mounted Docker container. Tools like linters or type-checkers may exist on the host but not inside the container.
- **Inquiry vs. Directive:** Treat questions as Inquiries. Do not modify files unless a clear Directive (instruction to act) is issued.

## 2. Strategy & Planning
**Design the solution before writing code.**

- For complex tasks, use `enter_plan_mode` to draft a design and get approval.
- Explicitly state assumptions and potential tradeoffs.
- **Configuration Scrutiny:** Do not assume `pyproject.toml` settings (like Ruff configs) are applicable; verify if they are relevant to the current task.

## 3. Surgical & Idiomatic Execution
**Maintain structural integrity and follow local conventions.**

- **Surgical Edits:** Touch only what is necessary for the task. Avoid "cleanup" of unrelated code unless explicitly requested.
- **Local Consistency:** Analyze existing code to match naming conventions, formatting, and architectural patterns.
- **Type Safety:** Use explicit language features (type guards, explicit interfaces).

## 4. Validation Lifecycle
**A task is incomplete until verified.**

- **Functional Verification:** Verify changes through scripts or manual execution within the container.
- **Testing:** While formal frameworks like `pytest` are not required, ensure logic is verified through reproducible scripts.
- **External Tools:** If linting/formatting is required, consult the user as these tools may reside on the host.

## 5. Simplicity & Maintenance
**Favor readable, maintainable code over "clever" abstractions.**

- No speculative features or "just-in-case" configurations.
- Consolidate logic into clean abstractions if it improves readability, but avoid over-engineering.

---

**Success Metric:** Changes are functional, verified, and idiomatic, respecting the containerized environment.
