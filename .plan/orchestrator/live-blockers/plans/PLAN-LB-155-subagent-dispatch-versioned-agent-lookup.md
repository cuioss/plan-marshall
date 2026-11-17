# PLAN-LB-155: The subagent-dispatch seam resolves an installed `execution-context-level-N` agent

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

`platform_runtime subagent dispatch --agent execution-context-level-3` answers `prompt_not_found` while the agent is installed, because the agent lookup globs `*/agents/{name}.md` under the plugin cache root, whose deployed layout is `{bundle}/{version}/agents/{name}.md`, and the source-tree fallback holds only the bare `execution-context` agents. The orchestrator's per-harness dispatch branch then falls back to inlining each phase-5 envelope. Make the lookup resolve the deployed layout, and make the failure name what was searched.

## Deliverables

1. `_find_agent_file` resolves an agent from the versioned deployed layout: it picks the live version directory per bundle (reusing the marketplace's existing live-version selection rather than a second one) or also globs one level deeper, and a bare-name lookup still resolves from the source tree. The repro `--agent execution-context-level-3` returns `status: success` on a machine whose cache holds that file, and `--agent execution-context` is unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
2. A `prompt_not_found` answer for an agent-file miss names the roots it searched, and `platform-runtime/standards/contract.md` documents `prompt_not_found` for both the prompt-file miss and the agent-file miss and corrects its `subagent_type: execution-context-level-3` example to the behaviour that now holds.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: documenter
3. A test fixture for the versioned cache layout asserts the variant-suffixed name resolves, across the Claude, OpenCode and Antigravity runtime implementations that share `_find_agent_file`, and that a missing agent still returns the error.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- The cache-root lookup order (deployed layout before source tree) is unchanged.
- The seam is read-only: no write to the cache or the marketplace tree.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.

## Claim Labels

- OBSERVED: `_find_agent_file` builds its roots from the caller's extra roots plus a script-relative walk and globs `*/agents/{agent_name}.md` per root — read at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` lines 357-380 (re-read at HEAD).
- OBSERVED: `subagent dispatch --agent execution-context-level-3` returns `status: error`, `error: prompt_not_found` on this machine at executor 0.1.2139; the leaf confirmed the file exists at `~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.2139/agents/execution-context-level-3.md` — reproduced by the orchestrator.
- OBSERVED (leaf reading, not re-read): the claude wrapper passes the bundle cache root as the extra root (`claude_runtime.py` around line 2959); the only documentation caller is `plan-marshall/workflow/execution.md` line 181; no test fixture uses the versioned layout.
- HYPOTHESIS: the OpenCode and Antigravity implementations share the same glob and the same miss — confirm/refute at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` and the two runtime files (verify-at-outline).
- Verify-first clause: the outline settles which existing helper selects the live version directory, and that the claimed "no `[ERROR]` marker in the work log" from the consumer is not part of this plan's scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/platform-runtime/` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none staged.
- Adjacent to: `PLAN-LB-39`, `-48` and `-50` (shipped) touched the seam for other reasons; their behaviour stays untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-155-subagent-dispatch-versioned-agent-lookup.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
