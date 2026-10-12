# Landing Analysis: PLAN-LB-32 — Head-dependent step re-fire

epic: live-blockers
workstream: WS-01
pr: #1741 (https://github.com/cuioss/plan-marshall/pull/1741)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-32.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-32-head-dependent-step-refire-007.md` (kind `landing`,
`landing-check` `complete: true`; its surface delta is `unmeasured`, because neither a
declared nor a realized set was supplied to the check). Checked against:

- `ci pr queue-state --pr-number 1741`: `pr_state: merged`,
  `merge_commit_sha: ef7d366176e00193389ee3d2538282575e841ffb`, merge-group run `success`.
- The file list of the merge as it fast-forwarded into the ledger worktree: 13 files, 3793
  insertions, 341 deletions.
- A read-only review of the commit against the spec, deliverable by deliverable, by a
  delegated agent that ran nothing. Its verdicts are the table below.
- `manage-lessons list` on this machine on 2026-10-10: `total: 1, filtered: 0`.

Not read by that review: parts of `test_affected_lessons.py` (lines 400-535, 580-758), the
doc-contract test beyond line 310, the new plugin-doctor test beyond line 485, and the
plugin-doctor step document as a hunk-by-hunk diff (the current file was read). No test was
run here; the merge-group run is the evidence that the suite passes.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 — a re-fired step can ask what changed since its last firing | shipped-as-specified | `verdict_currency.py` gains the verb `changed-paths --plan-id --step`, which calls the existing `resolve_changed_paths`. `changed_paths` appears only on `outcome: computed`; `first_firing`, `last_firing_not_done` and `diff_unavailable` carry no such key. Tests use a real temporary repository; the recorded firing is a hand-built status record, not a real `mark-step-done` |
| 2 — housekeeping re-examines only the lessons a commit could affect | shipped, with a deviation that is a defect | `.claude/skills/finalize-step-lessons-housekeeping/scripts/affected_lessons.py`, verb `resolve`, selects a lesson when its file is newer than the last firing, when a changed path lies under its component's standards directory, or when a changed path contains a path the lesson names. "Edited since" is decided by file modification time, not by the content hash the spec's re-scope note required. The helper is imported by file path, not copied |
| 3 — one log line per firing for what was kept | shipped-as-specified | Step 6 keeps one entry per removal, promotion and adaptation and writes aggregate `firing summary` entries otherwise; doc-contract tests assert both |
| 4 — housekeeping reads the realized footprint | partly shipped | Step 1 calls `compute-footprint` with a row per named error, and two standards were corrected. Missing: `.claude/skills/recipe-plan-review/SKILL.md` lines 70 and 86 still tell the reader to use `references.json` `modified_files`, because the sweep test matches the `--field` form only; the `field_retired` error still does not name the replacement |
| 5 — plugin-doctor gates what the plan changed | shipped, with a deviation | Scope is the realized footprint united with the declared list, and a failed read of either forces whole-tree. Deviation: the whole-tree triggers were not left as they were — a new family was added (target registry, `plugin.json`, bundle agents and commands, the project instruction files). The derivation is prose, so the tests run a model of it pinned to the document's trigger table |
| 6 — plugin-doctor skips a re-fire that cannot change its verdict | shipped as the recorded refusal the spec allowed | The step document records the counter-example (`analyze_target_scope` reads content outside the gated directories) and states "No skip predicate is admitted. The step keeps the unconditional re-fire". No script, no skip test |
| 7 — the standard and the contract describe the lever | shipped-as-specified | `verdict-currency.md` § "Three levers, two columns" names the lever and both steps, one using it and one refusing it; `ext-point-finalize-step.md` gains the section on reading the change list. The three guard test modules are untouched |

Realized surface against the declared one: `source-edit-pushability.md` is outside the
declaration. The three project-step test modules were created under
`test/pm-plugin-development/` and not under `test/plan-marshall/` as declared — the operator
decided at plan time that tests live with the module that owns the code. The plugin-doctor
wrapper test moved there as well: all eight classes and eleven tests are present by name, no
coverage was lost.

## What the plan achieved against its objective

The objective was to make a re-fire of the two project steps cheap. On the evidence of this
landing it has not done that yet:

