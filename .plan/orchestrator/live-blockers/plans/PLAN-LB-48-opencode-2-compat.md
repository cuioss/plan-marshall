# PLAN-LB-48: OpenCode 2 applies this repository's permission rules and guard

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-48-opencode-2-compat.md` and is queued as one row file, `queue/PLAN-LB-48.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the Open Defect "The root `opencode.json` is in a shape nothing in this repository
> reads" and the OpenCode 1 → 2 switch on this machine (OpenCode 2.0.25 from 2026-10-08, 2.0.28
> from 2026-10-13). Every OBSERVED claim was read at `501aeb313`, in the installed `opencode`
> 2.0.28 binary, or read-only in `~/.local/share/opencode/opencode.db`. The orchestrator re-checked
> `guard.js:264`, the rule order of `opencode.json` and the completed `gh pr comment` calls.

## Objective

Under OpenCode 2 none of this repository's shell deny rules apply, and the guard plugin blocks
nothing.

- The root `opencode.json` has the shape OpenCode 2 expects, but its rules are in the wrong order
  for how OpenCode 2 evaluates them: the last matching rule wins, and each list ends with its
  catch-all, which overrides every deny before it.
- The guard plugin checks for a tool named `bash`; OpenCode 2 names its shell tool `shell`.

The effect is on record: since 2026-10-13 plan sessions ran 120 `gh` calls (one posted a PR
comment from a dispatched sub-agent), `rm` from a sub-agent and `rm -rf` from the main session —
all configured `deny`.

This plan restores the deny/ask/allow rules the repository had under OpenCode 1, makes the guard
see the shell tool, makes the permission tooling read and write the shape the file actually has,
and makes the sub-agent dispatch seam and the skill-load directive use OpenCode 2's tool names.

## Deliverables

1. **The root `opencode.json` rules take effect under OpenCode 2's last-match-wins evaluation.**
   - The catch-all rule goes first and every specific rule after it, in the top-level
     `permissions` list and in each `agents.*.permissions` list.
   - The rule set and effects stay those of the OpenCode 1 file at `35b5589b5^`.
   - A test evaluates the file the way OpenCode 2 does — project rules, then the agent's rules,
     last match wins, no match means `ask` — over fixed probes for `build` and every
     `execution-context*` agent: `gh pr view 1`, `rm x`, `git stash`, `git restore x` and
     `mvn verify` resolve to `deny`; `python3 .plan/execute-script.py a:b:c` resolves to `allow`;
     each probe's effect equals its effect under the `35b5589b5^` file.

   *Done when:* the test exists and passes. At `501aeb313` it fails: `gh pr view 1` resolves to
   `ask` for `build` and for `execution-context-level-5`.

2. **The guard plugin guards OpenCode 2's shell tool.**
   - `.opencode/plugin/guard.js` applies R1/R2/R4 to tool `shell` as well as `bash`; its header
     comment about the plugin load path is corrected.
   - `test_opencode_enforcement.py`, which mirrors the decision table, asserts that the guarded
     shell-tool set contains `shell`.

   *Done when:* the mirror test fails at `501aeb313` and passes after; the PR records one live
   OpenCode call `rm .plan/temp/guard-probe` refused with an R2 message.

3. **OpenCode permission tooling reads and writes the shape the file has.**
   - Every `opencode_runtime.py` operation that reads or writes the `permission` map (configure,
     analyze, fix, protect-path, the web ops, ensure-defaults, the settings skeleton, the health
     `_has_exec` check) and the OpenCode branches of `permission_fix.py`: when the target file has
     a `permissions` list they read it and write into it, specific rules after the catch-all, and
     never add a `permission` map beside it. A file in the OpenCode 1 shape keeps today's
     behaviour.

   *Done when:* a fixture in the OpenCode 2 shape run through ensure-defaults gains the executor
   `allow` inside `permissions`, after the catch-all, and no `permission` key; analyze over a copy
   of the root file reports its deny rules. At `501aeb313` ensure-defaults writes
   `permission.bash` and analyze reads `{}`.

