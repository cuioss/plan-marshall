# Landing Analysis: PLAN-PR-042 — The required reviewer returns an empty list on a correct full review

epic: review-apparatus
workstream: WS-03
pr: #1410 — https://github.com/cuioss/plan-marshall/pull/1410

> Landing record for one shipped plan. Written by `analyze` after corroborating every material
> claim against ground truth. Source: inbox message `required-reviewer-returns-empty-list-013.md`
> (`kind: landing`, `landing-check complete: true`, `missing_keys[0]`), plus an operator paste.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Shipped as #1410, merged | **corroborated** | `ci pr view --pr-number 1410` → `state: merged`, `merge_commit_sha: 4972615257305e5ccb79f1a1c19a72517a2c15c3` |
| Merge commit reachable | **corroborated** | `git log` → `497261525 feat(automatic-review): diagnose required-reviewer empty yield (#1410)`, 2026-09-05 15:19:52 +0000 |
| 3/3 deliverables | **corroborated in count, but against a 4-deliverable spec** | Spec declares **D0–D3**. See Deliverable Fidelity — the run shipped 3 and the spec staged 4. |
| `pr=#1410` sourced correctly | **corroborated** | `step.create-pr.pr_number=1410` **agrees** with the merged PR — unlike PLAN-PR-032, this run did not replace its PR, so the stale-fact trap did not fire here |
| 3-file change | **corroborated** | `git show --stat` → 3 files, +354/−14 |

## Deliverable Fidelity vs Spec

The spec staged **four** deliverables (D0–D3); the landing reports **3/3**. The three shipped
deliverables map onto D1–D3's subject matter, and **D0 (reproduce the null result under controlled
conditions) was not shipped as a deliverable** — the plan's Goal statement says why, and it is a
sound re-scope rather than a drop:

> *"Re-ground the required reviewer's empty-yield evidence against the live configuration before
> varying any knob, since the corpus it rested on measures a configuration this repository has
> since replaced."*

| Shipped deliverable | Verdict | Evidence |
|---|---|---|
| 1. Re-ground the required reviewer's empty-yield evidence against the live configuration | shipped, **supersedes D0** | `cuioss-review-bot.md` +235/−? in `497261525`; the re-ground replaced reproduction because the corpus measured a **replaced configuration** |
| 2. Derive the reviewer-state summary's bucket coverage from the state population | shipped-as-specified (D3's subject) | `cuioss-review-bot.md`, `test_review_completeness.py` +94 |
| 3. Record the settled three-state reviewer-outcome signal in the participation contract | shipped-as-specified (D2's subject) | `bot-participation-contract.md` +39 |

⭐⭐ **The re-scope is the epic's own standing lesson applied correctly.** *"THE CORPUS MEASURES A
DEAD CONFIG"* is a recorded finding of this epic, and this plan refused to A/B knobs against evidence
drawn from a configuration that no longer exists. Reproducing a null result under a dead config would
have been the wrong deliverable. **D1's knob A/B was therefore not run, and that is deliberate.**

## Surface: declared vs realized

| Path | Declared | Realized |
|---|:--:|:--:|
| `automatic-review/standards/cuioss-review-bot.md` | ✅ | ✅ |
| `test/plan-marshall/automatic-review/` | ✅ | ✅ (`test_review_completeness.py`) |
| `automatic-review/standards/bot-participation-contract.md` | ❌ | ✅ |
| `automatic-review/scripts/review_completeness.py` | ✅ | ❌ |
| `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py` | ✅ | ❌ |
| `test/plan-marshall/finalize-step-review-retrospective/` | ✅ | ❌ |

⭐⭐ **The live-plan arm of the gate was RIGHT and my union-with-spec reading was over-conservative.**
While this plan ran, `corpus cross-check`'s `live_plan` rows named exactly
`bot-participation-contract.md` and `cuioss-review-bot.md` — **precisely the two production files it
actually touched.** I treated that as a partial reading and cleared candidates against the union of
the live rows and the spec's five declared entries, which serialized PLAN-PR-025B (declared
`test/plan-marshall/automatic-review/`) behind a plan that did, in fact, write there — so that
sequencing was correct — but also serialized **PLAN-PR-026, -030, -031, -047, -048** behind
`review_completeness.py` and `review_retrospective.py`, **which this plan never wrote.**

⇒ **Recorded as an over-declaration cost, not as a gate failure.** The conservative reading lost
throughput; it did not admit a collision. ⛔ **But the general rule stands unchanged**: a running
plan's live surface can be partial (it grows as the plan works), so clearing against the live arm
alone remains unsafe. What this landing adds is that the *union* reading has a measurable cost, and
that cost is five plans sequenced behind two files.

## Metrics and Anomalies

- **Tokens**: 8,628,382 (`total_tokens`); billing-weighted **142,487,850**.
- **Duration**: 103,479 s = **28 h 44 m** wall, 6 h 31 m worked, 22 h 13 m idle.
- ⛔ **Finalize was 72 % of the run — 6.20 M of 8.63 M tokens for a 3-file change**, across
  **4 loop-back iterations** (ceiling 17) and **32 dispatched step firings**.
