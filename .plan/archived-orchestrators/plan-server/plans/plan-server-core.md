# Plan — Rung 2: `marshalld`, the plan-marshall build server

**Command:** `/plan-marshall task="implement .plan/local/orchestrator/plan-server/plans/plan-server-core.md"`
**Status:** queued, **design complete — operator-reviewed 2026-07-16, ready to implement**
(this doc + [`../architecture.md`](../architecture.md) are the implementation inputs) —
**Rung 2** of the Orchestrator epic ([`../00-README.md`](../00-README.md)).
**UNGATED — Rung 1 shipped as PR #923 (2026-07-17,
`.plan/local/archived-plans/2026-07-17-plan-global-home-root/`):** `~/.plan-marshall/` exists
(`home_root()`/`ensure_home_root()` in `marketplace_paths.py`, 0o700, env override
`PLAN_MARSHALL_HOME`, ADR-008), the build queue is machine-global with per-entry `project_root`
stamping, and `holder_is_dead` is project-qualified — everything the daemon needs for its endpoint
and queue. **At outline, read the shipped Rung 1 surface, not this doc's pre-#923 assumptions**;
also verify the old `plan_id=null` queue-bypass is closed in the rewritten `build_queue.py`.
(The former experiment gate is resolved: buildable, with the double-fork constraint below. Evidence:
[`../background-build-kill-forensics.md`](../background-build-kill-forensics.md) § "The setsid /
daemonization experiment".)

**Lane/posture:** `deep` / `full`. DESIGN-FIRST — this is the project's first long-lived process.
Expect the outline to do real design work, including an honest re-evaluation of whether
`plan-background-build-kill`'s mitigations alone already reduce the pain enough.
**Surface:** new `marshalld` component + its **tiny client skill**; `manage-locks/build_queue.py`;
`script-shared/scripts/build/*`; `plan-marshall/workflow/await-long-running.md`;
`phase-1-init` (registry read + health-check + ask-to-start); new **control skill**
`manage-build-server` (provisioning, lifecycle, register/unregister — deliberately NOT
marshall-steward, which is already too big; steward gets a pointer only).

## Target

A single machine-level daemon — working name **`marshalld`** (provisional) — that **owns
build-class work**: builds and test runs, on behalf of every plan-marshall session on the machine,
across all projects. Sessions submit a job and poll for its result with cheap bounded calls; they
never hold the work. The wait and the work are separate processes, so a reaped wait costs one
re-poll, not the build.

**Scope criterion (settled 2026-07-16; outline confirms, does not rediscover):** a job belongs in
marshalld **iff killing its waiter destroys local work, or the job contends for local CPU.**
Builds and test runs pass both tests. **CI waits pass neither** — the work runs provider-side, so a
killed watcher costs one re-issued poll, and the existing bounded `ci:wait` primitives already
handle that correctly. **CI waiting stays on those primitives and is NOT a marshalld job kind.**
This is a build server, not a general async runner; anything new must pass the criterion.

**IS NOT a wake mechanism.** The no-dormancy ground rule ([`../00-README.md`](../00-README.md)
§ "Design ground rules") is settled: the session stays live and polls. The daemon's value is on the
*who-owns-the-process* axis (work-preservation + cross-project coordination), not on the wake edge
and not on token savings.

**IS NOT a finalize-cost fix.** Finalize idle is ceremony — merge-queue waits, review round-trips,
operator parking — none of which a work-owning server moves (counter-case on record: an 8h25m
finalize whose idle was a polling-window misread plus overnight parking, zero harness kills). An
outline that starts claiming finalize-idle savings has drifted off-thesis; cut that scope.

**IS NOT a general execution service.** See the security model below: the daemon executes only
executor-form commands that verify against a registered project (template + notation allowlist +
registered paths) — arbitrary commands are refused regardless of who submits.

## Optionality model (DECIDED 2026-07-16 — registration is the single enable signal)

The server is **strictly opt-in** ([[feedback_infra_steps_must_be_opt_in]]), with **one** source of
truth:

- **Registration IS enablement — there is no config knob**, not in `marshal.json`, not in
  `run-configuration.json`. A project uses the build server **iff it is registered with the
  daemon**. Unregistered ⇒ zero behavior change: no probe, no socket, no new hot-path code.
  Disabling = unregister via the control skill; if "registered but temporarily off" ever proves
  needed, that is a control-skill-set pause flag **on the registration record** (daemon-side
  state), never repo config. **Nothing about the build server is git-tracked.**
- **The registration record (one-time, operator-run via the control skill):** canonical project
  root + worktree container path(s) (e.g. `{root}/.plan/local/worktrees/`) + allowed notation set
  (defaults to the build/test job kinds), stored under `~/.plan-marshall/` (0700). It is both the
  enable signal AND what the daemon verifies **every** submit against. **The wall is
  operator-interactivity:** register/unregister live in `manage-build-server`, which is
  user-invocable only and is NEVER resolved into an execution-context dispatch's `skills[]` — an
  agent context cannot silently enroll a project into the execution surface. **Containers, not
  individual worktrees** — plan worktrees are ephemeral; the per-call check is dynamic (submitted
  path == registered root, OR a live linked worktree whose `git-common-dir` resolves to a
  registered root, under a registered container). Unregistered project ⇒
  `refused(reason=not_registered)` with a pointer to the control skill.
- **Init-phase contract (phase-1-init) — ONE deterministic script call; the LLM only acts on its
  TOON.** A single `preflight` verb does everything inside the script: registry file read (cheap,
  no daemon round-trip; unregistered → `status=disabled`, stop), then ping, then named-reason
  derivation on any failure — returning **one status TOON** (`disabled|ready|down+reason`). The
  LLM never composes the probe sequence; it branches on the TOON: `disabled`/`ready` → proceed
  with no ask; `down` → `AskUserQuestion` phrased from the TOON's `reason`. **Traceability rule —
  EVERY outcome:** each preflight result (`disabled`, `ready`, `down`+`reason`) and, on `down`,
  the chosen resolution emits one console line + one `decision.log` entry ("who runs this plan's
  builds" must be live-visible and reconstructable in retrospectives — this failure class stayed
  invisible for 23 days precisely because outcomes left no artifact trace). The 99% path stays
  one call. The `down` options: **(a)** start now (control-skill start verb → re-run preflight), **(b)**
  continue this plan without it (in-process fallback for this session), **(c)** unregister (via
  the control skill). Never auto-start silently — a process that executes builds does not appear
  on the machine without an explicit yes. Script-based is vital: the gate stays testable without
  a model in the loop.
  **Gate anti-pattern (evidenced — a strict ci-complete gate once deadlocked the only step able to
  fix the red it gated on):** the health-check gate must never refuse to start the daemon for a
  condition that *starting the daemon would resolve* (stale socket file, dead-but-locked pidfile,
  version-skewed leftover). The gate's predicate must **name the reason** in its TOON
  (`reason=not_running|stale_socket|version_skew|refused_...`), not return a bare boolean — the
  ask presented to the operator is phrased from that reason, and only reasons the daemon cannot
  self-resolve may block the start path.
- **Control home: the dedicated `manage-build-server` skill (decided 2026-07-16 — NOT
  marshall-steward, which is already too big).** It owns the full control surface: install,
  upgrade, start/stop/drain, status, register/unregister. User-invocable only; never enters an
  execution-context dispatch. `marshall-steward` gets a pointer only (its health check may surface
  daemon status and refer to the skill) — no daemon logic inside steward. This mirrors the
  client/control split: `build-server-client` teaches consumption, `manage-build-server` owns
  operations, and neither can do the other's job.
- **Fallback:** every submitting call site must degrade to today's in-process path when the daemon
  is unreachable mid-plan; the failure is recorded (ledger `status`), not silently retried.

## Call model (the operator's sketch, worked through — outline refines, does not discard)

```
session ──submit(command, exec_path, project_path)──▶ marshalld ──▶ job_id + ETA (learned)
session ──wait(job_id, max=300s)──▶ blocks (foreground, bounded) ──▶ status TOON
   ▲                                                                    │
   └──────────── re-issue wait while status=running ◀──────────────────┘
```

1. **Submit:** `build-server submit` hands the daemon a job spec of exactly three parts —
   **the exact command in executor form** (`python3 {tree}/.plan/execute-script.py {notation}
   {args}`, as the client already resolved it via `architecture resolve`), **the execution path**
   (usually the plan worktree), and **the project path** (the registered root) — plus the
   `plan_id`. It returns **immediately** with a TOON: `job_id`, `status: queued|running`,
   `eta_seconds` (from learned durations — `run-configuration.json` history is the seed),
   `queue_position` if queued.
   **The daemon does not resolve — it VERIFIES** every part against the project's registration
   (S1/S2 below): project path registered, execution path live under it, command matching the
   executor template + notation allowlist. Client-side resolution is deliberate: the executor is
   per-tree derived state (ADR-002), so the submitting tree's own executor is the only correct
   one — a server-side resolver would duplicate that machinery and re-open version skew.
   **The `job_id` is written to the change-ledger at submit time** — so any later context (or a
   rebuilt session after a context loss) can re-attach to the job from plan artifacts alone.
2. **Wait:** `build-server wait --job-id X --max-seconds 300` — a **foreground, bounded
   long-poll**. The script blocks server-side until the job reaches a terminal state OR the bound
   expires, then returns a status TOON either way. Wait bound = `min(eta_remaining, 300)`, floor
   ~30 s. The 5-min cap keeps every call safely inside foreground Bash limits (pass
   `timeout: (max+60)*1000` on the Bash call) and far away from the background primitive that gets
   reaped.
   - **Never `run_in_background`, never bare `sleep`.** A long-poll strictly dominates
     sleep-then-ask: it returns the instant the job lands (no dead air up to 5 min), costs one
     round-trip per window, and a lost call is re-issued with zero work lost.
3. **Status TOON (the one contract both sides share).** Two hard properties, both
   evidence-backed (forensics doc § "normalized as flaky"; the #909 false-blocker):
   **(a) job-died / job-running / job-done must be unambiguous in the response itself** — agents
   demonstrably read ambiguous outcomes as "flaky, retry" (never escalating) or as "blocked" (parking
   for an operator correction they don't need). The ledger record supplements; the response decides.
   **(b) "not yet" must be positively distinguishable from "stuck"** — a wait that returns on its
   time bound is NOT a timeout and must never look like one; it returns a full running-status TOON
   with **positive liveness evidence**, so "still working" can never be misread as "blocked". A
   response that carries nothing is the same ambiguity as today's 0-byte output file.
   - running (including every bound-expiry return): `status=running`, `elapsed_seconds`,
     `eta_seconds` (re-estimated from elapsed vs history), and **`last_progress_seconds`** (time
     since the child last produced output / advanced a phase marker) — the liveness signal that
     separates a slow-but-working job from a hung one.
   - terminal: `status=success|failure|timeout|killed`, plus the **same result shape today's build
     wrapper returns** (`errors[N]{file,line,message,category}`, `log_file`, `duration_seconds`) so
     downstream consumers (triage, findings, pre-commit-verify-freshness) need no second format.
     `killed` is its own status, never folded into `failure`, and its rendering must say
     **"externally killed — not flaky, do not blind-retry"** in so many words: the observed
     normalization means anything softer gets read as transient.
   - `status=not_found` for unknown/expired job ids (retention window — a design question below).
4. **Learned time:** first wait uses the persisted learned duration; the daemon refines
   `eta_seconds` continuously (elapsed vs per-command history percentiles).
5. **Idempotent submit:** submit carries `plan_id` + a job fingerprint (notation + args + tree
   state); re-submitting an identical in-flight job **attaches** to it instead of double-running —
   this kills the observed blind-retry storms at the protocol level.

## The client skill (requirement)

The client side is **a tiny skill** — working name `plan-marshall:build-server-client` — so every
dispatched context that builds gets the contract the same way it gets every other standard:

- **Contents (small, stable):** the submit/wait verb signatures (submit = exact executor-form
  command + execution path + project path); the status-TOON contract above (incl. the two hard
  properties and what `killed` means); the polling discipline (foreground bounded calls only,
  bound = `min(eta_remaining, 300)`, re-issue on bound expiry, re-attach via the ledger `job_id`);
  what `refused(reason=not_registered)` means (project needs the one-time registration via
  `manage-build-server` — escalate to the operator, do not work around); fallback semantics when
  the daemon is unreachable; and the one prohibition (never wrap the wait in
  `run_in_background` / `sleep`).
- **Wiring:** resolved into `skills[]` wherever build execution is dispatched (same profile
  machinery as build skills today); `await-long-running.md`'s detach seam is replaced by a pointer
  into this skill. The skill documents the *contract*; the executor scripts implement it — no logic
  in prose that the scripts don't enforce.
- **Boundary:** the client skill teaches consumption only. Provisioning/lifecycle (start, stop,
  upgrade, status, register/unregister) lives in the `manage-build-server` control skill, not
  here — a leaf that builds must not learn how to (re)start the daemon or enroll a project.

## Technology & topology (DECIDED 2026-07-16)

**A plain Python asyncio daemon on a Unix socket, run natively on the host (in-distro on
Windows/WSL2). No Docker, no JVM/Quarkus; MCP at most as a later optional facade.**

- **Python handles the parallelism fine — because the parallelism is not in-process.** marshalld is
  a *subprocess supervisor*: every parallel job (build, test run) is a child OS process; the daemon
  itself does only I/O — spawn, stream, track state, answer long-polls. That is asyncio's core
  competence (`asyncio.create_subprocess_exec`), and the GIL is irrelevant to it. The daemon must
  also emit **the same result TOON today's build wrappers produce** and reuse the
  learned-duration/run-config/TOON modules — all existing Python. Any other language reimplements
  that contract and drifts. Host contract stays "only Python 3 required".
- **MCP is NOT the core protocol — hard blocker:** dispatched `execution-context` agents have no
  MCP tools (tool surface: Read/Write/Edit/Glob/Grep/Bash/Skill), so the submit/wait seam MUST be
  an executor script over Bash regardless. Additionally, a stdio MCP server is a child of the
  harness — exactly the process ownership this epic escapes — and remote-MCP config is per-session
  and weak in headless runs. **Open (record, don't build): an optional MCP facade over the same
  socket** as orchestrator-session convenience — additive only, never the contract.
- **No Docker.** Jobs must run in the HOST environment: host worktrees, host toolchains
  (Maven/JDK/node/`./pw`), host caches and credentials, and **host paths in `errors[].file`**
  (container paths would poison every downstream consumer). Containerizing buys isolation we don't
  need (we run our own builds) at the cost of environment fidelity we can't lose, plus a dockerd
  dependency; the PID-1 escape is already achieved natively by the double-fork.
- **No Quarkus/JVM.** Same reuse/drift problem as any non-Python choice, plus a JVM requirement on
  every consumer machine — for a low-QPS supervisor of ~5–15 children, where the JVM's throughput
  strengths never engage. If the daemon ever needs real in-process compute, revisit then.
- **Platform (DECIDED 2026-07-16): POSIX everywhere — Windows is supported via a WSL2
  requirement.** Native Windows breaks three pillars at once (CPython exposes no `socket.AF_UNIX`
  there; no double-fork/`setsid`/PID-1; the reaper-escape evidence is POSIX-only), so instead of a
  second implementation, the support statement is: **plan-marshall on Windows = plan-marshall
  inside WSL2, entirely** — repo checkouts, worktrees, builds, the Claude Code session, AND the
  daemon all live in the distro (real Linux kernel + PID 1 ⇒ the whole design runs unchanged, one
  codebase). Binding conditions:
  - **All-in-distro, no mixed mode.** Native-Windows Claude Code submitting to a WSL daemon is
    NOT supported — toolchain-env fidelity and path semantics (`C:\` vs `/mnt/c` vs `\\wsl$`)
    break the S2 checks and poison `errors[].file`. Repos belong on the distro filesystem
    (ext4), not `/mnt/c` (I/O penalty).
  - **One distro = one "machine".** `~/.plan-marshall/`, registry, and daemon are per-distro;
    two distros are two independent build servers.
  - **VM lifecycle makes `down` routine, not exceptional, on Windows** — `wsl --shutdown`,
    reboot, and idle policies end the VM (a running daemon keeps it alive; the relay's death
    does not kill in-distro processes). The F2 gate already handles this (named reason,
    ask-to-start); the control skill's docs cover `vmIdleTimeout`/keep-alive.
  - **Re-run the reaper-escape experiment once inside WSL2** before shipping the Windows claim —
    cheap, and structurally it should be *stronger* there (upstream #68625's `WarmLifecycle`
    taskkill traverses Windows process trees, which cannot cross into the VM; a PID-1 daemon
    in-distro is invisible to it). Evidence over inference, as everywhere in this epic.

## Security model — design review 2026-07-16 (findings + resulting design changes)

**Trust boundary statement.** The outer boundary is the OS user: anything running as the same user
can already do everything marshalld can. So the review's question is not privilege escalation —
it is **(1) laundering** (the daemon outlives sessions and its jobs bypass Claude Code's
permission/sandbox layer), **(2) integrity** (daemon results feed merge-deciding gates), and
**(3) blast-radius** (a persistent process adjacent to a credentials store). Defense-in-depth
within the same-user boundary is warranted on all three.

| # | What can go wrong | Resulting design change (binding) |
|---|---|---|
| **S1** | **Permission-layer laundering / injection.** If the socket accepts arbitrary commands, any agent (or any local process) gets an execution service that Claude Code's permission prompts never see — and every future prompt-injection found in an agent escalates to "run anything, persistently". | **Verify-not-resolve (operator's model, 07-16).** Submit carries the exact executor-form command + execution path + project path; the daemon **verifies argv positionally against the executor template**: interpreter == registered baseline, argv[1] == `.plan/execute-script.py` **inside the submitted (verified) tree**, notation ∈ the registration's build/test allowlist, remaining args schema-checked. Any deviation ⇒ `refused`, logged. The registration itself is the outer wall: **enrollment only via the operator-interactive `manage-build-server` control skill** (user-invocable only, never in a dispatch's `skills[]`) — an agent cannot silently add a project or widen an allowlist. (Client-side resolution is kept deliberately: the executor is per-tree derived state, ADR-002 — a server-side resolver would duplicate it and re-open version skew.) Residual accepted: `--command-args` content reaches the build wrapper's own CLI — bounded by the wrapper's parser, same exposure as today's foreground path. |
| **S2** | **Env/cwd poisoning & path traversal.** Client-supplied env (`PYTHONPATH`, `PATH`) would let a submitter make the *daemon's child* load attacker code; a crafted cwd escapes into arbitrary trees (this repo has a live path-traversal lesson class in `_scope_fn`). | Daemon builds each job's env **from a clean server-side baseline** — client env is never forwarded wholesale. Execution path must canonicalize (symlinks resolved) to the **registered root or a live linked worktree of it** (dynamic check: `git-common-dir` resolves to the registered root, path under a registered worktree container) — a static worktree list would go stale, plan worktrees are ephemeral. Anything else ⇒ `refused`. |
| **S3** | **Impostor daemon / socket squatting ⇒ forged results.** A process squatting the socket path can return `status=success` for builds that never ran — and `pre-commit-verify-freshness` and triage would then gate merges on forged results. | State dir `0700`, socket `0600`; **client verifies socket-file owner == its own uid and completes a version/identity handshake before trusting any response**; gates may only consume results from a handshake-verified connection. Stale-socket takeover on daemon start: unlink only after liveness-probing the old pidfile. |
| **S4** | **Credentials adjacency / secrets side-channel.** Rung 1 puts the credentials store under the same `~/.plan-marshall/` root as daemon state and logs; job output can echo env; deny rules cover credential files, not new log paths. | Provider secrets **never cross the socket and are never placed in job env by default** — jobs that need providers use the existing provider machinery in-process, not via marshalld. Daemon state/logs live in a **sibling subtree, not inside the credentials dir**, so Rung 1's deny rules stay tight and log files never need to be deny-listed. |
| **S5** | **Persistence primitive.** Ask-to-start launches a long-lived process from plugin-cache code — a compromised bundle version would gain persistence beyond any session. | The start path **pins the entry point to the verified cache version** and writes an audit line (when, version, binary path, requesting plan). `manage-build-server status` shows the running daemon's version+path so the operator can audit what is actually resident. Upgrade = drain + restart **through the control skill only**. |
| **S6** | **Resource abuse / disk fill.** Any local process can flood the queue; journal/results/logs grow unbounded. | Bounded queue with per-project fairness; retention caps + GC for journal, results, and logs (tie into the existing GC discipline). Flooding degrades service, never correctness. |
| **S7** | **Version skew as an integrity risk.** An old daemon resolving new notations can silently run the wrong thing. | Handshake **refuses on version mismatch** (no best-effort mode); the refusal TOON names `reason=version_skew` and points at `manage-build-server upgrade`. |
| **S8** | **Prompt-injection via build output.** `errors[]`/logs can carry adversarial strings (e.g. a malicious dependency printing injection text). | **Unchanged vs today** — same output shape, same ingestion paths, same untrusted-content discipline applies to log contents. Recorded so the outline doesn't re-derive it; no new surface added. |
| **S9** | **Fail-open fallback.** Daemon-down fallback silently reintroduces the kill-prone in-process path. | Accepted availability trade-off; the degradation is **recorded** (ledger) and surfaced in the session — never silent. Already required by the optionality model. |

**Review verdict:** no finding kills the design; S1–S3 are binding shape-changers
(verify-not-resolve + the registration wall, clean-baseline env + dynamic path checks, verified
daemon identity before gate-trust) and are reflected in the call model above. The outline's
security pass re-runs this table against the concrete protocol rather than starting fresh.

## Hard design constraints

- **Launch = full double-fork daemonization** (intermediate in its own session spawns the daemon
  and exits → daemon re-parents to PID 1). A live-parented `setsid` child dies with its launcher —
  proven, see evidence doc. This applies to *every* path that starts the daemon, including the
  init-phase ask-to-start.
- **Nothing about the build server is git-tracked.** Endpoint, state, and the registration record
  (= the enable signal) all live under `~/.plan-marshall/` (Rung 1). `marshal.json` and
  `run-configuration.json` carry no build-server key at all — one contributor's machine setup
  never travels through the repo. Daemon state/logs in a sibling subtree to credentials (S4).
- **Unix domain socket** (filesystem-permission-scoped, no port, no port collisions); dir `0700`,
  socket `0600`, client-side owner check + handshake (S3).
- **Project-qualify `holder_is_dead`** before the daemon owns any cross-project lock (Rung 1
  landmine) — otherwise a foreign project's live lock gets falsely reclaimed mid-build.
- **Ops surface must be answered at outline:** crash recovery, restart-with-jobs-in-flight, log
  rotation, orphaned-job cleanup, upgrade path (control-skill-only, S5/S7), and how a user kills
  it safely — all owned by `manage-build-server`.
- **Retire-what-you-replace:** if the daemon subsumes `build_queue.py`'s slot logic (it should —
  a server-owned queue gets liveness detection for free), retire the file-based queue rather than
  stacking both.

## Design questions for the outline (do NOT pre-decide)

- **Wire format on the socket** (one-line TOON frames? length-prefixed JSON?) and the daemon's
  internal concurrency model details.
- **Retention:** how long do terminal results live server-side? What survives a daemon restart
  (jobs? results? both — needs an on-disk journal)? Caps per S6.
- **Queue semantics:** global `max_slots` (machine CPU) + per-project fairness details; priority
  for interactive-blocking jobs?
- **Name:** confirm or replace `marshalld` / `build-server-client` / `manage-build-server`
  (alternatives recorded in [`../00-README.md`](../00-README.md) § Naming).
- **Build-vs-buy honesty check:** with `plan-background-build-kill` landed (detector + legibility),
  is the residual pain still worth a daemon? Re-evaluate at outline with fresh kill-frequency data
  (re-run `../forensics-scripts/`).

## Documentation surface (explicit tasks — do not discover late; see [[project_plan_doc_contract_drift_underscoped]])

The platform decision (POSIX everywhere; **Windows = WSL2 only**) must land in the user-facing
machine requirements, which today state nothing about platform at all (both stop at "Python 3 in
PATH"):

1. **`README.md` § Prerequisites (`README.md:15-18`):** add a platform requirement block —
   supported platforms are macOS and Linux; **on Windows, plan-marshall runs exclusively inside
   WSL2**, with the entire runtime in-distro (repo checkouts, worktrees, builds, and the Claude
   Code session; repos on the distro filesystem, not `/mnt/c`). Mixed native-Windows/WSL usage is
   unsupported. Keep it to a few lines; link to the installation doc for the detail.
2. **`doc/user/installation.adoc` § Prerequisites (`doc/user/installation.adoc:10-14`):** the
   full statement — the WSL2 requirement and its why (one POSIX runtime), the all-in-distro rule,
   the one-distro-=-one-machine scoping (per-distro `~/.plan-marshall/`, registry, daemon), the
   `wsl --shutdown`/reboot/idle-timeout lifecycle note (daemon `down` is routine on Windows; the
   init preflight re-asks), and the `/mnt/c` performance warning. AsciiDoc conventions per
   pm-documents standards.
3. **Cross-references:** wherever the build server's own docs state the platform constraint
   (control-skill SKILL.md, client-skill SKILL.md), point at the installation doc rather than
   duplicating the requirement (no-duplication standard).
4. **NEW concept document `doc/concepts/build-server.adoc`** (the directory is
   one-concept-per-document — the build server gets its own, NOT a section inside an existing
   one): what marshalld is (machine-level owner of build-class work; wait and work are separate
   processes), the scope criterion (builds/tests in, CI waits out), registration-as-enablement
   and the control/client skill split, the submit → long-poll call model with the status-TOON
   three-way guarantee, the fallback path, and the platform statement (POSIX; Windows via WSL2 —
   xref the installation doc, don't duplicate). Current-state prose only (no history/rationale
   narrative — that stays in the epic's plan docs until shipped, then this doc describes what IS).
5. **Xrefs from the existing concept docs that describe building** — each gets a pointer to the
   new doc where its story changes when a project is registered: `build-management.adoc` (the
   primary one — how builds execute), `parallelism-and-locking.adoc` (build-queue/slot story —
   the daemon subsumes or hosts the queue), `execution-context.adoc` (leaves poll instead of
   holding builds), `security.adoc` (the registration wall + verify-not-resolve, one paragraph +
   xref), `audit-trail.adoc` (preflight + registration decision.log entries), and the concepts
   `README.adoc` index. Verify the exact list against the tree at execution — additional
   referrers may exist by then.
6. **Convert `../architecture.md` to AsciiDoc as `doc/developer/build-architecture.adoc`** — the
   as-built interaction architecture (component map, flows F1–F8, job state machine,
   deliberate-absences table) becomes a permanent developer doc. Update to as-built state during
   conversion (current-state only — drop the review-status header and any decided-on-date
   framing); ASCII diagrams per `pm-documents:ref-ascii-diagrams`. Division of labor vs task 4:
   `doc/concepts/build-server.adoc` = the concept (what and why, user-facing altitude);
   `doc/developer/build-architecture.adoc` = the interaction architecture (how, developer
   altitude) — cross-ref both ways, duplicate nothing. The source `architecture.md` is archived
   with the plan afterwards (per the epic's lifecycle convention), not left as a live duplicate.

These tasks ride this plan by default; if a documentation-only pass runs earlier, items 1–2 can
ship standalone (the platform requirement is decided and not gated on the daemon existing); items
4–6 describe shipped behavior and land WITH the daemon, not before.

## Acceptance (tests to demand at planning)

- A submitted job **survives a harness reap of the submitting session's wait**; the session
  recovers by re-issuing `wait` and gets the full result.
- A second session (or rebuilt context) re-attaches via the ledger-recorded `job_id`.
- Daemon down ⇒ submit degrades to the in-process fallback and records the degradation.
- A `wait` returning on its time bound carries `status=running` + `elapsed_seconds` +
  `eta_seconds` + `last_progress_seconds` — never an empty/timeout-shaped response.
- A reaped job's next poll returns `status=killed` with the explicit "externally killed — not
  flaky, do not blind-retry" rendering, and the ledger row carries the same status.
- Health-check gate: a self-resolvable condition (e.g. stale socket) does NOT block the start
  path; the gate TOON names its `reason`.
- Init preflight is ONE script call returning `disabled|ready|down+reason` — unregistered and
  healthy paths complete with a single call and no `AskUserQuestion`. **Every outcome** (all three
  statuses, plus the chosen resolution on `down`) emits one console line and one `decision.log`
  entry; the probe sequence is fully testable without a model in the loop.
- Unregistered project ⇒ byte-identical behavior to today (no registry hit ⇒ no probe, no socket).
- Init-phase ask fires when registered + daemon down; option (a) actually double-forks (child
  verified `ppid=1`) and the plan proceeds against the fresh daemon.
- Identical concurrent submits attach to one job (no double build).
- **Security (S1/S2/S3/S4):** submit from an **unregistered project** ⇒
  `refused(reason=not_registered)`; command deviating from the executor template (wrong
  interpreter, executor outside the submitted tree, non-allowlisted notation, malformed args) ⇒
  `refused`; execution path outside the registered root / not a live linked worktree of it (incl.
  via symlink) ⇒ `refused`; a **fresh plan worktree created after registration is accepted**
  (dynamic container check — no re-registration needed); job env equals the clean baseline (no
  client env leakage, no provider secrets); client refuses an impostor socket (wrong owner or
  failed handshake); register/unregister are reachable only via the user-invocable
  `manage-build-server` skill (never resolved into a dispatch's `skills[]`), and a registration
  change is audit-logged.

## Prior art / links

- [`../background-build-kill-forensics.md`](../background-build-kill-forensics.md) — all evidence,
  including the daemonization experiment and the "normalized as flaky" section.
- `.plan/archived-plans/2026-07-10-detach-long-running-builds/request.md:95-106,197-198` — the rung
  model and the original operator proposal.
- [`plan-background-build-kill.md`](plan-background-build-kill.md) — mitigation leg; lands first;
  its detector + ledger `status` are the fallback path's observability.
- `await-long-running.md:69-79` — today's agent-owned seam this plan replaces (superseded by the
  client skill).

## Lifecycle (handled like a plan source)

Move into the plan's own directory on creation. **After archive:** update
[`../00-README.md`](../00-README.md) (rungs table, layout, ordering, and the Naming section with
the confirmed names).
