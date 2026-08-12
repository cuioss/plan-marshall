# Run report — 180-orchestrator-cleanup-verb (run 01)

**Date (UTC):** 2026-08-12    **Branch:** claude/orchestrator-cleanup-verb-pfchgq (harness-assigned)    **PR:** TBD    **Outcome:** in-progress

## Skills loaded

Loaded via the bundle-path route (the `plan-marshall` plugin route was not attempted; bundle paths always resolve in a fresh clone):

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:persona-implementer` (production code — work identity)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)
- `pm-plugin-development:plugin-architecture` (SKILL.md / bundle structure)

## Claim-label verification (the plan's HYPOTHESIS table, re-derived against HEAD)

The plan's "Expected surface" names `marshall-orchestrator` / `persona-marshall-orchestrator`; those
do **not exist** at HEAD. The skill is **`plan-orchestrator`** and the standard is
**`persona-plan-orchestrator`** — the `marshall-*` names anticipate a *rename plan* that has not run.
Per the plan's own sequencing note ("run this one first, because renaming a verb set is cheaper than
adding a verb to a renamed set"), this run works against the **current** names. Test path is
`test/plan-marshall/plan-orchestrator/`, not `.../marshall-orchestrator/`.

| Claim | Verdict | Evidence |
|---|---|---|
| START-HERE block carries `BEGIN/END GENERATED` markers + regeneration invocation | **CONFIRMED** | `templates/epic.md` lines 17-26 (`<!-- BEGIN/END GENERATED: resume-summary -->`); generator is `orchestrator.py cmd_resume_summary` / `_build_summary` |
| Ordered Queue table duplicates derivable columns with **no** generated-block guard | **CONFIRMED (count re-derived)** | `templates/epic.md` lines 39-46: table `# \| Plan \| Workstream \| Status \| Surface \| Notes` has no markers. Derivable columns are **5** (order `#`, Plan=id, Workstream, Status from status.json; Surface from the spec's Expected Surface), not "four status.json columns" — `Notes` is the one narrative/annotation column. Substance (unguarded derivable table) holds. |
| Decisions list duplicates the decision log with no stated authority | **PARTIALLY REFUTED** | `templates/epic.md` line 50-51 DOES state "also logged via manage-logging (decision verb)". But no *authority* is named. Re-derived as **narrative, not a derivable surface**: it carries rationale/alternatives a log summary need not capture, so regenerating from the log risks dropping narrative. → declare authority (D2), do **not** regenerate. |
| Five emitted verb-output counts are LLM-tallied and cannot be checked | **NOTED (motivation)** | Motivation for D4: the compact report's counts are script-derived, each with its population. |
| Operator-confirmed `running` state has no machine field and no liveness signal exists | **CONFIRMED (nuanced)** | status.json `plans[].status` *can* hold `running` (a machine field for queue status), but **no liveness source** observes whether a `running` plan is alive (`status-lifecycle.md` — no liveness field; `orchestration-model.md` § Parallelization: `launched → running` is *operator-confirmed*, not observed). A queue **row** is regenerable (mirrors status.json); a narrative **running-note** about liveness is **not** (no derivable source → regenerating fabricates a fact). |
| Prior gate enumerated 13 derivable vs 8 narrative across 7 files | **NOT REACHABLE** | Under `.plan/` (git-ignored, absent). Used only as a starting shape; re-derived the split for the epic.md **template** (in git): 5 derivable columns in Ordered Queue + START-HERE (derivable) vs Vision/Decisions/Open Defects/Watches/annotations (narrative). |
| Anchor rewritten 8× / >12 KB | **NOT REACHABLE** | Under `.plan/`. Motivation for the `resume_anchor` cut, not cited as evidence. |
| Verb-routing table exists and can take another entry | **CONFIRMED (superseded)** | `SKILL.md` § Verb Routing has 10 verbs incl. `cleanup`. See D1 — a `compact` **router verb** is **not** added; the standard already settles `compact` as the **stage** `cleanup` calls. |
| **No existing verb performs live-epic compaction** (asserted absence, higher-risk) | **REFUTED at the verb tier, CONFIRMED at the stage tier** | A `cleanup` verb **already exists** (`workflow/cleanup.md`), sequencing corpus → **ledger-compaction (Phase B)** → archive → restart. Phase B *calls* a compaction **stage that has not landed** (`ledger_compaction: not_available`; "do not re-implement it … no spec yet owns the compaction surface"). **This plan is that successor spec** — it implements the `compact` stage. |

## D1 — GATE decisions (name, relocation target, idempotence)

1. **Verb name — settled by the standard, honoured at the stage tier.** `orchestration-model.md`
   § Cleanup Contract already states: *"`cleanup` names the operator-facing orchestrator verb … `compact`
   names the ledger stage that verb calls … both correct at their own tier."* The plan recommended
   `compact`; the standard reserves exactly that name for exactly this stage. Resolution: keep `cleanup`
   as the operator/router verb (unchanged), implement `compact` as the **stage** — a new
   `orchestrator.py compact` subcommand + `workflow/compact.md` — and **do not** add a `compact` router
   verb (that would contradict the settled standard). All three surfaces (router, standard, workflow
   doc) already agree; this run lands the stage they name. *(This is the plan's D1 recommendation,
   placed at the tier the standard already fixed.)*
