---
name: manage-build-server
description: Operator control surface for the marshalld build server — enrol/drop a project in the machine-global registry (the opt-in enable signal and anti-laundering wall), manage the daemon lifecycle (start, stop, drain, status, install, upgrade) version-pinned to the verified bundle copy, read/set/migrate the machine-global build-slot cap held in machine-config.json, and inspect the daemon's per-project interaction-audit log (read-only)
user-invocable: true
mode: script-executor
scope: global
---

# Manage Build Server Skill

The operator's control surface for `marshalld`, the machine-global plan-marshall
build server. This skill is `script-deterministic` — every verb is a deterministic
executor script call, no LLM judgement. It owns three responsibilities: **project
enrolment** (the opt-in registry), the **daemon lifecycle** (start/stop/drain/
status/install/upgrade), and the **machine-global build-slot cap** (`config
get`/`set`/`migrate`). Build *consumption* (submit/wait/ping/preflight) lives in
the separate `build-server-client` skill — this skill never submits work.

`marshalld` is strictly opt-in: **registration IS the enable signal.** There is no
config knob that turns the daemon on and nothing git-tracked that does. A project
is served by the daemon only after an operator runs `register` here; an
unregistered project's builds never touch the daemon or its socket and behave
byte-identically to a machine with no build server.

That statement is about the **enable signal** specifically. The build-slot cap DOES
have a machine-wide setting — reached through the `config` verbs below and stored in
the machine-global `machine-config.json` — but it is host state, so still nothing
git-tracked, and it governs how many builds run at once, never whether the daemon
serves a project.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run the control verbs via the executor; parse the TOON output for `status` / `running` and route accordingly.

**Prohibited actions:**
- Do not read, write, or mutate the machine-global `registry.json`, the daemon socket, or the pidfile directly — every mutation goes through the script API so the registry's atomic write + audit-line invariant holds.
- Do not hand-edit the machine-global `machine-config.json` either — `config set` and `config migrate` are its only writers, and they serialize on one `O_EXCL` guard file so `migrate`'s "is the cap unset?" check and its write cannot be separated by a concurrent writer.
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
project's existing registration (executor path inside the verified tree, notation
allowlist, argument schema) and refuses anything off-template. The interpreter is
NOT part of that registration — no registration field holds one. `command[0]` is
checked daemon-wide as an argv shape: against an explicit interpreter pin when the
caller supplies one (exact path or basename), and with no pin — what the shipped
daemon runs — only as a bare canonical `python3` / `python` name carrying no path
separator, so the daemon resolves the binary from its own server-side `PATH`
rather than following a client-supplied location such as `/tmp/x/python3`. That
is defence-in-depth on argv shape; the containment boundary remains the owner-only
socket (`0600` inside a `0700` state dir). The
control surface (enrolment) and the consumption surface (`build-server-client`
submit/wait) are deliberately split across two skills so enrolment can never be
laundered through a build dispatch.

## Default registration scope

`register` populates each project's scope fields so a plain enrolment yields a
routable project rather than an inert empty-scope entry. When `--container` /
`--notation` are omitted, registration stores canonical defaults:

- **`notation_allowlist`** — the routable build notations (Maven, Gradle, npm,
  Python), derived from the single source of truth shared with the daemon's
  build-routing seam, so a build tool that is routable is default-allowlisted
  from the same edit.
- **`worktree_containers`** — the canonical worktree location every plan uses,
  `<root>/.plan/local/worktrees`.

Re-running `register` is the **repair path** for an already-registered project
whose scope is empty: it backfills the missing defaults without hand-editing
`registry.json`. Per-field precedence is explicit CLI value > existing non-empty
stored value > computed default, so re-registration is idempotent — it backfills
empty fields, preserves any deliberately-customised non-empty values, and lets an
explicit `--container` / `--notation` override both the stored value and the
default.

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
| `machine-config.json` | Machine-global build configuration — the build-slot cap's single home (`0600`); written only by `config set` / `config migrate`, serialized on a `machine-config.json.lock` guard |
| `registry-audit.log` | Append-only registration audit |
| `lifecycle-audit.log` | Append-only start/stop/drain/install/upgrade audit |
| `interaction-audit.log` | Append-only per-request interaction audit (`0600`) |
| `journal/` | Durable job specs, results, and ETA history |
| `job-logs/` | Per-job captured build logs |

