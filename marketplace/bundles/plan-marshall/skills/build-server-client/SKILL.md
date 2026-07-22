---
name: build-server-client
description: The tiny build-consumption client for the marshalld build server — submit a build job, bounded long-poll for its result, ping the daemon identity, and preflight registry-plus-liveness in one call; consumption only, never provisioning or enrolment
user-invocable: false
mode: script-executor
scope: global
---

# Build Server Client Skill

The **consumption** surface for `marshalld`, the machine-global plan-marshall
build server. A build-dispatching context loads this skill to hand a build to the
daemon and long-poll for its result; enrolment and daemon lifecycle live in the
separate user-invocable `manage-build-server` control skill (the anti-laundering
wall). This skill is `script-deterministic` — every verb is a deterministic
executor call, no LLM judgement, no logic in this prose the script does not
enforce.

The client is deliberately tiny and **fail-soft**: when the daemon is down,
unregistered, or an impostor owns the socket, `submit` returns `degraded` and the
caller falls back to an in-process build. A build against a machine with no daemon,
or an unregistered project, behaves byte-identically to today.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run the verbs via the executor; parse the TOON output (`status`, `job_status`, `preflight`, `daemon`, `reason`) and route accordingly.

**Prohibited actions:**
- Never `run_in_background` or `sleep` the `wait`. The wait is a foreground, server-side bounded long-poll — a harness-reaped wait costs ONE re-poll (re-issue `wait`), never the whole build. Backgrounding it re-introduces exactly the harness-kill loss the daemon exists to remove.
- Do not start, register, unregister, or otherwise provision the daemon from this skill — that surface lives ONLY in `manage-build-server`. This skill never mutates the registry, the socket, the pidfile, or the daemon lifecycle.
- Do not invent script arguments not listed in the **Canonical invocations** section below.
- Do not trust a daemon response without the S3 identity check — the script performs the socket-owner uid check + version handshake; an impostor socket is treated as unreachable (fallback), never trusted.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All script output uses TOON format (see `plan-marshall:ref-toon-format`).
- The entry-point script (`build_server.py`) is invoked only through `python3 .plan/execute-script.py` with the 3-part notation.

## The call model — submit, then bounded long-poll

1. **submit** — the client S3-verifies the daemon (socket-owner uid check +
   version handshake), sends the job spec (the exact executor-form `command`, the
   `exec_path` tree root, the `project_path`, and the `plan_id`), and on
   acceptance **writes the daemon-assigned `job_id` to the change-ledger**
   (`kind=job`). That ledger row is what lets a rebuilt or harness-reaped session
   RE-ATTACH — `wait` with no `--job-id` recovers the id from the latest `kind=job`
   row for the plan. An unreachable daemon or impostor socket returns
   `degraded(reason=…)`; a verifier rejection returns `refused(reason=…)`.
2. **wait** — ONE server-side bounded long-poll (the caller chooses `--bound`,
   defaulting to the foreground-safe 300s ceiling). The daemon holds the connection up to `bound`
   seconds; on a terminal result it returns the full status-TOON, and on bound
   expiry it returns a LIVE `running` status — the caller re-issues `wait`. The
   wait NEVER returns an empty / timeout-shaped body on bound expiry.

## The status-TOON contract (two hard properties + `killed`)

A `wait` result carries `job_status` — the daemon's own status vocabulary. Two
properties are load-bearing:

- **Bound expiry is a live `running` status, never a timeout.** A `wait` that
  reaches its `bound` without a terminal result returns `job_status: running` with
  `elapsed` / `eta` / `last_progress` — a caller can always tell "still working"
  from "finished", and re-issues `wait`. There is no timeout-shaped empty body.
- **`killed` is its own terminal state.** A job whose child was reaped externally
  (harness kill, daemon restart) renders `job_status: killed` with the message
  `externally killed — not flaky, do not blind-retry`. It is NEVER folded into
  `failure`, so the caller never blind-retries a harness kill as if it were a
  flaky build.

Terminal statuses are `success` / `failure` / `timeout` / `killed`; `running` and
`queued` are non-terminal.

## Fallback semantics

`submit` is fail-soft. Every reason that prevents reaching a trusted daemon is a
`degraded` return with a named `reason` and `fallback: in_process`, so the caller
falls back to an in-process build (and records the degradation) rather than
failing the build:

| `reason` | Meaning |
|----------|---------|
| `socket_absent` | No socket — the daemon is down. |
| `impostor_socket` | The socket is owned by another uid (S3) — untrusted, treated as down. |
| `unreachable` | Connect / I/O failed, or a malformed response frame. |
| `version_mismatch` | The daemon answered a different protocol version. |
| `handshake_failed` | The daemon did not answer a clean `ping`. |

## Interaction audit logging (non-silent)

Every `submit` and `wait` interaction is logged to the **plan work log** at a
captured level, through the same `plan_logging` substrate the `manage-logging`
work verb writes through — so no interaction outcome is emitted only at an
uncaptured Python log level and silently lost. This closes the field-observed
defect class where a `degraded` fallback or a `refused` submit vanished because
it surfaced only below the captured threshold.

- **Normal outcomes log at INFO.** A queued `submit` acceptance and a `wait`
  result each write one entry carrying the `job_id` — the same id written to the
  change-ledger `kind=job` row, so the work log, the server-side interaction
  audit, and the ledger all correlate on one `job_id`.
- **Every fallback and refusal logs at WARNING.** No `degraded` (fallback) or
  `refused` branch returns without a captured entry naming the `reason`.
- **Plan-less builds are silent by design.** When no `--plan-id` is supplied
  there is no per-plan work log to write to, so the logging is a no-op.
- **The build-execute routing seam's own resolution line lands here too.** The
  routing decision (`[BUILD-SERVER] resolved build (requested=…, resolved=routed|in_process|fail-loud, reason=…)`)
  is written to the same plan work log through the same substrate, at the same
  INFO-normal / WARNING-on-fallback levels, and is additionally mirrored to
  stderr beside `[EXEC]` so a plan-less build stays observable. The emitting
  module is `script-shared/scripts/build/_build_execute_factory.py` — see it for
  the format string and the level rule (not restated here).
- **Secrets discipline.** A logged entry carries ONLY non-secret correlation
  fields — `job_id` / `job_status` / `reason` / `notation` / `attached` /
  `elapsed` / `eta`. It NEVER contains the raw `--command` argv, `exec_path` /
  `project_path`, env, or any spec field that may carry secrets.

## Preflight (F2) — one deterministic call

`preflight` is the single call the init phase branches on. It returns exactly one
of three outcomes, doing NO daemon round-trip when the project is unregistered:

- `disabled` — the project is not registered; the build server is off for this
  project (no socket is touched).
- `ready` — the project is registered AND a verified handshake succeeded.
- `down` — the project is registered but the daemon is unreachable; carries the
  named `reason` (same vocabulary as the fallback table).

## Scripts

**Script**: `plan-marshall:build-server-client:build_server`

| Verb | Purpose |
|------|---------|
| `submit` | S3-verify + submit a job; write `job_id` to the ledger; `degraded`/`refused` on failure |
| `wait` | One bounded long-poll; terminal or live `running` status-TOON; re-attach via the ledger |
| `ping` | Report the daemon identity (version + pid) or `down` + reason |
| `preflight` | One call: `disabled` \| `ready` \| `down` + reason |

## Canonical invocations

The canonical argparse surface for `build_server.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for the
`manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### build_server — submit

```bash
python3 .plan/execute-script.py plan-marshall:build-server-client:build_server submit \
  --command '["python3", "/tree/.plan/execute-script.py", "NOTATION", "run"]' \
  [--exec-path EXEC_PATH] [--project-path PROJECT_PATH] [--plan-id PLAN_ID]
```

`--command` is the executor-form argv as a JSON array of strings. `--exec-path`
defaults to `--project-path`; `--project-path` defaults to the current working
directory.

### build_server — wait

```bash
python3 .plan/execute-script.py plan-marshall:build-server-client:build_server wait \
  [--job-id JOB_ID] [--plan-id PLAN_ID] [--bound BOUND]
```

With no `--job-id`, the verb re-attaches via the latest `kind=job` ledger row for
`--plan-id`. `--bound` defaults to 300 seconds.

### build_server — ping

```bash
python3 .plan/execute-script.py plan-marshall:build-server-client:build_server ping
```

### build_server — preflight

```bash
python3 .plan/execute-script.py plan-marshall:build-server-client:build_server preflight \
  [--project-path PROJECT_PATH]
```

## Related

- `manage-build-server` — the operator control surface (enrol/drop a project, daemon lifecycle); this client never provisions.
- `manage-change-ledger` — the append-only ledger this client writes `kind=job` re-attach rows to at submit time.
- `manage-locks` — the machine-global build-queue slot substrate the daemon and the in-process fallback share.
