envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-25T13:59:00Z
revision=1

# Process-rule issue: `detect-artifacts` routes the entire tracked test-fixture corpus to `uncertain`, making the pre-commit confirmation step unactionable

Reporter: plan `module-budget-campaign-completion`, commit instrumentation for
`default:finalize-step-simplify` (2 edited files).

## Observation

`plan-marshall:workflow-integration-git` § "Commit Changes" Step 3 requires, before every
commit: detect artifacts, delete the `safe` list, and **ask the user via `question` for the
`uncertain` list**.

On this repository that step yields:

```
root: .plan/local/worktrees/module-budget-campaign-completion
safe:      []
uncertain: 271 entries
total: 271
```

All 271 are **tracked, pre-existing repository files** — the `test/**/fixtures/**` corpus
(`test/plan-marshall/build-*/fixtures/`, `test/pm-plugin-development/plugin-doctor/fixtures/`,
`test/pm-documents/*/fixtures/`, …). Not one is an artifact of the commit being prepared, and
not one is safe to delete. The contract routes every tracked file to `uncertain`
unconditionally ("Tracked files never appear in `safe`; they are always routed to
`uncertain` so the caller must confirm before deletion"), so the cardinality is a function of
repository size, not of the change.

## Why this is a process defect

- A confirmation prompt whose correct answer is "delete none of these" every time trains the
  operator to answer reflexively, which is the exact state in which a genuine artifact among
  270 fixtures would be waved through.
- The 2 files actually being committed were not in either list, so the step contributed
  nothing to this commit: zero artifacts found, and a 271-item prompt that must be dismissed
  to proceed.
- The behaviour scales with the repo, so it gets strictly worse over time and cannot be
  worked around by discipline.

## Consequence if unfixed

The artifact gate is a ritual with no discriminating power on this project. Either the
tracked-file routing is narrowed to files that are **new or modified in the current diff**
(the only ones a commit can actually introduce), or `uncertain` is split so that pre-existing
untouched tracked files are reported as a count rather than as 271 confirmation items.

## Evidence

- `git-workflow detect-artifacts --root {worktree}` → `safe: []`, `uncertain: 271`,
  `total: 271`, `gitignore_resolved: true`, `tracked_resolved: true`.
- The commit proceeded with no deletion and no operator prompt; the 2 changed files
  (`test/plan-marshall/tools-script-executor/test_generate_executor_bootstrap.py`,
  `test/pm-plugin-development/tools-corpus-language-server/test_corpus_lsp_serve.py`) appear
  in neither list.
- Related, distinct: the plugin-doctor whole-tree gate's 79-of-80 false-positive residue
  already filed as `truth-179-opencode-target-detection-landed-005` is a different surface
  (the gate's file discovery) and must not be folded into this one.
