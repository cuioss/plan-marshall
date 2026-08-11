# Run report — 030-attribution-populations-and-the-cost-decomposition (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/attribution-populations-cost-3tdp5o` (harness-assigned)    **PR:** [#1154](https://github.com/cuioss/plan-marshall/pull/1154)    **Outcome:** completed (auto-merge armed after this commit; landing delegated to the merge queue)

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
  - Reader: `parse_metrics_end_time_presence` → `MetricsEndTimePresence` in
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

### Pre-PR verification sub-agent (Step 6)

Independent read-only reviewer (general-purpose Task agent, ~124k tokens). Verdict:
**all four deliverables PASS, no code defects.** It verified D2's documented
mechanism line-by-line against `_attribute_cache_read`/`_fold_turn_residency` in
`claude_runtime.py` and confirmed it is a faithful read (not an inference), and it
confirmed the D4 three-state reader + per-state tests pre-exist and are untouched.
It also checked "everywhere emitted/rendered" for D1 across the retrospective,
audit, and platform-runtime surfaces and found no surviving bare-`unattributed`
site. Two items, both **accepted**:

| # | Source | Finding | Disposition |
|---|--------|---------|-------------|
| 1 | sub-agent | Report cited the D4 reader as `read_end_time_presence`; the actual symbol is `parse_metrics_end_time_presence`. | **Fixed** — report citation corrected. Documentation-accuracy nit; no code impact. |
| 2 | sub-agent | D3's published ratio is main-context-window `cache_read` ÷ dispatched-subagent `tool_uses` — a genuine cross-population figure whose literal "resident context per call" meaning is weaker than the plan's Problem-section framing implies. | **Accepted as designed** — this follows the plan's explicit formula (`cache_read / tool_uses`); the implementation is *more honest than the plan* in that it prominently discloses the population span (lattice entry, render bullet, § Read-Cost Decomposition) rather than presenting a clean "per-call" number, which is exactly what D4 demands. Recorded as a transparency note, not a defect. No code change. |

No finding required a code fix or a re-dispatch. Out-of-scope list confirmed clean
(retrospective render path, ledger-disagreement, per-phase cost ranking, and bias
correction all untouched).

### CI / PR review (Step 7)

Two automated reviewers produced actionable findings against the diff; both were
fixed in commit `a1e53b2`, and CodeRabbit confirmed both as addressed. One finding
was raised independently by two reviewers.

| # | Source | Finding | Disposition |
|---|--------|---------|-------------|
| 3 | `coderabbitai` (inline, 🟠 Major) | `cache_read_per_tool_use` could be left stale on regenerate, rendering an invalid identity or raising `KeyError` on an unconditional `int(phase['tool_uses'])`. | **Fixed** (`a1e53b2`) — persist step clears a stale factor (presence ⇔ derivable invariant); render guards on all three operands. Test `test_stale_factor_is_cleared_when_operands_stop_qualifying`. CodeRabbit confirmed addressed. |
| 4 | `cuioss-review-bot` (conversation "PR Reviewer Guide", focus area) | "Possible KeyError/TypeError" on the same `int(phase['tool_uses'])` render — the identical defect as #3. | **Fixed** (`a1e53b2`, same change) — acknowledged in a PR issue comment. |
| 5 | `coderabbitai` (inline, 🟡 Minor) | `_UNATTRIBUTED_RENDER` hardcodes a residual set that a new `*unattributed*` field could bypass, silently regressing D1; repo path-instruction requires deriving such a mirror set. | **Fixed** (`a1e53b2`) — residual set derived (`_UNATTRIBUTED_RESIDUAL_FIELDS`) + contract-drift test `test_unattributed_render_map_covers_every_residual`. CodeRabbit confirmed addressed. |

The CI `verify / conclusion` failure notice on the superseded head `572fa47` was a
concurrency-cancelled run (my `a1e53b2` push superseded it), not a real failure —
the current head's `verify` was re-triggered and judged on the current head SHA per
Step 8 condition 1. No `skip-bot-review` label was applied (the diff touches
`marketplace/bundles/**`, reviewed as code).

## Reviewer participation

