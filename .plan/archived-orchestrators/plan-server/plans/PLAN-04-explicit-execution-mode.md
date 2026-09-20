# PLAN-04: Explicit execution_mode on the build-server client API

epic: plan-server
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-explicit-execution-mode.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Today a build's execution path is decided by **ambient machine state**: the client reads the registry, pings the daemon, and routes to the daemon or falls back in-process (F2/F7). The caller — who is the only party that actually knows what it needs — has no say. That implicit coupling produces two live failures: script-shared build-queue/factory tests that exercise the in-process path get their execution stolen by a live daemon (8 spurious failures — confirmed 2026-07-20, since the module goes green in 735s with the daemon stopped), forcing plans to disable the daemon for the whole of finalize and thus run their longest, most reap-exposed builds with work-preservation switched off; and a build that genuinely needs work-preservation silently runs unprotected when the daemon is absent, then gets harness-reaped.

This plan makes the execution path a **first-class parameter of the client API**: `execution_mode = auto | in_process | daemon`. `auto` preserves today's behavior as the default, so no existing caller changes. `in_process` pins foreground execution. `daemon` *requires* daemon service and fails loud rather than silently degrading. The routing decision becomes explicit, per-call, visible in code, and auditable — instead of inferred from whatever the machine happens to be doing.

## Deliverables

1. **`execution_mode` parameter on the client submit/build API** — three values (`auto` default, `in_process`, `daemon`); `auto` is exactly today's registry+ping behavior, so the change is additive and backward-compatible for every existing call site.
2. **`in_process` path pinning** — the client never submits; it runs the foreground path directly, independent of registry/daemon state.
3. **`daemon` fail-loud semantics** — when the daemon is unregistered, down, or refuses, the call FAILS with the named reason rather than falling back to in-process. This is the assertive counterpart to F7's fallback, making "I require work-preservation" expressible.
4. **Routing-decision traceability** — each resolved execution mode emits the console line + `decision.log` entry that F2 already mandates for every routing outcome, now including which mode was requested and which was resolved (the requested-vs-resolved distinction is what makes a silent degradation visible).
5. **Test conversion** — the script-shared build-queue/factory tests that exercise the in-process path declare `execution_mode=in_process`, making them deterministic regardless of live daemon state. This is a *consequence* of deliverable 1, not the headline.
6. **Build-architecture diagram** — rework the diagram in `doc/developer/build-architecture.adoc` to render the three execution modes and the routing decision they replace, authored per the [`pm-documents:ref-svg-diagrams`](../../../../marketplace/bundles/pm-documents/skills/ref-svg-diagrams/SKILL.md) standard (load that skill and follow it; do not hand-roll an SVG or invent a house style). The current diagram documents routing as an inference from registry+ping state — after D1 that is no longer what the system does, so the diagram becomes actively wrong on merge if left alone. It should show `auto` / `in_process` / `daemon` as caller-declared inputs, and the requested-vs-resolved distinction from D4. **Verify the file path first** — the operator named `doc/developer/build-architecture.adoc`, but `CLAUDE.md` references `doc/developer/build.adoc` and `doc/developer/marketplace-build.adoc`; confirm which document actually owns the build-architecture diagram before editing, and correct this spec's path if it differs.

Split guard: 6 deliverables — at the threshold, so a split was considered and **rejected with rationale**. D2–D5 are thin consequences of the single API change in D1 (not independent work), and D6 is that change's documentation surface. Splitting D6 out would ship a merged API change alongside a diagram that describes the superseded routing model — and this project has a standing lesson that plans under-scope the doc contract surface, with the correction being to FOLD owning docs and xrefs into the plan rather than split them out. Proceeding unsplit as one coherent shippable unit.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/build-server-client/**` — the client API surface carrying the new parameter (**PLAN-03 also touches this — see Sequencing**)
- `script-shared/scripts/build/_build_execute_factory.py` — the routing decision seam
- `manage-locks/build_queue.py` — queue-side call sites, if the parameter threads through
- The script-shared build-queue/factory tests (deliverable 5)
- `build-server-client/SKILL.md` — documented API contract for the new parameter
- `doc/developer/build-architecture.adoc` + its diagram asset — D6 (path to be confirmed; see D6 note). Authored per `pm-documents:ref-svg-diagrams`.

Explicitly NOT in surface: `manage-build-server/scripts/marshalld.py`'s F3 verifier. The daemon gains **no** awareness of execution mode — a caller declining to use the daemon is not an attack on the daemon, so the verifier's checks are unchanged.

## Dependencies and Sequencing

