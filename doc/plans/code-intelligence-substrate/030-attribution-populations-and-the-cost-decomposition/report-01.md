# Run report — 030-attribution-populations-and-the-cost-decomposition (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/attribution-populations-cost-3tdp5o` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` — the working contract (first action).
- `plan-marshall:ref-code-quality` (always) → `standards/code-organization.md` — read by path.
- `pm-plugin-development:plugin-script-architecture` (always) — read by path.

Conditional skills whose surface applied were satisfied by reading the concrete
source in-tree (the change is a focused edit to one existing script + its
standards doc + its tests, all already-conventional in this repo), so
`persona-implementer` / `python-core` / `pytest-testing` were not separately
loaded — the code-organization and script-architecture standards plus the
surrounding file conventions governed the edit. This is recorded rather than
silently skipped.

## Deliverables

All code changes are within the plan's OBSERVED expected surface
(`manage-metrics/` emission + `standards/data-format.md` + `test/plan-marshall/manage-metrics/`).
The platform-runtime producer was **read, not modified** (D2 mechanism).

### D1 — GATE: name and separate the two unattributed populations ✅

- **Render (`manage-metrics.py` `cmd_generate`):** the flat presence-persisted
  render loop now special-cases the two residuals via `_UNATTRIBUTED_RENDER`.
  Each renders as `{value} of {denominator} {denominator_field} ({note})`, so
  `exploration_unattributed_bytes` names denominator `exploration_result_bytes`
  and `cache_read_unattributed` names denominator `cache_read_input_tokens`. The
  label carries the quantity (`… exploration bytes` vs `… cache_read tokens`), so
  neither figure is rendered merely as `unattributed`.
- **Emission:** the persisted keys already carried their quantity in the name;
  the emission-level distinctness is asserted by test.
- **Contract:** `data-format.md` gains `#### The two "unattributed" populations
  are different quantities — name which`, a table naming both quantities,
  denominators, and the residual each is of, plus the consumer rule.
- **Tests:** `TestTwoUnattributedPopulationsAreDistinguishable` —
  `test_emission_carries_two_distinct_keys_with_distinct_denominators` (asserts
  distinct keys, no bare `unattributed` key, distinct denominator fields) and
  `test_render_names_quantity_and_denominator_for_each_residual` (asserts each
  residual renders with its denominator, and that every rendered `…nattributed`
  bullet carries a denominator). Assertions are on names/denominators, not values.
- Six existing render assertions updated to the new denominator-bearing labels.
- **Commit:** `34cfd4e`. Verification: `./pw verify` green.

### D2 — attribute cache_read outside the well-attributed phase, or state why not ✅ (documented-limitation branch; corpus-blocked for the quantitative claim)

- **Mechanism read, not inferred.** Implementing symbol named at the emission
  contract: `_attribute_cache_read` (fed by `_fold_turn_residency`) in
  `platform-runtime/scripts/claude_runtime.py`. The residual is a **remainder by
  construction**: subagent-folded cache_read is subtracted before the split
  (`attributable = max(0, cache_read_total - max(0, subagent_cache_read))`,
  line 1874) and reaches the residual via the remainder (line 1880); a window
  with `total_weight == 0` leaves the whole figure in the residual.
- **Limitation documented at the emission contract:** `data-format.md`
  `#### Why cache_read cannot be fully attributed outside the parent-observed
  window (D2)`. This is the ⭐ "it cannot be attributed there, and here is why"
  outcome.
- **Corpus-blocked** for the quantitative claim (that the residual is *large in
  specific phases*): the originating figures come from archived plan records
  under the git-ignored `.plan/` tree, **not present in this clone** — established
  from git-reachable evidence (a fresh cloud clone has no `.plan/plans/` corpus),
  and the plan's scope note forbids searching for it. The mechanism claim is READ
  from source; the magnitude claim is reported unverifiable-here rather than
  inferred.

### D3 — emit resident context and turns per phase; settle the creation inversion ✅ (factors published; inversion = not-established/corpus-blocked)

- **Persisted factor:** `cmd_generate` writes `cache_read_per_tool_use =
  round(cache_read_input_tokens / tool_uses)` onto the phase row **before**
  `write_metrics`, so it is a persisted field, not a render-time computation. The
  turns factor is the existing `tool_uses` (not duplicated). Product identity:
  `cache_read ≈ cache_read_per_tool_use × tool_uses`.
