envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:01Z

# branch-cleanup called merge_lock acquire with --wait-seconds instead of --max-seconds

Component (suggested): plan-marshall:phase-6-finalize (branch-cleanup) / plan-marshall:manage-locks, category bug (marketplace-owned)
Signal: script-failure cluster, notation plan-marshall:manage-locks:merge_lock

## Observation

During branch-cleanup (2026-10-12T12:56:14Z, work log hash 861f03) `merge_lock acquire` rejected `--wait-seconds`; the error named the canonical `--max-seconds`. The next call acquired the lock (12:56:20) and the merge proceeded.

## Candidate directive

Check the branch-cleanup / merge-lock prose for a `--wait-seconds` example or paraphrase and replace it with `--max-seconds`; a plugin-doctor argument-naming check over that workflow would catch the class.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); work log 861f03.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-010.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
