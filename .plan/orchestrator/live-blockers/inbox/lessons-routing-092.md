envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-16T07:45:18Z

# The subagent-dispatch seam cannot resolve any installed `execution-context-level-N` agent and answers `prompt_not_found`

**Severity:** high (operator grade, 2026-11-16 `gather` run; the grading leaf had it BORDERLINE high/medium)
**Bundle:** plan-marshall (`platform-runtime`)
**Checked at:** `ee019bf1d` (origin/main), re-read and reproduced by the orchestrator

## What was reported

TokenSheriff lesson `2026-11-15-18-005` (relayed from the API-Sheriff epic `api-sheriff-seams`, message `client-refresh-verification-discovery-cache-008`): the orchestrator asked the platform-runtime subagent dispatch seam to dispatch the `execution-context` agent and got `prompt_not_found`. It bypassed the seam with the host Agent tool, and dispatch then worked, so the agent definition was installed. The sender says the work log carries no `[ERROR]` marker for the event, and it did not reproduce the failure. It names two hypotheses, a variant-suffixed agent name against a bare-name lookup, and the bundle cache path against the worktree path. Its asks are to log a `script_failure`-class record whenever the seam answers `prompt_not_found`, and to fix the lookup.

## Ground truth at the checked commit

`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/`:

- `_claude_runtime_impl.py:1861-1867`: `subagent_dispatch` returns `error: prompt_not_found`, message "Agent {agent!r} not found in marketplace tree", whenever `claude_runtime._find_agent_file(agent)` returns None.
- `claude_runtime.py:2959-2961`: `_find_agent_file` searches only `(_claude_bundle_cache_root(),)` before the source walk. `:2604-2612`: that root is `~/.claude/plugins/cache/plan-marshall`.
- `runtime_base.py:376-379`: for each root it does `root.glob(f'*/agents/{agent_name}.md')`. The deployed layout is `cache/plan-marshall/{bundle}/{version}/agents/{name}.md` (for example `.../plan-marshall/0.1.2134/agents/execution-context-level-3.md`), so `*/agents/` matches nothing under the cache root: the version directory is missing from the glob.
- `runtime_base.py:366-374`: the only other search is a script-relative walk to a `marketplace/bundles` or `bundles` directory. In the source tree only the bare `execution-context.md` and `execution-context-reader.md` exist; the `-level-N` variants are generated per target and are not there.

**Reproduction (orchestrator, this machine, primary checkout, executor 0.1.2134):**

- `platform_runtime subagent dispatch --agent execution-context-level-3` returns `status: error`, `error: prompt_not_found`, `message: Agent 'execution-context-level-3' not found in marketplace tree`.
- `platform_runtime subagent dispatch --agent execution-context` returns `status: success`, resolved from the source tree.
- The `-level-3` file exists in the cache for sixteen installed versions, so the miss is the lookup, not a missing install.

`platform-runtime/standards/contract.md:1401` documents `subagent_type: execution-context-level-3` in a success example, so the documented example is the name that fails. `contract.md:1429-1435` documents `prompt_not_found` only as the "prompt file not found" case, while the code also returns it for an agent-file miss.

## Not verified

- That the consumer's run used this exact seam and a version with this lookup. The consumer's installed version is unknown.
- The sender's claim that the work log has no `[ERROR]` marker for the event. The `script_failure` ask rests on that claim.
- Callers: a search of the bundles' markdown for `subagent-dispatch` / `subagent_dispatch` finds only `manage-metrics/standards/data-format.md`, so no workflow doc routes through the seam by name. Who calls it in a consumer run was not established.

## Relation to filed and shipped work

The leaf reports PLAN-LB-39, -48 and -50 touching the seam for other reasons (not re-read). No filing or plan was found that owns the lookup.

## Source

- TokenSheriff lesson `2026-11-15-18-005`, archived verbatim at `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-16/TokenSheriff/2026-11-15-18-005.md`.