- **Render:** a `Read-cost decomposition` bullet states the identity and discloses
  the population span.
- **Contract:** `data-format.md` `### Read-Cost Decomposition` + a lattice entry
  (Direction 1) + a Per-Phase Fields entry.
- **Creation inversion (D3b):** documented `#### The cache-creation inversion —
  not established here` — the creation/read mechanism is named (weights 1.25 vs
  0.1; first-write vs re-read), the **record model is ruled out** (write-path
  currency verdicts all `current`), and the magnitude is **not established**
  (n=1, corpus-blocked).
- **Tests:** `TestReadCostDecomposition` — factor is persisted and equals the
  decomposition; absent when `tool_uses` is 0/missing; render states the identity
  and discloses the population span.

### D4 — every figure names its population, its phase, and its sampling point ✅

- **New figures use the shipped vocabulary, no parallel discriminator.**
  `cache_read_per_tool_use` is labelled `derived-cost` (existing population
  vocabulary); the unattributed residuals name their denominators. No new
  discriminator field was introduced.
- **Three-state read (current / old-schema / pre-#812)** was verified **already
  implemented and tested** in the archived-record reader, with no dual-key shim
  on the writer (confirmed against `cmd_generate`, which emits the new keys only
  and drops the retired pair):
  - Reader: `read_end_time_presence` / `MetricsEndTimePresence` in
    `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`.
  - One-record-per-state tests, including old-schema-reported-as-old-schema
    (not defaulted): `test_parse_metrics_end_time_presence_reports_old_schema`
    and `..._reports_pre_812` in
    `test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py`; the
    `check_metrics` three-state tests in `test_audit_checks.py`; and the
    cross-reader tests in
    `test/plan-marshall/manage-metrics/test_record_model_representability.py`
    (`test_the_generated_record_reads_as_current_schema_in_the_archived_reader`,
    `test_old_schema_record_is_distinct_from_a_clean_verdict_and_from_pre_812`,
    `test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader`).
  - Introducing a second reader in `manage-metrics` would violate D4's "do not
    introduce a parallel one", so the existing reader is relied on and cited.
    The `close_count`/`value_scope` claim (HYPOTHESIS in the plan) was CONFIRMED:
    the rename is breaking with no shim, and the reader obligation is the fix.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → non-empty (manage-metrics.py,
test_manage_metrics.py). Ran `./pw verify`: **SUCCESS — 18903 passed, 14 skipped**
(`0:05:44`). Quality gate independently clean: mypy `Success: no issues found in
389 source files`, ruff `All checks passed!`, SPDX passed, plugin-doctor
`status: pass / total_issues: 0` (incl. `test_real_marketplace_quality_gate_has_zero_findings`).

## Findings

_Pre-PR verification sub-agent dispatched (Step 6); findings + dispositions to be
recorded here on return. CI/PR-review findings appended after Step 7._

## Reviewer participation

_To be filled after Step 7 from the stored comment bodies, per the configured
reviewer population._

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| _pending_ | _pending_ | _pending_ |

## Cost

- **Tokens:** not available to the agent in this session (the harness does not
  surface this session's own token usage to the agent).
- **Wall-clock:** run began ~2026-08-11T08:0x UTC; report timestamp
  2026-08-11T08:33Z. `./pw verify` alone was 5m44s.
- **Population:** this single Claude Code cloud session's own usage. ⛔ NOT
  comparable to a plan-marshall `metrics.toon` total — that counts an
  orchestrator-plus-agent dispatch tree under a per-task billing boundary this
  interactive session does not share. No comparable figure is presented.

## Contract check (Step 9)

_Filled at Step 8 condition 3 as the final pre-merge commit._

## What have we learned (Step 9)

_Filled at Step 9._

## Residue

- D2's quantitative claim and D3's creation-inversion magnitude remain
  **corpus-blocked** — reachable only with the git-ignored archived-plan record
  population. A future run with that corpus available could verify whether the
  cache_read residual is large in specific phases and whether the creation
  inversion reproduces beyond n=1.
