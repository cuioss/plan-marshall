# Landing Analysis: PLAN-PR-032 — Apply the cloud-plan-lane contract amendments, from outside the lane

epic: review-apparatus
workstream: WS-02
pr: #1416 — https://github.com/cuioss/plan-marshall/pull/1416

> Landing record for one shipped plan. Written by `analyze` after corroborating every material
> claim against ground truth. Source: inbox message
> `apply-the-cloud-plan-lane-contract-amendments-015.md` (`kind: landing`,
> `landing-check complete: true`, `missing_keys[0]`), plus an operator paste of the same run.

## Ground-Truth Corroboration

The landing message is a lead, not a fact. Every material claim was checked before any ledger write.

| Claim (from message / paste) | Verdict | Evidence |
|---|---|---|
| Shipped as #1416, merged | **corroborated** | `ci pr view --pr-number 1416` → `state: merged`, `merge_commit_sha: 5f810002571fc98f86479527be96c46391d630d3` |
| Merge commit `5f8100025...` | **corroborated** | `git log` → `5f8100025 chore(cloud-plan-lane): … (#1416)`; `git branch --contains` → present on `main` |
| #1411 closed WITHOUT merging | **corroborated** | `ci pr view --pr-number 1411` → `state: closed`, `merge_commit_sha: null` |
| Merged via merge queue | **corroborated (message-internal)** | `step.branch-cleanup.merge_mechanism=merge_queue`; not independently re-derivable post-merge |
| 6/6 deliverables | **contradicted in the denominator** | The spec declares **five** deliverables (D0–D4), not six. The run shipped a sixth the spec never staged. See Deliverable Fidelity. |
| Realized footprint = the declared one | **contradicted** | `git show --stat` → `.claude/skills/cloud-plan-lane/SKILL.md` **and `CLAUDE.md`**. `CLAUDE.md` was never declared. |

⛔ **This landing is the exact case the "stamp PR ids from PR state, never from the landing message"
rule exists for.** The message's own `step.create-pr.pr_number` is `1411` — a PR that closed unmerged.
Had the row been stamped from that step fact, the epic would carry a merged-plan row pointing at an
unmerged PR. The row below is stamped `1416`, read from PR state.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D0 — re-anchor all three proposals by quoted text; HALT if an anchor dissolved | shipped-as-specified | Run proceeded past the gate; no HALT recorded; D1–D3 landed against current spans |
| D1 — Step 7 verdict amendment (`reviewed-empty` + required/optional class), keeping `unreadable` row and `Reopens?` subsection | shipped-as-specified | `SKILL.md` +187 lines in the merged diff; the `Reopens?` subsection survives (candidate-lesson 014 reports a defect *inside* it, which proves it was kept) |
| D2 — Step 8 shortfall predicate naming its populations | shipped-as-specified | merged diff |
| D3 — § Report template gains a `Class` column and the two named ratios | shipped-as-specified | merged diff; candidate-lesson 014 names the report template's reviewer-participation table row verbatim |
| D4 — per-reviewer surface attribution; a verdict with no surface named is `unreadable`, not `silent` | shipped-as-specified | merged diff |
| (unstaged 6th) — narrow the `.plan/` access carve-out in `CLAUDE.md` | **added-unplanned** | `CLAUDE.md` +4/−4 in `5f8100025`; the Standalone Plan Lane table row now reads "Narrowed — … MAY `Read` git-tracked `.plan/` configuration … the git-ignored `.plan/local/` tree is absent and out of reach" |

**The added deliverable is sound work and it is also an undeclared surface.** `CLAUDE.md` is the
repository's highest-traffic contract file. It was not in the spec's `## Expected Surface`, so the
disjointness gate could not have serialized this plan against anything else touching `CLAUDE.md`.
That is the under-declaration residual class, observed live.

## Metrics and Anomalies

- **Tokens**: 4,790,971 total (message `total_tokens`, spans populations). Operator reports a
  billing-weighted 111.4M.
- **Duration**: 66,631 s ≈ 18 h 30 m wall (`total_wall_seconds`).
- **Finalize dominance**: 16 h 02 m of 18 h 30 m ≈ **70 %** in `6-finalize` — the single largest
  phase by an order of magnitude, and larger than when the epic first measured it.
