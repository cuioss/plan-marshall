# Metrics Data Format

Storage format specifications for plan metrics collection and reporting.

## Storage Files

| File | Format | Purpose |
|------|--------|---------|
| `work/metrics.toon` | TOON key-value | Intermediate timing and token data per phase |
| `work/metrics-accumulator-{phase}.toon` | TOON key-value | Per-phase running totals of subagent `<usage>` data, written by `accumulate-agent-usage` and read as fallback by `end-phase` / `phase-boundary` |
| `metrics.md` | Markdown | Human-readable report with tables |

All files live in `.plan/plans/{plan_id}/`. Accumulator files are created lazily — only phases that dispatch agents (and call `accumulate-agent-usage`) produce one.

## Token-Field Population Lattice

Every token- and usage-bearing field `manage-metrics.py` writes measures exactly ONE population — with a single, explicitly-labelled exception. A figure computed over population A and rendered under a label implying population B is the defect this lattice exists to prevent, so every field below names the population it measures, the method that measured it, and whether `generate` renders it. A consumer that aggregates two fields MUST check that their populations agree first; fields of different populations are not additively comparable.

**The exception is `total_tokens`, and it is a labelled one.** On a phase that dispatched nothing, `cmd_enrich` folds the inline main-context sum into `total_tokens` (see § Inline Main-Context Attribution) — a deliberate fold that keeps the phase countable rather than a silent substitution. Because the field's population therefore varies per row, its lattice entry names the `population-discriminated` class below, every such row carries `total_tokens_population` (`dispatched` / `inline` / `mixed`), and every render site prints that label. **A consumer MUST read `total_tokens_population` rather than assume the field name states a population**: `total_tokens` names a total, not a measured population.

`total_tokens_population` is itself bookkeeping, not a measurement, so it takes no lattice row of its own — it is specified in the Per-Phase Fields table below. The lattice enumerates fields that MEASURE something; a discriminator that names a measurement's population is not one of them.

**Populations:**

| Population | Meaning |
|------------|---------|
| `dispatched-subagent` | Work performed by dispatched `execution-context` leaves, measured from their `<usage>` envelopes — forwarded flags, the per-phase accumulator, or the `enrich` transcript walk. |
| `main-context-window` | Context the orchestrator's own turns loaded and produced, measured from raw `message.usage` dicts in the parent transcript and in the subagent transcripts attributed to the same phase window. |
| `per-dispatch` | One dispatch's own totals at its termination, recorded one row per dispatch. Never aggregated into a phase figure unless a named field says it is. |
| `derived-cost` | A weighted cost figure derived from another population's fields — a billing measure, not a work measure. |
| `population-discriminated` | The field's population **varies per row**, and the row carries an explicit discriminator naming which one applies. Exactly one field is in this class — `total_tokens`, discriminated by `total_tokens_population` (`dispatched` / `inline` / `mixed`). A consumer MUST read the discriminator; it may not infer a population from the field's name. |

The lattice has two directions and **both halves are first-class**. A field that is recorded but never rendered is not a footnote: it is a measure the report declines to show, which is exactly how a larger competing figure stays invisible while a smaller one is presented as the total. Direction 2 is therefore evidence in its own right, not an appendix to Direction 1.

### Direction 1 — recorded AND rendered

| Field | Producer | Population | Measurement method | Rendered as |
|-------|----------|------------|--------------------|-------------|
| `total_tokens` | `_close_phase_accumulating` (`end-phase` / `phase-boundary`); backfilled by `_reconcile_accumulator_into_phase`; folded by `cmd_enrich` on an inline-only phase | population-discriminated | Dispatched rows: forwarded `<usage>` total (per-close delta, ADDED) or the per-phase accumulator's cumulative value (ASSIGNED). Inline rows: the `cmd_enrich` fold of `input + output + cache_creation`. The row's `total_tokens_population` names which applies | Phase Breakdown `Tokens` cell and the `Total tokens` bullet — both print the row's population label |
| `tool_uses` | `_close_phase_accumulating`; backfilled by `_reconcile_accumulator_into_phase` | dispatched-subagent | Forwarded `<usage>` `tool_uses` or the accumulator's cumulative value | Phase Breakdown `Tool Uses` cell, and the `Tool uses` bullet |
| `dispatch_boundary_total` | `cmd_generate` via `_read_dispatch_boundary_totals` | dispatched-subagent | Sum of the `total_tokens` column across the phase's recorded dispatch-boundary rows. **Partial-capable** — the file may hold fewer rows than the phase had dispatches, so the sum is a floor unless `dispatch_boundary_rows_recorded` covers `subagent_samples` | `Dispatch-boundary total` bullet, which states the measure's coverage and whether it won; may also supply the `Tokens` cell under the reconciliation rule |
| `dispatch_boundary_rows_recorded` | `cmd_generate` via `_read_dispatch_boundary_totals` | per-dispatch | Count of data rows summed into `dispatch_boundary_total`. Persisted whenever the file held rows, including when they sum to zero | The coverage clause of the `Dispatch-boundary total` bullet |
| `subagent_total_tokens` | `cmd_enrich` | dispatched-subagent | Sum of `<usage>` totals across the dispatches attributed to the phase window | Named in the reconciliation annotation when it wins the maximum, and supplies the `Tokens` cell when it does |
| `input_tokens` | `cmd_enrich` | main-context-window | `message.usage.input_tokens` summed across the phase window's parent turns and its attributed subagent transcripts | own bullet, nested under the `Main-context-window usage` heading that names the population |
| `output_tokens` | `cmd_enrich` | main-context-window | `message.usage.output_tokens`, same dual-source attribution | own bullet, under the same heading |
| `cache_read_input_tokens` | `cmd_enrich` | main-context-window | `message.usage.cache_read_input_tokens`, same dual-source attribution | own bullet, under the same heading |
| `cache_creation_input_tokens` | `cmd_enrich` | main-context-window | `message.usage.cache_creation_input_tokens`, same dual-source attribution | own bullet, under the same heading |
| `billing_weighted_total` | `cmd_enrich` | derived-cost | `input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)` over the four-field view | First-class `Billing (cost)` column with its own Total, plus the `Billing-weighted total` bullet. Aggregated into the `total_billing_weighted` return field — never into `total_tokens` |
| `cache_read_per_tool_use` | `cmd_generate` | derived-cost | `round(cache_read_input_tokens / tool_uses)` — the resident-context factor of the read-cost decomposition. Numerator and denominator are different populations (main-context-window ÷ dispatched-subagent); the ratio is disclosed as a cost-decomposition factor, not a single-population measure | `Read-cost decomposition` bullet, which states the identity `cache_read ≈ resident_context_per_call × turns` and names the population span. Never aggregated into any Total |
| `inline_main_context_tokens` | `cmd_enrich` (the figure, on BOTH the inline-only and the mixed branch); `cmd_generate` (the measured-`0` / `unmeasured` completion) | main-context-window | `input + output + cache_creation`, EXCLUDING `cache_read`, so the figure matches the dispatched-`<usage>` total definition | `Inline main-context tokens` bullet, whose text states whether the figure stands alongside a dispatched total (mixed) or IS the folded `total_tokens` (inline). A `0` or `unmeasured` value renders no bullet |
| `exploration_tool_calls` | `cmd_enrich` | main-context-window | Count of phase-window tool calls classified *exploration* | own bullet, on a presence test |
| `work_tool_calls` | `cmd_enrich` | main-context-window | Count classified *work* | own bullet, on a presence test |
| `execute_tool_calls` | `cmd_enrich` | main-context-window | Count classified *execute* | own bullet, on a presence test |
| `orchestration_tool_calls` | `cmd_enrich` | main-context-window | Count classified *orchestration*; excluded from the share denominator | own bullet, on a presence test |
| `unclassified_tool_calls` | `cmd_enrich` | main-context-window | Count of tool names outside the classifier's domain; excluded from the denominator | own bullet, on a presence test |
| `exploration_result_bytes` | `cmd_enrich` | main-context-window | UTF-8 byte length of the `tool_result` payloads returned by *exploration* calls | own bullet, on a presence test |
| `work_result_bytes` | `cmd_enrich` | main-context-window | Same measure for *work* calls | own bullet, on a presence test |
| `execute_result_bytes` | `cmd_enrich` | main-context-window | Same measure for *execute* calls | own bullet, on a presence test |
| `orchestration_result_bytes` | `cmd_enrich` | main-context-window | Same measure for *orchestration* calls; excluded from the denominator | own bullet, on a presence test |
| `unclassified_result_bytes` | `cmd_enrich` | main-context-window | Same measure for *unclassified* calls; excluded from the denominator | own bullet, on a presence test |

### Direction 2 — recorded but NEVER rendered

| Field | Producer | Population | Measurement method | Why it never surfaces |
|-------|----------|------------|--------------------|-----------------------|
| `subagent_tool_uses` | `cmd_enrich` | dispatched-subagent | Sum of `<usage>` `tool_uses` across the same attributed dispatches | No render site |
| `subagent_duration_ms` | `cmd_enrich` | dispatched-subagent | Sum of `<usage>` `duration_ms` across the same attributed dispatches | Consumed only inside `_worked_ms`'s `max()`; never rendered as a figure of its own |
| `subagent_samples` | `cmd_enrich` | dispatched-subagent | Count of dispatch returns attributed to the phase window | No render site — yet it is the only signal that separates a measured dispatched zero from a phase that was never walked |
| `retrospective_tokens` | `_close_phase_accumulating` | dispatched-subagent | `--retrospective-tokens` flag (per-close delta, ADDED) or the accumulator's cumulative value (ASSIGNED) | No render site; read only by the audit checks that exclude deliberate-analysis spend |
| `samples` (accumulator file) | `cmd_accumulate_agent_usage` | per-dispatch | Count of `accumulate-agent-usage` calls folded into the phase accumulator | Accumulator-local; `generate` reads the accumulator's totals but never its call count |
| `tool_uses` (dispatch-boundary column 4) | `cmd_record_dispatch_boundary` | per-dispatch | `--tool-uses` at dispatch termination, default `0` | Recorded per dispatch, never aggregated into a phase figure and never rendered |
| `duration_ms` (dispatch-boundary column 5) | `cmd_record_dispatch_boundary` | per-dispatch | `--duration-ms` at dispatch termination, default `0` | Recorded per dispatch, never aggregated and never rendered |
| `input_tokens` (dispatch-boundary column 6) | `cmd_record_dispatch_boundary` | per-dispatch | `--input-tokens` (`message.usage`) at dispatch termination. An omitted flag writes the `unmeasured` token, NOT `0` | Recorded per dispatch, never aggregated and never rendered |
| `output_tokens` (dispatch-boundary column 7) | `cmd_record_dispatch_boundary` | per-dispatch | `--output-tokens` at dispatch termination. An omitted flag writes the `unmeasured` token, NOT `0` | Recorded per dispatch, never aggregated and never rendered |
| `cache_read_input_tokens` (dispatch-boundary column 8) | `cmd_record_dispatch_boundary` | per-dispatch | `--cache-read-input-tokens` at dispatch termination. An omitted flag writes the `unmeasured` token, NOT `0` | Recorded per dispatch, never aggregated and never rendered |
| `cache_creation_input_tokens` (dispatch-boundary column 9) | `cmd_record_dispatch_boundary` | per-dispatch | `--cache-creation-input-tokens` at dispatch termination. An omitted flag writes the `unmeasured` token, NOT `0` | Recorded per dispatch, never aggregated and never rendered |
| `rows_recorded` | `cmd_record_dispatch_boundary` return TOON | per-dispatch | Count of data rows in the boundaries file after the append | Returned to the caller only — never persisted. `generate` does not read it: it derives its own `dispatch_boundary_rows_recorded` from the file at render time |

Only column 3 of the dispatch-boundary row (`total_tokens`) escapes Direction 2: `_read_dispatch_boundary_totals` sums it into `dispatch_boundary_total`. Columns 1–2 (`timestamp`, `termination_cause`) carry no usage measurement and are outside the lattice.

## Intermediate Storage (metrics.toon)

The metrics.toon file stores raw phase timing and token data as flat key-value pairs:

