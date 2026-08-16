# Run report — 270-aggregate-cost-invisible-to-per-call-ceiling (run 01)

**Date (UTC):** 2026-08-16 **Branch:** `claude/aggregate-cost-per-call-ceiling-wxrfms` **PR:** _pending_ **Outcome:** _pending_

## Skills loaded

| Skill | Route | Why |
|---|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` (plugin notation) | First action of the run |
| `plan-marshall:ref-code-quality` | bundle path | Always |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Always |
| `pm-dev-python:python-core` | bundle path | Python production code |
| `pm-dev-python:pytest-testing` | bundle path | Python tests |

Every skill was read by **bundle path**; the `plan-marshall` plugin notation was not relied on. No skill was unobtainable.

⚠ **Ordering defect in this run:** the two conditional `pm-dev-python` skills were loaded *after* implementation had begun, not at Step 1. Loading them surfaced a real defect in work already written (see Findings VS-07), which is precisely the cost of the late load. Recorded rather than smoothed over.

## Deliverables

### D1 — GATE: verify first-party, restate in the billing currency — **PARTIAL (as the plan directs)**

**Corpus reachability: BLOCKED.** `.plan/local/archived-plans/` and `.plan/local/plans/` do not exist in this clone, so there is no archived-plan corpus and no multi-day history.

⚠ **A correction to this run's own earlier statement.** An earlier draft of this report said `.plan/` carries "only `marshal.json` and `project-architecture` — no `logs/`, no `local/`". That was true when written and is **false now**, and this run falsified it itself: the `./pw verify` build gate created `.plan/execute-script.py`, `.plan/temp/`, and `.plan/local/logs/script-execution-2026-08-16.log`. That log covers a single day, is largely this session's own build traffic, and yields `plan_windows_derived: 0` — so it is not the corpus D1 needs and the verdict is unchanged. The claim is corrected rather than quietly dropped, because a run that measures a tree it is concurrently mutating is exactly the failure mode this epic exists to catch.

The plan anticipated the blocked corpus and directed the fallback: *"ship D2 (which is a code change) and report D1's re-derivation and D3 blocked on corpus availability"*. The machine-local path was **not** searched for, per the plan's explicit instruction.

So the **numeric** re-derivation (call counts, cumulative durations, share-of-total for the two named hot paths) is **not delivered** and is blocked on corpus availability. Every number in the plan's Problem section remains a **LEAD**, unconfirmed by this run.

The **structural** half needed no corpus and was verified first-party by reading the predicates:

| Claim | Verdict | Artifact |
|---|---|---|
| A per-call ceiling is structurally incapable of surfacing this class | **CONFIRMED first-party** | `_GLOBAL_LOG_SLOW_SECONDS = 30.0`; `slow_call_count` increments only on `seconds >= _GLOBAL_LOG_SLOW_SECONDS`. A 0.2 s call repeated 100 000 times is 20 000 s of wall-clock and leaves the counter at `0`. |
| No cumulative view existed in the per-plan retrospective | **CONFIRMED first-party** | `slowest_scripts` ranks by largest **single** call (`sorted(durations, key=lambda x: (-x[1], x[0]))[:3]`); `script_duration_p50/p95/max_ms` are per-call distributional. A content sweep for `cumulative` / `total_duration` / `share_of_total` / `total_ms` across `plan-retrospective` returned **zero** hits. |
| The data was already present and discarded | **CONFIRMED first-party** | `extract_script_durations` already returns `list[tuple[notation, duration_ms]]` — the exact input a group-by needs — and nothing grouped it. `analyze_folded_global_logs` parsed **every** duration and kept only the `>= 30 s` count. |

**A correction to the framing, found by reading rather than assuming.** It is *not* true that no aggregate existed anywhere. The cross-plan check `cross_global_log_analysis` (`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`) already accumulated `call_counts`, `call_seconds` and `total_seconds`, and already emitted `high_frequency` rows carrying both `count` and `total_seconds`. But it was a **frequency** instrument, not a cost one, in three separate ways:

1. `frequent` filters `count >= high_frequency_calls` (50) — a key owning a large share of total time is dropped **entirely** if it is called rarely.
2. The survivors are sorted by `-count`, never by duration — so above the gate, ordering ignores time owned.
3. **No share-of-total was ever computed**, although the denominator (`total_script_seconds`) is computed a few lines away in the same function.

This is almost certainly the origin of the plan's "hundred thousand invocations" lead: `high_frequency` is the one surface that reports a large call count beside a cumulative-seconds figure.

**(a) observability — DECIDED.** The aggregate view that must exist is a per-script cumulative roll-up ranked by share of total, published over the *same population* as the per-call ceiling so the two are readable together. Shipped as D2.

**(b) reduction — NOT DECIDABLE in this run.** Which of the two hot paths is reducible, and by what mechanism, cannot be settled without the measurement the corpus would supply. The plan is explicit: *"⛔ Do not optimise a path whose cost this run could not measure."* Recorded as blocked rather than guessed. See D3.

### D1's currency restatement — **DELIVERED** (the deliverable's stated integrity check)

⛔ **This is a LATENCY finding, not a billing finding.** Stated plainly, as the plan's Verification section requires.

The restatement is stronger than "unverified" — it is **structurally unavailable**:

- The `script-execution.log` line grammar carries a timestamp, level, hash, notation, subcommand and a duration. It carries **no token field of any kind**.
- Token measurements live in a *different artifact*, `metrics-dispatch-boundaries-{phase}.toon`, whose four context-load columns (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) are keyed **per dispatch**, not per script call.
- ⇒ There is **no join key** between a script invocation and a token measurement anywhere in this corpus. A wall-clock share therefore **cannot** be converted into a billing share by any computation over the available data. Not "was not converted" — *cannot be*.

Consequently the plan's out-of-scope item **"Treating the wall-clock share as a token lever"** stays excluded, and the exclusion is now backed by a structural reason rather than by caution. The currency statement is carried into the shipped artifacts themselves (`log-analysis.md` LLM rule, `global-log-analysis.md` § signal 7, and both `summarize_script_cost` and the `audit.py` roll-up docstrings) so a future reader cannot quote the share without meeting the warning.

### D2 — aggregate cost is reportable — **DELIVERED** (commit `6a4254a`)

Shipped at **both** tiers, in each case as an **addition** — the per-call ceiling is untouched, keeps its predicate and its count, and both instruments are published over populations whose exact relationship is itself published, so they can be read together without assuming an identity that does not hold.

**Per-plan** (`plan-retrospective/scripts/analyze-logs.py`), via one shared helper `summarize_script_cost`:

- `script_cost_rollup` — population `plan_script_execution_log`, the same lines `slowest_scripts` and the percentiles summarise per-call.
- `global_log_signals.cost_rollup` — population `folded_global_logs`. Nearly, but **not exactly**, the lines `slow_call_count` reads: the roll-up additionally needs a parseable notation, because a cumulative total cannot be attributed to a script it cannot name. The excluded lines are published as `unattributable_calls`, which **bounds** the ceiling/roll-up gap rather than equalling it (it counts unnamed calls at every duration; the gap counts only those at or over the ceiling).

Each publishes `population`, `ceiling_seconds`, `calls_at_or_over_ceiling`, `total_calls`, `total_duration_ms`, `distinct_scripts`, `ranked_count`, and `ranked[]{notation,calls,cumulative_ms,share_pct,max_ms}`. `calls_at_or_over_ceiling` spans the whole population, **not** the truncated `ranked` list, so it can exceed the ceiling crossings the visible rows account for.

**Cross-plan** (`audit.py` `cross_global_log_analysis`): `cost_rollup` beside the existing `high_frequency` view — ungated by call count, ranked by seconds owned, each row carrying its share of the published `total_script_seconds`. Emitted as `dominant-cost-caller` rows plus the `cost_rollup_count`, `distinct_timed_call_keys`, `untimed_call_keys` and `cost_rollup_top_n` echo columns. The roll-up's `calls` counts **timed** calls only — the same population its seconds sum over.

**How the two are read together** — stated in the code and in three docs, not left implicit: a script ranked first with `calls_at_or_over_ceiling: 0` **is** the dominant-but-fast class the ceiling cannot see; a script the ceiling flags that ranks low is a rare outlier rather than a cost centre. Neither reading is available from one instrument alone.

**Context position** (the plan's second dimension) — `context_position_cost` reports weighted cached-read cost per tool use **by phase**, plus `position_multiple` and `position_multiple_basis` naming the two phases compared. It reports the **dimension** and asserts no figure, per the plan's claim-label instruction.

Population discipline throughout, because the epic's whole point is that a figure without its population is worse than none:

- A row missing **either** half of the rate — an unmeasured / unrecognised / indeterminate `cache_read_input_tokens`, or a `tool_uses` that is absent, null, non-integer or negative — is a **writer-side gap**, counted in `unmeasured_rows` and **never folded in as `0`**.
- A row where both are recorded and `tool_uses` is exactly `0` is a different fact: the record is complete and the ratio is arithmetically **undefined**. Counted apart, in `no_tool_use_rows`. The three counts reconcile against `total_rows`.
- Where a rate cannot be computed, **one of two** tokens is emitted, never a `0.0`: `unmeasured` when the record has a gap, `undefined` when it is complete and the arithmetic still has no answer. `unmeasured` is the weaker claim and is the default; only a demonstrably complete phase earns `undefined`.
- ⛔ The context-position figure is a **partition, not a whole**: cached-read is one of four context-load columns, so a `position_multiple` of 10x is 10x on cached-read tokens and is **not** a ratio over billed cost.
- `position_multiple` requires **two** measured phases; one phase is not a position signal.
- **No silent caps:** `distinct_scripts` / `distinct_timed_call_keys` are published beside the capped ranked lists, and the totals span the whole population, so a truncated tail stays derivable.

One design decision worth recording, forced by a regression the change itself caused: roll-up rows are stamped `informational`, not `genuine`. Some key is *always* the corpus's largest cost owner, so counting these would report a "signal" for every non-empty corpus and inflate `genuine_signal_count` by up to `cost_rollup_top_n` on every run — training readers to dismiss the count, which is the noise-source failure the plan's own claim-label table warns about.

### D3 — reduce the largest verified lever — **NOT ATTEMPTED (blocked), reason recorded**

D1 could not establish **which** path is reducible, because the corpus that would measure it is not in this clone. The plan forbids proceeding regardless: *"⛔ Do not optimise a path whose cost this run could not measure."*

The plan's own fallback is explicit and was taken: *"If the only available reduction risks either contract, prefer observability alone and record why"*, and *"The observability half is the durable deliverable and must not be dropped if the reduction half shrinks or empties."*

⇒ The **hard invariant is trivially preserved**: no change in this run touches the terminal-title / session-binding surface, the title-delivery-onto-the-delivering-channel fix, or the wait-mechanism stamp. The branch diff is 11 files, none of them in that surface.

### D4 — tests — **(a) DELIVERED, (b) N/A, (c) DELIVERED**

**(a) the roll-up ranks many-fast above few-slow — and it fails against today's reporting.** Two records, both stated, because they answer different questions.

*Observed at the time the first tests were written*, against the pre-change source:

```
12 failed, 1 passed
FAILED ...::TestScriptCostRollup::test_ranks_many_fast_above_few_slow  -> KeyError: 'cost_rollup'
FAILED ...::TestContextPositionCost::...  -> AttributeError: module 'analyze_logs' has no attribute 'summarize_context_position_cost'
```

*Re-derived at the moment of this claim* — the added test set has since grown through four verification rounds, so the earlier figure no longer describes it. The current tests were run against a `git worktree` at `origin/main`:

| Selection | Result against `origin/main` |
|---|---|
| `test_analyze_logs.py -k "ScriptCostRollup or ContextPositionCost or PerCallCeilingPreserved"` | **23 failed, 1 passed** |
| `test_audit_checks.py` (whole file) | **10 failed, 445 passed** |

The two passes are the ceiling pins (`test_ceiling_constant_unchanged`, `test_cross_plan_ceiling_constant_unchanged`) — correct, since they pin behaviour that already existed and that this change deliberately does not move. The cross-plan 10 is 8 added tests plus the 2 pre-existing tests this change legitimately modified.

The cross-plan assertion is the sharper of the two, because it fails **against a view that already existed**: the fixture puts 60 calls × 0.5 s (most calls) against 4 calls × 20 s (most time), then asserts the frequency view ranks the former first and **drops the latter entirely**, while the cost view ranks by time owned.

**(b) the reduction preserves the title/session contract — NOT APPLICABLE.** D3 was not attempted, so there is no reduction to assert against. Recorded as N/A rather than silently omitted. ⚠ **This means the plan's D4(b) requirement is genuinely undischarged, not satisfied** — it becomes live the moment D3 is attempted with corpus access.

**(c) a regression pin on the quantity D1 made the target — DELIVERED.** `test_ceiling_constant_unchanged` pins `_GLOBAL_LOG_SLOW_SECONDS == 30.0`. The target quantity D1 identified is the ceiling that proved blind, and the pin exists because the tempting "fix" is to lower it — which would silently redefine `slow_call_count` for every archived plan already measured against it. The roll-up was added *beside* the ceiling precisely so the ceiling need not move.

Also pinned: `test_cross_plan_ceiling_constant_unchanged` (the cross-plan copy of the same ceiling, which no test previously covered — every other test reads it dynamically, so lowering it failed nothing), `test_slow_call_count_still_fires_at_the_ceiling`, and `test_rollup_rows_are_informational_not_genuine_signals`.

**Test count.** Re-derived by AST at the moment of this claim, not carried forward from an earlier round — **33 test functions added**, 0 removed:

| File | added |
|---|---|
| `test/plan-marshall/plan-retrospective/test_analyze_logs.py` | 24 (78 → 102) |
| `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_checks.py` | 9 (439 → 448) |

Plus **2 pre-existing tests modified**: `test_block_carries_summary_lines_and_genuine_count` (the block now carries an informational row) and `test_thresholds_table_carries_every_documented_constant` (a new documented threshold).

⚠ The unit is **test functions**, counted by parsing the AST. It is **not** the number of cases pytest collects — parametrised tests expand — so a reader running the suite will see a larger number and the two are not comparable.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **non-empty** (`analyze-logs.py`, `audit.py`, and two test modules) ⇒ full `./pw verify` required and run.

⚠ **A defect in this run, recorded rather than hidden:** the first derivation of this diff was taken **before** `git fetch origin main` and was therefore against a stale `origin/main`, returning ~250 files spanning the whole repository. The Step 2 fetch had been skipped. Re-derived after fetching, and again at the moment of this claim: **11 files, of which 4 are `*.py`** (the branch has grown by four verification rounds since that first derivation, which reported 9). A stale ref makes the build-gate predicate over-fire rather than under-fire, so it did not weaken the gate — but the diff it produced was not the branch's diff, and every conclusion drawn from it would have been wrong.

**Result, from the run at the final code commit (`5dc5c67`): `=== verify: SUCCESS ===` — 20305 passed, 14 skipped, 357.92 s.** The gate was re-run after every verification round; earlier rounds recorded 20291 and 20301 as the test set grew. All three sub-steps ran: quality-gate (`ruff … All checks passed!`, `mypy … Success: no issues found in 408 source files`, `SPDX-header check passed`, plugin-doctor `issues[0]`), test-compile (`mypy(test)` 760 files), and module-tests.

A per-commit `./pw quality-gate` was run and read clean before the implementation commit. No `uv.lock` churn: `git status --porcelain` was empty after the build, and deliverable paths were staged explicitly (never `git add -A`).

## Findings

_Completed after the verification sub-agent and the PR review cycle report._

## Reviewer participation

_Completed after the PR review cycle._

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a token counter to the running agent, so no figure is stated rather than an estimated one.
- **Wall-clock:** not precisely available; the single measured component is the `./pw verify` gate at **405.61 s** (reported by pytest), plus one earlier `./pw quality-gate`.
- **Population:** these figures count **this single Claude Code cloud session**, as the harness counts it. ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a boundary a single interactive cloud session does not share. The figures cannot be made comparable here, so no ratio against any such total is offered.

## Contract check (Step 9)

_Completed at Step 8 condition 3, as the final pre-merge commit._

## What have we learned (Step 9)

_Completed at Step 8 condition 3._

## Residue

_Completed at Step 8 condition 3._