- **Anomalies**:
  - `pre-submission-self-review` fired 6×, `automatic-review` 3×, `ci-verify` 3×, `push` 2×.
  - **Five PRs closed unmerged** (#1411–#1415); four (#1412–#1415) opened purely as CodeRabbit
    review triggers. Six trigger attempts across ~5 h for one review.
  - `2-refine` left recorded `in_progress` while the plan sat at `6-finalize`; `completed_phases: 4`
    where five are genuinely complete. The light planning lane never closed the phase.
    **Deliberately not repaired by the run** — the accurate record is that the machinery skipped it.
    Recorded here as an Open Defect rather than papered over.
  - Duplicate step record: `phase_steps["6-finalize"]` carries both `plan-marshall:plan-retrospective`
    and a bare `plan-retrospective`, inflating any count over `phase_steps`.

## Routing and Merge Behavior

- **Review**: 3 reviewers compared over 3 actionable comments. **CodeRabbit produced all 3**
  (2 Major, 1 Minor): `e4aea1` (no defined failure mode in the new `required_bots` reader — fixed,
  TASK-007), `ebea56` (partial de-duplication in the report template — fixed, TASK-008), and `89625f`
  (`.plan/` write enforcement in the lane — dispositioned `taken_into_account`, recorded as owed).
  `cuioss-review-bot` — the **required** bot — returned canned-empty again, reporting "no major issues
  detected" on the same head where CodeRabbit filed two Majors.
- **CI/merge**: merged through the merge queue as `5f8100025`. No rebase conflict reported.
- ⛔ **The merge crossed a review barrier under an explicit `barrier-ask-override`**, gap class
  `review-barrier-gap`, at head `30b32598457c9d221771392625b770c65853e71f`. The grant rests on
  `cuioss-review-bot`'s participation reading unproven **solely** through the known `head_sha_verified`
  comment-arm defect: `github_re_review.py:394` hard-codes `matched_signal == 'review'`, so the comment
  arm can never verify a SHA. **This is the THIRD occurrence of that defect on this epic's plans, and
  it is still unfixed.** The bot's own comment body names the reviewed commit verbatim.
- **Terminal commit unreviewed**: `30b325984` (the fix for self-review round 6's own two findings)
  shipped reviewed by nothing but `verify` — no bot review, no self-review round.

## Surface / Parallelization Consequences

- **No collision occurred.** PLAN-PR-042 ran concurrently and touches a disjoint surface
  (`automatic-review/`, `finalize-step-review-retrospective/`). `CLAUDE.md` and
  `cloud-plan-lane/SKILL.md` are outside it.
- ⚠ **The emit-time disjointness rationale was partly wrong on its facts, and is corrected here.**
  The 2026-09-04 emit recorded that PR-032's five sibling-epic overlaps (`PLAN-TRUTH-061`, `-063`,
  `-075`, `-081`, `-092`) were "all STAGED in that epic, NOT in flight". Re-read from
  `truthful-signals`' own queue: **061, 063, 075 and 081 are `shipped`; 092 is `retired`.** Only
  `PLAN-TRUTH-125` and `-129` (PR-042's overlaps) are genuinely `staged`. The *conclusion* — none in
  flight, so no live collision — held, but it was reached from a wrong reading and must not be
  reused as precedent. **A sibling-epic overlap is cleared by reading that epic's queue, never by
  assuming a status.**
- **Under-declaration recorded**: `CLAUDE.md` realized but never declared (see Deliverable Fidelity).
  The spec is now shipped, so its `## Expected Surface` has no consumer and is NOT retro-corrected —
  the same "a shipped spec's surface has no consumer" rule the 2026-09-04 cleanup applied.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-PR-032 --status shipped`
- [x] row `pr` stamped `1416` — **from PR state, not from `step.create-pr.pr_number=1411`**
- [x] row `landing` stamped `landings/PLAN-PR-032.md`
- [x] row `plan_marshall_plan_id` stamped `apply-the-cloud-plan-lane-contract-amendments`
- [x] Discharged proposals retired: **PLAN-PR-031 D5 items 1–3** and **PLAN-PR-026 D6's lane item**
      are now discharged by this landing, per PR-032's own Dependencies section. Recorded in
      `### Queue annotations`; leaving them staged would re-open the proposal-only loop.
- [x] Open Defects added (see `epic.md`): the `head_sha_verified` comment-arm defect (3rd occurrence),
      the `create-pr` stale-PR-fact producer gap, `finalize-step-preference-emitter` structural
      unreachability, and the `2-refine` phase drift.
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] resume_anchor updated

## Follow-Ups

| Follow-up | Where it went |
|---|---|
| `create-pr`'s `pr_number` goes stale when a run replaces its PR mid-finalize; `branch-cleanup` knows the real number but records it only in prose `display_detail` | Open Defect + folded into the landing-payload producer surface |
| `finalize-step-preference-emitter` is **structurally unreachable** for any review-driven or doc-only plan: `pr-comment` finding records carry no `module`/`component` field, so attribution always falls back to `default` and the gate always drops. The threshold knob is not the binding constraint | Open Defect — the missing attribution, not the threshold, is the subject |
| `head_sha_verified` comment arm cannot verify a SHA (`github_re_review.py:394`), 3rd occurrence | Open Defect; mechanism belongs to PLAN-PR-045's currency subject |
| `2-refine` left `in_progress`; `completed_phases` under-counts | Open Defect (light-lane phase closure) |
| 14 candidate-lesson messages from this run | Dispositioned individually in the same drain — see `logs/decision.log` |
