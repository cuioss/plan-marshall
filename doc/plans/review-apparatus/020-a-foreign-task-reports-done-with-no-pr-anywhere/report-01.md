# Run report — a-foreign-task-reports-done-with-no-pr-anywhere (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/foreign-task-no-pr-ynmbpv` (harness-assigned; kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded per the cloud-plan-lane surface for a Python-production + skill/bundle change:

- `plan-marshall:ref-code-quality` (bundle path)
- `pm-plugin-development:plugin-script-architecture` (bundle path)
- `plan-marshall:persona-implementer` (bundle path)
- `pm-dev-python:python-core` (bundle path)
- `pm-dev-python:pytest-testing` (bundle path)
- `pm-plugin-development:plugin-architecture` (bundle path)

GitHub access path: **GitHub MCP server** (cloud session; no `gh` CLI reachable).

## Deliverables

### D0 — GATE (mutates nothing): is a foreign task distinguishable from a host task at the moment `done` is written?

**Verdict: the discriminator EXISTS and is derivable. The plan does NOT halt; D1 and D2 proceed.**

**The completion seam is single and locatable** (confirms the HYPOTHESIS claim label). `done` is
written in exactly one place: `manage-tasks/scripts/_tasks_crud.py::cmd_update` (the
`args.status == 'done'` branch, lines ~662–667), which loads the full task record, sets
`status='done'`, and writes it back. Done-ness is decided at this one seam, not distributed across
per-task-kind logic. The task-completion validation rules (`task-contract.md` §"Validation Rules"
8–9: `done` requires all steps `done`/`skipped` and verification passed) are keyed on the same record.

**No repository-target field exists** in the task schema. `manage-tasks/standards/task-contract.md`
and `_tasks_core.py::TaskDict` carry `number/title/status/domain/profile/origin/skills/deliverable/
depends_on/description/steps/verification/current_step` (+ optional `priority/finding/cost_*/
envelope_id`). None names a repository or project-dir. So the naïve "read a foreign flag" path does
not exist — which is exactly the halt-trigger the plan warned about IF nothing else were derivable.

**But the discriminator the plan names IS present and survives to the seam.** The candidate is
"an `affected_files` path outside the project root", and it is preserved at both read points:

- **Task record (`steps[].target`), read at the completion seam.** Step targets are normalised at
  task-creation time via `_tasks_core.normalize_step_path` → `file_ops.normalize_to_repo_relative`
  (`tools-file-ops/scripts/file_ops.py:339`). That function strips the repo-root prefix **only when
  the path is under the git toplevel**; an absolute path **outside** the project root falls through
  and is **returned unchanged** (line 366). A relative path is returned unchanged. So a foreign
  task authored with an absolute outside-root target keeps that absolute outside-root string in
  `steps[].target`, and `validate_steps_are_file_paths` admits it (it has a `/` separator and a
  source extension). The foreign signal is therefore intact in the record the seam mutates.
- **Deliverable (`affected_files[].path`), read at the archive gate (D1's position).**
  `manage-solution-outline/scripts/_plan_parsing.py::_extract_affected_files` (lines 277–303)
  captures each path **verbatim** — no normalisation at all — so an outside-root path survives at
  the deliverable level too.

**Derivation method (the population is derived, not enumerated).** A path is *foreign* iff, resolved
against the project root (the git toplevel — `file_ops.cwd_checkout_root()`, the same reference
`normalize_to_repo_relative` uses), it lies outside it: an absolute path not under the root, or a
relative path that escapes via `../`. The population of foreign tasks/deliverables is obtained by
applying this predicate to every declared path — **not** by hand-listing task `origin` kinds. This
satisfies D0's "derive the population; do not hand-enumerate the task kinds."

**Supporting mechanism (the foreign lane is real, not hypothetical).** The system already targets a
non-host repository through `--project-dir`: the CI router `tools-integration-ci/scripts/ci.py`
consumes `--project-dir` **before** provider dispatch (lines 121–131, via
`ci_base.extract_routing_args`), setting the process-global cwd for every `gh`/`git` subprocess; and
`script-shared/scripts/resolve_project_dir.py` is the canonical two-state `--plan-id`/`--project-dir`
resolver returning an absolute working-tree root. "Outside the project root" is thus a real,
already-instrumented axis, not an invented one.

**Honest caveat (recorded, does not trigger the halt).** The discriminator's *reliability* depends on
foreign `affected_files` being authored as absolute-outside-root (or `../`-escaping) paths; a foreign
change authored with bare relative paths would resolve *inside* the root and read as host. This is a
property of authoring convention, not of the seam — and it is the same discriminator the plan itself
adopts (D1 operationalises "path outside the project root"). It bounds the gate's coverage, not its
correctness, so it is residue, not a halt.

**Re-derivation of the plan's OBSERVED leads (per the plan's own "every count is a lead" warning):**

