# PLAN-TRUTH-005: Project-Local Synchronize Reconciles marshalld After a Version Bump (idle-conditional)

> Renamed from **PLAN-58** on 2026-07-30 (see `plan-id-rename-map.md`). ⚠ An emit under the OLD id was
> issued to the operator earlier on 2026-07-30 and superseded by the re-emit under this name.

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Operator observation + design 2026-07-23: marshalld drifts to
> `registered`-but-`socket_absent` because THIS meta-repo bumps the plugin-cache version at every
> finalize while the version-pinned daemon keeps running the old pin with nothing reconciling it.
> Operator scoping: the problem is **mainly in the meta-project**, so the **project-local synchronize
> skill is the correct home** — reconcile the daemon there, idle-conditionally, using the existing
> `manage-build-server` verbs. Grounded at `main` @ `110a51367`.

## Objective

The project-local synchronize flow (`sync-plugin-cache` / the meta-project sync skill — a surface
consumer repos do NOT have) already bumps the plugin-cache version at every finalize. Make it also
reconcile the running daemon to the new verified version — but ONLY when the daemon is idle, never
killing an in-flight build. This heals the `registered`-but-`socket_absent` drift at its source
(the version churn is meta-project-only), using the drain-then-start-verified primitive that already
exists, gated on the daemon's own in-flight count.

## Why project-local (scope decision, operator-set)

- The trigger — a plugin-cache version bump on nearly every plan finalize — is a **meta-project
  phenomenon**. Consumer repos do not regenerate the executor / bump the cache at finalize, so they do
  not accumulate the version skew. The synchronize skill is already meta-project-only.
- So this is a **project-local self-heal**, not a change to the shared marshalld daemon. The larger
  "daemon self-reloads itself on a version signal" design (an in-daemon `os.execv` re-exec at a
  self-known drained point — the answer to "how can a process start itself without harm") was
  considered and is **deliberately deferred**: it is general marshalld surface and over-scoped for a
  meta-project-only trigger. Recorded as the rejected alternative below; revisit only if the drift ever
  appears in a consumer repo.

## ⚠ Grounding — verified at `110a51367`

- OBSERVED: `manage_build_server.py`:506 `run_upgrade` = drain-then-start-verified (the reconcile
  primitive); :478 `run_drain` = `SIGTERM` + patient wait up to `_DRAIN_GRACE_SECONDS`, a job outlasting
  the grace is marked `killed` + replayed on next start (not lost, but disruptive — the exact outcome an
  idle-gate must avoid).
- OBSERVED: `_marshalld_scheduler.py` tracks in-flight jobs (slot budget) — the in-flight count the
  reconcile must read to decide idle-vs-busy.
- OBSERVED: a `status` verb exists on `manage-build-server` (lifecycle/status surface) — the idle oracle
  the skill queries; D1 confirms it reports in-flight count + running version.
- OBSERVED: the version-pin / anti-laundering wall — `upgrade` starts ONLY the verified bundle copy.

## ⭐ NEW DELIVERABLE ADDED 2026-07-27 — the drift this plan heals is currently INVISIBLE

A live operator diagnosis caught the exact drift condition this plan exists to prevent, **and caught
the reporting surface hiding it**:

- OBSERVED (first-party, 2026-07-27): `manage_build_server status` reported
  `binary_path: …/plan-marshall/0.1.1231/skills/manage-build-server/scripts/marshalld.py`, while the
  actual running process (pid 77349, started Jul 26 10:07, 1d 11h uptime) was executing
  `…/plan-marshall/**0.1.1212**/skills/manage-build-server/scripts/marshalld.py`. Read from `ps`
  against the live pid.
- **⇒ `binary_path` is a RESOLVED-NOW path presented as the running daemon's provenance.** It answers
  "which binary would I start today?" while reading as "which binary is running?". Nineteen versions of
  drift rendered as a clean status line — the epic's flagship archetype, on the very surface an
  operator would consult to detect drift.
- **⇒ This materially weakens the plan's own premise.** D-reload heals drift at its source, but with
  `status` unable to *show* drift, neither an operator nor a future gate can confirm the heal worked,
  and a regression would be silent. **The self-reload and the truthful report are complements.**

### D-truthful-version — `status` reports the RUNNING daemon's provenance (added 07-27)

Report the version/binary the live process is actually executing, sourced from the running process
rather than re-resolved at call time; where the two differ, say so explicitly rather than showing one.
⚠ **Fail-closed:** if the running binary's provenance cannot be determined, report it as `unknown` —
never fall back to the resolved-now path, which is precisely the substitution that produced this
defect. This deliverable is independently valuable and **must not be dropped if the reload work is
descoped**.

## Deliverables

