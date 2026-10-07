# Landing Analysis: PLAN-04 — Autonomy gate defaults

epic: operator-ux
workstream: WS-02-autonomy-defaults
pr: #1437 — https://github.com/cuioss/plan-marshall/pull/1437

> Landing record for one shipped plan. Lives at `landings/PLAN-04.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Input mode: inbox scan — **12 messages**, 11 `candidate-lesson` + 1 `landing`, all valid, all
drained and archived. `landing-check` on `-012.md` returned `complete: true`, `missing_keys: []`.
Corroborated against the operator's paste, git, and the read-side CI abstraction.

⭐ **The orchestration-context bypass did NOT recur.** PLAN-02 bypassed the inbox entirely and
PLAN-03 bypassed it for the retrospective's nine; PLAN-04 routed **all eleven** candidates plus the
landing here. Three plans, and the third is clean — the defect's remedy (corpus lesson
`2026-09-06-07-002`) reached the dispatcher.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. `_config_defaults.py`: `loop_back_without_asking` defaults to `true` | shipped-as-specified | `_config_defaults.py` +24; `.plan/marshal.json` reads `true` at HEAD |
| 2. A decision on `final_merge_without_asking`, landed either way with rationale | shipped, **location corrected** | The knob has **no default in `_config_defaults.py`** — it is declared in `branch-cleanup.md`'s `configurable:` frontmatter and resolved via `configurable_contract.py`. The spec assumed the seed file and was wrong; the plan corrected rather than worked around it |
| 3. The pause-gate census — every gate that can halt a run, with default, config path and keep/flip verdict | shipped, **artifact changed** | 25 gates in `doc/user/configuration.adoc` (+76). The keep/flip column did **not** ship there: self-review `20608c` established `keep`/`FLIP` are transitional information, which the Documentation Standards forbid in permanent user docs. The column became `Halt behaviour` (current-state) and the 25 verdicts moved to the PR body, which is a dated record |
| 4. Tests asserting the new defaults, plus a documented-equals-declared parity test | shipped-as-specified | `test_autonomy_defaults_documented.py`, **496 new lines** |
| 5. *(spec had 5; landing reports 4)* | re-cut | The spec's 1 and 2 are the landing's 1 and 2; spec 3 is landing 3; spec 4 and 5 fold into landing 4 |

⭐ **An operator decision overrode the outline's recorded verdict.** The outline recorded *keep
`false`* for `final_merge_without_asking` on three grounds — merging is outward-facing and
irreversible, `plan_without_asking` is the planning-side checkpoint and this the shipping-side one,
and the opt-in path already worked. The operator overrode it deliberately. The residual guards on
the now-default auto path are `pre_merge_comment_barrier` and the cross-plan merge mutex, both
recorded at the declaration site and in the PR body. Recorded here because a landing that silently
matched the outline would hide a real decision.

## Metrics and Anomalies

- **Tokens**: 6,689,612. **Wall**: 71,811 s = 19 h 57 m; operator reports 4 h 56 m worked.
- **Finalize consumed 55% of the plan's tokens**, outspending 5-execute **2.8:1** across 17 dispatch
  boundaries, driven by head-dependent steps re-firing on every HEAD advance —
  `pre-push-quality-gate` ×6, `automatic-review` ×5, `plugin-doctor` ×4. **None of those steps
  declares a `verdict_inputs` surface**, so the verdict-currency classifier can never narrow a
  re-fire. Third landing in a row to measure this; corpus lesson `2026-09-04-17-001` names the fix.
- **Steps**: 23 recorded; the facts block carries `archive-plan:pending` because `emit-landing`
  runs before it. The paste (later) reports it done. Not a defect — an ordering artifact of when
  the landing is emitted.
- ⚠ **The landing message names a merge sha that is not in main.** Its prose says *"merged via the
  platform merge queue at `ef6aff8357…`"*. That object exists (`git cat-file -t` → `commit`) but
  **`git merge-base --is-ancestor` reports it is NOT an ancestor of HEAD** — it is the merge queue's
  ephemeral commit, discarded when the queue squashed. The authoritative merge commit is
  **`c0e945d6a`** (`ci pr view --pr-number 1437`, and main's first-parent history). Anyone chasing
  the quoted sha later finds an orphan. Third member of a family this epic tracks: `2026-09-05-16-003`
  (a `--head-at-completion` resolving to no commit) and this run's own self-caught fabricated SHA.
- **Review**: `review_decision: none`; 2 CodeRabbit reviews, 7 findings, all handled;
  `review-retrospective` graded 1 of 3 reviewers measurable.
  ⭐ **CodeRabbit was required and was never demoted to `optional_bots`.** Only 1 of 10 quota waits
  was spent — and the run established the real blocker was a **missing trigger**, not a closed
  window, which is a materially better diagnosis than "we waited it out".

## Routing and Merge Behavior

- **Merged through the platform merge queue**, squash, `c0e945d6a`. `sync-baseline` rebased over 2
  upstream commits. No re-verify signals.
- **CodeRabbit's CWE-862 finding was declined, not fixed** — it argued that auto-admitting a
  `5-execute` loop-back runs fix tasks the planning approval never authorized. Declined on three
  grounds, with the concession recorded that the consent point genuinely moved, and two prior
  verification passes had settled the same question against the implementing dispatcher.
  ⚠ The plan flags this as **a design question worth revisiting rather than a settled review
  comment**, and this ledger agrees: deliverable 1 moved a human checkpoint, and the argument that
  it moved consent is not answered by showing the mechanism is bounded.
- **No surface collision occurred** — PLAN-04 ran alone; slot 2 was unfillable, not unfilled by
  choice.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` `#1437`; `landing` `landings/PLAN-04.md`;
      `plan_marshall_plan_id` `plan-04-autonomy-gate-defaults`
