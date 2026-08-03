# Metrics Data Format

Storage format specifications for plan metrics collection and reporting.

## Storage Files

| File | Format | Purpose |
|------|--------|---------|
| `work/metrics.toon` | TOON key-value | Intermediate timing and token data per phase |
| `work/metrics-accumulator-{phase}.toon` | TOON key-value | Per-phase running totals of subagent `<usage>` data, written by `accumulate-agent-usage` and read as fallback by `end-phase` / `phase-boundary` |
| `metrics.md` | Markdown | Human-readable report with tables |

All files live in `.plan/plans/{plan_id}/`. Accumulator files are created lazily — only phases that dispatch agents (and call `accumulate-agent-usage`) produce one.

## Intermediate Storage (metrics.toon)

The metrics.toon file stores raw phase timing and token data as flat key-value pairs:

```toon
phase.1-init.start: 2026-03-27T10:00:00Z
phase.1-init.end: 2026-03-27T10:03:00Z
phase.1-init.total_tokens: 25514
phase.1-init.duration_ms: 180000
phase.1-init.tool_uses: 12
phase.2-refine.start: 2026-03-27T10:03:15Z
phase.2-refine.end: 2026-03-27T10:08:45Z
phase.2-refine.total_tokens: 42000
phase.2-refine.input_tokens: 38000
phase.2-refine.output_tokens: 4000
phase.2-refine.cache_read_input_tokens: 210000
phase.2-refine.cache_creation_input_tokens: 12000
phase.2-refine.billing_weighted_total: 78000
session_message_count: 127
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
| `total_tokens` | int | Task agent `<usage>` tag (forwarded explicitly OR read from accumulator file). **Accumulating**: an explicitly-forwarded flag value is a per-close delta ADDED to the row; an accumulator-sourced value is already cumulative and is ASSIGNED |
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
| `billing_weighted_total` | int | Derived by `enrich` from the four-field view: `input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`. A billing-cost figure, NOT a work-comparable measure |
| `idle_duration_ms` | int | Derived by `generate` — the per-phase idle residual `max(0, wall_clock_ms - worked_ms)` |
| `dispatch_boundary_total` | int | Derived by `generate` — the sum of the `total_tokens` column across the phase's `work/metrics-dispatch-boundaries-{phase}.toon` rows. Persisted as a DISTINCT field (it never overwrites `total_tokens`); present only when the boundary file exists and sums to a truthy value. See Dispatch-Boundary Reconciliation below |
| `inline_main_context_tokens` | int | Derived by `enrich` — `input_tokens + output_tokens + cache_creation_input_tokens` (EXCLUDING `cache_read_input_tokens`) surfaced when a phase carries BOTH a dispatched `total_tokens` AND non-zero four-field usage (the inline-step signature). Persisted as a DISTINCT field (it never overwrites `total_tokens`). See Inline Main-Context Attribution below |
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

### Dispatch-Boundary Reconciliation

`generate` reconciles each phase's recorded `total_tokens` against the durable
dispatch-boundaries sum (the `total_tokens` column summed across the phase's
`work/metrics-dispatch-boundaries-{phase}.toon` rows). `generate` reads the
dispatch-boundaries file as a reconciliation source; `plan-retrospective` also
reads it, as an audit trail.

The per-phase accumulator (`work/metrics-accumulator-{phase}.toon`) and the
dispatch-boundaries file record the **same population**: every dispatched leaf
appears once in each. They diverge only when a leaf's Step-8b
`record-dispatch-boundary` fired but the accumulator fold
(`accumulate-agent-usage`) was missed, which makes the accumulator
*under-count* relative to the boundary sum. Because the two measure the same
leaves, the non-double-counting reconciliation is:

```text
reported = max(total_tokens, dispatch_boundary_total)   # NOT a sum
```

Summing would double-count every leaf; `max()` recovers the under-count while
staying safe under the same-population invariant. The reconciliation is
**generate-side / render-time**:

- The raw `total_tokens` field is left **byte-identical** on the row
  (explicit-wins — a value recorded by `end-phase` / `phase-boundary` is never
  overwritten).
- The boundary sum is persisted as the DISTINCT `dispatch_boundary_total`
  field.
- When `dispatch_boundary_total > total_tokens`, the Phase Breakdown `Tokens`
  cell renders the larger (boundary) value and feeds it to the Total, and an
  annotation line under the table names the reconciled phases
  (`> Tokens reconciled from dispatch boundaries …`). The Phase Details section
  also surfaces the `Dispatch-boundary total` bullet.
- When the boundary file is absent (sum is `0`) the reconciliation is a clean
  no-op — no field is persisted and the render is unchanged.

The `#812` `partial` / `unrecorded_phases` completeness verdict (which keys off
`end_time` only) is untouched by this reconciliation.

### Inline Main-Context Attribution

