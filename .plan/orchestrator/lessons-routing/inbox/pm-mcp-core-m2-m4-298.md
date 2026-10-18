envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:08Z

# Candidate lesson: script failures seen in this run (plan-marshall tooling, version 0.1.1947)

Source: failure lines in this plan's work log, as forwarded by the finalize dispatcher. The failure clusters were
not counted; the items below are the known sources. All concern plan-marshall components, not this repository's
code, so they may belong in plan-marshall's lessons-routing inbox.

## Items

1. **`git-workflow commit` verb does not exist** in this plan-marshall version. A workflow step or the agent
   called a commit verb that the `workflow-integration-git` script does not declare (argparse rejection).
2. **`manage-solution-outline deliverable-hashes` is missing.** The verb was called but is not part of the
   script's surface in this version.
3. **`manage-tasks` `tasks_already_exist` guard on a phase-4-plan re-run.** Re-running phase-4-plan after the
   outline was rebuilt (Q-Gate 46f50b fix) hit the guard because the earlier tasks were still present; the re-run
   path needs a documented way to replace or clear them.
4. **`switch-and-pull` returned `pull_failed`** because the main checkout had unstaged changes
   (`.plan/marshal.json` modified, untracked `opencode.json`). The finalize branch switch does not tolerate or
   report a dirty main checkout up front.
5. **`pr edit` without a prepared body** failed with "At least one of --title or a prepared body must be
   provided": the body has to be staged with `prepare-body` before `pr edit` is called.
6. **A first refine pass overwrote another plan's `.plan/temp/module_mapping.toon`.** The scratch file sits at a
   fixed path shared by all plans, so concurrent plans clobber each other; it should be plan-scoped
   (e.g. under the plan's `work/` directory).

## Candidate rules

- Workflow docs and the scripts they call must agree on verb names (items 1 and 2).
- Re-entrant phases need an explicit replace or clear path for state they create (item 3).
- Shared fixed-path scratch files must be plan-scoped (item 6); steps that need a clean main checkout should
  check for it before acting (item 4); verbs that need a staged body should say so in their error (item 5).