1. **D1 (design gate) — the idle-conditional reconcile contract (mutates nothing).** Confirm the
   `manage-build-server status` fields the skill reads (running version, in-flight job count, socket
   liveness). Decide: reconcile fires only when running-version ≠ verified-pin AND in-flight == 0; a
   BUSY daemon is left running and the reconcile DEFERS (retry on the next sync / a persisted marker),
   never drains a live build. Settle the reconcile call (`upgrade` = drain+start-verified, vs a plain
   `start` when the daemon is already down / socket_absent). Decide the socket_absent case: a
   `registered`-but-`socket_absent` daemon is already dead, so reconcile = plain start of the verified
   version (no drain needed, nothing in flight).
2. **D2 — wire the reconcile into the project-local synchronize skill.** After the sync bumps the
   plugin-cache version, the skill queries `status`; if idle-and-stale (or socket_absent), it runs the
   D1 reconcile; if busy, it logs a deferral and leaves the daemon running. Meta-project-only surface;
   no shared-daemon change. Absent/disabled build-server ⇒ the reconcile is a silent no-op (a repo not
   using marshalld is unaffected).
3. **D3 — the deferral is observable, not silent.** A deferred reconcile (busy daemon) must leave a
   readable signal (a log line + optionally a persisted "reconcile-owed" marker the next sync consumes),
   so a daemon that stays stale across several busy syncs is visible rather than silently drifting to
   socket_absent. Truthful-signal discipline: a skipped reconcile is reported, not swallowed.
4. **D4 — tests.** Idle-and-stale daemon → reconciled to the verified version; BUSY daemon (in-flight
   job) → NOT drained, reconcile deferred + logged, job survives; `registered`-but-`socket_absent` →
   plain start of verified version (no drain); running-version == pin → no-op; no build-server enrolled →
   silent no-op. Pins the idle-gate (never kills an in-flight build) and the socket_absent self-heal.

Four deliverables (D1 a gate) — comfortably under the split guard; the tight meta-project scope keeps
it small.

## Claim Labels

- OBSERVED: `upgrade`/`drain` primitives — `manage_build_server.py`:506 / :478.
- OBSERVED: scheduler in-flight tracking (the idle oracle) — `_marshalld_scheduler.py`.
- OBSERVED: the symptom + meta-project cause (cache 1199→1201 this session, bumped per finalize).
- HYPOTHESIS: `manage-build-server status` reports in-flight count + running version + socket liveness
  as the skill needs — confirm/refute at the `status` verb impl in `manage_build_server.py`
  (verify-at-outline). If it lacks the in-flight count, D1 adds a minimal read-only accessor (still no
  daemon behavior change).
- Verify-first clause: before D2 wires the reconcile, confirm the project-local synchronize skill is the
  right seam (the `sync-plugin-cache` project-local skill vs `finalize-step-sync-plugin-cache` vs the
  on-main executor-regen step) — name the exact step that owns the post-sync moment, and place the
  reconcile there, not in a shared bundle skill.

## Expected Surface

- OBSERVED: the project-local synchronize skill (`.claude/skills/sync-plugin-cache` /
  `finalize-step-sync-plugin-cache` — the meta-project-only sync surface; D1 names the exact seam).
- OBSERVED: `manage-build-server/scripts/manage_build_server.py` — READ of the `status`/`upgrade`/`start`
  verbs (and a minimal read-only in-flight accessor only if D1 finds `status` lacks it). ⚠ **Now also
  WRITTEN, for D-truthful-version:** the `status` verb's `binary_path` / `version` derivation, which
  currently reports a resolved-now path rather than the running process's provenance.
- ⚠ **Adjacent to PLAN-88** (`daemon-audit-logs-interactions-not-job-lifecycles`) — same bundle
  (`manage-build-server`), different concern (version reporting vs. job observability). **Do not run
  concurrently**; whichever lands second re-grounds.
- OBSERVED: tests under the project-local skill's test home + `test/plan-marshall/manage-build-server/**`
  if a status accessor is added.

Meta-project-only surface — no consumer-facing change.

## Dependencies and Sequencing

- Relation to #909 half-(b) daemon liveness relay: this PARTIALLY addresses the symptom (heals the
  meta-project drift) but does NOT discharge the general daemon-side liveness contract (registered must
  imply live-or-stale for ANY cause, in any repo). Keep the #909 half-(b) relay OPEN as a separate,
  general, daemon-side concern; note this plan covers only the meta-project self-heal.
- Disjoint from all in-flight plans (project-local sync skill + read-only manage-build-server) — distinct
  from PLAN-45 (client routed-verdict mapping; different file, and this plan only READS the daemon
  lifecycle verbs). Emittable independently.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-005-marshalld-self-reload-on-version-signal.md"
