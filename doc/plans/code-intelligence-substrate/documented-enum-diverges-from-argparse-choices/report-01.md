# Run report — documented-enum-diverges-from-argparse-choices (run 01)

**Date (UTC):** 2026-08-07    **Branch:** `fix/documented-enum-diverges-from-argparse-choices`    **PR:** [#1100](https://github.com/cuioss/plan-marshall/pull/1100)    **Outcome:** partial (in progress)

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
- **Tests**: 15005 passed, 1 skipped, **3 failed**. The 3 failures are in files this change
  does not touch:
  - `test/plan-marshall/platform-runtime/test_opencode_runtime.py::test_project_initial_setup_invalid_dir_returns_error`
  - `test/plan-marshall/workflow-integration-git/test_git_workflow.py::TestAnalyzeDiff::test_analyze_file_not_found`
  - `test/plan-marshall/workflow-integration-git/test_git_workflow.py::TestDetectArtifacts::test_nonexistent_root_fails`

  **Control run (unmodified tree, this VM).** "CI was green on main" was not accepted as
  settling it — CI is GitHub Actions, a different environment from this cloud sandbox. The same
  3 test IDs were run against a clean `origin/main` checkout **in this VM** (a detached
  `origin/main` git worktree; the lane's `.venv` pytest, since `.plan/execute-script.py` — the
  executor the `module-tests` command uses — does not exist in a fresh clone). **All 3 fail
  identically in the control** (`assert 'success' == 'error'`). They are therefore
  **environment-dependent in the cloud sandbox, not caused by this change** — each expects an
  `error` status for a nonexistent/invalid path but gets `success` (a root-execution /
  path-validation artifact: the suite runs as `root`, so existence/permission-denial checks do
  not trip). The change's own surface is clean: all manage-metrics tests, including the 4 new
  guards, pass in both the branch run and in isolation.

  **Lane-structural finding.** Because these 3 tests fail environmentally in the cloud sandbox
  on the *unmodified* tree, a `module-tests` run in this lane can **never** produce a clean
  result here, yet the merge gate (Step 8) requires "all checks green". The clean signal for
  this lane therefore has to come from CI (GitHub Actions, non-root), not from the in-VM build.
  This is a structural gap in the lane, recorded as a contract-learning candidate (Step 9,
  "What have we learned").

## Findings

### Verification sub-agent (Step 6)

An independent read-only `general-purpose` sub-agent verified the committed diff against the
plan's deliverables (not the diff's intent). **Clean verdict — no findings requiring a fix.**
It independently re-derived the counts (tuple = 11; SKILL.md documents 11 at all three sites),
so it confirmed the D1 "already-satisfied, no defect skipped" claim rather than taking it on
trust; confirmed D2's consumer set now equals the tuple; **re-implemented `_parse_backticked_value_set`
against the real files** and confirmed each anchor is unique, the run captures exactly 11
tokens and stops at the terminating period (no over-capture, a subset fails the bidirectional
`==`), and both negative controls drop the first (enumeration) `agent_returned` and diverge —
i.e. the guard genuinely fails on divergence, it is not vacuous; and confirmed D4 is a
complete record-only sweep meeting its "Done when", with the parser's accepted values
unchanged and no undeclared collateral.

Two caveats it raised, both now closed by this run:

- *"pytest is not installed in the sub-agent's environment, so I replicated the guard logic
  rather than running the suite."* — Closed: the suite ran in the main session's `.venv`
  (15005 passed, incl. the 4 new guards).
- *"I did not independently reproduce the claim that the 3 failures are pre-existing."* —
  Closed: the control run above reproduces all 3 on a clean `origin/main` in this VM.

No finding was rejected — there were none. Nothing was deferred.

### Cross-plan finding (operator-provided, recorded as residue — no action taken)

