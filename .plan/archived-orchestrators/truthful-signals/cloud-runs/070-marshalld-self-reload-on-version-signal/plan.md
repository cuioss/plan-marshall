> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The project-local sync reconciles marshalld after a version bump, and status tells the truth about which daemon is running

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

This meta-repository bumps the plugin-cache version at nearly every plan finalize. The `marshalld`
build daemon is **version-pinned**, so it keeps running the old pin with nothing reconciling it. Over
time the daemon drifts to `registered`-but-`socket_absent`: enrolled, believed available, actually
dead. Builds then silently fall back to in-process execution.

The drift is a **meta-project phenomenon** — consumer repositories do not regenerate the executor or
bump the cache at finalize, so they never accumulate the skew. That is why the fix belongs in the
project-local synchronize surface rather than in the shared daemon.

**And the surface an operator would consult to detect the drift is itself hiding it.** A live
observation caught `manage_build_server status` reporting a `binary_path` under version `0.1.1231`
while the actual running process — read from `ps` against the live pid — was executing the binary
under `0.1.1212`. **`binary_path` is a resolved-now path presented as the running daemon's
provenance.** It answers *"which binary would I start today?"* while reading as *"which binary is
running?"* Nineteen versions of drift rendered as a clean status line: this epic's flagship archetype,
sitting on the one surface built to reveal it.

That materially weakens the reconcile half's own premise. Healing drift at its source is worth little
while `status` cannot *show* drift — neither an operator nor a future gate could confirm the heal
worked, and a regression would be silent. **The self-reload and the truthful report are complements,
not alternatives.**

A third instance completes the picture. A run's `1-init` recorded *"Preflight ready (marshalld v1) —
no action required; builds route to the daemon."* That held for about eighty minutes. One routed
build succeeded; from then on **every** build logged `resolved=in_process, reason=socket_absent`, ten
or more times across two phases. The fallback is correct behaviour and *is* logged at `WARNING` — but
the preflight phrased a **point-in-time probe as a standing guarantee**, and the tenth identical
warning is emitted exactly like the first, so *"a one-off fallback"* and *"the daemon has been gone
all run"* are indistinguishable in the log.

## Goal

After a version bump, an **idle** daemon is reconciled to the newly verified pin and a **busy** one is
left alone with the deferral recorded; `status` reports the version the live process is actually
executing; and a readiness probe reads as a timestamped observation rather than a whole-run contract,
with sustained degradation escalating once instead of repeating quietly.

## Deliverables

The deliverables fall into **two independently shippable groups**. See the split-guard verdict below.

**Group A — reconcile (the self-heal)**

1. **D1 — GATE: settle the idle-conditional reconcile contract.** Mutates nothing. Confirm which
   fields `manage-build-server status` actually exposes: running version, **in-flight job count**,
   socket liveness. Then settle: the reconcile fires only when running-version ≠ verified-pin **AND**
   in-flight == 0; a **busy** daemon is left running and the reconcile **defers**; a
   `registered`-but-`socket_absent` daemon is already dead, so its reconcile is a plain **start** of
   the verified version, with no drain and nothing in flight.
   *Done when:* the contract is recorded, naming the exact `status` fields it reads and the exact
   reconcile call per case (`upgrade` = drain-then-start-verified, versus plain `start`).
   ⛔ **STOP CONDITION.** If `status` does not expose an in-flight count, **do not infer idleness from
   anything else** — halt Group A and report it, or (if trivially available) add a **read-only**
   accessor and say so. Guessing idleness is how a live build gets drained, which is the one outcome
   the gate exists to prevent.
2. **D2 — Wire the reconcile into the project-local synchronize skill.** After the sync bumps the
   plugin-cache version, query `status`; if idle-and-stale (or socket_absent) run the D1 reconcile; if
   busy, log a deferral and leave the daemon running.
   *Done when:* the reconcile runs from the meta-project sync surface only, and an absent or disabled
   build server makes it a **silent no-op** so a repository not using marshalld is unaffected.
   ⛔ **No shared-daemon behaviour change.** The seam is meta-project-only.