The **interaction audit** is a central append-only log — the natural third
sibling of `registry-audit.log` and `lifecycle-audit.log` — which answers "who
asked the daemon to do what, and how did it turn out?". It carries two record
kinds, discriminated by an explicit `kind` field:

| `kind` | Written when | Fields |
|--------|--------------|--------|
| `interaction` | Every request the daemon dispatches (`ping` / `submit` / `wait`) | `op`, `project_root`, `plan_id`, `job_id`, `request_status`, `timestamp` (plus a non-secret `reason`) |
| `job_fate` | A job terminalizes — after the journal records its result, and once per job the restart replay forces to `killed` | `job_id`, `fate`, `project_root`, `plan_id`, `timestamp` |

`request_status` is the **request's** response status (e.g. `queued` for an
accepted submit) — it is deliberately not called `outcome`, because it says
nothing about how the job itself ended. `fate` is the **job's** terminal status
(`success` / `failure` / `timeout` / `killed`); a fate the daemon cannot
substantiate is recorded and rendered as `unknown`, never a terminal value and
never `queued`.

The fate is emitted into this log rather than resolved by a read-time join
against the journal because the two stores have deliberately different retention:
terminal journal entries are GC'd after an hour, while audit records are kept for
days. A join could therefore answer the fate question only for the first hour of
a record's life. No record of either kind ever carries a secret-bearing spec
field — a fate record's attribution copies only `project_root` and `plan_id` out
of the stored spec. Retention is bounded and GC'd on every daemon start, parallel
to the journal's bounded-retention model.

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
- **status** — ping the daemon over its socket and report the running version, the
  daemon's in-flight / queued job counts — reported as `unknown` when the daemon
  did not send them (a daemon pinned to a copy predating the counts extension
  omits both keys), **never** coerced to `0`, which would render it as idle —
  the build-slot cap the **running** daemon is applying (`max_slots`) together
  with its `max_slots_source`, both taken from the ping and never re-resolved
  locally (a local resolve answers what a *fresh* daemon would apply, a different
  question), and the binary the **running process** is
  actually executing (`running_binary_path`, read from the live process) alongside
  the resolve-now path a fresh start would launch (`resolved_binary_path`).
  `binary_diverges` flags a stale daemon — one still executing an older pinned copy
  after a plugin-cache bump — and an undeterminable running provenance is reported
  as `unknown`, **never** the resolved-now path (S5, D4). A daemon predating the
  cap-reporting extension sends neither cap field, so both render `unknown`, and a
  degraded source (`invalid` / `unreadable`) additionally gets a
  `max_slots_warning` line naming the fallback being admitted against. Reports
  `down` with a named reason when unreachable. Also reports whether the caller's
  project is registered.
- **install** — idempotent version-pinned start (a no-op when already running).
- **upgrade** — drain the running daemon, then start the verified version (S7).
  Reports the two fields that can carry a **failed** upgrade: `drain_exited`
  (whether the old daemon actually exited within the drain grace window — an
  upgrade with nothing to drain reports `true`) and `already_running` (whether
  the start half found a daemon still up, which for an upgrade is a failure, not
  an idempotent no-op, because the drain was supposed to have removed it).
  Either signal yields `status: error`, so a caller gates on a field that can
  report failure rather than on the word `success`. The failure payload carries
  the full shared error shape — `error` (the machine-readable code) and `message`
  (what failed, in words) per `ref-workflow-architecture/standards/manage-contract.md`
  — alongside the `reason` this verb has always reported, which is retained
  because `reconcile_daemon` reads it. `error` and `reason` always carry the same
  value, drawn from the closed set `drain_did_not_exit` (the old daemon outlived
  the drain grace window) and `already_running_after_drain` (the drain reported a
  clean exit, yet the start half still found a daemon up).

