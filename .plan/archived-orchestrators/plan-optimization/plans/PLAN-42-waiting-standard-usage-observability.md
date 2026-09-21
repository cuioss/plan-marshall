# PLAN-42: Waiting-Standard Usage Is Runtime-Invisible

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Surfaced 2026-07-22 by an orchestrator audit of the PLAN-29 (#969)
> platform-agnostic waiting standard: the operator asked whether *consistent usage* of the
> waiting seam ("using the background primitive for a CI-wait") could be verified **from the logs**.
> It cannot — the mechanism the seam selects leaves no runtime trace. Source is clean (no general
> body names `Monitor`); the gap is **observability**, not a leak.
>
> **Grounded at `main` @ `dfc4ac15c` (2026-07-22).** Evidence captured at ground truth this session:
> - `tools-integration-ci/scripts/_ci_barrier.py` — grep for log/Monitor/background/fallback/detach
>   returns **nothing**: the CI-wait implementation emits **no line naming the mechanism it ran**.
> - `plan-marshall/workflow/await-long-running.md:145` — states detach/wake/clear transitions are
>   "surfaced via `manage-logging` records," but (i) it is an **orchestration-guidance seam the
>   main-context agent *follows as prose***, not a script with deterministic logging; (ii) it logs
>   only on the **inline** path (a `Task: execution-context` dispatch emits a TOON status shape
>   instead); (iii) it records **transitions**, never the **mechanism selection**.
> - `await-long-running.md:123-127` (fallback path g) — the synchronous degrade is
>   "**behaviourally identical to the pre-detach model**", so a silent fall-back from
>   background-primitive → synchronous blocking leaves **no distinguishing record**.
>
> ⚠ Treat cited line numbers as approximate; D1 is a re-trace GATE regardless.

## Objective

The PLAN-29 waiting standard (ADR-011: policy renders everywhere, the `Monitor`/background
primitive lives behind the Runtime `wait-for` op) is **held only by convention**. At runtime the
seam records **which** primitive it selected nowhere, so two questions are unanswerable from the
logs:

1. **Was the standard used consistently?** — no log attests that a given CI-wait / build-wait ran
   on the background primitive rather than the synchronous fallback.
2. **Did the seam silently degrade?** — a fall-back to the synchronous blocking model (path g),
   which *is* a regression of PLAN-29's intent, is indistinguishable from the intended path.

Close the gap by making the seam **emit a mechanism-selection record** on every long-running wait,
so "used consistently" becomes a log query and a silent degrade becomes visible.

## Deliverables

### D1 — GATE: re-trace the two wait arms and where each is (not) logged

Confirm, against `main`, the exact seam surfaces before writing any emission:
- the **CI-wait arm** — `_ci_barrier.py` + `await-long-running.md` inline path;
- the **build-wait arm** — `build-server-client` submit/wait (the build consumer moved off this
  seam onto that client per `await-long-running.md:131`), so covering only the CI arm would be a
  **partial gate**. Enumerate every place a long-running wait resolves and classify each as
  logged / unlogged. Mutates nothing.

### D2 — emit a mechanism-selection record on the CI-wait / await arm

Where the seam resolves a wait inline, write one `manage-logging` record stamping:
`mechanism` (`background_primitive | synchronous_fallback`), `consumer` (ci-wait | build | …),
`wait_target` (pr#/check/job), and outcome. Best-effort, mirroring the title-surface ops — a
logging failure never aborts the wrapped wait (same contract as `await-long-running.md:121`).

**HYPOTHESIS (confirm in D1):** the inline path is the only place a Python script can deterministically
emit this. The `Task: execution-context` dispatch path returns a TOON shape, not a log — so its
mechanism stamp may have to ride the TOON `display_detail` and be reconciled by the orchestrator,
not written by the seam. Named confirm/refute artifact: `await-long-running.md:138-145` (the Output
contract) — if it already carries a mechanism field, D2 extends it; if not, D2 adds one.

### D3 — cover the build-wait arm

Apply the same mechanism stamp to the `build-server-client` wait path, so both arms are auditable
by the same log query. If D1 finds the client already emits a submit/wait record, extend it with the
`mechanism` field rather than adding a parallel record.

### D4 — regression test: the synchronous fallback stamps its marker

A test that drives the seam with the background primitive unavailable and asserts the emitted record
carries `mechanism=synchronous_fallback` — the exact silent-degrade this plan exists to make
visible. Pins the observability, not the current behaviour.

## Expected surface

- `tools-integration-ci/scripts/_ci_barrier.py` (+ its manage-logging call site)
- `plan-marshall/workflow/await-long-running.md` (Output contract + the inline-path logging clause)
- `build-server-client/**` wait path (D3)
- one new test under the CI / seam test suite (D4)

**Disjointness:** does NOT touch `marshall-orchestrator` (PLAN-40), `_markers_search.py` (PLAN-23),
or `manage-execution-manifest.py` (PLAN-35) — all three running plans are on unrelated surfaces.
The title-surface seam (PLAN-05/26/30) is shipped and D2 only *reads* its best-effort contract as a
shape precedent, so no collision with landed work.

## Notes

- Plugin-doctor static-grep rule (a source-level `Monitor`-in-general-body check) was considered and
  **dropped per operator** — the valuable gap is runtime observability, which a static grep cannot
  see (it catches leaks, not silent fallbacks).
- Theme fit: this is the enforcement/observability family — a standard whose conformance has no
  firing signal, adjacent to the vacuous-guards archetype (predicate never fires) but distinct: here
  the predicate is *absent*, not inert.