- [x] 12 inbox messages drained and archived, each with a logged disposition
- [x] 9 corpus lessons promoted (`2026-09-07-13-001` … `-13-009`); 1 discarded as a tracked
      recurrence
- [x] Open Defect **closed** — the awaitable-refusal coverage hole; `review_rate_window_await` is
      `true` at HEAD
- [x] Open Defect **closed** — the orchestration-context bypass; did not recur on this plan
- [x] Watch updated — declared-surface honesty, fourth measurement and the first improvement
- [x] epic.md reconciled from status.json; both generated blocks regenerated

## Follow-Ups

- ⭐ **Under-declaration fell to 44%, and the cleanup correction is why.** Declared 9 entries, **all
  9 touched**; realized 27, of which 15 are covered. The series is 71% → 78% → 67% → **44%**, the
  first improvement in the epic. The two entries added at the 2026-09-06 cleanup were both realized
  — `doc/user/configuration.adoc` at **+76 lines**, the plan's largest documentation deliverable and
  the whole of deliverable 3. Without that correction the census would have shipped entirely
  undeclared.
- ⛔ **One of my own cleanup judgements was refuted by this landing, and it was an explicit one.** I
  inspected `manage-config/standards/api-reference.md` and **excluded** it from PLAN-04's surface,
  recording the reason: *"its only mention (:181) cites the family as an analogy for
  `orchestrator.auto_emit` and states no default of its own."* The plan touched it — `:284` carries
  `final_merge_without_asking: false` inside a worked `step get` example, which is a site that
  states the default in exactly the sense deliverable 4 means. **The evidence was in front of me**:
  an earlier `architecture search --content` for `final_merge_without_asking` listed
  `api-reference.md` with 2 matches, and I then grepped only for `loop_back_without_asking`, got
  nothing for that file, and concluded it stated no default. A narrower second query overrode a
  broader first result. This is `2026-09-02-14-001`'s exact warning — verify by re-searching the
  literal, not by enumeration — applied to the orchestrator's own act.
- **11 undeclared realized files**: `api-reference.md`, `getting-started.adoc`,
  `parallelism-and-locking.adoc`, `phase-6-finalize/standards/branch-cleanup.md`,
  `standards/emit-landing.md`, `plan-marshall/standards/execution-recovery.md`,
  `workflow/execution.md`, `workflow/planning.md`, `standards/phase-lifecycle.md`,
  `test/conftest.py`, and two `test/plan-marshall/phase-6-finalize/` modules.
- ⛔ **Three deliverables shipped with no test verdict.** A timed-out focused build produced no
  result, the run continued as though verified, and the landing reports 4/4. Corpus lesson
  `2026-09-07-13-008`. The timeout path needs no misreading to reach.
- **Two unfixed machinery defects** carried correctly rather than patched: `automatic-review` Branch
  A's `mark-step-done` snippet omits `--force` (hit twice), and `review_completeness.py check`
  rejects its own documented invocation — the **third** instance of `2026-08-25-09-014`. Both routed
  to `finalize-machinery`.
- **`references.modified_files` is a retired shim whose step has no reachable input**: both
  documented inputs are unavailable by construction, on all three measured runs, while the step
  reported normally. Corpus lesson `2026-09-07-13-004`.
