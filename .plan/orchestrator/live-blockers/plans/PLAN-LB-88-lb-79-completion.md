# PLAN-LB-88: A spliced command, a `cd` inside it and the repository's own commands get the same R5 verdict on both harnesses

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-88-lb-79-completion.md` and is queued as one row file, `queue/PLAN-LB-88.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-79 (#1835, `d60b36f8d`),
> `landings/PLAN-LB-79.md` § Code Defects (C1-C6, C8). Priority is **high**: this is the third completion
> in the chain PLAN-LB-65, PLAN-LB-68, PLAN-LB-79, and each one left the enforcement walkable by the next
> class of input. **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** A Done-when says "fails at `d60b36f8d`" only where the behaviour is new at
> that sha; a clause that already holds says "holds at `d60b36f8d`"; and no Done-when is labelled "holds at"
> while a claim it rests on is still a HYPOTHESIS below. Grade each deliverable against THIS spec's Done-when
> text; an outline that rewrites a Done-when must say so and why.

## Objective

PLAN-LB-79 made the R5 wrapper decision data-driven and shared, and made the relative-executor and
deployed-root admissions exact. Reading what it merged shows the decision still stops at the first
level of shell grammar: a spliced command string is split on `; & | newline` only, so a grouping keyword,
a shell option before `-c`, a here-string or a `cd` inside the string hides the interpreter call or the
working directory from the check, and the relative executor admission it made exact is defeated by the
same shells it added. The hook that gained parity now refuses `./pw generate`, which the repository's own
CLAUDE.md prescribes. This plan closes the class instead of the next instance: the walk either models the
shell constructs it claims to read or refuses what it cannot read, both harnesses give the same verdict on
the same input, and the statements about the enforcement scope are true.

## Deliverables

1. **The spliced-command walk reads the grammar it claims to read, or refuses what it cannot.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Decide at outline, and record why, between (i) extending the segment walk to the constructs it misses
     (grouping keywords `if then else elif fi while until do done case esac`, `{ }`, `( )`, `!`, `time`;
     shell options before `-c` such as `-o pipefail`, `-e`, `-x`; here-strings and here-documents on a
     table shell; a table shell given a script file) and (ii) a fail-closed floor: a table shell given a
     command string or stdin that names an interpreter token ANYWHERE is refused, with (i) only deciding the
     executor admission. The recommendation is (ii) as the floor, because (i) alone restates the problem
     as a longer list.
   - `fish`, `csh`, `tcsh` join the shared table; the R2 spawn set is derived from the same table and no
     second literal shell list remains in either implementation.
   - The new rows are a generated cross-product (every table wrapper and shell against every construct
     above), not a hand-picked list, so a wrapper added later is covered by construction.

   *Done when:* each of these fails at `d60b36f8d`, through the shared parametrised table on `guard.js`
   under node and on the hook:
   - `zsh -c 'if true; then python3 -c x; fi'`, `zsh -c '(python3 -c x)'`, `zsh -c '{ python3 -c x; }'`,
     `zsh -c '! python3 -c x'` and a `for … do python3 -c x; done` string are refused;
   - `zsh -o pipefail -c 'python3 -c x'`, `zsh <<< 'python3 -c x'` and `zsh script.zsh` with an
     interpreter call inside a fixture script are refused;
   - each of `fish -c`, `csh -c` and `tcsh -c` with an interpreter call inside is refused;
   - a structural test shows neither implementation carries a second literal shell list and the R2 spawn
     set equals the table's shells;
   - the cross-product test fails when one table wrapper or one construct is removed from its data source.

2. **A `cd` inside a spliced string is applied, and the executor admission has no vacuous or over-wide case.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The effective working directory is computed across the spliced segments in order, so
     `zsh -c "cd /tmp/x; python3 .plan/execute-script.py …"` is judged from `/tmp/x`.
   - The plan-worktree exemption admits exactly `.plan/local/worktrees/{plan}` (one level), and neither
     `.plan/local/worktrees/_orchestrator` nor a sub-directory unless outline records why.
   - With `CLAUDE_PROJECT_DIR` unset the hook's repository root is derived from its own location or the
     call is refused as unresolvable; it is never the payload cwd, which makes the check vacuous.
   - Decide at outline whether the unversioned `{root}/plan-marshall/{entry}` candidate stays accepted
     (guard L823, hook L1112); record why. The lane marker binds R1-R5 for the whole checkout for 24 hours
     after any `rb-*/progress.md` write: decide whether that scope is intended or narrows to the lane's
     own session, and record why.

   *Done when:* each of these fails at `d60b36f8d`:
   - `zsh -c "cd /tmp/x; python3 .plan/execute-script.py plan-marshall:… "` is refused for each shell in
     the table, on both harnesses;
   - the relative executor from `.plan/local/worktrees/_orchestrator` and from a sub-directory of a plan
     worktree is refused, and from `.plan/local/worktrees/{plan}` is admitted (this last clause **holds
     at** `d60b36f8d`, kept as the positive control);
   - a hook call with `CLAUDE_PROJECT_DIR` unset and a cwd that is not the repository root refuses the
     relative executor.

3. **The two harnesses give the same verdict on the repository's own documented commands, and an absent table refuses a spliced interpreter.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `./pw generate` (CLAUDE.md § Multi-Assistant Support) gets one verdict on the guard and the hook:
     decide at outline whether R4 admits the `generate` verb of the wrapper or both refuse it and the
     document changes, and record why. The decision is data in one place, not a branch in each file.
   - A shared row set of the repository's documented commands (`./pw generate`, `python3
     .plan/execute-script.py …`, the build commands the executor resolves) is run through both
     implementations and must agree.
   - The missing-table branch (guard L1432-1442, hook L1362-1371) checks the command string for an
     interpreter, not only raw tokens, so a spliced interpreter is refused with the table absent.
   - D1 of PLAN-LB-79 asked for a decision on `git grep` and `git -C … grep` and none was recorded:
     decide here whether the file-search git verbs join the refusal table or are recorded as outside what
     the guard enforces, and write the decision with its reason in `pretooluse-enforcement.md`.

   *Done when:* each of these fails at `d60b36f8d`:
   - the shared documented-command rows return the same verdict on the guard under node and on the hook,
     and `./pw generate` is among them;
   - with `r5-wrappers.json` absent, `zsh -c "python3 -c x"` is refused on both harnesses;
   - `pretooluse-enforcement.md` carries the `git grep` decision and a doc test asserts the sentence
     exists.

4. **The statements about the enforcement scope are true.**
   - Skills: pm-plugin-development:plugin-architecture, pm-documents:ref-documentation, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-documenter
   - `CLAUDE.md` § Standalone Plan Lane says the PreToolUse hook's context gate "fires only inside a plan
     context" and that the lane's hard-rule relaxations therefore "neither bind nor are enforceable"; since
     PLAN-LB-79 D3 the hook binds a root session of this repository. The row is rewritten to what is true
     and keeps the lane's reason for the relaxations (a fresh clone has no hook installed).
   - `pretooluse-enforcement.md` states the scope exactly: the three signals, the repository marker, the
     24-hour lane marker, and which harness each applies to.
   - The Claude hook is not installed in this checkout's `.claude/settings.local.json` and no cached hook
     references the new table: record in the document how an operator verifies installation, and do not
     claim a binding the install does not provide.

   *Done when:* doc tests assert that `CLAUDE.md` no longer says the gate fires only inside a plan context
   and that the enforcement document names each scope signal and the installation check; each fails at
   `d60b36f8d`.

Split guard: four deliverables, one subsystem (`guard.js`, the hook, the shared table and their tests).

## Claim Labels

- OBSERVED: `splicedSegments` splits only on `;`, `&`, `|` and newline, quote-aware — `.opencode/plugin/guard.js` L344-380 (read by the orchestrator at `d60b36f8d`); the hook's counterpart is L662-697 (corroboration read, not re-read).
- OBSERVED: a segment that begins with a grouping keyword leaves the keyword at token 0, so the wrapper strip stops and R5 names no interpreter — by reading `guard.js` L344-380 and the hook L662-697 (corroboration, mechanism re-read in `guard.js`); not executed.
- OBSERVED: `effectiveCwd` stops at the splice and never applies a `cd` inside the string — `guard.js` L628-630 and the hook L911-914 (corroboration read, not re-read).
- OBSERVED: the R2 spawn sets contain only `sh`, `bash` and `source` — `guard.js` L135-138, hook L199 (corroboration read, not re-read).
- OBSERVED: with the table absent, both implementations refuse only when a RAW token is an interpreter — `guard.js` L1432-1442 (re-read) and hook L1362-1371 (corroboration read).
- OBSERVED: the hook's R4 refuses every `./pw` — `claude_pretooluse_hook.py` L529-537 (re-read); the guard admits `./pw generate` — `guard.js` L1406-1415 (corroboration read, not re-read).
- OBSERVED: `_is_this_repository` decides on the marker file under `CLAUDE_PROJECT_DIR` or the payload cwd, falling back to the hook's own location only when neither exists — hook L1005-1021 (re-read); the hook's root falls back to the payload cwd at L1263 (corroboration read).
- OBSERVED: the plan-worktree exemption is a realpath plus a `worktrees/` prefix with a slash boundary and admits any depth below it — `guard.js` L564-570, hook L827-842 (corroboration read, not re-read).
- OBSERVED: both implementations accept the unversioned `{root}/plan-marshall/{entry}` candidate — `guard.js` L823, hook L1112 (corroboration read, not re-read).
- OBSERVED: no decision on `git grep` is recorded in `r5-wrappers.json`, `pretooluse-enforcement.md`, the PR body or the run's progress file, and `guard.js` has no `git grep` rule — corroboration read of PLAN-LB-79's artifacts.
- HYPOTHESIS: the forms listed in D1's Done-when are admitted by the running guard and hook, not only by the code reading — confirm by running them as the new rows against `d60b36f8d` (verify-at-outline). Nothing in the landing analysis was executed.
- HYPOTHESIS: no cached Claude hook references `r5-wrappers.json` and `.claude/settings.local.json` carries no `claude_pretooluse` entry — confirm at `~/.claude/plugins/cache/plan-marshall/` and `.claude/settings.local.json` before D4 words the installation check (verify-at-outline).
- Verify-first clause: decide D1's option (i) versus (ii) and D3's `./pw generate` verdict before either is scoped; record why.

## Expected Surface

- OBSERVED: `.opencode/plugin/guard.js` — `splicedSegments`, `effectiveCwd`, the missing-table branch, the R4 build check, the worktree exemption (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` — the same functions on the hook (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-wrappers.json` — shells added, the R2 spawn derivation (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md` (D3, D4)
- OBSERVED: `CLAUDE.md` — the Standalone Plan Lane gate sentence (D4)
- OBSERVED: `test/plan-marshall/platform-runtime/` — the wrapper-table, exact-admission, root-session and hook-parity tests (D1, D2, D3, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/deployed-layout.json` and `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` — only if the unversioned candidate is removed at the resolver and not at the two callers (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-79 (shipped, `d60b36f8d`).
- Overlaps with: PLAN-LB-69 declares the `platform-runtime/scripts/` directory as a hypothesis for its
  session-store reader, which contains the hook; no shared function. The emit gate decides. No overlap
  with PLAN-LB-83, PLAN-LB-84 or PLAN-LB-86 (`opencode_runtime.py`, not touched here).
- Adjacent to: PLAN-LB-89, which owns the lane's improvised recipes (base-sha evidence, thread replies);
  this plan does not edit the lane skill.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-88-lb-79-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
