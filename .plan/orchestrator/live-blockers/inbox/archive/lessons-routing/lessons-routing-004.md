envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T14:43:51Z

# Lessons ingest: review-bot fleet enrolment of the schema-failing repositories

Severity: high. Subject: cuioss organisation repositories and review-bot configuration, outside the
`plan-marshall` bundle. Backlog reference: `backlog.md` § 4.5.

Lesson `2026-10-06-15-001` was retired from the lessons corpus by the `lessons-routing` ingest of
2026-10-09 and is handed to this epic. Its full body is kept at
`lessons-routing/lessons-archive/filed-live-blockers/2026-10-06-15-001.md`.

The lesson's directive has four items. Its own text marks items 1, 3 and 4 as completed in
PLAN-LB-30 (schema and docs updated in cuioss-organization v0.39.0, the three migrated repositories
re-validated whole-file, a runnable `./pw validate` added). One item is open:

- **Item 2.** Enrol every repository PLAN-PR-078 left unwritten for schema failure: the
  `cuioss-review-bot.yml` caller at the current org pin plus the `cuioss-review-bot:` block with the
  operator-confirmed packs (PLAN-PR-078 pack table), with the pre-merge release-guard gate. The lesson
  records this as deferred to PLAN-LB-31.

## What to check here

Confirm PLAN-LB-31 (`in-house-reviewer`, staged, emitted) carries item 2, then discard this message as
covered. Nothing else in the lesson is outstanding.
