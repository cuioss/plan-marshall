# PLAN-TRUTH-060: The Daemon's Baseline Interpreter Is Unregistrable and Its Safe Default Unreachable

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-060-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.
>
> Raised 2026-08-07 from a cross-repo operator observation (TokenSheriff: "the build daemon is
> refusing all submits for this project with `wrong_interpreter`"). Corroborated first-party
> against `main` @ `667625ad7` by symbol reading plus a live probe of the running daemon — and the
> corroboration made the finding STRICTLY LARGER than the report: the refusal is **machine-global,
> not project-specific**, and this repository's own builds are subject to it.

## Objective

`marshalld` refuses every submit on this machine with `wrong_interpreter`, and each refusal
degrades to an in-process build that looks like an ordinary successful build. The cause is a
three-part stack in our own code: the verifier has a permissive default for "no baseline
registered", the daemon destroys that default by substituting its own `sys.executable`, and no
registry surface can supply a baseline in the first place — so the parameter the verifier's
docstring calls "the daemon's **registered** baseline interpreter" is registered by nothing. Ship
a baseline-interpreter contract that is either genuinely registrable or genuinely defaulted, with
the doc and the code agreeing, so a build server that is enrolled and answering actually accepts
the builds it was enrolled to run.

## Deliverables

1. **D0 — Re-ground and measure the blast radius.** ⛔ **The condition is currently MASKED** — the
   2026-08-07 upgrade relaunched the daemon under an interpreter that happens to match, so a naive
   "does it work?" check reads green. D0 therefore measures the *mechanism*, not the current mood:
   the daemon's in-process `sys.executable` basename, the `command[0]` clients submit, and the
   accept/refuse verdict for each — **from the interaction-audit log and live submits, NEVER from
   `ps` or from `manage-build-server status`** (both were shown to mislead; see Claim Labels).
   Confirm the baseline is daemon-wide with no per-project component ⇒ when it mismatches, ALL
   enrolled projects are refused. ⛔ Mandatory matched control: a known-bad interpreter must still
   be refused, so "accepted" is distinguishable from "the check stopped firing".
2. **D1 — Stop destroying the safe default.** `marshalld.py:267` (`baseline_interpreter or
   sys.executable`) makes `_marshalld_verifier.py:115`'s `_DEFAULT_INTERPRETER_NAMES` branch
   unreachable from the only production construction site. Either propagate `None` so the
   permissive branch is reachable, or resolve a baseline that a `python3` argv can match. The
   choice is the plan's to make and must be justified against D0's measurement — but a fix that
   leaves the verifier's default branch dead in production has not fixed this.
3. **D2 — Settle the "registered" claim, one way.** Either make `baseline_interpreter` a real
   registry field written by `manage_build_server.py` enrol and read by the daemon, or correct
   every doc that calls it registered. ⛔ Exactly one of the two — shipping both is a contradiction,
   shipping neither leaves the divergence. Includes the module docstring at
   `_marshalld_verifier.py:14-15` and `:50`, whose usage example passes the very value
   (`baseline_interpreter='python3'`) that no caller passes.
4. **D3 — Tests, with a matched positive and negative control.** A test that pins the
   Homebrew-shaped baseline (`…/Python.app/Contents/MacOS/Python`) against a `python3` submit and
   asserts the post-fix verdict, plus a control asserting a genuinely wrong interpreter is STILL
   refused. ⛔ The existing suite passes today while production refuses everything — so the suite's
   population, not just its assertions, is in scope: state why no existing test caught this.

## Claim Labels

- OBSERVED: `_interpreter_ok` accepts only an exact baseline match or a basename match, and falls
  back to `{'python3', 'python'}` ONLY when `baseline_interpreter` is falsy — read at
  `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_verifier.py`
  § `_interpreter_ok` (`:110-115`).
- OBSERVED: the daemon substitutes its own `sys.executable` for an absent baseline — read at
  `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py`
  § `Daemon.__init__` (`:267`).
- OBSERVED: the sole production construction site passes NO `baseline_interpreter`, so the
  substitution always fires — read at `marshalld.py` § `:606`
  (`return Daemon(scheduler=..., journal=..., interaction_audit=...)`). This is an ENUMERATION of
  every `Daemon(` construction site across `manage-build-server/scripts/*.py`, not a sample: the
  sweep returned exactly one row.
- OBSERVED (asserted absence, verified as an absence): `manage_build_server.py` — the enrol/registry
  surface — contains ZERO occurrences of `interpreter`. The sweep covered every `*.py` under
  `manage-build-server/scripts/` and found the token in exactly two files (`_marshalld_verifier.py`,
  `marshalld.py`). ⇒ no registry field for a baseline interpreter exists to be written or read.
- OBSERVED (**empirical, the primary evidence — supersedes any inference from `ps`**): the daemon's
  own `interaction-audit.log`, project-scoped to this repository, records **four
  `request_status: refused` / `reason: wrong_interpreter` submits on 2026-08-07** (18:00:54Z,
  18:40:08Z, 19:09:14Z, 19:12:03Z) and a **successful** `queued → success` submit on 2026-08-01.
  Read via `manage_build_server logs --limit 12`. ⇒ the refusal is real, live, and affects THIS
  repository — not only the reporting one — and it began between those dates.
- OBSERVED: the pre-upgrade daemon (pid 85849) was launched under Homebrew's `python@3.14`, whose
  `sys.executable` is `/opt/homebrew/opt/python@3.14/bin/python3.14` — basename **`python3.14`**.
  Measured by executing that interpreter and printing `sys.executable`. ⇒
  `Path('python3').name == Path(baseline).name` is `'python3' == 'python3.14'` → False →
  `REFUSE_WRONG_INTERPRETER` for every `python3` submit. **This is the mechanism that produced the
  four refusals.**
- ⛔ **CORRECTED 2026-08-07, and the correction is itself a finding.** An earlier reading of this
  claim asserted the baseline basename was `Python`, inferred from `ps -o comm=` / `ps -o args=`.
  **`ps` output is NOT `sys.executable`**: for a framework build macOS reports the
  `Python.app/Contents/MacOS/Python` image path, while CPython computes a different
  `sys.executable` (`…/bin/python3.14` for Homebrew, `…/bin/python3` for the venv). The two probes
  disagree, and only the in-process value is what `Daemon.__init__` stores. ⇒ **D0 MUST measure the
  baseline from the audit log's accept/refuse behaviour and from in-process `sys.executable`, NEVER
  from `ps`.** A control assertion is mandatory: submit a known-bad interpreter and confirm it is
  STILL refused, or an "it works now" reading cannot be distinguished from a check that stopped
  firing.
- OBSERVED (**post-upgrade, matched positive and negative control, 2026-08-07**): after
  `manage-build-server upgrade` relaunched the daemon (pid 83325, cache `0.1.1293` → `0.1.1304`)
  under an interpreter whose `sys.executable` basename IS `python3`, a `python3` submit was
  **accepted** (`queued`, then a routed build `success`, exit 0) while a `/bin/sh` submit was
  **still refused** with `wrong_interpreter`. ⇒ the check is firing correctly; only the baseline
  changed.
- ⭐ OBSERVED (**the sharpened statement of the defect**): the baseline is **whatever interpreter
  the daemon happened to be launched under**, because `_spawn_detached` passes the control verb's
  `sys.executable` (`manage_build_server.py:182`) and `Daemon.__init__` stores it. ⇒ the failure is
  **environment-determined and intermittent**: it appears and disappears across restarts with no
  code change, and **a restart MASKS it rather than fixing it**. That is why the four refusals
  ended without anyone fixing anything, and why this plan is still needed after the upgrade.
- OBSERVED: `manage-build-server status` reported `binary_path: …/0.1.1304/…` while the running
  daemon was `…/0.1.1293/…` (from `ps -p 85849 -o args=`) — `status` reports the version it WOULD
  launch, rendered as the running daemon's. ⛔ **Already owned by `PLAN-TRUTH-005`** (its spec
  records the identical `0.1.1231`-vs-`0.1.1212` observation); recorded here only so this plan does
  not re-file it, and as the reason `status` is not an acceptable D0 measurement surface.
