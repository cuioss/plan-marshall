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
- Never `run_in_background` a daemon-routed build. One runnable rule: the wrapper call for a daemon-routed build returns within a bound below the per-call ceiling with a terminal result or a live running status plus job id, and the orchestrator re-attaches with a bounded wait on that id; backgrounding (`run_in_background`) is named only for the non-daemon fallback, never for a daemon-routed build.
- Do not start, register, unregister, or otherwise provision the daemon from this skill — that surface lives ONLY in `manage-build-server`. This skill never mutates the registry, the socket, the pidfile, or the daemon lifecycle.
- Do not invent script arguments not listed in the **Canonical invocations** section below.
- Do not trust a daemon response without the S3 identity check — the script performs the socket-owner uid check + version handshake; an impostor socket is treated as unreachable (fallback), never trusted.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All script output uses TOON format (see `plan-marshall:ref-toon-format`).
- The entry-point script (`build_server.py`) is invoked only through `python3 .plan/execute-script.py` with the 3-part notation.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## The call model — submit, then bounded long-poll

1. **submit** — the client S3-verifies the daemon (socket-owner uid check +
   version handshake), sends the job spec (the exact executor-form `command`, the
   `exec_path` tree root, the `project_path`, the `plan_id`, and — when the
   caller named one — the explicit `timeout` bound), and on
   acceptance **writes the daemon-assigned `job_id` to the change-ledger**
   (`kind=job`). That ledger row is what lets a rebuilt or harness-reaped session
   RE-ATTACH — `wait` with no `--job-id` recovers the id from the latest `kind=job`
   row for the plan. An unreachable daemon or impostor socket returns
   `degraded(reason=…)`; a verifier rejection returns `refused(reason=…)`.
2. **wait** — ONE server-side bounded long-poll (the caller chooses `--bound`,
   defaulting to the foreground-safe 300s ceiling). The daemon holds the connection up to `bound`
   seconds; on a terminal result it returns the full status-TOON, and on bound
   expiry it returns a LIVE `running` OR `queued` status — the caller re-issues
   `wait`. The wait NEVER returns an empty / timeout-shaped body on bound expiry.

### Both replies name the tree they built

A green result says nothing about WHICH tree it is green for unless the reply
names it, and the daemon's own status payload carries the job's outcome and never
its paths. So both replies carry the three fields a caller compares against the
tree it meant:

| Field | Meaning |
|-------|---------|
| `exec_path` | The submitted tree root the daemon was handed (`--exec-path`, defaulting to `--project-path`). |
| `project_path` | The build working directory the daemon was handed. |
| `plan_id` | The submitting plan, or the `NO_PLAN` sentinel STATED rather than left blank. |

`submit` states them from the job spec it just built. `wait` states the SAME three
by reading the `kind=job` row that submission wrote — the record the client keeps
is the one that knows. A
job whose row cannot be read, or a row written before the path fields existed,
reports no PATH fields: an absent path is honest, a guessed one is not. The plan
id the row itself states is still reported, so a legacy row answers with
`plan_id` and no `exec_path` / `project_path`.

## The status-TOON contract (two hard properties + `killed`)

A `wait` result carries `job_status` — the daemon's own status vocabulary. Two
properties are load-bearing:

- **Bound expiry is a LIVE status, never a timeout.** A `wait` that reaches its
  `bound` without a terminal result returns either `job_status: running` with
  `elapsed` / `eta` / `last_progress`, or — for a job that is accepted but not yet
  admitted — `job_status: queued` with `waiting_on` (the job id, or the identity
  of the in-process holder, it waits for) and `queued_seconds` (how long it has
  waited). A caller can always tell "still working" from "still waiting" from
  "finished", and re-issues `wait` in the first two cases. There is no
  timeout-shaped empty body. A `submit` response carries the same signal at the
  point of submission as `queued_behind`: the id of the job running in the same
  project directory, empty when there is none.
- **`killed` is its own terminal state.** A job whose child was reaped externally
  (harness kill, daemon restart) renders `job_status: killed` with the message
  `externally killed — not flaky, do not blind-retry`. It is NEVER folded into
  `failure`, so the caller never blind-retries a harness kill as if it were a
  flaky build.

Terminal statuses are `success` / `failure` / `timeout` / `killed`; `running` and
`queued` are non-terminal.

A `timeout` or `killed` result additionally names the bound the job was measured
against, when the daemon knows it:

| Field | Meaning |
|-------|---------|
| `timeout_used_seconds` | The bound that was **applied** — never the elapsed time, which is `duration_seconds`. |
| `timeout_source` | Where that bound came from: `daemon_default` (the daemon's own default) or `explicit` (a submit's `--timeout` raised it) for the daemon's own bound; the inner build wrapper's own source (`explicit` / `learned` / `default` / `floor`) when that wrapper reported the non-finish itself. |

