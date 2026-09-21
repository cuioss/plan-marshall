# Lessons index — finalize-machinery epic-owned copies

Source: corpus lessons under `.plan/local/lessons-learned/`, moved/copied here per
operator direction 2026-09-17 ("analyze all lessons describing issues for this epic;
move into the epic; remove duplicates and already-covered ones").

Layout variance note: the canonical epic tree
(`persona-plan-orchestrator/standards/orchestration-model.md` § Directory Layout) defines
no `lessons/` directory. This epic carries one as a deliberate variance: the corpus
removal below would otherwise leave the retired rules with no home. Recorded in epic.md
Decisions and the decision log.

## Removed from corpus (tombstoned with verdicts)

### Completely covered by shipped plans

| Lesson | Covered by | Covering clause |
|--------|-----------|-----------------|
| 2026-09-03-19-004 | PLAN-02 / PR #1507 | executor-template rejection names flag + sibling verb at exit 2 |
| 2026-09-03-19-003 | PLAN-02 / PR #1507 | ci router-position --plan-id accepted on prepare-body/edit |
| 2026-08-25-09-014 | PLAN-02 / PR #1507 | measured-diff-size is a value-required scalar |
| 2026-09-03-11-004 | PLAN-02 / PR #1507 | manage-status read accepted forms (--plan-id/--store) |
| 2026-09-03-11-002 | PLAN-01 / PR #1505 | self-review order 8, gate last order 10 |
| 2026-09-03-19-005 | PLAN-01 / PR #1505 | single-pass HEAD anchor, ≤1 firing bound |
| 2026-09-03-11-007 | PLAN-01 / PR #1505 | same mechanism as 19-005 (cost symptom) |
| 2026-09-04-17-016 | PLAN-03 / PR #1510 | _github_pr SHA-comparison currency guard |
| 2026-09-05-14-001 | PLAN-03 / PR #1510 | head_sha_verified reachable on issue_comment path |
| 2026-09-06-07-003 | PLAN-03 / PR #1510 | Trigger-B selects actually-stale bot |
| 2026-09-08-22-001 | PLAN-03 / PR #1510 | same comment-path repair as 14-001 |
| 2026-09-08-13-004 | PLAN-02 / PR #1507 | same scalar contract as 08-25-09-014 |

### Redundant (representative retained in corpus)

| Removed | Representative (retained, open) |
|---------|---------------------------------|
| 2026-09-02-08-001 | 2026-08-25-09-012 (sourcery refusal; confirmation run still owed) |
| 2026-09-14-12-001 | 2026-09-12-08-001 (CI-timeout acceptance practice) |
| 2026-09-04-17-010 | 2026-09-03-18-001 (pollution-guard attribution) |

## Copied, corpus original retained (open or staged)

Staged in plans (retire at ship via that plan's housekeeping): 06-07-002, 06-08-002
(PLAN-05); 05-16-001 (PLAN-05); 05-16-002, 05-16-003, 05-16-004, 03-16-005, 19-006
(PLAN-06).
Open future work (this epic's lane, no owning plan yet): 08-25-09-001, 08-25-09-002,
08-25-09-004, 08-25-09-007, 08-25-09-009, 08-25-09-010, 08-25-09-012, 08-25-09-013,
08-25-09-016, 09-03-06-001, 09-03-11-001, 09-03-11-003, 09-03-11-006, 09-03-16-004,
08-13-001, 08-13-002, 08-13-003, 08-13-005, 08-13-008, 08-13-011, 08-01-003, 08-01-002,
08-30-16-001, 09-02-13-002, 09-03-07-003, 09-04-14-006, 09-04-14-007, 09-04-14-008,
09-07-13-004, 09-07-13-005, 09-07-13-006, 09-07-13-009, 09-09-01-002, 09-12-08-001,
09-13-09-001, 09-13-12-001, 09-13-12-002, 09-14-05-003, 09-03-10-001, 09-04-17-001,
09-04-17-005, 09-06-10-001, 09-13-12-004, 09-03-18-001, 09-03-19-007, 09-03-22-002,
09-07-15-004, 09-07-15-011.

## Explicitly out of scope (left in corpus untouched)

Retrospective/test/phase-3/phase-4/plugin-dev/execute-lane lessons; shipped-by-other-
epics lessons (16-17-001/003, 14-05-005, 13-12-013/014, 07-15-009, 09-03-06-002);
already-retired lessons (11-005, 06-08-001, 17-008, 02-001..009, 04-07-001/002,
03-17-001, 17-15-001, 14-005); git-lane baseline-reconcile quartet (19-001, 04-07-001,
04-17-011, 07-21-001 — see 08-01-002); triage-lane (08-13-007/010, 13-12-012);
sourcery representative 08-25-09-012 stays until its confirmation run.

## Stray file (operator cleanup)

`lessons/2026-09-08-25-09-012.md` is a misnamed duplicate of
`lessons/2026-08-25-09-012.md` (typo during staging; no delete tool available to the
orchestrator). Delete manually.
