---
name: tools-sync-agents-file
description: Create or update the project-specific AGENTS.md file following the OpenAI specification
tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch, AskUserQuestion, Task
---

# Create/Update AGENTS.md

Creates or updates the project-specific `AGENTS.md` following the OpenAI specification.

## Parameters

- `push` — Auto-commits and pushes changes after successful execution. Any other argument is rejected with an error.

## Preconditions

Fail fast (with a clear error and exit) if any of the following are not met:

- Project is a git repository (`git rev-parse --is-inside-work-tree`).
- No unrecognized arguments were passed.

## Workflow

### Step 1 — Research the OpenAI Format

Fetch the OpenAI specification from `https://github.com/openai/agents.md` via WebFetch and cache the required structure for validation. If WebFetch fails, fall back to the minimum baseline (title, description, instructions).

### Step 2 — Inspect Existing State

Use `Read` to check whether `./AGENTS.md` exists (creation vs update mode) and whether `./CLAUDE.md` exists.

### Step 3 — Choose Source of Truth

If `CLAUDE.md` exists, prompt the user via `AskUserQuestion` whether to use it as the primary source for `AGENTS.md` or to use other sources (project `doc/ai-rules.md` or global standards baseline).

### Step 4 — Gather Content Sources

1. If `./doc/ai-rules.md` exists, use it as the PRIMARY content source (it will be removed in Step 7).
2. Otherwise, if creating new and no `CLAUDE.md` (or the user chose "other sources"), read `~/git/plan-marshall/standards/ai-rules.md` as a BASELINE. Never modify this global file.
3. Run a `Task` with the Explore agent (thoroughness: "medium") to collect project architecture, build system, modules, testing frameworks, key technologies, and coding conventions.

### Step 5 — Synthesize and Write

Combine CLAUDE.md (if selected), `doc/ai-rules.md` or the baseline, and the project analysis into an `AGENTS.md` that follows the OpenAI structure. Remove duplication, keep language concise, and ensure every section is actionable. Use `Write` for creation or `Edit` for update. On failure, surface the error and abort.

### Step 6 — Validate

Re-read the generated `AGENTS.md` and verify:

- All OpenAI-required sections are present and the heading hierarchy is correct.
- Markdown, links, and references parse cleanly.
- Project-specific details match reality and contain no contradictions.

### Step 7 — Cleanup Legacy References

Use `Grep` for `doc/ai-rules\.md|ai-rules\.md` and update every match to point at `AGENTS.md` with `Edit`. If `doc/ai-rules.md` still exists, remove it with `Bash` and verify deletion. Log and continue on any per-file edit failure.

### Step 8 — Commit and Push (when requested)

If `push` was not provided, display the summary and exit successfully. If `push` was provided, commit all changes with a message describing the generated `AGENTS.md`, the sources used, removed `doc/ai-rules.md` (if applicable), and updated reference files; then push and display the final status.

### Step 9 — Post-Conditions

- `AGENTS.md` exists and is readable.
- `doc/ai-rules.md` is gone if it was present at start.
- Display a completion summary listing sources used, files modified, and the `doc/ai-rules.md` status.

## Critical Rules

- **The filename is `AGENTS.md`, uppercase, and the case is load-bearing.** The PR-Agent reviewer resolves its `repo_context_files` through GitHub's contents API, which is case-sensitive, so a repository carrying a lowercase `agents.md` hands the reviewer nothing — silently, with no error anywhere. This command emits the uppercase name ONLY: there is no lowercase fallback and no dual-name write. Do not "normalize" it back.
- **The two surviving lowercase tokens are the upstream spec's own address**, not this file's name: the WebFetch URL in Step 1 and the link under "Related" both point at `https://github.com/openai/agents.md`. Leave them verbatim — rewriting either breaks the fetch.
- **Allowed modifications**: `AGENTS.md`, `doc/ai-rules.md` (removal only), `CLAUDE.md` and other project docs (reference updates only).
- **Never modify** `~/git/plan-marshall/standards/ai-rules.md` — read-only baseline.
- **Never create** additional documentation files beyond `AGENTS.md`.
- **Quality**: concise, project-specific, no duplicate boilerplate, unambiguous language.
- **Structure**: always follow the OpenAI spec; never skip validation.
- **Source priority**: project `doc/ai-rules.md` > user-selected `CLAUDE.md` > global standards baseline — always combined with project analysis.
- **Preconditions and post-conditions are gates**: never proceed on a failed precondition or complete on a failed post-condition.

## Tool Usage Summary

- `WebFetch` — OpenAI specification
- `Read` — existing files
- `Write` / `Edit` — author or update `AGENTS.md` and reference files
- `Grep` — locate reference sites
- `Bash` — git repo check and legacy file removal
- `Task` — Explore agent for project analysis
- `AskUserQuestion` — CLAUDE.md source choice

## Continuous Improvement Rule

If you discover issues or improvements during execution, activate `Skill: plan-marshall:manage-lessons` and record a lesson for the `{type: "command", name: "tools-sync-agents-file", bundle: "plan-marshall"}` component with a category (bug | improvement | pattern | anti-pattern), summary, and detail.

## Related

- OpenAI specification: https://github.com/openai/agents.md
