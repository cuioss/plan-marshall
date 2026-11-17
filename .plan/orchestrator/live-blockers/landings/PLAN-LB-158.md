# Landing Analysis: PLAN-LB-158 — Stale ledger statements, the package-phase zero-test guard, and a refusal that names its row

epic: live-blockers
workstream: WS-01
pr: #2009 (https://github.com/cuioss/plan-marshall/pull/2009)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-158.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-158-follow-ups-ledger-docs-package-guard-root-diagnostic`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `68b2c719e2d2817a222063525f3f3a521a00f2d4` through the merge queue (merge-group run 44136673945). Message
`rb-lb-158-follow-ups-ledger-docs-package-guard-root-diagnostic-001.md` carries `total_tokens=unknown` (out of scope under the standing ruling),
`self-review:clear` after three rounds, and `deliverables_done=4` of 5.

## Deliverable Fidelity vs Spec

Corroborated against `origin/main` at the merge commit: the diff stat (27 files, 587 insertions, 114 deletions) and a read of the merged diff of
`_maven_execute.py`, `_cmd_pre_commit_verify_freshness.py`, `_build_cli.py`, `_build_execute_factory.py`, `_build_shared.py`, `_pyproject_execute.py`,
`plugin_discover.py`, `_freshness_crosscheck.py`, `_ledger_core.py`, `canonical-commands.md`, `build-api-reference.md` and the four documentation
corrections of D1. The three test files were checked by name and by the lane's mutation runs only.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 correct the stale statements | shipped-as-specified, with scope growth | `manage-change-ledger/SKILL.md` (the Prohibited bullet now names the first-parent diff for a merge commit; the producer row for `manage-status` names the per-SHA `append` invocations beside `remap`), `workflow-integration-git/SKILL.md` (target-tree ledger, merge-commit case, the resolver note now names the `commit` verb's TARGET-anchored write), `execution.md` (the verb is the third row owner), `_ledger_core.change_record` docstring — all re-read in the diff. Growth: the changed-path commands in four documents now read `-z --root` (CodeRabbit findings), see L3-3 |
| D2 a `module-tests` run leading with `package` and no summary or fresh report is `indeterminate`; a plain `package` / `quality-gate` / `verify` keeps its behaviour; the identity travels through the `command_key` channel | shipped-with-deviation (operator-decided) | the guard arm exists (`_maven_execute.py`, `elif _is_module_tests_canonical(canonical)`), the requested-skip marker is honoured on both forms, and the `test`-phase branch is untouched. **The mechanism differs from the spec:** the spec's HYPOTHESIS that `command_key` carries the canonical name was REFUTED by the lane (`compute_command_key` yields `maven:package_-pl_...`), so a new `--canonical` channel was threaded and the operator chose it. Limit paragraphs in `maven-impl.md` and the `_parse_module_entries` docstring narrowed |
| D3 tests for the guard | shipped-as-specified (lane-reported) | three named guard tests, a `cmd_run` forwarding test and a test that every bundle command carries its identity; `mutation-after` run recorded with the guard arm removed. Not read in full |
| D4 the refusal names plan, row, field, and says the pre-fix executor writes the null | **not met as written; met in true form** | the naming clauses are met: `_refused_rows_named` names `#{ledger_index} ({notation})`, the message names the plan and the field `worktree_root`. The mandated sentence ("a row written by an executor generated before the writer fix carries the null, so regenerating the executor is part of the remedy") is **absent because it is false** — see L1-1 |
| D5 tests for the refusal and docs | shipped-as-specified (lane-reported) | `test_the_unreadable_root_refusal_names_the_plan_the_row_and_the_field`, `test_every_refusal_route_names_its_own_cause` (route set derived from `_REFUSAL_ROUTES`), the doc pin for the `manage-tasks/SKILL.md` row |

