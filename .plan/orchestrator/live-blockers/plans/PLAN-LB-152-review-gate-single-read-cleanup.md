# PLAN-LB-152: The review gate's single-read change is cleaned up: the contract says what the code does, the dead branch and the dead guard are gone, a failing flatten is classified, and the tests no longer depend on the machine

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-152-review-gate-single-read-cleanup.md` and is queued as one row file, `queue/PLAN-LB-152.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-14 ("create a small plan for the fixes", after the three-layer analysis of PR #1988, merge `2bf7cd83d`).
> Every claim below was read at `2bf7cd83d` by a read-only three-layer leaf and the orchestrator re-read the ones marked as re-read. All of it fails
> closed today: the gate stops rather than passes. **Out of scope, and not in this plan:** the HIGH defect in the review-body parser (a CodeRabbit
> CAUTION-shape outside-diff block reads as zero findings; `_SUMMARY_RE`, the section table and `_body_findings` in `runbook_lane.py`), which stays
> an Open Defect for its own plan. If that plan is staged it overlaps this one on `runbook_lane.py` and is sequenced after it. No Sonar. No token or
> measurement work.

## Objective

PR #1988 made the runbook lane's review gate decide on one in-process GitHub fetch. The merge left the documented contract describing the old read,
left one verdict reason and one guard that the new read can never reach, let one in-process step sit outside the read guard, and gave a few tests a
dependency on the machine they run on. This plan makes the contract, the verdict code and the tests say and do what the single-read gate does, and
removes the wording the same PR added against the documentation standard. It changes no verdict a real read can produce.

## Deliverables

1. **The review-gate contract and the verdict code describe only what the single in-process read can produce.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: implementer
   - `runbook-lane/SKILL.md` § `review-gate` no longer says the read is `ci pr comments`, and no longer says a GitLab project answers
     `coverage_unavailable`; it says the gate reads GitHub's comment data in-process and that a project whose CI provider is not GitHub, or is not
     resolvable, answers `undecidable_read`.
   - The `coverage_unavailable` branch of `_review_gate_verdict` (`'complete' not in read`, with its comment about "the GitLab read") is removed with
     its mention in the SKILL.md reason list and its test, because a successful GitHub fetch always carries `complete`; a read without it is a truncated
     or malformed read and is covered by the `complete is not True` branch. Verify-at-outline first (Claim Labels): if any consumer outside
     `runbook_lane.py` reads the reason `coverage_unavailable` from `review-gate`, keep the branch and correct its comment and the document instead.
   - The unreachable required-reviewer read guard (`_required_review_read_failure(read)` and its call in `_review_gate_verdict`) is removed with the
     helper when nothing else calls it, and the verdict's docstring bullet about a separate required-reviewer read is corrected.

   *Done when:* these hold at `2bf7cd83d`, as behaviour (nothing a real read can produce changes): a read whose `status` is not success, a read with
   `complete` false, and a read for a project that does not route to GitHub each answer `merge_allowed: false` with `reason: undecidable_read`; a read
   with no `complete` key answers `undecidable_read` and not a traceback. The SKILL.md paragraph and the verdict docstring state the in-process GitHub
   read and name no reason the code cannot give; a test fails if the SKILL.md reason list names a reason `runbook_lane.py` can no longer return.

2. **A failing flatten is classified, and the read guard's import placement is pinned.**
   - Skills: pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: implementer
   - `_display_read` (the flatten) and its call in `_review_gate_verdict` run inside a guard that answers `undecidable_read` with a readable
     `detail` for the same exception types `_read_review_surfaces` classifies, so a malformed entry is never a traceback.
   - A test makes the provider module's import raise `ImportError` (by `sys.modules` entry set to `None`, or an equivalent that fails at the import
     statement and not at the fetch) and asserts `_read_review_surfaces` answers `status: error`; it fails if the imports move back outside the `try`.

   *Done when:* a read envelope whose `comments` holds a non-dict entry (or whose flatten raises) answers `undecidable_read` through `review-gate`; that
   fails at `2bf7cd83d` (a traceback). The import-placement pin holds at `2bf7cd83d` and is shown red by moving the two imports in
   `_read_review_surfaces` above the `try`.

