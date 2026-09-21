# Landing: PLAN-PR-010 — Landing message carries the outcome post-merge

epic: review-apparatus · workstream: WS-04 · shipped 2026-08-12 (**as a refutation**)
cloud run: `cloud-runs/080-landing-message-carries-the-outcome-post-merge/`
PR #1196 (`6b9233092`) — *"docs(review-apparatus): refute plan 080 — landing emission already
post-merge"*

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.** Nothing shipped but the plan directory and the report
— two files under `doc/plans/**`, 120 added lines, **no source change**.

## The refutation's TRIGGER is sound; its CLOSURE is not

**Trigger — genuinely false premise, not a weak read.** `lessons-capture.md` carries `order: 991`
against `branch-cleanup`'s `order: 70`; ascending order is runtime order
(`_manifest_validation.py:409`); and `git log -p` shows exactly one change to the field, `-order: 60` /
`+order: 991`, in `e1ae3814`. That is the gate's literal *"has since moved"* trigger.

**Where the evidence is weak is one layer up:** the report attributed the move to sibling plans
040/050 (#1165/#1170/#1175) and never named the commit that actually did it. Re-verified first-party:
`e1ae38142 fix(phase-6-finalize): reorder post-run-review steps after the merge gate (#1080)`.

**Deliverables: 6 — 0 done, 2 partial (D0, D4), 4 closed as moot (D1, D2, D3, D5). Verification finds
each of the four NOT satisfied.**

## ⛔⛔ The defect the plan named most emphatically is LIVE

`080 G1`, severity **blocker**: a landing is emitted for a run whose merge did not land.

Mechanism, verified: all six `branch-cleanup` terminal branches record `--outcome done`; only A and E
record `merge_mechanism`; nothing halts the loop; `emit-landing` (order 1000) emits unconditionally.
`branch-cleanup.md:1068` states this consequence in its own words. **`merge_mechanism`'s presence is
the only landing/non-landing discriminator, and it is named at the consuming site only as an example,
never as the rule.**

## Report claims the verification found false

- "Never-merges is already correct — a finalize that halts pre-merge never reaches order 991" —
  **refuted**, mechanism above.
- "The plan's own OUT-OF-SCOPE **forbade** the enrichment" — **refuted**; the clause constrains
  *labelling*, not existence. PR #1215 implemented exactly the labelled-as-own-report shape one day
  later. **This is a straight inversion of the plan's own text.**
- "D3 — already the documented invariant" — misleading; the invariant is per *finalize run*, the
  reported defect was three landings for one *plan*.
- "An independent verification sub-agent returned REFUTATION CONFIRMED on all six checks" —
  unverifiable; no persisted artifact, and its Q1/Q2 conclusions are contradicted by two of the
  verification's own checks.
- Residue "Nothing else open" — **false**; D1, D3 and four D5 tests were closed as moot rather than
  recorded.

**Not a report falsehood, worth recording so a later reader does not file it as one:** the report's D0
table lists `1000 | archive-plan`. Verified — that was **correct at the HEAD it read**; #1215 later
inserted `emit-landing` at 1000 and pushed `archive-plan` to 1100.

## Gaps: 11 — 10 full, 1 partial, 0 uncovered

- **partial**: **G5** (major) — PLAN-PR-028 delivers only the *documentation* half (stop
  `branch-cleanup.md:1801` claiming a re-entry that `:1068` says the terminal `done` suppresses). The
  mechanism choice — record `loop_back`, declare `head_dependent: true`, or accept operator-deferred
  cleanup — alters dispatcher control flow on **every** finalize run and goes to D6 as a proposal. The
  third clause is additionally barred by PLAN-PR-028's own out-of-scope. **Needs an operator decision
  → staged as PLAN-PR-033.**

## Standing facts

- ⭐ **A refutation's trigger and its closure are separately assessable.** The gate fired for a real
  reason, yet four of six deliverables were closed as moot, one on a straight inversion of the plan's
  own out-of-scope text. **A verify-first gate licenses closing the PLAN, not closing every DEFECT it
  named.** Adopt as a standing epic rule.
- ⭐ **PLAN-PR-028 deliberately overrides one gap's prescription, and is right to.** `080 G3` proposed
  a `sender_id`-scoped landing-uniqueness key; D2 scopes it on **`target_plan`**, because a retry or
  re-entered finalize arrives with a different `sender_id` and would file a second landing for the same
  plan. **Read the plan's key, not the gap's.**
