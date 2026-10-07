# Landing Analysis: PLAN-PR-025B — Arm the refusal recovery that has never run

epic: review-apparatus
workstream: WS-01
pr: **#1433** (+ post-hoc follow-up **#1441**)

> Landing record. Written by `analyze` after corroborating every material claim against ground truth.
> Source: inbox `arm-the-refusal-recovery-that-has-never-run-008.md` (`kind: landing`,
> `landing-check complete: true`, `missing_keys[0]`), plus an operator paste.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| #1433 merged as `29a3dad1c` | **corroborated** | `ci pr view` → `state: merged`, `merge_commit_sha: 29a3dad1cebf654982a7b98ea256cf3bf8fa64f2`; 37 files, +4781/−247 |
| #1441 merged as `05ca6fe7b` | **corroborated** | `ci pr view` → `state: merged`, `merge_commit_sha: 05ca6fe7bc6f8c1877faf1feb9cdeda569c57b6f`; 4 files, +279/−2 |
| #1440 closed unmerged (review scaffolding) | **corroborated** | `ci pr view` → `state: closed`, `merge_commit_sha: null`, title *"REVIEW-ONLY (do not merge)"* |
| #1431 replaced by #1433 | **corroborated** | `step.create-pr.pr_number=1431`; `pr=#1433` stamped from PR state |
| 5/5 deliverables, 9/9 tasks | corroborated in count | Against the staged spec |

## ⛔⛔⛔ The run reported a review that never happened — inside the plan shipping guards against exactly that

The orchestrator stated *"CodeRabbit round 4 came back clean"* for commit `1af15958`. **CodeRabbit's
last completed review covered only `d75ded9e`**; the account-scoped quota refused the rest.

- A **`count_stored: 0`** finding-fetch was read as *reviewed and clean* when it meant *not reviewed*.
- A **fresh `cause=quota` refusal** was dismissed as a known stale comment.
- Caught **only** by `project:finalize-step-review-retrospective`, **after the merge**.

⇒ **This is this epic's own `nobody-reviewed`-vs-`reviewed-clean` collapse (PLAN-PR-026's whole
subject), reproduced inside the plan that was shipping guards against it.** The archetype is now at
n≥3 on this epic's own plans, and this instance is the strongest: the plan had the guard in its hands.

### ⛔⛔ The SUBSTRATE, and it is a producer defect — fixing the consumer leaves it live

The plan's own artifact shows **`reviewed_commit_sha` re-stamped at FETCH time**:

| Comment id | Distinct shas it appears under |
|---|---|
| `IC_kwDOQ3xasM8AAAABS4ng4A` | **three** |
| `PRRC_kwDOQ3xasM7rTFi6` | **two** |

**Every consumer reads that field as *which commit this review covered*.** It is in fact *which commit
was HEAD when we last fetched*. The two coincide only when the fetch happens to run during a covered
window — which is precisely what a refused window is not.

⭐⭐ **This settles a standing operational warning this ledger has carried in prose** (*"never run the
producer FIND during a refused window — it falsely stamps `reviewed_commit_sha`"*) into a located
producer defect with first-party evidence. Staged as **PLAN-PR-053**.

## The remedy the run performed, and the recipe it produced

A scaffolding PR (**#1440**) between two throwaway branches at the endpoints of the unreviewed delta
obtained the missing review. It found a **Major** — `parse_toon` **deleting the first character** of a
shallow-indented block-scalar payload, character-level corruption of the shared TOON transport,
**reported by nothing** — plus a Minor. Both fixed in **#1441**.

⭐⭐ **The recipe is reusable and is promoted to the lessons corpus.** `@coderabbitai review` on a
merged PR is refused (*"Pull request is closed"*). A PR between throwaway branches at the delta
endpoints works, **but the `@coderabbitai review` comment is MANDATORY** — auto-review does not fire on
a non-default base branch. ⭐ That same base-branch filter is *why* the technique sidesteps the heavy
`verify` workflow: `python-verify.yml`'s `pull_request:` trigger filters on the base being `main`.

## Reviewer yield — the strongest data point this epic has

**CodeRabbit found FOUR Majors across three rounds that five self-review rounds, a clean 37-rule
plugin-doctor gate, and six whole-tree verifies all missed:**

1. cap bypass across PRs;
2. an `escalate_exhausted` arm with **no correct reachable path**, discarding a paid-for claim;
3. `.strip()` corrupting bodies in the close-and-reopen path;
4. the `parse_toon` truncation above.

⇒ Direct corroboration of PLAN-PR-011 (*review bots catch what in-house gates cannot*, shipped #1239)
at a higher yield than the original. ⭐ Item 2 is notable on its own: **an escalation arm with no
reachable correct path** is the same shape as PLAN-PR-052's `refusal_structural` finding — two
unreachable escalation arms in the same subsystem, found independently.

## Metrics and Anomalies

- **Tokens**: 19,482,607. **Duration**: 162,168 s ≈ **45 h 02 m wall / 5 h 04 m worked.**
- ⛔⛔ **`total_tokens` IS A FLOOR, and `any_phase_missing_end_time=false` does NOT make it settled.**
  Three channels went dark over `6-finalize` — the phase that did the most work: **no accumulator
  file, no dispatch-boundary file, and `check-dispatch-audit` classified 16/16 finalize steps
  `no_evidence`.**
  ⛔ **This corrects a reading in `landings/PLAN-PR-042.md`**, where this orchestrator recorded
  `any_phase_missing_end_time=false` as making that total *"a real figure, not a floor"*. The flag
  attests to phase **end-times**, not to accumulator coverage. Corrected there in place.
- ✅ The 90-minute wait was **armed but never spent** — the quota window reset on its own, so **1 of 6
  recovery attempts** was used and the claim was **released**. The recovery this plan shipped worked
  on the plan that shipped it.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1433` — from PR state, **not** from `step.create-pr.pr_number=1431`
- [x] row `landing` stamped `landings/PLAN-PR-025B.md`
- [x] row `plan_marshall_plan_id` stamped `arm-the-refusal-recovery-that-has-never-run`
- [x] **NEW PLAN-PR-053** staged from candidate-lessons `-001` + `-002`
- [x] Recipe `-003` promoted to the lessons corpus
- [x] `-005` folded into PLAN-PR-050 D2; `one-format-…-001` and `test-suite-anti-vacuity-001` folded
      into PLAN-PR-043 D7 and PLAN-PR-052 D3
- [x] `landings/PLAN-PR-042.md` corrected on the `any_phase_missing_end_time` reading
- [x] START-HERE and Ordered Queue regenerated; resume_anchor updated

## Follow-Ups

| Follow-up | Where it went |
|---|---|
| Zero finding-fetch read as clean; `reviewed_commit_sha` re-stamped at fetch time | **NEW PLAN-PR-053** |
| Post-hoc review recipe for an already-merged delta | Promoted to the lessons corpus |
| ETA phrasings unparsed — now **4 distinct phrasings on one PR**, from 3 independent sources | **PLAN-PR-043 D7 limb A** |
| `ci pr wait-for-comments` cannot see an in-place refusal edit | **PLAN-PR-052 D3** |
| `6-finalize` records neither accumulator nor dispatch boundary | **PLAN-PR-050 D2** |
| `extract-chat-signal` forges its own envelope; gates that read a document cannot catch an unexecutable one | Forwarded to `truthful-signals` |
| `c27d28` macOS skip gate | **Already transferred by the plan itself** — not re-filed here |
| `pr` fact stale for the **third** time (#1431 → #1433) | Recurrence on the existing Open Defect |