3. **The review-gate tests do not depend on the machine and do not leak process state.**
   - Skills: pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: module-tester
   - Every test that drives the real `_read_review_surfaces` stubs `resolve_ci_provider` to `'github'` (a fixture, not a repeated patch), so its outcome
     does not depend on the ambient `.plan/marshal.json`. This covers `test_the_gate_fetches_the_surface_once_and_spawns_no_cli`, the required-reviewer
     read-seam tests built on `_verdict_through_the_read_seams`, the raising-read test, and `_lane_admits` in `test_finished_review_shape_table.py`.
   - Every test that sets the process default working directory restores the value it found: the two tests without `restore_default_cwd`
     (`test_the_gate_fetches_the_surface_once_and_spawns_no_cli`, the raising-read test) take the fixture.
   - The "spawns no CLI" half of the single-fetch pin trips for a read routed through `ci_base.run_cli` too: `run_cli` catches every `Exception`, so
     the pin raises something it does not catch (a `BaseException` subclass such as `pytest.fail`), or patches `run_cli` itself.
   - `_lane_admits` drops its dead `subprocess.run` and `toon_parser.parse_toon` stubs and its "two TRANSPORT seams" docstring; the section comment
     before `_QUOTED_MARKER_CONSTRUCTIONS` in `test_runbook_lane_review_gate.py` describes the one fetch the helper stubs.
   - The tests that asserted the removed `coverage_unavailable` reason and the removed guard are rewritten or deleted with deliverable 1, never left
     passing for an unrelated reason.

   *Done when:* these fail at `2bf7cd83d`: the review-gate and shape-table tests pass when the test's working directory is a temporary directory
   with no `.plan/marshal.json` above it (`resolve_ci_provider` walks up from the project directory the gate is handed, `'.'` in these tests; today
   those tests answer `undecidable_read` and fail); `ci_base.get_default_cwd()` is the same value
   before and after the whole review-gate test module; a second read routed through `run_cli` fails the single-fetch pin. These hold at `2bf7cd83d`:
   the quoted-marker shape table and its matched control keep their verdicts.

