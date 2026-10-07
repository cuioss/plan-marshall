# Landing Analysis: PLAN-TRUTH-074 — Spec corpus review and cleanup entry point

epic: truthful-signals
workstream: WS-01
pr: #1134

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth. Drained from inbox message
> `spec-corpus-review-and-cleanup-entry-point-008.md` (`kind: landing`,
> `landing-check` → `complete: true`, `missing_keys[0]`).

## Ground-Truth Corroboration

The landing message is a lead, not a fact. What was checked, and how:

| Claim | Verdict | Evidence |
|-------|---------|----------|
| PR #1134 merged as squash `c0bbd2d8b` | **corroborated** | `git log --grep="#1134"` on `main` → `c0bbd2d8b feat(marshall-orchestrator): add cleanup verb for spec-corpus reconciliation (#1134)`. Verified against git history, NOT against the step's landing message |
| 9 deliverables, all done | **corroborated** | `manage-solution-outline list-deliverables` → `deliverable_count: 9`; phase 5 `done`; `tasks_completed: 14` |
| `total_tokens=5432972` is a floor at n=5/6 | **corroborated, then superseded** | True at emission. `record-metrics` has since run: 6-finalize closed at 3,573,359, plan total **5,787,862**, `any_phase_missing_end_time: false` |
| `emit-landing` absent from this manifest | **corroborated, root cause REFINED** | See Open Defect D-074-a below |
| `steps` grammar ambiguous for namespaced IDs | **corroborated (latent)** | `landing-payload-spec.md:97` defines `steps` as comma-joined `{step}:{outcome}` and states no split rule. 5 of 22 step IDs contain a colon. No current consumer splits the value — `landing-check` only tests key presence — so the ambiguity is real but not yet biting |

## Deliverable Fidelity vs Spec

The staged spec carried **10 deliverables (D0–D9)**; **9** landed. This is not a shortfall:
the spec explicitly pre-authorized the collapse — *"D7's report and D8's block-validation both
emit verdicts against `status.json`; if outline finds one mechanism serves both, that is a
collapse to 9, not two implementations."* Outline found exactly that.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — boundary, verb name, apply-policy | shipped-as-specified | `orchestration-model.md` § Cleanup Contract carries the verb-name settlement, the subject boundary, and the five-row apply-policy table verbatim |
| D1 — enumerate corpus, re-ground vs HEAD | shipped-as-specified | `corpus enumerate` (bidirectional, `rows_without_spec` / `specs_without_row` kept separate); `cleanup.md` Step 3 (A1) |
| D2 — applicability / already-fixed | shipped-as-specified | `cleanup.md` Step 4 (A2) — LLM step, per the spec's "one seam per mechanism, not one seam per deliverable" design |
| D3 — ambiguity | shipped-as-specified | `cleanup.md` Step 5 (A3) |
| D4 — duplication, both directions | shipped-as-specified | `corpus cross-check` (sibling epics + live plans); `cleanup.md` Step 6 (A4) |
| D5 — distribution / regrouping | shipped-as-specified | `cleanup.md` Step 7 (A5) |
| D6 — verb wiring + phase order | shipped-as-specified | Router table, `workflow/cleanup.md`, Canonical invocations block; `cleanup restart-check` seam |
| D7 — report, idempotence, tests | shipped-as-specified | `test_cleanup_contract.py`; idempotence asserted with a matched control |
| D8 + D9 — un-hand-writable block, self-contradiction detection | shipped-COLLAPSED (authorized) | Landed as one deliverable: `resume-summary` self-validation + `test_resume_summary_self_validation.py` |
| — | **added-unplanned** | Landed #9: *make the architecture-hints reader reachable at phase-3-outline for `use_worktree` plans*. Origin: the operator's mid-finalize "Fix it in this plan" disposition of finding `5b1178` (declared cost: +1 execute cycle, +3 orchestrator-tier builds) |

**Verdict: full fidelity.** Every spec deliverable shipped; the one count difference is the
collapse the spec authorized in advance, and the one addition is an operator-gated scope decision
with its cost declared before the choice.

## Metrics and Anomalies

