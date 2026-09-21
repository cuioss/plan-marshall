envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:35:14Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=plan-04-autonomy-gate-defaults

# Resolve max_iterations from the live config, never from a documented default

## Context

The run rationed its loop-back budget against a ceiling of 3. Three work-log
`[STATUS]` lines carry the belief and act on it:

- `21:42:06Z` — "Loop-back iteration 2/3 ... This is the LAST iteration that
  will be spent on self-review findings: iteration 3 is reserved so a genuinely
  blocking defect found later in the run still has an admissible round."
- decision `30dc4d` — reserved iteration 3 for a post-review finding.
- `09:08:04Z` — "Loop-back iteration 3/3 admitted — the CEILING IS NOW SPENT
  ... after these tasks land, no admissible loop-back remains. Anything the
  merge gate surfaces afterward cannot be absorbed by the machinery and must
  escalate to the operator instead."

The project's live value is `plan.phase-6-finalize.max_iterations: 17`, and it
was 17 for the entire run — verified both against the current `.plan/marshal.json`
and against the file as it stood at commit `d03ca621c`, the state in force when
the plan started. `3` is the value the documentation states as the shipped
default (`manage-config/standards/data-model.md:829`,
`| max_iterations | int | 3 | Maximum finalize-verify-finalize loops |`).

The cost was not exhausted iterations — only three were needed. The cost was
decision distortion: a rationing posture adopted across three dispatches, and a
declared escalation obligation that did not exist.

## Root cause

A configured value was read from prose stating the shipped default instead of
from the store holding the project's value. Two structural contributors:

1. `automatic-review/SKILL.md:1011` hard-codes the range in prose —
   "`{iteration}` is the current loop-back iteration number (1..3)". A reader
   composing an iteration-N-of-M line has a literal `3` handed to it at the
   call site, with no indication the bound is configurable.
2. Nothing in the loop-back admission path resolves or logs the live value, so
   the number in the `[STATUS]` line has no provenance a later reader can check.

The recurrence is self-referential: the same plan committed the census NOTE that
forbids exactly this read — `doc/user/configuration.adoc:191`, "Every value above
is the **shipped default** ... never the value in any particular project's
config. Read your own with `manage-config plan <phase> get --field <knob>`; a
configured project routinely differs."

## Proposed action

1. Resolve `max_iterations` at loop-back admission time via
   `manage-config plan phase-6-finalize get --field max_iterations`, and include
   the resolved value and its source in the `[STATUS]` line, so an iteration
   count cannot be composed from a remembered default.
2. Replace the literal `(1..3)` at `automatic-review/SKILL.md:1011` with a
   pointer to the configured bound.

## Evidence

- aspect: chat_history_analysis — "The run rationed loop-back iterations against
  a ceiling of 3 that the project does not have."
- `.plan/marshal.json` `plan.phase-6-finalize.max_iterations: 17`; identical at
  `git show d03ca621c:.plan/marshal.json`.
- `manage-config/standards/data-model.md:829` — the documented default `3`.
- `doc/user/configuration.adoc:189-196` — the census NOTE this plan authored.

## Same-run recurrence of the same root cause

Twice more in this run a value with an authoritative reader was instead composed
or inferred:

- `10:07:23Z` (self-caught and corrected) — `head_at_completion` was stamped with
  a SHA composed from a short prefix rather than read from `git rev-parse`. The
  run recorded its own consequence: "the head-dependent re-entry check compares
  the recorded SHA against live HEAD, so a fabricated SHA never matches and the
  gate would have re-fired on every re-entry forever."
- Three firings of `finalize-step-lessons-housekeeping` read
  `references.modified_files`, a key retired with the change-ledger (filed
  separately).

Three independent instances in one run is what makes this a class rather than a
slip: the discipline to add is "read the value from the store that owns it", not
"remember this particular number".