**Crash recovery.** A crashed daemon leaves a stale socket and pidfile; the next
`start` liveness-probes the recorded pid and, finding it dead, cleans the stale
state and binds fresh. A daemon restart replays the journal: terminal results
survive, and any job that was in flight when the daemon died is marked `killed`
(never silently resumed). **Log rotation** is automatic — `daemon.log` rotates to
`daemon.log.1` once it passes its size cap, so daemon logging never grows unbounded.

## The machine-global build-slot cap

`build.queue.max_slots` has exactly one home: the machine-global
`machine-config.json` in the daemon state dir, beside `registry.json`. Both
consumers that must agree resolve it through one shared, **cwd-independent**
function — the daemon's scheduler and the in-process fallback admission
(`plan-marshall:manage-locks:build_queue`) — because both admit against the ONE
machine-global `build-queue.json`. A cap read per caller from that caller's own
repository is a cap two callers can disagree on while contending for the same slots.

Cwd independence is the point, not a side effect: the daemon double-forks and
`chdir('/')`, so a cwd-relative walk-up finds no repository at all, and a per-repo
cap would silently degrade to the default — indistinguishable from a deliberately
configured `5`.

### Every resolution names its source

The cap is never reported as a bare integer, because the value alone cannot
distinguish a configured `5` from a fallback `5`. Every resolution carries a
`max_slots_source` drawn from this closed, total set, plus a `max_slots_detail`
explaining any non-nominal one:

| `max_slots_source` | Meaning | Value applied |
|--------------------|---------|---------------|
| `machine_config` | `build.queue.max_slots` holds a positive int (a `bool` is rejected although it is an `int` subclass) | the configured value |
| `default` | The file or the key is absent — nothing is configured, which is a legitimate state | `5` |
| `invalid` | The key IS present but holds a non-int, a `bool`, or a non-positive int | `5`; `detail` names the offending value |
| `unreadable` | The file exists but could not be read or parsed, or does not hold a JSON object | `5`; `detail` names the error |

`invalid` and `unreadable` are deliberately NOT collapsed into `default`: the file
exists and holds something, so a cap may well be configured there and merely
unreachable or mistyped. `config set` is the verb that repairs either; `config
migrate` refuses on both rather than overwriting one.

### The daemon reports the cap it is applying

`ping` carries `max_slots` and `max_slots_source`, plus `max_slots_detail` when
that source is not `machine_config`. `status` renders those daemon-reported values
and never substitutes a local resolve — a local resolve answers "what would a
*fresh* daemon apply", a different question. Only `status`, `pid` and `version` are
guaranteed on a ping: a daemon pinned to a copy predating the cap fields answers
without them, and both then render `unknown` rather than a plausible substitute.

**The cap is re-resolved per submit.** The daemon resolves it when it starts and
again on every submit, applying the result to its scheduler — so a `config set`
takes effect on the next submitted build with **no restart required**. `config set`
says so in its returned `note`.

### `config migrate` outcomes

`migrate` moves a repository's lingering `build.queue.max_slots` to its
machine-global home in one step. The machine-global write happens FIRST,
deliberately: if the repository edit then fails, the recoverable state is "the value
is machine-wide, the key is still present", which a re-run completes. The reverse
order would delete the operator's only record of the value before it was stored
anywhere.

| `outcome` | `status` | What changed |
|-----------|----------|--------------|
| `nothing_to_migrate` | `success` | Nothing. The repository carries no per-repo key (the `marshal.json` may not exist) |
| `migrated` | `success` | The machine-global side was unset; the value was copied there and the per-repo key removed |
| `removed_duplicate` | `success` | The machine-global side already held the SAME value; only the per-repo key was removed, and `machine-config.json` was left byte-identical |
| `refused` | `error` | **Nothing, on either side** — both files byte-identical. See the reason table below |
| `partial` | `error` | The machine-global side is settled but the `marshal.json` edit did not commit. Re-running converges via `removed_duplicate` |
| `undetermined` | `error` | The machine-global write raised and the state it left could not be established afterwards. Claims **neither** that the migration partly landed **nor** that both files are untouched |