```

## Notes

- Theme fit: machinery-integrity self-heal — the meta-project reconciles its own daemon to the version
  it just synced, and reports a deferral truthfully instead of drifting silently to socket_absent.
- Rejected/deferred alternative (recorded, thinking preserved): an in-daemon **self-reload** — outside
  writes a reload-request marker, the daemon re-execs itself (`os.execv`, same PID, inherited listening
  socket → no socket gap, no double-start) at a self-known drained point. Elegant and general, and it is
  the correct answer to "how can a process start itself without harm," but over-scoped for a
  meta-project-only trigger. Revisit as a separate general-marshalld plan only if the drift appears in a
  consumer repo.

## Two daemon design constraints, established from code

Both surfaced while PLAN-88 shipped and are load-bearing for any further `marshalld` work. Both are
message-supplied and HYPOTHESIS until re-verified, but each was established from code rather than
assumed, so verification is cheap.

**(a) A scheduler admission and a terminal-state store are TWO AUTHORITIES that must be reconciled at
the admission seam.** #1037 found a live bug proving it: `_admit_ready` re-executed an
already-terminalized job, **clobbering the terminal journal status back to `running`** and appending a
duplicate fate record. Fixed there with a `_is_terminalized` guard — but the general shape is that
admission does not consult terminal state, and this plan's self-reload work adds a third actor to the
same seam. **Re-check the guard holds under reload.**

**(b) ⭐ A read-time join is only as answerable as the SHORTER retention window.** Terminal journal
entries are GC'd after **3600 s**; audit rows live **7 days**. So a join between them can only answer
for a row's **first hour** — after that it silently returns nothing, and nothing in the module docs
surfaced this. **This is the epic's archetype in the design space rather than the code:** a join that
looks correct and stops answering, with no signal at the boundary. Any reload/liveness feature that
reads across those two stores inherits it.

⚠ **This plan is UNBLOCKED by PLAN-88 / #1037** (which held `manage-build-server`).

## ⭐ (c) Preflight readiness is a point-in-time probe reported as a STANDING guarantee — folded 2026-07-28 from the PLAN-94 landing (#1040), inbox message 009

**OBSERVED, first-party in PLAN-94's work log.** At `16:15:03Z`, `1-init` recorded:

```text
(plan-marshall:phase-1-init:build-server) Preflight ready (marshalld v1)
  - no action required; builds route to the daemon
```

That claim held for about **eighty minutes**. One routed build succeeded at `17:34:58Z`
(`mechanism=daemon_longpoll`, `job_status=success`). From `17:36:24Z` onward, **every** build logged
`resolved=in_process, reason=socket_absent, mechanism=in_process_fallback` — **ten or more
occurrences** across phases 5 and 6 (the phase-5 verification sweep, all three
`pre-push-quality-gate` builds, the loop-back re-verification, the post-fix builds). The daemon died
mid-run and every subsequent build silently degraded.

The fallback itself is **correct behaviour** and *is* logged at `WARNING`. Two things are still wrong:

1. **The preflight's phrasing is a standing claim** — *"no action required; builds route to the
   daemon"* — for a probe that only ever established a fact about `16:15Z`. Nothing re-asserted it and
   nothing reconciled the init-time claim against the run-time reality.
2. **Sustained degradation never escalates.** The tenth identical `socket_absent` warning is emitted
   exactly like the first, so a one-off fallback and a daemon-is-gone-for-the-rest-of-the-run
   condition are **indistinguishable in the log**, and neither surfaces above `WARNING`.

⇒ **Rule this plan carries:** a readiness probe reports a **timestamped observation**, not a standing
guarantee, and a **repeated** degradation is a different signal from a single one.

- Phrase the preflight as observed-at: `Preflight ready (marshalld v1) as of {ts} — builds will route
  to the daemon while it stays up`. Cheap, and it stops the init-time line reading as a whole-run
  contract.
- **Count consecutive fallbacks and escalate.** After N consecutive `socket_absent` resolutions, emit
  ONE `ERROR` line naming the transition (`daemon was reachable at {ts}, unreachable since {ts}, {n}
  builds degraded`) rather than the N+1st identical `WARNING`. **One transition event beats ten
  repeats.**
- **Reconcile at finalize.** A plan that preflighted `ready` and then ran every build in-process
  belongs in its own record — today that is recoverable only by reading the raw work log.

⚠ The practical cost here was **schedule, not correctness** — in-process builds produce the same
verdicts, just slower. But the shape is the dangerous part, and it directly aggravates the two
`marshalld` false-signal incidents already recorded in **both** polarities (a routed build reporting
false-green; a genuinely green verify reported as `timeout/-1`): *"was the daemon even up?"* is not
answerable from anything except a manual work-log scan.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests — it creates and edits
NO file under `.plan/local/orchestrator/` during execution, and reports its outcome through its PR
alone. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
