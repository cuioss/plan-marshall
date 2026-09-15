# Runtime-Info Extension Point

Logical extension point for runtime information collection. The `runtime-info`
operation reports the harness/client identifier, model name/type/version,
effort level, and build-version on a best-effort basis for the `client.toon`
pre-flight artifact.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Scope

Concrete providers exist for `claude` and `opencode` only. `antigravity` is an
example harness value in documentation and test vectors, never a registered
runtime target.

## CLI Shape

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime runtime-info
```

Takes no arguments. Routing is config-driven via `runtime.target` in
`.plan/marshal.json`; an unregistered target yields the established
`unknown_target` error path.

## Client.toon Schema

One required attribute (`harness`) and five optional attributes per run entry. Unreadable attributes are absent rather than estimated.

| Key | Meaning | Always present |
|-----|---------|----------------|
| `harness` | Harness identifier (`claude`, `opencode`) | Yes |
| `model_name` | Model name as reported by script-accessible sources | No |
| `model_type` | Model type as reported by script-accessible sources | No |
| `model_version` | Model version as reported by script-accessible sources | No |
| `effort` | Effort level as reported by script-accessible sources | No |
| `build_version` | Build version as reported by script-accessible sources | No |

`model_type` and `model_version` are never derived from `model_name`.
Derivation would be estimation. Where script access is hard or strange, an LLM
fallback may fill the gap upstream; the collector itself never estimates.

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
model_name: claude-sonnet-4-5
model_type: chat
model_version: 2026-09-01
effort: standard
build_version: "0.1"
```

Best-effort drop, when only the harness and build-version are readable:

```toon
status: success
operation: runtime-info
harness: claude
build_version: "0.1"
```

Timestamp-keyed client.toon artifact, after two runs appended:

```toon
schema_version: 1
entries:
  2026-09-15 07-00-00 UTC:
    harness: claude
    build_version: "0.1"
  2026-09-15 08-00-00 UTC:
    harness: claude
    model_name: claude-sonnet-4-5
    effort: standard
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
message: "runtime.target 'antigravity' is not in the registry; valid targets are: claude, opencode"
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

`Runtime.runtime_info` takes no arguments and returns a serialized TOON
string. Providers read from script-accessible sources through the shared
`runtime_info` collector module and wrap the result with `toon_success`.
No per-target logic lives in the ABC or the collector.

## Adding a Future Target

1. Add a `Runtime` subclass implementing `runtime_info` via the shared collector.
2. Register it in `platform_runtime._TARGET_RECORDS`.
3. No router change is needed beyond the registry entry.
