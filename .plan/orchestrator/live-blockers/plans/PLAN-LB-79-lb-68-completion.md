# PLAN-LB-79: The R5 enforcement cannot be walked around with a path-qualified wrapper, an unlisted wrapper or a relative executor

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-79-lb-68-completion.md` and is queued as one row file, `queue/PLAN-LB-79.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-68 (#1814, `7ccd9166f`),
> `landings/PLAN-LB-68.md` § Code defects. Priority is **high**: PLAN-LB-68 is the plan that closed the R5
> side doors, and its merged guard and hook still admit the interpreter call through a path-qualified
> `env`, through unlisted wrappers, through a relative executor run from another directory, and, on Claude,
> through every form in a root session. **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** A Done-when says "fails at `7ccd9166f`" only
> where the behaviour is new at that sha; a clause that already holds says "holds at `7ccd9166f`"; and no
> Done-when is labelled "holds at" while a claim it rests on is still a HYPOTHESIS below. Grade each
> deliverable against THIS spec's Done-when text; an outline that rewrites a Done-when must say so and why.

## Objective

PLAN-LB-68 made the OpenCode guard and the Claude hook admit a deployed bundle script exactly and refuse
several interpreter side doors. Reading the merged code shows the refusal is decided on the raw first token
of a hand-maintained wrapper list, so `/usr/bin/env python3 -c x`, `env -iu FOO python3 -c x`, `ionice`,
`flock`, `zsh -c` and `find -exec` are admitted; the relative executor `.plan/execute-script.py` is admitted
whatever directory the shell is in; the deployed-root admission trusts any path under a broad, hard-coded
set of roots; the consumer scope does not bind a runbook-lane run; and on Claude the hook's R1, R2 and R4
are gated, so a root session in this repository is admitted for forms the guard refuses. This plan makes the
wrapper decision data-driven and shared, makes the admissions exact, and gives both harnesses the same
verdict.

## Deliverables

1. **One shared wrapper table decides the interpreter, and path-qualified and unlisted wrappers cannot hide it.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The wrapper walk looks a program up by its basename, so `/usr/bin/env` and `/usr/bin/timeout` strip like
     `env` and `timeout`.
   - Each wrapper's value options and option clusters come from one table (`env -u/-C/-S`, a cluster such as
     `-iu`, `sudo -D/-p/-R/-T/-u/-g/-h`, and so on), not from the exact option text.
   - The table gains the wrappers and shells found missing: `ionice`, `chrt`, `taskset`, `flock`,
     `script -c`, `watch`, `parallel`, `busybox`, the shells `zsh`, `dash`, `ksh` and `$SHELL -c`, the
     interpreters `pypy` and `pypy3`, and `find … -exec` / `-execdir`.
   - The table lives in ONE data source (a sibling of `r5-allowlist.json`) that `guard.js`, the hook and the
     pin test all read; the two literal copies (`guard.js:159-171`, hook `:537-539`) are removed. This is the
     "one place" PLAN-LB-68 D3 asked for and did not deliver.

   *Done when:* each of these fails at `7ccd9166f`, through the shared parametrised table on `guard.js` under
   node and on the hook:
   - `/usr/bin/env python3 -c x` and `/usr/bin/timeout 5 python3 -c x` are refused;
   - `env -iu FOO python3 -c x`, `sudo -D /tmp python3 -c x` and `sudo -p P python3 -c x` are refused;
   - each of `ionice`, `chrt`, `taskset`, `flock`, `watch`, `parallel` and `busybox sh -c` with an
     interpreter call inside is refused, as are `zsh -c`, `dash -c`, `ksh -c`, `$SHELL -c`, `pypy3 -c x` and
     `find . -exec python3 -c x {} +`;
   - a structural test shows `guard.js`, the hook and the pin read the same table (no second literal list);
   - the 18 rows that exist at `7ccd9166f` still pass (holds at `7ccd9166f`, kept as the preservation guard).