- **Plugin-doctor still re-runs in full on every fix commit.** The narrower skip rule was
  examined and refuted with a named counter-example, which the spec allowed. That is a sound
  result and it saves nothing.
- **Housekeeping's delta rule narrows the judging, not the dispatch.** Each re-fire is still
  a full dispatched envelope; the rule applies after the corpus has been enumerated with
  `manage-lessons list --full`, so every lesson body is still loaded before anything is
  narrowed.
- **The rule never ran on real lessons.** Every housekeeping firing of this plan found zero
  active lessons and left through the empty-corpus exit, which sits before the delta rule and
  records no firing time, so the next firing is a full run again. The rule is covered by
  tests only.
- **On its own run** the plan fired housekeeping 11 times and plugin-doctor 10 times, and
  finalize took 9.5 of 13.5 million recorded tokens (70 percent) over 46 dispatches.

## Metrics and Anomalies

- Tokens: 13,742,801. Duration: 57,075 seconds wall time (about 16 hours).
- The pre-submission self-review **closed by its verifier**: `acceptance=accepted`,
  `may_close=yes`, 0 blocking findings, 12 advisory notes left open. It is the first landing
  of this epic whose self-review did not need an operator close.
- `project:finalize-step-sync-plugin-cache` is recorded `failed`: the cache was synced to
  0.1.1894 while Claude Code's registry pins 0.1.1892 and repinning is disabled on this
  machine. All three installs synced and the executor was regenerated.
- Task planning ran twice: a quality-check finding moved five tasks' tests to another module,
  no verb edits a task's verification block, and all 13 tasks were cleared and re-created.
- `scope_creep_check` failed on all five passes; 150 to 161 residual files, all ledger paths.
- All 54 dispatch-boundary rows lack a step id, so finalize cost per step is an estimate.
- The lessons corpus showed 18 lessons at the plan's first outline pass and none afterwards.
  The plan could not say why. The cause is known here: the `lessons-routing` epic's two
  ingest runs of 2026-10-09 retired the corpus into its archive
  (`lessons-routing/lessons-archive/`).
- `archive-plan` is listed `n/a`. `cleanup_owed=false`.

## Routing and Merge Behavior

- Review: one comment (re-examine lessons when a plan-wide input changes) was declined as a
  design decision; a second was declined and recorded `accepted`, which the review
  retrospective reads as a false positive that belongs on `rejected`. The pull request
  body's review notes describe the first submission and were not updated for later rounds.
- CI/merge: merged through the merge queue; the merge-group run concluded `success`.
- Collisions with plans in flight: the commit changed `phase-6-finalize/SKILL.md` (30
  lines), which PLAN-LB-24 (running) declares, and
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md`, which PLAN-LB-33 (running) edits
  in its last deliverable. PLAN-LB-33 may now do that deliverable: the passage it targets is
  unchanged — the step still calls the worktree executor a symlink (lines 29 and 203) and
  its generation call (206-207) names no working directory.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-32 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-32 --field pr --value 1741`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-32 --field landing --value landings/PLAN-LB-32.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-32 --field plan_marshall_plan_id --value lb-32-head-dependent-step-refire`
- [x] epic.md narrative reconciled against the queue rows (queue annotations)
- [x] Watches updated: head-dependent steps (not retired), the regraded self-review (first
  close by verifier), harness installs
- [x] Open Defects added: the delta rule's three gaps; keyless dispatch-boundary rows
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated with the row change

## Follow-Ups

- **A lesson restored into the corpus can be carried over without ever being judged.**
  `affected_lessons.py` line 245 compares the file's modification time (line 339) with the
  last firing. `restore-from-plan` moves files and keeps the old modification time, which is
  the reason the spec's re-scope note required a content hash. No test covers it.
- **The delta rule runs after every lesson body has been loaded**, and the empty-corpus exit
  runs inside the dispatched step after five reads. Neither saves the dispatch.
- **Unconfirmed:** the imported helper resolves the bundles root by walking up from the
  working directory. If the step's script runs with the main checkout as working directory
  while it is given the worktree path, the standards directory resolves outside the
  repository, which forces a full run and withholds the firing time on every firing. The
  tests pin the root and do not exercise this.
- One document still names the retired `modified_files` field
  (`.claude/skills/recipe-plan-review/SKILL.md`).
