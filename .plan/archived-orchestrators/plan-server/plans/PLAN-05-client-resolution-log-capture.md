# PLAN-05: Capture the client build-routing resolution/fallback log

epic: plan-server
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.

## Objective

The build client's routing-resolution log — the single line that says which
`execution_mode` was requested and how it actually resolved (routed to the daemon,
fell back in-process with a named reason, or failed loud) — is emitted at
`logger.info(...)` on `logger = logging.getLogger(__name__)` in
`_build_execute_factory.py` (lines 301 fail-loud, 551 routed, 581 in_process+reason),
and **no handler / `basicConfig` / `setLevel` is configured anywhere** in
`script-shared`, the executor, or `build-server-client` (verified: exhaustive grep,
empty). With an unconfigured logger, Python's last-resort handler surfaces only
WARNING+, so **every `[BUILD-SERVER] resolved build …` line is silently discarded.**
Only the adjacent `[EXEC]` line survives — because it is a bare `print(..., file=sys.stderr)`
(`_build_shared.py:513`), not a logger call.

This is the exact API-Sheriff INFO-invisibility failure PLAN-03 (#949) was chartered
to eliminate ("the fallback reason is logged ONLY at Python INFO, which nothing
captures — that is why it looked armed while doing nothing"). PLAN-03 delivered the
captured-level intent for the DAEMON-side audit log, but the CLIENT resolution line
was never wired to a captured sink; PLAN-04 D4's requested-vs-resolved traceability
rides the same dropped line. The consequence is live and blocking: on 2026-07-21,
four build-heavy worktree plans ran with zero daemon audit / journal / job-log
activity, and we could not tell whether every build correctly resolved in-process or
a genuine routing failure occurred — **because the reason line that would say so is
dropped.** This plan makes the client resolution line visible, which both restores
the PLAN-03/04 observability contract and unblocks the epic's worktree-routing
diagnostic.

## Deliverables

1. **Capture the three client resolution lines to a durable sink.** The
   `[BUILD-SERVER] resolved build (requested=…, resolved=routed|in_process|fail-loud,
   reason=…, notation=…, plan=…)` lines must reach a captured destination so the
   requested-vs-resolved mode and the fallback reason are readable after any build —
   at the same visibility as the surviving `[EXEC]` line. The mechanism (wire a
   handler + raise to a captured level; route through the build's captured
   stderr/log-file stream the way `[EXEC]` already is; or emit through the
   `manage-logging` client integration PLAN-03 introduced) is an OUTLINE decision, not
   fixed here — but it MUST NOT remain `logger.info` on an unconfigured logger.
2. **Regression tests.** Assert that each of the three resolution paths emits its line
   to the captured sink: (a) routed-to-daemon, (b) in-process with a named
   `fallback_reason`, (c) `execution_mode=daemon` fail-loud. These lock the
   observability so it cannot silently regress to INFO-invisibility again — the very
   failure mode that recurred here.
3. **Doc note (fold, do not split).** State where the client resolution log lands, in
   the owning doc surface (`build-server-client/SKILL.md` and/or
   `doc/developer/build-architecture.adoc`), so the captured-log location is
   discoverable. Keep it a cross-reference, not a duplication.

Split guard: 3 deliverables — well under the threshold. D2/D3 are the test and doc
surfaces of the single change in D1.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py`
  — the three `logger.info` resolution calls + whatever logging-capture seam D1 chooses.
- Possibly a shared logging-config helper under `script-shared/scripts/build/` if the
  chosen mechanism is a wired handler.
- The script-shared build tests (D2).
- `build-server-client/SKILL.md` and/or `doc/developer/build-architecture.adoc` (D3).

## Dependencies and Sequencing

- Depends on: nothing in this epic (queue is otherwise drained).
- **Surface adjacency (CROSS-EPIC): plan-optimization PLAN-32** (truthful-build-timeout-accounting)
  touches `_build_execute.py` + `manage-run-config/run_config.py` — the same build-emit
  module family, but DIFFERENT files (this plan's edits are in `_build_execute_factory.py`).
  File-level disjoint, so they MAY run concurrently — BUT both may want a
  "captured logging for the build-emit layer" seam. **Coordination rule for the outline:
  if PLAN-32 introduces a captured-logging-config seam for its status-truthfulness work,
  this plan RIDES it rather than adding a second one; if this plan lands first, PLAN-32
  reuses this seam.** Do not duplicate a build-layer logging-config mechanism across the
  two plans. Watch for rebase adjacency on shared imports in `script-shared/scripts/build/`.

## Design Notes

- **Not a runtime guard / not a difflib hack.** The fix is to route an existing,
  correct log statement to a sink that captures it — a call-site/config fix, not a
  new suppression or `[HINT]` layer.
- **This is where the routing diagnostic resumes.** Once the resolution line is
  captured, re-run a real build from a worktree and read `requested=` / `resolved=` /
  `reason=` — that collapses the OBSERVED-NEGATIVE worktree-routing watch into one of
  its three worlds (call-site bypass / correct in_process / genuine routing failure).

## Hand-Off Command

```text
/plan-marshall task="The build client's routing-resolution log line is silently dropped. In script-shared/scripts/build/_build_execute_factory.py the three '[BUILD-SERVER] resolved build (requested=..., resolved=routed|in_process|fail-loud, reason=..., notation=..., plan=...)' lines are logger.info(...) on logging.getLogger(__name__), and no handler/basicConfig/setLevel is configured anywhere in script-shared, the executor, or build-server-client — so Python's last-resort WARNING threshold discards them. Only the adjacent [EXEC] line survives because it is a bare print() to stderr (_build_shared.py:513). This is the exact API-Sheriff INFO-invisibility failure PLAN-03 (#949) was chartered to fix for the DAEMON audit log but which was never wired for the CLIENT resolution line; PLAN-04 D4's requested-vs-resolved traceability rides the same dropped line. Fix: capture the three resolution lines to a durable sink at the same visibility as [EXEC] — the mechanism (wire a handler and raise to a captured level, route through the build's captured stderr/log-file stream, or emit via the manage-logging client integration PLAN-03 added) is yours to choose at outline, but it must NOT remain logger.info on an unconfigured logger. Add regression tests asserting each of the three paths (routed, in-process with a named fallback_reason, execution_mode=daemon fail-loud) emits its line to the captured sink, so the observability cannot silently regress to INFO-invisibility again. Add a doc note in build-server-client/SKILL.md and/or doc/developer/build-architecture.adoc stating where the client resolution log lands (cross-reference, not duplication). IMPORTANT coordination: plan-optimization PLAN-32 (truthful-build-timeout-accounting) is touching the sibling files _build_execute.py + manage-run-config/run_config.py in the same build-emit module family; if it introduces a captured-logging-config seam, RIDE it rather than adding a second one — do not duplicate a build-layer logging-config mechanism. Design inputs and the full failure analysis: .plan/local/orchestrator/plan-server/plans/PLAN-05-client-resolution-log-capture.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-05.md}
