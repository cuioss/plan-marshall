envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:31Z

component=plan-marshall:plan-marshall
category=bug

# Triage-allocated fix tasks stamp an unresolvable build notation (maven_build), which the executor rejects with Unknown notation

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-18-002` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-18-002`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities`, 2026-09-08, on the loop-back from the
phase-6-finalize unified wait-region triage.

The triage dispositioned two findings as FIX and allocated `TASK-011` / `TASK-012`. Both were stamped
with the verification command:

```
plan-marshall:build-maven:maven_build run --command-args \"...\"
```

The executor rejects that with `Unknown notation` — the script is `maven`, not `maven_build`.

**The scope is diagnostic.** `TASK-001` through `TASK-010`, stamped by phase-4-plan, all carry the
correct `plan-marshall:build-maven:maven` notation; only the two triage-allocated tasks carry the
broken one. So the defect is in the fix-task allocation path (`verification-feedback` /
`manage-tasks` fix-task creation), not in the planner.

## Impact

This is the argparse/notation-rejection signature `persona-plan-marshall-agent` § \"Never invent
script subcommands\" exists to catch, arriving from the framework rather than from an agent's
paraphrase — so an executor that follows its own task record faithfully hits it.

The failure is loud (exit non-zero, `Unknown notation`), which is the good case: the executing agent
noticed, ran the corrected notation, and reported the discrepancy rather than silently substituting.
The bad case is an agent that reads the rejection as \"the build failed\" and marks the task blocked,
or one that quietly swaps in some other command and records a green whose provenance nobody can
reconstruct. A fix task exists precisely to close a review finding, so a bogus verification arm on
it means the fix ships with its own verification unproven.

## Directive

Fix the fix-task allocation path to stamp the same notation phase-4-plan stamps. Derive it rather
than hard-coding a second copy — a literal in a second place is what let these two diverge.

Add a validation at task-creation time that every stamped `verification.commands` entry resolves
against the executor's registered notations, so an unresolvable notation fails when the task is
written rather than when an executor tries to run it.

Until then: when a stamped verification command is rejected with `Unknown notation`, correct the
notation, run the real command, and SAY that the stamped one was wrong — never record the task green
without naming the substitution.
