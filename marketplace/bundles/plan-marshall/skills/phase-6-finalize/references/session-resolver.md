# Session ID and Transcript Resolver (phase-6-finalize)

## How to obtain session_id

Claude Code exposes `session_id` only in the JSON stdin payload delivered to hook invocations — it is **not** available via any environment variable or Bash command from a main-context skill run. The outer workflow obtains it by calling the resolver script, which reads a cache populated by the terminal-title hook on every `UserPromptSubmit`:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:manage_session current
```

Parse `session_id` from the TOON output. Resolution order: `~/.cache/plan-marshall/sessions/by-cwd/{sha256(cwd)}` → `~/.cache/plan-marshall/sessions/current` → `status: error\nerror: session_id_unavailable`. On error, the caller decides whether to abort finalize or degrade (skipping `enrich`); the contract here stays `Yes` / required and the caller is responsible for producing a valid value before dispatching this skill.

**Forbidden resolution patterns** (all trip the Bash sandbox or produce garbage):

- `echo "$CLAUDE_SESSION_ID"` — invented env-var name, not exposed by Claude Code; expansion triggers the `simple_expansion` sandbox heuristic and prompts the user
- `printenv`, `env | grep`, `$(...)` command substitution — forbidden by `workflows/planning.md` for the one env-var case it handles; same prohibition applies here
- Any other `$VAR` expansion — the **only** allow-listed env-var read pattern in plan-marshall is `echo "TERM_PROGRAM=$TERM_PROGRAM"` (installed by the marshall-steward wizard for IDE hand-off)

As a last resort (fresh checkout, stripped platform config, hook has not fired yet), use the user-question tool to ask the user for the id — but prefer the resolver in every other case, since users typically do not know where to find the id in the platform UI.

## How to obtain transcript_path

When a step needs the absolute path of the session transcript JSONL on disk (e.g., for `default:record-metrics` `manage-metrics enrich`, or for any aspect that reads the transcript directly), call the canonical resolver — the same script that exposes `current` also exposes `transcript-path`:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:manage_session \
  transcript-path --session-id {session_id}
```

Parse `transcript_path` from the TOON output. Resolution order: `~/.claude/projects/{cwd-slug}/{session_id}.jsonl` (where `{cwd-slug}` is the absolute project cwd with each `/` replaced by `-`) → in-process `pathlib.Path.glob` parent-directory scan for cross-cwd recovery → `status: error\nerror: transcript_not_found`. On error, the caller decides whether to abort finalize or degrade (e.g., skip `enrich`); the resolver does not shell out beyond the single `git rev-parse` already in `_resolve_cwd()`. Never substitute Bash file discovery (`ls`, `find`, Glob) for this resolver — the dev-general-practices ban on Bash file discovery already covers it, and the resolver is the only sanctioned alternative.
