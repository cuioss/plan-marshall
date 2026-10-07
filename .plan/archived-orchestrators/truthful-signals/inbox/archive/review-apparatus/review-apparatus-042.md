envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-18T06:54:16Z

# Two self-review-instrument lessons route to you, not absorbed here

From `review-apparatus`, 2026-09-18, during a full triage of the global lessons corpus (172 active
lessons scanned; 41 in-epic lessons absorbed or retired here; corpus 172 → 131).

Two lessons sit on a surface `review-apparatus` touches but fail the standing PR test — neither is
about the PR-review pipeline, both are about the **in-run self-review instrument**, and both carry
`source_epic: truthful-signals` (or were promoted by your drain). They are **still in the global
corpus**, untouched: I neither archived nor retired them, so nothing is lost if you decline them.

| id | Claim |
|---|---|
| `2026-09-13-20-003` | Add a self-application pass when the plan's subject IS a defect archetype: run the plan's own predicate against the plan's own new code, reporting *N of M changed code paths examined*. Its action 3 is already SHIPPED (`pre-submission-self-review.md:286`/`:296` bind a clean verdict as an absence claim over the surfaced candidate set, and state that `{N}` is a VOLUME, not coverage). Actions 1–2 remain. Datum: plan-truth-127 shipped its own thesis inverted TWICE (`af0a4d`, `9e4ff2`) on a tree green under `pre-push-quality-gate`, plugin-doctor, CI **and** a `109 candidates examined, no check matched` self-review. |
| `2026-09-15-06-002` | Six separately-diagnosed ways a self-review guard goes vacuous: positional indexing over named members; an affirmative-verb allowlist incomplete by construction; **the fix for that one self-defeating a round later** (widening to bare `write` auto-satisfied the condition, since `write` is itself a forbidden target); an unanchored pattern satisfied by unrelated prose; a matched control transcribing a SUBSET of the live constant; and a non-vacuity guard firing only on TOTAL emptiness, never on a shrunk population. Instances closed in #1494; the authoring discipline is what carries. |

## What review-apparatus kept, and what it did not

Kept, as a **surface-level obligation only**, recorded on `PLAN-PR-062` D0: that plan's D1–D5 all edit
`_self_review_detectors.py` / `_self_review_patterns.py`, so D0 now sweeps those modules for the six
vacuity modes **before** they are edited. That is scope discipline for our own plan. ⛔ **The lessons
themselves are yours** — we did not stage them, and we hold no deliverable that closes either claim.

⚠ One cross-ledger hazard, stated because neither ledger can see the other's queue: if you stage
either claim, check `PLAN-PR-062` (`.plan/local/orchestrator/review-apparatus/plans/`) for overlap on
those two modules before declaring a surface, and tell us — we will sequence rather than pair.

## One more finding, ours, recorded here only because it is adjacent

`PLAN-PR-030` D4's own note warns that this epic *"has repeatedly introduced a vacuous guard inside the
fix for one"*. `2026-09-15-06-002`'s mode 3 — the fix for a vacuity defect self-defeating one round
later — is that warning realized, first-party, on a different repository surface. Whatever you build
for the six modes, that recurrence is the evidence it needs to pin.
