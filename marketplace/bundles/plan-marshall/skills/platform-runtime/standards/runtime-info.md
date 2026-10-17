# Runtime-Info Extension Point

Logical extension point for runtime information collection. The `runtime-info`
operation reports the harness/client identifier, the transcript-availability
capability, model name/type/version,
effort level, and build-version on a best-effort basis for the `client.toon`
pre-flight artifact. Every value that can come from more than one place carries
its source (`model_source` / `effort_source`): `self_reported` when a CLI flag
supplied it, `measured` when a script-readable source did.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Scope

Concrete providers exist for `claude`, `opencode`, and `antigravity`.

## CLI Shape

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime runtime-info
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime runtime-info \
  --model <id> --effort <level>
```

`--model` and `--effort` are optional and carry the executing LLM's
self-report about itself; each is recorded with its `self_reported` source tag.
Routing is config-driven: the target is resolved through
`target_context.resolve_target` (ambient environment signal, then the
machine-local harness/run configuration, then the `claude` fallback); an
unregistered target yields the established `unknown_target` error path.

## Client.toon Schema

One required attribute pair (`harness`, `transcripts`) and eight optional attributes per run entry. Unreadable attributes are absent rather than estimated.

| Key | Meaning | Always present |
|-----|---------|----------------|
| `harness` | Harness identifier (`claude`, `opencode`, `antigravity`) | Yes |
| `transcripts` | Transcript-availability capability (`full` on `claude`, `none` on `opencode`/`antigravity`; unrecognised harness reads as `none`) | Yes |
| `model` | Model identifier as reported by a script-accessible source or self-reported through `--model`; `mixed` when an OpenCode session tree ran more than one, `unknown` when the OpenCode session database could not be read | No |
| `model_source` | `self_reported` (a `--model` flag) or `measured` (a script-readable source) | No |
| `variant` | The OpenCode session tree's variant (e.g. `high`) | No |
| `provider` | The OpenCode session tree's provider id | No |
| `models` | Distinct `id/variant` values of an OpenCode session tree recorded as `mixed` | No |
| `model_type` | Model type as reported by script-accessible sources | No |
| `model_version` | Model version as reported by script-accessible sources | No |
| `effort` | Effort level as reported by a script-accessible source or self-reported through `--effort` | No |
| `effort_source` | `self_reported` (an `--effort` flag) or `measured` (a script-readable source) | No |
| `build_version` | Build version as reported by script-accessible sources | No |

`transcripts: none` is the capability flag a transcript-less harness carries:
its token figures report `unknown` rather than zero (see
`manage-metrics/standards/data-format.md` § unknown vocabulary). The value is
derived from the harness identifier alone — never estimated, and never absent.

`model_type` and `model_version` are never derived from `model`.
Derivation would be estimation. Where script access is hard or strange, an LLM
fallback may fill the gap upstream; the collector itself never estimates.

### The OpenCode model is measured, not self-reported

On OpenCode the model comes from the session record, not from a flag: the
collector reads `session_v2.model` (id, provider, variant) from `opencode.db`
opened read-only, for the plan's root session (`OPENCODE_SESSION_ID` resolved to
its root through `parent_id`) and for every descendant, and records it as
`measured`. A flag never stands in for the record. A tree that ran more than one
model or variant is recorded as `model: mixed` with the distinct values listed —
never averaged and never reduced to the root's value. An absent database, an
unreadable schema or an unresolvable session records `model: unknown`.

Entries are keyed by human-readable UTC datetime stamp
(`YYYY-MM-DD HH-MM-SS UTC`, no colons so the key survives TOON parsing).
Multiple runs append a new timestamped entry instead of overwriting; a repeated
stamp gains a ` (N)` suffix. A legacy flat document migrates under the
`legacy` entry key on first append. Helpers live in `runtime_info.py`:
`format_timestamp_key` formats a stamp, `append_client_entry` merges one run's
attributes into the entries map, and `to_client_toon` renders a single run.

## Success

Full attribute set, when every source is readable:

```toon
status: success
operation: runtime-info
harness: claude
transcripts: full
model: claude-sonnet-4-5
model_source: measured
model_type: chat
model_version: 2026-09-01
effort: standard
effort_source: measured
build_version: "0.1"
```

Best-effort drop, when only the harness and build-version are readable:

```toon
status: success
operation: runtime-info
harness: opencode
transcripts: none
build_version: "0.1"
```

Timestamp-keyed client.toon artifact, after two runs appended:

```toon
schema_version: 1
entries:
  2026-09-15 07-00-00 UTC:
    harness: claude
    transcripts: full
    build_version: "0.1"
  2026-09-15 08-00-00 UTC:
    harness: claude
    transcripts: full
    model: claude-sonnet-4-5
    model_source: measured
    effort: standard
    effort_source: measured
    build_version: "0.1"
```

## Error

Router-level errors reuse the existing codes. An unregistered
`runtime.target` reports `unknown_target`; a missing `.plan/marshal.json`
reports `marshal_not_found`:

```toon
status: error
operation: runtime-info
error: unknown_target
message: "runtime.target 'unknown-platform' is not in the registry; valid targets are: antigravity, claude, opencode"
```

## No-Op

A target that cannot collect runtime information returns `no-op` with a
`reason` and an `alternative` rather than fabricating values:

```toon
status: no-op
operation: runtime-info
reason: no script-accessible source exposes runtime information on this target
alternative: record the client attributes manually
```

## Runtime ABC Contract

`Runtime.runtime_info(model=None, effort=None)` returns a serialized TOON
string; the two keyword arguments carry the executing LLM's self-report and are
optional. Providers read from script-accessible sources through the shared
`runtime_info` collector module and wrap the result with `toon_success`.
No per-target logic lives in the ABC; the collector owns the OpenCode session
measurement.

## Adding a Future Target

1. Add a `Runtime` subclass implementing `runtime_info` via the shared collector.
2. Register it in `platform_runtime._TARGET_RECORDS`.
3. No router change is needed beyond the registry entry.
