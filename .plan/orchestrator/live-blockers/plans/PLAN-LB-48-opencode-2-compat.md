# PLAN-LB-48: plan-marshall emits and edits OpenCode 2 configuration

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-48-opencode-2-compat.md` and is queued as one row file, `queue/PLAN-LB-48.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the OpenCode 1 → 2 switch on this machine (OpenCode 2.0.25 from 2026-10-08, 2.0.28
> from 2026-10-13) and the Non-Claude-Code Failure "OpenCode 2: no deny rule applies". **Re-scoped
> 2026-10-14 by operator decision**: the live harm in this repository — the root `opencode.json`
> rule order and the guard plugin's tool name — was hot-fixed outside the plan lifecycle in PR
> #1772 (`fix/opencode-2-permission-order`), with `test/plan-marshall/platform-runtime/test_opencode_root_config.py`
> pinning it. This plan makes plan-marshall itself **emit and edit OpenCode 2 configuration**, so
> no producer re-introduces the OpenCode 1 shape and consumer projects get correct files.

## Objective

Everything plan-marshall generates or edits for OpenCode is written for OpenCode 1. OpenCode 2
still accepts most of it through a normalizer, which is why nothing failed loudly — but the
normalizer's ordering is what turned this repository's deny rules into dead letters, and the
same trap waits in every file plan-marshall emits or edits:

- the target emitter writes the global `opencode.json` with OpenCode 1 keys (`skills.paths`,
  `agent`) and a skills path (`./skill`) the sync never creates;
- emitted agents carry an OpenCode 1 `permission:` map with `bash:` keys;
- the tool mapping names OpenCode 1 tools (`bash`, `task`) and the skill directive passes
  `{ name }` where OpenCode 2's `skill` tool takes `{ id }`;
- the permission tooling (`opencode_runtime.py`, `permission_fix.py`) reads and writes the
  OpenCode 1 `permission` map, so a rule it adds beside an OpenCode 2 list lands before the list
  and is overridden by its catch-all;
- the sub-agent dispatch seam returns OpenCode 1's `task` / `subagent_type`.

This plan moves every one of those to OpenCode 2's native schema and tool names, with
catch-all-first ordering wherever a rule list is written, and adds a version check so a future
OpenCode major cannot drift silently again.

## Deliverables

1. **The OpenCode target emits OpenCode 2 configuration.**
   - `target/opencode/opencode.json` uses `skills` as a list naming the directory the sync really
     installs, and `agents` instead of `agent`.
   - Emitted agent frontmatter carries an OpenCode 2 `permissions` list of
     `{action, resource, effect}` rules (shell action `shell`), with any catch-all first.
   - Emitted command frontmatter uses OpenCode 2 fields (`subagent`, not the deprecated
     `subtask`, if the emitter sets it).
   - The emitter's docstrings and `doc/developer/opencode.adoc` describe the OpenCode 2 shape.

   *Done when:* an emitter test asserts the global config's top-level keys are a subset of the
   OpenCode 2 `Config.Info` keys and its `skills` entry names an installed directory; an
   emitted-agent test evaluates the `permissions` list last-match-wins and gets the same effect
   per tool as the source agent's tool grants; no emitted file contains a top-level `permission:`
   map or a `bash:` permission key. At `501aeb313` all three fail.

2. **Tool names and directives match OpenCode 2.**
   - `marketplace/targets/opencode/mapping.json`: `Bash` → `shell`, `Task` → `subagent`, and the
     `skill_directive` template becomes `{ id: "{bundle}-{skill}" }`.
   - `OpenCodeRuntime.subagent_dispatch` returns `tool: subagent` with `agent`, `description` and
     `prompt`.

   *Done when:* the emitted body for a `Skill: a:b` line reads `{ id: "a-b" }`; a test reads
   `tool: subagent` and `agent: execution-context-level-5` from `subagent dispatch`. At
   `501aeb313` the output is `{ name: … }`, `task` and `subagent_type`.

3. **The permission tooling reads and writes the shape the file has.**
   - Every `opencode_runtime.py` operation that reads or writes permissions (configure, analyze,
     fix, protect-path, the web ops, ensure-defaults, the settings skeleton, the health
     `_has_exec` check) and the OpenCode branches of `permission_fix.py` read the `permissions`
     list when present and write into it — specific rules after the catch-all — never adding a
     `permission` map beside it. New files are created in the OpenCode 2 shape.

   *Done when:* a fixture in the OpenCode 2 shape run through ensure-defaults gains the executor
   `allow` inside `permissions`, after the catch-all, and no `permission` key; analyze over a copy
   of the root `opencode.json` reports its deny rules; a fresh skeleton is OpenCode 2-shaped. At
   `501aeb313` ensure-defaults writes `permission.bash` and analyze reads `{}`.

4. **The installed OpenCode version is checked against the emitted schema.**
   - The OpenCode runtime's health/doctor path reads the installed major version
     (`opencode --version`) and reports a mismatch with the schema major the emitter targets,
     instead of emitting silently for the wrong major.
   - `script-shared/scripts/target_context.py` drops the `OPENCODE_PID` probe OpenCode 2 never
     sets (detection stays on `OPENCODE`).

   *Done when:* a test with a stubbed `opencode --version` of `1.x` reports the mismatch and `2.x`
   reports none; an absent binary reports "not checkable", never "ok".

Split guard: four deliverables, all on what plan-marshall writes for OpenCode. The measurement
half is PLAN-LB-49.

## Claim Labels