4. **The sub-agent dispatch seam and the emitted skill-load directive use OpenCode 2's tool names.**
   - `OpenCodeRuntime.subagent_dispatch` returns `tool: subagent` with `agent: {agent}`,
     `description` and `prompt`.
   - In `marketplace/targets/opencode/mapping.json` the `skill_directive` template becomes
     `{ id: "{bundle}-{skill}" }`, and `Task` maps to `subagent` if the outline confirms the
     normalizer accepts it as a permission action.

   *Done when:* a test reads `tool: subagent` and `agent: execution-context-level-5` from
   `subagent dispatch`; the emitted body for a `Skill: a:b` line reads `{ id: "a-b" }`. At
   `501aeb313` the output is `task`, `subagent_type` and `{ name: … }`.

Split guard: four deliverables, all on what OpenCode 2 lets a session do. The measurement half is
PLAN-LB-49.

## Claim Labels

- OBSERVED: installed OpenCode is `v2.0.28` (`opencode --version`, binary `~/.opencode/bin/opencode`); `opencode.db` `session_v2.version` is `2.0.25` for 5 sessions on 2026-10-08 and `2.0.28` for 202 sessions from 2026-10-13 17:57Z.
- OBSERVED: the 2.0.28 config schema `Config.Info` declares `permissions` ("Ordered tool permission rules applied to agent tool use"), `agents`, `skills` (string list), `commands`, `instructions`, `plugins`; `Config.Agent` declares `model, request, system, description, mode, hidden, color, steps, disabled, permissions` — read in the binary's schema strings.
- OBSERVED: 2.0.28 evaluates permission rules last-match-wins (`rules.flat().findLast(…) ?? {effect: "ask"}`), read in the binary's Permission service.
- OBSERVED: 2.0.28 still accepts the OpenCode 1 keys through a normalizer that concatenates `[...tools, ...permission, ...permissions]`; `permission.bash` becomes action `shell`; `skills.paths` becomes a plain list.
- OBSERVED: the root `opencode.json` at `501aeb313`: top-level `permissions` has 35 rules, first `{shell, "gh *", deny}`, last `{shell, "*", allow}`; each `agents.*.permissions` list ends `{shell, "*", ask}`. At `35b5589b5^` the OpenCode 1 map put `"*"` first. The 35b5589b5 commit body calls the change "operator-authored … transported from `main`" (orchestrator re-checked the order).
- OBSERVED: `opencode debug agents` for this repository merges rules defaults → project → agent; the last shell rule is `{shell,*,ask}` for `build` (index 70 of 72) and `execution-context-level-5` (73 of 75), so `gh`, `rm` and `git stash` resolve to `ask`, not `deny`.
- OBSERVED: completed calls in `opencode.db`, all configured `deny`: 120 `gh` calls from 2026-10-13, among them `gh pr comment 1065 --repo cuioss/plan-marshall --body /review` from an `execution-context-level-5` sub-agent (`ses_ec94bfe08ffetY3k2BZkwSs6Nq`, PLAN-LB-31); `rm test/plan-marshall/manage-metrics/test_probe_inline_debug.py` from a sub-agent (`ses_ec836f0e9ffet1EYb40mNtxnw7`, PLAN-LB-39); `rm -rf …/antigravity-execution-fidelity/.plan/local/worktrees` from the build agent (`ses_ec9968164ffeRdYIgaux9dNEOC`).
- OBSERVED: the root file is hand-maintained; `emitter.py` `_generate_opencode_json` (`:520-527`) writes only `target/opencode/opencode.json` in the OpenCode 1 shape, which `sync.py` (`:288-296`, `:618-631`) copies to `~/.config/opencode/`. `opencode debug config` lists the root file as a config source.
- OBSERVED: `.opencode/plugin/guard.js:264` reads `if (tool !== "bash") return` (orchestrator re-checked); OpenCode 2's shell tool id is `shell` (binary; 9,149 completed `shell` calls and 0 `bash` calls in the DB); `opencode plugin list` loads `plan-marshall-guard`, so the plugin is discovered but never matches.
- HYPOTHESIS: the `execute.before` event carries `tool: "shell"` — confirm with the live refused `rm` of deliverable 2 (verify-at-outline).
- OBSERVED: `opencode_runtime.py` reads and writes `permission` at `:507, :586, :646, :766, :878, :913, :1034-1050, :1317` and the skeletons at `:956-961, :983-988`; `permission_fix.py` writes `permission.bash` at `:393-413, :750-769, :1332-1355`. Because the normalizer orders `permission` before `permissions`, a rule these tools add beside an OpenCode 2 list is overridden by its trailing catch-alls.
- OBSERVED: `opencode_runtime.py:1252` returns `'tool': 'task'`, `:1255` `'subagent_type'`; OpenCode 2's sub-agent tool is `subagent` with input `{agent, description, prompt}` (198 calls in the DB); the skill tool input is `{id}` (881 calls); `mapping.json:12` maps `Task` → `task`, `:22` uses `{ name: "{bundle}-{skill}" }`.
- HYPOTHESIS: no emitted agent declares a `Task` tool, so the `mapping.json` `Task` entry changes no emitted file — confirm with `test/marketplace/targets/opencode/test_frontmatter.py` (verify-at-outline).
- OBSERVED (operator action, not code): `opencode.db` `permission` holds persisted "always allow" approvals for this project (`python3 *`, `grep *`, `head *`, `ls *`, `git -C *`, `node *`, `opencode *`, `ps *`). Where they sit in evaluation order is not verified; if after config, `python3 *` overrides the `python3 -m pytest *` deny. Report in the PR; the operator clears them.
- Verify-first clause (deliverable 1): keep the OpenCode 2 shape with corrected order (recommended: native schema) or revert to the OpenCode 1 shape (accepted by the normalizer). Record the choice; the evaluation test must pass either way.
- Verify-first clause (deliverable 4): PLAN-LB-39 (running) D1 wires phase 5 through this seam. If LB-39 has already changed `subagent_dispatch`, drop that half and keep only the `mapping.json` template.

