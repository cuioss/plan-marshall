envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:52Z

# Candidate lesson: architecture search called with flags it does not declare

- Component: plan-marshall:manage-architecture
- Suggested category: anti-pattern
- Signal: script failure cluster (argparse rejections, 5 occurrences, phases 5 and 6)

## Evidence (script-execution-2026-10-12.log)

- 17:14:11Z and 20:10:19Z: `search --content ... --module pm-core|pm-workflow`, unknown_flag `--module`
  (declared only on sibling verbs).
- 17:37:22Z and 21:29:59Z: `search ... --project-dir <path>` placed after the verb,
  misplaced_router_flag. In the first call the path also pointed at a surefire-reports directory,
  which is outside the inventory.
- 21:30:02Z: `search ... --literal false`, "unrecognized arguments: false" (`--literal` is a switch).

## Suggested correction

The persona's "structured queries first" rule sends agents to `architecture search --content`. Agents
then assume `--module` scoping and value-taking switches. Add worked examples to the search
documentation: no `--module` (filter by path pattern instead), `--project-dir` before the verb, and
`--literal` without a value. Alternatively, add a `--module` filter to search.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-010.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
