# Landing Analysis: PLAN-150 — Close the Architecture Slice Namespace Conversion

epic: test-quality
workstream: WS-02
pr: #1383 — https://github.com/cuioss/plan-marshall/pull/1383

> Landing record for one shipped plan. Lives at `landings/PLAN-150.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

> ⚠️ **This landing reached the orchestrator through the inbox, not through an operator
> paste.** The operator's paste covered PLAN-170 only; PLAN-150's landing was found by the
> drain. Had this round been run as a paste-only analysis, a fully shipped plan would have
> stayed recorded as `running`.

## Deliverable Fidelity vs Spec

The spec staged **four** deliverables (D1–D4); the landing reports **eight** shipped
(`deliverables_total=8`, `deliverables_done=8`). The expansion happened at `4-plan`, not
as unplanned scope: the eight executed deliverables are D1–D4 decomposed per directory
family, which is what the spec's own Scope Note asked for ("convert by directory and
commit per directory"). Recorded because the spec-to-landing count does not match.

The executed set, from a later operator paste, confirms the mapping is a decomposition and
not added scope — spec D2 alone accounts for five of the eight:

| Executed | Spec deliverable |
|----------|------------------|
| 1. Re-derive the population + install the reverse-order seam | D1 |
| 2. Convert `plan-orchestrator/` (214 sites) | D2 |
| 3. Convert `manage-architecture/` (54 sites) | D2 |
| 4. Convert `build-server/` (73 sites) | D2 |
| 5. Convert `plan-marshall/` + `manage-plan-documents/` + `manage-lifecycle/` (84) | D2 |
| 6. Convert `build-pyproject/` + `phase-2-refine/` + `phase-1-init/` (21) | D2 |
| 7. Parametrize the two tabular families (101 sites, 5 groups) | D3 |
| 8. Report the measured deltas | D4 |

The per-directory counts sum exactly: 214 + 54 + 73 + 84 + 21 = **446** converted, plus
D3's **101** parametrized = **547**, the re-derived population. That closure is what makes
the decomposition checkable rather than merely plausible.

⚠️ **Two `plan-orchestrator/` figures appear in this epic's records and they are not in
conflict.** The executed deliverable 2 names **214 sites**; the plan's own residue and
candidate lesson `-008` say `plan-orchestrator/` "alone held **277** of 547 (51%)". Both
are right and they count different things: 277 is the directory's total hand-built
population, of which 214 were converted under deliverable 2 and the remaining 63 fell to
deliverable 7's tabular parametrization. The concentration finding stands on the 277
figure — a future slice plan sized from a directory count rather than a measured
per-directory distribution will over-estimate.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — re-derive the population and the seam map (gating) | shipped-as-specified, target re-derived | `outcome.hand_built_namespace_before=547` — the re-derivation the ledger required, not the stale 506 the spec was sized against. `outcome.blocked_sites=0` confirms the retired PLAN-145 dependency. |
| D2 — convert, hoisting every call to module scope | shipped-as-specified | `outcome.hand_built_namespace_after=1`, `outcome.parse_ns_before=1 → after=78`. 47 modules converted; no `parse_ns` call inside a test body. |
| D3 — close the two remaining tabular families | shipped-as-specified | `outcome.simple_namespace_before=13 → after=13` (stated and unchanged, as specified); `outcome.collected_items_before=3905 → after=3909`. |
| D4 — report the measured deltas | shipped-as-specified | All six `outcome.*` keys carried on the landing payload; `outcome.whole_tree_verify_tests=23739`. |

**Surface under-declaration — and this one has a live consequence.** The spec declared 29
paths, all under `test/plan-marshall/`. The merge touched **48 files**, including
`test/conftest.py` (+12 lines, adding the shared `parse_ns` helper). `test/conftest.py` is
outside the declaration and is claimed by **PLAN-020, PLAN-090 and PLAN-110**. No live
collision resulted — PLAN-110 is staged, not running — but the gate would have passed a
PLAN-150/PLAN-110 pairing it should have sequenced. Corrected forward: see Follow-Ups.

## Metrics and Anomalies

- Tokens: **4,376,049** total (`total_tokens=4376049`), crossing the `broad + tech_debt`
  error anchor of 3.5M. The plan's own retrospective fired its `[BUDGET]` findings on
  **3,952,297** — a figure that excludes a whole phase, because `manage-metrics enrich`
  never ran. The verdicts hold a fortiori (the real number is higher), but they were
  reached on an incomplete measurement.
- Duration: 7h24m wall (`total_wall_seconds=26640`).
- Anomalies:
  - `1-init` recorded 32m1s of wall with **no worked figure**, and every column Total in
    `metrics.md` remains `(n=5/6)` — a floor, not a total.
    ⚠️ **Corrected against a later operator paste of the same landing:** the *token* half of
    this has since resolved. `1-init` now carries **43,551 (inline)**, because `enrich` ran
    after the retrospective measured it — `enrich` executes at order 996 and the
    retrospective measures at 995. The figure was genuinely absent at measurement time and
    is present now, which is the ordering artifact candidate lesson `-003` describes rather
    than a second gap. The missing worked figure and the `(n=5/6)` denominator are
    unaffected and stand.
  - `pre-submission-self-review` was dispatched without the `candidates` prompt-body field
    it declares under `requires_prompt_fields`. The leaf refused correctly, at a cost of
    **130,209 tokens** — the whole of `6-finalize`'s `error_total_tokens`, with
    `retryable_total_tokens: 0`. The dispatcher then ran the surfacer inline and
    re-dispatched; round 1 of the completed review found 4 defects the bots did not.
  - The assessment store was empty (`assessments_store_present: false`), so Q-Gate section
    2.2 could not be evaluated and `outline-vs-shipped` reported 48 of 48 realized paths
    as `touched_but_unassessed`.
  - Build attribution is entirely lost: 27 change-ledger build rows for the day carry
    `plan_id: NO_PLAN` while the plan's own log records 175 `pyproject_build` calls
    consuming 71.5% of its script time.
  - `steps` carries `archive-plan:pending`, but the plan **is** archived at
    `.plan/local/archived-plans/2026-09-02-plan-150-close-the-namespace-conversion` — the
    step list was emitted before archival completed. Not a defect.

## Routing and Merge Behavior

- Review: **external review contributed zero findings.** pr-agent posted "no major
  issues"; CodeRabbit posted "no actionable comments" with Merge Risk Minimal; Sourcery
  refused on diff size (cap 150,000 diff *characters* against 4,086 changed *lines* — the
  same unit mismatch PLAN-170 hit). `pre-submission-self-review` found 4 real defects the
  bots did not, all fixed in `4f8b0733a`. Together with PLAN-170's inverse result
  (CodeRabbit found everything, pr-agent nothing), the epic now has two data points saying
  the required/optional split does not track measured yield.
- CI/merge: merged as `80da16e30f6f49c8ff7212a303b2e7f9c867d740`, base `main`, head
  `feature/plan-150-close-the-namespace-conversion`. Verified via the CI abstraction
  (`ci pr view --pr-number 1383` → `state: merged`); the payload's
  `step.branch-cleanup.merge_commit_sha` matches exactly. No rebase conflicts.
  `step.finalize-step-sync-baseline.action=noop` with `upstream_commit_count=0`.
  The run merged past review-verdict defect `cc3ce9` on a HEAD-bound `barrier-ask-override`
  grant carrying the evidence, not by forcing the step.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-150 --status shipped`
