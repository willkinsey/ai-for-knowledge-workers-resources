---
name: delegate-bounded-work
description: Delegate one independently verifiable unit of work to the configured luna_worker. Use when a separate GPT-6 Luna Max worker can safely own a bounded task.
---

# Delegate Bounded Work

The parent agent owns framing, authority, integration, evidence review, and final acceptance. Delegate a task only when its objective and completion evidence can be stated clearly.

## Build the Assignment

Request the `luna_worker` role, or explicitly request `gpt-6-luna` with `max` reasoning when launching a direct subagent. Preserve Max as configured. If that model or effort is unavailable, report the blocker; do not silently switch to another model or reasoning level.

Send a complete task packet:

    Persona: The task-specific perspective the worker should use.
    Objective: One concrete completion condition.
    Scope: Exact files, systems, and excluded work.
    Context: Required facts, decisions, sources, and evidence limits.
    Authority: Allowed reads and writes, plus prohibited actions.
    Deliverable: The artifact or findings to return.
    Success Criteria: Observable checks required for acceptance.
    Handoff: Outcome, evidence, files changed, validation, risks or blockers, and next step.

Give the worker exclusive ownership of its mutable files. Identify any shared files and resolve ownership before launch. Keep the work narrow, provide relevant source references, and do not ask the worker to delegate further.

## Review the Handoff

Inspect the reported result and the evidence needed to support it. Confirm the worker stayed within its file and authority boundaries. Run proportionate validation, repair or request a bounded follow-up if needed, and retain final acceptance in the parent task.

If no Luna subagent is available, explain that limitation to the parent. Do not imply that a different model completed the delegated task.
