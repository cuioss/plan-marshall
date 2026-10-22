# PLAN-LB-81: The runtime stamp keeps the variant, is refreshed at landing, and never lies by omission

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-81-lb-45-completion.md` and is queued as one row file, `queue/PLAN-LB-81.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-45 (#1802, `137986c61`),
> `landings/PLAN-LB-45.md` § Code defects 2-7. Priority is **medium**: the stamp exists and the plan-marshall
> producer emits it, but it drops the measured variant, is taken once at plan start, can survive a failed
> preflight from an earlier run, and the database reader has three small robustness gaps. The runbook lane's
> missing keys are PLAN-LB-78 D3; the OpenCode 2 detection signal shipped with PLAN-LB-48 D4 (#1830: `OPENCODE` is the only ambient signal); the token totals are
> PLAN-LB-49. **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** A Done-when says "fails at `137986c61`" only where the behaviour is new at
> that sha; a clause that already holds says "holds at `137986c61`". A clause whose premise this spec labels
> HYPOTHESIS gets no "holds at" label until the hypothesis is settled.

## Objective

A cross-model comparison needs each landing to say which model, at which variant, with which effort, produced
the run. After PLAN-LB-45 the landing says the model without its variant, takes `effort` from the model's own
report although the measured variant is in hand, measures once at plan start so a later switch is invisible,
and leaves a previous run's stamp in place when the collector fails. This plan makes the stamp complete,
current and loud about what it could not read.

## Deliverables

1. **The landing carries the measured variant, and effort is measured where the harness measures it.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_PREFLIGHT_METADATA_FIELDS` (`orchestrator.py`) gains `variant` (and `provider` when the collector reports
     it), so `emit-landing` writes `model` in the `{model}/{variant}` list form `landing-payload-spec.md`
     specifies. On OpenCode, where the collector measures the variant, `effort` is taken from it with
     `effort_source: measured`; the LLM's self-report stays the source only where nothing is measured. Decide at
     outline whether a measured variant and a self-reported effort that disagree is reported as a mismatch
     field, and record why.

   *Done when:* each of these fails at `137986c61`:
   - a single-model OpenCode fixture tree (`deepseek-v4.1-flash` / `high`) stamps `variant: high` into the plan
     metadata and `emit-landing` writes `model=deepseek-v4.1-flash/high`;
   - the same fixture stamps `effort: high` with `effort_source: measured`, and a call passing
     `--effort low` on that tree does not override it;
   - a `mixed` tree writes the distinct `{model}/{variant}` labels as the comma-separated list.

2. **The stamp is refreshed at landing time.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Preflight runs once at `phase-1-init` 8a.6 and `emit-landing` reads that snapshot, so sessions that run
     after the start are never measured and `mixed` can almost never appear. Decide at outline whether
     `emit-landing` (or the finalize step before it) re-runs the measured read and merges it into the
     stamp, and record why; a re-read that cannot reach the database keeps the start-time value and says so
     with its source (`measured_at_start`).

   *Done when:* each of these fails at `137986c61` (verify-at-outline for the Hypothesis below):
   - a fixture whose tree gained a second model after plan start yields `model=mixed` with both labels in the
     landing, where the start-time stamp had one;
   - a landing-time read that cannot reach the database keeps the start-time value and the landing marks it
     as start-time;
   - a tree unchanged since the start yields the same value as before (this clause **holds at**
     `137986c61`, kept as the regression guard).

3. **A failed preflight leaves no stale stamp, and a failed stamp is visible.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `cmd_preflight` clears the runtime keys of the plan's metadata before the collector runs, or on its
     failure, so a previous plan id's or a previous attempt's model and effort cannot survive a degraded
     result (today the degraded return at `orchestrator.py` L6686-6688 precedes the stamp and its clearing).
   - `phase-1-init` step 8a.6 branches on `metadata_stamped: false` as well as `degraded: true` and prints a
     warning naming the reason, so a landing's `unknown` has a trace in the plan's log.
   - On OpenCode with `OPENCODE_SESSION_ID` unset, the collector reports why the model is omitted
     (`no_session_id`) instead of omitting it silently.

   *Done when:* each of these fails at `137986c61`:
   - a preflight whose collector fails after a previous successful stamp leaves the runtime keys absent, not
     the previous values;
   - `metadata_stamped: false` with `degraded: false` makes step 8a.6 emit a warning (doc-contract test on the
     branch, plus a script test of the returned field);
   - a collector call on OpenCode without a session id returns the omission reason.

4. **The database reader is robust, and the tests that guard the stamp can fail.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The read-only URI is built with a percent-encoded path (a path containing `?`, `#` or `%` is read, not
     mis-parsed); `_default_opencode_db_path` honours `XDG_DATA_HOME`; the session-tree query is bounded to the
     tree (a recursive query over `parent_id`) rather than a scan of every project's sessions.
   - A deployed OpenCode layout fixture (the flat tree and the bundle-cache tree) proves `bundle_version` reads
     the deployed `plugin.json`, not the source placeholder (self-review F6 of PLAN-LB-45, dropped).
   - The vacuous tests are replaced: the preflight test goes through the router's argv path instead of a
     monkeypatched `subprocess.run`; the manifest-replacement test does not depend on the ambient install and
     its second assertion at `test_runtime_info.py` L494 asserts something; the D5 tests that pass at the base
     are either removed or reduced to the clause they can fail for.

   *Done when:* each of these fails at `137986c61`:
   - a database path containing `?` or `%` is read;
   - with `XDG_DATA_HOME` set the default path follows it;
   - the deployed-layout fixtures yield the deployed bundle's version;
   - each replaced test fails under a mutation of the code it names, run and recorded (`order=mutation-after`
     acceptable and labelled).

## Claim Labels

- OBSERVED: `_PREFLIGHT_METADATA_FIELDS` lists `harness`, `harness_source`, `model`, `models`, `model_source`, `effort`, `effort_source`, `bundle_version`, `executor_version` — no variant or provider — `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` L6388-6398 at `137986c61` (read by the orchestrator).
- OBSERVED: `landing-payload-spec.md` L120-124 specifies `model` as a `{model}/{variant}` list — `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (read by the orchestrator).
- OBSERVED: PLAN-LB-45's own landing reads `effort=high` although the landing-time `runtime-info` returned no `effort` key; the value came from the variant (landing analysis of PLAN-LB-45).
- OBSERVED: `cmd_preflight` returns degraded before the stamp call and the key clearing, so a previous run's keys survive a collector failure — `orchestrator.py` L6452, L6686-6695 (landing analysis of PLAN-LB-45, read by the corroboration; not re-read by the orchestrator).
- OBSERVED: `phase-1-init/SKILL.md` L859-866 branches only on `degraded: true` (same source).
- OBSERVED: the database URI is `f'file:{db_path}?mode=ro'` with no percent-encoding, the query scans all sessions, and the default path ignores `XDG_DATA_HOME` — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py` L253-255 and `opencode_runtime.py` L352-361 (same source).
- OBSERVED: `test_the_executor_version_stays_optional` and `test_a_block_carrying_all_four_is_complete` pass at the base; the preflight tests monkeypatch `subprocess.run` — `test/plan-marshall/plan-orchestrator/` (same source).
- HYPOTHESIS: `emit-landing` reads only `status.metadata` and never re-measures — confirm at `phase-6-finalize/standards/emit-landing.md` Step 1 item 5 (verify-at-outline); D2's clauses are labelled after it is settled.
- HYPOTHESIS: the collector reports the variant as a separate field the metadata writer can take (`variant` in the `runtime-info` payload) — confirm at `runtime_info.py` and the landing-time reading in `landings/PLAN-LB-45.md` (verify-at-outline).
- Verify-first clause: decide whether the landing-time re-read lives in `emit-landing` or in a finalize step, and whether a measured/self-reported effort disagreement is reported, before D1 and D2 are scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `_PREFLIGHT_METADATA_FIELDS`, `cmd_preflight`, the stamp and clearing (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py` — the OpenCode reader, effort source, the omission reason (D1, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — the default database path (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` — step 8a.6 branching (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` — the stamp read (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the `model` and `effort` rows (D1, D2)
- OBSERVED: `test/plan-marshall/platform-runtime/test_runtime_info.py` (D1, D3, D4)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_preflight_client_toon.py` and `test_landing_completeness.py` (D1, D2, D3, D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-45 (shipped, `137986c61`).
- Overlaps with: the staged PLAN-LB-78 D3 on `landing-payload-spec.md` (one file), PLAN-LB-49 on the `platform-runtime` tree, and PLAN-LB-79 on `test/plan-marshall/platform-runtime/`. PLAN-LB-48 shipped (#1830) and moved `opencode_runtime.py`: re-read every line reference in the Claim Labels against `main` at outline. The gate will ask.
- Adjacent to: PLAN-LB-49 D1's `session_v2` reader, which this plan's D4 hardens and which PLAN-LB-49 later absorbs; the OpenCode 2 detection signal shipped with PLAN-LB-48 D4.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-81-lb-45-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
