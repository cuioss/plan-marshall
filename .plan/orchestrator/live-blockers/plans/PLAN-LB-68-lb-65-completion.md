# PLAN-LB-68: Enforcement that does not break the steward — admit deployed bundle scripts exactly, name the plan from `git -C`, close the R5 side doors

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-68-lb-65-completion.md` and is queued as one row file,
> `queue/PLAN-LB-68.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-18 from the PLAN-LB-65 landing (`landings/PLAN-LB-65.md`), high only.
> Fix-forward: PLAN-LB-65 (`d3e9c2544`) is kept. **Each deliverable is its own outline
> deliverable, and each Done-when is its own success criterion. Do not merge them.** Every
> Done-when is a test that is **run and seen failing at `d3e9c2544` before the fix**. Log the red
> run, then the green.

## Objective

PLAN-LB-65 made R5 apply in every session and made the allow-list exact and
repository-relative. Two problems remain.

- **It broke the steward on OpenCode.** The wizard and the steward run their bootstrap scripts by
  the path `bootstrap_plugin resolve` returns, which is the deployed bundle outside the
  repository. Those paths never match a repository-relative entry, so `/marshall-steward`
  is refused on every re-run wherever `guard.js` is installed. A consumer also has no admissible
  executor recovery.
- **The enforcement still has holes:**
  - R6 cannot name the plan for the canonical `git -C {WORKTREE} commit` form;
  - several interpreter forms slip past R5;
  - the executor permit is suffix-matched.

## Deliverables

1. **R5 admits a deployed bundle script exactly, and the steward runs again on every guarded
   harness.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - An invocation is admitted when its resolved script path equals
     `{deployed bundle root}/{bundle-relative entry}` for an allow-list entry.
     - `{deployed bundle root}` comes from the same resolver the wizard uses (`bootstrap_plugin
       resolve`, platform-runtime `layout bundle-cache-root`, the flat OpenCode / Antigravity
       layout).
     - The match stays exact: never a basename, never a suffix, never a bare cache prefix.
   - The allow-list gains a bundle-relative form for each steward, wizard and recovery script,
     with each entry citing its documenting line:
     - `determine_mode.py`, `gitignore_setup.py`, `bootstrap_plugin.py`;
     - `permission_fix.py`;
     - `generate_executor.py`, the consumer recovery that PLAN-LB-43 D3 builds on.
   - **Scope in consumer repositories** (medium, same surface; decide at outline and record):
     R5 must not refuse a consumer's ordinary Python work (`python3 x.py`, `python3 -m venv`,
     `python3 -m pip`) outside a plan context or a runbook-lane run. It must still bind inside
     one. Recommended: bind R5 when the session is in a plan context or a lane worktree, and in
     every session of this repository.
   - Remove the `"{GENERATE_EXECUTOR}"` placeholder dodge in `upgrade-flow.md` and
     `tools-script-executor/SKILL.md`. The docs show the real, admitted command. Correct
     `opencode.adoc:174`, `platform-runtime/SKILL.md:107` and the hook docstring (`:798`).

   *Done when:* each of these tests fails at `d3e9c2544`:
   - in a fixture with a plugin only in a deployed cache or flat layout, the guard **and** the
     hook admit `python3 {resolved}/skills/marshall-steward/scripts/determine_mode.py mode` and
     the cache-path `generate_executor.py generate`;
   - both refuse `python3 /tmp/x/skills/marshall-steward/scripts/determine_mode.py`;
   - both refuse a same-named script under a non-deployed directory;
   - in a consumer fixture outside a plan context, `python3 -m pip install x` is admitted, and
     refused inside a plan worktree (or as recorded at outline);
   - the doc sweep checks resolved-path templates rather than skipping them, and it fails on any
     prescribed command R5 would refuse.