**Scope additions beyond the spec's Expected Surface**, all consequences of D2's new channel unless noted: `script-shared/scripts/build/_build_cli.py`
(`--canonical` on the shared `run` subparser, so all four build tools accept it), `_build_execute_factory.py` and `_build_shared.py` (the flag is read and
every canonical string now ends `--canonical {name}`), `build-pyproject/scripts/_pyproject_execute.py` (the self-heal wrapper forwards it on both calls),
`manage-tasks/scripts/_freshness_crosscheck.py` (`--canonical` joins the recorded-flag table), `pm-plugin-development` `plugin_discover.py` (its own canonical
strings), `extension-api` standards (three documents), `build-maven/SKILL.md`, `phase-5-execute/SKILL.md`, and seven test files. The spec named eleven surfaces;
the merge touches 27 files.

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — the guard, the new flag path and the refusal text, read on the merged tree. By reading: no build,
no test run.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | spec D4: "a row written by an executor generated before the writer fix carries the null" | checked | **refutes** | `_ledger_core.py:289-295`: a keyword left at `NOT_GIVEN` contributes NO key; only an explicit `None` writes a `null`. A pre-fix executor passes no tree fields, so its row is the absent-key legacy shape, which the gate admits. A present `null` is a failed capture on a current writer. The sentence was mine: it was written into the spec's deliverable text, not labelled a HYPOTHESIS, and not re-read at HEAD before staging. The lane found it, took it to the operator, and shipped the true text |
| L1-2 | spec D2 HYPOTHESIS: `command_key` carries the name `module-tests` | checked | refutes | labelled as a HYPOTHESIS with a verify-at-outline clause, so the process caught it; the lane refuted it before writing code |
| L1-3 | OBSERVED: `apply_zero_test_guard` returns a leading `package` result unchanged | checked | confirms | the `else: return result` arm is the one the new `elif` precedes |

**Layer 1 verdict:** two spec claims refuted, one of them a staging error of the orchestrator's. Both were caught inside the plan and neither reached shipped
behaviour.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file | Verdict |
|-------------|------------|--------------------|------------------|---------|
| D1 | the four documents plus the docstring | none by design (documentation); the lane verified each corrected statement against the merged code | none | checked |
| D2 | `--canonical` parsed in `_build_cli.add_run_subparser`, read in the factory (`canonical = getattr(args, 'canonical', None)`), passed to the in-process leg, forwarded by `_selector_miss_guard` and the pyproject self-heal wrapper, read by `apply_zero_test_guard`. A routed build re-enters the factory inside the daemon child on the same argv, so the child parses the flag itself | `mutation-after`: guard arm removed fails with `'success' == 'indeterminate'` at `test_maven_execute.py:927` (log named) | the plumbing files above | checked |
| D4 | `_refusal_reason(refused, gate_root, plan_id)`, `_refused_rows_named` | `test-first`: fails at the base with "the refusal must name the plan it is about" (log named) | none | checked |
| D3, D5 | the test files | the runs above | none | lane-reported |

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_build_shared.build_canonical_commands`, `_build_cli.add_run_subparser` | a project whose generated executor predates this change meets a canonical string carrying `--canonical` | the stale executor validates against the argparse surface embedded when it was generated and refuses with `invalid_invocation` / `unknown_flag` (exit 2). The merge documents the obligation in `build-api-reference.md` ("adding a flag to the run surface obliges an executor regeneration"). On this repository the installed copy predates the merge, so nothing breaks until `/apply-changes` runs, which regenerates the executor in the same run. Every consumer project of plan-marshall carries the same obligation on upgrade | **major for consumers, documented**: the release needs an operator note; no code path softens it |
| L3-2 | the guard's reach | a `module-tests` command persisted in a project's architecture data before this change | the string lacks `--canonical`, so it claims no canonical and keeps the compile-and-package reading: the guard is inert for that command until the map is rebuilt. The Maven overlay path re-emits the string at resolve time (`test_cmd_resolve.py` asserts `--canonical module-tests` on the merged map), so the reactor-root case is likely covered at once. Not traced for a stored `commands` entry that the overlay does not replace | not shown by reading |
| L3-3 | the changed-path commands in `phase-5-execute/SKILL.md`, `execution.md`, `manage-change-ledger/SKILL.md` | an agent reading `git diff-tree ... -z` output through the Bash tool | the tool renders the NUL separators as spaces (probed here with five paths), so the agent sees a space-separated list. A path with a space is ambiguous again; the `-z` buys protection against git's quoting of a non-ASCII path, and nothing against a space. The instruction to "read NUL-terminated entries" cannot be followed literally through a tool that does not show the NUL. Scope growth the spec did not ask for, taken from review findings | minor |
| L3-4 | `_STALE_ROOT_UNREADABLE` text | a present `null` root | the message states the absent-key legacy shape is admitted and a `null` is a failed capture, names the plan and each refused row, and points at the tree the build is dispatched against. It does not tell the operator to regenerate the executor, correctly | info, correct |
| L3-5 | the lane's own report | `deliverables_done=4` | the message states D4 is "not fully met as written" and the mechanism of D2 differs; both are decisions of the operator in the lane, recorded. The ledger row is `shipped`, not partial | info |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (the lane reports 34 123 tests at the final head and a green
merge-group run), the three mutation runs, and the guard against a real Maven reactor-root `module-tests` run that collected nothing. No run was made here.

**Layer 3 verdict:** no blocker. L3-1 is the one finding that needs an operator action beyond this repository, and it is documented by the change itself.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only, no duplication | conforms | the corrected statements state the merged behaviour |
| CLAUDE.md Commit Trailer | exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>` | conforms after a correction | one commit carried a wrong trailer email and was amended before the push (self-reported); the pushed commit is correct |
| CLAUDE.md Workflow Discipline | no wholesale staging | deviates (self-reported) | one `git add -A`; the staged set was checked to be exactly the 17 intended files before the commit. No other staging was wholesale |
| `pm-dev-python:python-core` | typed signatures, explicit forwarding | conforms | `canonical: str | None = None` on every wrapper signature, forwarded on every inner call, with the wrapper contract updated to name three forwarded values |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: about 35 builds, all `daemon_longpoll`; one routed `verify` returned a live `running` result and was re-attached with a bounded wait; one build call
  was rejected by argparse (a value with spaces) and changed no state. The learned build timeout moved from 1915 s to 1247 s during the run.

