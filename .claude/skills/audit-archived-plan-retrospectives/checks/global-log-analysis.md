# Check: global-log-analysis (cross-plan)

Parses the global `.plan/local/logs/` corpus and surfaces operational signals
the per-plan checks cannot see — they read a single plan's artifacts, whereas
the global logs interleave every plan's (and every ad-hoc command's) script
calls, work-progress lines, and decision entries. This is a cross-plan check: it
emits one aggregate block over the whole log corpus rather than one row per plan.
Each flagged line is correlated to the archived-plan execution window it falls
inside. The deterministic computation lives in `scripts/audit.py`
(`cross_global_log_analysis` / `emit_global_log_block`); this sub-document is the
interpretation guide.

## Inputs the check reads

The script globs three log families under `.plan/local/logs/` and parses every
line that matches the shared log grammar:

| Log family | Glob | Carries |
|------------|------|---------|
| Script execution | `script-execution-*.log` | One line per executor script call, with a trailing `(<seconds>s)` duration. |
| Work progress | `work-*.log` | `[STATUS]` / `[ATTEMPT]` / `[DISPATCH]` / `[VERIFY]` work lines. |
| Decision | `decision-*.log` | Recorded decision / deviation entries. |

**Line grammar** (all three families share it):

```
[2026-05-31T22:00:01Z] [INFO] [3befe7] <rest>
```

— ISO-8601 UTC timestamp (trailing `Z`), a bracketed `[LEVEL]`, a bracketed short
hash, then the `<rest>` body. Script-execution bodies additionally carry a
`bundle:skill:script subcommand …` head and a trailing `(<seconds>s)` duration.

**Plan-window correlation**: the script reads each plan's `work/metrics.toon`
per-phase `start_time` / `end_time` lines (under both
`.plan/local/archived-plans/` and `.plan/local/plans/`) and derives the enclosing
window `(min start, max end)` per plan. A flagged line's timestamp is matched
against every window; the matching plan ids are its `attributed_plans`. A line
falling inside no window is attributed `ad-hoc` (a command run outside any
tracked plan execution).

## Computation

For each parsed line the script:

1. **Buckets by LEVEL** — increments a per-level counter (`INFO`, `WARNING`,
   `ERROR`, …) reported as `level_counts`.
2. **Aggregates script calls** — keys each script-execution line by
   `notation subcommand` (trailing args dropped) and accumulates a call count and
   summed duration per key.
3. **Flags error / elevated-level lines** — any line whose LEVEL is *elevated*
   (`WARNING`/`WARN`/`ERROR`/`CRITICAL`/`FATAL` — levels more severe than `INFO`),
   OR whose body matches a failure marker (`invalid choice`,
   `the following arguments are required`, `unrecognized arguments`, `Traceback`,
   `exit_code 1/2`, `status: error`, `Error`, `failed`). These are
   argparse-rejection and runtime-failure signatures even when the logging
   wrapper stamped `INFO`. Two recording-noise classes are deliberately NOT
   flagged: (a) `DEBUG`-level lines (diagnostic output *below* `INFO`, never a
   failure — flagging every non-INFO level previously swept thousands of DEBUG
   lines into the error count); and (b) a completed script-execution call whose
   subcommand is a known read-only **query** (`exists`/`read`/`get`/`list`/`find`/
   `search`/`resolve`) stamped at an elevated level with no failure marker — a benign
   non-zero-exit probe answering "not found", which is a normal query result, not a
   runtime failure. The exclusion is restricted to that query allowlist: a
   NON-query command (e.g. `run`) at an elevated level with no marker is NOT treated
   as benign and stays flagged, so a genuine failure from a non-probe command is
   never silently dropped. A genuine failure also always carries a failure marker,
   so it is still flagged at any level regardless of subcommand.
4. **Flags slow calls** — a script call whose duration is `>= slow_call_seconds`
   (but below the impossible ceiling).