```toon
phase.1-init.start: 2026-03-27T10:00:00Z
phase.1-init.end: 2026-03-27T10:03:00Z
phase.1-init.total_tokens: 25514
phase.1-init.total_tokens_population: inline
phase.1-init.inline_main_context_tokens: 25514
phase.1-init.duration_ms: 180000
phase.1-init.tool_uses: 12
phase.1-init.close_count: 1
phase.1-init.value_scope: single_close
phase.1-init.tokens_cell_source: total_tokens
phase.2-refine.start: 2026-03-27T10:03:15Z
phase.2-refine.end: 2026-03-27T10:08:45Z
phase.2-refine.total_tokens: 42000
phase.2-refine.total_tokens_population: dispatched
phase.2-refine.inline_main_context_tokens: 0
phase.2-refine.input_tokens: 38000
phase.2-refine.output_tokens: 4000
phase.2-refine.cache_read_input_tokens: 210000
phase.2-refine.cache_creation_input_tokens: 12000
phase.2-refine.billing_weighted_total: 78000
phase.2-refine.tokens_cell_source: total_tokens
session_message_count: 127
totals_tokens: 67514
totals_tokens_population_count: 2
totals_population_denominator: 6
totals_tokens_spans_populations: true
```

### Key Naming Convention

> **Phase naming**: TOON keys use the `phase.{N}-{name}.{field}` prefix form (e.g., `phase.1-init.start`). The canonical phase name is `1-init` — see [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the standard phase list.

- `phase.{phase_name}.{field}` — per-phase timing/token data, including the four-field usage view (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) and the derived `billing_weighted_total` written by `enrich`
- `session_message_count` — plan-level count of transcript messages carrying usage data, written by `enrich`

### Per-Phase Fields

| Field | Type | Source |
|-------|------|--------|
| `start` | ISO 8601 timestamp | `start-phase` command |
| `end` | ISO 8601 timestamp | `end-phase` command |
| `close_count` | int | `end-phase` / `phase-boundary` — incremented on every close of this phase (absent read as `0`). `close_count > 1` is the **authoritative, inference-free re-entry marker**: the row was closed more than once (a finalize loop-back), so its token/tool and `duration_seconds` figures are sums across every close. `generate` reads it for the top-level `re_entered_phases` list and the `> Re-entered phases: …` marker |
| `value_scope` | `single_close` \| `mixed_cumulative_and_last_close` | Written by `end-phase` / `phase-boundary` on **every** close, as the last write of the close. Names what the close did to the row's OWN fields: `single_close` (this is the first close — every value covers exactly one close, so the cumulative-vs-last-close split is vacuous), `mixed_cumulative_and_last_close` (the row was closed more than once — some values are sums across every close and some are scoped to the latest close, named individually by `cumulative_fields` / `last_close_fields`). **Absent reads as `single_close`** — the best available default, not a guarantee: a row written before this discriminator existed whose `close_count` is 1 reaches the same absent state as a pre-stamping re-entered row, and the default under-reports the second. A consumer that has `close_count` on the row SHOULD prefer it — `close_count > 1` is the authoritative re-entry marker, and `value_scope` says what that re-entry did to the individual fields. Follows the `total_tokens_population` precedent: a row-level discriminator with a documented absent-reads-as default |
| `cumulative_fields` | list (comma-joined) | Written by `end-phase` / `phase-boundary` **only** on a `close_count > 1` row. Names, from the fields the row actually carries, those whose value is the SUM across every close. Absent on a `single_close` row, where the distinction is vacuous. This is what makes the split readable off the row itself — a script consumer never has to consult this document to interpret a re-entered row |
| `last_close_fields` | list (comma-joined) | Written alongside `cumulative_fields`, under the same condition. Names the fields scoped to the LATEST close alone — assigned unconditionally on every close, never summed (`start_time`, `end_time`) |
| `total_tokens` | int | Task agent `<usage>` tag (forwarded explicitly OR read from accumulator file). **Accumulating**: an explicitly-forwarded flag value is a per-close delta ADDED to the row; an accumulator-sourced value is already cumulative and is ASSIGNED. On an inline-only phase the field is instead filled by `enrich`'s main-context fold — read `total_tokens_population` before treating the value as a dispatched measurement |
| `total_tokens_population` | `dispatched` \| `inline` \| `mixed` | Written by `enrich` on every phase row it touches. Names which population this row's `total_tokens` measures: `dispatched` (dispatched-subagent `<usage>` / accumulator, no inline spend attributed), `inline` (the phase dispatched nothing and `total_tokens` carries the main-context fold), `mixed` (dispatched `total_tokens` PLUS a separately-recorded `inline_main_context_tokens` the field does not include). **Absent reads as `dispatched`** — the best available default, not a guarantee: the absent set is wider than the never-enriched set. A row `enrich` never touched can only have been filled from dispatched sources (exact); a row enriched by a PRE-labelling `enrich` already received the inline fold yet carries no discriminator, so it renders unmarked and its Total takes no `spans populations` marker (under-reported). The second case is unrecoverable without re-enriching a usually-gone transcript and is accepted rather than guessed at — go-forward rows are always stamped. See Inline Main-Context Attribution below |
| `duration_ms` | int | Task agent `<usage>` tag (agent-reported, distinct from wall-clock) |
| `tool_uses` | int | Task agent `<usage>` tag |
| `retrospective_tokens` | int | Tokens attributable to the plan-retrospective dispatch within the phase window (forwarded explicitly via `--retrospective-tokens` OR read from the accumulator when the finalize retrospective step seeded it). Default-absent — present only on `[6-finalize]` rows of plans where the opt-in retrospective step ran |
| `subagent_total_tokens` | int | `enrich` post-hoc transcript walk (sum of `<usage>` totals for Task calls inside this phase's window) |
| `subagent_tool_uses` | int | `enrich` post-hoc transcript walk |
| `subagent_duration_ms` | int | `enrich` post-hoc transcript walk |
| `subagent_samples` | int | `enrich` post-hoc transcript walk — count of attributed Task-agent calls |
| `input_tokens` | int | `enrich` four-field walk — sum of `message.usage.input_tokens` across the parent orchestrator turns AND every subagent transcript attributed to this phase |
| `output_tokens` | int | `enrich` four-field walk — sum of `message.usage.output_tokens` (same dual-source attribution) |
| `cache_read_input_tokens` | int | `enrich` four-field walk — sum of `message.usage.cache_read_input_tokens` (same dual-source attribution) |
| `cache_creation_input_tokens` | int | `enrich` four-field walk — sum of `message.usage.cache_creation_input_tokens` (same dual-source attribution) |
| `billing_weighted_total` | int | Derived by `enrich` from the four-field view: `input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`. A **derived-cost** measure over the main-context window — what the phase cost to buy, a different question from how much dispatched work was done. Never summed into `total_tokens` |
| `idle_duration_ms` | int | Derived by `generate` — the per-phase idle residual `max(0, wall_clock_ms - worked_ms)` |
| `cache_read_per_tool_use` | int | Derived by `generate` — `round(cache_read_input_tokens / tool_uses)`, the resident-context factor of the read-cost decomposition (see § Read-Cost Decomposition). Written ONLY when both operands are present and `tool_uses > 0`; absent otherwise, never a guessed `0`. A **derived-cost** ratio whose numerator and denominator are DIFFERENT populations (main-context-window cache_read over dispatched-subagent tool_uses) — read it as a cost-decomposition factor, never as a single-population measurement |
| `dispatch_boundary_total` | int | Derived by `generate` — the sum of the `total_tokens` column across the phase's `work/metrics-dispatch-boundaries-{phase}.toon` rows. Persisted as a DISTINCT field (it never overwrites `total_tokens`); present only when the boundary file exists and sums to a truthy value. See Dispatch-Boundary Reconciliation below |
| `dispatch_boundary_rows_recorded` | int | Derived by `generate` — the number of data rows summed into `dispatch_boundary_total`. Persisted whenever the boundary file held at least one parseable row, INCLUDING when those rows sum to zero. This is the boundary measure's **coverage** against `subagent_samples`: `<` is partial (a floor), `==` is exact agreement, `>` is an impossible over-coverage FAILURE (the two counts are cross-population). A partial OR over measure is ineligible for the reconciliation maximum |
| `inline_main_context_tokens` | int \| `unmeasured` | Derived by `enrich` — `input_tokens + output_tokens + cache_creation_input_tokens` (EXCLUDING `cache_read_input_tokens`) surfaced on ANY phase whose window carries a non-zero such sum, whether or not a dispatched `total_tokens` also exists. It is the inline measurement's own population-honest name, so the figure is never readable only through the dispatched-population `total_tokens` field. **Never absent**: `generate` completes the field on every phase row, because absence conflated "`enrich` measured no inline spend" with "`enrich` never visited this phase". The discriminator is the row's own `total_tokens_population` stamp, which `enrich` writes on every row it touches — a stamped row with no figure reads `0` (a MEASURED zero, including the cache_read-only window), an unstamped row reads `unmeasured`. `generate` re-derives the non-numeric value each run, so an `enrich` that later measures the phase is never shadowed by a stale marker. See Inline Main-Context Attribution below |
| `tokens_cell_source` | field name \| `unclosed_boundary_floor` \| `unclosed_boundary_over_covering` | Derived by `generate` — which measure fed this row's rendered `Tokens` cell: `total_tokens`, `dispatch_boundary_total`, `subagent_total_tokens`, or, for a phase with no `end_time` whose cell is its dispatch-boundary sum, `unclosed_boundary_floor` (coverage partial or undecidable — a genuine lower bound) or `unclosed_boundary_over_covering` (more recorded rows than sampled dispatches, so the figure may double-count and is not a floor). Absent when the cell renders `-`. Persists the provenance the reconciliation annotation states in prose, so a consumer reads it off the row instead of re-running the comparison. See Dispatch-Boundary Reconciliation below |
| `boundary_non_monotonic` | `true` token | Derived by `generate` — set on a phase whose `start_time` precedes the maximum `end_time` of earlier phases in canonical order (a finalize loop-back re-entry). Read-only annotation; the recorded `start_time` / `end_time` are never rewritten. See Boundary Monotonicity below |
| `exploration_tool_calls` | int | `enrich` tool-call walk — count of tool calls in this phase's window classified as *exploration* (locate or inspect existing state) |
| `work_tool_calls` | int | `enrich` tool-call walk — count classified as *work* (produce or mutate state) |
| `execute_tool_calls` | int | `enrich` tool-call walk — count classified as *execute* (shell invocation, whose intent the tool name alone does not carry) |
| `orchestration_tool_calls` | int | `enrich` tool-call walk — count classified as *orchestration* (control plane). Emitted but EXCLUDED from the exploration-share denominator |
| `unclassified_tool_calls` | int | `enrich` tool-call walk — count of tool names outside the classifier's population-derived domain. Non-zero means a new tool name was counted rather than dropped. Emitted but EXCLUDED from the denominator |
| `exploration_result_bytes` | int | `enrich` tool-call walk — UTF-8 byte length of the `tool_result` payloads returned by this phase's *exploration* calls |
| `work_result_bytes` | int | `enrich` tool-call walk — same measure for *work* calls |
| `execute_result_bytes` | int | `enrich` tool-call walk — same measure for *execute* calls |
| `orchestration_result_bytes` | int | `enrich` tool-call walk — same measure for *orchestration* calls. Excluded from the denominator |
| `unclassified_result_bytes` | int | `enrich` tool-call walk — same measure for *unclassified* calls. Excluded from the denominator |
| `exploration_index_answerable_bytes` | int | `enrich` tool-call walk — the part of `exploration_result_bytes` whose call targeted source or test code (a lookup an index could answer) |
| `exploration_doc_residency_bytes` | int | `enrich` tool-call walk — the part whose call targeted a workflow/standard document: skill and standard markdown bodies, `doc/**`, `*.adoc`, `CLAUDE.md` |
| `exploration_unattributed_bytes` | int | `enrich` tool-call walk — the part whose call exposes no recoverable target path (no path input, or a non-path-addressed tool such as `WebFetch`/`WebSearch`). Fails OPEN: an unrecognised shape is counted here, never guessed into a named sub-source |
| `cache_read_attributed_exploration` | int | `enrich` tool-call walk — the part of this phase's `cache_read_input_tokens` attributed to *exploration* payloads by turn-weighted residency |
| `cache_read_attributed_work` | int | `enrich` tool-call walk — same attribution for *work* payloads |
| `cache_read_attributed_execute` | int | `enrich` tool-call walk — same attribution for *execute* payloads |
| `cache_read_attributed_orchestration` | int | `enrich` tool-call walk — same attribution for *orchestration* payloads |
| `cache_read_attributed_unclassified` | int | `enrich` tool-call walk — same attribution for *unclassified* payloads |
| `cache_read_unattributed` | int | `enrich` tool-call walk — the residual: the part of `cache_read_input_tokens` the walk could not tie to an observed payload, plus every flooring remainder. Always emitted with the group, including at `0` |

#### Exploration-share counters (absent is not zero)

The ten `*_tool_calls` / `*_result_bytes` counters above are the inputs to the `exploration-share` audit check. Each observed tool call is classified by its tool name into one of five buckets, and both the call itself (turn share) and its result payload's byte length (payload-byte share) are accumulated into the phase window containing the call's timestamp. `exploration + work + execute` is the share denominator; `orchestration` and `unclassified` are emitted so the five buckets partition the observed population and the exclusion from the ratio stays auditable.

**A counter is written only when the runtime supplied it.** An absent counter is NEVER persisted as `0`, and a *measured* zero IS persisted as `0`. The two are different facts: absent means the target declined the transcript primitive and measured nothing (OpenCode exposes no transcript, so it emits no bucket at all); zero means the walk ran and found no calls in that bucket. Collapsing them would let an unmeasured plan enter the `exploration-share` corpus as a maximally-efficient one. For the same reason `generate` renders these bullets on a **presence** test rather than the truthiness test the four-field bullets use — see the render-guard divergence comment at the per-phase render in `manage-metrics.py`.

#### Exploration sub-sources (index-answerable vs doc-residency)

`exploration_result_bytes` is one number over two different activities. Reading a source or test file is a lookup an INDEX could answer — the bytes need not have entered context at all. Reading a workflow or standard document is context that has to be RESIDENT to be useful. Collapsing them hides the only part of exploration a lookup substrate could remove, so the three sub-source fields separate them by the call's target path, recovered from the `tool_use` item's `input`.

`exploration_unattributed_bytes` **fails open**, exactly as the `unclassified` tool bucket does: a call with no recoverable path — and a path shape outside the recognised populations — is COUNTED here and surfaced, never dropped and never guessed into a named sub-source. Widening the recognised populations therefore buys visibility; it can never correct a wrong named attribution, because none was made.

**Partition invariant**: `exploration_index_answerable_bytes + exploration_doc_residency_bytes + exploration_unattributed_bytes` equals `exploration_result_bytes` EXACTLY. The sub-sources re-cut bytes already counted in that field and add none, so they must never be summed alongside it.

They carry the `_bytes` suffix rather than `_result_bytes` deliberately: they are a byte-only sub-split of ONE bucket, **not** members of the `{bucket}_{measure}` exploration-counter family — `_EXPLORATION_COUNTER_FIELDS` stays a ten-member product over the five buckets, and a consumer deriving that family's key set must not pick these up. There is no matching `_tool_calls` sub-split. The same absent-is-not-zero persistence and presence-guarded render rules stated above apply.

#### Cache-read attribution (turn-weighted residency, exact reconciliation)

The `{bucket}_result_bytes` counters say what ENTERED context. They do not say what that entry COST, because a payload is billed again as `cache_read` on every later turn it stays resident — the reason a byte read once can dominate a phase's bill. The six `cache_read_attributed_{bucket}` / `cache_read_unattributed` fields answer the cost question by splitting the phase's recorded `cache_read_input_tokens` across the byte sources that put those bytes there.

**The attribution model** is turn-weighted residency. Each bucket's weight is its payload bytes multiplied by the number of the phase's billed turns those bytes remained in context; the recorded `cache_read` is then divided in proportion to the weights. A turn here is one usage-bearing transcript entry — one context read the phase was actually billed for — so a large payload arriving on a phase's last turn weighs far less than a smaller one that sat in context throughout. Payloads folded in from subagent transcripts are added to `{bucket}_result_bytes` after the parent walk and carry no residency weight of their own, so their share is disclosed in the residual rather than spread across buckets on a weight that was never observed.

**Exact reconciliation is the invariant**: `cache_read_attributed_exploration + …_work + …_execute + …_orchestration + …_unclassified + cache_read_unattributed` equals that phase's `cache_read_input_tokens` EXACTLY. Named parts are floored and `cache_read_unattributed` is the remainder, so every rounding crumb lands in the residual and never inflates a named share. When a phase was billed for a context read but no payload residency was observed, the whole figure stays in the residual.

`cache_read_unattributed` is the disclosure column and is emitted with the group unconditionally — a residual of `0` is the statement that the split was fully explained, and omitting it when it happens to be zero would make "fully explained" indistinguishable from "never computed". The absent-is-not-zero persistence and presence-guarded render rules stated above apply to this group verbatim.

#### The two "unattributed" populations are different quantities — name which

The word "unattributed" labels **two separately-computed quantities** on a phase row, and they are not the same number:

| Field | Quantity | Denominator | Residual of |
|-------|----------|-------------|-------------|
| `exploration_unattributed_bytes` | **bytes** | `exploration_result_bytes` | the exploration payload-byte split — bytes whose call exposed no recoverable target path (fails open) |
| `cache_read_unattributed` | **cache_read tokens** | `cache_read_input_tokens` | the turn-weighted cache-read residency split — tokens the walk could not tie to an observed payload |

They are computed by different walks, have **different denominators**, and their **shares** (each residual over its own denominator) differ materially — so a consumer that quotes "the unattributed share" without saying *which* is quoting an ambiguous figure. This module never emits or renders either as a bare `unattributed`: the persisted keys carry their quantity in the name (`…_bytes` vs `cache_read_…`), and every render names the quantity **and** prints its denominator inline (`{value} of {denominator} {denominator_field}`), so the byte residual and the cache_read residual can never be read as the same number. A consumer holding both MUST keep them separate; they are not additively comparable and neither substitutes for the other.

#### Why `cache_read` cannot be fully attributed outside the parent-observed window (D2)

The residual `cache_read_unattributed` is **large by construction** in any window where the phase's cache-read is not dominated by *parent-observed payload residency* — and this is a structural property of the attribution model, not a measurement gap to be closed. The mechanism is read from the producer, not inferred: the implementing symbol is **`_attribute_cache_read`** in `platform-runtime/scripts/claude_runtime.py`, fed by **`_fold_turn_residency`** in the same file. `_attribute_cache_read` splits only the parent-observed portion of the recorded cache-read across the byte buckets: subagent-folded cache-read (`subagent_cache_read`) is **subtracted before the split** and reaches the residual via the remainder (`attributable = max(0, cache_read_total - max(0, subagent_cache_read))`), and a window with **no observed residency weight** (`total_weight == 0` while the phase was still billed for a context read) leaves the *whole* figure in the residual. `_fold_turn_residency` accrues a bucket's weight only from `{bucket}_result_bytes` observed on the **parent** transcript's turns; payloads folded in from subagent transcripts carry no residency weight of their own.

The consequence: in a phase where the cache-read is billed against **subagent-dispatched** work (whose payloads have no parent residency) or against context the parent loaded but the walk saw no per-bucket residency for, the named `cache_read_attributed_{bucket}` shares are small and `cache_read_unattributed` is the majority — **and that residual is the honest disclosure, not a defect**. Attributing it to a named bucket would spread cache-read over buckets it was never observed to occupy, which is exactly the mislabel the residual exists to prevent. "It cannot be attributed there, and here is why" is the outcome: the split names what parent-observed residency can explain and discloses the rest. Improving the attribution — splitting the subagent-folded share by its own residency — would require the producer to fold subagent-transcript turns into the residency walk, which this emission contract does not do; whether that improvement is warranted needs a population of instrumented records to size the residual across phases, which is not reachable from a fresh clone (the archived records live under the git-ignored `.plan/` tree).

The four-field usage view (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) lives only in the raw `message.usage` dicts inside the transcripts — the single-figure `<usage>` return tag carries no input/output split and no cache fields. `enrich` accumulates these four fields per phase from BOTH the parent orchestrator turns and every discovered subagent transcript, then records `billing_weighted_total` per phase. These fields exist independently of `total_tokens`, which `enrich` leaves untouched.

#### Whole-transcript attribution and slug-gap robustness

Each subagent transcript is summed as a whole and attributed to the single phase window containing its spawn/first-message timestamp (latest-window-wins on a boundary tie). Transcripts are NOT split by slug boundaries — the whole transcript is attributed to the one phase that spawned it. Subagent discovery is anchored to the *resolved parent transcript location* (`{parent_transcript_path.parent}/{session_id}/subagents/agent-*.jsonl`) rather than re-derived from the current git root, so the worktree-vs-main-checkout cwd at `enrich` time no longer changes the answer. The direct-session-file fallback branch retains the legacy cwd-slug path.

#### Billing weights

| Field | Weight | Rationale |
|-------|--------|-----------|
| `input_tokens` | 1.0 | Baseline input cost |
| `output_tokens` | 1.0 | Counted at par in the weighted total |
| `cache_read_input_tokens` | 0.1 | A cached read is ~0.1× the cost of an input token (request-stated approximation) |
| `cache_creation_input_tokens` | 1.25 | A cache-creation write is ~1.25× the cost of an input token (request-stated approximation) |

`subagent_*` fields exist independently of the closed-phase `total_tokens` row. The closed-phase row is filled at `end-phase` time from explicit flags (preferred) or the accumulator file (fallback). The `subagent_*` fields are written by `enrich` as a post-hoc safety net so that even when the orchestrator never called `accumulate-agent-usage`, the transcript walk surfaces the missed totals.

### Read-Cost Decomposition

The read cost — a phase's `cache_read_input_tokens` — is one opaque number that hides **two levers**: the average resident context per API call, and the number of calls. A consumer that sees only the total cannot tell a phase that re-read a small context over many turns from one that re-read a large context over few. `generate` publishes the decomposition so both levers are readable:

```text
cache_read_input_tokens  ≈  cache_read_per_tool_use  ×  tool_uses
        (read cost)            (resident context/call)    (turns)
```

- **`cache_read_per_tool_use`** (the resident-context factor) is a **persisted** field, not a render-time computation — `generate` writes `round(cache_read_input_tokens / tool_uses)` onto the row before rendering, so a script reads it off `metrics.toon` directly. It is present only when both operands are present and `tool_uses > 0`.
- **`tool_uses`** (the turns factor) is the count already on the row; it is not duplicated under a second name.

**Population disclosure (D4).** The numerator (`cache_read_input_tokens`, main-context-window) and the denominator (`tool_uses`, dispatched-subagent) are **different populations** per the Token-Field Population Lattice, so `cache_read_per_tool_use` is a **derived-cost ratio spanning two populations**, disclosed as such at both its lattice entry and its render bullet. It is NOT a single-population measurement, and a consumer must not read it as one or sum it with anything.

#### The cache-creation inversion — not established here

A separate anomaly motivates reading this decomposition: one phase can spend the large majority of its billing weight on cache **creation** where the others spend a small minority, at a read/creation ratio an order of magnitude apart. The **mechanism** of the two is readable — `cache_creation_input_tokens` bills the *first write* of newly-loaded context into the cache (weight `1.25`), while `cache_read_input_tokens` bills each *re-read* of already-resident context (weight `0.1`), so a window that loads much fresh context but re-reads it little skews toward creation, and a long window that re-reads a stable context skews toward read. What is **not established** is that any specific phase's inversion is a real, reproducible effect: the originating observation is `n=1`, and the corpus needed to size the ratio across phases lives under the git-ignored `.plan/` tree and is **not reachable from a fresh clone**. Ruled out as a cause: the **record model** — the `_close_phase_accumulating` write path's currency verdicts are all `current` (§ Per-Field Write Semantics), so the creation/read figures are not a write-path artifact. The inversion is therefore recorded here as *mechanism-named, magnitude-not-established (corpus-blocked)* rather than assigned a settled cause.

### Dispatch-Boundary Reconciliation

`generate` reconciles each phase's recorded `total_tokens` against the durable
dispatch-boundaries sum (the `total_tokens` column summed across the phase's
`work/metrics-dispatch-boundaries-{phase}.toon` rows). `generate` reads the
dispatch-boundaries file as a reconciliation source; `plan-retrospective` also
reads it, as an audit trail.

**Three** fields measure the dispatched-subagent population by three independent
routes, and they routinely disagree:

| Measure | Route |
|---------|-------|
| `total_tokens` | Forwarded `<usage>` flags, or the per-phase accumulator |
| `dispatch_boundary_total` | Sum of the per-dispatch boundary rows |
| `subagent_total_tokens` | `enrich`'s post-hoc transcript walk |

They diverge when a leaf appears in one route and not another — a leaf whose
Step-8b `record-dispatch-boundary` fired but whose accumulator fold
(`accumulate-agent-usage`) was missed makes the accumulator *under-count*
relative to the boundary sum. Because all three count the **same leaves**, the
non-double-counting reconciliation is a maximum, never a sum:

```text
reported = max(every ELIGIBLE measure of the dispatched population)   # NOT a sum
```

Summing would double-count every leaf; `max()` recovers whichever route
under-counted.

### Symmetry, and the two eligibility rules

The rule is applied to **all three measures or to none** — never to a subset.
Comparing only `total_tokens` against `dispatch_boundary_total` let
`subagent_total_tokens` exceed the rendered figure with the report never saying
so. Two eligibility rules keep the comparison honest:

1. **A measure that cannot state its own coverage may not win.** Only
   `dispatch_boundary_total` can under-cover: its file may hold fewer rows than
   the phase had dispatches. It is marked **partial** when
   `dispatch_boundary_rows_recorded < subagent_samples`, and a partial measure is
   ineligible for the maximum — it is a floor, not a competing measurement.
   Coverage is **undecidable** (not partial) when the row carries no
   `subagent_samples`: an un-enriched row has no reference count, and treating
   undecidable as partial would refuse the maximum on every un-enriched plan and
   lose the accumulator-under-count recovery the reconciliation exists for.
   Coverage is a **failure** (`over`) when
   `dispatch_boundary_rows_recorded > subagent_samples`: the numerator exceeds the
   denominator, which is impossible for one population — the numerator
   (boundary rows, written by `record-dispatch-boundary`) and the denominator
   (`subagent_samples`, from `enrich`'s transcript walk) are then drawn from
   different populations (e.g. a resumed / re-entered phase appends boundary rows
   the single-window walk never re-counts). An over-covering measure is rendered
   as a loud `FAILURE` that names both producers — never `complete` — and is
   **ineligible** for the maximum, so an inflated / double-counted figure cannot
   feed the Total.
2. **A measure of a different population may not enter.** On a row whose
   `total_tokens_population` is `inline`, `total_tokens` carries a
   main-context-window measurement (see Inline Main-Context Attribution), so it
   is excluded from the dispatched-population maximum. Admitting it would be the
   exact cross-population mislabel the discriminator exists to prevent.

An exact tie resolves to the earliest measure in the declared order
(`total_tokens`, `dispatch_boundary_total`, `subagent_total_tokens`), so the
render is deterministic.

### Mechanics

The reconciliation is **generate-side / render-time**:

- The raw `total_tokens` field is left **byte-identical** on the row
  (explicit-wins — a value recorded by `end-phase` / `phase-boundary` is never
  overwritten).
- The boundary sum and its row count are persisted as the DISTINCT
  `dispatch_boundary_total` / `dispatch_boundary_rows_recorded` fields.
- The winning measure supplies the Phase Breakdown `Tokens` cell and feeds the
  Total. When the winner is NOT `total_tokens`, an annotation line under the
  table names the phase, **which measure won**, its value, and its **true
  relation** to the `total_tokens` it met: `> total_tokens N` (recovered an
  under-count), `= total_tokens N; measures agree` (the reconciliation identity —
  two independent producers agree exactly, the most valuable signal the surface
  emits), or `< total_tokens N` (a genuine anomaly). An exact agreement is never
  dressed up as a strict inequality.
- The `Dispatch-boundary total` bullet states the measure's coverage on every
  render (complete / partial / undecidable / **failure** over-coverage) and
  whether it won the maximum. It no longer asserts an unqualified "same-population
  max" — a partial measure has not earned that claim.
- When the boundary file is absent (no rows) the reconciliation is a clean
  no-op — no field is persisted and the render is unchanged.

### The declared dispatch-boundary population

`dispatch_boundary_rows_recorded` counts only the dispatch classes that call
`record-dispatch-boundary` — a **declared subset** of the dispatched population
`enrich` samples as `subagent_samples`, never the whole of it. The classes that
register no boundary are named in the source-derived
`DISPATCH_BOUNDARY_EXCLUDED_CLASSES` constant (derived from the call graph in
`ref-workflow-architecture/standards/call-graph.md`, not from any single run):
of the 9 dispatch classes, 3 register a boundary (phase-4-plan, phase-5-execute,
phase-6-finalize) and 6 do not (phase-2-refine, phase-3-outline, q-gate-validation,
verification-feedback, research, enrich-module). Whenever the report carries a
boundary numerator or a `subagent_samples` denominator, a declaration line names
those excluded classes so a `dispatch_boundary_rows_recorded < subagent_samples`
shortfall reads as a **declared** exclusion rather than as missing data — silent
exclusion is the defect the ledger exists to avoid.

The `#812` `end_time`-presence check (`any_phase_missing_end_time` /
`phases_missing_end_time`) is untouched by this reconciliation.

### Inline Main-Context Attribution

An **inline** step runs in the orchestrator's own (main) context rather than as a
dispatched subagent, so it produces no `<usage>` envelope and contributes nothing
to the per-phase accumulator — there is no per-step `<usage>` source. Its cost is
instead captured by `enrich`'s phase-window attribution, which sums the
parent-window `message.usage` four-field view into the phase row.

`enrich` writes that inline contribution to the `inline_main_context_tokens`
field on **every** phase whose window carries a non-zero
`input_tokens + output_tokens + cache_creation_input_tokens` sum — the
derivation below, not the full four-field `message.usage` view, is the trigger:

```text
inline_main_context_tokens = input_tokens + output_tokens + cache_creation_input_tokens
```

`cache_read_input_tokens` is **excluded** so the figure matches the
dispatched-`<usage>` total definition (which is fed via `end-phase --total-tokens`
and excludes cache reads); including it would over-count the inline contribution
by ~100× versus comparable dispatched rows.

#### Three signatures, one derivation, always labelled

The derivation is the same wherever it applies; what differs is whether the sum is
ALSO folded into `total_tokens`, and the row records which case applied. "Non-zero
inline sum" below means the `input + output + cache_creation` derivation above, NOT
the full four-field `message.usage` view — a window carrying only
`cache_read_input_tokens` takes the `dispatched` row:

| Signature | Condition | `total_tokens` | `inline_main_context_tokens` | `total_tokens_population` |
|-----------|-----------|----------------|------------------------------|---------------------------|
| **inline-only** | non-zero inline sum, **no** dispatched `total_tokens` (`1-init`, recipe-inline refine/outline) | the inline sum is folded in | the same sum, under its own name | `inline` |
| **mixed** | non-zero inline sum **and** a dispatched `total_tokens` (the `6-finalize` shape — dispatched steps and inline finalize steps both ran) | left byte-identical (explicit-wins) | the inline sum | `mixed` |
| **dispatched** | zero inline sum (no inline attribution) | left byte-identical | not written by `enrich`; `generate` then completes it as a measured `0` | `dispatched` |

The `inline_main_context_tokens` column above describes what **`enrich`** writes. `generate` completes the field on every phase row afterwards, so it is never absent from the record — see its Per-Phase Fields row for the `0`-versus-`unmeasured` rule.

**The inline-only fold is deliberate, not a silent substitution.** Folding the
inline sum into `total_tokens` is what keeps a zero-dispatch phase countable in
the Phase Breakdown — the report reads `n=6/6` rather than `n=5/6` — and what
keeps the downstream zero-token predicates (the audit's `incomplete_recording`
anomaly, the checkpoint budget verdict, the corpus percentile cut-points) off a
phase that really did cost something. The defect the labelling closes is not the
fold; it is a main-context figure being **read as** a dispatched one. Two records
prevent that, and they are written together, never apart:

- `inline_main_context_tokens` carries the figure under a name that states its
  own population, so the inline measurement is never readable ONLY through a
  dispatched-population field.
- `total_tokens_population` states which population `total_tokens` measures on
  this row, and **every render site prints it** — the `Tokens (dispatched unless
  marked)` column header declaring the default, an `(inline)` / `(mixed)` suffix
  on the Phase Breakdown `Tokens` cell, a `(spans populations)` marker on the
  `Total` cell when an `inline` row fed the sum, a population annotation under
  the table declaring the default and naming the marked phases, and a population
  qualifier on the Phase Details `Total tokens` bullet.

`total_tokens` is **explicit-wins** on both non-inline signatures: a value
recorded by a dispatched step's `<usage>` / the accumulator is never overwritten.
This attribution does not touch the `#812` `end_time`-presence check — a
timestamps-only inline close still carries its `end_time` marker.

**Consumer rule.** `inline_main_context_tokens` and a dispatched `total_tokens`
are measured by different methods over different populations and are **not
additively comparable** — never sum them into a phase figure. A consumer that
needs to know what `total_tokens` measures reads `total_tokens_population`; it
must not infer a population from the field's name, which states a total.

### Worked, Reported (Wall), and Idle Time

`generate` derives three time quantities per phase from already-persisted fields — no new pause/resume or user-gate API is introduced:

- **Worked** — effort actually spent on the phase: `worked_ms = max(agent_duration_ms, subagent_duration_ms)` (missing operands treated as `0`). The `max(...)` form is the non-double-counting definition: when a main-context (orchestrating) turn dispatches a subagent, the subagent's wall span overlaps with the orchestrator's own wall span — the orchestrator is awaiting the subagent return, not doing independent compute. Summing the two values would double-count that overlap and could produce `Worked > Reported (wall)`. Taking the maximum lets the longer attribution span subsume the shorter overlap so the per-phase **`Worked <= Reported (wall)`** invariant always holds.
- **Reported (wall)** — wall-clock span of the phase: `duration_seconds` (or, when absent, the span between `start_time` and `end_time` — a first-entry-only approximation, not an equivalent; see the Timestamp-vs-duration divergence subsection below). This is calendar time between the phase's recorded `start_time` and `end_time` (a conversation boundary, not a compute measure). Calendar time is the right basis for the Idle residual because it is the only quantity that captures user-wait gaps — a compute-time wall would collapse Idle to zero by construction.
- **Idle** — the residual user-wait/idle time, persisted into `metrics.toon` as `idle_duration_ms`: `idle = max(0, wall_clock - worked)`. Because Worked is now bounded above by the longer of the two attribution sources rather than their sum, `wall_clock - worked` is non-negative for every phase whose subagent dispatches stay within the phase window, so the `max(0, …)` clamp is a safety net rather than a routine path. Idle time is computed post-hoc via session-boundary inference — `generate` reads the persisted phase window and effort fields and writes `idle_duration_ms` back before rendering.

#### Worked <= Reported (wall) Invariant

For every phase row that carries both signals, `Worked <= Reported (wall)` MUST hold. The invariant is what makes the `Idle` column non-blank for subagent-dispatching phases — when Worked could exceed wall (the prior additive formula), Idle clamped to zero and the column rendered `-`, hiding all user-wait time. The `max(agent_duration_ms, subagent_duration_ms)` definition guarantees the invariant for any phase whose dispatched subagents return within the phase window; out-of-window attribution (a subagent that overruns the boundary) cannot occur because `enrich` only attributes `<usage>` totals to phases whose `start_time..end_time` window contains the subagent's timestamp.

**On a re-entered row the invariant survives because the wall span accumulates alongside the worked span**, and it is preserved by **clamping the summed worked value against the accumulated wall span** — not by any re-entry carve-out inside the clamp. The write site accumulates `agent_duration_ms` first and hands the clamp the SUM, which the clamp then bounds by the already-accumulated `duration_seconds`. The opposite ordering is unsound: clamping each per-close delta against the accumulated wall and then adding it to an already-clamped existing value can sum past that wall span and break the invariant. The clamp itself is therefore ordering-dependent but re-entry-agnostic — it needs no knowledge of `close_count`.

#### Timestamp-vs-duration divergence on a re-entered row

Accumulating the wall span makes `duration_seconds` and the `start_time`/`end_time` pair **stop being interchangeable definitions** on a `close_count > 1` row:

- `start_time` stays **re-entry-scoped** — the latest entry's start. Both writers assign it unconditionally, and accumulation does not change that.
- `duration_seconds` is the **cumulative sum of every entry's active span**.

Such a row therefore deliberately does **not** satisfy `duration_seconds == end_time − start_time`. The intended reading: the accumulated value is the phase's total **active** wall time, excluding the gap during which the plan was executing a different phase. Preserving the first entry's `start_time` instead was rejected — it would make `duration_seconds` a contiguous span that silently bills the other phase's time to this row, and it would inflate the clamp ceiling, weakening the very invariant the accumulation exists to protect.

The one consumer of the alternative definition is `_wall_clock_ms`'s timestamp-derived fallback, which is consequently a **first-entry-only approximation**, not an equivalent. It is unreachable for an accumulated row: it fires only when `duration_seconds` is absent, and a closed accumulated row always carries the field. The two definitions therefore never disagree about the same row in practice — but they are no longer interchangeable, and a consumer must not re-derive a re-entered phase's wall span from its timestamps.

**This divergence is stated ON the row, not only here.** The prose above is the rationale; the machine-readable form is the `value_scope` / `cumulative_fields` / `last_close_fields` triple in the Per-Phase Fields table, written by the same closing call that creates the divergence. A `close_count > 1` row therefore carries `value_scope: mixed_cumulative_and_last_close` together with the two field lists naming which side each of its values falls on — a script consumer reading such a row off disk gets the split without reading this document. Where the two could ever disagree, the row wins: the lists name only fields the row actually carries, and they are written after every other field write of the close.

### Boundary Monotonicity (Loop-Back Re-entry)

A finalize **loop-back** re-enters a prior phase (e.g. `5-execute`) and
re-records its work under that phase's key. Because a later phase (`6-finalize`)
was already closed, the re-entered phase's fresh `start_time` can end up
preceding a prior phase's already-recorded `end_time` — a **non-monotonic**
boundary. The overlapping window makes a wall span derived from those timestamps
(and therefore the `idle = max(0, wall - worked)` residual) meaningless.

**This detector is a timestamp-ordering signal, not the re-entry marker.** The
write-side loss it once stood in for is fixed — a repeat close now accumulates —
and `close_count` is the authoritative re-entry marker (see the Per-Phase Fields
table and the top-level `re_entered_phases` list). Critically, the two do not
agree on *which* phase to name: the detector flags the **later** phase, not the
re-entered one. On a `6-finalize → 5-execute` loop-back, `5-execute`'s fresh
`start_time` is later than every earlier phase's `end_time`, so the phase that
trips the check is `6-finalize` — whose original `start_time` now precedes
`5-execute`'s new `end_time` — even though `6-finalize` was never re-entered.
Read `boundary_monotonicity` as "these rows' timestamp windows overlap, so their
idle residual was guarded", and `re_entered_phases` / `close_count` as "this is
the row that was closed more than once".

`generate` carries a **render-time monotonicity detector**. Walking the canonical
`PHASE_NAMES` order it tracks the maximum `end_time` seen so far and flags any
phase whose `start_time` precedes it. On a violation it:

- persists the top-level `boundary_monotonicity` key (comma-joined list of the
  offending phase names, in canonical order) to `metrics.toon`, and returns the
  same list under `boundary_monotonicity` in the `generate` TOON;
- stamps the per-phase `boundary_non_monotonic: true` annotation on each
  offending phase row;
- **guards the idle residual** for each offending phase by zeroing its
  `idle_duration_ms` rather than deriving a corrupt figure from the overlapping
  span; and
- renders a `> Boundary monotonicity warning: …` marker line under the
  `## Phase Breakdown` heading.

The detector is **read-only** with respect to the boundary fields — it NEVER
rewrites `start_time` / `end_time`, and it does not touch the `#812`
`end_time`-presence check (a re-entered phase still carries its `end_time`, so
it never appears in `phases_missing_end_time`). It adds no new write path; it
reuses the existing `generate` read → annotate → write loop.

| Field | Type | Source |
|-------|------|--------|
| `boundary_monotonicity` | list (comma-joined in `metrics.toon`, simple TOON array in the `generate` return) | Derived by `generate` — canonical-order list of phases whose `start_time` precedes a prior phase's `end_time`; absent when every boundary is monotonic. Names the LATER phase, not the re-entered one |
| `re_entered_phases` | list (comma-joined in `metrics.toon`, simple TOON array in the `generate` return) | Derived by `generate` — canonical-order list of phases whose row carries `close_count > 1`; absent when no phase was re-entered. Rendered as the `> Re-entered phases: …` marker under `## Phase Breakdown`, with a per-phase **Closes** bullet under Phase Details. The authoritative re-entry signal — it names the phase that was actually closed more than once |

### The Persisted Aggregate

`generate` persists every figure its **Total** row renders, and then renders that row *from* the persisted values — so there is one producer of each figure, not a rendered number and a separate store the reader must reconcile.

Each column persists a **triple**: the value, the count of phase rows that fed it, and the shared denominator. A figure a renderer computes and does not persist is a number nobody can check, and the `(n=k/N)` qualifier is as load-bearing as the value it qualifies — a sum over 2 of 6 phases and a sum over 6 of 6 render identically without it.

| Field | Type | Source |
|-------|------|--------|
| `totals_worked_ms` / `totals_wall_ms` / `totals_idle_ms` | int (milliseconds) | Derived by `generate` — the `Worked` / `Reported (wall)` / `Idle` column sums. **Milliseconds, not rounded seconds**: the per-phase operands are held in ms, and a decisecond-rounded seconds total would put the store's precision below the render's (at 59.96 s the rounding flips `format_duration` from `60.0s` to `1m0s`) |
| `totals_tokens` | int | Derived by `generate` — the `Tokens` column sum, over whichever measure fed each cell (see `tokens_cell_source`) |
| `totals_tool_uses` | int | Derived by `generate` — the `Tool Uses` column sum |
| `totals_billing_weighted_total` | int | Derived by `generate` — the `Billing (cost)` column sum. A derived-cost measure, never folded into `totals_tokens` |
| `{total}_population_count` | int | Derived by `generate` — the number of phase rows that contributed to that column. A value without its count cannot state its own coverage, the same reason `dispatch_boundary_rows_recorded` rides beside `dispatch_boundary_total`. A `0` value beside a `0` count is legible as the empty sum it is, never as a measured zero |
| `totals_population_denominator` | int | Derived by `generate` — the canonical-six baseline every count is read against. A count without its denominator is not a population statement |
| `totals_tokens_spans_populations` | `true` / `false` token | Derived by `generate` — whether an `(inline)` row fed the token sum, i.e. whether the rendered Total carries `(spans populations)` |
| `dispatch_boundary_excluded_classes` | list (comma-joined) | Derived by `generate` from `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` — the dispatch classes that register no boundary. These are the key to every boundary coverage shortfall the report shows; as prose alone, a script got the coverage numbers without the declaration that makes them interpretable |
| `totals_sampled_at` | ISO 8601 timestamp | Written by `generate` — the moment the aggregate above was computed. Provenance for a reader; **not** the freshness signal, which is presence (below) |

**The row-derived aggregate is present iff the most recent write computed it.** Only `generate` computes the totals, while every other writer of this store — `start-phase`, `end-phase`, `phase-boundary` and `enrich` — rewrites the phase rows underneath them, so `write_metrics` **drops the `totals_*` family** for those writers. A reader that finds the keys knows the rows have not moved since they were summed; a reader that finds them absent knows to re-run `generate`. There is nothing to compare and no stale value to mistake for a current one.

Two scoping facts ride with that rule. `phase-boundary` regenerates unconditionally as its own last step, so although its `write_metrics` call drops the aggregate, the verb as a whole leaves it present and fresh — the invalidation is a property of the *write*, and only `start-phase`, `end-phase` and `enrich` leave it visible to a reader. And `dispatch_boundary_excluded_classes`, though it sits in the table above, is **not** dropped: it is derived from a module constant rather than from the rows, so it cannot go stale against them.

⛔ Do **not** substitute a timestamp comparison for this. `updated` and `totals_sampled_at` are both second-granularity, so a write landing in the same second as the `generate` it invalidates is indistinguishable from a fresh one — presence is exact where the comparison is not. The rule is the same present-iff-derivable-from-this-run invariant `cache_read_per_tool_use` follows.

**The round-trip rule.** Every figure the Total row renders is locatable in the store, with its population count. A figure present only in the render is a number nobody can check, and fails this contract. The rule governs the render's own output — it is emphatically **not** satisfied by parsing `metrics.md`: the markdown is the artifact, not the source.

### Enrichment Fields

`enrich` writes the four-field usage view and `billing_weighted_total` per phase (under the `phase.{phase_name}.{field}` prefix — see Per-Phase Fields above), plus one plan-level field:

| Field | Type | Source |
|-------|------|--------|
| `session_message_count` | int | Plan-level count of transcript messages that carried usage data (input/output/total) |

The denominator family (`deliverable_count`, `files_modified`, `tasks_completed`, their `_sampling_point` companions, and `denominators_sampled_at`) lives at the same plan-level tier and is written by `generate` — see § Denominators and Their Sampling Point.

The four-field usage view is no longer stored as plan-level `enriched.{field}` keys — it is attributed per phase by the transcript walks. See the Per-Phase Fields table for `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, and `billing_weighted_total`.

## Per-Field Write Semantics

A field's value is only interpretable once you know what the WRITE did to it — whether the incoming number was added to what was already there, replaced it, or was ignored. Two writers own every field a plan record accumulates across repeat entries: `manage-metrics`'s `_close_phase_accumulating` (shared by `end-phase` and `phase-boundary`) and `manage-status`'s `mark-step-done` (`status.metadata.phase_steps[phase][step]`). This section states that semantics per field, and records a **currency verdict** — whether the code as it stands already behaves as documented.

### Vocabulary

| Semantics | Meaning |
|-----------|---------|
| **add** | The incoming value is a per-close **delta** and is ADDED to the row's existing value (absent read as `0`) |
| **assign-cumulative** | The incoming value is **already cumulative** and is ASSIGNED unchanged. Adding it would double-count every re-close |
| **replace** | Assigned unconditionally on every write (last-write-wins). Earlier values are not retained on the row |
| **append** | The superseded value is folded into an ordered trail on the field rather than overwritten. The trail is append-only — extended, never rewritten — so every earlier value stays readable |
| **derive** | Computed at write time from other fields already on the row |
| **leave-untouched** | The source resolved to nothing, so the field is not written at all — never a `0` |

### `_close_phase_accumulating` (`end-phase` / `phase-boundary`)

| Field | Rule | Semantics | Currency verdict |
|-------|------|-----------|------------------|
| `end_time` | — | **replace** — stamped unconditionally, so it always names the latest close | **current** |
| `start_time` | — | **replace** — written by `start-phase` / the `phase-boundary` next-phase half; a re-entry re-stamps it, so it stays scoped to the latest entry | **current** |
| `close_count` | — | **add** (+1 on every close) | **current** — written at the write site, read by `generate` for `re_entered_phases` |
| `duration_seconds` | B | **add** — this close's ACTIVE span, anchored at `max(start_time, prior_end_time)`. Unparseable timestamps **leave-untouched** | **current** — the three close shapes (first close, loop-back re-entry, bare second close) are all correct under the one anchor rule |
| `agent_duration_ms` | C | **add** when flag-sourced / **assign-cumulative** when accumulator-sourced, then the RESULT is clamped to the accumulated wall span | **current** — accumulate-then-clamp is the sound ordering; clamping the delta first can sum past the wall span |
| `agent_duration_seconds` | C | **derive** from the clamped `agent_duration_ms` | **current** |
| `total_tokens` | A | **add** when flag-sourced / **assign-cumulative** when accumulator-sourced / **leave-untouched** when neither resolves | **current** |
| `tool_uses` | A | same as `total_tokens` | **current** |
| `retrospective_tokens` | A | same as `total_tokens`; additionally **leave-untouched** on a falsy resolved value | **current** |
| `value_scope` | — | **replace** — recomputed from `close_count` on every close | **current** |
| `cumulative_fields` / `last_close_fields` | — | **replace** on a `close_count > 1` row; removed on a `single_close` row | **current** |

**Is the originating impossible row still reproducible through this write path? No.** The record that motivated this section — a re-entered `5-execute` whose `duration_seconds` was a single close's span while its token total spanned two, so the row's own numbers could not describe any real execution — required a writer that REPLACED some accumulating fields while ADDING others. Rules A, B and C above are present and correct in current code, and `close_count` is written at the write site rather than inferred, so that row cannot be produced again by `end-phase` / `phase-boundary`. What was genuinely missing was not the arithmetic but the row's ability to SAY which of its values the arithmetic had accumulated — which is what `value_scope` / `cumulative_fields` / `last_close_fields` now supply. Sub-gap (c) of the originating deliverable is therefore the machine-readable marker only; the accumulate machinery is not re-implemented.

**The canonical `6-finalize` under-count is not a record-model defect.** A `6-finalize` row that never received its terminal close — and so appears in `phases_missing_end_time` — most often has a **finalize step-ordering** cause: `record-metrics` runs late in the finalize step list, so an interrupt, a loop-back, or a step that never reached it leaves the durable accumulator unfolded. That ordering lives outside this document's write boundary. A reader must not read the renamed `end_time`-presence verdict as evidence that the write path lost the figures; the figures are usually still on disk in `work/metrics-accumulator-6-finalize.toon`, waiting for a close that never came.

### `mark-step-done` (`status.metadata.phase_steps[phase][step]`)

The entry is a dict built by `_build_entry`, which omits every optional key that was not supplied — so a caller passing nothing writes the byte-identical historical record shape.

| Field | Semantics | Currency verdict |
|-------|-----------|------------------|
| `outcome` | **replace** — `done` / `skipped` / `failed` / `loop_back`; a differing outcome requires `--force` | **current** |
| `display_detail` | **replace**, omitted when absent | **current** |
| `head_at_completion` | **replace**, omitted when absent. Refused (nothing written) on a `done` outcome for a `head_dependent: true` step | **current** |
| `loop_back_target` | **replace**, omitted when absent. REQUIRED on `loop_back`, FORBIDDEN otherwise | **current** |
| `facts` | **replace** (the whole dict), omitted when absent. Participates in the idempotency comparison | **current** |
| `firing_count` | **derive** — incremented by `_extend_firing_history` on each changed firing | **current** |
| `prior_firings` | **append** — the superseded firing is folded into the new entry before the write | **current** |

**The entry is replaced, but the history is not lost:** the write is `phase_entry[step] = new_entry`, so every field above is entry-scoped **replace** — yet a step that fires more than once (the ordinary `loop_back` → `loop_back` → `done` shape) does NOT retain only its last firing. `_extend_firing_history` folds the superseded firing into `new_entry` as `prior_firings` and increments `firing_count` before the assignment, so an eventful gate and a first-pass-clean one are distinguishable in structured state. The `previous_*` return fields still echo the immediately-superseded firing to the caller; they are no longer the only surviving record of it. See [`manage-status/SKILL.md`](../../manage-status/SKILL.md) § `mark-step-done` for the firing-history contract this row pair implements.

## Denominators and Their Sampling Point

`metrics.toon` otherwise persists **numerators only** — `total_tokens`, `tool_uses`, `duration_seconds`, `billing_weighted_total` — so a script reading it supports exactly one verdict: *"this got more expensive."* Every denominator a ratio needs lived outside the record and was re-derived at render time, which is a figure nobody can check.

**The sampling point is what makes a denominator dangerous rather than merely absent.** Each one is a MOVING quantity: `affected_files` grows during execute, the task count grows as triage appends fix-tasks, and the deliverable count can change on a Q-Gate re-entry. The same numerator over the same plan therefore yields a different ratio depending on WHEN the denominator was read — so a count with no stated reference moment is not a fixed reference class at all.

### The two-field pair, and the third discriminator

Each denominator is persisted as a **pair**, written together or not at all:

| Field | Type | Source |
|-------|------|--------|
| `deliverable_count` | int | Derived by `generate` — the number of `### N. Title` deliverable headings in the **Deliverables section** of the plan's `solution_outline.md`. `generate` does not own that grammar: it calls `_plan_parsing.extract_deliverable_headings`. `manage-solution-outline list-deliverables` counts through a sibling extractor in that same module (`extract_deliverables` → `split_deliverable_blocks`), and both match through the one shared `_plan_parsing.DELIVERABLE_HEADING_PATTERN` — so the two counts agree by construction, and one plan cannot carry two disagreeing deliverable counts |
| `files_modified` | int | Derived by `generate` — the length of `references.json`'s `affected_files` list. A present-but-empty list is a measured `0` |
| `tasks_completed` | int | Derived by `generate` — the number of `tasks/TASK-*.json` files recording `status: done` |
| `{denominator}_sampling_point` | `generate_time` | Written by `generate` beside each count above. Names WHICH moment the count was taken at |
| `denominators_sampled_at` | ISO 8601 timestamp | Written by `generate` whenever at least one denominator was persisted — the single instant every denominator in that call was counted at |

**On-disk type note**: every plan-level key round-trips as TEXT. `read_metrics_raw` numeric-coerces per-phase block values only, so a consumer reading `deliverable_count` off `metrics.toon` receives `'4'`, not `4`, and must coerce — the same shape `session_message_count` and the `end_time`-presence keys already have. The `generate` RETURN carries the real ints.

`{denominator}_sampling_point` is the **third** use of this module's row-level discriminator convention, and deliberately not a new vocabulary — it has the same shape as `total_tokens_population` (§ Per-Phase Fields) and `value_scope` (§ Per-Field Write Semantics): a closed value set and a companion field per measurement. What does NOT carry over is an absent-reads-as default — this discriminator has none, per the next-but-one paragraph.

**Sampling-point vocabulary** (closed):

| Value | Meaning |
|-------|---------|
| `generate_time` | The count was taken from live plan state at the instant `generate` ran, stamped as `denominators_sampled_at`. It reflects the plan's state at that moment only, and it WILL move if `generate` runs again later in the plan. |

**Absent reads as: nothing.** There is no default. A denominator whose `_sampling_point` companion is absent is a denominator this record does not carry, and a consumer MUST NOT treat the bare count as anchored — the two fields are written as a pair precisely so that state is unreachable going forward.

### A denominator with no determinable sampling point is not persisted

When a source cannot be read — no `solution_outline.md`, no `references.json` (or one that is unparseable, or that carries no `affected_files` list at all), no `tasks/` directory, or one holding no readable `TASK-*.json` — the count is **absent from the record entirely**, never written as `0` and never guessed. This is the module's own absent-is-not-zero rule (§ Exploration-share counters) applied to the reference class rather than to a measurement: a `0` denominator would read as "this plan had no deliverables", which is a claim, while absence reads as "this record does not carry that count", which is the truth.

**Could-not-be-read is the ONLY trigger, and a readable-but-empty source is a measured `0`.** The inverse is the same rule read the other way, and it binds just as hard: an outline whose Deliverables section carries no `### N. Title` heading, and a `references.json` whose `affected_files` list is present but empty, were both COUNTED — the answer was zero, and `0` is what the record carries. Those are legitimate plan states, not failures to read: `solution-outline-standard.md` defines `scope_estimate: none` as pure analysis with no affected files. Collapsing such a plan into absence would tell a reader that the source could not be read when it was read fine — the same conflation of "measured zero" with "unmeasured" that the dispatch-boundary row's `unmeasured` token exists to prevent (§ Per-Dispatch Context-Load Attribution), and the split `tasks_completed` already keeps for an all-pending task population.

`generate` also REMOVES any pair whose source has become unreadable since it was last written, so the record never presents a count beside a `denominators_sampled_at` naming a moment at which that count was not what the plan held.

A consumer that needs a ratio the record does not supply a denominator for MUST state that denominator's provenance and its unstated sampling point wherever it presents the ratio, rather than presenting the ratio as though it were anchored.

## `end_time` Presence Across the Canonical Phases

`generate` checks one thing per canonical phase — does its row carry an `end_time`? — and persists the answer as two plan-level (top-level, non-phase) keys in `metrics.toon`, alongside the `generate` return TOON and a `metrics.md` marker.

**The keys name the predicate, and the predicate is narrow.** They were formerly called `partial` / `unrecorded_phases`, which asserted a completeness verdict the check never computed; they are renamed so a reader at the point of use learns what was actually examined without consulting this document.

### Plan-Level Fields

| Field | Type | Source |
|-------|------|--------|
| `any_phase_missing_end_time` | bool (`true` / `false`) | Derived by `generate` — `true` whenever at least one canonical phase's row carries no `end_time` |
| `phases_missing_end_time` | list (comma-joined in `metrics.toon`, simple TOON array in the `generate` return) | Derived by `generate` — every canonical phase whose row carries no `end_time`, in canonical phase order |

### The Predicate

A canonical phase carries the marker iff its `metrics.toon` row has an `end_time` — the boundary-close stamp `end-phase` / `phase-boundary` writes, the same definition `boundary-status` uses for a missing boundary. A phase with no row at all is missing it too. `phases_missing_end_time` lists the canonical phases (from the standard six-phase model) failing that test; `any_phase_missing_end_time = len(phases_missing_end_time) > 0`.

### What the Check Does NOT Assert

The check reads `end_time` and nothing else. A phase absent from `phases_missing_end_time` therefore carries its boundary marker — and that is the whole claim. It is specifically **not**:

- a **completeness** verdict — the row's `total_tokens`, `tool_uses` and `duration_seconds` are never examined, so a row with `tokens > 0` and `tool_uses == 0` passes;
- an **internal-consistency** check — a `duration_seconds` inconsistent with the row's own `start_time`/`end_time` span passes, and on a re-entered row that divergence is the documented, intended state (see § Timestamp-vs-duration divergence on a re-entered row);
- a statement that the recorded figures are **right**, only that the close happened.

A consumer needing completeness or consistency must derive it from the fields themselves; no key in this record supplies it.

### Floor-Not-Truth Semantics

An `any_phase_missing_end_time: true` total is a **floor, not a truth**: the tokens and durations of at least the listed phases are under-counted, so a consumer MUST treat the aggregate as a lower bound rather than a complete accounting. The canonical under-count is a `6-finalize` whose terminal `record-metrics` close never folded its durable accumulator in (interrupt / loop-back / never-reached). A six-phase plan whose rows all carry `end_time` reports `any_phase_missing_end_time: false` with an empty `phases_missing_end_time` — which, per the section above, is a statement about the six markers and not about the figures behind them.

### No Dual-Key Emission, and the Reader's Three-State Obligation

The writer emits the new keys **only**. It never writes `partial` or `unrecorded_phases`, and it actively drops either key found on an existing `metrics.toon` before writing, so a regenerate cannot leave a stale pair beside the current one.

Archived `metrics.toon` files are immutable history and still carry the old keys, so every consumer that reads an **archived** record MUST implement a three-state read and MUST NOT collapse it to two:

| State | Condition | Required report |
|-------|-----------|-----------------|
| current | the new key is present | the value, read normally |
| **old-schema** | the new key is absent **AND** `partial` or `unrecorded_phases` is present | reported as **old-schema / unrecognised** — never defaulted, never read as a clean verdict, never folded into the pre-`#812` bucket |
| pre-`#812` | neither the new nor the old key is present | the legitimate degrade, which MUST stay distinguishable from old-schema |

Reading an old-schema record as the pre-`#812` degrade would manufacture a clean verdict out of an absent key — the exact defect the rename exists to remove, reproduced one layer down. The three-state read is what makes that impossible; it is a reader obligation, not a writer shim.

### Completeness Denominator and the `metrics.md` Marker

The `## Phase Breakdown` Total uses the **canonical-six baseline** (`len(PHASE_NAMES)`) as its denominator rather than the count of present rows. An entirely-absent phase therefore makes a per-column Total render as a floor (`{sum} (n=k/6)`) instead of silently looking complete. When `any_phase_missing_end_time` is `true`, `generate` also renders an explicit marker line directly under the `## Phase Breakdown` heading — worded so it names the boundary-close marker rather than a completeness verdict:

```markdown
## Phase Breakdown

> Phases missing an end_time boundary marker — 6-finalize. These rows were never closed by end-phase / phase-boundary, so no close recorded their totals and every column Total above is a floor. Such a row can still show figures recovered from sources that do not depend on the close — its accumulator, and its dispatch-boundary rows — and each carries its own marker saying how far it can be trusted: `(boundary floor)` is a lower bound, `(boundary sum, over-covering)` explicitly is not. This is an end_time-presence check only: a phase NOT listed here carries the marker, which says nothing about whether its recorded figures are complete or internally consistent.
```

## Generated Report (metrics.md)

The `generate` command produces a markdown report with per-phase rows:

```markdown
# Plan Metrics: my-feature

| Phase | Worked | Reported (wall) | Idle | Tokens (dispatched unless marked) | Tool Uses | Billing (cost) |
|-------|--------|-----------------|------|-----------------------------------|-----------|----------------|
| 1-init | 2m 30s | 3m 0s | 30s | 25,514 (inline) | 12 | 41,003 |
| 2-refine | 4m 0s | 5m 30s | 1m 30s | 42,000 | 8 | 78,000 |
| 3-outline | 7m 0s | 8m 15s | 1m 15s | 68,000 | 25 | 96,400 |
| **Total** | **13m 30s (n=3/6)** | **16m 45s (n=3/6)** | **3m 15s (n=3/6)** | **135,514 (n=3/6) (spans populations)** | **45 (n=3/6)** | **215,403 (n=3/6)** |

> Tokens population: an unmarked cell is a dispatched-subagent measurement — the default this column header declares. Marked `(inline)` — the phase dispatched nothing, so the cell is the main-context-window measurement enrich folded into total_tokens (also recorded under its own name as inline_main_context_tokens): 1-init. The **Total** therefore sums more than one population and is not a dispatched total; its cell is marked `(spans populations)`.

## 2-refine

- **Total tokens**: 42,000 (dispatched-subagent population — summed from the dispatched leaves' `<usage>` envelopes)
- **Main-context-window usage**: raw `message.usage` summed over this phase's parent turns and the subagent transcripts attributed to the same window. Every bullet below measures that one population
  - **Input tokens**: 38,000
  - **Output tokens**: 4,000
  - **Cache read input tokens**: 210,000
  - **Cache creation input tokens**: 12,000
- **Billing-weighted total**: 78,000 (derived-cost population — input + output + 0.1 × cache_read + 1.25 × cache_creation. What this phase cost to buy, over the main-context window; a different question from the dispatched work the Tokens column measures, so the two are never summed)
```

The four-field usage view and the billing-weighted total are rendered per phase (each phase that carries them gets its own bullet list), not as a single plan-level "Session Enrichment" block. Each four-field bullet renders only when its underlying value is present and non-zero.

The four `message.usage` bullets are **nested under a `Main-context-window usage` heading** that names the population all four measure. An API field name states no population at all, so without the heading these were the only rendered token figures carrying no population claim. The heading states its population outright rather than as a default-plus-exception, because all four fields measure that one population on every row — there is no exception to mark. The bullet-label set is `_FOUR_FIELD_USAGE_LABELS` in `manage-metrics.py`: a usage field added there renders under the same heading and cannot slip in unlabelled.

### Default-plus-exception labelling of the `Tokens` column

The `Tokens` column is **not** single-population — an inline phase's cell carries a main-context-window figure (see § Inline Main-Context Attribution) — so its header names a default plus the marking convention that carries the exceptions: `Tokens (dispatched unless marked)`. A bare `Tokens (dispatched)` would assert a single population over a mixed column, which is the mislabel this contract exists to prevent.

A label may state a default population only when **both** guards hold, and they hold here:

1. **Every exception is marked at the row level.** A phase cell takes an `(inline)` / `(mixed)` suffix; an unmarked cell is dispatched. A phase is named in the annotation only when its cell actually carries the marker — a cell that renders `-` contributes nothing to the Total and is not claimed as marked.
2. **The annotation declares the default.** The `> Tokens population: …` line renders whenever any marker appears (including a report whose only exceptions are `(mixed)`), so a marker is never printed without its key. It is ONE blockquote carrying the default and every exception clause together — a key split from the markers it explains is a key the reader has to reassemble. A wholly-dispatched report renders no annotation at all, because it has no exception to key.

The **Total** row is a cell in the same column and inherits the same default, so it takes the same discipline: when an `(inline)` row fed the sum it is marked `(spans populations)`. Only `(inline)` rows cross-contaminate the Total — a `(mixed)` row's cell is the dispatched figure with its inline spend deliberately excluded. The distinct marker is deliberate: `(mixed)` already means something else on a phase row.

**A third marker qualifies COVERAGE, not population.** A phase whose row carries no `end_time` was never closed, so no close recorded its totals — yet its `work/metrics-dispatch-boundaries-{phase}.toon` file accumulated a row per dispatch throughout, independent of whether the boundary ever closed. When that sum is what the cell shows, the cell is marked `(boundary floor)` and the row records `tokens_cell_source: unclosed_boundary_floor`. This is the same move `enrich` makes when it folds inline spend into a zero-dispatch phase's total and labels the row — a real cost that would otherwise render as nothing — applied to the dispatched population instead of the inline one. It closes two gaps: a boundary sum refused as PARTIAL or OVER leaves the cell rendering `-` while the file holds the phase's whole recorded spend, and a sum whose coverage is UNDECIDABLE already wins the maximum but renders as an ordinary dispatched total, saying nothing about the phase never having closed. The fold can only ever RAISE a cell, and never displaces a measure the reconciliation trusted more.

**The marker states the figure's coverage, so it tracks the coverage classification.** A boundary sum whose recorded rows EXCEED the phase's sampled dispatches is `over` — which this contract calls impossible for a single population and potentially double-counted across a resume — so it is marked `(boundary sum, over-covering)` and records `tokens_cell_source: unclosed_boundary_over_covering` instead. The fold still happens (the alternative is rendering nothing for a phase that demonstrably spent something), but calling that figure a **floor** would assert a lower bound the classification denies. The two markers are never interchangeable, and each renders its own annotation.

⛔ Neither marker is a `total_tokens_population` value, and they add no member to that vocabulary: the figure measures the dispatched population like any other boundary sum. And the fold is scoped to the token figure alone — the phase keeps its place in `phases_missing_end_time`, and **no duration is derived from the boundary file**, which records per-dispatch spans rather than the phase span the close never stamped.

That is a statement about the fold, not about the row. An unclosed row can still render a **Worked** figure, because `generate` backfills `agent_duration_ms` from the phase's durable accumulator — a source that likewise does not depend on the close. Its **Reported (wall)** cell stays `-`, since `duration_seconds` is written only by a close. Neither behaviour is changed by the fold.

Every rendered `total_tokens` figure therefore carries its population: the column header states the default, the `Tokens` cell takes an `(inline)` / `(mixed)` suffix, the Total takes `(spans populations)` when it spans them, the annotation under the table declares the default and names the marked phases, and the `Total tokens` bullet carries the exact per-row population qualifier shown above. The bullet states its row's population outright — it needs no default, so it does **not** take a `(dispatched)` label that would be false on an `inline` row. See § Inline Main-Context Attribution for the three signatures and the `total_tokens_population` discriminator that drives every render site.

### Duration Formatting

The Phase Breakdown table carries three time columns in this order — `Worked`, `Reported (wall)`, `Idle` — followed by `Tokens (dispatched unless marked)`, `Tool Uses`, and `Billing (cost)`. Each time cell is formatted as `Xm Ys`. A cell renders `-` when its underlying value is absent or zero (the symmetric per-cell present/absent rule), and **every column is aggregated independently** under the same symmetric rule, so each Total carries its own `(n=k/6)` partiality marker. See the Worked, Reported (Wall), and Idle Time subsection above for how each time quantity is derived.

`Billing (cost)` carries the per-phase `billing_weighted_total` — a **derived-cost** measure of what the phase cost to buy over the main-context window. It is a different question from the dispatched work `Tokens` measures, so the two columns are never summed into one another: `generate` returns the billing aggregate as its own `total_billing_weighted` field alongside `total_tokens`.

## Valid Phase Names

> Phase names follow the standard 6-phase model. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) § Phase Names for the canonical definition.

## Phase Boundary Record

The fused `phase-boundary` subcommand writes the same persisted state as the
sequence `end-phase {prev}` → `start-phase {next}` → `generate`. After a
boundary call, the per-phase fields recorded for the previous phase are
exactly those `end-phase` would have written, and the next phase has a
`start_time` field as if `start-phase` had been called next. `metrics.md` is
regenerated from the resulting state.

### Persisted Fields After `phase-boundary`

For the **previous phase** (closed):

Every usage/duration source below **accumulates** onto the row rather than
replacing it, so a loop-back that closes the same phase a second time keeps both
entries' figures. A forwarded flag is a per-close **delta** that is ADDED; an
accumulator-sourced value is already **cumulative** and is ASSIGNED unchanged
(adding it would double-count every re-close). A field that resolves from
neither source leaves the row untouched — it never writes a `0`.

| Field | Source |
|-------|--------|
| `end_time` | Timestamp at boundary call (stamped unconditionally, so it always reflects the latest close) |
| `close_count` | Incremented on every close of the closing phase (absent read as `0`) |
| `value_scope` | Recomputed on every close from `close_count` — `single_close` on a first close, `mixed_cumulative_and_last_close` from the second onward |
| `cumulative_fields` / `last_close_fields` | Written only from the second close onward, naming which of the row's own fields the accumulation summed and which stayed scoped to the latest close |
| `duration_seconds` | ADDS this close's **active span** — from whichever of `start_time` / the prior `end_time` is later, up to this `end_time`. A first close is therefore identical to a plain `end_time − start_time`; a second close with no intervening `start-phase` adds only the genuinely-new span. Unparseable timestamps leave the field untouched |
| `agent_duration_ms` | `--duration-ms` (when forwarded) ADDED to the row, or the accumulator's cumulative `duration_ms` ASSIGNED; the resulting **sum** is then clamped to the accumulated wall span |
| `agent_duration_seconds` | Derived from the clamped `agent_duration_ms` |
| `total_tokens` | `--total-tokens` (when forwarded) ADDED, or the accumulator's cumulative value ASSIGNED |
| `tool_uses` | `--tool-uses` (when forwarded) ADDED, or the accumulator's cumulative value ASSIGNED |
| `retrospective_tokens` | `--retrospective-tokens` (when forwarded) ADDED, or the closing phase's accumulator value ASSIGNED |

For the **next phase** (entered):

| Field | Source |
|-------|--------|
| `start_time` | Timestamp at boundary call (always equal to or just after the previous phase `end_time`) |

### Equivalence Guarantee

The fused call produces output that is byte-equivalent to the prior
three-call sequence for the same inputs at the same instant. The only
observable difference is fewer script invocations and a single timestamp
reused for both `end_time` (previous phase) and `start_time` (next phase) —
removing the small wall-clock gap that would otherwise appear between two
separate calls. Treat the gap removal as intentional: phase transitions are
modelled as instantaneous handoffs.

### Boundary Output (TOON)

```toon
status: success
plan_id: EXAMPLE-PLAN
prev_phase: 1-init
next_phase: 2-refine
end_time: 2026-03-27T10:03:00+00:00
start_time: 2026-03-27T10:03:00+00:00
prev_close_count: 1
prev_duration_seconds: 180.0
prev_total_tokens: 25514
metrics_file: metrics.md
phases_recorded: 2
```

`prev_close_count` reports how many times the closing phase has now been closed.
`prev_duration_seconds` / `prev_total_tokens` report the row's **persisted
accumulated** values, not the per-close delta forwarded in — identical figures on
a first close, divergent on a re-entry.

If `generate` cannot run (no phase data at all — only possible at plan
start), the boundary call still writes the start/end records and surfaces the
generate status in `generate_status` / `generate_message` instead of
`metrics_file` / `phases_recorded`.

## Token Data Sources

| Source | When Used | Granularity |
|--------|-----------|-------------|
| Task agent `<usage>` tags (forwarded to `end-phase` flags) | Agent-delegated phases — single agent per phase | Per-phase |
| `accumulate-agent-usage` per-phase accumulator file | Phases that dispatch multiple agents (`5-execute`, `6-finalize`) | Per-phase, summed across agent returns |
| JSONL session transcript (`enrich` subagent `<usage>`-tag attribution) | Any phase whose timestamp window contains Task tool calls | Per-phase (`subagent_*` fields) |
| Raw `message.usage` dicts in the parent + subagent transcripts (`enrich` four-field walk) | Any phase whose window contains a parent turn or a spawned subagent transcript | Per-phase (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `billing_weighted_total`) |
| `tool_use` / `tool_result` content items in the parent + subagent transcripts (`enrich` tool-call walk) | Any phase whose window contains a tool call, on a target that exposes a transcript | Per-phase (`{exploration,work,execute,orchestration,unclassified}_tool_calls` and the matching `_result_bytes`). ABSENT — never zero — on a target that declines the transcript primitive |
| Payload residency across the phase's billed turns (`enrich` tool-call walk) | Same condition as the row above — the attribution is derived from the same payloads | Per-phase (`cache_read_attributed_{bucket}` and the `cache_read_unattributed` residual, reconciling EXACTLY to `cache_read_input_tokens`). ABSENT — never zero — on a target that declines the transcript primitive |
| Target path on each exploration `tool_use` item's `input` (`enrich` tool-call walk) | Same condition as the two rows above — the sub-split re-cuts the same payloads | Per-phase (`exploration_{index_answerable,doc_residency,unattributed}_bytes`, partitioning `exploration_result_bytes` EXACTLY). ABSENT — never zero — on a target that declines the transcript primitive |

## Per-Phase Subagent Accumulator (`work/metrics-accumulator-{phase}.toon`)

Written by `accumulate-agent-usage`, read as fallback by `end-phase` and `phase-boundary` when explicit token flags are omitted. One file per phase that dispatches agents (e.g., `work/metrics-accumulator-5-execute.toon`, `work/metrics-accumulator-6-finalize.toon`). Other phases never produce one.

### Format

```toon
plan_id: EXAMPLE-PLAN
phase: 6-finalize
total_tokens: 84211
tool_uses: 38
duration_ms: 412390
retrospective_tokens: 31200
samples: 4
updated: 2026-03-27T10:25:00+00:00
```

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `plan_id` | string | Echoed for sanity-checking against the parent plan directory |
| `phase` | string | Must be one of the canonical phase names |
| `total_tokens` | int | Running sum across every `accumulate-agent-usage` call for this phase |
| `tool_uses` | int | Running sum |
| `duration_ms` | int | Running sum |
| `retrospective_tokens` | int | Running sum of `--retrospective-tokens` values — non-zero only when the finalize retrospective step forwarded its `<usage>` total. `end-phase` / `phase-boundary` read this as the fallback for the `[6-finalize].retrospective_tokens` row |
| `samples` | int | Number of `accumulate-agent-usage` calls — reflects how many Task-agent returns were rolled in |
| `updated` | ISO 8601 timestamp | Updated atomically on every write |

### Idempotency & Lifecycle

- The file is the only authoritative state for the running totals — model-context numbers are not preserved across context compactions.
- `accumulate-agent-usage` always reads-then-writes: missing flags do not zero a field, they leave it unchanged. Each call increments `samples` by 1 regardless of which flags were provided.
- The file is left in `work/` after `end-phase` consumes it — the audit trail (per-call `samples` count, last `updated` timestamp) is useful when investigating drift between accumulator totals and the closed-phase row.
- `archive-plan` moves `work/` along with the rest of the plan directory; archived accumulator files therefore remain available for retrospective analysis.

## Per-Dispatch Boundary Record (`work/metrics-dispatch-boundaries-{phase}.toon`)

Written by `record-dispatch-boundary`, one TOON-tabular row appended per phase Task dispatch termination. The file is the audit trail `plan-retrospective` correlates with `[OUTCOME]`-log coverage gaps to detect agent-initiated re-dispatch. `generate` is a second consumer — it sums the `total_tokens` column per phase and reconciles it against the recorded phase total (see Dispatch-Boundary Reconciliation above). One file per phase that dispatches Task agents (in practice `5-execute` and `6-finalize`).

### Format

```toon
plan_id: EXAMPLE-PLAN
phase: 5-execute
rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:
2026-05-08T14:23:11Z,clean_exit_queue_empty,84211,38,412390,38000,4000,210000,12000
2026-05-08T14:41:02Z,budget_yield,51044,17,238110,unmeasured,unmeasured,unmeasured,unmeasured
2026-05-08T15:02:55Z,clean_exit_queue_empty,12903,4,61220,9100,0,0,0
```

The first three lines are the TOON-tabular header (`plan_id:`, `phase:`, `rows[]{…}:`); each subsequent line is one CSV-style data row in the declared column order.

The three data rows above are the three distinguishable cases, in order: a dispatch whose context load was measured; one whose caller forwarded no `message.usage` figures at all (four `unmeasured` cells); and one measured to be zero on three of the four columns (three genuine `0` cells). Before the `unmeasured` token existed, row 2 would have carried four literal `0`s — and **that** all-zero pre-token row is byte-identical to a genuine all-measured-zero row, since neither carries anything on columns 6–9 but zeros. Row 3 is not half of that pair: its nonzero `input_tokens` cell dates the row, so its three `0`s are readable as genuine measured zeros. See *Provenance of a measured zero* below for the fingerprint rule that separates the two members of the identical pair — and for why, absent a fingerprint, it cannot.

### Per-Dispatch Context-Load Attribution

This section is the **single source of truth** for the dispatch-boundary row's column order, count, and unmeasured representation. Every consumer cites it as authority — and each one nonetheless RESTATES part of the schema in its own file, because they run in separate processes (and one lives outside this repository's crawled inventory) and cannot import a shared constant. Those restating surfaces are enumerated, with the obligation they carry, in **Restating surfaces (lock-step obligation)** at the end of this section; that list is the thing to keep in sync, and it is not empty.

Each row carries **nine columns**: the **legacy five** followed by the **four context-load columns appended at the END** for positional backward compatibility. The four context-load columns are the per-DISPATCH counterpart to the per-PHASE four-field `message.usage` view that `enrich` writes (see Per-Phase Fields above); they capture the dispatched agent's context-load totals at dispatch termination so per-dispatch context cost (dispatch count, collapsed triage contexts, per-dispatch context size) becomes measurable.

| # | Column | Type | Source | Value when the flag is omitted |
|---|--------|------|--------|--------------------------------|
| 1 | `timestamp` | ISO 8601 timestamp | Set by `record-dispatch-boundary` at append time | — |
| 2 | `termination_cause` | enum | `--termination-cause` (see enum below) | — (required) |
| 3 | `total_tokens` | int | `--total-tokens` (subagent `<usage>` total at termination) | `0` |
| 4 | `tool_uses` | int | `--tool-uses` | `0` |
| 5 | `duration_ms` | int | `--duration-ms` | `0` |
| 6 | `input_tokens` | int \| `unmeasured` | `--input-tokens` (dispatch `message.usage.input_tokens`) | the literal `unmeasured` |
| 7 | `output_tokens` | int \| `unmeasured` | `--output-tokens` (dispatch `message.usage.output_tokens`) | the literal `unmeasured` |
| 8 | `cache_read_input_tokens` | int \| `unmeasured` | `--cache-read-input-tokens` (dispatch `message.usage.cache_read_input_tokens`) | the literal `unmeasured` |
| 9 | `cache_creation_input_tokens` | int \| `unmeasured` | `--cache-creation-input-tokens` (dispatch `message.usage.cache_creation_input_tokens`) | the literal `unmeasured` |

#### The unmeasured token, and the cell read

The four context-load columns are OPTIONAL — a caller with no `message.usage` figure to forward passes no flag. They therefore carry **no numeric default**: an omitted flag writes the literal `unmeasured`, never `0`. "The caller passed no measurement" and "the dispatch loaded zero context" are different facts, and writing `0` for both made them byte-identical rows. This is the module's own absent-is-not-zero rule (the one the exploration counters and the cache-read attribution group already follow — see § Exploration-share counters) applied to the ledger row; the positional row shape means the column cannot be dropped, so it carries a token instead.

The legacy five columns keep their `0` default deliberately: no consumer distinguishes an absent from a zero on those, so introducing a second unmeasured surface there would add a distinction nothing reads.

Every reader of columns 6–9 MUST implement the same cell read, and MUST NOT collapse it to two:

| Cell | Reading | Required behaviour |
|------|---------|--------------------|
| a nonzero integer | **measured** | Carry the int — a real value under any writer |
| a literal `0` | **measured** when the row is datable to the current writer, else **indeterminate** | Carry `0` only when a post-token fingerprint dates the row; otherwise omit the key and name the column indeterminate — see *Provenance of a measured zero* below |
| the literal `unmeasured` | **recognised, and deliberately not measured** | Carry the column as ABSENT. Never substitute `0` |
| a column the row is too short to have | **unmeasured** | Carry the column as ABSENT, exactly as an explicit `unmeasured` token. A legacy five-column row recorded no context-load measurement at all, so absence is the honest reading — not a parse failure. Never substitute `0` |
| anything else (a non-int, non-token cell value) | **unrecognised** | Report as unrecognised — distinct from unmeasured. Never default it, and never fold it into either neighbour |

The distinction between *unmeasured* and *unrecognised* is load-bearing: the first is a statement the writer made on purpose, the second is a shape the reader failed to understand. Collapsing them would let a genuinely corrupt row read as a deliberate abstention.

#### Provenance of a measured zero (the fourth state)

A cell parsed as an integer is a MEASUREMENT — except that a literal `0` cannot always be trusted as one. Before the `unmeasured` token existed, the writer defaulted every omitted context-load column to a literal `0`, so a nine-column row written by that pre-token writer is **byte-identical** to a genuine all-measured-zero row. "Measured zero" and "wrote 0 because the column was never measured" are the same bytes on disk: no reader-side change can separate them by looking at the cell alone. This is an information-loss property of the record, not a parsing gap — widening the column-count floor cannot recover a distinction the two-state writer already destroyed.

There is **no out-of-band discriminator** that dates such a row: the format carries no schema stamp and no writer-emitted provenance field, and a row's own timestamp cannot be compared against a landing instant the record does not carry. What a reader *can* use is an IN-band, post-token **fingerprint** on the row itself:

- an **`unmeasured` token** in any of columns 6–9 — only the current writer emits it, so the row was written by the current writer; or
- a **nonzero** context-load cell — "nothing to measure" never yields a nonzero, so the cell is a real measurement and dates the row.

A literal `0` in a row carrying **either** fingerprint is a genuine measured zero and is carried as `0` — this is why the row `2026-05-08T15:02:55Z,…,9100,0,0,0` above reads as three genuine measured zeros. A literal `0` in a row carrying **neither** — every context-load cell a literal `0`, or `0`s beside only unrecognised cells — cannot be dated, and is reported as a **fourth state, `indeterminate`**: the key is omitted and the column is named in the row's `indeterminate_columns`. It is distinct from `unmeasured` (a statement the writer made on purpose — collapsing to it would assert an abstention the writer never made) and from `unrecognised` (a shape the reader failed to parse).

The `plan-retrospective` reader (`_parse_dispatch_boundary_file`) implements this row-level provenance gate. A reader that does not recover provenance still performs the cell read above, but reads an undatable `0` as a measured zero — the pre-fix behaviour whose correction this section documents.

**Positional backward compatibility**: the four context-load columns are appended at the END so columns 1–5 are positionally unchanged. A legacy five-column row (written before the columns existed) still parses — the `plan-retrospective` reader uses a `len(parts) >= 5` floor — and its four **missing** columns read as **unmeasured** (absent), never as a measured `0`. That is the honest reading: a row written before the columns existed recorded no context-load measurement at all. A malformed appended cell reads as **unrecognised** and does not drop the whole row.

The harder case is a **widened nine-column row written before the `unmeasured` token existed**: its four columns are PRESENT and carry a literal `0`, so a reader that trusts every integer records four measured zeros — the same over-claim positional compatibility exists to prevent, one floor lower than the five-column case. Such a row's zeros are of **indeterminate** provenance (see *Provenance of a measured zero* above) and read as the fourth state, never as measured `0`, unless the row carries a post-token fingerprint that dates it. A row written before the token existed recorded no *datable* context-load measurement, whether it omitted the columns (five-column) or defaulted them to `0` (nine-column).

**Restating surfaces (lock-step obligation).** This section is the single source of truth; **five** surfaces restate it and MUST move together — the writer in `manage-metrics.py` (`cmd_record_dispatch_boundary` + `_DISPATCH_CONTEXT_LOAD_COLUMNS`), the `record-dispatch-boundary` operation block in `manage-metrics/SKILL.md`, the reader in `plan-retrospective/scripts/analyze-logs.py` (`_parse_dispatch_boundary_file`), the hand-copied `_BC_LEDGER_COLUMNS` / `_BC_LEDGER_UNMEASURED_TOKEN` constants — together with the `_parse_dispatch_boundary_totals` cell read and the row-level provenance gate that consumes them — in `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` (that reader recovers provenance too, so a change to *Provenance of a measured zero* above moves it as well as the `plan-retrospective` reader), and the `billing-composition` check's own restatement of the column set, the four-way cell read and that same provenance gate in `.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md`. The last **two** live in a tree the architecture inventory does not crawl, so a drift in either is invisible to a content sweep — they are named here so they are found by reading rather than by searching.

**`termination_cause` enum**: `voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`, `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`, `returned_with_findings`. Missing or unrecognised causes are script errors (no implicit fallback). `returned_with_findings` marks a productive non-completion — a dispatch that returned findings and signalled a loop-back — and is the dispatch-ledger counterpart of the step-completion `loop_back` outcome (see § Per-Field Write Semantics for that outcome); it exists so a findings-bearing loop-back is not mis-stamped as `error`.

### Lifecycle

- Atomic append — partial files are never visible to readers; the same shared file-write helpers as `accumulate-agent-usage` are used.
- The file is left in `work/` after the plan completes; `archive-plan` moves it with the rest of the plan directory so archived dispatch-boundary records remain available for retrospective analysis.
