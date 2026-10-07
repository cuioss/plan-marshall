# marshalld — interaction architecture

**Status: operator-reviewed 2026-07-16 — ready to implement** (not yet built; Rung 2 is gated on
Rung 1). Companion to [`plans/plan-server-core.md`](plans/plan-server-core.md), which holds the
requirements, the security findings (S1–S9), and the rationale for every decision referenced
here. This document is the **structural and interaction view**: who talks to whom, over what, in
which order. The Rung 2 outline consumes both as its implementation inputs and may refine
details, but the decided shape (scope, enablement, call model, security walls, platform) is
settled — deviations need an operator gate, not silent redesign.

---

## 1. Component map

```
┌─ Claude Code session ────────────────────────────┐      ┌─ operator (human) ─┐
│                                                  │      │                    │
│  orchestrator context          leaf contexts     │      │ manage-build-server│
│  (phase skills)                (execution-       │      │ (control skill;    │
│        │                        context-*)       │      │ user-invocable     │
│        │  skills[] loads        │                │      │ ONLY — never in a  │
│        ▼                        ▼                │      │ dispatch skills[]) │
│  ┌──────────────────────────────────────────┐    │      └─────────┬──────────┘
│  │ build-server-client (tiny skill +        │    │                │ interactive verbs:
│  │ executor scripts: submit / wait / ping)  │    │                │ install/upgrade/status
│  └───────────────┬──────────────────────────┘    │                │ start/stop/drain
│                  │ change-ledger: job_id         │                │ REGISTER/UNREGISTER
└──────────────────┼───────────────────────────────┘                ▼
                                                          ┌──────────────────────┐
                                                          │ registration record  │
                                                          │ + daemon lifecycle   │
                                                          └──────────┬───────────┘
                   │ Unix domain socket                              │
                   │ (0600, owner-checked, version handshake)        │
                   ▼                                                 ▼
┌─ marshalld (daemon, ppid=1, double-forked) ─────────────────────────────────────┐
│                                                                                 │
│  ┌────────────┐   ┌───────────────┐   ┌────────────────┐   ┌────────────────┐   │
│  │ VERIFIER   │──▶│ QUEUE /       │──▶│ SUPERVISOR     │──▶│ RESULTS +      │   │
│  │ registry + │   │ SCHEDULER     │   │ (asyncio; one  │   │ JOURNAL        │   │
│  │ template + │   │ (max_slots,   │   │ child process  │   │ (status TOON,  │   │
│  │ path check │   │ per-project   │   │ per job, clean │   │ retention, ETA │   │
│  │            │   │ fairness)     │   │ baseline env)  │   │ history)       │   │
│  └────────────┘   └───────────────┘   └───────┬────────┘   └────────────────┘   │
└───────────────────────────────────────────────┼─────────────────────────────────┘
                                                │ spawns, in the submitted tree
                                                ▼
                                    child: python3 {tree}/.plan/execute-script.py
                                           {notation} {args}   (the build/test run)

~/.plan-marshall/                 (Rung 1 home, 0700)
├── credentials/                  ← deny-rule-guarded; marshalld NEVER reads or forwards
├── marshalld/                    ← sibling subtree, deliberately outside credentials/
│   ├── socket                    (0600)
│   ├── daemon.pid / daemon.log   (rotated, capped)
│   ├── registry.json             (per-project registrations = THE enable signal; control-skill-written only)
│   └── journal/                  (job specs, results, ETA history; GC'd)
└── build-queue.json              (machine-global slot state, if not subsumed by the queue)
```

Roles in one line each:

| Component | Role | Never does |
|---|---|---|
| **client skill + scripts** | resolve command locally (per-tree executor), submit, poll, interpret status TOON, record `job_id` in ledger | background waits, daemon lifecycle, registration |
| **marshalld** | verify → queue → supervise → answer polls; owns the child process | resolve notations, read credentials, accept unregistered/unverified work |
| **manage-build-server** (control skill) | install/upgrade/start/stop/drain/status; **register/unregister** | run builds; enter any dispatch's `skills[]`; get invoked by leaf contexts |
| **marshall-steward** | pointer only — health check may surface daemon status and refer to the control skill | own any daemon logic (deliberately: steward is already too big) |
| **phase-1-init** | registry read; health-check + operator ask when project is registered but daemon down | silent auto-start |
| **change-ledger** | durable `job_id` + terminal `status` per submit | act as the primary legibility surface (the poll response is) |

---

## 2. Interaction flows

### F1 — One-time registration = enablement (per project, operator-run)