Figures below are the CLOSED totals (`record-metrics` ran during this drain's finalize), not
the floor the landing message carried.

- **Tokens**: 5,787,862 total (n=5/6 phases; 1-init carries no token row).
  Per phase — 2-refine 143,813 · 3-outline 742,244 · 4-plan 417,078 · 5-execute 911,368 ·
  **6-finalize 3,573,359 (61.7%)**.
- **Duration**: 7h26m worked · 320h23m wall · 312h56m idle (the plan spanned 2026-08-09 → 08-22
  across several sessions).
- **Billing**: 73,955,161 weighted, population n=1/6 — 6-finalize only, and only because `enrich`
  ran in this drain's session. Five phases carry no billing figure.

**Anomalies:**

1. **Finalize consumed 61.7% of plan tokens against 16.8% for the phase that did the work.**
   Against the `single_module + feature` anchor (1.0M watch / 1.6M error) the plan came in at
   **3.6× the error anchor**. All four fallback ratios tripped.
2. **144 build invocations for a 16-file change** — 4h27m, 62.4% of all script wall time.
   Builds + CI + CI-polling = 92.3% of script wall time.
3. **Zero waste in the failure sense**: 20 finalize dispatches, all `step_complete`, zero error,
   zero retryable. The spend was the cost of the work as configured, not of thrashing.
4. **One defect class re-found three times.** `regex_overfit` in `orchestrator.py`'s markdown
   scanner: filed → fixed → re-filed twice (`e62e54` → `da5425` → `2cc20c`), each fix leaving a
   CommonMark clause the next round found (fence state, fence-close run length, delimiter
   indentation). Each fix shipped green tests sitting entirely on one side of the boundary the
   next finding crossed. **The epic's vacuous-guard archetype recurring inside its own fixes.**
5. **Q-Gate signal named a population that does not exist.** The dispatcher's gate reported 13
   pending findings; 13 were recorded and **0** were unresolved. "13 pending" and "13 recorded,
   0 pending" are different claims and only the second is true.

## Routing and Merge Behavior

- **Review**: 4 comments found by `automatic-review`; review-retrospective compared 3 reviewers
  (1 measured) over 10 actionable comments. All findings dispositioned — 2 `accepted`,
  5 `taken_into_account`, 0 `suppressed`, 0 pending at archive.
- **CI/merge**: all checks green; merged via **merge queue, squash strategy**. Three CI runs
  archived (31339017325, 31359625036, 31362783120). No rebase conflicts, no surface collision
  with a concurrent plan (R=1 throughout).
- **Parallelization consequence**: none. The plan ran alone; no disjointness verdict was tested.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-074 --status shipped`
- [x] row `pr` stamped — `1134`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-074.md`
- [x] row `plan_marshall_plan_id` stamped — `spec-corpus-review-and-cleanup-entry-point`
- [x] epic.md narrative reconciled; Open Defects opened (below)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Open Defects Opened by This Landing

**D-074-a — `emit-landing` never fired, and the stated cause is only half of it.**
CORROBORATED: `emit-landing` is `default_on: true, order: 1000` in bundle source and is absent
from this plan's 22-step manifest (composed 2026-08-09). The landing was emitted by
`lessons-capture` (order 991) instead — nine slots early, which is exactly why its token total
was a floor and its last five step outcomes read `pending`.
**REFINED, and this is the part the message did not have:** current `marshal.json` carries
`default:emit-landing: lane: off`. So a manifest composed **today** would also exclude it. The
message names manifest staleness; the lane exclusion is a **second, independent** cause with a
different fix. Its proposed remedy #1 — warn when a `default_on: true` step is missing from a
composed manifest — would, as written, fire on a step the operator has explicitly laned off.
⇒ Settle which of the two is intended **before** building the guard. Folded into PLAN-TRUTH-096.

**D-074-b — the change-ledger observed none of the plan's 144 builds, and the reason is now
narrower than the message could state.** The ledger lives at `.plan/work/change-ledger.jsonl`,
is **main-anchored, present, and readable post-worktree-removal** (433 rows) — so the message's
second hypothesis ("written where the retrospective reader cannot resolve it") is **REFUTED**.
Of the 433 rows, exactly **4** fall in the plan's active window (2026-08-09/10), and all four are
`run --help` probes carrying `plan_id: NO_PLAN`, `status: unknown`, `duration_seconds: null`.
Zero real build runs wrote a row. `--help` short-circuits before daemon routing; the plan's real
builds resolved `mechanism=daemon`. ⇒ **The ledger write is not reached on the routed/daemon
path.** That is now a single testable claim, not a two-way guess. Folded into PLAN-TRUTH-088.

**D-074-c — an owed `architecture enrich` hint names a module that no longer exists.**
`finalize-step-preference-emitter` filed an owed hint for module
`plan-marshall:marshall-orchestrator`. CORROBORATED stale: `architecture find "*orchestrator*"`
returns only `plan-orchestrator` paths; the rename shipped as PLAN-TRUTH-015 / PR #1162. The
orchestrator cannot discharge the hint itself — `architecture enrich` writes tracked descriptors
outside this epic's write boundary. Folded into PLAN-TRUTH-093 with the live module resolved.

## Watches Opened

**W-074-a — finalize cost concentration.** 61.7% of plan tokens and 92.3% of script wall time in
finalize, driven by 144 builds. `status.metadata.execution_profile_cost_preview` was never
recorded, so `check-routing-decisions` reported `comparison: not_attempted` — the plan had no
predicted cost to measure its actual spend against, and nothing in the run could observe the
anchor breach while it was happening. Watch until PLAN-TRUTH-088 records the preview.

## Follow-Ups

| Signal | Went to |
|--------|---------|
| Footprint resolver blind to squash landings (msg 001) | **STAGED** as PLAN-TRUTH-098 |
| `references.affected_files` never reconciled with post-outline scope (msg 002) | folded into PLAN-TRUTH-098 |
| Change-ledger recorded 0 build rows (msg 003) | folded into PLAN-TRUTH-088 |
| Per-dispatch context-load columns unfed (msg 004) | folded into PLAN-TRUTH-097 |
| Dispatch shape-violation check has no left-hand side (msg 005) | folded into PLAN-TRUTH-097 |
| Finalize cost concentration / no cost preview (msg 006) | folded into PLAN-TRUTH-088 + W-074-a |
| `emit-landing` absent from composed manifests (msg 007) | folded into PLAN-TRUTH-096 + D-074-a |
| Owed architecture hint, stale module name (msg 009) | folded into PLAN-TRUTH-093 + D-074-c |
