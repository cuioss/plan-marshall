# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks.

Its sections, in order:

* D5a — the project-local production tree survives the filter
* D5b — a reduced input set reports the reduction
"""


from __future__ import annotations

from _footprint_oracle_classification_fixtures import (
    MANIFEST_SCRIPT,
    PROJECT_LOCAL_PRODUCTION,
    ROUTING_SCRIPT,
    _check,
    _setup,
    _write_diff,
)

from conftest import run_script

# =============================================================================
# D5a — the project-local production tree survives the filter
# =============================================================================


class TestProjectLocalTreeSurvivesFilter:
    """``build.map`` routes the project-local skill tree production, so it is kept."""

    def test_multi_file_project_local_footprint_is_not_filtered(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        diff = _write_diff(tmp_path, PROJECT_LOCAL_PRODUCTION)

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        # Every supplied path is production per the oracle — none may be dropped.
        assert data['diff']['files_total'] == len(PROJECT_LOCAL_PRODUCTION)
        assert data['diff']['files_filtered'] == 0
        assert data['diff']['files_kept'] == len(PROJECT_LOCAL_PRODUCTION)

    def test_runtime_state_directory_is_still_bookkeeping(self, tmp_path, monkeypatch):
        """``.plan/`` stays bookkeeping — it appears in no build map."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(
            tmp_path,
            ['.plan/plans/oracle-plan/status.json', '.claude/skills/sync-plugin-cache/scripts/sync.py'],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['diff']['files_filtered'] == 1
        assert data['diff']['files_kept'] == 1

    def test_routing_check_sees_project_local_production(self, tmp_path, monkeypatch):
        """The SECOND site: ``footprint_has_production`` must see the same tree.

        A ``no_code_delta`` prune of ``finalize-step-simplify`` is a mis-prune when
        the realized footprint touched production code. Pre-fix the private prefix
        tuple hid the project-local tree, so the mis-prune reported ``pass``.
        """
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                # Both prunable steps absent → their predicates are re-evaluated.
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        # A readable decision log naming no removal mechanism: the predicate runs.
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        diff = _write_diff(tmp_path, PROJECT_LOCAL_PRODUCTION)

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        simplify = [c for c in data['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify']
        assert simplify, data['mis_prune_checks']
        assert simplify[0]['status'] == 'fail', simplify[0]


    def test_unclassifiable_path_counts_as_production_for_the_mis_prune(self, tmp_path, monkeypatch):
        """Fail-closed: a path no route covers must not exonerate a ``no_code_delta`` prune.

        The oracle is unavailable here (no ``build.map``), so every path is
        unclassified. Answering "not production" would turn an unknown into an
        exoneration and report the mis-prune as a clean ``pass``.
        """
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        (tmp_path / 'base' / 'marshal.json').unlink()
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        diff = _write_diff(tmp_path, ['some/unrouted/module.rb'])

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'fail', simplify[0]

    def test_documentation_alone_does_not_count_as_production(self, tmp_path, monkeypatch):
        """The negative control — a docs-only footprint leaves the prune justified."""
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        diff = _write_diff(tmp_path, ['doc/developer/build.adoc', '.plan/plans/oracle-plan/status.json'])

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'pass', simplify[0]


# =============================================================================
# D5b — a reduced input set reports the reduction
# =============================================================================


class TestReducedInputSetReportsReduction:
    """A rule that saw only a fraction of the supplied footprint must say so."""

    def test_majority_filtered_footprint_never_yields_a_bare_pass(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                # M1 applies: empty verification_steps, not early-terminate.
                'phase_5': {'early_terminate': False, 'verification_steps': []},
                'phase_6': {'steps': ['push']},
            },
        )
        # Five of six paths are runtime-state bookkeeping; the survivor is a doc,
        # so M1 would otherwise emit a clean pass over one sixth of the input.
        diff = _write_diff(
            tmp_path,
            [
                '.plan/plans/oracle-plan/status.json',
                '.plan/plans/oracle-plan/tasks/TASK-001.json',
                '.plan/plans/oracle-plan/logs/decision.log',
                '.plan/plans/oracle-plan/execution.toon',
                '.plan/marshal.json',
                'doc/developer/build.adoc',
            ],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        docs_only = _check(data['checks'], 'docs_only_diff')
        assert docs_only['status'] == 'indeterminate', docs_only
        assert '5' in docs_only['message'] and '6' in docs_only['message'], docs_only['message']
        assert data['summary'].get('indeterminate') == 1, data['summary']

    def test_unreduced_footprint_still_passes_cleanly(self, tmp_path, monkeypatch):
        """The negative control — no reduction, so the ordinary pass survives."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': []},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(tmp_path, ['doc/developer/build.adoc', 'doc/developer/marketplace-build.adoc'])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert _check(data['checks'], 'docs_only_diff')['status'] == 'pass'
        assert data['summary'].get('indeterminate') == 0, data['summary']