```
operator        manage-build-server       marshalld              ~/.plan-marshall/
   │  (control skill, user-  │                      │                      │
   │   invoked)              │                      │                      │
   ├─ register project ─────▶│                      │                      │
   │                         ├─ canonicalize root, worktree container ───▶│ registry.json
   │                         │  + notation allowlist (build/test default) │ (audit line)
   │                         ├─ start daemon? ────▶│ double-fork → ppid=1 │
   │                         │◀── ping: version ───┤                      │
   ▼                         ▼                     ▼                      ▼
```

- **Registration IS the enable signal (decided 2026-07-16)** — there is no config knob anywhere;
  disable = unregister via the control skill. Nothing build-server-related is git-tracked.
- Register/unregister live **only in `manage-build-server`** (user-invocable, operator-interactive,
  never in a dispatch's `skills[]`). This is the anti-laundering wall: no agent context can enroll
  a project or widen an allowlist (S1). `marshall-steward` holds a pointer only — deliberately, it
  is already too big.
- Registered: project **root** + worktree **container** (e.g. `{root}/.plan/local/worktrees/`) —
  never individual worktrees; they are ephemeral and validated dynamically per call (F3).

### F2 — Session init (every plan; ONE script call decides, the LLM only acts on its TOON)

The entire probe is **a single deterministic client-script verb** (`build-server preflight`):
registry read, ping, reason derivation all happen **inside the script**. The LLM never composes
the check sequence — it makes exactly one call and branches on the returned TOON.

```
phase-1-init (LLM)          preflight script (deterministic)         marshalld
     │── one call ──────────────▶│ read registry.json (file)              │
     │                           │   unregistered → stop here             │
     │                           │   registered → ping ──────────────────▶│
     │                           │   derive named reason on any failure   │
     │◀── ONE status TOON ───────┤                                        │
     │
     │  status=disabled      → proceed, no ask ("not registered — builds run in-process")
     │  status=ready         → proceed, no ask (incl. daemon version)
     │  status=down + reason → AskUserQuestion, phrased FROM the TOON's reason:
     │        (a) start now   → control-skill start verb (script) → re-run preflight
     │        (b) continue without → session-scoped fallback flag → in-process builds
     │        (c) unregister  → control-skill verb → status=disabled from now on
```

- **Traceability — EVERY outcome, no exceptions:** each preflight result (`disabled`, `ready`,
  `down`+`reason`) AND, on `down`, the operator's chosen resolution emits **one console line and
  one `decision.log` entry**. The routing decision "who runs this plan's builds" must be visible
  live and reconstructable in retrospectives — this failure class stayed invisible for 23 days
  precisely because outcomes left no artifact trace.
- **Script-based is vital here:** the TOON is the contract; the LLM acts on `status`/`reason`,
  never on its own probing. This keeps init cheap for the 99% path (`disabled`/`ready` = one call,
  no ask) and makes the gate's behavior testable without a model in the loop.

- The gate never blocks the start path on a condition starting would resolve (stale socket,
  dead pidfile) — the named `reason` decides what the ask offers (gate anti-pattern, evidenced).

### F3 — Submit (the verify-not-resolve pipeline)

```
leaf/orchestrator        client script                    marshalld VERIFIER
     │ architecture resolve → exact executor-form command
     │──────────────────────────▶│ submit {command, exec_path, project_path, plan_id}
     │                           │────────────────────────────▶│
     │                           │              1 project_path ∈ registry (canonical)?
     │                           │              2 exec_path == root, OR live linked worktree:
     │                           │                under registered container AND
     │                           │                git-common-dir → registered root?
     │                           │              3 argv template: interpreter == baseline;
     │                           │                argv[1] == {exec_path}/.plan/execute-script.py;
     │                           │                notation ∈ allowlist; args schema-valid?
     │                           │              4 fingerprint(plan_id+notation+args+tree) —
     │                           │                identical in-flight job? → ATTACH (no dup run)
     │                           │◀─ job_id, queued|running, eta_seconds, queue_position ──┤
     │◀── TOON ──────────────────┤
     │ ledger row: {job_id, plan_id, notation, status=submitted}     ← re-attach anchor (F6)
```

Any check failing ⇒ `refused(reason=…)`, logged daemon-side, never partially executed.

### F4 — The poll loop (steady state)

```
client                                      marshalld
  │ wait --job-id X --max-seconds min(eta,300)   │        foreground Bash call,
  │─────────────────────────────────────────────▶│        timeout=(max+60)s
  │            (server-side block until terminal OR bound)
  │◀─ running: elapsed / eta / last_progress ────┤  ← bound expiry: NEVER empty,
  │   … re-issue wait (loop) …                   │    never timeout-shaped (#909)
  │◀─ terminal: success|failure|timeout|killed ──┤
  │   + errors[]/log_file/duration (wrapper shape)
  │   killed ⇒ "externally killed — not flaky,   │
  │             do not blind-retry"              │  ← anti-normalization (#572)
  │ ledger row updated: terminal status          │
```

### F5 — The core scenario: the wait dies, the work survives

```
harness reaper           client wait call         marshalld          child build
     │── kills the wait ──▶ ✝ (foreground call     │ unaffected        │ unaffected
     │                        or its context)      │                   │ keeps running
     │                                             │                   │
next turn / notification handler:                  │                   │
     │ re-issue wait --job-id X ──────────────────▶│                   │
     │◀─ running (elapsed/eta/progress) … or terminal result ──────────┤
```

Cost of a kill: **one re-issued poll.** No build minutes lost, no blind retry, no 0-byte file.

### F6 — Context loss / second session re-attach

```
rebuilt session: ledger read → job_id → wait --job-id X → current status
```

The submit-time ledger row is the durable anchor; results are re-readable within the retention
window (`status=not_found` after it — the client skill says what to do then: re-submit, which
either attaches (F3 step 4) or starts fresh).

### F7 — Daemon unreachable (fallback)

```
client: connect fails / owner check fails / handshake refused
   → TOON: degraded(reason=…)
   → call site runs today's in-process foreground path
   → ledger row records the degradation (never silent)      [S9: accepted fail-open]
```

Impostor socket (wrong owner uid, failed handshake) is treated as *unreachable*, never trusted —
forged results must not reach freshness/triage gates (S3).

### F8 — Upgrade / shutdown (control-skill-only)

```
manage-build-server: drain → daemon stops accepting submits, finishes running jobs,
         answers waits until drained → stop → install new version → start → ping
version-skewed client meanwhile: handshake refuses
         (reason=version_skew → manage-build-server upgrade)
```

---

## 3. Job state machine

```
                    ┌──────────┐  slot free   ┌─────────┐
 submit(verified) ─▶│  queued  │─────────────▶│ running │
                    └────┬─────┘              └────┬────┘
        attach ──────────┘ ▲                       │
        (idempotent)       │            ┌──────────┼──────────┬────────────┐
                           │            ▼          ▼          ▼            ▼
                           │       ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐
                           │       │ success │ │ failure │ │ timeout │ │ killed │
                           │       └─────────┘ └─────────┘ └─────────┘ └────────┘
                           │            └──────────┴─────┬────┴────────────┘
                           │                     retention window, then GC
                           └──── not_found ◀─────────────┘
```

`killed` here means the daemon's **child** died externally (machine shutdown, manual kill) — the
harness reaper cannot reach it (ppid=1, proven). It is a distinct terminal state so the poll
response stays three-way unambiguous: job-died / job-running / job-done.

---

## 4. Deliberately absent from this architecture

| Absent | Why (pointer) |
|---|---|
| A config knob (`marshal.json` / `run-configuration.json`) | registration is the single enable signal; disable = unregister (plan doc § Optionality) |
| A native-Windows implementation | Windows is supported via the **WSL2 requirement**: the entire runtime (repos, builds, session, daemon) lives in the distro, where the POSIX design runs unchanged; mixed native/WSL mode is explicitly unsupported (plan doc § Technology) |
| Any wake/push channel into a session | not achievable; no-dormancy ground rule (README) |
| CI-wait job kind | fails the scope criterion — provider-side work, nothing local to preserve (plan doc § Target) |
| Server-side notation resolution | executor is per-tree derived state (ADR-002); daemon verifies, never resolves (S1) |
| MCP as the protocol | leaves have no MCP tools; optional facade later at most (plan doc § Technology) |
| Docker / JVM | host-env fidelity + reuse of Python build-wrapper contract (plan doc § Technology) |
| Credentials access in the daemon | secrets never cross the socket or job env (S4) |
| A finalize-cost story | ceremony idle is a different problem with a different owner (plan doc § Target) |

## Lifecycle

Operator-reviewed 2026-07-16 — on Rung 2 plan creation this document moves with
`plan-server-core.md` into the plan directory as an implementation input; the outline may refine
details but escalates deviations from the decided shape to an operator gate. **End state (plan
documentation tasks 4+6):** the as-built version is converted to AsciiDoc as
`doc/developer/build-architecture.adoc` (developer altitude) and seeds
`doc/concepts/build-server.adoc` (concept altitude); this markdown source is then archived with
the plan, not left as a live duplicate. After archive: update the epic README's layout table.