2. **R6 names the plan from the `git -C` target, on both harnesses.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `isGitCommit` and the hook's equivalent return the `-C` value.
   - The plan is named from that path when it lies under `.plan/local/worktrees/{plan}`, before
     the `workdir`, project-root and cwd fallbacks.
   - On Claude, R6 also runs for a main-context session committing into a worktree whose plan is
     in phase 6. It is not gated behind the plan-context gate.
   - The R6 tests use `manage-status` fixtures, not hand-written `status.json`.
   - Restore `test_plan_only_commit_passes`'s dropped `assert _commit_count(tmp_path) == 2`.
   - A hook test no longer depends on `CLAUDE_PROJECT_DIR`: the fixture pins or clears it.

   *Done when:* each of these tests fails at `d3e9c2544`:
   - from the main checkout, `git -C .plan/local/worktrees/{plan} commit -m x` is refused by the
     guard **and** the hook when that plan is in `6-finalize` with no sanction;
   - the same command for a runbook-lane worktree with no plan record passes;
   - the restored commit-count assertion holds.

3. **The R5 side doors are closed and the executor permit is exact.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-frontend:javascript, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Refused on both harnesses:
     - `python3 -<<<'…'`, `python3 - < x.py`, and `python3 -` reading stdin;
     - `exec python3 -c …`;
     - `stdbuf … python3 -c …`, `setsid python3 -c …`, `nice`, `timeout` and `env -i` prefixes;
     - `bash -c "python3 -c …"` / `sh -c` with an interpreter inside;
     - `uv run python -c …`, which the Claude hook's R4 must cover as the guard does.
   - The executor permit admits only `{repository root}/.plan/execute-script.py`, called by
     its relative or absolute form. `python3 /tmp/x/.plan/execute-script.py` is refused.
   - A wrapper is decided by an explicit list of known prefix programs, extended in one place
     and shared by both harnesses, never by guessing.

   *Done when:* a shared parametrised test table runs every form above through `guard.js` (node)
   and the hook, expecting a refusal; the documented executor form and the D1 admitted forms still
   pass. Every refusal row fails at `d3e9c2544` on at least one harness.

Split guard: three deliverables.

## Claim Labels

- OBSERVED: `guard.js:783-791` runs R5 with no gate.
- OBSERVED: `wizard-flow.md:20-32` runs `python3 "{GITIGNORE_SETUP}"` with a
  `bootstrap_plugin resolve` path.
- OBSERVED: `r5-allowlist.json` at `d3e9c2544` holds repository-relative entries only.
- OBSERVED: `isGitCommit` (`guard.js:580-597`) skips `-C` and its value.
- OBSERVED: `isExecutorPermit` (`guard.js:382-388`) accepts `endsWith("/.plan/execute-script.py")`.
- OBSERVED: OpenCode's shell tool passes an optional `workdir` as `cwd`, so it is empty unless the
  model sets it (delegated agent, installed binary schema).
- OBSERVED: commit `4a22f9db8` replaced the cache-path recovery command with a placeholder
  because the doc sweep skips comment lines.
- HYPOTHESIS: the hook's interpreter scan (`claude_pretooluse_hook.py:765-780`) and the guard's
  cluster scan (`guard.js:499-506`) share one decision table that can be extracted to the
  `r5-allowlist.json` sibling (verify-at-outline).

## Expected Surface

- OBSERVED: `.opencode/plugin/guard.js` and its shipped template source, wherever the bundle
  carries it (verify-at-outline) (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md`,
  `wizard-flow.md`, and `marshall-steward/SKILL.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md` (D1)
- OBSERVED: `doc/developer/opencode.adoc`, `platform-runtime/SKILL.md`,
  `platform-runtime/standards/pretooluse-enforcement.md` (D1, D2)
- OBSERVED: `test/plan-marshall/platform-runtime/` (the guard and hook tests),
  `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py`, and the
  doc-sweep test (D1, D2, D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-65 (shipped).
- PLAN-LB-43 D3 (executor recovery) uses D1's admission. Emit PLAN-LB-68 before PLAN-LB-43, or
  state at PLAN-LB-43's outline that its recovery admission is PLAN-LB-68 D1.
- Overlaps: PLAN-LB-43 D3 on `upgrade-flow.md` and `tools-script-executor/SKILL.md` (2 files);
  PLAN-LB-48 (OpenCode compat) on `guard.js`. The emit gate decides.
- Emitted after the drain, in the PLAN-LB-66 structure.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-68-lb-65-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
