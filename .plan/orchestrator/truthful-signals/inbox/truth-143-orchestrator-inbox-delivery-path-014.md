envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:28:04Z

# Candidate lesson: a deliverable named the dispatch wrapper, not the module that defines the symbol

## Signal source

Q-Gate `3-outline` finding `1d4017` (severity error, operator-escalated as blocking via `3b061a`).

## Observation

Deliverable 5 declared the write target for a transition-verb change as `manage-status/scripts/manage-status.py`. `cmd_transition` is actually **defined** in `manage-status/scripts/_cmd_lifecycle.py`; `manage-status.py` carries only import and dispatch references (4 matches vs 9 in the defining module).

The consequence is not cosmetic: `_cmd_lifecycle.py` appeared in **neither** the deliverable's Affected files **nor** its `module_testing` scope. The declared write path did not contain the code the change described, so the footprint and the test scope were both wrong before a line was written.

## What resolved it

`architecture search --content 'def cmd_transition'` returned exactly one manage-status definition site. The deliverable was retargeted in both Affected files and the Module_testing scope, the Change-per-file text was amended to state why the wrapper needs no edit, and a success criterion was added pinning the payload change to the defining module.

Crucially, the fix was then **generalised rather than spot-applied**: a symmetric-peer audit ran over every other deliverable naming a symbol home (`cmd_inbox_write`, `cmd_corpus*`, `VALID_STATUS_VOCABULARY`, `PLAN_ID_SEGMENT`) and confirmed deliverable 5 was the only mis-target.

## Corrective rule

1. **Resolve a symbol's home before declaring it an affected file.** `architecture search --content 'def {symbol}'` answers it in one call; inferring the home from the script's public notation (`manage-status:manage-status`) reliably lands on the dispatch wrapper in this codebase, because `manage-*` scripts split their verbs into `_cmd_*.py` modules.
2. **When one mis-target is found, audit the symmetric peers** in the same artifact rather than fixing the single instance. A reviewer's (or validator's) hit list is a sample, not the population.
3. A deliverable whose Verification command and declared module disagree (finding `1f422c` in the same pass: `module: default` against a `test/plan-marshall/**` write target with a `module-tests plan-marshall` verification) is the same error class seen from the routing side.