- [x] row `pr` stamped `#1383`
- [x] row `landing` stamped `landings/PLAN-150.md`
- [x] row `plan_marshall_plan_id` stamped `plan-150-close-the-namespace-conversion`
- [x] epic.md queue reconciled from status.json
- [x] 12 inbox messages drained and archived (1 landing + 11 candidate-lessons)
- [x] **PLAN-155's `## Expected Surface` corrected** to declare `test/conftest.py` — the
      same-act obligation discharged, see Follow-Ups
- [x] Open Defect opened — review-verdict pair `cc3ce9` (detection) / `cf3722` (transport)
- [x] Watch opened — gate-versus-external-review yield asymmetry, now two-plan evidence
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **PLAN-155's declared surface was corrected in the same act as this reconciliation.**
  PLAN-155 is the identical conversion on PLAN-060's runtime slice and its declaration
  omitted `test/conftest.py` exactly as this spec's did. Since this landing proves the
  conversion adds a shared helper to that file, PLAN-155 would have repeated the
  under-declaration — and `test/conftest.py` is claimed by PLAN-020, PLAN-090 and
  PLAN-110, so the gate would have mis-predicted a PLAN-155/PLAN-110 pairing. Declaring it
  now makes the collision visible to the matcher instead of leaving it to be discovered by
  a rebase.
- **Re-cost the remaining WS-02 work.** The spec expected a second run and treated partial
  completion as acceptable; all eight deliverables landed in one. The distribution is far
  more concentrated than the spec assumed — only 9 of 29 enumerated entries carried any
  hand-built site, and `plan-orchestrator/` alone held 277 of 547 (51%). A future slice
  plan sized from a directory count rather than a measured per-directory distribution will
  over-estimate. The sizing error is in the run **count**, not the budget: this was one
  large run, not a cheap one.
- **`198a01` is deferred plan-sized work, not a defect this plan left broken.** The
  `_variant` helper is duplicated byte-identically across 38 test modules (~500 lines).
  Consolidating means one shared helper plus ~230 call-site renames plus per-file import
  pruning. Recorded as a candidate for a future staged spec, not folded into a live one.
- **Two production-relevant defects were exposed by the conversion, which is its whole
  point** — and both are already fixed in the merge: `test_phase_1_init.py` used lesson id
  `2026-04-15-099`, which `validate_lesson_id` rejects; `test_lifecycle_handshake_e2e.py`
  carried an unreachable stub branch matching `--task`/`task` where the CLI declares
  `--task-number`/`task_number`. Both were invisible to a hand-built namespace.
- **Out of scope by the spec, still owed elsewhere:** ~20 rule-invisible docstring B3
  citations (PLAN-130 owns that sweep tree-wide) and 10 `spec_from_file_location` preamble
  sites (PLAN-135). Both reported, neither fixed, exactly as the spec required.
