envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-27T14:23:49Z

# Rules mandate Grep/Glob as the fallback, but the session does not expose them

## Observed

The hard rules (CLAUDE.md "No shell file operations", persona `agent-behavior-rules.md` Principle 4 and
"Structured queries first") prescribe `architecture search --content` first and `Grep`/`Glob` as the
qualified fallback — never `grep`/`find` via Bash.

In this session the `Grep` tool call failed with: "No such tool available: Grep ... search file contents
with `grep` via the Bash tool instead." `Glob` is likewise absent from the tool list. The harness itself
therefore steers to the exact form the rules forbid.

To locate a function body inside an already-known file (`file_ops.py`, `_orchestrator_inbox.py`,
`_cmd_lifecycle.py`) after `architecture search --content` had identified the files, the orchestrator
used `grep -n` via Bash on those single known files — a rule deviation forced by tool availability.

## Suggested fix

Either document the sanctioned substitute when `Grep`/`Glob` are not exposed (e.g. `Read` with
offset, or an `architecture search` line-level mode), or add a line-level content verb so the fallback
never needs Bash. The rules should name what to do when the named fallback tool does not exist.
