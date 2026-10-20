# Runtime-Info Extension Point

Logical extension point for runtime information collection. The `runtime-info`
operation reports the harness/client identifier, the transcript-availability
capability, model name/type/version,
effort level, and the installed bundle and executor version on a best-effort
basis for the `client.toon`
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

One required attribute pair (`harness`, `transcripts`), one further always-present attribute (`harness_source`), and fourteen optional attributes per run entry. Unreadable attributes are absent rather than estimated.

| Key | Meaning | Always present |
|-----|---------|----------------|
| `harness` | Harness identifier (`claude`, `opencode`, `antigravity`) | Yes |
| `transcripts` | Transcript-availability capability (`full` on `claude`, `none` on `opencode`/`antigravity`; unrecognised harness reads as `none`) | Yes |
| `harness_source` | The cascade tier that produced the identifier — `env` (an ambient signal), `local_config` (machine-local harness/run configuration), or `fallback` | Yes |
| `reason` | On the `fallback` tier, WHICH absence it was (`local_config_absent`, `local_config_unreadable`, `local_config_malformed`, `target_absent`) | No |
| `harness_configured` | The target the machine-local configuration names, when it differs from an ambient-tier resolution | No |
| `harness_mismatch` | `true` when the ambient tier and the machine-local configuration name different targets | No |
| `model` | Model identifier as reported by a script-accessible source or self-reported through `--model`; `mixed` when an OpenCode session tree ran more than one, `unknown` when the OpenCode session database could not be read | No |
| `model_source` | `self_reported` (a `--model` flag) or `measured` (a script-readable source) | No |
| `variant` | The OpenCode session tree's variant (e.g. `high`) | No |
| `provider` | The OpenCode session tree's provider id | No |
| `models` | Distinct `id/variant` values of an OpenCode session tree recorded as `mixed` | No |
| `model_type` | Model type as reported by script-accessible sources | No |
| `model_version` | Model version as reported by script-accessible sources | No |
| `effort` | Effort level as reported by a script-accessible source or self-reported through `--effort` | No |
| `effort_source` | `self_reported` (an `--effort` flag) or `measured` (a script-readable source) | No |
| `bundle_version` | The `version` in `.claude-plugin/plugin.json` of the bundle the collector runs from | No |
| `executor_version` | The `MARSHALL_VERSION` of the executor (`plugin_registry.read_executor_version`) | No |

`harness_source` is what keeps a fallback `claude` distinguishable from a
DETECTED `claude`: the same identifier no longer means the same thing, and a
reader that only saw `harness` could not tell them apart. A `fallback` tier names
its own `reason`, so the four distinct fall-through conditions stay separable
downstream. When the ambient tier and the machine-local configuration name
different targets, `harness_configured` carries the configured one and
`harness_mismatch: true` records the disagreement — a stale machine-local
configuration is a fact worth reporting, not a silent loss.

`bundle_version` is the INSTALLED bundle's own manifest version — not the
marketplace manifest's `metadata.version`, which describes the aggregate project
rather than the bundle that is loaded. `executor_version` is read through the
shared `plugin_registry` reader, so the assignment's grammar has one definition;
an absent or unreadable executor omits the key rather than substituting a version.

`transcripts: none` is the capability flag a harness with no WALKABLE transcript
carries. It states which transcript surface is missing — it does not state that
no measurement is possible, because a database-backed source can answer without
a transcript: OpenCode reports `transcripts: none` and still measures its token
figures from its session database. A phase whose figures no measured source
could supply reports `unknown` rather than zero (see
`manage-metrics/standards/data-format.md` § unknown vocabulary). The value is
derived from the harness identifier alone — never estimated, and never absent.

`model_type` and `model_version` are never derived from `model`.
Derivation would be estimation. Where script access is hard or strange, an LLM
fallback may fill the gap upstream; the collector itself never estimates.

### The OpenCode model is measured, not self-reported

On OpenCode the model comes from the session record, not from a flag: the
collector reads `session_v2.model` (id, provider, variant) for the plan's root
session (`OPENCODE_SESSION_ID` resolved to its root through `parent_id`) and for
every descendant, and records it as `measured`. Every read goes through the
shared read-only session reader (`_opencode_sessions`), which owns the database
path, the read-only connection, the schema gate and the tree walk, so the
collector opens no database of its own and needs only the tier-1
`session_v2(id, parent_id, model)` schema. A flag never stands in for the record.
A tree that ran more than one model or variant is recorded as `model: mixed` with
the distinct values listed — never averaged and never reduced to the root's
value. An absent database, an unreadable schema or an unresolvable session
records `model: unknown`.

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
harness_source: env
transcripts: full
model: claude-sonnet-4-5
model_source: measured
model_type: chat
model_version: 2026-09-01
effort: standard
effort_source: measured
bundle_version: 0.1.1919
executor_version: 0.1.1916
```

Best-effort drop, when only the harness and the bundle version are readable:

```toon
status: success
operation: runtime-info
harness: opencode
harness_source: env
transcripts: none
bundle_version: 0.1.1919
```

Fallback tier, with the ambient signal absent and no machine-local configuration:

```toon
status: success
operation: runtime-info
harness: claude
harness_source: fallback
reason: local_config_absent
transcripts: full
```

Timestamp-keyed client.toon artifact, after two runs appended:

```toon
schema_version: 1
entries:
  2026-09-15 07-00-00 UTC:
    harness: claude
    harness_source: local_config
    transcripts: full
    bundle_version: 0.1.1919
  2026-09-15 08-00-00 UTC:
    harness: claude
    harness_source: local_config
    transcripts: full
    model: claude-sonnet-4-5
    model_source: measured
    effort: standard
    effort_source: measured
    bundle_version: 0.1.1919
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
