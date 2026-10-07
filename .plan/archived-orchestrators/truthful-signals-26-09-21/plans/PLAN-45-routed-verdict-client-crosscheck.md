# PLAN-45: Routed Build Verdict Has No Client-Side Cross-Check (single point of truth)

epic: truthful-signals
workstream: WS-01

> Staged plan spec. **Migrated from the plan-server epic 2026-07-22** (plan-server closed; its
> build/status-truthfulness residue folds into this successor's flagship theme). This is the
> DEFENSE-IN-DEPTH complement to the already-shipped daemon-side false-green fix.
>
> **Re-grounded at `main` @ `110a51367` (2026-07-23, post-#988).** Evidence captured at ground truth:
> - `script-shared/scripts/build/_build_execute_factory.py:221` — `_daemon_result_to_direct` returns
>   `success_result(...)` on `job_status == 'success'` with NO re-read of the child's build-TOON. The
>   client trusts the daemon's `job_status` verbatim. (Was line 220 pre-#988; shifted +1.)
> - `manage-build-server/scripts/_marshalld_supervisor.py:315-319` — the daemon (post-#979 D4) makes
>   `job_status` truthful by reading the SAME job log (`read_log_verdict`) and downgrading a `success`
>   classification to `failure` when the child TOON's `status != success`.
>
> ⚠ **PLAN-42 (#988, `110a51367`) landed in THIS SAME FILE 2026-07-23** — it extended
> `_record_resolution`'s `_audit_log` with a `mechanism=` field (`daemon_longpoll` / `in_process_fallback`
> / `no_build`) from a shared closed vocabulary. That is a DIFFERENT concern (wait-mechanism
> observability, not verdict correctness) but it OVERLAPS this file, so scope D2/D3 on the post-#988
> version and do not clobber the mechanism logging. Notably #988's `no_build` member — the honest label
> for "nothing ran" — is the truthful-status precedent D2's fail-closed disagreement branch should read
> as: a routed `success` whose log verdict disagrees is exactly the "the signal lied about what ran"
> case, and must surface as ERROR consistent with that vocabulary's intent.
>
> ⚠ Treat cited line numbers as approximate; a re-trace is the D1 GATE regardless.

## Objective

A daemon-routed build reports its verdict to the caller through the `wait` status-TOON, and the
caller trusts the top-level `job_status`. PR #979 (plan-server PLAN-06 D4) fixed the ROOT cause on the
DAEMON side: the supervisor now cross-checks the child's emitted build-TOON before recording
`job_status`, so a failing routed build classifies `failure` instead of a false `success`. That fix is
correct and covers every known case.

But it leaves a **single point of truth**: `_daemon_result_to_direct` on the client side still trusts
`job_status` verbatim with no independent verification. If the daemon's narrowing ever has a gap — a
build tool whose result TOON uses a different status vocabulary, a `read_log_verdict` miss that returns
`None` and keeps `success`, a protocol-version skew where an old daemon serves a new client — the
client has no second line of defense and would propagate a false green into every
`phase_5.verification_steps` entry, the phase-6 `pre-push-quality-gate`, and the `execute-task`
Handle-Verification loop. On a marshalld-enabled machine those signals are the documented,
machine-read build contract, so a false green there lets a plan reach `create-pr` with its quality gate
never actually green.

This is the flagship archetype — a confident signal that hides the caveat making it wrong — applied to
the routed-build result contract. Close it by making the client independently affirm the routed verdict
against the same job-log the daemon read, and fail closed on disagreement.

## Provenance / already-covered

- The **daemon-side** false-green (exit-0-on-failure classified `success`) is **already fixed** by
  plan-server PLAN-06 D4 (#979) and is the `n=4` flagship-watch data-point already recorded in this
  epic. This plan does NOT re-fix that; it is a pure client-side defense-in-depth backstop that D4
  deliberately did not add — the second line of defense for the window where a daemon could ever lag
  the fix.

## Deliverables

### D1 — GATE: re-trace the routed-result path and the daemon verdict contract

Confirm against `main`: where `_daemon_result_to_direct` consumes `job_status`; what fields the `wait`
status-TOON carries (does it already forward the child TOON's `status`/`exit_code`/`errors[]`, or only
`job_status` + `log_file`?); and whether `cmd_run_common`'s `parser_fn` re-populates `errors[]` from
`log_file` on the routed path today. Mutates nothing. Determines whether the fix is "parse the log the
daemon already pointed at" or "forward a verdict the daemon already computed."

### D2 — client independently affirms the routed verdict (fail closed)

When `job_status == 'success'`, the client MUST NOT return `success_result` on the daemon's word alone.
Either (a) forward the daemon's already-computed log verdict (if D1 finds the `wait` TOON can carry it —
preferred, lossless, no double parse), or (b) re-read the child TOON from `log_file` client-side and
require its `status` to affirmatively agree. On disagreement — `job_status: success` but the log verdict
is not `success` — surface an ERROR, not the success envelope. `timeout`/`killed` legs are untouched.

### D3 — routed-failure `errors[]` fidelity

Verify (and fix if absent) that a routed `failure` carries the same structured `errors[]` diagnostics an
in-process build parses from the log — the report noted the routed result was a fully-formed success
envelope with no `error`/`errors[]` at all. A routed failure should be as legible as an in-process one.

### D4 — regression test: a failing goal returns `status: error` through BOTH execution modes

Assert a deliberately-failing build returns `status: error` under `--execution-mode in_process` AND
under `--execution-mode daemon` (with a stubbed/faked daemon `wait` returning `job_status: success` over
a failure-log, to prove the client cross-check catches a lying daemon). Pins the client-side backstop so
it cannot regress to trusting `job_status` blindly.

## Expected surface

- `script-shared/scripts/build/_build_execute_factory.py` (`_daemon_result_to_direct` + the `wait` TOON
  contract it consumes)
- possibly `build-server-client/**` wait response shape IF D1 finds the verdict must be forwarded there
- the script-shared / build-server test suite (D4)

**Disjointness:** touches the ROUTED-RESULT client mapping in `_build_execute_factory.py` and its tests.
PLAN-42 (#988, SHIPPED) already landed the wait-*mechanism-logging* in this same file — a different
concern on different lines (`_record_resolution`/`_audit_log`), now on `main`, so this is a
build-on-top not a live collision. Disjoint from the three CURRENTLY in-flight plans: PLAN-41
(phase-1-init), PLAN-27 (openrewrite `search-markers`), PLAN-46 (manage-status/platform-runtime title).

## Notes

- **Not a re-fix of the daemon.** D4-on-the-daemon (#979) stays the primary fix; this is the client
  backstop. Reject any framing that reverts to "the daemon should just exit non-zero" (the report's
  option 2 — larger blast radius, callers rely on exit 0).
- **Cross-epic adjacency:** the in-process timeout-truthfulness thread (#909 / plan-optimization PLAN-32
  terminal-status-correctness) is the sibling on the OTHER execution path; if PLAN-32 is still live in
  plan-optimization, this plan's D2 verdict-affirm shape should stay consistent with its shared
  terminal-status contract. Relay owed: report the #909 hoist decision (terminal-status-correctness →
  shared build layer; bound-expiry liveness → daemon-local) to plan-optimization; first check whether
  merged #972 (attach-test-evidence-to-timeout-killed-status) already discharged that half.