- ⛔⛔ **CORRECTED 2026-09-07 — this reading was WRONG and is retracted here.** This landing
  originally recorded `any_phase_missing_end_time=false` as making the total *"a real figure, not a
  floor"*. **That flag attests to phase END-TIMES and to nothing else.** PLAN-PR-025B's finalize
  demonstrated the gap: three channels went dark over `6-finalize` — no accumulator file, no
  dispatch-boundary file, and `check-dispatch-audit` classified **16/16 finalize steps
  `no_evidence`** — while that same flag read `false`. ⇒ **A green end-time flag does not make a
  token total settled**, and this run's 8.63 M is a floor for the same reason. Staged as
  **PLAN-PR-050 D2a**.
- ✅ **It converged.** `loop_back_iteration=4` of 17, against PLAN-TRUTH-089 which consumed all 17.

## Routing and Merge Behavior

- **Review**: `automatic-review` recorded **1 reviewed, 1 empty, 1 refused** across three configured
  bots. `finalize-step-review-retrospective` compared 4 reviewers over 4 actionable findings —
  **1 measured, 2 unmeasurable.**
  ⛔ **A merge that cleared the barrier is not evidence that three reviewers read this diff**, and the
  landing says so itself. This is the epic's own subject reproduced inside its own plan's finalize.
- **CI/merge**: all checks green; merged via the merge queue (squash) as `497261525`.

## Defects this finalize hit in its own machinery

1. ⛔ **`bd825d` recurred — SECOND confirmed occurrence.** After `branch-cleanup` merged and removed
   the worktree, `metadata.use_worktree` stayed `true` and `metadata.worktree_path` still named the
   deleted directory, so **every** later phase-entry assertion refused with `worktree_unresolved` and
   the finalize could not be resumed until it was hand-repaired with two `manage-status metadata
   --set` calls. Root cause: `worktree-remove` is **not the symmetric counterpart** of
   `worktree-create`, which sets both fields.
2. ⛔ **The post-run dirty-path guard's contract is wrong about itself.** It calls its finding
   "non-blocking", but the `qgate add` call it prescribes files under the **actionable** qgate type —
   which **blocked the archive** until it was resolved. It also fired identically against **5
   consecutive steps** for one file (`uv.lock`) that **none of them wrote**; the real cause is
   dependabot **#1417** raising the ruff specifier without refreshing the lock.
3. ⛔ **The plan's own subject component failed 5 times during its own finalize.**
   `review_completeness check` took 3 argparse rejections and 2 exit-1 internal errors. **The exit-1
   cause is ESTABLISHED, not pending reproduction** — both are deliberate `malformed_bot_flag`
   refusals: `--participated-bots cuioss-review-bot` passed a bare token where a
   `bot_kind:evidence_kind` pair is required, and `--refused-causes sourcery=quota` used `=` where
   `:` is the separator. ⭐ **This supersedes candidate-lesson 002's claim** that the cause needed
   reproducing; 009 settles it.
4. ⚠ **`manage-logging read --phase` appears not to filter.** Two reads with different `--phase`
   values returned the same `total_entries: 396`, and the shorter result was exactly the tail of the
   longer one — a vacuous-filter defect. Observed outside the emitting step's candidate population,
   so it carries no candidate-lesson and is recorded here.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1410` — from PR state
- [x] row `landing` stamped `landings/PLAN-PR-042.md`
- [x] row `plan_marshall_plan_id` stamped `required-reviewer-returns-empty-list`
- [x] Defects recorded in `epic.md` § Open Defects; two prior entries CORRECTED by drained messages
- [x] START-HERE and Ordered Queue blocks regenerated
- [x] resume_anchor updated

## Follow-Ups

| Follow-up | Where it went |
|---|---|
| `review_completeness`'s own invocation contract rejects its callers 5× in one finalize | **NEW PLAN-PR-051** (from messages 002 + 009) |
| Dirty-path guard names the step that ran, not the step that wrote — and calls itself non-blocking while filing as actionable | **PLAN-PR-050 D5** (from message 010) |
| `merge_lock rate-window check` ignores `--pr-number` and echoes a foreign PR's counter | **PLAN-PR-043** (from `preference-admissibility-prose-vs-auditor-code-001`) |
| CodeRabbit's ETA patterns cannot match its actual phrasing; ~3 h lost waiting on a reopened window | **PLAN-PR-043** (from `truthful-signals-049`) |
| The participation quorum lies in BOTH directions | **PLAN-PR-048** (from `truthful-signals-048` item 1) |
| A required bot with no re-trigger path cannot be waited out | **PLAN-PR-043** (from `truthful-signals-048` item 2) |
| 9 non-review candidate-lessons (retrospective/execute/outline/executor mechanics) | Forwarded to `truthful-signals`, discarded here |
| `bd825d` worktree-remove asymmetry, 2nd occurrence | Open Defect — **not staged here**: `workflow-integration-git` is outside this epic's subject |