## Routing and Merge Behavior

- Review: CodeRabbit (required, `review_complete_after_handling`) reviewed `5e8195ea0`, the final head, with eight inline findings: five fixed, three answered with a stated
  reason (finalize ledger re-check, `--no-renames`, the lossy comma-joined `--changed-paths`), each a pre-existing gap outside the surface. Sourcery (optional) refused on quota.
  Not independently re-run here.
- CI/merge: `verify` ran on every pushed head and the merge-group run passed; queue merge.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-159 on declared-disjoint surfaces; no collision reported, and the two diffs share no file.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-158 --status shipped`
- [x] row `pr` stamped — `2009`
- [x] row `landing` stamped — `landings/PLAN-LB-158.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-158-follow-ups-ledger-docs-package-guard-root-diagnostic` (from the sender)
- [x] `epic.md` narrative: one Decision bullet for the landing, including the staging error
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- **Executor regeneration IS owed** — unlike the two earlier landings, this change adds a flag to the shared `run` surface, so `/apply-changes` is owed again (it
  regenerates the executor in the same run). The previous run predates this merge.

## Follow-Ups

- **L3-1 (every consumer needs an executor regeneration on upgrade)** — recorded here with the operator note. Not a plan: the merged documentation states the obligation.
- **L3-2 (a persisted map without `--canonical` keeps the guard inert)** — recorded here; trace a stored `commands` entry the overlay does not replace after the
  apply, with one `architecture resolve` read of a `module-tests` command.
- **L3-3 (`-z` rendered as spaces)** — recorded here; candidate for the small documentation plan below.
- **The lane's residue, none staged without the operator's word** (each is pre-existing and outside this plan's surface):
  - the `6-finalize` completion path does not re-check the change ledger after a failed `ledger_record_change`;
  - `--no-renames` is absent from the writer's merge enumeration, so a merge rename records only the new path;
  - `--changed-paths` is comma-joined and lossy for a path containing a comma;
  - npm's chained `verify` carries no canonical identity;
  - `tools-script-executor/standards/cwd-policy.md` and its five siblings still describe the main-anchored exception as the only departure from cwd-relativity
    — the same class of stale statement D1 corrected, and the one item here that is a documentation fix rather than a behaviour change;
  - one stale comment remains in `test_source_commit_gate_commit_path.py` ("outside both settlement owners").
- **Spec-authoring note for future staging:** a sentence that states what a past executor, writer or reader DID is a claim to re-read at HEAD, however confident the
  paraphrase; it takes a claim label like any other.
