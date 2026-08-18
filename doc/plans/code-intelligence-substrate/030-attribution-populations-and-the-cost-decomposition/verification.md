# Verification — 030-attribution-populations-and-the-cost-decomposition

**Audited:** `plan.md`, `report-01.md` (the plan directory holds no other file)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Landing commit:** `18ddd54` — `fix(manage-metrics): separate the two unattributed populations and publish the read-cost decomposition (#1154)`
**Overall verdict:** CONFIRMED WITH GAPS

All four deliverables are implemented, present in the tree now, and covered by non-vacuous tests
(two mutations proved). The gaps are in the *surrounding* documentation surfaces the deliverables
lean on, plus one name collision introduced by a later plan that contravenes this plan's explicit
one-writer constraint.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: name and separate the two unattributed populations | Render special-cases both residuals with denominators; contract section added; two consumer tests | `_UNATTRIBUTED_RENDER` at `manage-metrics.py:419-430`, render at `:2336-2362`, contract at `data-format.md:198-207`, tests at `test_manage_metrics.py:2048-2160` + drift test `:2289`. Mutation-proved non-vacuous | CONFIRMED |
| D2 | Attribute `cache_read` outside the well-attributed phase, or state why not | Mechanism read (`_attribute_cache_read` / `_fold_turn_residency`), limitation documented at the emission contract, magnitude corpus-blocked | Mechanism claim is a faithful read of `claude_runtime.py:1892-1934`; limitation documented at `data-format.md:209-213`. But the **producer's own** contract (`platform-runtime/standards/contract.md:967`, `runtime_base.py:733`) still states the un-subtracted version and was not corrected | PARTIAL |
| D3 | Emit resident context and turns per phase; settle the creation inversion | `cache_read_per_tool_use` persisted before `write_metrics`; turns = existing `tool_uses`; inversion documented as not-established | Persist loop `manage-metrics.py:1528-1541` runs before `write_metrics` at `:1954`; contract at `data-format.md:232-248`; tests `test_manage_metrics.py:2163-2286`. Mutation-proved non-vacuous | CONFIRMED |
| D4 | Every figure names its population, phase, sampling point; three-state read | Vocabulary reused, no parallel discriminator; three-state read pre-existing and tested | `MetricsEndTimePresence` / `parse_metrics_end_time_presence` at `audit.py:1052-1180`; one test per state at `test_audit_check_metrics_end_time_markers.py:72/147/163`; writer emits new keys only and drops the retired pair (`manage-metrics.py:1576-1577`) — no shim, single reader | CONFIRMED |

## Per-deliverable detail

### D1 — GATE: name and separate the two unattributed populations

- **Required (plan):** *"no emitted or rendered field is named merely `unattributed`; each carries its
  quantity and its denominator, and a test asserts a consumer can distinguish them."*