## Expected Surface

- OBSERVED: `opencode.json` — rule order (D1)
- HYPOTHESIS: `test/plan-marshall/platform-runtime/test_opencode_root_config.py` — new evaluation test (verify-at-outline) (D1)
- OBSERVED: `.opencode/plugin/guard.js` — guarded tool set, header (D2)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_enforcement.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — permission ops, `subagent_dispatch` (D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D3, D4)
- OBSERVED: `test/plan-marshall/platform-runtime/test_permission_ops.py` (D3)
- HYPOTHESIS: `test/plan-marshall/tools-permission-fix/test_runtime_dsl.py` — only if it pins the OpenCode write shape (verify-at-outline) (D3)
- OBSERVED: `marketplace/targets/opencode/mapping.json` (D4)
- HYPOTHESIS: `test/marketplace/targets/opencode/test_body_transforms.py` — only if it pins the skill directive template (verify-at-outline) (D4)
- HYPOTHESIS: `doc/developer/opencode.adoc` — only where it states the OpenCode 1 permission shape or `bash` tool name (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md` — only if it names `task` / `bash` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. **Highest priority in WS-04**: deny rules are not applied in any OpenCode
  session of this repository today.
- Overlaps with: PLAN-LB-39 (running) on the `test/plan-marshall/platform-runtime/` and
  `test/marketplace/targets/` directories and its HYPOTHESIS `marketplace/targets/opencode/`; its
  D1 consumes the `subagent dispatch` seam deliverable 4 reshapes (`opencode_runtime.py` is not in
  its surface). PLAN-LB-45 (staged) on its HYPOTHESIS `opencode_runtime.py` (runtime_info only).
  PLAN-LB-49 on `opencode_runtime.py` and `test_opencode_runtime.py` — this plan goes first.
  PLAN-LB-43 / PLAN-LB-47: no declared file shared.
- Adjacent to: the emitted global `target/opencode/opencode.json` (OpenCode 1 shape, accepted by
  the normalizer, no harm observed) and `script-shared/scripts/target_context.py` (OpenCode 2
  still sets `OPENCODE=1`) — untouched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-48-opencode-2-compat.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