The operator independently verified, on `main`, that **PLAN-TRUTH-012** (epic
`truthful-signals`, staged) carries the same premise this plan's D1 refuted — but as an
**OBSERVED** claim rather than a HYPOTHESIS. TRUTH-012's objective states that
`manage-metrics` SKILL.md documents the termination-cause enum "in two places, and both list
six of the eleven values." That premise is **refuted**: `DISPATCH_TERMINATION_CAUSES` has 11
values and both doc sites (SKILL.md lines 388 and 639) list all 11 — the same re-derivation
this run performed for D1. TRUTH-012's header explicitly split the item, routing the DOC half
to this plan (PLAN-CIS-009) with the note "do not re-file it here"; only the CIS-009 copy
carried a HYPOTHESIS label, which is why this run caught the staleness while the unlabelled
TRUTH-012 copy is still queued. TRUTH-012's *other* half — "add the structural guard that
retires the class" — is **not** refuted and is exactly what this run's new guards prototype.

Recorded as a recommendation only; **no fold performed and nothing edited outside this
branch** (per the operator's instruction). Recommended routing for the two live sibling drifts
found by D4 (`manage-findings/SKILL.md` finding-types 12/14; `manage-lessons/SKILL.md`
categories 3/4, both missing `arch-constraint`): **PLAN-TRUTH-012**, which owns the
class-retirement half.

### Deliverable-4 sweep (independent read-only sub-agent)

**Population swept — exact, reproducible census.** The initial sub-agent sweep reported
approximate figures ("~140 sites"); a tilde cannot support a completeness claim, so the
population was re-counted deterministically with an **AST walk** (which sees only real
`choices=` keyword arguments in `ast.Call` nodes — comments, docstrings, and string literals
containing the text `choices=` are never counted, and a function-definition default such as
`def add_phase_arg(..., choices=None)` is excluded because it is a parameter default, not a
call keyword). The census script is `count_choices.py` (reproduced verbatim at the end of this
report); run as `python3 count_choices.py` over `marketplace/bundles/**/scripts/**/*.py` it
emits:

```text
files scanned            : 380
parse errors             : 0
TOTAL choices= call sites: 148
  named-constant shape   : 52
  inline-literal shape   : 96
  other/indirection      : 0
```

- **148** argparse `choices=` call sites (exact, not approximate).
- **96** use an inline literal list/tuple (`choices=['toon','json']`, `choices=('github','gitlab')`, …).
- **52** are name references (bare `Name`/`Attribute`, or `list()`/`sorted()` wrapping one),
  comprising **50 references to module-level named constants** — the drift-prone shape —
  across **25 distinct constant expressions** (note `VALID_TYPES` resolves to two distinct
  constants in different skills, so this is a floor on distinct constants), **plus 2
  non-constant name refs**: the `add_phase_arg(..., choices=choices)` parameter passthrough in
  `tools-input-validation/scripts/input_validation.py` and one `choices=modes` local in
  `script-shared/scripts/build/_build_cli.py`.
- **0** other/indirection shapes.

The 25 distinct module-level named-constant expressions (site counts in parentheses):
`BOT_KINDS` (3), `CERTAINTY_VALUES` (2), `FINDING_TYPES` (2), `PR_COMMENT_KINDS` (2),
`QGATE_PHASES` (4), `QGATE_SOURCES` (2), `RESOLUTIONS` (4), `SEVERITIES` (2), `VALID_LEVELS`
(1), `VALID_STATUSES` (3), `VALID_STORES` (2), `VALID_TYPES` (4), `VALID_WARNING_CATEGORIES`
(3), `list(ARCHITECTURE_REFRESH_TIER_0_VALUES)` (1), `list(ARCHITECTURE_REFRESH_TIER_1_VALUES)`
(1), `list(CLEANUP_TARGETS)` (1), `list(COVERAGE_VERDICTS)` (1), `list(DISPATCH_TERMINATION_CAUSES)`
(1), `list(LIST_STATUS_CHOICES)` (1), `list(VALID_CATEGORIES)` (3), `list(VALID_STEP_INTENTS)`
(2), `list(_REGISTRY)` (1), `list(_RESOLVED_ASK_LANE_VALUES)` (1), `sorted(TITLE_TOKEN_OWNERS)`
(2), `sorted(TITLE_TOKEN_STATES)` (1). Most constants are defined in
`tools-file-ops/scripts/constants.py`. The sub-agent additionally grepped each constant's
distinctive values across `marketplace/bundles/**/*.md`, and grepped the whole `test/` tree
for any test that parses those docs and compares to the constant.

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

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | partial | Only `cloud-plan-lane` loaded; the plugin skills did not resolve (cache absent) — recorded in § Skills loaded, not papered over. |
| 2 Branch | done | `fix/documented-enum-diverges-from-argparse-choices`, prefix from the closed set, cut from freshly-fetched `origin/main`. Prefix conflict with the harness-assigned `claude/` branch resolved by operator permission. |
| 3 Plan directory | done | `doc/plans/code-intelligence-substrate/documented-enum-diverges-from-argparse-choices/plan.md` exists (git mv, history preserved) and opens with the first-instruction block (verified present, no repair needed). |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" footer; deliverables addressed (D1 verified no-op, D2/D3 implemented, D4 recorded). |
| 5 Build gate | done | Python changed → full `./pw verify plan-marshall`; quality-gate clean, 15005 tests pass incl. 4 new guards; 3 environment-dependent failures proven pre-existing on `origin/main` in-VM (control run). |
| 6 Verification sub-agent | done | Independent read-only agent; clean verdict, no findings; both its caveats closed by this run. Recorded in § Findings. |
| 7 PR cycle | in progress | PR [#1100](https://github.com/cuioss/plan-marshall/pull/1100) open; subscribed to activity. Both comment surfaces read; bot findings dispositioned as they arrive. |
| 8 Merge gate | pending | Auto-merge (squash) to be enabled only once CI is green **and** every comment is handled; `state: MERGED` confirmed by read-back before the ledger stamp. |
| 8 Bridge ledger | pending | `doc/plans/code-intelligence-substrate/LEDGER.md` this plan's row stamped `implemented` (this row only) **after** the merge read-back; left `authored` if the run ends before merge. |
| 9 This check | done | This table. |

GitHub access path used: the **GitHub MCP server** (cloud path), as the contract expects for a
cloud run. Plugin-cache/`marketplace/bundles/**` edit: **yes** (`logging-gap-analysis.md`) — a
local `/sync-plugin-cache` is owed (recorded in § Residue).

## What have we learned (Step 9)

This run exercised the contract end to end and surfaced **three run-produced findings**. Per the
contract these are *presented to the operator* for a decision; none is self-approved, and any
accepted change ships as a **separate `chore/` PR**, not folded into this plan's PR.

1. **A cloud in-VM `module-tests` run can never be clean (lane-structural).** Three tests fail
   environmentally on the *unmodified* `origin/main` in this sandbox (root-execution
   path-validation; control run above). Step 5 tells the executor to "fix and re-run until it is
   genuinely clean" and Step 8 requires "all checks green", but neither acknowledges that the
   in-VM build for this lane structurally cannot go green, so the clean signal must come from CI
   (non-root GitHub Actions). **Proposed edit:** Step 5 should distinguish the in-VM build from
   the authoritative CI signal, and give a rule for known environment-dependent failures (prove
   pre-existing on `origin/main` in-VM → record and defer to CI, rather than block the PR).
2. **The lane depends on plugin skills that may be absent at session start.** Step 1's skills did
   not resolve because `~/.claude/plugins/cache/plan-marshall/` was absent even though
   `.claude/settings.json` declares the plugin. The contract already says to record the failure
   (which was done), but does not say how to proceed when the *work-identity* skills are the ones
   missing. **Proposed edit:** Step 1 should name this failure mode explicitly and state the
   fallback (source standards from the files, as this run did) so it is a sanctioned path, not an
   improvisation.
3. **Step 2 has no rule for a harness-assigned branch that violates the closed prefix set.** The
   session harness assigned `claude/…` and forbade switching without explicit permission, which
   directly conflicts with the closed-set requirement; a `claude/` branch gets no push-triggered
   CI. Resolved here via `AskUserQuestion`. **Proposed edit:** Step 2 should name this conflict and
   prescribe the resolution (obtain explicit operator permission, then use a closed-set prefix).

_Operator decision on these three proposals: **pending** — presented in the session, not yet
accepted; no `chore/` PR opened._

## Residue

- **Two live sibling drifts** (manage-findings finding-types 12/14; manage-lessons categories
  3/4, both missing `arch-constraint`) — same archetype, warrant their own fix-plus-guard.
  Not fixed here to keep this PR scoped to the `termination_cause` enum (matching the plan
  title and deliverables). **Recommended routing: PLAN-TRUTH-012** (`truthful-signals`), which
  owns the "add the structural guard that retires the class" half — see the Cross-plan finding
  above. Recommendation only; no fold performed.
- **PLAN-TRUTH-012 stale premise** (operator-verified): its OBSERVED claim that SKILL.md lists
  six of eleven values is refuted by this run's D1 re-derivation. Its DOC half was routed here
  and is now closed; its class-retirement half remains valid and is the natural owner of the
  sibling-drift residue above.
- **Systemic gap**: 50 named-constant `choices=` references (24 further distinct constants
  besides `DISPATCH_TERMINATION_CAUSES`) have full-set prose mirrors in their SKILL.md/standards
  docs with no doc-parsing guard. A generalized guard (parse each doc's enumeration, compare to
  the constant) would retire the whole class; that is an epic-level decision, not this plan's.
- **Plugin cache unsynced**: this run edited `marketplace/bundles/**`. Per the contract, a
  local `/sync-plugin-cache` is owed by whoever picks this up on a developer machine — the
  cloud lane cannot write `~/.claude/`.

## Appendix — `count_choices.py` (deliverable-4 census, verbatim)

Run as `python3 count_choices.py`; it walks `marketplace/bundles/**/scripts/**/*.py` via AST
and prints the exact `choices=` census reproduced in the Findings section above.

```python
import ast
from pathlib import Path

ROOT = Path('/home/user/plan-marshall/marketplace/bundles')
files = sorted(ROOT.glob('**/scripts/**/*.py'))
named, inline, other, parse_errors = [], [], [], []
WRAPPERS = {'list', 'tuple', 'sorted', 'frozenset', 'set'}


def is_named(node):
    if isinstance(node, (ast.Name, ast.Attribute)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in WRAPPERS:
        return len(node.args) == 1 and isinstance(node.args[0], (ast.Name, ast.Attribute))
    return False


def is_inline(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in WRAPPERS:
        return len(node.args) == 1 and isinstance(node.args[0], (ast.List, ast.Tuple, ast.Set))
    return False


for f in files:
    try:
        tree = ast.parse(f.read_text(encoding='utf-8'))
    except SyntaxError as e:
        parse_errors.append((str(f), str(e)))
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != 'choices':
                continue
            entry = (str(f.relative_to(ROOT.parent.parent)), kw.value.lineno, ast.unparse(kw.value))
            (named if is_named(kw.value) else inline if is_inline(kw.value) else other).append(entry)

total = len(named) + len(inline) + len(other)
print(f'files scanned            : {len(files)}')
print(f'parse errors             : {len(parse_errors)}')
print(f'TOTAL choices= call sites: {total}')
print(f'  named-constant shape   : {len(named)}')
print(f'  inline-literal shape   : {len(inline)}')
print(f'  other/indirection      : {len(other)}')
```
