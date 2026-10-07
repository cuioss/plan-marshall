# PLAN-32: Truthful Build-Timeout Accounting

epic: plan-optimization
workstream: WS-10

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-32-truthful-build-timeout-accounting.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The build wrapper reported `status: timeout` over a pytest suite that **completed
successfully** (`1868 passed in 62.47s`), observed live during PLAN-28 / PR #962. This is the
direct sibling of PLAN-24 (#963): that plan fixed build status lying **green** over a real
failure; this one fixes status lying **red** over a real success. Same defect class — a
terminal status not derived from the true process outcome — and the same emit layer.

Two distinct root causes were identified by the orchestrator, both verified in source:

1. **Bound inversion.** `pyproject.toml:90-94` sets `timeout = 300` (pytest-timeout), added by
   the plan-server epic's PLAN-03 (#949) with the explicit stated intent of producing *"failure
   with a stack rather than an opaque job timeout"*. But the OUTER adaptive wrapper budget was
   ~120s — **smaller than the inner 300s bound** — so the wrapper preempts pytest's backstop,
   which can therefore never fire. The opaque job timeout PLAN-03 set out to eliminate is
   precisely what occurred: this is a partial regression of that remediation.
2. **Misleading observation surface.** The `62.47s` in the log is pytest-**internal** execution
   time; the wrapper budget is wall-clock and additionally covers collection, coverage
   reporting, and teardown. A later run measured ~103s wall-clock. So the true margin was
   ~103 vs ~120s — genuinely marginal — while the log invited the conclusion "62s timed out
   against 120s", which is absurd on its face and cost real diagnosis time.

**Not a straight bug: the system already self-heals.** On timeout the learned value doubles
(`timeout_set(key, min(t*2, MAX_TIMEOUT=1800))`), so the budget corrects on the next run. The
defects are narrower and must be scoped as such: a completed run is **discarded** before the
correction lands, and the log **actively misdirects** the diagnosis. Do not "fix" the adaptive
learning wholesale — it is working as designed.

## Cross-Epic Contract — RESOLVED (operator-confirmed 2026-07-21)

The plan-server epic owns the governing #909 invariant. Its `analyze` run **settled the hoist
question with a scoped split** — this is no longer an open dependency:

| Half | Disposition | Rationale |
|------|-------------|-----------|
| **(a) terminal-status correctness** — *"a run that ran to completion is never timeout-shaped; `timeout` is reserved for a genuine kill"* | **HOISTED into the shared build layer** (`script-shared/build/_build_execute.py` + `manage-run-config`) | Both execution paths already converge on one `DirectCommandResult`. **This is the half that was violated** — cited at `_build_execute.py:264` |
| **(b) bound-expiry running-liveness** — the long-poll's running-TOON on time-bound return | **stays daemon-local** | No synchronous in-process analogue exists |

**D3 therefore conforms to the SHARED terminal-status-correctness contract** — NOT a
daemon-local application with an xref. **D3 is unblocked to design.** D1/D2/D4 are unchanged.

Standing agreement reaffirmed by both epics: PLAN-32 owns the fix (route-agnostic layer,
sibling of PLAN-24 #963); the bound-inversion value stays **inferred** until D1 reads
`run-config.json`; any routing defect surfaced — including the `execution_mode=daemon` second
bound in `build_server.py` — goes back to plan-server.

### ⚠ Design refinement the orchestrator found while verifying `_build_execute.py:264`

The cited line is `except subprocess.TimeoutExpired:`, whose branch unconditionally emits
`status: 'timeout'`, `exit_code: -1`. **That exception only fires when Python actually killed
the child** — so in the observed incident the *process* did **not** run to completion; it was
genuinely killed. What completed was the **test phase** (pytest had already written
`1868 passed in 62.47s` to the log) before the kill landed during the post-test tail
(coverage reporting, teardown, plugin cleanup).

This matters for D3's design, and the plan must not gloss it:

- Under half (a) as worded — *"`timeout` is reserved for a genuine kill"* — this **was** a
  genuine kill, so `status: timeout` is not straightforwardly wrong. The naive reading
  ("don't say timeout when it completed") does **not** resolve this case.
- The actual defect is that the timeout branch **discards evidence it already holds**: the log
  contains a complete, passing test summary, and the emitted result throws it away. The run is
  reported as an undifferentiated timeout when the truthful characterization is *"killed during
  teardown after the tests had already passed."*
- **Exact symmetry with PLAN-24 (#963)**: that plan fixed the *success* path by making it
  consult `test_summary` instead of trusting `returncode == 0`. D3 should make the *timeout*
  path consult `test_summary` instead of trusting `TimeoutExpired` alone. Same defect shape,
  opposite branch, same remedy — and it means D3 extends an established pattern rather than
  inventing one.
- Consequently D3 must decide (and record) what the truthful terminal status **is** for
  work-succeeded-then-killed. Do not assume it is `success`: the process was killed and side
  effects may be incomplete. A distinct discriminator, or `timeout` carrying positive evidence
  of what completed, are both defensible — this is a genuine design call for outline.

## Deliverables

1. **Characterize before fixing.** Read the actual persisted `run-config.json` entry for the
   affected command key (the ~120s figure is operator-reported, NOT yet verified on disk) and
   establish the real wall-clock breakdown: pytest-internal time vs collection vs coverage vs
   teardown. Do NOT fix on the hypothesis — same discipline PLAN-24's D1 followed successfully.
2. **Order the bounds: inner < outer, structurally.** The pytest-timeout backstop must be
   reachable — it can only produce its diagnostic stack if it fires before the wrapper kills the
   process. Derive the wrapper budget so it always exceeds the inner bound (plus margin), or
   otherwise guarantee the ordering. A guard/test must fail if the two ever re-invert, since the
   inversion is silent and cost this epic a full diagnosis cycle.
3. **Make the terminal status truthful — conform to the HOISTED half-(a) contract.** The
   `except subprocess.TimeoutExpired` branch at `_build_execute.py:264` emits an
   undifferentiated `status: 'timeout'` while **discarding the passing test summary already
   present in the log**. Make that branch consult `test_summary` — the exact mirror of PLAN-24's
   fix to the success branch — and decide/record the truthful terminal status for
   *work-succeeded-then-killed*. Do NOT assume it is `success`: the process was genuinely killed
   and side effects may be incomplete. See the design-refinement note above; this is the one
   genuine design call in the plan.
4. **Fix the misleading observation surface.** When a timeout IS reported, the emitted result
   must carry the wall-clock figure the budget was actually measured against — not only the
   tool-internal duration — so the number in the log and the number in the budget are
   commensurable. This is the deliverable that would have made the incident self-diagnosing.

Four deliverables, comfortably under the ~6 split guard, and tightly coupled (D2/D3/D4 all act
on the same emit path).

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute.py`
  (`execute_direct_base`, `MIN_TIMEOUT`, `MAX_TIMEOUT`, the timeout except-branch)
- `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py`
  (`timeout_get`, `timeout_set`, `compute_weighted_timeout`, `SAFETY_MARGIN`)
- `pyproject.toml` (the `timeout = 300` pytest-timeout bound, if the ordering fix lands there)
- possibly `script-shared/scripts/build/_build_result.py` (the emit choke point PLAN-24 hardened
  with `assert_truthful_status` — the natural home for a red-lying guard alongside the
  green-lying one)
- tests under `test/plan-marshall/build-operations/`

## Dependencies and Sequencing

- Depends on: **PLAN-24 (#963) — SHIPPED**, which freed `_build_shared.py` / `_build_result.py`
  and established `assert_truthful_status` at both emit choke points. This plan extends that
  guard's remit rather than introducing a parallel mechanism.
- **Soft-blocked on the plan-server `analyze` decision** (see Cross-Epic Dependency). Emittable
  now; D3 must not be *designed* until that answer lands.
- Overlaps with: **none in flight.** PLAN-25 owns `_cmd_skill_domains`+compose-resolve, PLAN-26
  owns `platform-runtime`, PLAN-30 owns `marshall-orchestrator/workflow/*.md`. All disjoint.
- Note vs **PLAN-23** (staged): PLAN-23 touches `build-maven`/`script-shared` marker detection.
  If both are live simultaneously, re-check disjointness — PLAN-32 touches
  `script-shared/scripts/build/` but a different module set.
- ⚠ Any *routing* defect this plan uncovers (daemon vs in-process resolution) is **handed to the
  plan-server epic, never absorbed here.** Under `execution_mode=daemon` a second, independent
  bound applies (`build-server-client/build_server.py`: `_CONNECT_TIMEOUT_SECONDS`, and the
  bounded long-poll `bound + _WAIT_TIMEOUT_MARGIN_SECONDS`); verify this plan's contract holds
  on that path, but do not fix daemon routing here.

## Hand-Off Command

```text
/plan-marshall The build wrapper reported `status: timeout` over a pytest suite that actually COMPLETED successfully (log showed "1868 passed in 62.47s"), observed live during PR #962. This is the direct sibling of the just-shipped PLAN-24/#963: that fixed build status lying GREEN over a real failure, this fixes status lying RED over a real success — same defect class (terminal status not derived from true process outcome), same emit layer. Two verified root causes. FIRST, bound inversion: pyproject.toml:90-94 sets pytest-timeout `timeout = 300` with the explicit intent "failure with a stack rather than an opaque job timeout", but the OUTER adaptive wrapper budget was ~120s — smaller than the inner 300s bound — so the wrapper preempts pytest's backstop and it can never fire; the opaque timeout that config exists to prevent is exactly what occurred. SECOND, misleading observation surface: the 62.47s figure is pytest-internal execution time while the wrapper budget is wall-clock including collection, coverage reporting and teardown; a later run measured ~103s wall-clock, so the true margin was ~103 vs ~120s (genuinely marginal), but the log invited the absurd reading "62s timed out against 120s" and cost real diagnosis time. IMPORTANT SCOPING: the adaptive learning already self-heals (on timeout the learned value doubles via timeout_set(key, min(t*2, 1800))), so do NOT rework adaptive learning wholesale — it works as designed; the defects are that a completed run is discarded before the correction lands, and that the log misdirects. Deliverables: (1) characterize before fixing — read the actual persisted run-config.json entry for the affected command key, since the ~120s figure is operator-reported and NOT verified on disk, and establish the real wall-clock breakdown (pytest-internal vs collection vs coverage vs teardown); do not fix on the hypothesis. (2) Order the bounds inner<outer structurally so the pytest backstop is always reachable, with a guard/test that fails if they ever re-invert, since the inversion is silent. (3) Make the terminal status truthful at the except subprocess.TimeoutExpired branch (_build_execute.py:264), which currently emits an undifferentiated status: 'timeout' / exit_code: -1 while DISCARDING the complete passing test summary already present in the log. (4) When a timeout IS reported, emit the wall-clock figure the budget was actually measured against, not only the tool-internal duration, so the log number and the budget number are commensurable. CRITICAL CONSTRAINT — the governing contract is OWNED BY THE plan-server EPIC and its scope is ALREADY SETTLED (operator-confirmed 2026-07-21), so conform, do NOT re-derive: the #909 contract was hoisted in two halves. Half (a) terminal-status correctness — "a run that ran to completion is never timeout-shaped; timeout is reserved for a genuine kill" — IS HOISTED into the shared build layer (script-shared/build/_build_execute.py + manage-run-config) where both execution paths converge on one DirectCommandResult, and this is the half that was violated. Half (b) bound-expiry running-liveness (the long-poll's running-TOON) STAYS DAEMON-LOCAL, no in-process analogue. So deliverable 3 conforms to the SHARED terminal-status-correctness contract, not a daemon-local application with an xref. IMPORTANT DESIGN NOTE, verified in source by the orchestrator and NOT to be glossed: subprocess.TimeoutExpired only fires when Python actually KILLED the child, so in the observed incident the PROCESS did not run to completion — it was genuinely killed; what completed was the TEST PHASE (pytest had already written "1868 passed in 62.47s") before the kill landed during the post-test tail of coverage reporting and teardown. Therefore the naive reading "don't say timeout when it completed" does NOT resolve this case, because by half (a)'s own wording this WAS a genuine kill. The real defect is that the timeout branch throws away evidence it already holds. The remedy has exact symmetry with PLAN-24/#963: that plan fixed the SUCCESS path by making it consult test_summary instead of trusting returncode == 0; make the TIMEOUT path consult test_summary instead of trusting TimeoutExpired alone — same defect shape, opposite branch, same remedy, so this extends an established pattern rather than inventing one. You must decide and RECORD what the truthful terminal status is for work-succeeded-then-killed; do NOT assume it is success, since the process was killed and side effects may be incomplete — a distinct discriminator, or timeout carrying positive evidence of what completed, are both defensible. This is the one genuine design call in the plan. Primary surface: script-shared/scripts/build/_build_execute.py (execute_direct_base, MIN_TIMEOUT, MAX_TIMEOUT), manage-run-config/scripts/run_config.py (timeout_get/timeout_set/compute_weighted_timeout/SAFETY_MARGIN), pyproject.toml, possibly _build_result.py where PLAN-24 put assert_truthful_status (the natural home for a red-lying guard beside the green-lying one), plus tests under test/plan-marshall/build-operations/. Finally: any ROUTING defect uncovered (daemon vs in-process resolution) is handed to the plan-server epic, never absorbed here — under execution_mode=daemon a second independent bound applies in build-server-client/build_server.py (_CONNECT_TIMEOUT_SECONDS and the bounded long-poll bound + _WAIT_TIMEOUT_MARGIN_SECONDS); verify this plan's contract holds on that path but do not fix daemon routing here.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-32.md}
