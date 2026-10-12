envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:39Z

# Cross-repository verification commands must pass explicit absolute roots, not rely on cwd defaults

## Observation

Deliverable 11 verified with `python3 ../plan-marshall-documentation/.claude/skills/doc-review/scripts/trace.py` and no argument. trace.py defaults DOC_ROOT to `<git rev-parse --show-toplevel>/doc` of the current directory. Run from the pm-mcp-core plan worktree it would scan pm-mcp-core/doc (only doc/plans) and pass without checking the edited files. The relative script path also does not resolve from the worktree under `.plan/local/worktrees/{plan}`. Fixed by using `python3 /Users/oliver/git/plan-marshall-documentation/.claude/skills/doc-review/scripts/trace.py /Users/oliver/git/plan-marshall-documentation/doc` for baseline and after run.

## Rule

A verification command that targets another repository must name both the script and its target root with absolute paths. Relative `../sibling` paths break inside a plan worktree (different depth), and a tool that defaults its root from `git rev-parse` of the cwd silently checks the wrong tree and passes vacuously.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-004.md` from plan runtime-lifecycle (PLAN-08, #29)
