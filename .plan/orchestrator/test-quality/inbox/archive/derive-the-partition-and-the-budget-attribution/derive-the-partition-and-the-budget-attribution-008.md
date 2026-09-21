envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T08:57:58Z

component=project:finalize-step-deploy-target
category=bug
confidence=medium
source_plan=derive-the-partition-and-the-budget-attribution

# Resolve the generator interpreter instead of hard-coding uv run python

## Context

`project:finalize-step-deploy-target` documents its invocation as `uv run python marketplace/targets/generate.py`. On this machine `uv` is not on `PATH` and is not present under `/home/oliver` at all, so the documented invocation failed.

The step completed only because the executing agent substituted an interpreter by hand and recorded the substitution (decision `f79302`):

> Documented invocation 'uv run python marketplace/targets/generate.py' failed — uv is not on PATH in this environment (not found under /home/oliver either). Ran the generator with the project's own venv interpreter (.venv/bin/python), the same runtime ./pw provisions, rather than skipping the step. Output: 1174 entries, v0.1.1545 stamped into 11 bundle plugin.json, dist-manifest.json emitted. The skill doc's hard-coded 'uv run' prefix is an environment assumption worth revisiting.

The recovery was correct and the outcome was right. What is fragile is that the step's success depended on an agent choosing to reason about the failure rather than reporting the step blocked — and the two available wrong answers (skip the step; report it failed) would both have left the marketplace target un-regenerated after a bundle-editing plan.

## Root cause

The step hard-codes a launcher (`uv`) that the project does not require and this machine does not have, rather than resolving the interpreter the project actually provisions. `./pw` provisions `.venv`, which is the runtime the generator ran under successfully.

This is the same class as the repository's own "Build commands: resolve via architecture" hard rule, applied to a project-local finalize step: a hard-coded tool prefix is an environment assumption.

## Proposed action

Resolve the interpreter rather than naming a launcher — prefer the project venv interpreter that `./pw` provisions, falling back to `uv run python` where `uv` is present. Update the skill body so the documented invocation is the one that works on a machine with no `uv`.

## Evidence

- decision `f79302` — the failure, the substitution, the successful output, and the recommendation, all recorded at the moment it happened
- aspect: script_failure_analysis — the step's own record-step row shows `outcome=executed`, so the failure is invisible to the script-failure sweep; only the decision log carries it
- `project:finalize-step-deploy-target` completed `1174 entries emitted to target/claude/, v0.1.1545 stamped into 11 plugin.json`
