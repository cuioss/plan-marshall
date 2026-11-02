envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-25T22:12:14Z

# Candidate lesson: a dispatched subagent edited a persisted tool-result copy instead of the plan artifact (plan-marshall:persona-plan-marshall-agent tool usage)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-27-test-simplification (PR cuioss/API-Sheriff#520), inbox message plan-v02-27-test-simplification-005. Observed by the orchestrator; the plan logs hold no entry for it.

What happened: twice, a subagent rebuilding the git-ignored `work/test-inventory.md` edited a session tool-result copy under `~/.claude/projects/.../tool-results/` instead of the plan artifact. Those files are read-only snapshots of earlier tool output. The host refused some edits only after others had landed, which left a partial rebuild against the wrong file. The orchestrator had to notice and redo it.

Suggested direction:
- A leaf treats persisted tool-output files (`tool-results/*.txt`) as read-only evidence. Write targets live only under WORKTREE or the plan directory.
- To regenerate a git-ignored artifact, re-read its source with Read and write it to the plan path with Write.
- State this in the persona-plan-marshall-agent tool-usage rules next to "Bash: No file operations".