- OBSERVED: installed OpenCode is `v2.0.28` (`opencode --version`); `opencode.db` `session_v2.version` shows 2.0.25 from 2026-10-08 and 2.0.28 from 2026-10-13.
- OBSERVED: the 2.0.28 config schema `Config.Info` declares `permissions` (ordered `{action, resource, effect}` rules), `agents`, `skills` (string list), `commands`, `instructions`, `plugins`; `Config.Agent` declares `model, request, system, description, mode, hidden, color, steps, disabled, permissions`; commands take `template, description, agent, model, subagent` (`subtask` deprecated) — read in the binary.
- OBSERVED: 2.0.28 evaluates rules last-match-wins (`findLast`, default `ask`); its normalizer concatenates `[...tools, ...permission, ...permissions]`, maps `permission.bash` to action `shell` and `skills.paths` to a list.
- OBSERVED (hotfix, PR #1772): reordering the root `opencode.json` catch-alls to the front gives 0 effect differences against the OpenCode 1 file at `35b5589b5^` over 17 agents × 47 commands (518 before); `guard.js` now guards `shell` and `bash`.
- OBSERVED: `marketplace/targets/opencode/emitter.py` `_generate_opencode_json` (`:505-530`) writes `{'$schema', 'skills': {'paths': ['./skill']}, 'agent': {…}}`; the sync installs skills under `skills/` (`sync.py` `_deploy_skill`, ~`:589`), so `./skill` names a directory that does not exist.
- OBSERVED: emitted agents (`target/opencode/agent/execution-context-level-5.md`) carry `mode: subagent` and an OpenCode 1 `permission:` map (`bash: allow`, `edit`, `glob`, `grep`, `read`, `skill`).
- OBSERVED: `mapping.json` `tool_permissions` maps `Bash` → `bash`, `Task` → `task`; `skill_directive.template` is ``Call the `skill` tool with `{ name: "{bundle}-{skill}" }` before continuing.``; OpenCode 2's skill tool input is `{id}` (881 calls in `opencode.db`), its sub-agent tool is `subagent` with `{agent, description, prompt}` (198 calls).
- OBSERVED: `opencode_runtime.py` reads and writes `permission` at `:507, :586, :646, :766, :878, :913, :1034-1050, :1317`, skeletons at `:956-961, :983-988`; `permission_fix.py` writes `permission.bash` at `:393-413, :750-769, :1332-1355`; `subagent_dispatch` returns `'tool': 'task'` (`:1252`) and `'subagent_type'` (`:1255`).
- OBSERVED: OpenCode 2.0.28 sets `OPENCODE=1` and `OPENCODE_SESSION_ID` in the shell environment and no `OPENCODE_PID`; `target_context.py:167` still checks `OPENCODE_PID`.
- HYPOTHESIS: emitted variant agents carry no `model:` line although the variants pin a model/effort level — confirm at `marketplace/targets/opencode/variant_emitter.py` and `mapping.json` `model_map`; if a model pin is intended and missing, record it in the PR, do not widen this plan (verify-at-outline).
- HYPOTHESIS: on OpenCode the hand-off `/plan-marshall …` is not a registered command (the emitted one is `plan-marshall-plan-marshall`, `target/opencode/bundle-components.json`), so it reaches the model as prose — confirm with `opencode debug` command listing; report in the PR whether an alias command is cheap (verify-at-outline).
- Verify-first clause: decide whether the emitter supports OpenCode 1 at all after this change. Recommended: OpenCode 2 only, with deliverable 4's check reporting a 1.x install; keep a dual shape only if a machine still runs 1.x.
- Verify-first clause (deliverable 2): PLAN-LB-39 (running) D1 wires phase 5 through `subagent dispatch`. If LB-39 has already changed it, keep LB-39's shape and drop that half.

## Expected Surface

- OBSERVED: `marketplace/targets/opencode/emitter.py` — global config, agent frontmatter (D1)
- OBSERVED: `marketplace/targets/opencode/variant_emitter.py` — variant agent frontmatter (D1)
- OBSERVED: `marketplace/targets/opencode/mapping.json` (D1, D2)
- OBSERVED: `test/marketplace/targets/opencode/test_emitter.py` (D1)
- OBSERVED: `test/marketplace/targets/opencode/test_variant_emitter.py` (D1)
- HYPOTHESIS: `test/marketplace/targets/opencode/test_frontmatter.py` (verify-at-outline) (D1)
- HYPOTHESIS: `test/marketplace/targets/opencode/test_body_transforms.py` — skill directive template (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — `subagent_dispatch`, permission ops, health (D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D2, D3, D4)
- OBSERVED: `test/plan-marshall/platform-runtime/test_permission_ops.py` (D3)
- HYPOTHESIS: `test/plan-marshall/tools-permission-fix/test_runtime_dsl.py` — only if it pins the OpenCode write shape (verify-at-outline) (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py` (D4)
- OBSERVED: `test/plan-marshall/script-shared/test_target_context.py` (D4)
- HYPOTHESIS: `doc/developer/opencode.adoc` — OpenCode 2 shape (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md` — only if it names `task` / `bash` (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: PR #1772 (the hotfix) merged — this plan starts from its root `opencode.json` and
  regression test, and does not edit either.
- Overlaps with: PLAN-LB-39 (running) on the `test/marketplace/targets/` and
  `test/plan-marshall/platform-runtime/` directories and its `marketplace/targets/opencode/`
  entry; its D1 consumes the `subagent dispatch` seam deliverable 2 reshapes. PLAN-LB-43 (staged)
  on `test/marketplace/targets/opencode/test_variant_emitter.py`. PLAN-LB-45 (staged) on its
  HYPOTHESIS `opencode_runtime.py` (runtime_info only). PLAN-LB-49 on `opencode_runtime.py` and
  `test_opencode_runtime.py` — this plan goes first. PLAN-LB-47: none.
- Adjacent to: the root `opencode.json` and `.opencode/plugin/guard.js` (hot-fixed in #1772, not
  edited here); OpenCode token measurement (PLAN-LB-49).

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
