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

Recorded **per instance**, not bundled. Four independent verification-sub-agent rounds ran before the PR; each round targeted the **previous round's fixes**, because that is where this run's defects actually lived.

### Round 1 — against the original change (14 confirmed, 9 suspicions)

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | sub-agent | `cost_rollup` row paired `calls` from `call_counts` (all notation-headed lines) with `cumulative_seconds` from `call_seconds` (timed lines only) — an absent duration read as zero inside the roll-up's own denominator | **Fixed** — `timed_call_counts` accumulator + regression test |
| 2 | sub-agent | `global-log-analysis.md` column table: "Every surfaced row is `genuine` by construction" — false once informational rows exist | **Fixed** |
| 3 | sub-agent | Same doc: "`genuine_signal_count` equals the row count" — false | **Fixed** |
| 4 | sub-agent | `kind` enumeration missing `dominant-cost-caller` | **Fixed** |
| 5 | sub-agent | `detail` enumeration missing the roll-up row shape | **Fixed** |
| 6 | sub-agent | `attributed_plans` note did not cover roll-up rows | **Fixed** |
| 7 | sub-agent | No orchestrator interpretation entry for the new row kind, while the doc mandates every row be adjudicated | **Fixed** |
| 8 | sub-agent | `emit_global_log_block` docstring falsified by its own body | **Fixed** |
| 9 | sub-agent | `audit.py` threshold-provenance comment missing `cost_rollup_top_n` | **Fixed** |
| 10 | sub-agent | `global-log-analysis.md` Critical-rules threshold list, same omission | **Fixed** |
| 11 | sub-agent | `audit.py` module docstring signal enumeration incomplete | **Fixed** |
| 12 | sub-agent | audit `SKILL.md` check-table enumeration incomplete | **Fixed** |
| 13 | sub-agent | `cross_global_log_analysis` docstring did not mention the new returned keys | **Fixed** |
| 14 | sub-agent | `TestEmitGlobalLogBlock` class docstring falsified (test file — CI cannot catch it) | **Fixed** |
| 15 | sub-agent (S1) | `distinct_call_keys` mis-named: it is timed keys only, not the `high_frequency` denominator | **Fixed** — renamed `distinct_timed_call_keys`, added `untimed_call_keys` |
| 16 | sub-agent (S2) | `position_multiple` reported `unmeasured` for a measured-but-undefined ratio | **Fixed** — new `undefined` token |
| 17 | sub-agent (S3) | `unmeasured_rows` folded two exclusion causes needing different remedies | **Fixed** — split out `no_tool_use_rows` |
| 18 | sub-agent (S4) | `test_thresholds_table_carries_every_documented_constant` enumeration incomplete (passes on `<=`) | **Fixed** |
| 19 | sub-agent (S5) | D4(c) pins a constant rather than a measured quantity | **Accepted, reasoned in the open** — D1's numeric half is blocked, so no measured target exists; the pin is the most that blocked state allows |
| 20 | sub-agent (S6) | `CHECK_ERA["global-log-analysis"]` not bumped though the check's semantics changed | **Fixed** — bumped to `#1260` with a mirror test |
| 21 | sub-agent (S7) | `fragment-log-analysis.toon` fixture now lacks the new keys | **Rejected as a defect, recorded as residue** — the fixture was already partial before this branch, and `retro_sections.py` renders the fragment generically with no shape assumption, so nothing breaks. The real gap is render coverage; see Residue |
| 22 | sub-agent (S8) | `log-analysis.md` key order did not match emission order | **Fixed** |
| 23 | sub-agent (S9) | Context-position figure's unit not named beside the currency warning | **Fixed** |

### Round 2 — against round 1's fixes (8 confirmed, 5 suspicions)

