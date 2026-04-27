# Aspect: Chat History Analysis

**Conditional**: only dispatched when `--session-id` is present.

Complements log-analysis with conversational context — user pivots, mid-plan clarifications, permission prompts, and loop-backs. Purely LLM-driven; no script produces facts for this aspect.

## Input Resolution

Claude Code session transcripts live under `~/.claude/projects/{slug}/{session_id}.jsonl`, where `{slug}` is the absolute project cwd with each `/` replaced by `-` (path-slug). The orchestrator resolves the absolute path by calling `plan-marshall:plan-marshall:manage_session transcript-path --session-id {session_id}` (see `SKILL.md` Step 3, Aspect 12 dispatch instructions); the resolver returns `transcript_path` in TOON output and falls back to a parent-directory glob when the slug-derived path misses (cross-cwd recovery). The LLM does **not** manually construct the path or perform any file discovery — it receives `transcript_path` as a concrete absolute path from the orchestrator and reads it directly via the Read tool. If the transcript is unavailable (resolver returned `status: error\nerror: transcript_not_found`) or excessively large (> 2MB), the aspect degrades gracefully: emit a fragment with `status: skipped` and `reason: transcript_unavailable`.

## TOON Fragment Shape

```toon
aspect: chat_history_analysis
status: success|skipped
session_id: {session_id}
summary: |
  {3-5 sentence narrative of the session arc}
pivots[*]{turn_index,reason}:
  42,"user clarified compatibility strategy"
permission_prompts[*]{tool,resource,cause}:
  ...
loop_backs[*]{from_phase,reason}:
  ...
findings[*]{severity,message}:
  info,"User clarified requirement mid-refine — consider refine-phase prompt tuning"
```

## LLM Interpretation Rules

- Pivots AFTER `3-outline` completion indicate a missed clarification in refine — surface as `warning`.
- Any permission prompt within the plan SHOULD have a corresponding entry in the permission-prompt-analysis aspect.
- Loop-backs from `6-finalize` to `5-execute` are normal; loop-backs from later phases to `2-refine` are strong signals of an under-refined request.

## Finding Shape

```toon
aspect: chat_history_analysis
severity: info|warning|error
message: "{one-line}"
evidence: "turn_index={n}"
```

## Out of Scope

- Log-level quantitative counts — those belong to log-analysis.
- Root-cause of specific script failures surfaced in chat — those belong to script-failure-analysis.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-chat-history-analysis.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect chat-history-analysis --fragment-file work/fragment-chat-history-analysis.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
