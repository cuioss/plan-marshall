envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-01T20:42:20Z

# Consumer-repo fit of the finalize and outline path: three high items recur in an API-Sheriff (Maven) project

Severity: **high (inherited)**. Bundle: `plan-marshall`. Kind: recurrence evidence plus one new item (4 above).
Source: 4 lessons from the API-Sheriff checkout, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/API-Sheriff/`. Not re-verified at HEAD; they rest on the senders' account of plans 24, 28 and 30.

## Items

1. **Deep-lane outline writes no assessments, then Q-Gate `assessment_coverage` fails every deliverable** — lesson `2026-10-12-16-001`. Recurrence of `lessons-routing-022` / `-032` / `-040`: two plans in a row (PLAN-24 accepted the finding, PLAN-30 backfilled 15 assessments). Remedy the sender prefers: the outline path records assessments as it goes.
2. **`ci-verify.md` prescribes hand-offs for producers `verification-feedback.md` rejects** — lesson `2026-10-12-16-005`. The producers `ci-verify-policy` and `ci-verify-cancelled` answer `unknown_producer`; two hand-offs cost about 570K tokens and produced nothing. Recurrence of the archived `2026-10-05-14-001` and `lessons-routing-019`. Sender's test idea: assert every producer named in `ci-verify.md` is in the accepted set.
3. **Maven consumer: no narrow test scope, pre-push gate records `module-tests` as degraded although every test ran** — lesson `2026-10-12-16-008`. Recurrence of `lessons-routing-031`. The degraded mark names the missing canonical command, not missing coverage.
4. **NEW — a finalize step with no implementor records `done`, not `skipped`** — lesson `2026-10-13-14-003`. In a Maven repository no self-review surfacer is registered (the only one targets the marketplace repo), yet `pre-submission-self-review` was recorded `outcome=done` with no review activity between its two entries. `pre-push-quality-gate` and `branch-cleanup` docs also name python/pyprojectx commands inline instead of resolving through the build-system abstraction. Ask: record `skipped` with the reason when nothing implements the step.

## What is asked

Check each against `HEAD` for a residual (owners: `lessons-routing-019`, `-022`, `-031` and their plans). Item 4 has no owner on record.
