# Landing Analysis: PLAN-PR-036 — The exit-code convention stops at the skill boundary

epic: review-apparatus
workstream: WS-03
pr: **#1423 + #1429** (a review-driven split of #1419)

> Landing record for one shipped plan. Written by `analyze` after corroborating every material
> claim against ground truth. Source: inbox `exit-code-convention-stops-at-the-skill-boundary-007.md`
> (`kind: landing`, `landing-check complete: true`, `missing_keys[0]`), plus an operator paste.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| #1423 merged | **corroborated** | `ci pr view` → `state: merged`, `merge_commit_sha: 0fde908d03e0a6f0ffef15cede6d71fd6ce83d42` |
| #1429 merged | **corroborated** | `ci pr view` → `state: merged`, `merge_commit_sha: de10dfa97d7b7d391582cacb5530f9fba49f0236` |
| #1419 superseded, not merged | **corroborated** | `ci pr view` → `state: closed`, `merge_commit_sha: null` |
| 158-file footprint | **corroborated** | `git show --stat`: 95 files (#1423) + 63 files (#1429) = **158** |
| Net −549 lines | **not corroborated as a net** | The two merge commits show +553/−26 and +1746/−233. The −549 net is a claim about the *convention text* specifically, not about the diffs, and it is **not re-derivable from the commit stats**. Recorded as the sender's figure. |
| 4/4 deliverables | corroborated in count | Against a 4-deliverable spec. See below — the *payload* changed, not the count. |

⛔⛔ **The `pr` fact under-reports the landing by construction.** `landing-facts` carries `pr=1429`,
a single value, while this plan landed as **two merged PRs**. The producer did the right thing within
the schema — it preserved `step.branch-cleanup.pr_part1=1423`, both merge shas, and
`superseded_prs=1419,1428` — but a one-value `pr` key **cannot express a split landing**, and the
queue's `pr` row field has the same shape. Stamped as `1423,1429`; the schema gap is recorded as an
Open Defect.

## Deliverable Fidelity vs Spec

All four deliverables shipped. ⛔ **But D2 shipped the OPPOSITE payload to the one it was specified
with, and that redirect was the operator's at the review gate** — not a drift the plan chose:

| Deliverable | Verdict | Evidence |
|---|---|---|
| 1. Derive the executor-invocation population and classify each document | shipped-as-specified | `_exit_code_convention_derivation.py` (+469) in #1429 |
| 2. State the convention once canonically, and point every document at it | **shipped-INVERTED** | Spec D1 said *"the widened form, verbatim"*, which produced an insert of the three-clause block into **131 documents (+1602/−10)**. Shipped instead as **one body** at `tools-script-executor/standards/exit-code-convention.md` (+140) with a one-line reference elsewhere — a **net removal** |
| 3. State the `ci` exit-code rule once in `tools-integration-ci/SKILL.md` | shipped-as-specified | #1423 |
| 4. Guard the derived population with a test that publishes its size | shipped-as-specified | `test_exit_code_convention_population.py` (+317), `test_exit_code_convention_derivation.py` (+534) |

⭐ **The spec was right about the gap and wrong about the remedy.** Recorded because a future reader
comparing spec to landing would otherwise read D2 as a deviation rather than as a correction.

## ⛔⛔ The most valuable carry-out: a shrunken declaration gates which lessons a plan can SEE

`lessons-consult` **ran, succeeded, and searched exactly ONE component** (`tools-integration-ci`),
derived from a **9-file declaration against a realized 158-file footprint**.

Lesson `2026-08-27-16-005` carries `component: plan-marshall:phase-6-finalize`, and **its proposed
action is verbatim what the operator later redirected the plan to do.** It came from **PR #1356 — the
immediately preceding plan** — and was invisible because its component fell outside the shrunken
consult set. **Cost: a six-hour detour.**

⇒ **Under-declared `affected_files` does not merely mis-measure — it GATES what the plan can learn.**
This epic already knew under-declaration was the dominant residual class of the disjointness gate
(≈ two thirds of touched files never declared). What is new is that the *same* under-declaration
silently narrows the lessons population, and **a successful `lessons-consult` return is
indistinguishable from a complete one.**

⛔ Compounding it, candidate-lesson `-005` reports that **`affected_files_recall` is EASIER TO PASS the
more the declaration under-records** — the metric that would have caught this rewards the defect.

## Routing and Merge Behavior

- **Review**: CodeRabbit — 7 findings, 5 fixed, 2 taken-into-account. ⛔ `review-retrospective`
  returned **`indeterminate`** with **`reviewer_coverage: 0/3`** because the `pr-comment` store was
  **empty**: `automatic-review` does not follow a PR split, so the findings filed against #1419 were
  not carried to #1423/#1429 (finding `01ff9a`).
- **CI/merge**: all checks green; both parts merged via the queue.
- ⛔ **CodeRabbit refused the unsplit PR on a hard 100-file cap and the recovery cost ≈ 4.5 hours.**

### ⛔⛔ Two prior beliefs of this epic are REFUTED by this run — recorded so they are not re-derived

1. **Closing and reopening a PR does NOT push the CodeRabbit window.** Converting the stated ETAs to
   absolute instants: #1419's `12:49:31 +38m` and #1428's `13:06:37 +21m` **both resolve to
   `13:27:3x`** — the same instant, 6 seconds apart, **spanning a close and a fresh open.** The window
   is **ORG-scoped**, so any other PR in the org spends the same bucket; no reset mechanism is needed
   to explain a later shift.
   ⇒ **This corrects lesson `2026-09-05-07-008`**, promoted by this orchestrator on 2026-09-05, whose
   technique rested on trigger-PR churn. The lesson has been amended in place, not deleted.
2. **The four review refusals were NOT all quota.** Three were **91–94 minutes apart**, which an
   hourly quota cannot explain. The real cause was the **verb**: `@coderabbitai review` is the
   INCREMENTAL verb and returns "Review rate limited" when there is **no unreviewed commit**.
   ⇒ **What worked was `@coderabbitai full review`, accepted in 10 seconds on the same PR and the same
   HEAD.** The fix was a verb change, not waiting.

### ⛔ A bot refusal is a MUTABLE surface

#1419's original comment said *"158 files, 58 over the limit of 100"*. **The same `issue_comment` was
later EDITED IN PLACE** and now carries a rate-limit body describing a **63-file diff that did not
exist when it was posted**. ⇒ Any corpus that reads refusal bodies after the fact is reading a
surface that can be rewritten under it — and this epic's standing note that *"the corpus measures a
dead config"* now has a second, sharper form: **the corpus may measure a body that was edited after
the event it describes.**

## Metrics and Anomalies

- **Tokens**: 2,845,626. **Duration**: 128,056 s ≈ **35 h 34 m wall / 2 h 35 m worked.**
- ⛔ **Four defects were found INSIDE guards this plan wrote to close a completeness gap** — a vacuous
  `assert X == X`, a false universal, an order-dependent classifier, and a reachability-first test
  that would accept a forbidden heading. Two caught locally, two by CodeRabbit. **43 % of CodeRabbit's
  findings landed on the coverage claim of the instrument itself.** This is the epic's
  *vacuous-guard-introduced-by-its-own-fix* archetype, at n≥4 in a single plan.
- ✅ **Bounded gap declared, not hidden**: 24 `manage-*`-only documents keep their narrower section and
  are dropped by retention rule (c); the standard names the carve-out and the docstring records that
  it is a **scope boundary, not a sufficiency claim.**

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1423,1429` — from PR state, both parts
- [x] row `landing` stamped `landings/PLAN-PR-036.md`
- [x] row `plan_marshall_plan_id` stamped `exit-code-convention-stops-at-the-skill-boundary`
- [x] Lesson `2026-09-05-07-008` **amended** with the close/reopen refutation
- [x] Open Defects recorded; `truthful-signals-050` folded into PLAN-PR-026 D3
- [x] **NEW PLAN-PR-052** staged from the four refusal-surface findings
- [x] START-HERE and Ordered Queue regenerated; resume_anchor updated

## Follow-Ups

| Follow-up | Where it went |
|---|---|
| Refusal-message conflation, incremental-verb dead end, mutable refusal bodies, split-blind review pipeline | **NEW PLAN-PR-052** |
| The quorum passes identically when every required reviewer yields nothing | **PLAN-PR-026 D3** (from `truthful-signals-050`) |
| `affected_files` under-records ⇒ gates lessons-consult; `affected_files_recall` rewards it | Forwarded to `truthful-signals` — ⛔ **but it is the direct cause of this epic's own disjointness-gate residual**, so it is recorded here too |
| change-ledger dead since 2026-09-04; `build_time` all-zero block; loop-back stamps no metrics boundary; guards reproducing their own gap | Forwarded to `truthful-signals` |
| Registry pin `0.1.1592` vs cache `0.1.1613` — **widened by this finalize's own sync** | Open Defect; **operator-only repair** |
