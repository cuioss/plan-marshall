envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:41:27Z

component=plan-marshall:manage-references
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# Three finalize steps derived three different footprints in one run and each proceeded on its own

## Context

This extends already-filed lesson **2026-08-26-06-002** ("`affected_files` diverges from live git in BOTH directions"). That lesson establishes the divergence. This adds the **measured magnitude** and a **third independent observer**, which together show the problem is not a stale field but an absent single source of truth.

Within one finalize run, three separate steps each derived the plan's footprint independently and got three different answers:

| observer | count | when | what it did with it |
|----------|------:|------|---------------------|
| `references.affected_files` | **52** | generate_time 14:28:13Z | became the denominator of every plan-efficiency ratio |
| `project:finalize-step-plugin-doctor` live footprint | **54** | 06:44:32Z | detected an F1-trigger file absent from `affected_files` and escalated to a WHOLE-TREE gate |
| `project:finalize-step-lessons-housekeeping` branch diff | **54** | 06:30:38Z | reconciled 77 lessons against that set |
| landing diff (`dad45f1bf..b4e8a2364`) | **62** | merge | the truth |

None of the three reconciled against another. The plugin-doctor step logged the divergence explicitly and worked around it by widening its own scope; nothing propagated the correction back.

Measured against the landing diff:

- **recall 92.3%** — 48 of the 52 declared files were actually touched; the 4 misses are audit/standards docs the outline named as read-side grounding rather than edit targets.
- **precision 77.4%** — 48 of 62 touched files were declared. **14 files (22.6% of the realized footprint) never entered `affected_files`**, of which 13 are substantive source or test files, not bookkeeping.

The undeclared 13 include three whole `platform-runtime` files (`opencode_runtime.py`, `runtime_base.py`, `standards/contract.md`), four `marshall-steward` test files, and `plugin-doctor/references/rule-catalog.md` — the very file whose absence forced the plugin-doctor escalation.

## Root cause

`affected_files` is written once and never re-derived, while the footprint moves throughout execute and finalize (7 tasks were appended after 4-plan; loop-back added 5 more; architecture-refresh added a commit). Every consumer that needs a current footprint therefore derives its own, and there is no place for the answer to be recorded, so each derivation is thrown away after use.

## Proposed action

1. Re-capture `affected_files` (via `manage-references capture-footprint`) after every commit-producing step, so one recorded number exists and each consumer reads it instead of deriving.
2. When a consumer's own derivation disagrees with the record, treat that as a finding, not just as input to a local widening decision — the plugin-doctor step had the evidence and the only thing it did with it was change its own scope.
3. Publish the recall/precision pair against the landing diff in the retrospective as a standing measure, so the divergence has a trend rather than a per-run anecdote.

## Evidence

- aspect: `request_result_alignment` → `footprint_derivation` (recall 92.31%, precision 77.42%), `scope_creep[14]`, `declared_but_untouched[4]`, `footprint_count_divergence[3]`.
- `logs/work.log` 06:44:32Z: "F1 trigger fired on the LIVE footprint (plugin-doctor/references/rule-catalog.md changed) but is absent from affected_files (52 recorded vs 54 live). Running WHOLE-TREE quality-gate, no --paths".
- `logs/work.log` 06:30:38Z: "proceeding on request.md + branch diff (54 files) alone".
- `work/metrics.toon` → `files_modified: 52`, `files_modified_sampling_point: generate_time`.