- Depends on: **PLAN-03** (interaction-audit-logging)
- Overlaps with: **PLAN-03** — both plans touch `build-server-client`. This is a genuine surface collision, NOT disjoint; the two must NOT run concurrently. PLAN-03 makes fallback/refusal *legible* (captured-level logging); PLAN-04 makes it *controllable* (explicit mode). They are complementary halves of the same concern, and PLAN-04's deliverable 4 builds directly on PLAN-03's logging seam — so sequencing PLAN-04 second is both a collision-avoidance and a dependency ordering.

## Design Notes (carried from the analysis that produced this spec)

- **Why an API parameter and not an env var.** A `PLAN_MARSHALL_NO_DAEMON`-style env guard was considered and rejected — not on security grounds (the earlier claim that it "punches through the F3 security model" was over-stated and is retracted: F3 protects the daemon from being tricked into executing on its own authority, and a caller opting out does not attack it). It is rejected for **ambience**: process-global, invisible at the call site, set outside the code, no audit trail. The API parameter is the opposite on every axis and feeds F2's traceability requirement rather than eroding it. It is also the shape this project already rejected once, in the removed `require_wrapper` knob.
- **Why not daemon-side test detection.** Every submit is a canonical `python3 .plan/execute-script.py {notation} …` from a registered root with an allowlisted notation. From F3's viewpoint a test build and a production build are *identical and must remain so*. Teaching the verifier to recognize test invocations puts test awareness inside the security boundary — wrong layer.
- **Causation confirmed; failure mode still open.** Verified 2026-07-20: with marshalld stopped the full `plan-marshall` module goes green (735s, exit 0), proving the 8 failures are daemon interception of builds the queue tests expect in-process. What that does NOT settle is the sub-mechanism — green-when-stopped is equally consistent with path-selection and with a contract-shape mismatch (synchronous in-process result vs the daemon's `job_id`/`queued`/fingerprint-attach response). This fix does not depend on the answer: under `in_process` the tests deterministically get the path they were written against either way. **If the implementing plan finds the failures are contract-shape mismatches, say so in the landing** — that raises a separate and larger question (should the two execution paths be contract-equivalent?) which is explicitly OUT of scope here but would be worth its own plan.
- **Do not overstate the urgency.** An earlier revision of this spec and of the epic defect described the situation as "blocking phase-5 verify gates" and as a closed-both-doors deadlock (daemon-live ⇒ failures, daemon-stopped ⇒ harness reap). The 2026-07-20 green corrects both: the reap is **intermittent**, not deterministic, so a local whole-module green is reachable — just unreliably. The honest cost is a workflow tax plus one perverse consequence: the workaround is to stop the daemon for the duration of finalize, so the longest and most reap-exposed builds in the lifecycle run with work-preservation deliberately disabled. That is the real argument for this plan.

## Hand-Off Command

```text
/plan-marshall task="Make the build-server client's execution path an explicit API parameter instead of an inference from ambient machine state. Today the client reads the registry, pings marshalld, and silently routes to the daemon or falls back in-process; the caller has no say. Add execution_mode = auto | in_process | daemon to the client submit/build API: auto (default) is exactly today's registry+ping behavior so all existing call sites are unchanged; in_process pins foreground execution regardless of daemon state; daemon requires daemon service and fails loud with the named reason instead of silently degrading to in-process. Emit the console line and decision.log entry that the architecture already mandates for every routing outcome, recording both the requested and the resolved mode so a silent degradation is visible. Then convert the script-shared build-queue/factory tests that exercise the in-process path to declare execution_mode=in_process, which makes them deterministic whether or not a daemon is live — this currently causes 8 spurious module-tests failures that block phase-5 verify gates. Do NOT add any execution-mode awareness to the marshalld F3 verifier: a caller declining the daemon is not an attack on the daemon and its checks must be unchanged. Do NOT introduce an environment-variable bypass; the whole point is an explicit, per-call, auditable parameter. Finally, rework the build-architecture diagram in doc/developer/build-architecture.adoc so it renders the three execution modes and the requested-vs-resolved distinction instead of the old routing-by-registry-and-ping inference, which this change supersedes and which would otherwise be left documenting behavior the system no longer has; load the pm-documents:ref-svg-diagrams skill and follow its standard rather than hand-rolling an SVG, and confirm the owning document's real path first since CLAUDE.md also references doc/developer/build.adoc and doc/developer/marketplace-build.adoc. Design inputs and rejected alternatives: .plan/local/orchestrator/plan-server/plans/PLAN-04-explicit-execution-mode.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-04.md}