- OBSERVED: the documented client submit form is `["python3", "…/execute-script.py", …]` — read at
  `build-server-client/scripts/build_server.py` § module docstring (`:40`). ⇒ `command[0]` is
  `python3` by contract, so the mismatch is total rather than incidental.
- OBSERVED: a refused submit returns `status: refused` with its reason and writes a WARNING to the
  plan audit log — read at `build_server.py` § `:459-470`. The refusal is therefore NOT silent AT
  THAT SEAM; the operator's "silently falling back" describes the observed end-to-end effect.
- HYPOTHESIS: the refusal is absorbed above `build_server.py`, so a refused submit reaches the
  agent/operator as an ordinary build result — confirm/refute at
  `plan-marshall:build-pyproject` / `_build_execute_factory.py` § `_route_to_daemon` and its
  handling of a `status: refused` return (verify-at-outline). ⛔ This half is DELIBERATELY OUT OF
  SCOPE for this plan (see Dependencies); it is labelled here only so the implementing phase does
  not re-derive it.
- HYPOTHESIS: every enrolled project on the machine is refused, not just TokenSheriff — the
  baseline is daemon-wide state, held once in `Daemon.__init__`, with no per-project component.
  Confirm/refute at `_marshalld_verifier.py` § `verify_submit` (`:210-245`) — check that no
  registry record contributes to the interpreter test (verify-at-outline). This is D0's job.
