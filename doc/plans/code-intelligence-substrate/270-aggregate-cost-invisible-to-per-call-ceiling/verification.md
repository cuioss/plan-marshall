# Verification — 270-aggregate-cost-invisible-to-per-call-ceiling

**Audited:** `plan.md`, `report-01.md`
**Tree state:** `26a54e0` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The observability half of the plan (D2) shipped, is correct on the paths I read and mutated, and is
covered by tests that go red against the pre-change source. D1's numeric half and D3 are blocked
exactly as the plan's own fallback directs, and the run said so.

The gaps, in the order the Correctness review takes them: a precision defect in the cross-plan
roll-up's *published denominator* (§1 — the same arithmetic class the PR reviewer rated Major one
column over, and re-rated **high** on adversarial review); a duration-grammar asymmetry inside
`analyze-logs.py` that makes its two roll-ups disagree about the same log line (§2); a
duration-bearing line silently dropped from every published counter (§3); a **missing line-shape
guard** on the per-plan reader that lets a captured-output continuation line enter the shipped
roll-up as a call that never happened (§4 — added on adversarial review, **high**); and schema-doc
key-order drift in `references/log-analysis.md` (§5). Beyond the code: three stale numeric claims in
`report-01.md`, and the run's own declared residue. Each maps to a numbered entry in `gaps.md`.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: first-party figures + currency restatement + decide (a)/(b) | PARTIAL — corpus unreachable, numeric half blocked; structural half + currency delivered | Structural predicates confirmed in the tree; currency statement present in code and in three docs; (a) decided and shipped, (b) undecided | PARTIAL (as the plan directs) |
| D2 | Aggregate cost reportable, ranked by share, ceiling preserved, context position included | DELIVERED at both tiers | `summarize_script_cost` + `summarize_context_position_cost` (per-plan) and `cost_rollup` (cross-plan) all present; ceiling constant and predicate untouched | CONFIRMED (with a denominator-precision defect and an unguarded per-plan input path, both **high** — see Correctness §1 and §4) |
| D3 | Reduce the largest verified lever | NOT ATTEMPTED, reason recorded | No file in the merge commit touches the terminal-title / session-binding surface | CONFIRMED (blocked, correctly recorded) |
| D4(a) | Roll-up ranks many-fast above few-slow; must fail against today's reporting | DELIVERED; pre-fix failure recorded | Tests exist at both tiers and both go red against the pre-change source and against a ranking mutation | CONFIRMED |
| D4(b) | Reduction preserves the title/session contract | N/A — genuinely undischarged | No such test exists; correctly so, since D3 did not land | CONFIRMED as undischarged |
| D4(c) | Regression pin on the quantity D1 made the target | DELIVERED — pins `_GLOBAL_LOG_SLOW_SECONDS == 30.0` | Both pins present and both are the only added tests that pass against the pre-change source | PARTIAL — pins a constant, not a measured quantity (deviation accepted in the open as finding #19) |

## Per-deliverable detail

### D1 — GATE: verify first-party and restate in the billing currency

- **Required (plan):** *"the figures are first-party, the currency is stated, and (a) and (b) are
  decided"*, with an explicit fallback: if the corpus is unreachable, *"ship D2 … and report D1's
  re-derivation and D3 blocked on corpus availability"*.
- **Claimed (report):** numeric re-derivation blocked; structural half confirmed first-party;
  currency restated as a **latency** finding, structurally unconvertible; (a) decided, (b) not
  decidable.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:132` —
    `_GLOBAL_LOG_SLOW_SECONDS = 30.0`, and `analyze-logs.py:1471` `if seconds >=
    _GLOBAL_LOG_SLOW_SECONDS: slow_call_count += 1`. The ceiling's blindness to a
    many-fast-calls script follows from that predicate alone; no corpus needed.
  - `analyze-logs.py:1524` — `slowest = sorted(durations, key=lambda x: (-x[1], x[0]))[:3]`, i.e.
    ranking by the largest **single** call, exactly as the report states.
  - Currency statements are in the tree at four sites: `analyze-logs.py:427-432` (roll-up docstring),
    `analyze-logs.py:543-555` (context-position docstring, including the partition warning),
    `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2875-2877`, and
    `.claude/skills/audit-archived-plan-retrospectives/checks/global-log-analysis.md:101-105` and
    `:264-267`, plus
    `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/log-analysis.md:141-142`.
- **Checks run:**
  - Re-derived the report's pre-change "zero hits" sweep:
    `git grep -nE "cumulative|share_of_total|total_duration|total_ms" '89edc99^' -- '…/plan-retrospective/scripts/'`
    → **no output** (zero hits). The same sweep over the whole skill directory returns **one** hit
    (`SKILL.md:157`, "assign-cumulative"), so the report's unscoped phrasing is imprecise — see
    Report accuracy.
- **Verdict:** PARTIAL, and the partiality is the plan's own instructed fallback rather than a
  shortfall. The integrity check the plan names ("a run report that quotes the wall-clock share
  without saying which currency it is in has failed this deliverable") is **passed**: the report
  states plainly that this is a latency finding and the statement is carried into the shipped code
  and docs, not just into the report.

### D2 — aggregate cost is reportable

- **Required (plan):** a roll-up of cumulative wall-clock and call count per script, ranked by share
  of total; the per-call ceiling stays; the deliverable states how the two are read together; context
  position is a reportable dimension. *Done when:* the roll-up ranks a many-fast-calls script above a
  few-slow-calls script.
- **Claimed (report):** shipped at both tiers as an addition, with population discipline and the
  read-together instruction stated in code and in three docs.
- **Found:**
  - Per-plan: `analyze-logs.py:400-508` `summarize_script_cost`, wired at `analyze-logs.py:1688`
    (`script_cost_rollup`, population `plan_script_execution_log`) and at `analyze-logs.py:1500`
    (`global_log_signals.cost_rollup`, population `folded_global_logs`).
  - Context position: `analyze-logs.py:527-706` `summarize_context_position_cost`, wired at
    `analyze-logs.py:1696`.
  - Cross-plan: `audit.py:2887-2912` (roll-up construction), `audit.py:2949-2955` (published
    counters), `audit.py:6053-6068` (the `dominant-cost-caller` rows), `audit.py:6085-6087` (the
    `informational` stamp).
  - Ceiling preserved: `analyze-logs.py:132` and `audit.py:681` `"slow_call_seconds": 30.0` are
    unchanged; `audit.py:394` bumps `CHECK_ERA["global-log-analysis"]` to `#1260` with the reason
    documented at `audit.py:384-393`.
  - Read-together instruction: `analyze-logs.py:417-425`,
    `checks/global-log-analysis.md:91-105` and `:245-256`, `references/log-analysis.md:139`.
- **Checks run:**
  - Ran the shipped tests: `uv run python -m pytest test/plan-marshall/plan-retrospective/test_analyze_logs.py test/plan-marshall/audit-archived-plan-retrospectives/ -o addopts="" -q` → **750 passed**.
  - Mutation: changed the per-plan ranking key from `-cumulative[n]` to `-maxima[n]`
    (`analyze-logs.py:476`) → `test_ranks_many_fast_above_few_slow` and
    `test_ceiling_is_blind_to_the_script_the_rollup_ranks_first` **failed** (2 failed, 9 passed).
  - Mutation: changed the cross-plan ranking key from `-call_seconds[k]` to `-call_counts[k]`
    (`audit.py:2888`) → `test_ranks_by_time_owned_not_by_call_count` **failed**.
  - First-party probe of the emitted block on a synthetic corpus (see Correctness review) — the
    roll-up ranks and publishes as described.
- **Verdict:** CONFIRMED. The *Done when* holds — the roll-up ranks by cumulative time, re-verified
  first-party by emitting the shipped function's output and by killing `test_ranks_many_fast_above_few_slow`
  with a ranking mutation — and the addition-not-replacement constraint holds. Two correctness
  defects sit inside the confirmed deliverable and neither unseats it: the cross-plan tier's
  **published denominator** misreports in the small-corpus regime (Correctness §1), and the per-plan
  tier's **input path is ungated**, so a captured-output continuation line can enter the roll-up as a
  call that never happened (Correctness §4). Both are rated **high**: the ranking contract the
  *Done when* names is intact, but what the instrument publishes beside that ranking is not
  trustworthy in the regimes named.

### D3 — reduce the largest verified lever

- **Required (plan):** the reduction lands with the contract asserted, **or** the run records why it
  was not attempted; the terminal-title / session-binding contract may not regress.
- **Claimed (report):** not attempted, blocked on D1; the branch diff is 15 files, none in that
  surface.
- **Found:** `git show --stat 89edc99` lists exactly **15** paths: `audit.py`, `analyze-logs.py`,
  five test modules, the audit `SKILL.md`, `checks/global-log-analysis.md`,
  `checks/architecture-lookup-ratio.md`, the plan-retrospective `SKILL.md`,
  `references/log-analysis.md`, `references/report-structure.md`, and the plan's own `plan.md`
  (moved) and `report-01.md`. No session/terminal-title/hook file appears.
- **Verdict:** CONFIRMED — blocked, with the reason recorded, and the hard invariant trivially
  preserved because nothing in that surface was touched.

### D4 — tests

- **Required (plan):** (a) the ranking assertion, which must fail against today's reporting;
  (b) delivery of the title/session contract asserted; (c) a regression pin on whichever quantity D1
  made the target.
- **Found and checks run:**
  - (a) Per-plan `TestScriptCostRollup` (`test/plan-marshall/plan-retrospective/test_analyze_logs.py:1980-2176`,
    11 tests) and cross-plan
    `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_global_log_analysis_cost_rollup.py`
    (12 tests). **Pre-fix failure re-derived first-party**: I temporarily wrote the `89edc99^`
    versions of `analyze-logs.py` and `audit.py` into place (byte snapshots taken first, restored
    afterwards, `git status --porcelain` clean for both) and ran the two selections:
    - `test_analyze_logs.py -k "ScriptCostRollup or ContextPositionCost or PerCallCeilingPreserved"`
      → **29 failed, 1 passed**;
    - `test_audit_check_global_log_analysis_cost_rollup.py` → **11 failed, 1 passed**.
    The single pass in each is the ceiling pin, exactly as the report describes.
  - (b) No such test exists; correct, since D3 did not land. The plan's requirement is therefore
    genuinely undischarged rather than satisfied, which the report states.
  - (c) `test_ceiling_constant_unchanged` (`test_analyze_logs.py:2181`) and
    `test_cross_plan_ceiling_constant_unchanged`
    (`test_audit_check_global_log_analysis_cost_rollup.py:172`).
- **Verdict:** (a) CONFIRMED and non-vacuous; (b) CONFIRMED as undischarged; (c) PARTIAL — the pin is
  on a **constant**, not on a measured quantity, because D1 never produced one. The run recorded and
  reasoned this deviation openly (finding #19), so it is a labelled deviation rather than a hidden
  one.

## Correctness review

I read `summarize_script_cost`, `_is_usable_count`, `summarize_context_position_cost`,
`analyze_folded_global_logs`, `cross_global_log_analysis` and `emit_global_log_block` end to end.
Five defects, all first-party reproduced. (§4 and §5 were added on adversarial review; §1–§3 were
independently re-reproduced then and are unchanged.)

### 1. The cross-plan roll-up's published denominator is rounded away (`audit.py:2931`)

`share_pct` is computed against `rollup_total = round(total_seconds, 3)` (`audit.py:2887`), while the
block publishes `"total_script_seconds": round(total_seconds, 1)` (`audit.py:2931`, emitted at
`audit.py:6120`). The in-code comment at `audit.py:2871-2873` and `:2884-2886` asserts the opposite —
that `share_pct` is *"a share of `total_script_seconds`, the SAME denominator the block publishes …
so a reader recomputing it from the printed columns gets the printed value back"* — and
`checks/global-log-analysis.md:94` and `:247` repeat the claim to the orchestrator.

Reproduced by loading `audit.py` directly and calling `cross_global_log_analysis` on synthetic logs:

- One `0.04 s` call → the emitted block reads `total_script_seconds: 0.0` and
  `sub_precision_call_count: 0`, beside
  `dominant-cost-caller,1x 0.040s 100.0% pm:a:a run,,informational`. A corpus total of `0.0` with a
  row owning `100.0 %` of it, and nothing flagging the shortfall.
- `pm:a:a run (0.24s)` + `pm:b:b run (0.20s)` → published `total_script_seconds: 0.4`,
  rows `0.24 / 54.5 %` and `0.20 / 45.5 %`. Recomputing from the printed columns gives `60.0 %` and
  `50.0 %`, which also sum to 110 %.

Consequence: in the small-corpus regime the published corpus total is a measured non-zero rendered as
zero, and the reconciliation the doc promises does not hold. This is the identical arithmetic class
CodeRabbit rated **Major** (report finding #54) applied one column over — the row was fixed to
millisecond precision, the denominator it is a share of was not.

### 2. Two duration grammars inside the same file disagree about the same line (`analyze-logs.py:88` vs `:112`)

`_DURATION_RE = re.compile(r'\((\d+\.?\d*)s\)')` (`analyze-logs.py:88`) feeds
`extract_script_durations` and therefore the per-plan `script_cost_rollup`, the percentiles and
`slowest_scripts`. `_GLOBAL_LOG_DUR_RE = re.compile(r'\((\d+(?:\.\d+)?)s\)\s*$')`
(`analyze-logs.py:112`) feeds `analyze_folded_global_logs` and therefore `slow_call_count` and
`global_log_signals.cost_rollup`. The second was deliberately tightened by report finding #42; the
first was not. Reproduced by loading the module through `test/conftest.py`:

```
per-plan extract_script_durations -> [('pm:x:x', 5000.0), ('pm:y:y', 1500.0), ('pm:z:z', 1500.0)]
global: pm:x:x run (5.s)                     -> None
global: pm:y:y run (1.5s) failed             -> None
global: pm:z:z run (1.5s) retried (2.00s)    -> 2.00
```

Three divergences: a malformed `(5.s)` is read as **5000 ms** by one roll-up and refused by the
other; a non-terminal duration is counted by one and invisible to the other; and where two
parenthesised durations appear, the per-plan reader takes the **first** and the global reader the
**last**, so the two roll-ups publish different cumulative totals for the same physical line.
`references/log-analysis.md:109-110` tells the reader the two are the *"Same shape … different
population"*, which understates the difference: they are also different **grammars**. This is
precisely the "a guard applied to one half of a symmetric pair" shape the run's own Proposal 3 names.

### 3. A refused-duration line is dropped from every published counter (`analyze-logs.py:1462-1477`)

In `analyze_folded_global_logs`, a line whose duration the strict regex refuses (`dur_match` is
`None`) contributes to `total_lines` and nothing else: it is not in `slow_call_count`, not in the
roll-up, and — unlike a duration-bearing line with no notation — not in `unattributable_calls`. The
fragment's population discipline publishes the ceiling/roll-up gap (`unattributable_calls`) but has
no counter for the timed-lines-refused-by-the-grammar class, so that exclusion is silent. The
cross-plan tier does not have this hole: an untimed notation-headed line still lands in
`untimed_call_keys` (`audit.py:2950`).

### 4. The per-plan duration reader has no line-shape guard (`analyze-logs.py:378-397`)

`extract_script_durations` runs `_DURATION_RE` and `_NOTATION_RE` over **every line** it is handed.
`read_log` (`analyze-logs.py:335`) returns every non-empty line of the script log with no shape
filter, so the input includes an entry's indented **continuation lines** — which
`format_log_entry` (`manage-logging/scripts/plan_logging.py:138-142`) emits for `exit_code`, `args`,
`stdout` and `stderr` on every non-zero-exit call (`plan_logging.py:346-360`). The sibling
`analyze_folded_global_logs` does gate, on `_GLOBAL_LOG_LINE_RE.match(raw)` at
`analyze-logs.py:1455-1457`.

Reproduced by generating one entry through the real writer and feeding both readers:

```
[2026-08-19T07:41:58Z] [ERROR] [0ee8a3] pm:b:build run (1.20s)
  exit_code: 1
  args: pm:b:build run --command-args verify
  stdout: tests finished pm:t:t run (9.99s) ok

per-plan extract_script_durations -> [('pm:b:build', 1200.0), ('pm:t:t', 9990.0)]
global reader                     -> 1.20   (three continuation lines SKIPPED, no header)
```

The per-plan reader manufactured a 9.99 s `pm:t:t` call out of text a failing script printed. That
list is the sole input to `summarize_script_cost` (`analyze-logs.py:1521`) — the deliverable this
plan shipped — and to `total_duration_ms`, every `share_pct`, `script_duration_p50/p95/max_ms` and
`slowest_scripts`. This is the sharper half of the §2 asymmetry: §2's bodies are synthetic and no
current writer emits them, whereas this one has a writer path that fires on every failed script call.
Filed as `gaps.md` **G14**, severity **high**.

### 5. The schema doc's key order does not match the emitted TOON (`references/log-analysis.md:50-61`)

`serialize_toon` iterates `data.items()` (`ref-toon-format/scripts/toon_parser.py:552`) and
`_is_uniform_array` builds a uniform-array header from first-occurrence key order (`:520-527`), so
emitted order **is** dict insertion order. Emitting the shipped function's own output first-party:

```
script_cost_rollup:
  population / ceiling_seconds / calls_at_or_over_ceiling / total_calls / total_duration_ms
  sub_precision_calls / distinct_scripts / ranked_count
  ranked[2]{notation,calls,cumulative_ms,sub_precision_calls,share_pct,max_ms}:
```

The doc places `sub_precision_calls` after `ranked_count` (`log-analysis.md:60`) and documents the
header as `{notation,calls,cumulative_ms,share_pct,max_ms,sub_precision_calls}` (`:61`). Both differ
from what ships. Report finding #22 recorded and fixed exactly this drift class; the later
`sub_precision_calls` addition (finding #55) reintroduced it in two places. Filed as `gaps.md` **G6**
and **G7**, both **low** — a schema doc is read by a parser author, not by the running code.

### Paths read and found clean

- `_is_usable_count` (`analyze-logs.py:511-524`) is symmetric and applied to both halves at
  `analyze-logs.py:635`; `bool` is excluded explicitly and pinned by a test.
- `no_tool_use_rows` vs `unmeasured_rows` reconcile: `unmeasured_rows = total_rows - measured_rows -
  no_tool_use_rows` (`analyze-logs.py:701`), and `undefined` is gated on `phase_unmeasured == 0`
  (`analyze-logs.py:667`) so it never claims completeness a phase lacks.
- The `position_multiple` tie-break (`analyze-logs.py:686-687`) does name two distinct phases on
  equal rates, and a zero lowest rate yields `undefined` rather than `unmeasured`
  (`analyze-logs.py:691-696`).
- `calls_at_or_over_ceiling` spans the whole population, not the truncated `ranked` list
  (`analyze-logs.py:462, 471-472`), and a test pins that.
- `share_pct` on the **per-plan** side is computed from the same rounded `total_duration_ms` the
  fragment publishes (`analyze-logs.py:474, 491-493`) — the defect in §1 is confined to the
  cross-plan tier.
- `informational` stamping cannot leak into `genuine_signal_count` (`audit.py:6085-6087`), pinned by
  `test_rollup_rows_are_informational_not_genuine_signals`.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D2 roll-up (`summarize_script_cost`, driven via the `folded_global_logs` wiring) | `TestScriptCostRollup` (11) at `test_analyze_logs.py:1980` | Ranking mutation (`-cumulative[n]` → `-maxima[n]`) killed 2 tests, re-run and re-confirmed on adversarial review (2 failed, 9 passed); pre-change source killed 29 of 30 in the selection. ⚠ The `plan_script_execution_log` wiring is **not** driven here — see the second coverage hole below |
| D2 context position | `TestContextPositionCost` (17) at `test_analyze_logs.py:2204` | Dropping the numerator half of the guard at `analyze-logs.py:635` killed 4 tests (`null`, `non_numeric`, `negative`, `bool` cache-read) |
| D2 cross-plan roll-up | `test_audit_check_global_log_analysis_cost_rollup.py` (12) | Ranking mutation killed `test_ranks_by_time_owned_not_by_call_count`; swapping `timed_call_counts[key]` for `call_counts[key]` killed `test_calls_counts_only_timed_calls_not_every_notation_line` |
| D4(c) ceiling pins | `test_ceiling_constant_unchanged`, `test_cross_plan_ceiling_constant_unchanged` | Both are the only added tests that pass against the pre-change source — correct, since they pin unmoved behaviour |

No vacuous test found among those I mutated. One **coverage hole** proved by mutation: changing
`audit.py:2931` from `round(total_seconds, 1)` to `round(total_seconds, 3)` — the candidate fix for
defect §1 — leaves the whole audit suite green (`640 passed`). Nothing pins the published
denominator's precision, and `test_share_is_a_share_of_the_published_denominator`
(`test_audit_check_global_log_analysis_cost_rollup.py:71`) uses `30.0 s` / `10.0 s`, which round
cleanly at one decimal and so cannot see the regime the sibling sub-decisecond tests deliberately
introduced. Re-run independently on adversarial review: the same mutation still gives `640 passed`,
so the hole is current, not a stale reading.

A **second coverage hole**, found on adversarial review, and it explains why defect §4 is invisible
to the suite. `summarize_script_cost` has two wirings: `folded_global_logs`
(`analyze-logs.py:1500`) and `plan_script_execution_log` (`analyze-logs.py:1688`). Every test in
`TestScriptCostRollup` drives the **first**, through `analyze_folded_global_logs`, which is the
line-shape-gated reader. The second wiring — the one that runs `extract_script_durations` over
`read_log`'s unfiltered lines — is reached only through the end-to-end `run_script` fixtures, and
`extract_script_durations` has **no direct test in the module at all** (`grep extract_script_durations
test_analyze_logs.py` → no hits). The roll-up's ranking is pinned; the eligibility of its per-plan
input is pinned nowhere.

All mutations were applied to files whose original bytes I had first copied to
`$TMPDIR/verify-270-mutsweep/` (and, on adversarial review,
`$TMPDIR/adv-270-aggregate-cost-invisible-to-per-call-ceiling-mutsweep/`), restored from those
copies, and confirmed with `git status --porcelain` reporting nothing for either path.

## Report accuracy

Three false or stale claims, all numeric, all in the run report only.

1. **Test count.** The report states *"**37 test functions added**, 0 removed"*, with
   `test_analyze_logs.py` *"27 (78 → 105)"* and the new cross-plan module *"9 (new module)"* — and
   labels the figure *"Re-derived by AST at the moment of this claim"*. Re-derived by AST against the
   merged commit and its parent: **43 added**, `test_analyze_logs.py` **30 (78 → 108)**, the new
   module **12**, `test_audit.py` **1 (81 → 82)**. The 6-test delta is exactly the tests added by the
   post-report CodeRabbit fixes (#54, #55, #58, #59), so the table was derived before those commits
   and not re-derived afterwards, despite the claim.
2. **Pre-fix failure figures.** The report's re-derivation table states
   `test_analyze_logs.py -k "ScriptCostRollup or ContextPositionCost or PerCallCeilingPreserved"` →
   *"23 failed, 1 passed"*. Running the **current** selection against the pre-change source gives
   **29 failed, 1 passed** (30 tests). The report's `test_audit_checks.py (whole file) → 10 failed,
   445 passed` row is **UNVERIFIABLE**: that module no longer exists (decomposed by #1258); the
   surviving cost-roll-up module gives 11 failed, 1 passed against the pre-change source, consistent
   with the report's narrower claim that exactly the two ceiling pins pass.
3. **The "zero hits" sweep.** The report says *"A content sweep for `cumulative` / `total_duration` /
   `share_of_total` / `total_ms` across `plan-retrospective` returned **zero** hits."* Re-derived at
   `89edc99^`: zero hits when scoped to `…/plan-retrospective/scripts/`, but **one** hit across the
   skill directory (`SKILL.md:157`, "assign-cumulative"). The PR body scoped this to `scripts`; the
   report dropped the scope, which is the same defect its own finding #34 claims to have fixed.

Claims that held, checked individually: the 15-file / 7-`*.py` branch diff; `_GLOBAL_LOG_SLOW_SECONDS
== 30.0`; `slowest_scripts` ranking by largest single call; `CHECK_ERA["global-log-analysis"]` bumped
to `#1260`; the `dominant-cost-caller` row kind, its `informational` stamp, and
`genuine_signal_count` excluding it; `unattributable_calls` documented as a **bound**; the
`unmeasured` / `undefined` two-token discipline; `sub_precision_calls` published per script and per
corpus at both tiers; the currency statement carried into code and docs; and D3 leaving the
terminal-title surface untouched.

The `./pw verify` result (*"20309 passed, 14 skipped, 353.51 s"*) is **UNVERIFIABLE** here — running
the full build is outside this audit's remit; I ran the two affected test trees instead (750 passed).

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D1's numeric re-derivation and D3 blocked on corpus availability; D4(b) genuinely undischarged | **Open** | No corpus in this clone; no later epic plan closes it — `doc/plans/code-intelligence-substrate/` carries no successor naming the two hot paths |
| No end-to-end render coverage for the new fragment keys | **Open** | `test/plan-marshall/plan-retrospective/fixtures/archived-plan/work/fragment-log-analysis.toon` still ends at `top_error_tags[0]:` — no `script_cost_rollup`, no `context_position_cost`, no `global_log_signals`, no `build_time`, no `dispatch_boundaries`, no `findings` |
| The log's `%.2f` duration precision remains a ceiling on the instrument | **Open** | `marketplace/bundles/plan-marshall/skills/manage-logging/scripts/plan_logging.py:344` — `message = f'{notation} {subcommand} ({duration:.2f}s)'` |
| `CLAUDE.md` ↔ `cloud-plan-lane` contradiction on plugin-cache sync | **Closed** | `CLAUDE.md:91` now reads *"neither performs a sync nor records one as owed"*, aligned by `cd11d46` (#1267) |
| Pre-existing deliverable-id citations in the two touched test modules | **Open** | `test/plan-marshall/plan-retrospective/test_analyze_logs.py:762, 807, 843, 873, 1761, 1844, 1878` still carry `D0/D2/D3/D4` citations from earlier plans |

## Out-of-scope and collateral

All four exclusions were respected. Nothing in the merge commit reconciles token totals, closes the
late-phase metrics row, or touches the phase-window lifecycle. The fourth exclusion — *"treating the
wall-clock share as a token lever"* — is honoured positively rather than merely by omission: every
roll-up surface states its currency, and `context_position_cost` carries an explicit
partition-not-a-whole warning at both its code site (`analyze-logs.py:548-555`) and its doc site
(`references/log-analysis.md:142`).

Collateral beyond the plan's expected surface: `checks/architecture-lookup-ratio.md` (a sibling
check doc's discovery-volume pointer, report finding #49) and
`test_audit_thresholds_centralization.py` (one line, the new threshold). Both are declared in the
report's findings table, neither is undeclared.

## Method and coverage

**Checked.** Both implementation files read end to end for the changed regions
(`analyze-logs.py:88-137, 380-706, 1387-1501, 1660-1699`; `audit.py:380-395, 675-690, 2690-2960,
5995-6136`). All five touched test modules read or enumerated by AST. Four docs checked against the
code they describe. Five production mutations run and reverted from byte snapshots. Two pre-change
source swaps run and reverted the same way. Three first-party probes of the shipped functions
(cross-plan block emission on synthetic corpora; the two duration grammars on the same line bodies;
TOON key ordering via `serialize_toon`, which iterates `data.items()` and derives a uniform-array
header from first-occurrence key order, so emitted order **is** dict insertion order).

**Not checked.**

- The report's `./pw verify` figures — outside remit, marked UNVERIFIABLE above.
- Anything requiring the archived-plan corpus (`.plan/local/archived-plans/`, `.plan/local/plans/`) —
  absent from this clone, exactly as the run reported. D1's numeric half remains unverifiable by the
  same constraint that blocked the run.
- The report's `10 failed, 445 passed` cross-plan row — the module it names no longer exists.
- The plugin cache / generated `target/claude/` mirror of the edited bundle files — the lane does not
  own it and this clone does not carry it.

**Guards against false negatives.** Every grep that returned nothing was first confirmed to find
something where the pattern is known to exist: the pre-change `cumulative` sweep was re-run without
the `scripts/` scope and did return a hit, proving the filter rather than the corpus was what emptied
it.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | **Nothing false.** Every gap's `path:line` was opened and the claim checked against the current tree. Verified individually: G1 (`audit.py:2931` / `:2887` / `:2907-2909`), G2 (`global-log-analysis.md:94`, `:247` — both quotes verbatim, including the word *"published"*), G3 (`…cost_rollup.py:71` does use `30.0`/`10.0` and asserts `total_script_seconds == 40.0`, which rounds identically at 1 and 3 decimals), G4 (`analyze-logs.py:88` vs `:112`), G5 (`unattributable_calls += 1` sits inside `if dur_match:` at `:1477`), G6/G7 (`log-analysis.md:61` and `:50-61` vs the dict order at `analyze-logs.py:481-496` / `:498-508`; `toon_parser.py:552` and `:520-527`), G8/G9/G10 (`report-01.md:130`, `:115-116`, `:36` — all three quotes verbatim), G11 (fixture does end at `top_error_tags[0]:`), G12 (`report-01.md:23`; no successor plan in the epic names the two hot paths — the only other epic hit for `PreToolUse` is 280's F38, an unrelated preflight-gate discussion), G13 (`plan_logging.py:344`). | None needed. |
| A2 | False negatives | **One, and it is the most consequential finding of this review.** `extract_script_durations` (`analyze-logs.py:378-397`) has **no line-shape guard**, while its sibling `analyze_folded_global_logs` gates on `_GLOBAL_LOG_LINE_RE` at `:1455-1457`. `read_log` (`:335`) returns every non-empty line, and `format_log_entry` emits `exit_code`/`args`/`stdout`/`stderr` as indented continuation lines on every non-zero-exit call. Feeding one real writer-produced ERROR entry to both readers, the per-plan reader returned `[('pm:b:build', 1200.0), ('pm:t:t', 9990.0)]` — a 9.99 s call manufactured out of a failing script's stdout — where the global reader correctly returned only `1.20`. That list is the sole input to the per-plan `script_cost_rollup`, the deliverable this plan shipped. The audit read this function (its Method names `analyze-logs.py:380-706`) and did not catch it. | Added Correctness §4 and `gaps.md` **G14** (severity **high**, topic `measurement/metrics`), with the writer path, the reproduction, a concrete `path`, and an observable *Done when*. D2's verdict paragraph and the Test-adequacy section were rewritten to carry it. |
| A3 | Vacuous evidence | **Both claimed mutation sweeps re-run, both reproduce.** (i) `audit.py:2931` `round(…,1)` → `round(…,3)` — the candidate G1 fix — still leaves the audit tree at **640 passed**, confirming nothing pins the published denominator. (ii) `analyze-logs.py:476` `-cumulative[n]` → `-maxima[n]` still gives **2 failed, 9 passed**, killing `test_ranks_many_fast_above_few_slow` and `test_ceiling_is_blind_to_the_script_the_rollup_ranks_first` — D4(a) is non-vacuous. Both files were byte-snapshotted to `$TMPDIR/adv-270-…-mutsweep/` and restored by copy (never `git checkout`/`restore`/`stash`); `git status --porcelain` reports nothing for either path and both md5sums match the originals. **A gap in the audit's own coverage claim:** the audit credits `TestScriptCostRollup` as covering the *per-plan* roll-up, but every one of those tests drives the `folded_global_logs` wiring; the `plan_script_execution_log` wiring is reached only end-to-end, and `extract_script_durations` has no direct test at all. | Test-adequacy row relabelled to name the wiring actually driven; second coverage hole added, explaining why §4 escaped the suite. |
| A4 | Counts and quotes | **Every number re-derived at the moment of checking; all reproduce.** AST diff of `89edc99` against `89edc99^`: **43** added — `test_analyze_logs.py` 78→108 (30), `…cost_rollup.py` 0→12, `test_audit.py` 81→82 (1), the other two touched modules 0 — matching the audit's correction of the report exactly. Two test trees together: **750 passed**. Audit tree alone under the G1 fix: **640 passed**. G1's two emitted blocks reproduce byte-for-byte, including `dominant-cost-caller,1x 0.040s 100.0% pm:a:a run,,informational` beside `total_script_seconds: 0.0`. G4's three-line divergence table reproduces value-for-value (`5000.0/1500.0/1500.0` vs `None/None/2.00`). Every quoted line checked against its attributed file: verbatim in all cases. | None needed. |
| A5 | Actionability | All thirteen pre-existing entries carry a concrete path, a concrete change and an observable *Done when*; none reads "review/consider/investigate". G2 is conditional on G1 but states both branches, and G12 names the instrument to use and what "stated first-party" means, so a later run that has read neither the plan nor this audit can execute them. | New G14 written to the same standard. |
| A6 | Severity and topic | **G1 was under-rated.** The medium band covers *"a false claim in shipped documentation"* — that is G2. G1 is the code half, and it trips two high-band triggers: *a measurement misreports* (the block publishes `total_script_seconds: 0.0` for a corpus carrying measured work, with no counter marking it unreliable — `sub_precision_call_count` is `0` because a `0.04 s` call is above the writer's floor) and *a documented contract is unimplemented* (`global-log-analysis.md:94` and `audit.py:2871-2873` both promise recomputability from the printed columns; it fails below ~1 s). Decisive on the precedent the audit itself cites: the PR reviewer rated the identical rounding-before-dividing defect **Major** (finding #54), the run accepted that rating and fixed the row, and the report calls it *"the most consequential of the run"* — rating the residue of that same defect medium is inconsistent with that. **G4, by contrast, is correctly medium and stays there:** its three line bodies are synthetic, and no current writer emits them (`plan_logging.py:344` always writes a terminal, well-formed `(N.NNs)` on the header line), so it is a latent asymmetry plus a doc mismatch rather than a defect today's corpus trips — the distinction G14 makes concrete. All other severities and all fourteen `Topic` values check out against the owning surface. | G1 medium → **high**, with the two-trigger rationale and the precedent argument written into the entry. G4 held at medium but given an explicit reachability qualifier so a later run does not over- or under-invest. G14 filed **high**. |
| A7 | Coverage | `plan.md` names D1, D2, D3 and D4(a)/(b)/(c); all six have their own verdict row and detail block. Out-of-scope compliance (all four exclusions), report accuracy, and the declared residue each have a section. No deliverable is silently unmentioned. | None needed. |
| A8 | Internal consistency | **One real break.** `gaps.md` **G6** and **G7** (schema-doc key-order drift) traced to nothing in `verification.md` — its Correctness review declared *"Three defects"* and the drift was not among them; only the Method section mentioned the `serialize_toon` mechanism, and only in passing. The opening summary also under-listed the findings, naming three of the six classes `gaps.md` carries. The overall verdict CONFIRMED WITH GAPS does follow from the rows. | Added Correctness §5 so G6/G7 trace, with a first-party emission of the shipped function's TOON showing both mismatches; count corrected to *"Five defects"*; opening summary rewritten to enumerate every class and map it to its `gaps.md` entry. |

**Residual doubt:** the sharpest remaining unknown is the *magnitude* of G14 on a real corpus — the
guard's absence is proved and the writer path is proved, but whether a production script log actually
contains a continuation line carrying both a notation and a parenthesised `(N.Ns)` body was not
measurable here, for the same reason D1's numeric half was not: this clone has no archived-plan
corpus. A further round with a corpus should measure that.

It should also sweep the *other* consumers of `read_log`'s unfiltered output for the same
missing-guard shape. A partial sweep here already found one confirmed instance, deliberately **not**
filed as a gap of this plan: `error_lines = [line for line in work if ' ERROR ' in line]`
(`analyze-logs.py:1517`) tests for a space-delimited `ERROR`, but `format_log_entry` writes the
bracketed form — a real header reads `[2026-08-19T07:47:17Z] [ERROR] [c340dc] …`, and `' ERROR '
in header` is `False` (verified first-party against the writer). `error_lines`, and therefore
`top_error_tags`, is empty for every real log — which is consistent with the archived-plan fixture
ending at `top_error_tags[0]:`. It is a pre-existing defect on a surface this plan did not touch, so
it belongs to whichever plan owns the work-log reader, not to this one; it is recorded here so a
later run knows it is *real and unfiled* rather than unexamined.

Finally, `summarize_context_position_cost` was re-read but not independently mutated here; the
audit's own mutation of the guard at `:635` was accepted on its evidence rather than re-run.

**Verdict on the audit:** SOUND AFTER CORRECTION — every claim it made was true and re-derived
first-party, but it under-rated its headline defect (G1: medium → high), missed a reachable
misreport on the same deliverable (G14), and left two of its own gap entries untraceable to any
finding in the verification document.