An **inline** step runs in the orchestrator's own (main) context rather than as a
dispatched subagent, so it produces no `<usage>` envelope and contributes nothing
to the per-phase accumulator — there is no per-step `<usage>` source. Its cost is
instead captured by `enrich`'s phase-window attribution, which sums the
parent-window `message.usage` four-field view into the phase row.

`enrich` surfaces that inline contribution as the distinct
`inline_main_context_tokens` field on any phase that carries **both**:

- a truthy dispatched `total_tokens` (recorded by a dispatched step's `<usage>` /
  the accumulator), AND
- non-zero four-field `message.usage` (the inline-step signature — the `6-finalize`
  case where dispatched steps AND inline finalize steps both ran).

The derivation matches the inline-only `total_tokens` narrowing:

```text
inline_main_context_tokens = input_tokens + output_tokens + cache_creation_input_tokens
```

`cache_read_input_tokens` is **excluded** so the figure matches the
dispatched-`<usage>` total definition (which is fed via `end-phase --total-tokens`
and excludes cache reads); including it would over-count the inline contribution
by ~100× versus comparable dispatched rows. The field is **explicit-wins**: it is
surfaced ALONGSIDE `total_tokens`, never overwriting it, and `generate` renders it
as a reconciliation line under the phase total in `metrics.md`. This attribution
does not touch the `#812` `end_time`-keyed `partial` verdict — a timestamps-only
inline close stays non-`partial`.

When a phase carries four-field usage but **no** dispatched `total_tokens` (the
pure inline-only phase — `1-init`, recipe-inline refine/outline), the same sum is
folded directly into `total_tokens` instead (see the inline-derivation note in
`cmd_generate` / the `enrich` writer). The `inline_main_context_tokens` field is
the complementary case: a mixed phase where a dispatched total already exists.

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
`end_time`-keyed `partial` verdict (a re-entered phase still carries its
`end_time`, so it stays recorded / non-`partial`). It adds no new write path; it
reuses the existing `generate` read → annotate → write loop.

| Field | Type | Source |
|-------|------|--------|
| `boundary_monotonicity` | list (comma-joined in `metrics.toon`, simple TOON array in the `generate` return) | Derived by `generate` — canonical-order list of phases whose `start_time` precedes a prior phase's `end_time`; absent when every boundary is monotonic. Names the LATER phase, not the re-entered one |
| `re_entered_phases` | list (comma-joined in `metrics.toon`, simple TOON array in the `generate` return) | Derived by `generate` — canonical-order list of phases whose row carries `close_count > 1`; absent when no phase was re-entered. Rendered as the `> Re-entered phases: …` marker under `## Phase Breakdown`, with a per-phase **Closes** bullet under Phase Details. The authoritative re-entry signal — it names the phase that was actually closed more than once |

### Enrichment Fields

`enrich` writes the four-field usage view and `billing_weighted_total` per phase (under the `phase.{phase_name}.{field}` prefix — see Per-Phase Fields above), plus one plan-level field:

| Field | Type | Source |
|-------|------|--------|
| `session_message_count` | int | Plan-level count of transcript messages that carried usage data (input/output/total) |

The four-field usage view is no longer stored as plan-level `enriched.{field}` keys — it is attributed per phase by the transcript walks. See the Per-Phase Fields table for `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, and `billing_weighted_total`.

## Partiality (Completeness Verdict)

`generate` computes a first-class completeness verdict over the canonical six-phase baseline and persists it as two plan-level (top-level, non-phase) keys in `metrics.toon`, alongside the `generate` return TOON and a `metrics.md` marker.

### Plan-Level Fields

| Field | Type | Source |
|-------|------|--------|
| `partial` | bool (`true` / `false`) | Derived by `generate` — `true` whenever at least one canonical phase lacks a recorded boundary |
| `unrecorded_phases` | list (comma-joined in `metrics.toon`, simple TOON array in the `generate` return) | Derived by `generate` — every canonical phase that lacks a recorded boundary, in canonical phase order |

### Recorded-Phase Predicate

A canonical phase is **recorded** iff its `metrics.toon` row carries an `end_time` (the boundary-close marker `end-phase` / `phase-boundary` write — the same definition `boundary-status` uses for a missing boundary). A phase with no row at all is **unrecorded** too. `unrecorded_phases` is the list of canonical phases (from the standard six-phase model) failing this predicate; `partial = len(unrecorded_phases) > 0`.

### Floor-Not-Truth Semantics

A `partial: true` total is a **floor, not a truth**: the tokens and durations of at least the listed phases are under-counted, so a consumer MUST treat the aggregate as a lower bound rather than a complete accounting. The canonical under-count is a `6-finalize` whose terminal `record-metrics` close never folded its durable accumulator in (interrupt / loop-back / never-reached). A fully-recorded six-phase plan reports `partial: false` with an empty `unrecorded_phases`.

### Completeness Denominator and the `metrics.md` Marker

The `## Phase Breakdown` Total uses the **canonical-six baseline** (`len(PHASE_NAMES)`) as its completeness denominator rather than the count of present rows. An entirely-absent phase therefore makes a per-column Total render as partial (`{sum} (n=k/6)`) instead of silently looking complete. When `partial` is `true`, `generate` also renders an explicit marker line directly under the `## Phase Breakdown` heading:

```markdown
## Phase Breakdown

> Partial: unrecorded phases — 6-finalize
```

## Generated Report (metrics.md)

The `generate` command produces a markdown report with per-phase rows:

```markdown
# Plan Metrics: my-feature

| Phase | Worked | Reported (wall) | Idle | Tokens | Tool Uses |
|-------|--------|-----------------|------|--------|-----------|
| 1-init | 2m 30s | 3m 0s | 30s | 25,514 | 12 |
| 2-refine | 4m 0s | 5m 30s | 1m 30s | 42,000 | 8 |
| 3-outline | 7m 0s | 8m 15s | 1m 15s | 68,000 | 25 |
| **Total** | **13m 30s** | **16m 45s** | **3m 15s** | **135,514** | **45** |

## 2-refine

- Total tokens: 42,000
- Input tokens: 38,000
- Output tokens: 4,000
- Cache read input tokens: 210,000
- Cache creation input tokens: 12,000
- **Billing-weighted total**: 78,000 (billing-cost figure, not a work-comparable measure — cache_read sums context re-reads across turns)
```

The four-field usage view and the billing-weighted total are rendered per phase (each phase that carries them gets its own bullet list), not as a single plan-level "Session Enrichment" block. Each four-field bullet renders only when its underlying value is present and non-zero.

### Duration Formatting

The Phase Breakdown table carries three time columns in this order — `Worked`, `Reported (wall)`, `Idle` — followed by `Tokens` and `Tool Uses`. Each cell is formatted as `Xm Ys`. A cell renders `-` when its underlying value is absent or zero (the symmetric per-cell present/absent rule), and the Total row sums `Worked`, `Reported (wall)`, and `Idle` independently. See the Worked, Reported (Wall), and Idle Time subsection above for how each quantity is derived.

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
```

The first three lines are the TOON-tabular header (`plan_id:`, `phase:`, `rows[]{…}:`); each subsequent line is one CSV-style data row in the declared column order.

### Per-Dispatch Context-Load Attribution

This section is the **single source of truth** for the dispatch-boundary row's column order, count, and defaults. Consumers (the `manage-metrics` script writer, the `plan-retrospective` `analyze-logs.py` reader, and `SKILL.md`) reference this section rather than restating the schema.

Each row carries **nine columns**: the **legacy five** followed by the **four context-load columns appended at the END** for positional backward compatibility. The four context-load columns are the per-DISPATCH counterpart to the per-PHASE four-field `message.usage` view that `enrich` writes (see Per-Phase Fields above); they capture the dispatched agent's context-load totals at dispatch termination so per-dispatch context cost (dispatch count, collapsed triage contexts, per-dispatch context size) becomes measurable.

| # | Column | Type | Source | Default |
|---|--------|------|--------|---------|
| 1 | `timestamp` | ISO 8601 timestamp | Set by `record-dispatch-boundary` at append time | — |
| 2 | `termination_cause` | enum | `--termination-cause` (see enum below) | — (required) |
| 3 | `total_tokens` | int | `--total-tokens` (subagent `<usage>` total at termination) | `0` |
| 4 | `tool_uses` | int | `--tool-uses` | `0` |
| 5 | `duration_ms` | int | `--duration-ms` | `0` |
| 6 | `input_tokens` | int | `--input-tokens` (dispatch `message.usage.input_tokens`) | `0` |
| 7 | `output_tokens` | int | `--output-tokens` (dispatch `message.usage.output_tokens`) | `0` |
| 8 | `cache_read_input_tokens` | int | `--cache-read-input-tokens` (dispatch `message.usage.cache_read_input_tokens`) | `0` |
| 9 | `cache_creation_input_tokens` | int | `--cache-creation-input-tokens` (dispatch `message.usage.cache_creation_input_tokens`) | `0` |

**Positional backward compatibility**: the four context-load columns are appended at the END so columns 1–5 are positionally unchanged. A legacy five-column row (written before the columns existed) still parses — the `plan-retrospective` reader uses a `len(parts) >= 5` floor and defaults columns 6–9 to `0` when a row carries only the legacy five. A malformed appended field degrades the four context fields to `0` rather than dropping the whole row.

**`termination_cause` enum**: `voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`, `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`. Missing or unrecognised causes are script errors (no implicit fallback).

### Lifecycle

- Atomic append — partial files are never visible to readers; the same shared file-write helpers as `accumulate-agent-usage` are used.
- The file is left in `work/` after the plan completes; `archive-plan` moves it with the rest of the plan directory so archived dispatch-boundary records remain available for retrospective analysis.
