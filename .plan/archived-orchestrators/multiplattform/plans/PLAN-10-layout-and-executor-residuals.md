# PLAN-10: The unowned layout, executor, host-signal and permission-grammar couplings

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** to close coupling-inventory rows that **no** staged plan claimed.
> Source evidence: `../reference/coupling-inventory.md` §B rows 3, 5, 6, 10, 11 and §C rows 5, 6.
> **WIDENED on an operator decision (2026-09-08)** from five rows to seven — see Objective.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

⛔ **This plan's scope premise was refuted, and the correction is now applied.** The spec claimed to
close *the* unclaimed §B/§C set; the set was derived at `1c4e6febb` as **17** rows, not five. The
operator's decision was to **widen to the derived set**. Widening it literally to all 17 would have
been wrong, and the reason is recorded here so nobody re-derives it: **the inventory's `Drawn by`
column is STALE**, because it is ledger-resident and no plan may edit it — PLAN-11's D4 was
report-only by explicit constraint. Counting rows whose `Drawn by` reads `—` therefore counts owned
work as unclaimed. Partitioned against the corpus at HEAD `b64db6671`, the 17 resolve as:

| Rows | Actual owner | Widen onto them? |
|---|---|---|
| 5 | **this plan already** (§B 3, 10, 11; §C 5, 6) | already here |
| 2 | **LANDED plans** — `extract-chat-signal.py` → PLAN-13 (#1376); `opencode_runtime` metrics boundary → PLAN-09 (#1405) | ⛔ no — already shipped |
| 8 | **other staged specs** — `_dep_index.py` + the plugin-doctor `.claude` anchors + `frontmatter-standards.md` + the `_cmd_apply`/`cmd_validate` slash-command emitters → PLAN-06; the 24-op no-op table → PLAN-07; `manage-metrics` prose, `manage-lessons` launch strings, the Claude-as-assistant prose → PLAN-12 | ⛔ no — would duplicate a sibling's declared surface |
| **2** | **genuinely unowned** — the `permission_fix.py` permission-DSL residue and `permission_doctor.py`'s enforcement half | ✅ **added below as D6 and D7** |

So the honest widening is **five → seven**, not five → seventeen. The two added rows are exactly the
two the epic's resume anchor has carried as UNCLAIMED for several rounds: the `permission_fix.py`
DSL residue, orphaned when WS-01 closed and unreachable by any chain, and `permission_doctor`'s
direct-script `detect-*` FALSE ZERO. ⚠️ The set GROWS as plans land — both of these were made
unowned by this epic's own landings — so "closes the class" is a claim this plan still must not
make. It closes the class **as partitioned at `b64db6671`**, and says so.

## Deliverables

1. **D1 — `marketplace_paths.py`'s fallback composer stops duplicating the runtime's.** `CLAUDE_DIR`, `PLUGIN_CACHE_SUBPATH`, `_DEFAULT_BUNDLE_CACHE_ROOTS` and `_DEFAULT_SKILL_ROOTS` compose the Claude layout a second time, beside the runtime-op composition, with nothing keeping the two in step. Either single-source the constants or add a lockstep test that fails when the two compositions diverge — and say which, with the reason, in the PR body.
   *Done when:* a deliberate divergence between the runtime-op composition and the fallback composition is caught by a test that fails red before the fix.
2. **D2 — `generate_executor.py::discover_local_scripts` resolves its root.** The build-time discovery root still hardcodes `.claude/skills` — while the *embedded* resolver the same file generates is already sanctioned-clean and multi-root. Make the discovery root target-aware the same way.
   *Done when:* no `.claude` literal remains in the generator's own discovery path; a test pins a non-default root.
3. **D3 — The executor's session-cache write gets a runtime home.** `generate_executor.py` writes `~/.cache/plan-marshall/sessions/{session_id}/active-plan` directly. The session identity and its cache location are host facts, not build facts. Route the write through a runtime operation, or record — with the reason — why it is genuinely host-neutral and belongs where it is.
   *Done when:* either the write routes through the seam, or the PR body carries a stated, evidenced justification and the inventory row is narrowed to that residue rather than retired.
4. **D4 — `HARNESS_BASH_CEILING_SECONDS` moves behind the runtime.** `tools-file-ops/scripts/constants.py` holds a Claude-harness ceiling as a core constant. PLAN-07 covers the *prose* that restates the value; this deliverable relocates the **constant itself** so a non-Claude target is not bound by a Claude harness's limit.
   *Done when:* the constant is runtime-sourced; every consumer reads it through the seam; a test asserts a different target can carry a different ceiling.
5. **D5 — `manage-files.py`'s IDE launch stops living in core file CRUD.** `detect_ide` and `cmd_open_in_ide` embed host-editor signal recognition inside the generic file-operations skill. Relocate behind the seam (the argument is per-host rather than per-target, but it is the same argument).
   *Done when:* `manage-files` performs no host-editor detection; the capability is reachable through the seam or honestly declined.

6. **D6 — `permission_fix.py`'s permission-DSL residue.** `EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, the `Skill(…)` / `SlashCommand(…)` wildcard generators, `TIMESTAMP_PATTERN` / `DATE_PATTERN`, `normalize_path_perm` and `is_individual_script_permission` render and parse Claude permission-DSL strings inside a general script. The *default* permission set already renders behind the runtime; this residue does not. ⛔ It carries **no path literal**, which is why every `.claude`-literal sweep in this epic missed it — it is the same grammar-in-a-general-script class as the `workflow-permission-web` row PLAN-14 closed.
   *Done when:* the DSL grammar is reached through the runtime seam or honestly declined per the no-op policy; a test asserts a non-Claude target does not receive Claude permission-DSL output. ⛔ Re-derive the symbol set before acting — it is a lead from the inventory, not a measurement.
7. **D7 — `permission_doctor`'s direct-script route stops reporting a FALSE ZERO.** The rule-pack *declaration* is already done and was deliberately kept rather than moved (PLAN-14 landing: relocation considered and rejected). ⛔ **What remains is enforcement, not declaration** — the declaration is structural, not a dispatch path, so the direct-script `detect-*` route still runs the Claude rules against a non-Claude target and returns a clean zero. That is an unchecked negative presented as a checked one, which is the exact `could-not-evaluate reported as a clean zero` class this epic has now recorded eight times. The documented `platform_runtime permission analyze` path is already honest; only the direct route is not.
   *Done when:* the direct `detect-*` route fails closed on a non-Claude target — returning could-not-evaluate rather than zero — with a red-first test that pins the distinction between "checked, found nothing" and "could not check". ⛔ Governing authority: **ADR-019**. Do NOT touch the three permission standards documents; their provenance declaration is settled and is not this deliverable's subject.

⚠️ **Split guard fired TWICE and was resolved as proceed-unsplit both times.** Seven deliverables. Rationale, recorded
as an epic decision: all seven are the same one-line-of-argument change (a host/target fact stops
living in a general script) applied to seven small, independent sites, each with a self-contained
test. The review burden is additive, not multiplicative, and splitting would produce seven PRs whose
individual value is below the cost of a review cycle. ⛔ **Seven exceeds the ~6 guard, and the
operator widened it knowing that** — the alternative considered and rejected was keeping five and
staging D6/D7 separately, which would have left the two rows unowned for at least another round
after they have already survived several. ⚠️ D6 and D7 are the two LEAST like the others: both are
permission-grammar work rather than layout/path work, and D7's remedy is a fail-closed dispatch
change, not a relocation. **If the outline finds D6+D7 do not share the implementation shape of
D1-D5, split them out as one spec rather than forcing the fit** — and record that as the second
resolution of this guard. ⛔ **If D3's investigation turns out to need a
new runtime operation, stop and report** — that is a genuine scope change and PLAN-09 owns the ABC.

## Out of Scope

- **`marketplace_paths.get_base_path`'s `global`/`project` scopes** — PLAN-07's D1. ⛔ Same file, different symbols. Touch only the fallback constants; report rather than fix if the two turn out inseparable.
- **The prose that restates the Bash ceiling** — PLAN-07's D3.
- **The plugin-doctor analyzers' `.claude` anchors and `_dep_index.py`** — PLAN-06's D4.
- **`platform-runtime`'s own scripts** — WS-01's surface. A needed operation is recorded and requested, never added here.

## Claim Labels

- OBSERVED, **line evidence refreshed at the 2026-09-06 re-grounding**: `marketplace_paths.py` carries the fallback-composer constants `CLAUDE_DIR`, `PLUGIN_CACHE_SUBPATH`, `_DEFAULT_SKILL_ROOTS` and `_DEFAULT_BUNDLE_CACHE_ROOTS`. ⚠️ **Locate by SYMBOL, not by the line numbers this claim used to carry** — they were `105, 110, 125, 136` and at `1c4e6febb` the real positions are **:105, :110, :134, :145**. PLAN-09 moved this file once already and these are PLAN-10's half of a three-owner file: touch only these constants.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: FIRST verdict ever stamped on this spec. Substance holds at 1c4e6febb - all four fallback-composer constants are present and are a distinct symbol set from PLAN-07's get_base_path scopes - but the LINE EVIDENCE was stale and is corrected in the claim text in the same act: the claim carried 105/110/125/136 and the real positions are :105, :110, :134, :145. PLAN-09 moved this file at its landing. Claim now instructs symbol-based location.
- ⚙️ **RE-SCOPED at the 2026-09-06 re-grounding — the count TWO is refuted; it is SEVEN.** `generate_executor.py` carries **7** `.claude/skills` occurrences at `1c4e6febb`, not 2, and `discover_local_scripts` is at **:405**. The SUBSTANCE holds — the function still hardcodes the project-local root while the same file's *embedded* multi-root resolver is sanctioned-clean, and the inventory still splits the two correctly. ⛔ Re-derive the hit set before acting; the figure here is a lead and has already drifted once.
  - verdict: contradicted | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: yes | evidence: Count refuted, substance holds; absorbed into the claim text in the same act. The claim asserted TWO .claude/skills hits in generate_executor.py; at 1c4e6febb there are SEVEN, and discover_local_scripts sits at :405. The hardcoded project-local root is still there and the file's embedded multi-root resolver is still the sanctioned-clean half, so what the claim asserts about the SHAPE is correct - only its cardinality drifted. The claim now instructs re-deriving the hit set rather than trusting the figure.
- OBSERVED: `generate_executor.py` writes a `cache/plan-marshall/sessions` path directly.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb. generate_executor.py documents the session-cache side effect at :66 (the ~/.cache/plan-marshall/sessions/{session_id}/active-plan path) and constructs a Claude cache root directly at :522 (Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'). The session-keyed side effect the claim names is present and is a live construction site, not merely a docstring mention.
- OBSERVED: `tools-file-ops/scripts/constants.py::HARNESS_BASH_CEILING_SECONDS` is present as a core-owned constant.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb: tools-file-ops/scripts/constants.py:35 carries HARNESS_BASH_CEILING_SECONDS = 600 as a core-owned constant, exactly as claimed.
- OBSERVED: `manage-files.py::detect_ide` / `cmd_open_in_ide` are present — **11** hits. Count is a lead.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb: manage-files.py carries exactly ELEVEN detect_ide / cmd_open_in_ide occurrences - the claim called 11 a lead and the lead is exact. Recorded as a measured match rather than an assumed one.
- HYPOTHESIS: none of D1–D5 needs a new `Runtime` operation — confirm/refute at `platform-runtime/standards/contract.md` (verify-at-outline). ⛔ D3 is the likeliest to refute this. A refutation is a **halt-and-report**, not a silent ABC edit: PLAN-09 owns the ABC.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Whether any of D1-D5 needs a NEW Runtime operation is a design question over contract.md and the five deliverables' eventual shapes, and no read of the contract settles it - the contract says what operations EXIST, not whether these five can be expressed within them. The claim names D3 as the likeliest to require one, and that flag is the useful part. ⚠️ Note the contract has MOVED since this claim was written: PLAN-09 added the decline vocabulary and PLAN-08 added seven permission_* operations, so the operation set D1-D5 would be measured against is materially larger than at staging. Verify-at-outline work, not a ledger derivation.
- ⚙️ **RE-SCOPED at the 2026-09-06 re-grounding — REFUTED, and by a wide margin.** The hypothesis read *the five rows above are the complete unclaimed §B/§C set*. Derived at `1c4e6febb` by counting rows whose `Drawn by` cell is unclaimed: **17**, not 5. ⛔ **This plan therefore covers a SUBSET, and its scope premise — that it closes the unclaimed set — does not hold.** Two of the seventeen were made unclaimed during this epic's own landings (the `permission_fix.py` DSL residue, orphaned when WS-01 closed, and the `permission_doctor` rule-pack enforcement row), so the set grows as plans land rather than shrinking. Decide deliberately whether this plan widens to the derived set or stays at its five and the remainder is staged separately — do not let the spec keep implying it closes the class.
  - verdict: contradicted | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: yes | evidence: REFUTED by a wide margin and absorbed into the claim text in the same act. The hypothesis read 'the five rows above are the complete unclaimed section B/C set'. Derived at 1c4e6febb by counting inventory rows whose Drawn by cell is unclaimed: SEVENTEEN, not five. So this plan covers a SUBSET and its scope premise does not hold. ⚠️ The set GROWS as plans land rather than shrinking - two of the seventeen were orphaned by this epic's own landings (the permission_fix.py DSL residue, unreachable once WS-01 closed, and the permission_doctor rule-pack enforcement row). The claim now says so and asks for a deliberate decision: widen this plan to the derived set, or keep it at five and stage the remainder. It must stop implying it closes the class.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` — D1, **fallback constants only**
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — D2, D3
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` and its consumers — D4
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-files/scripts/manage-files.py` — D5
- OBSERVED: `test/plan-marshall/script-shared/**`, `test/plan-marshall/tools-script-executor/**`, `test/plan-marshall/tools-file-ops/**`, `test/plan-marshall/manage-files/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — D6
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py` — D7, **the direct-script `detect-*` dispatch path only**
- OBSERVED: `test/plan-marshall/tools-permission-fix/**`, `test/plan-marshall/tools-permission-doctor/**`

⚠️ **The four entries added at the 2026-09-08 widening were swept against HEAD `b64db6671` before
staging** — all four resolve on disk. ⛔ **Explicitly NOT declared, and deliberately so:** the three
permission standards documents (`permission-architecture.md`, `permission-validation-standards.md`,
`permission-anti-patterns.md`). Their Claude-rule-pack provenance declaration is settled work from
the PLAN-14 landing; D7 is enforcement only and must not reopen it.

## Dependencies and Sequencing

- Depends on: **PLAN-07**. ⛔ Run after it. Both touch `marketplace_paths.py` — PLAN-07 routes `get_base_path`'s scopes, this plan closes the fallback constants in the same file. Running second means re-deriving what PLAN-07 left rather than assuming it.
- Overlaps with: **PLAN-09** on `marketplace_paths.py` (`_DEFAULT_RUNTIME_TARGET` — a third symbol in the same file). ⛔ Sequence.
- Overlaps with: **PLAN-06** adjacently — `_dep_index.py` sits beside these scripts and is PLAN-06's. Do not touch it.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint), PLAN-05 (disjoint bundles).

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]`.
- Red-first tests for D1 (the divergence catch), D2 (the non-default root), D4 (a different target's ceiling).
- D3's outcome is a **reported decision either way** — the PR body states whether the write moved or why it stayed, with evidence. A silent "left as is" is the failure mode this deliverable exists to prevent.
- The inventory-row re-derivation for all five rows, reported in the PR body **and** the inbox message. ⛔ A row whose detection still finds something **stays, narrowed to the residue** — a row is retired because the coupling is gone from the tree, never because this plan merged.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-10-layout-and-executor-residuals.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. It **reports** its row re-derivations through that
message; the orchestrator retires the rows from the landing.
