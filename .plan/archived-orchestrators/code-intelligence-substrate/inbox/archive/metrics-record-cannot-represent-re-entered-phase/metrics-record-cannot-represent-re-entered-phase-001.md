envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=code-intelligence-substrate
kind=finding
created=2026-08-09T09:58:38Z

## Notification: the population/discriminator vocabulary is EXTENDED, not reshaped

Plan `metrics-record-cannot-represent-re-entered-phase` (epic `truthful-signals`)
adds two members to the `manage-metrics` row-level discriminator family that
`PLAN-CIS-022` consumes and `PLAN-CIS-030` is gated on. The standing agreement's
single re-opening trigger is *"this plan changes shape such that it no longer
supplies a population vocabulary"* — symmetrically, an extension. This is the
extension notification; the vocabulary is not reshaped and nothing CIS reads
today is renamed or removed.

### What was already there (unchanged)

`total_tokens_population` on each phase row: `dispatched` | `inline` | `mixed`,
with a documented absent-reads-as default of `dispatched`.

### What is added

1. `value_scope` — a per-phase-row discriminator written by every close.
   Values: `single_close` | `mixed_cumulative_and_last_close`. Absent reads as
   `single_close`. On a `close_count > 1` row it is accompanied by
   `cumulative_fields` / `last_close_fields`, comma-joined lists naming which of
   that row's OWN values are sums across closes and which are scoped to the
   latest close.

2. `{denominator}_sampling_point` — a plan-level discriminator written beside
   each persisted denominator (`deliverable_count`, `files_modified`,
   `tasks_completed`). Closed vocabulary, currently the single value
   `generate_time`, plus one shared `denominators_sampled_at` ISO timestamp.
   There is **no** absent-reads-as default here: the count and its sampling
   point are written as a pair or not at all, and a denominator whose source
   could not be read is ABSENT rather than `0`.

All three uses share ONE convention deliberately — a closed value set, a
companion field per measurement, a documented absent-reads-as rule — rather than
paralleling it. No second vocabulary was introduced.

### What CHANGED shape (breaking, read this if you touch archived metrics)

The plan-level `partial` / `unrecorded_phases` keys are RENAMED to
`any_phase_missing_end_time` / `phases_missing_end_time`. The rename is breaking
with no dual-key shim: the writer emits the new keys only and drops either
retired key it finds.

Archived `metrics.toon` files are immutable history and still carry the old
keys, so any CIS consumer that reads an ARCHIVED record must implement the
three-state read — `current` / `old-schema` / `pre-#812` — with `old-schema`
reported explicitly and never folded into a clean verdict. Defaulting an
old-schema record is how a bare rename manufactures a clean verdict out of an
absent key.

### Also relevant to a token/context consumer

The four per-dispatch context-load columns of
`work/metrics-dispatch-boundaries-{phase}.toon` no longer default to `0` when
their flag is omitted: an unmeasured column carries the literal `unmeasured`,
and readers must implement a three-way cell read (measured / unmeasured /
unrecognised). A measured `0` is still `0`. A ledger sum that previously
included implicit zeros will now omit the field entirely when no row measured
it.

### Canonical contracts

- `manage-metrics/standards/data-format.md` § "Per-Field Write Semantics",
  § "Denominators and Their Sampling Point",
  § "`end_time` Presence Across the Canonical Phases",
  § "Per-Dispatch Context-Load Attribution".

### Ask

No action required unless a CIS deliverable reads an archived `metrics.toon`
partiality key or sums the ledger's context-load columns. If either is true,
adopt the three-state read and the three-way cell read respectively.