4. **The wording this change added or left against the documentation standard is current-state only.**
   - Skills: pm-documents:ref-documentation
   - Persona: documenter
   - Comments, docstrings and test docstrings state current behaviour and no change history ("now", "used to", "no longer", "was exempt", "Without
     this test", "Before this test"): `github_re_review.py` module docstring ("That skip is now VISIBLE"), the `review_coverage_names_commit`
     docstring paragraph added by #1988 in `_github_pr.py`, the docstring of `test_the_gate_fetches_the_surface_once_and_spawns_no_cli`, the docstring
     of `test_a_project_that_does_not_route_to_github_is_never_read`, and the new docstring in `test_finished_review_one_reader.py` near its line 221.
   - No behaviour changes and no assertion changes in this deliverable.

   *Done when:* holds at `2bf7cd83d`, as a documentation pin: each named docstring states the rule it pins without a comparison to an earlier
   behaviour, and the existing documentation pins in `test/plan-marshall/automatic-review/test_review_complete_after_handling_docs.py` keep passing.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- Fail closed: no change here may turn a read the gate stops on into one it admits. Every verdict a real read can produce at `2bf7cd83d` is the same
  after this plan; the only new verdict is `undecidable_read` where there was a traceback.
- One fetch per verdict stays: no deliverable adds a second read, a subprocess, or a second predicate at the lane's site.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so; a fixture never hands the lane a
  value its real read cannot give.
- The PR states whether an executor regeneration is owed (none if no verb or flag is added) and that a harness sync is owed for the edited bundle
  sources.
- Out of scope, recorded as such in the PR: the CAUTION-shape parser defect; the hex-word placeholders that still pass `review_coverage_names_commit`
  (`facade`, `dead`); `Path.resolve()` in `resolve_ci_provider` following symlinks; whether the dropped TOON round trip changed any body.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `cmd_review_gate` fetches once and hands the same `read` to `_review_gate_verdict`; `_display_read` flattens that snapshot — read at `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` § `_read_review_surfaces`, `_display_read`, `cmd_review_gate` (L2649-2680, L2894-2897 at `2bf7cd83d`; re-read)
- OBSERVED: `coverage_unavailable` is unreachable from the real read: `_review_gate_verdict` returns it only when `'complete' not in read` (L2772-2784), and a successful GitHub fetch always publishes `complete` (`github_ops.py` L984-994); a non-GitHub project stops earlier at `_read_review_surfaces` (L2653-2663) — re-read
- OBSERVED: `runbook-lane/SKILL.md` still says `ci pr comments` publishes `complete` and that a GitLab project answers `coverage_unavailable` — read at `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` L213 and L218-221 (re-read)
- OBSERVED: `_required_review_read_failure(read)` at L2856-2858 can never be non-None, because the failed, coverage-less and truncated reads already returned at L2765, L2772 and L2785; the helper has two matches in the tree, its definition and that call — re-read, and `architecture search --content` (inventory-scoped)
- OBSERVED: `coverage_unavailable` appears in five inventoried files: `runbook-lane/SKILL.md` (two), `runbook_lane.py` (one), `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` (one, L741) and two `manage-tasks` freshness scripts (`_freshness_crosscheck.py`, `_cmd_pre_commit_verify_freshness.py`) — `architecture search --content` (inventory-scoped; the `.claude/`, `.github/` and `.plan/` trees are not covered)
- HYPOTHESIS: the `manage-tasks` freshness scripts use `coverage_unavailable` as their own reason and do not read it from `review-gate` — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` and `_cmd_pre_commit_verify_freshness.py` (not read; verify-at-outline, D1)
- OBSERVED: `_display_read` and the `:2796` call run outside the `try` in `_read_review_surfaces`; `flatten_comment_bodies` calls `.get` and `{**comment}` on every entry before the dict filter at L2796; the real fetch builds only dicts, so a raise is not reachable today — read at `runbook_lane.py` L2670-2680, L2796 (re-read) and `github_ops.py` L984-994
- OBSERVED: `test_the_gate_fetches_the_surface_once_and_spawns_no_cli` and the raising-read test carry no `restore_default_cwd` fixture, though the real read sets the process default working directory; the raising-read test patches the fetch and so does not pin the import placement — read at `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` L954-978, L1322-1340 (re-read)
- OBSERVED: two tests in that module stub `resolve_ci_provider` (L997, L1012) and the ones above do not, so the latter depend on the ambient `.plan/marshal.json` routing to GitHub (it does in this repository today) — read at the same file (re-read of the stubs; the dependence is the leaf's reading)
- OBSERVED: the section comment at L1229-1233 still describes two transport seams, and `_lane_admits` keeps dead `subprocess.run` and `parse_toon` stubs and a "two TRANSPORT seams" docstring — read at `test_runbook_lane_review_gate.py` L1229-1233 and `test/plan-marshall/workflow-integration-github/test_finished_review_shape_table.py` L149-171 (re-read)
- HYPOTHESIS: `forbid_run` (a patch of `subprocess.run` that raises `AssertionError`) does not trip for a second read routed through `ci_base.run_cli`, because `run_cli` catches every `Exception` — confirm/refute at `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` § `run_cli` (leaf read; not re-read; verify-at-outline, D3)
- OBSERVED: wording against the standard left or added: `github_re_review.py` L121 ("That skip is now VISIBLE", re-read); `_github_pr.py` L595-597 ("Without this test ... was exempt", re-read in the diff); `test_runbook_lane_review_gate.py` L957-961 ("used to", "now", re-read) and L985-987 ("Without it"); `test_finished_review_one_reader.py` near L221 ("Before this test", re-read)
- Verify-first clause: before scoping D1, read the two `manage-tasks` freshness scripts and settle the hypothesis above; before scoping D3, run the single-fetch pin against a read routed through `run_cli` and state what it returns at `2bf7cd83d`, so the red run the Done-when asks for exists; a clause the run does not bear out is dropped and the PR says so.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_review_gate_verdict`, `_display_read`, `_required_review_read_failure` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the `review-gate` reason list and the coverage paragraph (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — the module docstring wording (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — the `review_coverage_names_commit` docstring wording (D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` — the read-seam tests, the fixtures, the removed reason's test, the docstrings (D1, D2, D3, D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_finished_review_shape_table.py` — `_lane_admits` and its provider stub (D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_finished_review_one_reader.py` — one docstring (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` and `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — read only; they move only if the hypothesis above is refuted (D1; verify-at-outline)

## Dependencies and Sequencing

- Depends on: PR #1988 (merged, `2bf7cd83d`); PLAN-LB-148 (shipped).
- Overlaps with: none declared by a running row at staging (PLAN-LB-150 is the apply-changes command, PLAN-LB-151 the handle-open verb); the `corpus cross-check` names the exact files and is re-read before the emit.
- Adjacent to: the review-body parser (`_SUMMARY_RE`, the section table, `_body_findings`) with its open CAUTION-shape defect, which this plan does not touch and which must be sequenced after it if staged; the finished-review predicate in `_github_pr.py` beyond the one docstring.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-152-review-gate-single-read-cleanup.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
