envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:59:16Z

component=plan-marshall:execution-context
category=improvement
confidence=high
source_aspects=permission_prompt_analysis,chat_history_analysis

# Give leaves a sanctioned in-file search when Grep is not granted

## Context

At least five dispatched leaves in lb-33 reported that Grep/Glob were not granted. Three of them (TASK-9..16 executor, self-review rounds 2 and 3) fell back to one `git grep` to find a line number or a function body, which violates the no-shell-search hard rule; each disclosed it as a process slip. Others could not locate a function in a 2900-line file (`git-workflow.py` `_run_generate_executor`, `generate_executor.py` flat-root injection) and left the claim unverified. For `.claude/**` and `.github/**`, one leaf listed tracked files with `git ls-files` and read all 27.

## Root cause

The execution-context envelope declares Grep/Glob but the harness denies them to subagents. `architecture search --content` answers "which files", not "which line in this known file", and does not walk `.claude/**` / `.github/**`, so leaves reach for the forbidden fallback.

## Proposed action

Add a line-level mode to the sanctioned surface (for example `architecture search --content --pattern P --path F` returning line numbers, and coverage of the allowlisted dotfile trees). Name it in the execution-context runtime-tool-availability section as the replacement for in-file Grep, so a denied Grep has a compliant answer.

## Evidence

- aspect: permission_prompt_analysis — tool_availability_denials: Grep (3 git grep slips), Glob (.claude/.github coverage gap)
- aspect: chat_history_analysis — leaves: "I ran it once to find line numbers ... Grep and Glob were not granted in this envelope"; "I could not locate it without a search tool"
