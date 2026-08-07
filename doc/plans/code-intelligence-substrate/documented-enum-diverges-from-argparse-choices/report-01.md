# Run report — documented-enum-diverges-from-argparse-choices (run 01)

**Date (UTC):** 2026-08-07    **Branch:** `fix/documented-enum-diverges-from-argparse-choices`    **PR:** _pending_    **Outcome:** partial (in progress)

## Skills loaded

Attempted the cloud-plan-lane Step 1 skill set. **The plugin skills did not resolve** in
this session: `~/.claude/plugins/cache/plan-marshall/` is absent (only
`~/.claude/plugins/installed_plugins.json` exists), so the `plan-marshall` plugin the
repository's `.claude/settings.json` declares was not installed at session start. The
following all returned "Unknown skill":

- `plan-marshall:ref-code-quality`
- `pm-plugin-development:plugin-script-architecture`
- (and, by extension, `plan-marshall:persona-implementer`, `pm-dev-python:python-core`,
  `pm-dev-python:pytest-testing`, `pm-plugin-development:plugin-architecture`)

Per the contract ("If a skill fails to resolve, say so in the report rather than proceeding
as if it had loaded"), this is recorded rather than papered over. The work identity and
standards were sourced directly from `CLAUDE.md` and the affected files instead. Only
`cloud-plan-lane` (project-local under `.claude/skills/`) loaded.

## Branch prefix divergence (recorded per contract)

The session harness assigned branch `claude/enum-argparse-choices-divergence-ckqr5h` and
instructed "never push to a different branch without explicit permission." The repository's
`CLAUDE.md` and the cloud-plan-lane contract require a branch from the closed set
(`feature/`/`fix/`/`chore/`) — the plan declares **Branch prefix: fix** — because
`python-verify.yml`'s push trigger only fires for those prefixes, so a `claude/` branch
could not produce the required `verify / conclusion` check. Resolved via `AskUserQuestion`;
the operator granted explicit permission to use `fix/documented-enum-diverges-from-argparse-choices`.

## Deliverables

Re-derivation first (the plan's counts "6 and 11" were unverified hypotheses):

- **Parser `choices`**: `DISPATCH_TERMINATION_CAUSES` in `manage-metrics/scripts/manage-metrics.py`
  is an **11-value** tuple (`voluntary_checkpoint`, `task_complete_returned_verbatim`,
  `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`, `step_complete`,
  `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`),
  used as `choices=list(DISPATCH_TERMINATION_CAUSES)`. The "11" half of the hypothesis is
  **confirmed**.
- **The "SKILL documents exactly the first 6" half is REFUTED.** `manage-metrics/SKILL.md`
  already documents all 11 values at all three sites (the fenced command block, the
  `--termination-cause` bullet enumeration, and the Canonical-invocations block), and its
  rejection sentence is already accurate. This was corrected by an earlier commit
  (#1083 rewrote the file) and is guarded by `test_every_documented_termination_cause_site_matches_the_enum`.

### Deliverable 1 — Correct the enum + rejection sentence in `manage-metrics/SKILL.md`

**Already satisfied — verified no-op.** The documented list equals the parser's `choices`
at every site, and the rejection sentence ("Required — missing or unrecognised values are
rejected as script errors …") is true of the parser as written (see the `cause not in
DISPATCH_TERMINATION_CAUSES` guard and the argparse `choices`). No change made; recorded as
verified rather than assumed.

### Deliverable 2 — Correct the consumer `plan-retrospective/references/logging-gap-analysis.md`

**Done** — commit `09f4acd`. The `DISPATCH_TERMINATION_CAUSE` rule's "canonical value set"
enumerated only 6 of the 11 values (`voluntary_checkpoint`, `task_complete_returned_verbatim`,
`budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`), so an analyst
following the reference literally emitted a per-cause distribution omitting every cause past
the sixth. Rewrote it to enumerate the full accepted set, point at `DISPATCH_TERMINATION_CAUSES`
as the source of truth, and expand the example distribution to all 11. No count word ("eleven")
was hard-coded into the prose, to avoid re-introducing the count-prose-staleness archetype the
plan's provenance note identifies.

### Deliverable 3 — Pin it structurally

**Done** — commit `09f4acd`, in `test/plan-marshall/manage-metrics/test_manage_metrics.py`.
Four new tests, modelled on the existing SKILL.md documentation-site contract (the plan's
named model), derive **both** sides — the documented set is parsed out of the markdown, the
expected set is read from `DISPATCH_TERMINATION_CAUSES`:

- `test_logging_gap_analysis_termination_cause_set_matches_the_enum` (positive) +
  `test_logging_gap_analysis_guard_detects_a_dropped_value` (negative control).
- `test_data_format_termination_cause_enum_matches_the_enum` (positive) +
  `test_data_format_termination_cause_guard_detects_a_dropped_value` (negative control).

The `data-format.md` enum line was already in sync but previously unguarded; it is now pinned
too. The SKILL.md side keeps its pre-existing guard. Each negative control drops one value and
proves the guard fails (verified: the mutated set loses `agent_returned` and diverges). All
8 termination-cause tests pass; both positive parses equal the 11-value set; both negative
controls fail in the correct direction.

### Deliverable 4 — Sweep for siblings

**Done (recorded)** — the sweep's population and result are below (Findings § sweep). "Done
when" is a recorded population + result, not a fix of every sibling (each named-constant enum
is a separate decision with its own consumers, mirroring the plan's out-of-scope reasoning).
Two live drifts of the same defect class were found and are recorded as residue for
follow-up plans, not fixed here.

## Build gate

`git diff --name-only origin/main...HEAD` = `plan.md`, `logging-gap-analysis.md`,
`test_manage_metrics.py`. A `*.py` file changed → the gate is the full `./pw verify plan-marshall`
(quality-gate **and** tests), matching the plan's "both build-gate surfaces apply".

- **Quality-gate**: clean after one fix. First run failed on a single ruff `W605`
  (escaped-backtick `\`` in a new docstring); reworded the docstring and folded the fix into
  the commit via `--amend` (unpushed at the time). Re-run: mypy "no issues found in 269 source
  files", ruff clean.
- **Tests**: 15005 passed, 1 skipped, **3 failed**. All 3 failures are in files this change
  does not touch and are **proven pre-existing on `origin/main`** (ran them against a clean
  `origin/main` worktree — identical failures). They are a root-execution / path-validation
  artifact of the sandbox (each expects an `error` status for a nonexistent/invalid path but
  gets `success`):
  - `platform-runtime/test_opencode_runtime.py::test_project_initial_setup_invalid_dir_returns_error`
  - `workflow-integration-git/test_git_workflow.py::TestAnalyzeDiff::test_analyze_file_not_found`
  - `workflow-integration-git/test_git_workflow.py::TestDetectArtifacts::test_nonexistent_root_fails`

  The change's own surface is clean: all manage-metrics tests, including the 4 new guards,
  pass. These are the "red on the base branch too" case; CI (non-root) is expected to be green.

## Findings

### Verification sub-agent (Step 6)

_Pending — recorded after dispatch._

### Deliverable-4 sweep (independent read-only sub-agent)

**Population swept**: every `choices=` occurrence under `marketplace/bundles/**/scripts/**.py`
— ~140 real argparse call sites after excluding 6 comment/docstring non-sites. Of these,
**51 reference a named module-level constant** (the drift-prone shape), ~88 use an inline
literal list/tuple, and 1 is a parameterized indirection (`add_phase_arg(..., choices=…)`,
through which `manage-findings` passes `QGATE_PHASES`). **26 distinct named constants** are
used as choices besides `DISPATCH_TERMINATION_CAUSES` (defined mostly in
`tools-file-ops/scripts/constants.py`). The sweep also grepped each constant's distinctive
values across `marketplace/bundles/**/*.md`, and grepped the whole `test/` tree for any test
that parses those docs and compares to the constant.

**Result — the archetype is systemic.** Essentially every named-constant `choices=` site has
its full value set re-spelled as literal prose in the owning skill's docs, and **none of those
prose enumerations are guarded by a doc-parsing test** (the few existing tests —
`test_cleanup.py`, `test_title_token.py`, `test_phase_6_manifest_executor.py` — pin the
constant against code or do partial per-token presence checks, none parse the doc for full-set
equality). **No other `termination_cause` enumeration** exists beyond the three known docs.

**Two live drifts (same defect class as the one fixed here) — recorded as residue, not fixed:**

1. `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:70` — the "Finding
   Types" prose lists **12** types (`bug … pr-comment`) but `FINDING_TYPES` (constants.py:118)
   has **14** (adds at least `arch-constraint`, and `pr-comment-overflow`). Verified: SKILL.md:70
   omits `arch-constraint`. Unguarded at the doc level.
2. `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md:260` — the `--category`
   prose lists **3** values (`bug, improvement, anti-pattern`) but `LESSON_CATEGORIES`
   (constants.py:191) has **4** (`… , arch-constraint`). Verified. The same file's synopsis
   (~line 700) lists all 4, so it is internally inconsistent too. Unguarded at the doc level.

## Contract check (Step 9)

_Pending — completed as the final action._

## What have we learned (Step 9)

_Pending — completed as the final action._

## Residue

- **Two live sibling drifts** (manage-findings finding-types 12/14; manage-lessons categories
  3/4) — same archetype, warrant their own fix-plus-guard plans. Not fixed here to keep this
  PR scoped to the `termination_cause` enum (matching the plan title and deliverables).
- **Systemic gap**: ~24 further named-constant `choices=` sets have full-set prose mirrors in
  their SKILL.md/standards docs with no doc-parsing guard. A generalized guard (parse each
  doc's enumeration, compare to the constant) would prevent the whole class; that is an
  epic-level decision, not this plan's.
- **Plugin cache unsynced**: this run edited `marketplace/bundles/**`. Per the contract, a
  local `/sync-plugin-cache` is owed by whoever picks this up on a developer machine — the
  cloud lane cannot write `~/.claude/`.
