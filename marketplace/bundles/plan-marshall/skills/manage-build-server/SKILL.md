---
name: manage-build-server
description: Operator control surface for the marshalld build server — enrol/drop a project in the machine-global registry (the opt-in enable signal and anti-laundering wall) and manage the daemon lifecycle (start, stop, drain, status, install, upgrade), version-pinned to the verified bundle copy
user-invocable: true
mode: script-executor
scope: global
---

# Manage Build Server Skill

The operator's control surface for `marshalld`, the machine-global plan-marshall
build server. This skill is `script-deterministic` — every verb is a deterministic
executor script call, no LLM judgement. It owns two responsibilities: **project
enrolment** (the opt-in registry) and the **daemon lifecycle** (start/stop/drain/
status/install/upgrade). Build *consumption* (submit/wait/ping/preflight) lives in
the separate `build-server-client` skill — this skill never submits work.

`marshalld` is strictly opt-in: **registration IS the enable signal.** There is no
config knob and nothing git-tracked. A project is served by the daemon only after
an operator runs `register` here; an unregistered project's builds never touch the
daemon or its socket and behave byte-identically to a machine with no build server.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run the control verbs via the executor; parse the TOON output for `status` / `running` and route accordingly.

**Prohibited actions:**
- Do not read, write, or mutate the machine-global `registry.json`, the daemon socket, or the pidfile directly — every mutation goes through the script API so the registry's atomic write + audit-line invariant holds.
- Do not invent script arguments not listed in the **Canonical invocations** section below.
- Do not add daemon lifecycle logic to any other skill — this skill is the single owner of start/stop/drain/register/unregister. `marshall-steward` carries a read-only status pointer only.

**Constraints:**
- This skill is **user-invocable ONLY**. It MUST NEVER be resolved into a dispatch's `skills[]` (see the anti-laundering wall below).
- `register` / `unregister` mutate only `registry.json` (plus its audit line) — never source, never `.plan/` plan state.

## The anti-laundering wall (S1)

`register` and `unregister` are the operator-interactivity wall for the build
server. Registration is a deliberate, human-driven enrolment action — so it lives
ONLY in this user-invocable control skill and is NEVER reachable from a dispatched
agent's `skills[]`. A plan cannot enrol itself onto the served set, and the daemon
never *resolves* what to run: it **verifies** every submit positionally against the
project's existing registration (interpreter, executor path inside the verified
tree, notation allowlist, argument schema) and refuses anything off-template. The
control surface (enrolment) and the consumption surface (`build-server-client`
submit/wait) are deliberately split across two skills so enrolment can never be
laundered through a build dispatch.

## Platform constraint (WSL2)

`marshalld` requires a POSIX runtime (Unix domain sockets, `fork`/`setsid`
double-forking, `ppid==1` re-parenting). Supported platforms are macOS and Linux;
on Windows, plan-marshall runs exclusively inside WSL2 with the entire runtime
in-distro. One distro is one machine: each distro has its own `~/.plan-marshall/`,
registry, and daemon, and `wsl --shutdown` / reboot / idle timeout stops the
daemon (a `down` status is routine on Windows — the init preflight re-asks). The
full statement lives in `doc/user/installation.adoc` § Prerequisites — see there,
not duplicated here.

## Daemon state layout

All daemon state lives under the machine-global home root
(`~/.plan-marshall/marshalld/`, overridable via `PLAN_MARSHALL_HOME`), created
`0700`:

| Path | Contents |
|------|----------|
| `socket` | Unix domain socket (`0600`, owner-only) |
| `daemon.pid` | Running daemon pid |
| `daemon.log` | Daemon log (rotated to `daemon.log.1` past a size cap) |
| `registry.json` | Machine-global project registry (`0600`) |
| `registry-audit.log` | Append-only registration audit |
| `lifecycle-audit.log` | Append-only start/stop/drain/install/upgrade audit |
| `journal/` | Durable job specs, results, and ETA history |
| `job-logs/` | Per-job captured build logs |

## Lifecycle operations

- **start** — launch the daemon detached, **version-pinned** to the copy of
  `marshalld` co-located with this control skill (the verified bundle / plugin-cache
  version, never a project-local executor an attacker could tamper with — S5).
  Refuses to launch a second daemon when one is already live (idempotent).
- **stop** (forced kill) — send `SIGTERM`, then escalate to `SIGKILL` after a grace
  window, then remove the socket and pidfile. Use `stop` when the daemon is wedged.
- **drain** (graceful) — request a graceful shutdown (`SIGTERM`) and wait for the
  daemon to exit on its own, never escalating to `SIGKILL`. A job still in flight is
  recorded in the journal and replayed as `killed` on the next start — never
  silently lost, never blind-resumed. Prefer `drain` for planned restarts.
- **status** — ping the daemon over its socket and report the running version +
  binary path (S5), or `down` with a named reason. Also reports whether the caller's
  project is registered.
- **install** — idempotent version-pinned start (a no-op when already running).
- **upgrade** — drain the running daemon, then start the verified version (S7).

**Crash recovery.** A crashed daemon leaves a stale socket and pidfile; the next
`start` liveness-probes the recorded pid and, finding it dead, cleans the stale
state and binds fresh. A daemon restart replays the journal: terminal results
survive, and any job that was in flight when the daemon died is marked `killed`
(never silently resumed). **Log rotation** is automatic — `daemon.log` rotates to
`daemon.log.1` once it passes its size cap, so daemon logging never grows unbounded.

## Scripts

**Script**: `plan-marshall:manage-build-server:manage_build_server`

| Verb | Purpose |
|------|---------|
| `register` | Enrol a project in the machine-global registry (the enable signal) |
| `unregister` | Drop a project from the registry |
| `start` | Start the daemon detached, version-pinned |
| `stop` | Force-stop the daemon (`SIGTERM` then `SIGKILL`) |
| `drain` | Gracefully stop the daemon (no `SIGKILL`) |
| `status` | Report running version + binary path |
| `install` | Idempotent version-pinned start |
| `upgrade` | Drain then start the verified version |

**Script**: `plan-marshall:manage-build-server:marshalld` — the daemon binary,
launched by `start` (never invoked directly by an operator).

## Canonical invocations

The canonical argparse surface for `manage_build_server.py`. The plugin-doctor
analyzer reads this section as source-of-truth for markdown notation occurrences.

### register

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server register \
  [--root ROOT] [--container DIR] [--notation NOTATION]
```

`--container` and `--notation` are repeatable. `--root` defaults to the caller's
main checkout.

### unregister

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server unregister \
  [--root ROOT]
```

### start / stop / drain / status / install / upgrade

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server start
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server stop
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server drain
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server status
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server install
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server upgrade
```

## Related

- `build-server-client` — the build-consumption surface (submit/wait/ping/preflight); this skill never submits work.
- `manage-locks` — the machine-global build-queue slot substrate the daemon's scheduler coordinates against.
- `marshall-steward` — carries a read-only daemon-status pointer into this skill; no daemon logic lives there.