2. **Relocation target — a new `settled.md`.** `history.md` is `close`'s exclusive artifact (mid-life
   appends blur the freeze semantics the standard defines); `landings/` is per-plan and not every
   settled item maps to a landing. `settled.md` is the mid-life relocation home, a clear sibling of
   `history.md`. A pointer remains at each origin (D3).
3. **Idempotence — content-addressed for the derivable half, pointer-keyed for the narrative half.**
   The between-marker derivable content is a deterministic render of status.json + filesystem, so a
   second run produces byte-identical content and writes nothing (empty `regenerated[]`). A narrative
   item already carrying a relocation pointer at its origin is not relocated again. Both halves are
   no-ops on a second run.

## D2 — GENERATED-block mechanism extension + annotation-zone tension

- Ordered Queue table gets `BEGIN/END GENERATED: ordered-queue` markers around the **derivable columns**
  (`# \| Plan \| Workstream \| Status \| Surface`) in `templates/epic.md`; the per-row `Notes` move to an
  adjacent `### Annotations` zone **outside** the markers (mirroring the START-HERE `### Annotations`
  zone already in the template).
- **Annotation-zone tension resolved on the second horn**: the contract *permits an annotation zone
  outside the markers* (the START-HERE block already established this). This is documented in the
  standard so "GENERATED, never hand-written" and per-row caveats coexist without either destroying the
  other. Pasting verbatim output as-is would destroy the annotations → the zone is the answer.
- **Decisions authority declared, not regenerated**: the `logs/decision.log` append-only record is the
  authoritative source; the epic.md `## Decisions` section is a curated human-facing view carrying
  rationale/alternatives, so it is **narrative** and compact never regenerates it.

## D3 — settled-narrative relocation

- Judgement (which sections are settled) stays with the orchestrator/LLM and is **presented for
  confirmation on a first run** (per Out of scope). "Settled" = subject closed (shipped plan's residue,
  resolved defect), never merely old. Move is **verbatim** to `settled.md`, leaving a pointer at origin.
- The script provides the **pointer-reachability** invariant (every relocation pointer resolves to
  content in `settled.md`). `workflow/compact.md` documents the procedure.

## D4 — report

- `orchestrator.py compact` emits a structured TOON report: `regenerated[]` (surface, changed,
  before/after line counts), `invariants[]` (name, verdict, evidence, population), `abstained[]`
  (narrative sections left verbatim, with reason). All counts script-derived, each with its population.

## D5 — invariants + tests

- Script invariants: bidirectional queue↔spec reconciliation; no terminal (shipped/landed) row in the
  live Ordered Queue; relocation pointers reachable.
- Tests: idempotence (2nd run no-op), retraction survives verbatim, stale derivable row corrected,
  report names every mutation, **refuses on a closed epic**.

## Design note — compact writes epic.md in place

Unlike `resume-summary` (which *emits* a block for the LLM to paste, so a hand-edit divergence is
catchable), the `compact` stage's derivable regeneration is **fully deterministic and idempotent**, so
it writes epic.md between the markers directly and returns the diff. This is the orchestrator's own
deterministic ledger-writing arm invoked inline by `cleanup`; documented in the standard as a bounded
extension of the direct-file-write carve-out. Content **outside** the markers is never touched, which
makes "a retraction survives verbatim" a structural guarantee rather than a test coincidence. The
narrative-relocation half stays LLM judgement.

## Deliverables

All in commit `63b9630` (`feat(plan-orchestrator): land the compact ledger-compaction stage`).

- **D1 — GATE (name, relocation target, idempotence).** Recorded above. Verb name settled at the stage
  tier (`compact` stage, `cleanup` verb) — the standard's § Cleanup Contract already fixed it and all
  three surfaces agree; relocation target = `settled.md`; idempotence = content-addressed (derivable) +
  pointer-keyed (narrative). **Verified**: documented in `orchestration-model.md` § Ledger-Compaction
  Stage; idempotence proven by `test_a_second_run_is_a_no_op_on_disk`.
- **D2 — GENERATED-block to every derivable surface.** Ordered Queue table gains `BEGIN/END GENERATED:
  ordered-queue` markers + a `### Queue annotations` zone in `templates/epic.md`; `orchestrator.py
  compact` regenerates it (and the START-HERE block) in place. Annotation-zone tension resolved on the
  second horn (contract permits a zone outside the markers). Decisions declared narrative (authority =
  `logs/decision.log`). **Verified**: `test_the_epic_template_carries_every_generated_block_marker_pair`,
  `test_a_stale_queue_row_is_corrected_from_status_json`, `test_the_surface_column_is_derived_from_the_spec`.