| # | Source | Finding | Disposition |
|---|---|---|---|
| 24 | sub-agent | `unattributable_calls` documented as "the gap is exactly that field" — it is an upper **bound** (it counts unnamed calls at every duration; the gap counts only those at or over the ceiling) | **Fixed** |
| 25 | sub-agent | `rows[G]` in the emitted schema — false once informational rows join the table | **Fixed** — `rows[N]` |
| 26 | sub-agent | `by_phase` rate described as two-valued after the third token was added | **Fixed** |
| 27 | sub-agent | Second site with the same two-valued residue | **Fixed** |
| 28 | sub-agent | `calls_at_or_over_ceiling` documented as computed "over exactly the calls `ranked` summarises" — it spans the whole population | **Fixed** + pinning test |
| 29 | sub-agent | The check doc's adjudication carve-out **contradicted** the `SKILL.md` contract it cited | **Fixed** — aligned the check doc to `SKILL.md` (one-line cited dismissal) rather than weakening the broader contract; `SKILL.md` Step-3 enumeration now names the kind |
| 30 | sub-agent | `undefined` emitted whenever a phase had any zero-tool-use row, asserting a completeness the phase lacked | **Fixed** — gated on `phase_unmeasured == 0` |
| 31 | sub-agent | `unattributable_calls` shipped with **zero** test coverage — the one field round 1 added without one, and precisely where its false claim survived | **Fixed** — two tests, covering the strict-inequality and equality cases |
| 32 | sub-agent (S-a) | A row missing `tool_uses` classified as `no_tool_use` though the record is incomplete | **Fixed** |
| 33 | sub-agent (S-b) | `context_position_cost` quoted a **partition as a whole** — cache-read is one of four context-load columns. The plan's own claim-label table demands establishing this before quoting any ratio | **Fixed** — partition warning at both sites |
| 34 | sub-agent (S-c) | Report's "zero hits" sweep claim not scoped | **Fixed** in the report |
| 35 | sub-agent (S-d) | Report called an `audit.py` inline comment a docstring | **Fixed** in the report |
| 36 | sub-agent (S-e) | Over-long line in the check doc | **Fixed** |

### Round 3 — against round 2's fixes (4 confirmed, 2 suspicions)

Round 3 verified round 2's substantive work by **mutation testing** (six mutations, all killed) and a **3,970-corpus brute force** of the bound inequality. All held.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 37 | sub-agent | `unmeasured_rows` docstring still said "carries no `cache_read_input_tokens` key at all" after the filter was broadened to require both keys — contradicting a test in the same commit | **Fixed** |
| 38 | sub-agent | Same claim mirrored in `log-analysis.md` | **Fixed** |
| 39 | sub-agent | `by_phase` `unmeasured` description false for an empty-rows phase | **Fixed** + test |
| 40 | sub-agent | `references/log-analysis.md` retained the "EXACT difference" framing after the docstring was corrected to "bound" | **Fixed** |
| 41 | sub-agent (S-a) | `row['tool_uses'] or 0` folds `None` into the zero bucket, routing a **null denominator** to `undefined` — which asserts a complete record. Same absent-read-as-zero shape, one layer down, inside the function whose comment forbids it | **Fixed** + two tests |
| 42 | sub-agent (S-b) | `_GLOBAL_LOG_DUR_RE` looser than the cross-plan reader's: `(1.2.3s)` matched, `float()` raised, the duration became `0.0`, and the line **still joined the roll-up** | **Fixed** — pattern refuses the match; parse guard drops rather than zeroes; + test |

### Round 4 — against round 3's fixes (2 confirmed, 6 nits) — **convergence**

Round 4 mutation-tested every round-3 claim and enumerated all 0x110000 codepoints against the regex/`float()` boundary. It found **no code defect** and reported the change ready.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 43 | sub-agent | Docstring said `slow_call_count` "counts every duration-bearing line" — it is *drawn from* them and counts only those at or over the ceiling | **Fixed** |
| 44 | sub-agent | Same population-vs-count conflation in `log-analysis.md` ("counted by the ceiling") | **Fixed** |
| 45 | sub-agent (N1) | "exact difference" framing survived in an inline comment | **Fixed** — clarified as population **sizes**, not ceiling counts |
| 46 | sub-agent (N2) | Comment describing `cost_rollup` attached to the key above it | **Fixed** |
| 47 | sub-agent (N3) | Docstring said "non-integer or negative", but a bool is an int and non-negative yet correctly excluded | **Fixed** — "not a usable count" |
| 48 | sub-agent (N4) | `by_phase` rate column shipped without a value legend | **Fixed** |
| 49 | sub-agent (N5) | Sibling check doc's discovery-volume pointer incomplete | **Fixed** |
| 50 | sub-agent (N6) | Report's two wall-clock figures disagreed | **Fixed** |