- The literal artifact string **"PR not yet opened"** does **not** exist anywhere in the current
  bundle tree (searched `marketplace/bundles/**`, case-insensitive, plus variants `not opened` /
  `PR pending` / `no PR`). The phase-5 "foreign" matches are about out-of-scope **test failures**
  (`exclusively_out_of_scope`), unrelated to foreign repositories. The branch-cleanup "foreign"
  matches mean **foreign-safe lock release** (idempotency), also unrelated. So the D2 premise "phase 5
  already emits *PR not yet opened*" does not reproduce against this clone — it is a lead from the
  motivating run, now re-derived as **absent**. There is likewise **no** existing landing gate, no
  `landing-state` verb, and no structured foreign-vs-host signal. This makes D1's verb/gate and D2's
  column genuinely new (matching their "add" framing) and means D2's "replace the prose" reduces to
  "have a gate read a structured signal instead" (D1's gate) plus the foreign column.

### D1 — a foreign task's done-ness is measured at the PR, not the commit

**Done.** Commit `5f9cd22` (`fix(review-apparatus): measure foreign-task done-ness at the PR, not the commit`).

- **The verb.** `ci_base.derive_landing_state(pr_states, pushed)` + the declared set
  `ci_base.LANDING_STATES = ('merged', 'pr_open', 'pushed_no_pr', 'unpushed')` — the pure, provider-
  agnostic correlation. PR state is authoritative over push state (merged/open precede the push check),
  so a merged-then-deleted branch is not misread as `unpushed` and a closed-unmerged PR collapses to
  the blocking `pushed_no_pr`. The github handler `_github_pr.cmd_pr_landing_state` gathers the two
  inputs — `github_ops.run_git` (new helper, routed at the foreign checkout via the router's
  `--project-dir`) for remote containment, and `gh pr list --head B --state all` for PR state — and is
  registered as `('pr','landing-state')` with a `--branch` subparser (github-provider-specific, like
  `add_pr_create_args`, leaving gitlab untouched). Auth failure / unparseable output / gh-list failure
  all hard-error rather than silently downgrading a merged/open verdict to `pushed_no_pr`.
- **The gate.** `phase-6-finalize/scripts/foreign_pr_gate.py::check` iterates the foreign deliverables
  (from `list-deliverables`' `foreign` column — D2), resolves each foreign repository's landing state
  via `ci pr landing-state --project-dir {root}`, and returns `status: blocked` while any is
  `pushed_no_pr`. It fails **closed** on every indeterminacy — an un-listable outline, an unresolvable
  project root, an unresolvable foreign root, or a landing state that is unreadable or outside the
  declared `LANDING_STATES` model all yield `status: error` (exit 1). It CLEARS only when it has
  positively read an in-model landing state for every foreign repository and none is `pushed_no_pr`
  (this fail-closed posture was hardened in response to PR review — see Findings). Wired into
  `standards/archive-plan.md` as the
  **first** section ("Pre-Archive Foreign-PR Landing Gate"), before Mark-Step-Complete and the archive
  call, with the exit-code/status handling spelled out. Auto-discovered by the executor generator's
  glob (no manifest edit; regeneration is machine-local and not owed by this lane).
- **Tests** (`test/plan-marshall/workflow-integration-github/test_pr_landing_state.py`,
  `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py`): one case per return value driven
  through **both** the pure function and the real handler, each parametrized over `LANDING_STATES` so
  the population is asserted against the verb's **own declared set** (`set(_CASE_PER_STATE) ==
  set(LANDING_STATES)`), not a hand-listed enum; plus the archive-refusal test proving a `pushed_no_pr`
  foreign deliverable is `blocked`. All fail before the change (the verb/gate did not exist).

### D2 — the recorded-but-unread gap becomes a gate input; foreign coverage column

**Done.** Commit `5f9cd22`.

- **The predicate.** `_plan_parsing.is_foreign_path(path, project_root)` — the single lexical
  (`os.path.normpath`/`commonpath`, never a filesystem `resolve()`, because the foreign tree may be
  absent) outside-the-project-root discriminator. Correct on every trap: host-relative → host,
  host-absolute-under-root → host, root-itself → host, foreign-absolute → foreign, `../` escape →
  foreign, and the sibling-prefix trap (`/repo-other` vs `/repo`, where a naïve `startswith` fails) →
  foreign.
- **The column.** `manage-solution-outline list-deliverables` now stamps `foreign: true/false` on each
  `affected_files` entry and a per-deliverable roll-up (`_annotate_foreign`). This is the population the
  D1 gate iterates, and it stops a coverage ratio from silently pooling host paths with foreign ones.
- **The recorded-but-unread gap.** A gate now reads a **structured signal** (the `landing-state` verb
  and the `foreign` column), not artifact prose — D2's essence. The plan's premise that phase-5 emits a
  literal *"PR not yet opened"* line does **not** hold against this clone (re-derived as absent, above),
  so there is no prose line to replace; the structured-signal-a-gate-reads requirement is met by D1's
  gate, and the coverage column separates the two populations. Recorded as a finding rather than
  chasing a non-existent string.
- **Test impact.** The existing `test_list_deliverables` asserted the exact `affected_files` shape and
  was updated to include the new `foreign` key (`foreign: False` for its repo-relative path) — the sole
  intended ripple; no other existing assertion changed.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production scripts + tests), so the
build ran. **`./pw verify plan-marshall`: green — `15848 passed, 1 skipped`, `=== verify: SUCCESS ===`.**
Quality gate clean (mypy `Success: no issues found in 274 source files`; ruff `All checks passed!`;
SPDX-header check passed) after one fix (mypy `arg-type` narrowing in `_annotate_foreign`:
`bool(project_root)` → `project_root is not None`). Scoped to the plan-marshall module because the whole
change is inside that bundle + `test/plan-marshall/`; CI (`python-verify.yml`) runs the full verify on
the PR.

## Findings

Per instance (source / description / disposition):

- **verification-subagent / D0:** confirmed the "no halt" verdict independently against the actual
  code (single completion seam at `_tasks_crud.py:cmd_update`; `normalize_to_repo_relative` preserves
  outside-root absolute paths; `_extract_affected_files` verbatim). **Accepted — no change.**
- **verification-subagent / D1:** verb + gate satisfy the plan's exact test demands (population asserted
  against declared set; archive-refusal test); correlation logic correct (merged authoritative;
  closed-unmerged → `pushed_no_pr`). **Accepted — no change.**
- **verification-subagent / D2:** predicate correct on every trap incl. the sibling-prefix case;
  "PR not yet opened" independently confirmed absent from the tree. **Accepted — no change.**
- **verification-subagent / out-of-scope:** diff confirmed clear of the landing-message site, the
  merge-lock/branch-cleanup surfaces, and any other repository. **Accepted — no change.**
- **verification-subagent / test-harness artifact:** running whole affected directories through a bare
  single-process `pytest` surfaces 7 failures + collection errors from the pre-existing
  `github_ops ↔ _github_pr` circular import under single-process collection — **reproduced identically
  on `origin/main`** (7 failed / 23 errors on main vs 7 failed / 24 on branch, the +1 being the new
  test file entering the shared `sys.modules`), and the canonical `./pw` harness (which isolates via
  xdist) is green. **Rejected as collateral — pre-existing, not attributable to this change; verified.**
- **verification-subagent / cold read of the refusal text:** **BLOCKING** — the operator-facing
  `archive-plan.md` gate section and the `foreign_pr_gate` blocked-path message both read as an
  unambiguous prohibition on proceeding, not advice to note. **Passes the plan's cold-read bar.**
- **verification-subagent / residue (not a gap):** discriminator coverage depends on foreign paths
  being authored absolute-outside-root or `../`-escaping; a bare-relative foreign path would read as
  host. Bounds coverage, not correctness; same discriminator the plan adopts. **Recorded as residue.**

The verification sub-agent (read-only) found no gaps against the plan. The subsequent PR review did —
see the next subsection.

### PR review round (CodeRabbit, 9 actionable comments)

CodeRabbit posted 9 comments; most flagged a genuine **fail-closed** weakness (my first cut surfaced
indeterminacies but still cleared), which aligns with the plan's own discipline and `ref-code-quality`
§ error-handling ("a gate must fail closed rather than emit an unsubstantiated clean verdict"). Fixed
in commit that follows this report update:

- **pr-review / gate fail-closed (Major ×2):** the gate cleared on an unresolvable foreign root and on
  a landing-state read failure. **Fixed** — unresolvable project root, unresolvable foreign root,
  unreadable landing state, and any state outside `LANDING_STATES` now yield `status: error` (fail
  closed); the gate clears only on a positively-read in-model state. `archive-plan.md` + the gate
  docstring + tests updated.
- **pr-review / handler fail-closed (Major):** `_branch_is_pushed` turned a git failure into `False`
  (→ `unpushed` → clear), and malformed PR entries were ignored. **Fixed** — a git-containment failure
  the verdict rests on now errors (tolerated only when a tip-matching merged/open PR settles it);
  non-object entries and entries with no usable `state` now error. Tests added.
- **pr-review / stale-tip + truncation (Major):** `gh pr list --head` returns historical PRs by branch
  name, so a merged PR for an earlier tip could report `merged` for new commits; the default 30-limit
  could truncate. **Fixed** — the handler resolves the branch tip SHA and counts only PRs whose
  `headRefOid` is that tip; `--limit 100` with a fail-closed truncation guard. Stale-tip + truncation
  tests added.
- **pr-review / derive test population (Minor):** removed the mirrored-literal state-tuple assertion in
  favour of a non-vacuity guard + a coverage assertion against `LANDING_STATES`. **Fixed.**
- **pr-review / unpushed coverage (Minor):** added a gate test asserting `unpushed` clears. **Fixed.**
- **pr-review / manage-solution-outline should hard-error on root-resolution failure (Major, sub-point
  of the gate comment):** **Rejected, with reason.** `list-deliverables` is a general-purpose command
  used across planning and finalize; hard-erroring on a non-git cwd would regress every caller, and the
  plan makes the `foreign` column *advisory* by design with the blocking decision in the gate. The
  fail-closed guarantee now lives fully in the gate: it resolves its OWN project root and errors if it
  cannot, so an unresolvable root can never produce a false clear even though the advisory column fails
  open. Reply posted on the PR.
- **pr-review / plan.md: contract-load guard, done-vs-archive seam, historical D2 wording (3 comments
  on the plan spec):** **Rejected, with reason.** These critique the input plan document, not this
  change's code. (a) The cloud-plan-lane skill-load guard is lane infrastructure, out of this plan's
  scope. (b) The "done written at the commit, enforced at archive" seam is the plan's *deliberate*
  design: the foreign PR is opened in finalize, so it legitimately does not exist at per-task
  `done`-write time (phase 5) — the archive gate is the correct, and plan-specified, enforcement point;
  moving enforcement to the `done` transition would block on a PR that is not yet due. (c) The plan's
  *"PR not yet opened"* premise is already reconciled in this report (§ D0) as a historical lead absent
  from the clone, exactly as the plan's own claim-labels anticipate ("every count is a lead").
  Replies posted on the PR; the plan spec is the input and is not rewritten here.

## Reviewer participation

_Filled at the merge gate from the stored comment bodies (§ Step 7 / Step 8)._

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

- **Owed conditional check (carried so it cannot lapse).** A prior plan shipped a language-specific
  reviewer instruction pack and left its confirm/refute check unrun. The procedure: re-review a closed
  Java pull request another reviewer found in-charter defects on — `cuioss/API-Sheriff` **#185**
  (26 inline items) or **#154** (47) — with the shipped pack installed, and compare against this
  reviewer's recorded zero on those same diffs. **That repository is not in this session's scope and
  this plan changes nothing in it — the check is read-only and NOT reachable from this clone, with no
  operator to grant access.** Per the plan's instruction, the check **remains owed**; a refutation
  would be a publishable result, not a failure. Do not read this plan's completion as implying the
  check ran.
- The absolute-path authoring dependency of the foreign discriminator (see D0 caveat).