- **D3 — relocate settled narrative with pointers.** Relocation is the orchestrator's judgement half,
  documented in `cleanup.md` § Step 8 (present-for-confirmation on first run, verbatim move to
  `settled.md`, pointer at origin). Script provides the `relocated_pointer_reachable` invariant.
  **Verified**: `TestPointerReachability` (resolved / no-file / missing-heading).
- **D4 — report what moved.** `compact` emits `regenerated[]`, `invariants[]`, `abstained[]`, each count
  script-derived with its population. **Verified**: `test_abstained_names_the_narrative_sections_left_verbatim`,
  `test_carries_three_invariants_each_with_verdict_evidence_population`.
- **D5 — invariants + tests.** Three invariants in the script; four required tests plus the closed-epic
  refusal. **Verified**: idempotence (`TestIdempotence`), retraction verbatim
  (`test_a_retraction_survives_a_pass_byte_identical`), stale row corrected
  (`test_a_stale_queue_row_is_corrected_from_status_json`), report names mutations
  (`test_regenerates_every_declared_block`), refuses closed epic (`TestRefusals`). Each failure mode was
  seen to fail pre-fix during authoring (e.g. the missing SKILL.md `### compact` block and the router
  closure both failed first, then passed).

**Deviation from the plan's Expected surface (recorded):** the Expected surface named a new
`workflow/compact.md`. That is **refuted** by the router-closure invariant
(`test_cleanup_contract.py::test_every_workflow_doc_on_disk_is_referenced`): every `workflow/*.md` MUST
be a Verb Routing table row, and `compact` is a **stage**, not an operator verb (the standard forbids
adding it to the router). So the stage has **no workflow doc**; its procedure lives in `cleanup.md`
§ Step 8 (Phase B) and its contract in `orchestration-model.md` § Ledger-Compaction Stage. This is the
`marshall-orchestrator`/`persona-marshall-orchestrator` situation repeating: the Expected surface
anticipated a shape the current tree does not have.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (orchestrator.py + the new test),
so the build takes its full path. `./pw verify plan-marshall` ran to **`=== verify: SUCCESS ===`** —
16097 passed, 1 skipped; coverage line confirms mypy(production, 277 files), ruff, SPDX headers,
mypy(test, 572 files), and module-tests[plan-marshall] all clean. Ran the direct `./pw` path (no
executor in this cloud clone).

## Findings

Recorded per instance. The Step 6 verification sub-agent (`general-purpose`) was dispatched three times
(find → fix → re-verify), which is the lane's fix-and-re-dispatch loop.

**Pass 1 (verification sub-agent).**
- All deliverables D1–D5: **PASS** (verdict named per deliverable; the D3 cold-read test returned A,B
  REGENERABLE / C,D PRESERVE — exactly the plan's mandated answers, so the written boundary does not
  invite fabricating a fact). Out-of-scope constraints all honored (never deletes; no `resume_anchor`
  reshape; no inbox foldering).
- **Finding (real, fixed):** three verb docs (`decompose.md`, `analyze.md`, `lessons-handling.md`) still
  instructed *hand-writing* the now-guarded Ordered Queue block — the doc-contract-divergence archetype
  this epic exists to close. **Disposition: fixed** in `8e160d3` by giving those verbs a render path —
  `resume-summary` now emits both derivable blocks (`ordered_queue` added), reusing `_build_ordered_queue`.
- **Finding (real, fixed):** stale `_registry_parity_signal` docstring claimed the compaction stage uses a
  `not_available` unowned-surface convention it does not have. **Fixed** in `8e160d3`.
- **Findings (minor, fixed):** double `_abstained_sections(original)` compute; `no_terminal_in_live_queue`
  docstring understated the markers-absent case. **Fixed** in `8e160d3`.

**Pass 2 (re-verification).** Points 1–3 confirmed clean. **Finding (real regression the Pass-1 fix
introduced, fixed):** making `resume-summary` a two-block emitter left several *consumers* pasting only the
START-HERE block — most seriously `close.md` (would freeze a stale Ordered Queue into `history.md`
permanently), plus `resume.md`, `orchestrate.md`, `analyze.md` (a back-reference), `landing-analysis.md`,
`persona SKILL.md`, and `init.md`. **Disposition: fixed** in `dbe474b` (all consumers paste/regenerate both
blocks). An independent `git grep` sweep then found six more single-block descriptions (SKILL.md Scripts row
+ Enforcement, argparse help, `orchestrate.md` status path, two headers) — **fixed** in `14e23a3`.

**Pass 3 (final focused re-verification).** _(result pending — recorded before the merge gate.)_

**CI / PR review findings:** _(pending — recorded at Step 7/8.)_

## Reviewer participation

_(pending)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

- **Owed work (recorded per plan):** the `resume_anchor` shape question is **cut** and needs its own
  plan (a different file/authority, operator-owed, and a dependency of other epic plans). The `inbox/`
  per-sender foldering is owned by the sibling inbox plan. Neither is implemented here.