- Verify-first clause: the mechanism above is grounded at `main` @ `667625ad7` and on a daemon
  running the `0.1.1304` cache binary. A daemon restarted under a different interpreter, or a
  landed change to `manage-build-server`, invalidates the D0 measurement — RE-GROUND before
  scoping, and treat a non-reproducing D0 as a refutation that loops back, not as a pass.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py`:267,
  :606 — `Daemon.__init__`, the production construction site.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_verifier.py`:14-15,
  :50, :110-115, :220 — `_interpreter_ok`, the module docstring, the `verify_submit` docstring.
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py`
  — the enrol/registry surface, touched only under the D2 "make it registrable" arm
  (verify-at-outline).
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-build-server/SKILL.md` — the enrol
  and registry documentation, touched under either D2 arm (verify-at-outline).
- OBSERVED: `test/plan-marshall/build-server/test_marshalld_verifier.py` (13 `baseline_interpreter`
  occurrences) and `test/plan-marshall/build-server/test_acceptance_security_refusals.py` (7) — the
  suites that pass today while production refuses everything.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-TRUTH-005** (`marshalld-self-reload-on-version-signal`) — SAME BUNDLE
  (`manage-build-server`), and TRUTH-005 additionally restarts the daemon. ⛔ SERIALIZE; do not
  pair. ⭐ Note the interaction is not merely a file overlap: TRUTH-005's restart-under-a-new-version
  behaviour is what would silently CHANGE the baseline this plan is fixing, because the baseline is
  whatever interpreter the daemon happened to start under. Whichever runs second must RE-GROUND D0.
- Adjacent to: **PLAN-45** (`routed-verdict-client-crosscheck`) and **PLAN-42** (`waiting-standard
  usage observability`) — both `build-server-client`, untouched here. The refusal-visibility half
  (the HYPOTHESIS above) belongs to that surface, not this one; it is recorded as an epic Open
  Defect lead rather than folded, because no such edit has been made to either spec.
- Adjacent to: `build-server-client/scripts/build_server.py` — read for grounding, NOT modified by
  this plan.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-060-the-daemon-baseline-interpreter-is-unregistrable-and-its-safe-default-unreachable.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
