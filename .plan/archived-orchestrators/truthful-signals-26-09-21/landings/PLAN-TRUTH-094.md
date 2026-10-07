# Landing Analysis: PLAN-TRUTH-094 — plugin-doctor-detector-coverage-residue

epic: truthful-signals
workstream: WS-01
pr: #1343 — https://github.com/cuioss/plan-marshall/pull/1343

> Landing record for one shipped plan. Lives at `landings/PLAN-TRUTH-094.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Two inputs, one landing: the operator pasted the finalize report AND the plan filed a
`kind: landing` inbox message (`-008`, `revision: 1`). They describe the same PR, so this is
ONE reconciliation, not two. `inbox landing-check` returned `complete: true`, `missing_keys[0]`
— every required fact key supplied with a real value, no `n/a` and no `unknown`.

## Deliverable Fidelity vs Spec

Six shipped against six specified (D0–D5). The mapping is 1:1 and the ORDER differs from the
spec's — report items 3 and 4 correspond to spec D3 and D2 respectively. Verified against the
merged commit `1169fb5bf` (squash of the feature branch) rather than against the report's own
claim.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — GATE: re-derive rule population and per-rule substrate reachability | shipped-as-specified | `test/pm-plugin-development/plugin-doctor/test_rule_substrate_absence_census.py` (new in `1169fb5bf`); report item 1 |
| D1 — `analyze_argument_naming` reports unreachability, not cleanliness | shipped-as-specified | `test_argument_naming_absent_substrate.py` (new); `_analyze_argument_naming.py` modified; PR title is this deliverable |
| D2 — the anchor-vs-type-list control actually exercises `_scoped` (matched pair) | shipped-as-specified | report item 4; matched positive/negative pair also pins the post-convergence fix (`0abdc8713`) |
| D3 — publish `blind_spots` on a clean gate run | shipped-as-specified | measured `population_size: 2792`, `blind_spots: 304`; report item 3 |
| D4 — bind the mutation register and collateral list to a derivation | shipped-as-specified | report item 5 |
| D5 — record that a disposition surviving only on a PR thread is not recorded | shipped-as-specified | report item 6 |

**Unplanned surface.** The realized footprint is far larger than the declared one, in BOTH
directions — see `c6ad9f` under Follow-Ups. Nothing here reads as scope creep: the extra files
are the version-stamp sweep (40 files at ≤4 changed lines) plus the plugin-doctor test/reference
expansion the deliverables imply.

**⚠ Magnitude divergence between spec and shipped figures, NOT resolved here.** Spec D3 states
the clean gate publishes population `152` and `blind_spots` `69`; the landing measures `2792`
and `304`. Whether these are the same population measured differently or two different
populations is **not established** by anything in the landing or the spec — recorded as
Watch `W-094-a` rather than asserted either way. The spec labelled every claim `HYPOTHESIS` and
required D0 to re-derive, so a moved number is the contract WORKING; only the unexplained
~18× is open.

## Metrics and Anomalies

- **Tokens: 4,605,535 — a FLOOR, not a total, and the plan says so first-party.** `6-finalize`
  carries no end boundary because `print-phase-breakdown` executes inside the phase it reports.
  Finalize was this run's most expensive phase.
- **`manage-metrics enrich` walked 48 subagent transcripts and attributed 0.** None of ~20
  dispatches reached the breakdown table; the retrospective envelope alone was 313,010 subagent
  tokens. The real cost is materially higher than the headline (`011afa`).
- Per-phase (reported): 5-execute 3,400,443 / 1215 tool uses; 3-outline 614,520; 4-plan 421,929;
  2-refine 168,643. Wall 12h45m (n=5/6), worked 5h29m (n=4/6), idle 7h16m.
- **Anomaly — the settle band ran 17 rounds (11–27)**, findings per round
  1, 8, 7, 4, 6, 9, 4, 1, 1, 1, 0, 2, 4, 3, 11, 1, 0. The `round 27 clean` row is truthful but
  reads as one clean pass; the 11-finding round at position 15 is the shape that matters. The
  dominant defect class was **a fix's own replacement text being the next round's defect**, and
  the cycle broke only when claims were DELETED rather than qualified.
- Finalize: 22/23 steps done, 1 skipped (`lessons-capture`, `lane: off` in this plan's manifest).

## Routing and Merge Behavior

- **Review:** `automatic-review` triaged 16 items — 1 blocking fixed, 4 accepted, 2 declined,
  9 deferred. `finalize-step-review-retrospective`: CodeRabbit 6 fixed of 15 in R1; **R2 absent
  from the store** (`a02741` — see candidate-lesson `-007`).
- **⛔ The merge-candidate defect was caught by an OPTIONAL bot, after convergence.** 17 settle
  rounds converged to two consecutive clean results and every required check was green; the
  required reviewer reported "no major issues" on BOTH reviews. CodeRabbit's re-review found
  `_analyze_argument_naming.py` counting an UNDECIDED site as DECIDED — introduced by this
  plan's own commit `4ca2481a9` and missed by `77f493597`, whose subject reads *"close four
  coverage over-claims"*: it closed four and left a structurally identical fifth. Delegated to
  `review-apparatus` as `5bdbb9`.
- **CI/merge:** 11 required checks green at merged head, 0 failing, CodeRabbit SUCCESS.
  Squash-merged via the platform merge queue as `1169fb5bf`. `pr view --pr-number 1343` confirms
  `state: merged`, base `main`, head `feature/plugin-doctor-detector-coverage-residue`.
  1 conflict resolved during `finalize-step-sync-baseline` (6 upstream commits).
- **Surface collisions:** none observed against the other running plan (`PLAN-TRUTH-087`). The
  two are disjoint in fact as well as in declaration.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-094 --status shipped`
