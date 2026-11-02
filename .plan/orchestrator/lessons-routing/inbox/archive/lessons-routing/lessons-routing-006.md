envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T14:51:13Z

# Two finalize traps cost a repair round each: sanction ordering and prose in the evidence array

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-06-enumeration-hardening (PR #528), candidate lessons 002 and 005. Observed with plugin and executor 0.1.2010.

## Observation

1. In 6-finalize, `git-workflow commit` refuses with `no_sanction` once the fix task it belongs to is marked done. The plan hit that ordering trap twice.
2. The functional-review author wrote free-text explanations into the verdict's `evidence` entries. The validator treats every entry as a repository path that must exist at the graded head, so it rejected the verdict (`evidence ... does not exist at the graded head`) and the one allowed inline repair was spent.

## What to consider

- Order the finalize fix-task recipe as edit, gate, commit, then mark-done. Or let the sanction check accept a just-closed fix task whose commit is pending, or make the task-done verb refuse while the task's changes are uncommitted, so the trap fails early.
- State in the functional-review author prompt that `evidence` holds only repository paths (optionally with a line anchor) that exist at the graded head, with one valid and one invalid example, and name the narrative field for reasoning in the validator's error.