5. **Flags impossible / hang durations (call-class-aware, #849)** — a single
   script call recorded at/over its class ceiling. The ceiling is **call-class
   aware**: a *deterministic per-plan-op* call keeps the flat
   `_IMPOSSIBLE_DURATION_SECONDS = 600s` bound (not a real wall-clock cost — clock
   skew or a hung-then-killed call), but a *build / ci-wait / sonar-CE / merge-wait*
   class call is bounded by the **ratcheted ci-wait ceiling** instead. #849's
   adaptive ci-wait ratchet grows the ci-wait budget as observed durations rise,
   so a legitimately-long ratcheted ci-wait used to false-positive against the flat
   600s ceiling; it now lands in the *slow* band, not the *impossible* one. The
   ratcheted ceiling is read INLINE from `.plan/run-configuration.json`
   (`commands.{key}.timeout_seconds` and `build.queue.upper_limit_seconds`, taking
   the max, never below the 600s floor) — consistent with the skill's
   inline-reader rule (no `manage-*` dispatch for deterministic work), degrading to
   the flat ceiling when the config or the ratcheted values are absent. Reported
   separately from *slow* because for a deterministic call the **recording itself**
   is suspect, not merely the cost.
6. **Flags high-frequency callers** — a `notation subcommand` key called
   `>= high_frequency_calls` times across the whole corpus. This is a
   **frequency** instrument: it answers *"who is called most often?"*, ranks by
   count, and drops any key below the gate however much time that key owns.
7. **Ranks callers by time owned** (`cost_rollup`) — the **cost** complement to
   the two instruments above, and the only one that answers *"what dominates
   total time?"*. Ungated by call count and ranked by cumulative seconds, with
   each row's `share_pct` of the published `total_script_seconds`.
   ⛔ **Read it beside the slow-call ceiling, never instead of it.** A call at a
   fraction of a percent of `slow_call_seconds`, repeated a hundred thousand
   times, is invisible to that ceiling **by construction** — a key ranked first
   here while `slow_call_count` is `0` is exactly that dominant-but-fast class.
   Conversely a key the ceiling flags that ranks low here is a rare outlier
   rather than a cost centre.
   ⛔ **Currency: these are WALL-CLOCK seconds.** The log carries no per-call
   token measurement, so `share_pct` does **not** restate as a share of billed
   cost — a ranking here is an operator-**latency** finding. Roll-up rows are
   stamped `informational`, not `genuine`: some key is always the largest cost
   owner, so counting them would inflate `genuine_signal_count` on every run.
8. **Detects test-fixture leaks** — a line whose body names a synthetic test
   bundle / plan id (`fake-*-bundle`, `idem-bundle`, `raising-bundle`,
   `orphan-md-*`). These exist only inside the test suite's tmp fixtures; their
   presence in the **shared** corpus means a test run wrote to the real
   `.plan/local/logs/` instead of an isolated `PLAN_BASE_DIR`.

## Threshold

Thresholds come from the centralized `THRESHOLDS` table in `scripts/audit.py` —
no magic number is re-declared in the check body:

| Signal | Source | Default |
|--------|--------|---------|
| Slow call | `THRESHOLDS["slow_call_seconds"]` | `30.0` s |
| High-frequency caller | `THRESHOLDS["high_frequency_calls"]` | `50` calls |
| Cost roll-up depth | `THRESHOLDS["cost_rollup_top_n"]` | `10` keys |
| Impossible / hang duration (deterministic per-plan-op call) | module constant `_IMPOSSIBLE_DURATION_SECONDS` | `600.0` s |
| Impossible / hang duration (build / ci-wait class call, #849) | `_ratcheted_ci_wait_ceiling()` — inline read of `run-configuration.json`, `max(_IMPOSSIBLE_DURATION_SECONDS, ratcheted timeouts)` | ≥ `600.0` s |
| Build / ci-wait call classifier | `_BUILD_CI_WAIT_KEY_RE` over the `{notation} {subcommand}` key | any match |
| Fixture leak | `_FIXTURE_LEAK_RE` (no numeric threshold) | any match |

The emitted block echoes the active `slow_ceiling_seconds`,
`high_frequency_ceiling` and `cost_rollup_top_n` so the read-out is
self-describing. `distinct_timed_call_keys` — every key that carried a duration
— is published beside `cost_rollup_count` so a truncated roll-up tail is legible
rather than silent. It is deliberately **not** the `high-frequency-caller`
denominator: that view is derived from *all* notation-headed lines, timed or not,
and `untimed_call_keys` names the difference.

## Emitted columns

```
logs_present: true|false
plan_windows_derived: W
total_log_lines: N
total_script_seconds: S
level_counts: "ERROR=2;INFO=9001;WARNING=14"
error_count: E
slow_call_count: SC
impossible_count: IC
high_frequency_count: HC
cost_rollup_count: CC
distinct_timed_call_keys: DK
untimed_call_keys: UK
fixture_leak_count: FL
slow_ceiling_seconds: 30.0
high_frequency_ceiling: 50
cost_rollup_top_n: 10
genuine_signal_count: G
rows[G]{kind,detail,attributed_plans,severity}
```

| Column | Meaning |
|--------|---------|
| `kind` | The signal class: `error:{LEVEL}`, `slow-call`, `impossible-duration`, `high-frequency-caller`, `dominant-cost-caller`, or `fixture-leak`. |
| `detail` | The signal payload — truncated line body for errors/leaks, `{seconds}s {notation subcommand}` for slow/impossible calls, `{count}x {total}s {key}` for high-frequency callers, `{calls}x {seconds}s {share}% {key}` for dominant-cost-caller rows. |
| `attributed_plans` | `;`-joined plan ids whose execution window contains the line's timestamp, or `ad-hoc` when it falls outside every window (empty for high-frequency **and** dominant-cost-caller rows, which are corpus-wide aggregates rather than single lines). |
| `severity` | Uniform severity column. Every surfaced row is `genuine` — a row only appears when its flag fired — **except `dominant-cost-caller`, which is always `informational`** (see below). |

⛔ **`genuine_signal_count` is NOT the row count.** It counts only the `genuine`
rows, and the table additionally carries up to `cost_rollup_top_n`
`dominant-cost-caller` rows stamped `informational`. A reader comparing the two
numbers is reading the intended signal: the difference is the size of the cost
roll-up, not a discrepancy.

The reason those rows are informational is structural, not a severity judgement:
**some key is always the corpus's largest cost owner**, so a roll-up row fires
for every non-empty corpus. Counting them as genuine would report a "signal" on
every run and train the reader to dismiss the count — which is exactly when a
real signal goes unexamined. The summary counters above the table carry the rest
of the informational context (corpus size, level buckets).

## How the orchestrator interprets the rows

- **`fixture-leak`** — highest-priority signal. A synthetic fixture id in the
  shared corpus is a test-isolation defect (a test wrote to the real
  `.plan/local/logs/`). File a lesson via the three-gate policy keyed to the
  leaking fixture signature; the leak is environmental, so attribution names the
  plan window only as context, not as the culprit.
- **`error:{LEVEL}` / `impossible-duration`** — inspect the `detail` for the
  failure signature. An `invalid choice` / `the following arguments are required`
  / `unrecognized arguments` body is an argparse-rejection: file (or, on Gate-1
  dedup, extend) a **source-keyed** lesson naming the exact
  `{notation} {subcommand}` whose surface drifted — not the consuming plan in
  `attributed_plans` (mirrors the recurring-pattern detector's source-keyed
  rule in SKILL.md Step 4). An `impossible-duration` row is now already
  call-class-filtered by the script: a surviving row is EITHER a deterministic
  per-plan-op call over 600s (a genuine recording artifact) OR a build/ci-wait
  call that exceeded even the ratcheted ci-wait ceiling (a real hang past the
  adaptive budget) — do NOT re-dismiss it as "just a long CI wait", because the
  #849-aware ceiling already carved those out.
- **`slow-call`** — a script call over the slow ceiling. Cross-read with the
  caller's `attributed_plans` window; a one-off slow build is usually expected,
  but a *recurring* slow notation across multiple plan windows is a performance
  signal worth a lesson.
- **`high-frequency-caller`** — a notation called past the frequency ceiling.
  Usually a workflow-shape signal (a polling loop, a redundant re-resolve), not a
  defect on its own; pair it with the slow-call read-out before drawing a
  conclusion.
- **`dominant-cost-caller`** — the cumulative cost roll-up: the keys that own
  the most recorded wall-clock, ranked by seconds owned with each row's share of
  `total_script_seconds`. **Read it against `slow-call` and
  `high-frequency-caller`, because it answers a question neither can.** A key
  ranked at the top here while `slow_call_count` is `0` is a *dominant-but-fast*
  caller — cost accumulated below the per-call ceiling, invisible to it by
  construction rather than by oversight. A key here that does *not* appear under
  `high-frequency-caller` owns its share through few expensive calls rather than
  many cheap ones, and the two remedies differ (make the call cheaper vs. make
  fewer calls). A key the slow ceiling flags that ranks *low* here is a rare
  outlier, not a cost centre.
  ⛔ **Currency: these are WALL-CLOCK seconds.** The corpus carries no per-call
  token measurement, so `share_pct` does **not** restate as a share of billed
  cost — a ranking here is an operator-**latency** finding. Never quote it as a
  cost or token share.
  These rows are `informational` and are **exempt from the per-row adjudication
  rule below** — a ranking has no verdict to state. Adjudicate what the ranking
  *reveals* (a dominant-but-fast caller worth a lesson), not the ranking itself.
- **`level_counts` / `total_*`** — informational summary only; a healthy corpus
  is dominated by `INFO`. A non-trivial `ERROR` / `WARNING` bucket count that the
  rows do not already enumerate is itself a prompt to widen the scan.

Per the SKILL.md Step-3 contract, every emitted **`genuine`** row is adjudicated
with a stated verdict and cited evidence; such a row may be dismissed as
informational/expected ONLY with a cited reason. Rows the script already stamps
`informational` — the `dominant-cost-caller` roll-up — carry no per-row verdict
obligation, because they are a ranking rather than a flag; the obligation is to
read them, and to raise what they reveal.

## Critical rules

- The script is the single source of truth for the parsed corpus, the
  aggregation keys, and every threshold. Do not re-grep the logs or re-derive a
  signal in chat.
- Thresholds live in the `THRESHOLDS` table (`slow_call_seconds`,
  `high_frequency_calls`, `cost_rollup_top_n`); the flat impossible-duration ceiling, the build/ci-wait
  classifier (`_BUILD_CI_WAIT_KEY_RE`), the ratcheted-ceiling reader
  (`_ratcheted_ci_wait_ceiling`), and the fixture-leak signatures are module-level
  constants/helpers. If a threshold or the call-class boundary changes, edit
  `scripts/audit.py` rather than substituting a different reading.
- Attribution is best-effort: a plan whose `metrics.toon` carries no parseable
  per-phase window contributes no window, so a line that should attribute to it
  shows `ad-hoc`. Treat `ad-hoc` as "outside every derivable window", not "proven
  to be a manual command".
- This check is read-only; it never edits `.plan/` files.
