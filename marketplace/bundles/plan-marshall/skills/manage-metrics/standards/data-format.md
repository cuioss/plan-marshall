# Metrics Data Format

Storage format specifications for plan metrics collection and reporting.

## Storage Files

| File | Format | Purpose |
|------|--------|---------|
| `work/metrics.toon` | TOON key-value | Intermediate timing and token data per phase |
| `metrics.md` | Markdown | Human-readable report with tables |

Both files live in `.plan/plans/{plan_id}/`.

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
enriched.input_tokens: 450000
enriched.output_tokens: 35000
enriched.total_tokens: 485000
enriched.message_count: 127
```

### Key Naming Convention

> **Phase naming**: TOON keys use the `phase.{N}-{name}.{field}` prefix form (e.g., `phase.1-init.start`). The canonical phase name is `1-init` — see `ref-manage-contract` for the standard phase list.

- `phase.{phase_name}.{field}` — per-phase timing/token data
- `enriched.{field}` — session transcript enrichment data (attributed to plan as a whole)

### Per-Phase Fields

| Field | Type | Source |
|-------|------|--------|
| `start` | ISO 8601 timestamp | `start-phase` command |
| `end` | ISO 8601 timestamp | `end-phase` command |
| `total_tokens` | int | Task agent `<usage>` tag |
| `duration_ms` | int | Task agent `<usage>` tag (agent-reported, distinct from wall-clock) |
| `tool_uses` | int | Task agent `<usage>` tag |

### Enrichment Fields

| Field | Type | Source |
|-------|------|--------|
| `input_tokens` | int | JSONL session transcript parsing |
| `output_tokens` | int | JSONL session transcript parsing |
| `total_tokens` | int | Sum of input + output |
| `message_count` | int | Number of messages in transcript |

## Generated Report (metrics.md)

The `generate` command produces a markdown report with per-phase rows:

```markdown
# Plan Metrics: my-feature

| Phase | Duration | Tokens | Tool Uses |
|-------|----------|--------|-----------|
| 1-init | 3m 0s | 25,514 | 12 |
| 2-refine | 5m 30s | 42,000 | 8 |
| 3-outline | 8m 15s | 68,000 | 25 |
| **Total** | **16m 45s** | **135,514** | **45** |

## Session Enrichment

- Input tokens: 450,000
- Output tokens: 35,000
- Total tokens: 485,000
- Messages: 127
```

### Duration Formatting

Duration is computed as wall-clock time from start/end timestamps and formatted as `Xm Ys`.

## Valid Phase Names

Must match `manage-status` phases exactly: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`.

## Token Data Sources

| Source | When Used | Granularity |
|--------|-----------|-------------|
| Task agent `<usage>` tags | Agent-delegated phases | Per-phase |
| JSONL session transcript | Main-context phases (via `enrich`) | Per-plan (spans phases) |