Every `refused` payload reports `machine_config_modified: false` **and**
`marshal_json_modified: false`: a migration that cannot pick a winner must not
leave the operator half-migrated, so it declines rather than choosing.

`undetermined` is the one outcome that reports **neither** modification field.
The machine-global write is not all-or-nothing from the caller's side — the cap
file's `chmod` runs AFTER the atomic replace, so an `OSError` from it arrives
with the migrated cap already on disk. Which side of the replace the failure fell
on is therefore read back, not assumed: the machine side holding this
repository's value is `partial`, a still-unset machine side is `refused`, and
anything else (unreadable, invalid, or a configured cap that is not this
repository's value) is `undetermined`. Sending `false` there would assert the
`refused` both-files-untouched guarantee the caller cannot honour, and `true`
would assert `partial` — so the keys are omitted and the absence is the report.

| `reason` | Why it refuses |
|----------|----------------|
| `values_differ` | The machine-global cap is set and differs from the repository's. Picking a winner is precisely what this verb declines to do, so the report names both values and both paths, plus the two ways out |
| `machine_config_invalid` | The machine-global file holds an invalid cap. It exists and is emphatically not "unset", so copying over it could discard a configured cap — repair it with `config set --max-slots N` first |
| `machine_config_unreadable` | The machine-global file exists but cannot be read or parsed. Same reasoning: not "unset" |
| `per_repo_value_invalid` | The repository's own value is not a positive int (`bool` rejected), so copying it would install a broken cap machine-wide |
| `machine_config_write_failed` | The guarded machine-global write raised AND the re-read shows the machine side still unset, so nothing committed. Its two siblings on the same raise are not refusals: `machine_config_write_failed_after_commit` carries `outcome: partial` (the cap landed, the per-repo key did not go) and `machine_config_state_undetermined` carries `outcome: undetermined` |
| `machine_config_unresolved` | A concurrent writer won the write race, yet the post-state does not resolve to a configured cap — so the repository's key is never removed on the strength of a stale "unset" |

**A key removal leaves an uncommitted edit.** `marshal.json` is git-tracked, so
`migrated` and `removed_duplicate` both leave the working tree dirty; each says so
in its `detail`. Commit the edit. The removal goes through `manage-config`'s own
`load_config` / `save_config` — the writer `manage-providers` and `marshall-steward
upgrade` already use from outside `manage-config` — so the canonical top-level key
order and the concurrent-modification fingerprint guard both apply and no second
`marshal.json` writer is introduced. `max_retries` and every other key in the
`build.queue` block survive, as does the block itself: the demotion is of ONE key,
not of the queue's config. A concurrent edit to `marshal.json` surfaces as
`reason: concurrent_modification` — the guard declining to clobber another writer,
recoverable by re-running.

### A surviving per-repo key is reported, never honoured

A `build.queue.max_slots` sitting in a repository's `marshal.json` never reaches
the admitted cap. `config get` reports it as
`per_repo_max_slots: {value, in_effect: false}`, and every `build_queue acquire`
carries a `per_repo_max_slots_not_in_effect` warning naming the repository path and
its value, the cap actually in effect with its source and path, and the one-step fix
— emitted on every queued build, because a once-off notice is one an operator who
inherited the repository never saw. See [`manage-locks/SKILL.md`](../manage-locks/SKILL.md)
for the queue-side result fields and the separate cap-disagreement report.

## Scripts

**Script**: `plan-marshall:manage-build-server:manage_build_server`

| Verb | Purpose |
|------|---------|
| `register` | Enrol a project in the machine-global registry (the enable signal) |
| `unregister` | Drop a project from the registry |
| `start` | Start the daemon detached, version-pinned |
| `stop` | Force-stop the daemon (`SIGTERM` then `SIGKILL`) |
| `drain` | Gracefully stop the daemon (no `SIGKILL`) |
| `status` | Report running version, in-flight/queued counts (`unknown` when the daemon did not send them — never `0`), the applied build-slot cap with its source (`unknown` for a daemon predating the fields; a degraded source gets a `max_slots_warning`), and running vs resolved binary provenance (divergence flagged; `unknown` never the resolved path) |
| `install` | Idempotent version-pinned start |
| `upgrade` | Drain then start the verified version. Reports `drain_exited` (did the old daemon actually exit?) and `already_running` (did the start find one still up?); when either says the daemon was never replaced it returns `status: error` with `error` + `message` + `reason`, where `error` and `reason` carry the same code (`drain_did_not_exit` or `already_running_after_drain`) |
| `logs` | Read-only, project-scoped view of the daemon's interaction-audit log |
| `config get` | Report the machine-global `max_slots` with its source, detail and path, plus the caller project's per-repo key (`absent`, or its value with `in_effect: false`). Read-only — writes neither file |
| `config set --max-slots N` | Set the machine-global cap. The **unconditional** writer, and therefore the only verb that can repair an `invalid` or `unreadable` machine-config value. A running daemon applies it on its next submit |
| `config migrate` | Move the caller repository's `build.queue.max_slots` machine-wide in one step. Copies the value **only when nothing is set machine-wide**, then removes the per-repo key; when the two values differ it changes **neither** file and reports both. Takes no flags |

**Script**: `plan-marshall:manage-build-server:marshalld` — the daemon binary,
launched by `start` (never invoked directly by an operator).

## Canonical invocations

The canonical argparse surface for `manage_build_server.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section.

### register

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server register \
  [--root ROOT] [--container DIR] [--notation NOTATION]
```

`--container` and `--notation` are repeatable. `--root` defaults to the caller's
main checkout. When `--container` / `--notation` are omitted, registration
populates canonical default scope and re-running `register` backfills an empty
existing entry — see **Default registration scope** above.

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

### logs

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server logs \
  [--root ROOT] [--limit LIMIT]
```

Read-only inspection of the daemon's central `interaction-audit.log`, filtered to
the caller project (the derived project-scoped view) — it never mutates the log.
`--root` defaults to the caller's main checkout; `--limit` returns the N most
recent records (default `50`), ordered oldest-first within the returned window
(so `records[0]` is the oldest of the window, not the newest). When the log is
absent or unreadable the verb returns an explicit empty `records` list with a
named `reason` (`log_absent` / `log_unreadable`; fails closed).

Each returned record is **rendered**, not echoed verbatim, so a per-request row
can never be misread as a job record. Every row leads with its `kind`; an
`interaction` row carries `op`, `job_id`, `project_root`, `plan_id`,
`request_status`, `fate`, `timestamp` (plus `reason` when present), and a
`job_fate` row carries `job_id`, `project_root`, `plan_id`, `fate`, `timestamp`.
On an interaction row the two status columns are distinct: `request_status` is
how the request was answered, and `fate` is the job's outcome, joined by `job_id`
from the job-fate rows in the same log. A job with no fate record yet — and any
row written by an older daemon that predates these field names — renders an
explicit `unknown` rather than a silently missing field, the same fail-closed
discipline as `log_absent` / `log_unreadable`.

### config get / set / migrate

`config` is a two-token verb: the operation is a sub-verb of `config`. Each
sub-verb's **complete** accepted flag set is printed beside it, so a caller never
borrows a sibling's flag — in particular, neither `get` nor `migrate` accepts
`--value`, which belongs to `build_queue limit set`, a different script.

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server config get
```

Accepted flags: **none**.

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server config set \
  --max-slots MAX_SLOTS
```

Accepted flags: `--max-slots` (**required**, a positive integer).

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server config migrate
```

Accepted flags: **none**.

## Related

- `build-server-client` — the build-consumption surface (submit/wait/ping/preflight); this skill never submits work.
- `manage-locks` — the machine-global build-queue slot substrate the daemon's scheduler coordinates against.
- `marshall-steward` — carries a read-only daemon-status pointer into this skill; no daemon logic lives there.
