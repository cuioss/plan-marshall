# Aspect: Chat History Analysis

**Conditional**: only dispatched when `--session-id` is present.

Complements log-analysis with conversational context — user pivots, mid-plan clarifications, permission prompts, and loop-backs. Purely LLM-driven; no script produces facts for this aspect.

## Input Resolution

The session transcript location is provider-specific. Claude Code session transcripts live under `~/.claude/projects/{slug}/sessions/{session_id}.jsonl`. The LLM reads the transcript directly via the Read tool. If the transcript is unavailable or excessively large (> 2MB), the aspect degrades gracefully: emit a fragment with `status: skipped` and `reason: transcript_unavailable`.

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
