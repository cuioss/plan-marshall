# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression suite: a retrospective check must not re-derive an input it was handed.

Each check covered here was handed an availability signal by its own loader and
then inferred a different one from a proxy — an empty file list, an optimistic
default, a plan-level count that can never reach zero. The inferred answer and the
published field then disagreed inside a single fragment, so the output stated
something false about its own inputs two lines from the field contradicting it.

The three surfaces:

* ``check-manifest-consistency`` rule M4 — skipped on ``raw_files_total == 0``
  while the loader's ``evidence_available`` sat unused, emitting *"no diff data
  available"* for a diff that had been supplied and read.
* ``check-manifest-consistency.filter_bookkeeping`` — seeded ``diff_available``
  ``True`` (fail-OPEN) and relied on one caller to correct it, so a caller that
  forgot would grant every clean verdict on no evidence.
* ``analyze-logs`` per-task ``[ARTIFACT]`` emission — the ``N == 0`` case was
  deferred to a plan-level floor that counts ``[ARTIFACT]`` lines from every
  caller, including ``phase-1-init``'s unconditional one, so the total-absence
  case was guarded by nothing at all.

Every test here fails against the pre-fix code.
"""


from __future__ import annotations

import json
from pathlib import Path

from _analyze_logs_fixtures import SCRIPT_PATH as ANALYZE_LOGS_SCRIPT
from _footprint_oracle_classification_fixtures import (
    MANIFEST_SCRIPT,
    _check,
    _setup,
    _write_diff,
)
from _plan_retrospective_fixtures import setup_live_plan

from conftest import load_script_module, run_script

_cmc = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_input_availability'
)


_BRANCH_CLEANUP_MANIFEST = {
    'manifest_version': 1,
    'plan_id': 'oracle-plan',
    'phase_5': {'early_terminate': False, 'verification_steps': []},
    'phase_6': {'steps': ['branch-cleanup']},
}


# =============================================================================
# Rule M4 reads the loader's evidence flag, not an empty file list
# =============================================================================


class TestBranchCleanupRuleReadsTheEvidenceFlag:
    """A RESOLVED empty footprint is evaluated; an ABSENT observation is skipped.

    The two produce the same ``raw_files_total == 0``, which is exactly why the
    rule must not read that proxy. Both directions are pinned, because a fix that
    only stopped skipping would start fabricating verdicts on no evidence.
    """

    def test_supplied_empty_diff_is_evaluated_not_skipped(self, tmp_path, monkeypatch):
        """The positive case: a diff was observed and named nothing.

        Pre-fix this returned ``skip`` carrying "no diff data available" — a
        statement the run's own ``diff_available: True`` field contradicted.
        """
        plan_id, _ = _setup(tmp_path, monkeypatch, _BRANCH_CLEANUP_MANIFEST)
        diff = _write_diff(tmp_path, [])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is True
        assert int(data['diff']['files_total']) == 0

        row = _check(data['checks'], 'branch_cleanup_changes')
        assert row['status'] == 'fail', row
        assert 'no diff data available' not in row['message']
        # The message describes the OBSERVED diff, not a filtered-away one.
        assert 'observed diff is empty' in row['message']

        codes = [f['code'] for f in (data.get('findings') or [])]
        assert 'branch_cleanup_without_changes' in codes

    def test_no_diff_input_at_all_still_skips(self, tmp_path, monkeypatch):
        """The negative control, and the distinction the whole change turns on.

        With neither ``--diff-file`` nor ``--base-ref`` the loader observed
        nothing, so the rule has no evidence to verdict on and must still skip.
        A fix that evaluated here would fabricate a finding out of an absence.
        """
        plan_id, _ = _setup(tmp_path, monkeypatch, _BRANCH_CLEANUP_MANIFEST)

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is False
        row = _check(data['checks'], 'branch_cleanup_changes')
        assert row['status'] == 'skip', row
        assert 'no diff evidence was available' in row['message']

    def test_a_filtered_away_diff_names_the_reduction_not_the_diff(self, tmp_path, monkeypatch):
        """The third input state, kept distinguishable from the empty-diff one.

        A non-empty raw diff whose every entry the filter dropped must NOT say the
        diff was empty — the filter produced that emptiness, and the observation
        contradicts the claim.
        """
        plan_id, _ = _setup(tmp_path, monkeypatch, _BRANCH_CLEANUP_MANIFEST)
        diff = _write_diff(tmp_path, ['pyproject.toml'])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        row = _check(data['checks'], 'branch_cleanup_changes')
        assert row['status'] == 'fail', row
        assert 'observed diff is empty' not in row['message']
        assert 'classified as bookkeeping' in row['message']


# =============================================================================
# filter_bookkeeping seeds the availability flag FAIL-CLOSED
# =============================================================================


class TestReductionSeedIsFailClosed:
    """No code path may reach the verdict-withholding logic with the flag unset-but-true.

    ``filter_bookkeeping`` never observes a diff, so it cannot know one was
    available. Seeding ``True`` made a forgotten caller assignment publish
    "evidence existed" on no evidence; seeding ``False`` makes the same omission
    withhold every clean verdict instead.
    """

    def test_filter_bookkeeping_seeds_diff_available_false(self):
        _, _, reduction = _cmc.filter_bookkeeping([])
        assert reduction['diff_available'] is False

    def test_a_seed_only_reduction_withholds_a_clean_pass(self):
        """The pin: a reduction block WITHOUT the caller's assignment.

        Constructed through the real producer and handed straight to the real
        consumer, with the assignment ``cmd_run`` makes deliberately omitted —
        which is the only way to observe the seed's own direction. Under the
        fail-open seed the pass survived untouched.
        """
        _, _, reduction = _cmc.filter_bookkeeping([])
        clean_pass = [
            {
                'name': 'docs_only_diff',
                'status': 'pass',
                'message': 'all 0 non-bookkeeping diff entries are docs-shaped',
            }
        ]

        annotated = _cmc.apply_input_reduction(clean_pass, reduction)

        assert annotated[0]['status'] == _cmc.STATUS_INDETERMINATE
        assert 'no diff evidence was available' in annotated[0]['message']

    def test_the_caller_assignment_restores_the_measured_verdict(self):
        """The matched control: with evidence recorded, the pass stands.

        Without this the test above would also pass against a consumer that
        withheld unconditionally, which would be a different defect.
        """
        _, _, reduction = _cmc.filter_bookkeeping([])
        reduction['diff_available'] = True
        clean_pass = [
            {
                'name': 'docs_only_diff',
                'status': 'pass',
                'message': 'all 0 non-bookkeeping diff entries are docs-shaped',
            }
        ]

        annotated = _cmc.apply_input_reduction(clean_pass, reduction)

        assert annotated[0]['status'] == 'pass'


# =============================================================================
# Per-task [ARTIFACT] emission — the N == 0 case is graded, not deferred
# =============================================================================


def _stage_emission_plan(
    tmp_path,
    monkeypatch,
    *,
    plan_id: str,
    done_tasks: list[int],
    artifact_task_nums: list[int],
    footprint: list[str] | None,
) -> tuple[str, Path]:
    """Stage a live plan with an exact completed-task set, artifact set and footprint.

    ``footprint=None`` writes no ``realized_footprint`` key at all, which is the
    unresolvable state; a list (possibly empty) is a RESOLVED footprint.

    Every staged ``work.log`` opens with a ``phase-1-init`` ``[ARTIFACT]`` line.
    That is not decoration — it is the unconditional emission that makes the
    plan-level ``artifact_entries == 0`` floor unreachable, so its presence is
    what proves the per-task rule is the only detector that can fire.
    """
    plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id=plan_id)

    tasks_dir = plan_dir / 'tasks'
    for existing in tasks_dir.glob('TASK-*.json'):
        existing.unlink()
    for num in done_tasks:
        (tasks_dir / f'TASK-{num:03d}.json').write_text(
            json.dumps({'number': num, 'deliverable': 1, 'status': 'done'}), encoding='utf-8'
        )

    lines = [
        '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] [ARTIFACT] '
        '(plan-marshall:phase-1-init) Wrote request.md'
    ]
    for num in artifact_task_nums:
        lines.append(
            f'[2026-04-17T10:0{num}:00Z] [INFO] [bbbbbb] [ARTIFACT] '
            f'(plan-marshall:phase-5-execute:{num}) Wrote src/f{num}.py'
        )
    (plan_dir / 'logs' / 'work.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    refs: dict = {'base_branch': 'main'}
    if footprint is not None:
        refs['realized_footprint'] = footprint
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')

    return plan_id, plan_dir


def _emission_findings(data: dict) -> list[str]:
    return [
        f.get('message', '')
        for f in (data.get('findings') or [])
        if 'ARTIFACT_EMISSION' in f.get('message', '')
    ]


class TestTotalAbsenceOfPerTaskEmissionIsGraded:
    """``N == 0`` is the case the old ``0 < N < M`` guard left to a dead floor."""

    def test_zero_of_many_with_a_non_empty_footprint_is_a_finding(self, tmp_path, monkeypatch):
        """The criterion case, staged exactly.

        M >= 1 completed tasks, zero per-task ``[ARTIFACT]`` lines, a non-empty
        footprint, and at least one non-task ``[ARTIFACT]`` line — which satisfies
        the plan-level floor and is precisely why that floor detects nothing here.
        """
        plan_id, _ = _stage_emission_plan(
            tmp_path,
            monkeypatch,
            plan_id='retro-emission-absent',
            done_tasks=[1, 2, 3],
            artifact_task_nums=[],
            footprint=['src/changed.py'],
        )

        result = run_script(ANALYZE_LOGS_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        emission = data['artifact_emission']
        assert int(emission['completed_tasks']) == 3
        assert int(emission['tasks_with_artifacts']) == 0
        # The plan-level floor is SATISFIED by the phase-1-init line alone, so it
        # cannot be what fires — the whole point of grading N == 0 here.
        assert int(data['counts']['artifact_entries']) >= 1

        messages = _emission_findings(data)
        assert any('ARTIFACT_EMISSION_ABSENT' in m for m in messages), messages
        assert not any('ARTIFACT_EMISSION_PARTIAL' in m for m in messages), messages

    def test_a_plan_with_no_completed_tasks_reports_nothing(self, tmp_path, monkeypatch):
        """The negative control named by the success criterion.

        ``M == 0`` means there was no population to emit for. The widened guard is
        ``N < M``, so an empty population cannot satisfy it and no finding is owed.
        """
        plan_id, _ = _stage_emission_plan(
            tmp_path,
            monkeypatch,
            plan_id='retro-emission-no-tasks',
            done_tasks=[],
            artifact_task_nums=[],
            footprint=['src/changed.py'],
        )

        result = run_script(ANALYZE_LOGS_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert int(data['artifact_emission']['completed_tasks']) == 0
        assert _emission_findings(data) == []

    def test_an_empty_resolved_footprint_reports_nothing(self, tmp_path, monkeypatch):
        """The second negative control: the two causes are indistinguishable here.

        With no file changed, "this plan uses no per-task emission" and "emission
        was bypassed" produce identical observations, so the honest output is the
        published ``0 of M`` population and no finding. This is also what keeps
        archived plans predating per-task emission from suddenly reporting one.
        """
        plan_id, _ = _stage_emission_plan(
            tmp_path,
            monkeypatch,
            plan_id='retro-emission-empty-footprint',
            done_tasks=[1, 2],
            artifact_task_nums=[],
            footprint=[],
        )

        result = run_script(ANALYZE_LOGS_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert int(data['artifact_emission']['completed_tasks']) == 2
        assert int(data['artifact_emission']['tasks_with_artifacts']) == 0
        assert _emission_findings(data) == []

    def test_partial_emission_still_reports_the_partial_finding(self, tmp_path, monkeypatch):
        """The widened guard must not swallow the interior case it replaced."""
        plan_id, _ = _stage_emission_plan(
            tmp_path,
            monkeypatch,
            plan_id='retro-emission-partial-guard',
            done_tasks=[1, 2, 3],
            artifact_task_nums=[1],
            footprint=['src/changed.py'],
        )

        result = run_script(ANALYZE_LOGS_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        messages = _emission_findings(data)
        assert any('ARTIFACT_EMISSION_PARTIAL' in m for m in messages), messages
        assert not any('ARTIFACT_EMISSION_ABSENT' in m for m in messages), messages
