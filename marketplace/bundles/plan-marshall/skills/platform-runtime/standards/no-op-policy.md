# No-Op Policy

When a target cannot implement an operation, `platform-runtime` returns `status: no-op`.

The calling skill MUST treat `no-op` as a normal continuation signal — not an error. A workflow that fails because a display hook is unsupported is a defect.

## TOON Shape

```toon
status: no-op
operation: <name>
reason: <why the target cannot perform this operation>
alternative: <what the caller can do instead>
```

`no-op` responses never carry `result`, `error`, or `message` fields. The `reason` and `alternative` fields are always present.

## Caller Obligations

When parsing a response from `platform-runtime`:

1. **Check `status` first.** A `status: no-op` response is not a failure — do not branch to an error handler.
2. **Log the `reason` at INFO level.** The reason string is human-readable and useful for diagnostics.
3. **Apply the `alternative` if the step is required.** If the workflow requires a result that the target cannot provide, use the `alternative` field to guide the fallback.
4. **Continue the workflow.** Never exit, halt, or mark a task `blocked` solely because a `no-op` was returned.

The `alternative` field is advisory — it names what the caller can do instead. It is not a command and does not require the caller to take any specific action if the step is optional.

## Worked Examples

### `session capture` on OpenCode

OpenCode does not expose a platform-provided session id to the shell environment. The operation always returns:

```toon
status: no-op
operation: session capture
reason: OpenCode does not expose a platform-provided session id to the shell; tracked upstream at issue #9292
alternative: pass --total-tokens manually to metrics capture
```

The calling skill MUST continue. Where automatic token capture was expected, the caller falls back to accepting a `--total-tokens` argument from the user.

### `session render-title` on OpenCode

The terminal-title renderer requires a platform-provided session id to locate the active plan. On OpenCode the session id is unavailable:

```toon
status: no-op
operation: session render-title
reason: OpenCode has no plugin-driven terminal-title hook (issue anomalyco/opencode#8619)
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

A target that RENDERS the title itself does not answer this way when a
precondition is unmet — and it is the one operation that does not. It owns
stdout, so it returns the empty string on every path and reports its outcome on
a side channel instead; on Claude that is an `outcome:` row written to stderr
(`outcome: no_session_id` for the case above). There is no `no-op` TOON on
stdout to read, which is why a caller cannot distinguish rendered, nothing-to-
render, and render-failed from the return value. See `contract.md`
§ `session render-title`.

The `no-op` block above is therefore what a target that DECLINES the operation
returns, and the distinction matters: declining is the general policy this
document describes, while owning stdout is one operation's documented exception
to it.

In every `no-op` case the calling skill continues and the terminal title is
simply absent.

### `metrics capture` when session data is missing

`metrics capture` returns `no-op` on OpenCode (no session id available) and may return `no-op` on Claude Code when the session id is present but the transcript contains no usage data for the requested phase:

```toon
status: no-op
operation: metrics capture
reason: Session ID found but transcript/DB query returned no usage data for this phase
alternative: Pass --total-tokens manually
```

The calling skill MUST continue. Metrics are recorded on a best-effort basis — an absent capture does not block phase completion.

## Distinguishing `no-op` from `error`

`no-op` means the target has determined the operation does not apply in this environment. `error` means the operation was attempted and failed.

| Situation | Status |
|-----------|--------|
| OpenCode returns for a Claude-only operation | `no-op` |
| `session capture` cannot find the env var (hook not installed) | `error` (code: `hook_not_configured`) |
| `marshal.json` is missing | `error` (code: `marshal_not_found`) |
| Agent uses unmapped tool (e.g., `SendMessage`) | `no-op` |
| `platform_runtime.py` cannot parse CLI arguments | `error` |

The key distinction: **if the target decided not to act because the environment does not support the operation, it is `no-op`; if the target tried and encountered a problem, it is `error`.**

## Cross-References

- `standards/contract.md` — per-operation TOON schemas listing which statuses each operation can return
- `SKILL.md` — No-Op Behavior section
