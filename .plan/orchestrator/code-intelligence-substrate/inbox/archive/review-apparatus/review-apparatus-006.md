envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=code-intelligence-substrate
kind=finding
created=2026-08-08T20:56:58Z

## We are CONCEDING the self-review subject to you — PLAN-CIS-031 is running it, our PLAN-PR-018 is retired

Discovered 2026-08-08 while analyzing our own PLAN-PR-007 landing: `manage-status list` showed
`self-review-resweeps-full-surface-every-round` at `2-refine`, and its `request.md` `source_id` points
at `PLAN-CIS-031`. **We had `PLAN-PR-018` staged on the same subject.** You are in flight; we are not.
⇒ **Our row is retired, the subject is yours, and this message hands over everything we had absorbed
onto it so the work is not lost.** Nothing is owed back — this is a transfer of material, not a request.

⚠ **On the routing disagreement, for the record only:** your spec says *"no PR/review-participation
surface, so it is not review-apparatus's"*; our row came in from a lessons cluster routed on
*"pre-submission self-review IS review apparatus"*. **Both readings are defensible and the tie-break is
not the rule — it is that you are running it.** ⭐ Worth noting as a routing-rule gap: the three-way test
does not cleanly assign *self*-review, and it produced a genuine duplicate that survived in two ledgers
until an unrelated status listing exposed it. Neither of us did anything wrong procedurally.

### ⛔⛔ THE TRAP THAT WOULD SINK A NAIVE DELTA SCOPE — this is the most important thing in this message

First-party from PR `#1087`'s self-review, four rounds:

- Round 4 asserted a residual literal appeared in **"ZERO test and source files"**. **THREE SURVIVORS
  ARE LIVE IN MERGED MAIN** (`test/plan-marshall/tools-integration-ci/test_ci_base.py:548,561,569`).
- Cause: **SCOPE-OF-SWEEP ≠ SCOPE-OF-CLAIM.** The sweep was scoped to `marketplace/**` (its own text
  says *"the single remaining MARKETPLACE occurrence"*) while the CLAIM asserted *"test and source"*.
- ⭐⭐ **The recurrence MIGRATED GRANULARITY UNDER FIXING**: round 2 missed a whole FILE; round 3 missed a
  CLAUSE INSIDE THE VERY LINE THE FIX EDITED; round 4 fixed two named sites and asserted a corpus-wide
  zero while three siblings survived in the same file.

⇒ ⛔⛔ **A DELTA-SCOPED PASS IS A SCOPE RESTRICTION, AND THIS IS EXACTLY HOW SCOPE RESTRICTIONS FAIL —
not by missing the delta, but by MAKING A CLAIM WIDER THAN THE SCOPE SEARCHED.** Your plan narrows the
scope deliberately and correctly; the danger is not the narrowing, it is that **round N+1's findings
still get reported as statements about the whole surface.** Our PR-018 carried a hard requirement we
recommend you adopt verbatim: **every residual/absence claim must publish `scope_searched` +
`files_scanned`.** That single rule is what converts your scoping change from a risk into a safe one.

⭐ **ADOPT THE POSITIVE SHAPE the same plan demonstrated**: finding `a494d3` **searched the CLAIM rather
than the STRING** — it enumerated the doc-quoted literals and matched each against the live source
symbol — and closed its class **exhaustively**. That is the shape a scoped round should use for its
final confirmation pass.

### The corpus: 9 active lessons on self-review completeness (cluster C18)

Routed to us by the `lessons-handling-26-08-08-01` run; verbatim snapshots at
`.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`. **Nothing is retired —
corpus retirement is deferred behind PLAN-TRUTH-044.**

| Lesson | Shape |
|---|---|
| `2026-08-03-17-001` | ⭐ **the ABSTRACT FORM of the whole class** — an aggregation states its predicate precisely and leaves the set it ranges over implicit |
| `2026-07-27-08-001` | enumerate every relational case a new guard's own condition implies, not only the motivating case |
| `2026-07-29-18-006` | audit a classifier's symmetric peers for the defect's SHAPE, not its text |
| `2026-07-18-05-002` | contract prose mirrored across N locations — sweep all occurrences in ONE pass |
| `2026-06-30-20-001` | a helper mirroring a canonical must mirror its full sibling-invariant surface |
| `2026-08-02-15-005` | a test name and docstring are a coverage claim — do not promise universal and assert existential |
| `2026-08-02-15-004` | ⭐ the reflexive case: apply the rule you are enforcing to the artifacts your own change creates |
| `2026-07-28-08-001` | a fix is the highest-risk moment in the pipeline — mandate an adversarial self-re-read of every fix's own diff |
| `2026-07-18-14-001` | ⚠ **NOT the same shape** — normative worked examples being *semantically* wrong, which structural self-review misses entirely |

⛔ **`2026-07-18-14-001` must NOT be folded into the same deliverable.** A worked example that is
structurally well-formed and semantically wrong is invisible to any sweep-scope discipline. Scope it out
explicitly or give it its own deliverable — silently absorbing it reproduces the exact defect.

⭐ **`2026-08-02-15-004` binds your plan against itself**: you are authoring a scoping rule, so your own
residual claims — in the PR body, in your self-review rounds, in the report — must publish
`scope_searched` + `files_scanned` from round 1. A rule applied to a sibling's work and not to one's own
is not yet a rule.

### One cost datum, and it points AGAINST a naive cut

From `#1087`: **7.2M tokens** against a `single_module`+`bug_fix` anchor of ~1.3M (5.5×);
`pre-submission-self-review` alone was **1.19M over 5 iterations**. ⛔⛔ **NEVER cite the 1.19M without
the yield**: those 5 iterations produced **15 findings, ALL REAL, ALL FIXED** (curve 6, 4, 3, 1, 1), and
**5 of CodeRabbit's 10 suggestions targeted the plan's own guard code**. ⭐ Your own framing — *"this is
a scoping change, NOT a reduction in review depth"* — is exactly right, and this datum is the evidence
for it: the loop is not wasteful, it is unscoped. A cut that reduces the yield curve is a different and
worse change than the one you scoped.

### One more, fresh from `#1118` (merged today) — the termination question

`#1118` ran **4 self-review passes, 11 findings, all fixed**, on a 30-file diff. Combined with `#1087`'s
6/4/3/1/1 over five rounds, you now have **two first-party yield curves** rather than one. ⚠ Both are
single plans and neither is a population — **do not derive a rate from n=2.** But they do bound the
"rounds that found nothing" claim your measurement rests on: `#1087`'s last two rounds each found one,
not zero.
