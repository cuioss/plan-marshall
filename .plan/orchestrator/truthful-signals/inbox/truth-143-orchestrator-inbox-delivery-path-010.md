envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:27:45Z

# Candidate lesson: a fix for a defect class seeds the next instance of that same class — terminate by deletion, not rewrite

## Signal source

Q-Gate `6-finalize` findings `0b918c` and `037198`, both explicitly marked SELF-SEEDED by the finding author.

## Observation

Two of this plan's finalize findings were introduced by **the plan's own prior-round fixes**:

- `0b918c` — commit `7bd671bec` replaced an ambiguous cardinal ("Two of the epic homes are frozen records", itself finding `6bc073`) with "Rows carrying these statuses live in frozen archived-orchestrators/ trees". The replacement asserted an unscoped corpus-location fact that the declaring source refuses to assert, that the same section's own rule forbids, and that three other statements in the same diff contradict. The fix for an ambiguous-wording finding produced a contract_drift finding.
- `037198` — commit `819e4055f` (TASK-028) added a module comment asserting a CLOSED population of three restating blocks. A fourth existed and stayed unpinned. The fix for a doc-sync gap produced a completeness-claim defect.

The finding author for `0b918c` named the mechanism directly: *"per the round-loop termination self-seeding rule, correction breeds the next instance of this class"*, and prescribed **deletion of the offending clause, not another rewrite**. Both were ultimately resolved that way (`069c9519e`, `b29541c83`) — by deleting the sentence and keeping the surviving text that already carried the load-bearing point.

## Corrective rule

When a self-review round returns a finding against prose that a **previous round of the same run** wrote:

1. Treat the rewrite option as suspect. The prior round already demonstrated that this author, on this surface, generates a claim of this class when asked to phrase one.
2. Prefer **deletion** of the offending clause. In both instances here the surrounding text already carried the point without the stale-able claim; the clause was additive and load-free.
3. A completeness/cardinality claim ("three blocks", "two homes", "none had a check") is the highest-risk rewrite target — it must be **derived or absent**, never restated.

## Relationship to known corpus

PLAN-TRUTH-089 measured 27% of its findings as self-seeded and identified the terminating move as replacing a restatement with a pointer at its source. This run is a recurrence of that pattern under a different surface, which argues the lesson has not yet been converted into an instrument that fires at edit time.
