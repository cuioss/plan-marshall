envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:16Z

# Candidate lesson: sweep criteria over resource trees cannot be executed by the agents that own them

Component: plan-marshall:manage-architecture / plan-marshall:phase-3-outline / plan-marshall:execute-task
Category (proposed): improvement
Source: plan spend-removal, outline and execute (four separate agent reports)

## Observation

- The outline, correctly, added execution-time success criteria "a word-boundary search of the resource trees finds nothing" because `src/{main,test}/resources/` (the `.pmwf` fixtures among them) is not in the architecture inventory and could not be searched at outline time.
- The dispatched agents of the outline, the plan phase, both execute envelopes and both review authors reported the same thing: `Grep` and `Glob` were refused to them, the `architecture search --content` inventory does not cover resource trees, and a shell `grep` is forbidden by the project rules. The execute envelope therefore could not perform the sweep its own task demanded, listed files with `git ls-files`, read three of them and handed the rest back as "run a Grep".
- The orchestrator context ran the sweep with a shell `grep` (no hits). So the criterion was met, but by a path the rules forbid and only because the main context was able to do it; two review rounds then had to describe the sweep as not recorded.

## Proposed correction

- Include declared resource trees (`src/*/resources`) in the architecture content-search inventory, or give `architecture search` an explicit `--path` mode for a tree outside it.
- Where a task's success criterion needs a search the agent cannot run, have the outline name the owner (orchestrator or a script) instead of the envelope, and record the sweep result as a typed fact the reviews can cite.