- **Claimed (report):** render loop special-cases both residuals via `_UNATTRIBUTED_RENDER`, each
  rendering as `{value} of {denominator} {denominator_field} ({note})`; contract table added; two
  tests asserting names and denominators, not values; six existing render assertions updated.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:419-430` —
    `_UNATTRIBUTED_RENDER` maps `exploration_unattributed_bytes` → denominator
    `exploration_result_bytes`, `cache_read_unattributed` → denominator `cache_read_input_tokens`.
  - `…/manage-metrics.py:2336-2362` — the presence-persisted render loop, denominator read off the
    same row, with a display fallback when the denominator is absent.
  - `…/manage-metrics.py:3441-3443` — `_UNATTRIBUTED_RESIDUAL_FIELDS`, **derived** from
    `_PRESENCE_PERSISTED_FIELDS` rather than hand-listed (the CodeRabbit finding #5 fix; present in
    the landing commit).
  - `…/manage-metrics/standards/data-format.md:198-207` — `#### The two "unattributed" populations
    are different quantities — name which`, with the quantity/denominator/residual-of table.
  - `test/plan-marshall/manage-metrics/test_manage_metrics.py:2048-2160` —
    `TestTwoUnattributedPopulationsAreDistinguishable`, both tests.
  - `test/plan-marshall/manage-metrics/test_manage_metrics.py:2289-2305` —
    `test_unattributed_render_map_covers_every_residual` (contract-drift guard).
- **Checks run:**
  - Both residuals' denominators are persisted co-present with the residuals: `cmd_enrich` writes the
    four-field group (`_FOUR_FIELD_USAGE_FIELDS`, `manage-metrics.py:3504`) and
    `_PRESENCE_PERSISTED_FIELDS` (`:3522`) from the same runtime bucket, and the runtime emits the
    full key set unconditionally (`contract.md:983` "Absent is not zero"). The render's
    absent-denominator fallback is therefore unreachable from a runtime-produced row.
  - "Everywhere emitted or rendered": grepped `unattributed` across `marketplace/`, `.claude/` and
    `test/`. The only sites naming these two fields are `manage-metrics` (script + standards + tests),
    `platform-runtime` (`claude_runtime.py`, `runtime_base.py`, `contract.md`). No consumer in
    `plan-retrospective` or `.claude/skills/audit-archived-plan-retrospectives` reads either field —
    confirmed the grep is not a false negative by the same pattern hitting the unrelated
    `unattributed_excluded_count` sites in `.claude/`. `cmd_enrich`'s return TOON echoes neither.
  - Re-derived the report's "six existing render assertions updated":
    `git show 18ddd54 -- test/.../test_manage_metrics.py | grep '^-' | grep -c nattributed` → **6**.
  - **Mutation A (non-vacuity):** rewrote `_UNATTRIBUTED_RENDER['cache_read_unattributed']` to the
    label `'Unattributed'` over the byte residual's denominator — i.e. exactly the confusion D1
    forbids. `uv run python -m pytest test/plan-marshall/manage-metrics/test_manage_metrics.py -o
    addopts="" -k "Unattributed or ReadCost or unattributed_render_map"` → **1 failed, 6 passed**,
    failing at `test_render_names_quantity_and_denominator_for_each_residual`
    (`test_manage_metrics.py:2152`). Restored from a byte snapshot at
    `$TMPDIR/…/verify-030-mutsweep/manage-metrics.py.orig`; md5 re-matched and
    `git status --porcelain -- marketplace/…/manage-metrics/` is empty.
- **Verdict:** CONFIRMED — implemented as specified, in the specified place, with a test that goes
  red against the defect it names. One test-adequacy weakness is noted under Test adequacy (the
  loop-form "no bare unattributed" guard is weaker than the exact-string assertions beside it).

### D2 — Attribute `cache_read` outside the well-attributed phase, or state why it cannot be

- **Required (plan):** *"the mechanism is named with the implementing symbol that enacts it, and
  either the attribution improves or the limitation is documented at the emission contract."* The
  ⛔ constraint: read the mechanism, do not infer it.
- **Claimed (report):** implementing symbol `_attribute_cache_read` fed by `_fold_turn_residency` in
  `platform-runtime/scripts/claude_runtime.py`; the residual is a remainder by construction
  (`attributable = max(0, cache_read_total - max(0, subagent_cache_read))`, line 1874; residual at
  line 1880); limitation documented at `data-format.md`; magnitude corpus-blocked.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py:1892-1934`
    — `_attribute_cache_read`. Line 1927 is verbatim
    `attributable = max(0, cache_read_total - max(0, subagent_cache_read))`; line 1933 is
    `attributed["cache_read_unattributed"] = cache_read_total - sum(attributed.values())`; the
    `attributable > 0 and total_weight > 0` guard at 1928 is what leaves the whole figure in the
    residual on a zero-weight window.
  - `…/claude_runtime.py:1871-1889` — `_fold_turn_residency` accrues weight only from
    `per_phase_counters` on the **parent** walk (called at `:2264` inside the parent-transcript
    loop); subagent transcripts are folded afterwards at `:2270-2292` and never reach it.
  - `…/manage-metrics/standards/data-format.md:209-213` — `#### Why cache_read cannot be fully
    attributed outside the parent-observed window (D2)`, naming both symbols and both branches.
- **Checks run:**
  - Verified the report's cited line numbers were correct **at landing**:
    `git show 18ddd54:…/claude_runtime.py | sed -n '1870,1884p'` puts `attributable = …` at 1874 and
    the residual at 1880. They have since drifted to 1927/1933 — normal drift, not a defect.
  - Verified the causal claim is a read and not an inference: the subtraction, the clamp, the
    zero-weight branch and the parent-only fold are all in the source, and the contract prose matches
    them clause for clause.
  - Verified the mechanism is itself tested (pre-existing):
    `test/plan-marshall/platform-runtime/test_metrics_tokens.py:579-620` —
    `test_attribute_cache_read_keeps_subagent_share_out_of_named_buckets`,
    `…_subagent_exclusion_is_load_bearing`, `…_subagent_exceeding_total_empties_rather_than_inverts`.
  - Verified the corpus-blocked claim: `.plan/` is git-ignored and absent from this clone, so the
    quantitative half is genuinely unreachable. The run did not substitute a hand-assembled corpus —
    `git show --stat 18ddd54` lists only `manage-metrics.py`, `data-format.md`,
    `test_manage_metrics.py` and the two plan files.
