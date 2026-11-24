envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:45Z

component=plan-marshall:manage-execution-manifest
category=bug
title=manifest compose resets envelope_count to 1 when --envelope-count is omitted, although the tasks carry the packed envelope ids
source_lesson=2026-11-24-07-012
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# manifest compose resets envelope_count to 1 when --envelope-count is omitted, although the tasks carry the packed envelope ids

Source: plan-retrospective (finalize), confirmed by the plan's decision log and two 4-plan hand-backs.

In the logs:
- 4-plan ran `manage-execution-manifest compose` four times between 2026-11-23T17:02:27Z and 17:09:41Z.
- The first 4-plan hand-back says: "The first compose recorded envelope_count 1 because the flag was omitted. I recomposed once with --envelope-count 4."
- The in-place amend that added TASK-13 hit the same thing: "The first compose without the flag reset it to 1, and the second compose fixed it."

Observation: the envelope count is already stamped on every task (`envelope_id`, from `pack-envelopes`), yet a compose without the flag writes 1 over the packed value. Each time an agent has to notice it and compose again.

Candidate rule (for the orchestrator to classify): compose should keep the existing `phase_5.envelope_count`, or derive it from the tasks' `envelope_id` stamps, when `--envelope-count` is not given. A silent reset to 1 should be refused or logged.

Not a duplicate of messages 001-016 from lessons-capture: none of them covers the manifest compose surface.

Context: plan plan-20-leftover-fixes-2.


Source: inbox plan-20-leftover-fixes-2-017.