3. **D3 — The deferral is observable, not silent.** A deferred reconcile leaves a readable signal — a
   log line, and optionally a persisted "reconcile-owed" marker the next sync consumes — so a daemon
   that stays stale across several busy syncs is visible rather than drifting quietly to
   `socket_absent`.
   *Done when:* a deferral is readable after the fact without a raw log scan. A skipped reconcile is
   **reported, not swallowed**.

**Group B — truthful reporting (independently valuable; ⛔ must NOT be dropped if Group A is descoped)**

4. **D4 — `status` reports the RUNNING daemon's provenance.** Source the version and binary from the
   **live process**, not from a call-time re-resolution. Where the running provenance and the
   resolve-now path differ, **say so explicitly** rather than showing one of them.
   *Done when:* a deliberately stale daemon makes `status` show the divergence.
   ⛔ **Fail closed:** if the running binary's provenance cannot be determined, report it as
   `unknown` — **never** fall back to the resolved-now path. That substitution *is* the defect.
5. **D5 — A readiness probe reports an observation, not a guarantee.** Phrase the preflight as
   observed-at (e.g. *"Preflight ready (marshalld v1) as of {ts} — builds will route to the daemon
   while it stays up"*), and **count consecutive fallbacks**: after N consecutive `socket_absent`
   resolutions emit **one** `ERROR` naming the transition (*"daemon reachable at {ts}, unreachable
   since {ts}, {n} builds degraded"*) instead of the N+1st identical `WARNING`.
   *Done when:* one transition event replaces the repeat, and the init-time line no longer reads as a
   whole-run contract. **One transition beats ten repeats.**
6. **D6 — Tests.** Idle-and-stale → reconciled. **BUSY → NOT drained**, deferral logged, the in-flight
   job survives. `socket_absent` → plain start, no drain. Version == pin → no-op. No build server
   enrolled → silent no-op. `status` on a stale daemon → divergence shown. Provenance undeterminable →
   `unknown`, never the resolved path.
   *Done when:* all cases pass, with the BUSY case and the `unknown` case present — they are the two
   that pin the safety properties.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables, **at the split presumption**,
and the two groups above are genuinely separable. **No split of the file** — the plan is named for one
orchestrator spec and splitting it would break that mapping — but the run is explicitly authorised to
**ship Group B alone** if Group A halts at D1's stop condition. Group B is the half that makes any
future regression visible, so it is the half that must not be lost. If Group A halts, say so and ship
B rather than abandoning both.

## Out of scope

- **An in-daemon self-reload** (the daemon re-`execv`s itself at a self-known drained point, same pid,
  inherited listening socket, so no socket gap and no double-start). This is elegant, general, and the
  correct answer to *"how can a process restart itself without harm"* — and it is **deliberately
  deferred** because the trigger is meta-project-only and this would change shared daemon surface for
  it. Revisit as its own plan **only if the drift ever appears in a consumer repository**.
- **The general daemon-side liveness contract** (`registered` must imply live-or-stale for *any*
  cause, in *any* repo). This plan heals the meta-project's own drift; it does not discharge that
  broader obligation, which stays open separately. Conflating them would turn a bounded self-heal into
  a daemon redesign with no operator present to bound it.
- **Job-lifecycle audit observability.** A sibling concern in the same bundle, different question
  (what the daemon logs about jobs, versus what it reports about itself). Keeping them apart is what
  lets either land without re-grounding the other.

## Expected surface

- `.claude/skills/sync-plugin-cache/**` and/or `.claude/skills/finalize-step-sync-plugin-cache/**` —
  the meta-project-only sync surface. ⛔ **D1 names the exact seam before D2 writes to it** (the
  project-local sync skill, versus the finalize step, versus the on-main executor-regen step); place
  the reconcile in the step that owns the post-sync moment, never in a shared bundle skill.
- `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py` —
  **read** of `status` / `upgrade` / `start`; **written** for D4's provenance derivation.
- `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` —
  read-only, the in-flight source.
- `test/plan-marshall/manage-build-server/**` and the project-local skill's test home.

Meta-project-only; no consumer-facing change.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `run_upgrade` is drain-then-start-verified, and `run_drain` is SIGTERM plus a bounded grace after which a job is marked `killed` and replayed | OBSERVED | `manage_build_server.py` § `run_upgrade`, § `run_drain` — locate **by symbol**; reported line numbers are leads |
| The scheduler tracks in-flight jobs (slot budget) | OBSERVED | `_marshalld_scheduler.py` — by symbol |
| `upgrade` starts only the verified bundle copy (the anti-laundering wall) | OBSERVED | that file's upgrade path |
| `status` reported `0.1.1231` while `ps` showed the live pid running `0.1.1212` | OBSERVED | reproduce: run `status`, then read the live pid's command line. ⛔ **The exact versions are leads** — the divergence is the claim, not the numbers |
| `manage-build-server status` exposes in-flight count, running version, and socket liveness in the shape D1 needs | HYPOTHESIS | the `status` verb implementation — **D1 itself, which HALTS if the in-flight count is absent** |
| The project-local sync skill is the right seam for the reconcile | HYPOTHESIS | the three candidate skills named under Expected surface — ⛔ D1 names the owning step before D2 writes |
| A preflight logged "ready … no action required" and every subsequent build resolved `in_process` / `socket_absent` | OBSERVED | reproducible by killing the daemon mid-run; the original run's log is **not reachable from this clone** |
| Consecutive `socket_absent` warnings are emitted identically, with no escalation | HYPOTHESIS | the fallback emission path — read it before building D5's counter |
| Nothing already counts or escalates consecutive fallbacks | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — search before adding a counter, or D5 ships a duplicate |
| Admission does not consult terminal state, so a reconcile adds a third actor at that seam | HYPOTHESIS | the `_admit_ready` path and its terminalization guard — **re-check the guard holds under a reload** |
| A read-time join across the terminal journal (~1 h retention) and the audit rows (~7 d) can only answer for a row's first hour | HYPOTHESIS | both stores' retention settings. ⚠ This is the epic's archetype in the *design* space: a join that looks correct and quietly stops answering |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5's preflight wording and D4's divergence output are text-whose-value-is-what-a-reader-does**,
  so both get a **cold read**. Show the Step 6 verification sub-agent the new preflight line and the
  new `status` output for a stale daemon, with no other context, and ask: *(a) does the preflight
  promise anything about later in the run?* and *(b) which version is actually executing?* The correct
  answers are **no** and **the running one, with the divergence visible**. If the reader still takes
  the preflight as a standing guarantee, the wording failed.
- **The BUSY-daemon test is the one that matters most** — it must demonstrate the in-flight job
  *survived*, not merely that a deferral was logged. A deferral log with a killed job is a failed
  deliverable.
- D4's fail-closed path must be tested by making provenance genuinely undeterminable and asserting the
  output is `unknown`. A test that only covers the happy path leaves the exact substitution that
  caused the defect unguarded.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing, local execution only:** on the machine this plan came from, the plugin registry pin
  and the generated executor had diverged, and this plan was being **withheld from local launch until
  that was repaired**. A cloud clone has no such state, so the constraint does not apply here — it is
  recorded so nobody re-derives it as a blocker.
- The practical cost of the preflight defect was **schedule, not correctness**: in-process builds
  produce the same verdicts, only slower. The shape is the dangerous part, and it aggravates two
  recorded `marshalld` false-signal incidents in **both** polarities — a routed build reporting
  false-green, and a genuinely green verify reported as a timeout. *"Was the daemon even up?"* should
  not require a manual log scan to answer.
- ⛔ **Do not go looking for the orchestrator spec, the inbox messages, or any landing record.** They
  live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this
  file.