- **Verdict:** PARTIAL — the mechanism half is fully met and read from source. The documentation half
  is met at `manage-metrics/standards/data-format.md` (the persistence/consumer contract) but **not**
  at the producer's own emission contract, which is where the symbol lives and which
  `manage-metrics.py:3391-3393` itself names as SOURCE OF TRUTH. Worse, both producer-side surfaces
  still assert the *un-subtracted* model: `platform-runtime/standards/contract.md:967` ("the phase's
  recorded `cache_read` is divided in proportion to those weights") and
  `platform-runtime/scripts/runtime_base.py:733` (same sentence). Only the parent-observed portion is
  divided. Two documents describing one producer now disagree. See G1, G2.

### D3 — Emit resident context and turns per phase, and settle the creation inversion

- **Required (plan):** *"both factors are persisted fields (not render-time computations), and the
  creation inversion has a named mechanism or an explicit 'not established' with what was ruled
  out."* Plus ⛔ one writer.
- **Claimed (report):** `cache_read_per_tool_use = round(cache_read / tool_uses)` written onto the
  phase row before `write_metrics`; turns is the existing `tool_uses`; render bullet states the
  identity and the population span; contract § Read-Cost Decomposition + lattice entry + per-phase
  field entry; inversion documented as mechanism-named/magnitude-not-established with the record
  model ruled out.
- **Found:**
  - `manage-metrics.py:1528-1541` — the persist loop, guarded on both operands and `tool_uses > 0`,
    with the `else: phase.pop(...)` stale-clear (CodeRabbit finding #3 fix; present at landing —
    `git show 18ddd54:…/manage-metrics.py | grep -n "phase.pop('cache_read_per_tool_use'"` → line
    1229).
  - `manage-metrics.py:1954` — `write_metrics(plan_id, data, preserve_totals=True)`, i.e. **after**
    the persist loop. Persisted, not render-time. Confirmed the render at `:2302-2319` reads the same
    in-memory `phases` dict (`data.get('phases', {})` at `:1410`, never re-read).
  - `data-format.md:232-244` — § Read-Cost Decomposition with the identity block and the D4
    population disclosure; `:49` — the Direction-1 lattice entry (`derived-cost`); `:146` — the
    Per-Phase Fields entry.
  - `data-format.md:246-248` — `#### The cache-creation inversion — not established here`, naming the
    1.25-vs-0.1 weight mechanism, ruling out the record model, and stating n=1/corpus-blocked.
  - `test/plan-marshall/manage-metrics/test_manage_metrics.py:2163-2286` —
    `TestReadCostDecomposition`, four tests.
- **Checks run:**
  - **Mutation B (non-vacuity):** replaced the stale-clear at `manage-metrics.py:1541` with `pass`.
    Same pytest invocation → **1 failed, 6 passed**, failing at
    `test_stale_factor_is_cleared_when_operands_stop_qualifying` (`test_manage_metrics.py:2282`).
    Restored from the same byte snapshot; md5 re-matched, `git status` clean for the file.
  - Re-derived the identity's exactness: `round(80000 / 8) * 8 == 80000` — the test asserts the
    product, and the rendered bullet uses `≈`, so rounding is disclosed rather than asserted away.
  - Verified the "one writer" constraint against the tree **at landing**:
    `git show 18ddd54:…/plan-retrospective/scripts/analyze-logs.py | grep -c cache_read_per_tool_use`
    → **0**. The plan was the only writer when it landed.
- **Verdict:** CONFIRMED for what this plan shipped. Two follow-on findings, neither this run's doing
  but both live in the tree now: a **second** `cache_read_per_tool_use` was added afterwards by
  `#1260` in `plan-retrospective/scripts/analyze-logs.py:662` over a different population (G3); and
  the render bullet/lattice name the factor `resident_context_per_call`, which is not a field
  anywhere (G4, G5).

### D4 — Every figure names its population, its phase, and its sampling point

- **Required (plan):** *"a record in each of the three states is read and reported as that state,
  asserted by test"*, using the already-shipped vocabulary and introducing no parallel one.
- **Claimed (report):** the new figure uses the existing `derived-cost` vocabulary with no new
  discriminator; the three-state read was verified already implemented and tested, with no dual-key
  shim on the writer; a second reader was deliberately not introduced.
- **Found:**
  - `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:1052-1136` —
    `MetricsEndTimePresence`, with `readable`, `explained_phases`, `forces_floor` and
    `unreadable_note` distinguishing `old-schema` from `pre-#812` in the emitted note itself.
  - `…/audit.py:1139-1180` — `parse_metrics_end_time_presence`, three-state, with both value fields
    `None` on either degrade so a caller cannot default them.
  - `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_metrics_end_time_markers.py:72`
    (current), `:147` (old-schema, asserting `schema == METRICS_SCHEMA_OLD`, both values `None`,
    `forces_floor is True`, `"old-schema" in unreadable_note`), `:163` (pre-#812, additionally
    asserting `"old-schema" not in unreadable_note`).
  - Writer: `manage-metrics.py:1576-1577` — `data.pop('partial', None)` /
    `data.pop('unrecorded_phases', None)`. No dual-key shim, confirming the plan's HYPOTHESIS.
  - Single reader: `_RETIRED_PARTIALITY_KEYS` occurs in exactly one file
    (`.claude/…/audit.py:1049`, used at `:1170`); no other module reads `partial` /
    `unrecorded_phases` as archived-record keys.
  - New-figure vocabulary: `cache_read_per_tool_use` is classed `derived-cost`
    (`data-format.md:49`), an existing population in the lattice's table at `:30`. No new
    discriminator field was added.
- **Checks run:** read all three tests for tautology — each asserts a distinct `schema` constant,
  `None` value fields, `forces_floor`, and note content, so none can pass against a defaulted
  old-schema record. Checked the sampling-point vocabulary applies: `_DENOMINATOR_FIELDS`
  (`manage-metrics.py:215`) is the plan-level denominator triple, so the per-phase factor is outside
  the sampling-point pair by design, not by omission.
- **Verdict:** CONFIRMED. Note that the deliverable was satisfied by pre-existing code — the run
  verified rather than built it, and said so. The plan's claim label anticipated exactly this
  ("verify against the current emission contract in the clone before implementing").

## Correctness review

Read in full: `manage-metrics.py` §§ `_UNATTRIBUTED_RENDER` (419-430), the D3 persist loop
(1510-1541), the render (2290-2362), the presence-persist site (3490-3524), the derived field sets
(3375-3443); `claude_runtime.py` §§ `_fold_turn_residency` / `_attribute_cache_read` (1871-1934) and
the composition loop (2262-2350); `audit.py` §§ 1049-1180.

**No functional defect found.** Specifically checked and cleared:

- *Fail-open branches.* The residual is a remainder by construction, and the `max(0, …)` clamp at
  `claude_runtime.py:1927` cannot invert a named share negative when the subagent figure exceeds the
  phase total — covered by `test_attribute_cache_read_subagent_exceeding_total_empties_rather_than_inverts`.
- *Unguarded `None`.* The render's decomposition guard (`manage-metrics.py:2305-2310`) tests all
  three operands with `isinstance(..., (int, float))` before `int()`, so a `None` or string cell
  renders nothing rather than raising. The residual render guards the denominator with the same
  `isinstance` test (`:2354`).
- *Rounding / off-by-one.* `round(cache_read / tool_uses)` is banker's rounding; the published
  identity uses `≈` and the contract (`data-format.md:237-241`) states the factor is a rounded
  derivation. No consumer sums it (`data-format.md:49` "Never aggregated into any Total").
- *Order dependence.* The persist loop (1528) precedes `write_metrics` (1954) precedes the render
  (2302) inside one `cmd_generate`; both loops iterate the same `PHASE_NAMES` sequence over the same
  `phases` dict, so a row can never be rendered with a factor the persist step did not just write.
- *Stale surface.* The stale-factor clear makes presence ⇔ derivability an invariant on every
  regenerate; proved load-bearing by Mutation B.

**One dead guard, deliberate and harmless.** The render's triple-operand guard at
`manage-metrics.py:2305-2310` is documented as "the defence for a row generate did not just write",
but the render is only reachable from inside `cmd_generate`, downstream of the persist loop that
enforces the invariant. It is therefore unreachable defence-in-depth rather than a live guard. Not a
defect — a guard that cannot fire because an upstream invariant holds is different from a guard whose
condition is unsatisfiable — but it means the CodeRabbit `KeyError` finding it answers was already
closed by the persist-side half of the same fix.

## Test adequacy

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D1 emission | `test_emission_carries_two_distinct_keys_with_distinct_denominators` (`test_manage_metrics.py:2059`) | Non-vacuous — asserts two distinct keys, absence of a bare `unattributed` key, and that the two denominators are distinct *fields with distinct values* (the fixture deliberately uses 4000 vs 9000 so equality cannot carry the test) |
| D1 render | `test_render_names_quantity_and_denominator_for_each_residual` (`:2109`) | Non-vacuous — **proved** by Mutation A (1 failed / 6 passed) |
| D1 drift | `test_unattributed_render_map_covers_every_residual` (`:2289`) | Non-vacuous — asserts set equality between the derived residual set and the render map, and pins today's two-member set |
| D3 persistence | `test_resident_context_factor_is_persisted_not_render_only` (`:2171`) | Reads the factor back out of `metrics.toon`, so a render-only computation would fail it |
| D3 absence | `test_factor_absent_when_tool_uses_is_zero_or_missing` (`:2197`) | Covers both the absent and the zero denominator |
| D3 staleness | `test_stale_factor_is_cleared_when_operands_stop_qualifying` (`:2251`) | Non-vacuous — **proved** by Mutation B (1 failed / 6 passed) |
| D3 render | `test_render_states_the_decomposition_and_discloses_the_population_span` (`:2223`) | Asserts the identity operands and the population-span disclosure strings |
| D4 three-state | `test_audit_check_metrics_end_time_markers.py:72 / :147 / :163` | One record per state; the old-schema test asserts values are `None` and `forces_floor is True`, so a defaulted read fails it |
| D2 mechanism | `test_metrics_tokens.py:579-620` (pre-existing) | Includes `…_subagent_exclusion_is_load_bearing`, which compares with/without the subtraction |

Baseline: the seven manage-metrics tests above pass unmutated (`7 passed, 200 deselected in 5.31s`).

**One weak guard.** `test_manage_metrics.py:2158-2160` sweeps every rendered `…nattributed` bullet and
asserts only that it contains `' of '`. Mutation A showed this loop passes when both residuals render
under the identical label `- **Unattributed**` over the identical denominator — the exact confusion
D1 exists to prevent. The exact-string assertions above it caught the mutation, so D1 is not
unguarded, but the loop as written cannot be relied on to catch a *third* residual added later, which
is precisely the case it was written for. See G8.

**One untested branch.** The absent-denominator display fallback (`manage-metrics.py:2358-2362`) has
no test — grepping `"not recorded on this row"` across `test/` returns nothing. Unreachable from a
runtime-produced row, but reachable from a hand-edited or truncated `metrics.toon`. See G7.

## Report accuracy

Every checkable factual claim in `report-01.md` held **as of the landing commit**. Re-derived, not
copied:

- "Six existing render assertions updated" — re-counted from the landing diff: exactly 6.
- `_attribute_cache_read` … "line 1874" / "line 1880" — correct at `18ddd54`
  (`git show 18ddd54:…/claude_runtime.py | sed -n '1870,1884p'`). **Stale now**: 1927 / 1933 at
  `61a43e5`. Ordinary drift, recorded rather than charged.
- Test citations `test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py` and
  `test_audit_checks.py` — both files existed at `18ddd54` (`git ls-tree 18ddd54`). **Stale now**:
  that directory was later split into ~40 per-check files; the cited tests live in
  `test_audit_check_metrics_end_time_markers.py` and `test_audit_check_metrics_core.py`.
- `test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader` — existed at `18ddd54`
  (`test_record_model_representability.py:848`). **Stale now**: renamed to
  `test_unmeasured_fixture_separates_measured_zeros_from_unmeasured_in_the_audit_ledger_reader`
  (`:816`).
- "All code changes are within the plan's OBSERVED expected surface" — confirmed:
  `git show --stat 18ddd54` lists exactly `manage-metrics.py`, `standards/data-format.md`,
  `test/plan-marshall/manage-metrics/test_manage_metrics.py`, plus `plan.md` (rename, 0 changes) and
  the new `report-01.md`.
- "The platform-runtime producer was read, not modified" — confirmed by the same stat.
- CI-finding fixes #3 and #5 (stale-clear, derived residual set) — both present in the landing
  commit's tree, corroborating the dispositions even though the intermediate commits `34cfd4e` /
  `a1e53b2` were squashed away and are not verifiable from `main`.
- Finding #1 self-correction ("actual symbol is `parse_metrics_end_time_presence`") — the corrected
  name is the one in the tree (`audit.py:1139`).

**Unverifiable from the tree:** the `./pw verify` figures ("18903 passed, 14 skipped", mypy "389
source files", plugin-doctor `total_issues: 0`), the reviewer-participation table and its comment
IDs, the wall-clock figures, and the superseded-run CI narrative. All are PR/CI-session facts. The
brief forbids running the full verify suite, and no in-tree artifact records them.

No claim in the report was found **false at landing**. The three staleness items above are all
downstream-refactor drift, not overstatement.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D2's quantitative claim — whether the `cache_read` residual is large in specific phases — corpus-blocked | **Still open** | `.plan/` is git-ignored and absent from this clone; no archived-plan record population exists in the tree. Nothing in `data-format.md:209-213` has been upgraded from structural argument to measured magnitude, and no later commit touches that section (`git log -- …/data-format.md` shows the section unchanged since `18ddd54`) |
| D3's creation-inversion magnitude (n=1) — corpus-blocked | **Still open** | `data-format.md:246-248` still reads "*mechanism-named, magnitude-not-established (corpus-blocked)*" verbatim |
| The `cloud-plan-lane` proposal on superseded-run CI classification (recorded, not self-applied, pending operator approval) | **Closed by a later plan** | The lane skill has since been revised repeatedly (`2cbcb1f`, `7d61d67`, `18b1b5c`, `b199d94`, `61a43e5`). Not re-verified clause-by-clause here — outside this plan's surface |
| The recorded one-command-per-Bash-call slip | **Moot** | A disclosed process slip with no artifact in the tree |

## Out-of-scope and collateral

The plan excluded four things. `git show --stat 18ddd54` shows the run touched no file outside
`manage-metrics` + its standards + its tests, so all four hold by construction:

- **The retrospective render path** — `plan-retrospective/` untouched by `18ddd54`. ✅
- **The ledger-disagreement question** — no ledger file touched. ✅
- **Re-deriving the per-phase cost ranking** — no ranking is emitted or rendered; the added surface
  publishes factors only. ✅
- **Bias correction on a figure whose error direction varies** — no correction applied anywhere. ✅

No collateral change. The sibling adjacency was respected: plan `080`'s deliverable is scoped to the
byte half (`080/plan.md:76-79` "Scope: the *byte* remainder only"), and this plan did not encroach.

## Method and coverage

**What I checked and how.** Read `plan.md` and `report-01.md` in full, then the shipped surface:
`manage-metrics.py` (the five relevant regions), `manage-metrics/standards/data-format.md` (lattice,
the two new §§, the per-phase field table), `claude_runtime.py` (the two named symbols plus the
composition loop that calls them), `runtime_base.py` and `platform-runtime/standards/contract.md`
(the producer contracts), `audit.py` (the three-state reader), and the test files for each. Re-derived
every count stated here at the moment of stating it. Located the landing commit `18ddd54` and used
`git show` against it to separate "wrong now" from "wrong then" for every report citation.

**Mutation sweep.** Two mutations, each restored from a byte snapshot I took at
`$TMPDIR/…/scratchpad/verify-030-mutsweep/manage-metrics.py.orig` (md5 `b9c88ef9…`), never with
`git checkout`/`restore`/`stash`. After each restore the md5 re-matched and
`git status --porcelain -- marketplace/bundles/plan-marshall/skills/manage-metrics/` was empty. Other
files show as modified in `git status` — those belong to sibling verification agents working in the
same clone and were not touched by me.

**Negative-result discipline.** Before reporting "no other consumer reads these fields", I confirmed
the same grep pattern hits known sites (`unattributed_excluded_count` in `.claude/`,
`cache_read_per_tool_use` in `plan-retrospective/`), so the empty results are real absences and not a
filtered-search artifact.

**What I could not check.**

- The originating per-phase measurements (D2's magnitude, D3's inversion). The archived-plan record
  corpus lives under the git-ignored `.plan/` tree, is absent from this clone, and the plan forbids
  searching for it. **UNVERIFIABLE** — and the report says the same, which is the correct posture.
- The full `./pw verify` result, the quality-gate figures, and the PR/CI narrative (reviewer table,
  comment IDs, the superseded-run classification). **UNVERIFIABLE** from the tree; the brief scopes
  the full suite out.
- Whether the *rendered* `metrics.md` of a real plan reads correctly end-to-end. Only the unit-level
  render was exercised; no real `metrics.toon` exists in this clone.