2. **The relative executor, the deployed roots and the consumer scope are admitted exactly.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The relative form `.plan/execute-script.py` is admitted only when the command's effective working
     directory is the repository root: a leading `cd`, `env -C`, `git -C`-style directory change, the OpenCode
     `workdir` and the hook's cwd are all resolved first. The documented form run from the repository root
     stays admitted.
   - The deployed roots come from the same resolver the wizard uses (`bootstrap_plugin resolve`,
     platform-runtime `layout bundle-cache-root`) instead of the hard-coded lists (`guard.js:513-533`, hook
     `:781-813`); roots no harness uses (`~/.agents/skills`, `~/.gemini/config/skills`,
     `~/.gemini/antigravity/skills`, `~/.claude/skills`) are not trusted unless the resolver names them. The
     candidate `{root}/plan-marshall/<any dir>/{entry}` is checked against the resolver's version directory.
   - A path is compared after `realpath`, so a symlinked deployed directory is not trusted lexically.
   - `OPENCODE_CONFIG_DIR` is honoured by `loadAllowList` exactly as by `deployedBundleRoots`.
   - R5 binds a runbook-lane run in a consumer repository. Decide at outline how a lane run is recognised
     when every call carries `workdir` = the main checkout (for example the `git -C` / `--project-dir`
     worktree target or the lane's own marker), and record why.

   *Done when:* each of these fails at `7ccd9166f`:
   - `env -C /tmp/x python3 .plan/execute-script.py`, a shell call with `workdir=/tmp/x` and a preceding
     `cd /tmp/x` followed by `python3 .plan/execute-script.py` are each refused, and
     `python3 .plan/execute-script.py` from the repository root is admitted (this last clause **holds at**
     `7ccd9166f`, kept as the positive control);
   - a script planted under `~/.agents/skills/plan-marshall-marshall-steward/scripts/` is refused when the
     resolver does not name that root, and a symlink out of a deployed root is refused;
   - with `OPENCODE_CONFIG_DIR` set, the deployed bundle script is still admitted;
   - in a consumer fixture, ordinary `python3 x.py` is refused inside a lane run and admitted outside any plan
     context or lane run.

3. **A Claude root session gets the guard's verdict, and R6 names the plan from every commit form.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The hook applies the side-door refusal table of D1 in a root session of this repository as the guard
     does: `true && python3 -c x`, `echo … | python3 -`, `bash -c "python3 -c x"`, `env bash -c …`,
     `uv run python -c x` and `env ./pw verify` are refused, not only in a plan context. Decide at outline
     whether R1, R2 and R4 stay gated and R5 gains its own full scan, or the gating is lifted, and record why.
   - The side-door test runs both `in_context=True` and `in_context=False`.
   - R6 names the plan from `git --git-dir=… --work-tree=…`, `GIT_DIR=…`, and a `-C` target carrying an
     unexpanded variable (refused fail-closed); a subcommand alias defined with `-c alias.…` is resolved or
     refused.

   *Done when:* each of these fails at `7ccd9166f`:
   - every form listed above is refused by the hook in a root session with no plan context;
   - the side-door table has a row set that fails when the hook's gating is restored;
   - from the main checkout, `git --git-dir=.git/worktrees/X --work-tree=.plan/local/worktrees/X commit`
     and `GIT_DIR=… git commit` are refused when that plan is in `6-finalize` with no sanction, and
     `git -C "$WT" commit` is refused (unresolvable target).

4. **The documentation sweep checks the forms the defect class lives in.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - Named placeholders resolve to the **deployed** path that `bootstrap_plugin resolve` returns, in addition to
     the repository-relative form; the generic `{SCRIPT_FILE}` expands over the bundle entries too; `stdbuf`
     joins the sweep's wrapper words from the D1 table; `uv run`, `bash -c` and `./pw` lines are candidates;
     the consumer recovery path in `upgrade-flow.md` that sits in prose is checked; a command turned into a
     comment to escape the sweep is flagged.

   *Done when:* each of these fails at `7ccd9166f`:
   - a doc line prescribing a deployed-form command R5 would refuse is reported;
   - a fixture doc with a `bash -c "python3 -c …"` line and one with `uv run python -c …` is reported;
   - the `upgrade-flow.md` recovery command is part of the swept set.

## Claim Labels

- OBSERVED: the wrapper walk matches the raw token — `.opencode/plugin/guard.js` L325 (`SHELL_WRAPPERS.has(token)`) and `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` L617 (orchestrator spot check at `da0b3ce04`).
- OBSERVED: the wrapper walk consumes a value only for an exact listed option — `guard.js` L354-358, hook L646-649 (landing analysis of PLAN-LB-68).
- OBSERVED: the relative executor is admitted before any root or cwd is consulted — `guard.js` L428, hook L676 (orchestrator spot check).
- OBSERVED: the wrapper list is two literal copies — `guard.js` L159-171, hook L537-539 — plus a pin in `test/plan-marshall/platform-runtime/test_opencode_enforcement.py`.
- OBSERVED: the deployed roots are hard-coded lists — `guard.js` L513-533 and L540-566, hook L781-843; comparison is lexical (`normalizePosixPath`, `posixpath.normpath`), with no `realpath`.
- OBSERVED: `deployedBundleRoots` honours `OPENCODE_CONFIG_DIR` (`guard.js` L517) and `loadAllowList` does not (L608-628).
- OBSERVED: `contextGate` needs the workdir or cwd under `.plan/local/worktrees` — `guard.js` L594-602; a runbook-lane run issues every call with `workdir` = the main checkout (landing analysis of PLAN-LB-68).
- OBSERVED: the hook's R1, R2 and R4 are gated and R5 inspects the first program only — `claude_pretooluse_hook.py` L1329-1334; the side-door test runs `in_context=True` only — `test/plan-marshall/platform-runtime/test_guard_hook_parity.py` L165-166.
- OBSERVED: R6 names the plan only from `-C` — `guard.js` L747-777, hook L1188-1225.
- OBSERVED: the sweep maps named placeholders to repository-relative paths, omits `stdbuf` from `_WRAPPER_WORDS` and skips comment lines — the documentation-sweep test in `test/plan-marshall/platform-runtime/` (landing analysis of PLAN-LB-68, citing L89, L121-134, L238, L296).
- OBSERVED: a forbidden `git grep` from a PLAN-LB-76 self-review sub-agent completed three times (09:02:03, 09:02:07, 09:29:50) and left no `guard.log` line; the guard has no rule for it (landing analysis of PLAN-LB-76, from the harness transcript). D1 decides at outline whether the file-search git verbs (`git grep`, `git -C … grep`) belong to the refusal table or are recorded as outside what the guard enforces; record why either way.
- HYPOTHESIS: the end-to-end bypass inputs in the landing analysis (for example `/usr/bin/env python3 -c x`) are admitted by the running guard and hook, not only by the code reading — confirm by running them as the new D1 and D2 rows against `7ccd9166f` (verify-at-outline).
- HYPOTHESIS: the documentation-sweep test lives in `test/plan-marshall/platform-runtime/` — confirm its path at outline (verify-at-outline).
- HYPOTHESIS: platform-runtime `layout bundle-cache-root` names every deployed root a harness really uses, so the hard-coded lists can be removed without losing the OpenCode flat or Antigravity layouts — confirm at `marketplace/bundles/plan-marshall/skills/platform-runtime/` (verify-at-outline).
- Verify-first clause: decide how a runbook-lane run is recognised for D2 and whether the hook gains a full R5 scan or loses its gating for D3, before either is scoped; record why.

## Expected Surface

- OBSERVED: `.opencode/plugin/guard.js` — the wrapper walk, `isExecutorPermit`, `deployedBundleRoots`, `loadAllowList`, `contextGate`, `gitCommitTarget` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` — the same functions on the hook (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json` and its new sibling wrapper table (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md` (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` (D4)
- OBSERVED: `test/plan-marshall/platform-runtime/` — the guard, hook, parity and sweep tests (D1, D2, D3, D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-68 (shipped, `7ccd9166f`).
- Overlaps with: the staged PLAN-LB-48 and PLAN-LB-49 on the `platform-runtime` tree, PLAN-LB-43 D3 on
  `upgrade-flow.md`, and the running PLAN-LB-45 on `test/plan-marshall/platform-runtime/`. The emit gate
  decides. PLAN-LB-43's recovery admission is the one this plan tightens.
- Adjacent to: the lane's `build-classify` and build-gate sections (PLAN-LB-78), untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-79-lb-68-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