### From PR review — the finding four verification rounds missed

| # | Source | Finding | Disposition |
|---|---|---|---|
| 53 | `cuioss-review-bot` (PR #1260) | `summarize_context_position_cost` guards `tool_uses` against `None` / non-integer / negative but does **not** guard `cache_read_input_tokens`. A row carrying a null numerator beside a valid denominator reaches the accumulator and raises `TypeError`, **crashing log analysis** on exactly the row this function exists to classify as a recording gap | **Fixed** — one `_is_usable_count` predicate applied to both halves, plus three tests (null, non-numeric, negative numerator) |

⭐ **This is the most valuable finding of the run, and no verification round found it.** It is the *same defect class* the rounds had already fixed twice — an unusable value folded into a measurement — but applied **asymmetrically**: round 3 hardened the denominator against a null and left the numerator, one line away, unguarded. Every round after that read the hardened line and saw the guard it expected.

Two things follow, both recorded rather than smoothed over:

- **The recovery check earned its place.** This reviewer's verdict was provisionally `silent`; the finding arrived only because § Step 7's recovery posted the registry's `trigger_comment`. Had the run disclosed `silent` and merged, this defect would have landed.
- **A guard added to one side of a pair is a defect surface.** The verification rounds sweep what a fix made false *elsewhere*; none of them asks whether a fix was applied to *every* member of the symmetric pair it belongs to. That is a narrower and more mechanical check than the sweeps already in the contract.

### From CI / the merge queue

| # | Source | Finding | Disposition |
|---|---|---|---|
| 51 | local build | `ruff I001` — import block un-sorted in the new test module created during merge resolution | **Fixed** — aligned to the sibling convention |
| 52 | GitHub | `mergeable_state: dirty` — #1258 decomposed `test_audit_checks.py` into 49 modules while this branch was editing it | **Fixed** — see Deliverables/merge note; each change placed in the home the new layout gives it |

## Reviewer participation

**Population derived from configuration**, not transcribed: the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc — `coderabbit.md`, `pr-agent.md`, `sourcery.md`.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | `rate-limited` | **yes** | *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. **Next review available in: 26 minutes**."* A per-developer rolling quota — clears on the clock. |
| `sourcery-ai` | `rate-limited` | **yes (weekly)** | *"you have reached your **weekly rate limit of 500000 diff characters**."* A weekly quota, not a per-PR size ceiling — it clears at the week boundary, but the notice states no time, so it is not re-requestable on a useful horizon for this run. |
| `cuioss-review-bot` | **`reviewed`** (after recovery) | — | Initially published nothing. After the recovery below, filed a *"PR Reviewer Guide"* issue-comment with one **Possible Issue** — the unguarded `cache_read_input_tokens` numerator (finding #53), which was real and is fixed. |

**Recovery check for the `silent` verdict** (§ Step 7). Queried the Actions API **by event, not by head branch** — the documented false-negative trap, since an `issue_comment`-triggered run is attributed to the default branch. One `PR Agent Review` run exists for this PR (`display_title` matches), `event: issue_comment`, `head_branch: main`, **`conclusion: skipped`** — triggered by CodeRabbit's own rate-limit comment rather than by a `/review` command, and correctly skipped. `.github/workflows/pr-agent.yml` deliberately does **not** subscribe to `synchronize`, so no push can trigger it; the only automatic chance was the `opened` event. The registry's declared `trigger_comment` (`/review`) was therefore posted as the recovery action, and the outcome is recorded above.

**Coverage: 1 of 3 — and the 1 is the recovered reviewer.** `cuioss-review-bot` reviewed and its single finding was real, actionable, and fixed. `coderabbitai` and `sourcery-ai` both refused on quota and neither reviewed this diff. The § Step 8 shortfall disclosure fired and is stated there in words.

⚠ **The recovery changed the outcome of this run.** Had the provisional `silent` verdict been disclosed and the PR merged on 0-of-3 actual reviews, finding #53 would have shipped. The recovery step is the reason coverage is 1 rather than 0.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a token counter to the running agent, so no figure is stated rather than an estimated one.
- **Wall-clock:** not precisely available for the run as a whole. The measured components are the `./pw verify` gate, run once per verification round — **405.61 s**, **353.72 s**, **357.92 s** and a final pass — plus several `./pw quality-gate` calls. Each figure is the pytest-reported duration of that run; they are not summable into a run total, because the agent's own wall-clock between them is not instrumented.
- **Population:** these figures count **this single Claude Code cloud session**, as the harness counts it. ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a boundary a single interactive cloud session does not share. The figures cannot be made comparable here, so no ratio against any such total is offered.

## Contract check (Step 9)

**GitHub access path:** the GitHub MCP server (the cloud path). No `gh` CLI in this session.
**Branch form:** **harness-assigned** — `claude/aggregate-cost-per-call-ceiling-wxrfms`, kept as-is per the lane contract; no prefixed branch was created.
**Plugin cache sync:** a cloud run neither performs nor owes one (§ Scope and precedence).

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done, with an ordering defect** | Named in § Skills loaded. The two `pm-dev-python` skills were loaded *after* implementation began; that late load is what surfaced the deliverable-id citations in the test docstrings. Recorded, not smoothed over. |
| 2 Branch | **Done** | Branch exists on `origin`. ⚠ **The Step 2 `git fetch origin main` was skipped**, which made the first build-gate diff derive against a stale ref (~250 files instead of 9). It over-fired rather than under-fired, so the gate was not weakened — but the diff was not the branch's diff. Corrected on discovery. |
| 3 Plan directory | **Done** | `doc/plans/code-intelligence-substrate/270-aggregate-cost-invisible-to-per-call-ceiling/plan.md` exists and opens with the first-instruction block (verified present on receipt — no repair needed — and re-verified after the move). |
| 4 Implement | **Done** | Commits carry the trailer; deliverables addressed per § Deliverables. |
| 4 Per-commit gate | **Done** | Every commit touching `*.py` was preceded by a `./pw quality-gate` read clean on the tool lines (`ruff … All checks passed!`, `mypy … Success`, `SPDX-header check passed`, plugin-doctor `issues[0]`). |
| 4 Pushed | **Done** | Pushed after every commit; no unpushed commit remains. |
| 5 Build gate | **Done** | Git-derived verdict and outcome in § Build gate. Full `./pw verify` re-run after every verification round and after the merge resolution. |
| 6 Verification sub-agent | **Done — four rounds** | 52 findings with dispositions in § Findings. Two rejected with reasons recorded (#19, #21). |
| 7 PR cycle | **Done** | PR #1260. Every comment dispositioned (finding #53 fixed; the two quota notices are not actionable). All **three** comment surfaces read (`get_comments`, `get_reviews`, `get_review_comments`) — the review-summary surface carried Sourcery's notice and nothing else would have shown it. Participation table carries a verdict **and** a `Reopens?` value per reviewer; the `silent` verdict records what its recovery check found. |
| 8 Merge gate | See § Step 8 disclosure below | Conditions 1–3 met before arming. |
| 8 Bridge | **Done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory. The merge commit brought in another plan's directory as ordinary merge content, not as a write by this run. |
| 9 This check | **Done** | This table. |
| 9 What have we learned | **Done** | Two proposals below, presented to the operator and **not** self-approved. |

### ⚠ A contract disagreement observed, and reported as the plan's preamble requires

`CLAUDE.md` § Standalone Plan Lane says a lane plan that edits `marketplace/bundles/` "records in its run report that a local sync is owed." The `cloud-plan-lane` skill says the opposite in bold: a cloud run "**neither performs nor owes**" a sync, and it is "not a debt this run tracks or records." This branch edits four files under `marketplace/bundles/`, so the two rules give opposite instructions.

The run followed **the skill**, because the plan's own first-instruction block makes the contract authoritative where the two disagree — and requires the disagreement to be reported. This is that report. The contradiction is **pre-existing** and not introduced by this branch.

## What have we learned (Step 9)

Two proposals, each with evidence **from this run**. Both are **presented to the operator and not self-approved**; neither is shipped in this PR, and if accepted each belongs on its own `chore/` branch.

### Proposal 1 — a field added without a test is where the next round's false claim survives

**Evidence.** The contract already says to sweep the previous round's fixes as a first-class surface, and that is what caught rounds 2–4. But it does not say *where inside those fixes to look first*. This run produced a sharp answer. Round 1 added five fields; four got pinning tests and one — `unattributable_calls` — did not. That is precisely the field whose docstring round 2 got wrong, and the error survived until round 3. Round 2's own commit message had already made "with a regression test that would have caught it" its stated standard, and then did not apply it to the field it was adding.

**Proposed edit** to § Step 6, in the per-round sweep: before re-dispatching, list the fields, constants, or return keys the round added, and check each has a test that would fail if its documented behaviour regressed. An untested addition is the highest-risk item in the round's own diff, because nothing but prose describes it.

### Proposal 3 — a guard applied to one half of a symmetric pair

**Evidence.** Round 3 hardened `tool_uses` against `None` / non-integer / negative and left `cache_read_input_tokens`, one line away and part of the same rate, unguarded. A null numerator therefore raised `TypeError` instead of being classified as the recording gap the function exists to classify. **Four verification rounds read that line and none caught it** — each saw a guard and confirmed the guard was correct. It took the PR reviewer, and it took the § Step 7 recovery firing to get that reviewer to speak at all.

The existing per-round sweep asks what a fix made false *elsewhere in the tree*. It does not ask whether a fix was applied to *every member of the symmetric pair it belongs to*, which is a narrower and far more mechanical question — a numerator and its denominator, a reader and its writer, a getter and its setter.

**Proposed edit** to § Step 6: when a fix hardens, validates, or normalises one value, name the values that must hold the same property and check each. A guard on one half of a pair is the shape a whole round can read past.

### Proposal 2 — the run's own build mutates the tree the report describes

**Evidence.** This report stated that `.plan/` carried "only `marshal.json` and `project-architecture` — no `logs/`, no `local/`". True when written. By the time the build gate had run, `./pw verify` had created `.plan/execute-script.py`, `.plan/temp/`, and `.plan/local/logs/script-execution-2026-08-16.log` — in the very tree the sentence described. A verification round caught it; no gate could have, because the claim is about the filesystem rather than the code.

**Proposed edit** to § Report or § Step 9: a report claim about the state of the working tree is re-verified at finalize, because the run's own build gate mutates that tree. Only claims about the *tree* need this — claims about the diff are already re-derived.

## Residue

- **D1's numeric re-derivation and D3 remain open**, blocked on corpus availability. When an archived-plan corpus is reachable, the roll-up shipped here is the instrument that answers D1(b)'s "which path is reducible" — that was the point of shipping observability first. D4(b) becomes live at the same moment and is **genuinely undischarged**, not satisfied.
- **No end-to-end render coverage for the new fragment keys.** `report-structure.md`'s section-4 contract now names `script_cost_rollup` and `context_position_cost`, but the archived-plan fixture `test/plan-marshall/plan-retrospective/fixtures/archived-plan/work/fragment-log-analysis.toon` is a hand-written partial that predates this branch (it already omitted `build_time`, `global_log_signals`, `dispatch_boundaries`, `findings`). Nothing breaks — `retro_sections.py` renders the fragment generically — so this is a coverage gap, not a defect. Widening the fixture is a clean follow-up.
- **`CLAUDE.md` ↔ `cloud-plan-lane` contradiction on plugin-cache sync** (§ Contract check). Pre-existing; needs one of the two documents amended so a future run is not left choosing.
- **Pre-existing deliverable-id citations in the two touched test modules.** The test-prose convention forbids them; this run removed its own but did not sweep the files, which carry others from earlier plans. Out of scope here.
