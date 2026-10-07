envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-06T19:51:07Z

# Forward from `review-apparatus` — 6 candidate-lessons from PLAN-PR-036's finalize, plus the one that cost six hours

Source: inbox `exit-code-convention-stops-at-the-skill-boundary-001` … `-006`, filed first-party by
that plan during its own finalize. It shipped as **#1423 + #1429** (a review-driven split of #1419),
merged `0fde908d0` and `de10dfa97`, **158 files** across the two parts.

⛔ **Notification and hand-off, NOT a transfer.** Nothing is staged or transitioned in our ledger for
any of these. Routed to you by the three-way test: **none carries a PR-or-review subject.** What we
KEPT is listed at the end so you can see the split and not duplicate it.

⚠ **Six items, one forward — split them as you see fit.** They are not one measurement, so this is a
bundling, not an aggregation.

---

## ⭐⭐⭐ Item 1 — `-001`: an under-recorded declared footprint silently shrinks the lessons-consult population

**This is the highest-value item we have forwarded you, and it cost that run a six-hour detour.**

`lessons-consult` **ran, SUCCEEDED, and searched exactly ONE component** (`tools-integration-ci`) —
derived from a **9-file declaration against a realized 158-file footprint**.

Lesson `2026-08-27-16-005` carries `component: plan-marshall:phase-6-finalize`, and **its proposed
action is verbatim what the operator later redirected the plan to do.** It came from **PR #1356 — the
immediately preceding plan** — and was invisible because its component fell outside the shrunken
consult set.

⇒ **Under-declared `affected_files` does not merely mis-measure — it GATES WHAT A PLAN CAN LEARN.**
⛔ And a successful `lessons-consult` return is **indistinguishable from a complete one**: it reports
that it searched, never that it searched everywhere it should have.

⚠ **Why we are flagging rather than just routing it.** This is the direct cause of our own
disjointness gate's dominant residual class — we measured roughly **two thirds of the files a landing
touched were never declared**, and we have a live Open Defect recording that our union-with-spec
workaround cost five plans a sequencing they did not need. **The same under-declaration feeds both
surfaces.** The defect is yours (footprint recording + consult-set derivation); the blast radius
reaches our gate, and a fix on your side retires a defect on ours.

## ⭐⭐ Item 2 — `-005`: `affected_files_recall` is EASIER TO PASS the more the declaration under-records

The metric that would have caught item 1 **rewards the defect it should detect.** Pair it with item 1
— they are one story, and fixing the recording without fixing the metric leaves nothing watching it.

## Item 3 — `-002`: the change-ledger has accepted no row since 2026-09-04, and the freshness gate reads it

**8 daemon builds in that run, zero rows** — derived from the append-only max timestamp, **not
sampled.** `pre-commit-verify-freshness` reads that ledger.

⚠ **The run's own gate PASSED on a corroborated entry**, so the writer is **not uniformly dead** —
which makes this **intermittent rather than total**, and intermittent is the harder shape: a gate that
usually works is trusted when it does not.

## Item 4 — `-003`: `build_time` emits a populated all-zero block carrying no substrate discriminator

⭐ Your *"which zero is this"* archetype, in a new producer: the block is present and fully populated
with zeros, so a consumer cannot tell *measured zero* from *nothing was measured*.

## Item 5 — `-004`: a phase loop-back stamps no metrics boundary, so `re_entered_phases` reports an empty list

A declared field with a guaranteed empty value on every looping run. ⚠ We hold a near-twin on our side
(`PLAN-PR-050` D2: finalize dispatch boundaries never stamp `returned_with_findings`) — **same shape,
different producer.** Check whether one fix covers both before staging.

## Item 6 — `-006`: guards written to close a completeness gap reproduced the gap they were closing

**Four defects were found INSIDE the guards that plan wrote** to close a completeness gap: a vacuous
`assert X == X`, a false universal, an order-dependent classifier, and a reachability-first test that
would accept a forbidden heading. Two were caught locally, **two by CodeRabbit**, and **43 % of
CodeRabbit's findings on that PR landed on the coverage claim of the instrument itself.**

⭐ This is the *vacuous-guard-introduced-by-its-own-fix* archetype at **n ≥ 4 in a single plan** — the
densest single-run instance either epic has recorded. ⚠ Adjacent to our `PLAN-PR-030` (*the
instruments that measure our gates report only what they measured*), but the component here is the
plan's own test guards, not the review instruments, so it is yours.

---

## What we KEPT (so you do not duplicate it)

| Subject | Where it went |
|---|---|
| Refusal-message conflation; `refusal_structural` unreachable at default config; bot refusals are MUTABLE; `automatic-review` does not follow a PR split | **NEW `PLAN-PR-052`** |
| The participation quorum passes identically when every required reviewer yields nothing (your `-050`) | **`PLAN-PR-026` D3a** — folded, not staged, exactly as you asked us to check |

## Two refutations from that run, recorded because they were OUR beliefs

- ⛔ **Closing and reopening a PR does NOT push the CodeRabbit window.** #1419's `12:49:31 +38m` and
  #1428's `13:06:37 +21m` **both resolve to `13:27:3x`** — the same instant, 6 seconds apart, spanning
  a close and a fresh open. The window is **ORG-scoped**. Our lesson `2026-09-05-07-008` has been
  amended in place rather than deleted.
- ⛔ **The four refusals were not all quota.** Three were 91–94 minutes apart. The real cause was the
  **verb**: `@coderabbitai review` is INCREMENTAL and refuses when there is no unreviewed commit.
  `@coderabbitai full review` was accepted in **10 seconds** on the same PR and HEAD.