- [x] row `pr` stamped — `#1343`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-094.md`
- [x] row `plan_marshall_plan_id` stamped — `plugin-doctor-detector-coverage-residue`
- [x] epic.md queue reconciled from status.json
- [x] 12 findings from `-001` dispositioned; 6 candidate-lessons from `-002`…`-007` dispositioned
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

**Corroborated first-party this drain, and STILL LIVE on main:**

- **The `scan-planning-inventory scan` corpus defect is NOT fixed.** The landing says it was
  "hiding a live corpus defect"; `0abdc8713` fixed the DETECTOR that now sees it. Reproduced at
  HEAD `1169fb5bf`: `scan-planning-inventory scan --format summary` →
  `error: unrecognized arguments: scan`. Four documented sites still carry the bogus positional
  (`tools-marketplace-inventory/SKILL.md` lines 335, 349, 352, 355). ⇒ folded into
  **PLAN-TRUTH-101** as a FOURTH member, found by a fourth independent accident.
- **⭐ #1343 shipped the instrument PLAN-TRUTH-101's D0 population gate needs.** `-101` D0 requires
  the population be DERIVED first, on the grounds that its three known members were each found by
  a different accident — evidence the surface was never swept. The argument-naming rule now
  publishes `population_size` AND `blind_spots` over the real corpus, so that sweep is now
  mechanically performable instead of accidental. This is a dependency `-101` did not have when
  it was staged.

**Routed elsewhere:**

- `5bdbb9` (optional bot caught the merge candidate) → `review-apparatus`, per the three-way
  routing rule. The plan also filed its own `-001.md` there with 3 findings.

**Needs an operator decision, not scheduling** — both escalated via `AskUserQuestion`:

- **`7a3b32`** — seven documented rule ids have no emitter; two detectors run whose output nothing
  reads. Two reviewers disagreed on whether the `doctor-skills.md` sections documenting them are
  legitimate LLM-phase checks or documentation of rules that emit nothing.
- **`c6ad9f`** — Expected Surface over-declaration gating epic disjointness. **Sharper than
  reported, and wrong in BOTH directions**: 3 of 6 declared files never touched
  (`resolve_project_dir.py`, `doctor-marketplace.py`, `test_analyze_argument_naming.py`), while
  76 files with >4 changed lines actually landed against that 6-file declaration. The declared
  footprint over-declares AND under-declares; combined with the already-known `affected_files`
  under-recording, neither the declared nor the realized footprint is currently reliable as a
  disjointness input.

**Folded / staged — see the epic's Open Defects and the per-message decision log for the full
12-finding and 6-lesson disposition set.**
