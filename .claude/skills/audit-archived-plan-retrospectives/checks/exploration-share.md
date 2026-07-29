# Check: exploration-share (cross-plan)

Reports how much of each plan's tool-call spend went to **exploration** —
locating and inspecting existing state — rather than to producing or mutating it.
It is the measured answer to the question `architecture-lookup-ratio` can only
prompt: that check counts calls to the structured-navigation *lever*, while this
one measures the navigation *cost* itself, whichever tool paid it. This is a
cross-plan check: it emits one aggregate block (per-plan rows + corpus aggregates
+ derived thresholds) rather than one row per plan in isolation. The
deterministic computation lives in `scripts/audit.py`
(`cross_exploration_share` / `emit_exploration_share_block`); this sub-document
is the interpretation guide.

## Inputs the check reads

Per plan, the script reads the ten per-phase exploration counters from
`work/metrics.toon` and sums them across the plan's phases. No other input is
consulted.

| Input | Field(s) read | Used for |
|-------|---------------|----------|
| `work/metrics.toon` | per-phase `{exploration,work,execute,orchestration,unclassified}_tool_calls` | turn share, unclassified-tool detection |
| `work/metrics.toon` | per-phase `{exploration,work,execute,orchestration,unclassified}_result_bytes` | payload-byte share |

The counters are written by `manage-metrics enrich` from the transcript engine's
tool-call walk: every observed `tool_use` item is classified by its tool name
into one of five buckets, and both the call itself and the UTF-8 byte length of
its `tool_result` payload are accumulated into the phase window the call's
timestamp falls in. See `manage-metrics/standards/data-format.md` § Per-Phase
Fields for the field definitions and § "Exploration-share counters (absent is not
zero)" for the persistence rule.

## Absent is not zero — the corpus-exclusion rule

**A plan whose counters are absent is EXCLUDED from the corpus. It is never
counted as zero exploration.** Two plan classes carry no counters:

- a plan archived **before** the counters existed, and
- a plan run on a target that **declines** the transcript primitive (OpenCode
  exposes no transcript, so it emits no bucket at all).

Neither measured anything, and admitting either at zero would enter it as a
*maximally efficient* plan — inventing the strongest possible signal out of the
absence of any measurement. The script therefore treats a plan with no present
counter as out-of-corpus and reports it under `plans_excluded_no_counters` /
`excluded_plan_ids`, so the exclusion is visible rather than silent. A
**measured** zero is different and IS in the corpus: the walk ran and found no
calls in that bucket, which is a real observation.

This is the check-side half of the same rule the producer enforces at
persistence and render time (an absent counter is never written as `0`; a
measured zero is written and rendered as `0`).

## Per-plan computation

The five buckets partition the observed tool-call population.
`exploration + work + execute` is the **productive denominator**;
`orchestration` and `unclassified` are read but excluded from it, so the
exclusion is auditable rather than invisible.

| Quantity | Definition |
|----------|------------|
| `phases` | Number of the plan's phases carrying at least one counter. |
| `exploration_calls` / `exploration_bytes` | Summed exploration counters across the plan's phases. |
| `denom_calls` / `denom_bytes` | Summed `exploration + work + execute` counters (the productive denominator). |
| `turn_share` | `exploration_calls / denom_calls`, or `n/a` when the denominator is 0. |
| `byte_share` | `exploration_bytes / denom_bytes`, or `n/a` when the denominator is 0. |
| `unclassified` | Summed `unclassified_tool_calls` — tool names outside the classifier's population-derived domain. |

**Byte share is the headline; turn share is the companion.** Payload bytes
measure the volume of context consumed by looking things up — the quantity that
actually drives token spend. Turn share measures how many *decisions* were spent
looking things up. Neither alone separates the two failure modes, and the pair
does:

- **high turn share + low byte share** — many small probes: the groping-around
  signature (`exploration-share`'s `many_cheap_probes` flag).
- **low turn share + high byte share** — a few very large reads.

Excluding `orchestration` from the denominator keeps the metric from moving when
the workflow machinery changes rather than when exploration behaviour does;
excluding `unclassified` keeps a bucket of unknown composition out of a ratio.
Both are still emitted.

## Dynamic-threshold rationale: computed from the live corpus each run

Every cut-point is derived from the LIVE corpus on each run via the `median` /
`percentile` helpers — NONE is read from the `THRESHOLDS` table and NONE is
hard-coded. There is no defensible universal "too much exploration" fraction:
the honest question is whether a plan explored more than its peers did, and that
comparand must float with the corpus.

| Threshold | Derivation |
|-----------|-----------|
| `byte_share_p75` | 75th-percentile of per-plan payload-byte shares |
| `byte_share_median` | median of per-plan payload-byte shares |
| `turn_share_p75` | 75th-percentile of per-plan turn shares |
| `turn_share_median` | median of per-plan turn shares |
| `corpus_byte_share` | corpus exploration bytes / corpus denominator bytes |
| `corpus_turn_share` | corpus exploration calls / corpus denominator calls |

### Degenerate-corpus guard

Each flag is a corpus-relative **outlier** detector, so it fires only when the
relevant share distribution has a genuine high tail. In a near-uniform corpus the
percentile band collapses (`p75 == median == max`) and a naive `share >= p75`
test would catch EVERY plan — the "fire on everything" failure the dynamic
thresholds exist to avoid. Each side therefore carries its own spread guard
derived from the same live corpus:

- `byte_share_has_spread` — some plan's byte share exceeds the median
  (`max > median`), i.e. there is a real high tail.
- `turn_share_has_spread` — the same test on the turn-share distribution.

When the relevant tail is absent the flag is suppressed: a corpus where every
plan explores alike is not a corpus of outliers. A single-plan corpus is
degenerate by construction and flags nobody, which is the correct read — one
plan is not a distribution.

## Flags (dynamically derived)

Each flag annotates the plan's value AND the floating cut-point it was measured
against, so a flagged row is self-describing.

| Flag | Fires when | Reading |
|------|-----------|---------|
| `exploration_byte_heavy` | byte share ≥ `byte_share_p75` (guarded) | This plan spent an unusually large share of its productive context on looking things up. |
| `exploration_turn_heavy` | turn share ≥ `turn_share_p75` (guarded) | This plan spent an unusually large share of its productive *decisions* on looking things up. |
| `many_cheap_probes` | turn share ≥ `turn_share_p75` AND byte share < `byte_share_median` (guarded) | Many small lookups rather than few large ones — the groping-around signature. This is the reading `architecture-lookup-ratio` cannot see, because those probes may never have touched the architecture lever at all. |
| `unclassified_tools` | `unclassified_tool_calls > 0` | A tool name outside the classifier's population-derived domain was observed. The classifier fails OPEN, so the call was counted rather than dropped — but the bucket map needs extending against the now-observed name. |

`severity` is `genuine` when a row carries any flag, `informational` otherwise.

## Emitted columns

```
exclusion_rule: absent counters exclude a plan from the corpus (never counted as zero exploration); a measured zero stays in
plans_in_corpus: K
plans_excluded_no_counters: X
excluded_plan_ids: id;id;…
corpus_byte_share: <derived>
corpus_turn_share: <derived>
byte_share_p75: <derived>
byte_share_median: <derived>
turn_share_p75: <derived>
turn_share_median: <derived>
genuine_signal_count: G
rows[K]{plan_id,change_type,phases,exploration_calls,denom_calls,turn_share,exploration_bytes,denom_bytes,byte_share,unclassified,flags,severity}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename (rows sorted by byte share, desc). |
| `change_type` | Joined from `status.json::metadata`. |
| `phases` | Phases carrying at least one counter. |
| `exploration_calls` / `denom_calls` | Turn-share numerator and productive denominator. |
| `turn_share` | `exploration_calls / denom_calls`, or `n/a`. |
| `exploration_bytes` / `denom_bytes` | Byte-share numerator and productive denominator. |
| `byte_share` | `exploration_bytes / denom_bytes`, or `n/a`. The headline number. |
| `unclassified` | Unclassified tool calls (excluded from the denominator). |
| `flags` | `;`-joined corpus-relative flags (empty for an unremarkable plan). |
| `severity` | Uniform severity column: `genuine` when the row carries any flag, else `informational`. |

## How the orchestrator interprets the rows

EVERY emitted row is adjudicated with a stated verdict and cited evidence; a row
may be dismissed as informational/expected ONLY with a cited reason.

- **`exploration_byte_heavy` (genuine)** — this plan's context spend leaned
  toward lookup. It is a **prompt, not a verdict**: a deep-lane plan over an
  unfamiliar surface legitimately explores more than a recipe plan over three
  known files. Cross-read the plan's `planning_lane` / `scope_estimate` and its
  `architecture-lookup-ratio` row before concluding anything. High exploration
  with a HIGH information-lookup ratio is a plan that navigated *well* and simply
  had a lot to navigate.
- **`many_cheap_probes` (genuine)** — the signature worth acting on. Many small
  lookups whose payloads were individually cheap is the "lever bypassed, groping
  around" pattern: read this row together with the plan's
  `architecture-lookup-ratio` row, which supplies the complementary evidence of
  whether the structured-navigation verbs were used at all. Together they
  distinguish "navigated a lot, via the lever" from "probed a lot, past the
  lever".
- **`exploration_turn_heavy` without `exploration_byte_heavy`** — decisions went
  to lookup but context did not. Usually cheap and usually benign; note it and
  move on unless `many_cheap_probes` also fired.
- **`unclassified_tools` (genuine)** — a classifier-maintenance signal, not a
  plan defect. The named plan used a tool the bucket map does not know. Extend
  the map in the transcript engine against the now-OBSERVED name; do NOT extend
  it by anticipation, which reintroduces the hand-written-list shape the
  population-derived classifier exists to avoid.
- **`plans_excluded_no_counters` / `excluded_plan_ids`** — the corpus-exclusion
  read-out, and a floor annotation for the whole block. A corpus summary MUST NOT
  claim a corpus-wide exploration verdict while excluded plans are unmeasured;
  name them, as the `input-integrity` cross-check obligation requires for blind
  plans. When exclusions outnumber inclusions the honest verdict is **"not yet
  measurable"**, which is neither a pass nor a regression.
- **`corpus_byte_share` / `corpus_turn_share`** — informational corpus shape, and
  the number a later acceptance read compares against. A movement in either
  across successive audits is the process signal this check exists to surface
  over time; a single run's value is a baseline, not a finding.

## Critical rules

- The script is the single source of truth for every per-plan number, every
  corpus aggregate, and every derived threshold. Do not re-read `metrics.toon`
  or re-derive a share in chat.
- Every threshold is corpus-relative (`median` / `percentile` over the live
  corpus). There are NO hard-coded cut-points in this check. If a derivation must
  change, edit `scripts/audit.py` rather than substituting a fixed number in a
  reading.
- **Absent is not zero.** A plan carrying no counters is excluded from the corpus
  and named, never admitted at zero exploration. A measured zero is a real
  observation and stays in.
- `orchestration` and `unclassified` are emitted but excluded from the
  denominator. Do not fold either into a share.
- A high exploration share is not a defect by itself — only a prompt. Never file
  a lesson claiming a navigation-adoption gap without the corroborating
  `architecture-lookup-ratio` cross-read.
- This check is read-only; it never edits `.plan/` files.