Both fields are **absent** when the daemon does not state a bound — a daemon that
predates them, or a job log that carried none. A caller must read an absent bound
as unknown and never substitute `duration_seconds` for it. The vocabulary is
defined once in [`extension-api/standards/build-execution.md`](../extension-api/standards/build-execution.md)
§ "Execution Metadata".

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

Every `submit` and `wait` interaction that reaches the routing decision is logged
to the plan's **work log** — the GLOBAL work log when the submission names no plan
— at a
captured level, through the same `plan_logging` substrate the `manage-logging`
work verb writes through, so no interaction outcome is emitted only at an
uncaptured Python log level: a `degraded` fallback or a `refused` submit stays
visible at the captured threshold. An invocation the verb REFUSES before that
point — an unparseable `--command`, a `wait` with neither a job id nor a
re-attachable ledger row — answers from its own error payload and writes no
interaction entry, because no job was submitted or waited on.

- **Normal outcomes log at INFO.** A queued `submit` acceptance and a `wait`
  result each write one entry carrying the `job_id` — the same id written to the
  change-ledger `kind=job` row, so the work log, the server-side interaction
  audit, and the ledger all correlate on one `job_id`.
- **Every fallback and refusal logs at WARNING.** No `degraded` (fallback) or
  `refused` branch returns without a captured entry naming the `reason`.
- **Every plan-less outcome is traced, not silent.** When no `--plan-id` is
  supplied the submission is recorded under the `NO_PLAN` sentinel (so the ledger
  `kind=job` row is never null), and there is no per-plan work log to write to —
  so `_audit_log` routes every such entry to the GLOBAL work log with
  `plan=NO_PLAN` in the message (a log path cannot carry the plan-less identity).
  That covers queued, degraded and refused submits and the wait outcomes alike,
  so a green main-checkout build leaves a trace beside the plans' own builds. The
  sentinel is truthy, so `_audit_log` tests for it
  explicitly rather than relying on falsiness — it is a routing/ledger value,
  never a plan-directory selector.
- **The build-execute routing seam's own resolution line lands here too.** The
  routing decision (`[BUILD-SERVER] resolved build (requested=…, resolved=routed|in_process|fail-loud, reason=…)`)
  is written to the same work log through the same substrate, at the same
  INFO-normal / WARNING-on-fallback levels, and is ALWAYS mirrored to stderr
  beside `[EXEC]` — the only sink a plan-less build has, because a plan-less
  dispatch owns no plan work log and its line goes to stderr alone. The emitting
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
| `submit` | S3-verify + submit a job; write `job_id` to the ledger; reply names the built tree; `degraded`/`refused` on failure |
| `wait` | One bounded long-poll; terminal, or a live `running`/`queued` status-TOON; reply names the built tree; re-attach via the ledger |
| `ping` | Report the daemon identity (version + pid) or `down` + reason |
| `preflight` | One call: `disabled` \| `ready` \| `down` + reason |

## Canonical invocations

The canonical argparse surface for `build_server.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### build_server — submit

```bash
python3 .plan/execute-script.py plan-marshall:build-server-client:build_server submit \
  --command '["python3", "/tree/.plan/execute-script.py", "NOTATION", "run"]' \
  [--exec-path EXEC_PATH] [--project-path PROJECT_PATH] [--plan-id PLAN_ID] [--timeout TIMEOUT]
```

`--command` is the executor-form argv as a JSON array of strings. `--exec-path`
defaults to `--project-path`; `--project-path` defaults to the current working
directory.

`--timeout` is a wall-clock bound in seconds that can only **raise** the daemon's
supervisory bound — it never lowers it. `marshalld._resolve_job_timeout` resolves
`max(requested + margin, daemon_default)` and reports which of the two produced the
bound (`explicit` only when the request actually raised it, `daemon_default`
otherwise). That is deliberate, not a defect — the inner
child reports a diagnosable timeout instead of losing a race to an opaque outer kill.
When `--timeout` is omitted the job spec carries no bound at all and the daemon applies
its own default.

A **lower** bound therefore takes effect only where something else enforces it. On the
routed leg it does: the routing client rebuilds `command` from its own argv tail (rewriting
only the `--project-dir` value onto the absolute project tree, so the child resolves the
same tree it was named with, and passing every other token through verbatim), so the
same `--timeout N` is a token inside the submitted command and the child re-runs it and
self-bounds. On the direct surface above, `--command` is whatever JSON array the caller
passes, so a lower `--timeout` there bounds nothing unless the caller also puts it in
that array. The value must be a positive integer; `0` and negatives are rejected by the
parser.

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