Expected reviewer population, derived from the registry docs
(`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{coderabbit,pr-agent,sourcery}.md`
→ `author_login`), cross-named by `.github/workflows/pr-agent.yml` — not a
hand-transcribed list. Each verdict is read from the stored comment bodies, not a
check state.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | **reviewed** | Published a full review (`pullrequestreview-4904421747`) with 2 actionable findings against the diff; both fixed and bot-confirmed as addressed. |
| `cuioss-review-bot` | **reviewed** | Published a "PR Reviewer Guide" (`issuecomment-5250932702`) with a "Possible KeyError/TypeError" focus-area finding against the diff; fixed and acknowledged. |
| `sourcery-ai` | **rate-limited** | Published only a quota notice (`pullrequestreview-4904401817`): "you have reached your weekly rate limit of 500000 diff characters." It engaged but did not review this diff; its `Sourcery review` check reports `skipped`. |

**Coverage: 2-of-3 reviewed** (`coderabbitai`, `cuioss-review-bot`); 1-of-3
rate-limited (`sourcery-ai`, weekly diff-char quota). The Step 8 condition-4
shortfall disclosure fired: "Review coverage: 2 of 3 — coderabbitai and
cuioss-review-bot reviewed; sourcery-ai rate-limited (weekly 500k diff-char
quota)." Per condition 4 this is a disclosure, not a merge block — a rate limit is
outside our control and does not hold the landing.

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

| Step | Verdict | Evidence |
|------|---------|----------|
| 1 Skills loaded | done | Named above; loaded by path (plugin not required present). |
| 2 Branch | done | Harness-assigned `claude/attribution-populations-cost-3tdp5o`, published on `origin` (pushed before any work). No run-created branch. |
| 3 Plan directory | done | `doc/plans/…/030-…/plan.md` exists and opens with the first-instruction block (present on arrival, no repair needed). |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer; all four deliverables addressed. |
| 4 Per-commit gate | done | Every `*.py`-touching commit was preceded by a `total_issues: 0` / empty-`errors[]` quality-gate log. |
| 4 Pushed | done | No unpushed commit remains after each commit; branch tracks `origin`. |
| 5 Build gate | done | Python changed → `./pw verify` run: 18903 passed, 14 skipped; quality gate clean. |
| 6 Verification sub-agent | done | Independent agent passed all four deliverables, no code defects; two report nits recorded (one fixed). |
| 7 PR cycle | done | PR #1154; every comment on both surfaces (inline review threads + conversation) dispositioned. |
| 8 Merge gate | conditions 1–3 met; auto-merge armed (see the arming note below). |
| 8 Bridge | done | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Recorded below (one proposal, pending operator approval). |

**GitHub access path:** the GitHub MCP server (cloud path), as expected for a cloud
session. **Branch form:** harness-assigned. **Plugin-cache sync:** not owed — a
cloud run neither performs nor records a `/sync-plugin-cache` (machine-local build
step).

**One-command-per-Bash-call slip (recorded honestly):** one Bash call combined
`git add … && git commit …`. The one-command-per-call discipline binds in this lane;
this was a process slip. It had no effect on the deliverables (both files staged
were the intended ones) and every other Bash call used exactly one command. Noted
so it is not narrated as clean.

## What have we learned (Step 9)

**One proposal, pending operator approval — not self-applied.** This run observed
that the lane's "superseded CI run" guidance (§ Step 4 "Commit and push" and
§ Step 7 "A push during the review cycle") describes a push-superseded run as
surfacing a `verify / conclusion` **cancellation**. In practice this run received a
webhook with `Conclusion: failure` for `verify / conclusion` on the superseded head
`572fa47` — the aggregating gate job reports **failure** (not cancellation) when its
upstream `verify / verify` is concurrency-cancelled. A run reading the contract
literally could misclassify this as a real CI failure and enter a needless
drive-to-green loop. **Proposed edit:** the lane's superseded-run guidance should
say the superseded run may surface as a cancellation *or* a failure on the
`verify / conclusion` job, and that the discriminator is the **head SHA** — a
non-success on a SHA that is no longer the PR head is superseded and is judged only
on the current head (which Step 8 condition 1 already mandates reading).

This run executed autonomously with no interactively-reachable operator, so per the
lane's escalation rule the proposal is **recorded here** (the durable channel)
rather than self-approved or shipped as a separate `chore(cloud-plan-lane)` PR. A
future run or the operator can adopt it. No other contract change is proposed.

## Residue

- D2's quantitative claim and D3's creation-inversion magnitude remain
  **corpus-blocked** — reachable only with the git-ignored archived-plan record
  population. A future run with that corpus available could verify whether the
  cache_read residual is large in specific phases and whether the creation
  inversion reproduces beyond n=1.
