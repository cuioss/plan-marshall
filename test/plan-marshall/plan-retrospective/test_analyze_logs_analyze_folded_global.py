# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``.

Scope: the signals read from folded global logs — line counts, error and slow-call
flags, the fixture-leak signature — and the tier-1 live diff, which runs only when a
worktree resolves.
"""


from __future__ import annotations

import json

from _analyze_logs_fixtures import SCRIPT_PATH, _analyze_logs, _git, _init_repo, _line, _write_folded_log
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402


class TestAnalyzeFoldedGlobalLogs:
    def test_no_logs_dir_yields_all_zero_signals(self, tmp_path):
        # logs_dir does not exist
        logs_dir = tmp_path / 'logs'

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert result['logs_present'] is False
        assert result['folded_log_files'] == 0
        assert result['total_lines'] == 0
        assert result['error_count'] == 0
        assert result['slow_call_count'] == 0
        assert result['fixture_leak_count'] == 0

    def test_only_canonical_logs_no_folded_globals_yields_no_signals(self, tmp_path):
        # canonical per-plan logs only; no date-stamped folded copies
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work.log',
            [_line('2026-06-01T10:00:00Z', 'ERROR', '[STATUS] (x) boom')],
        )

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # work.log is NOT a folded ``work-*.log`` glob match
        assert result['logs_present'] is False
        assert result['folded_log_files'] == 0
        assert result['error_count'] == 0

    def test_well_formed_lines_counted_and_error_flagged(self, tmp_path):
        # one INFO + one ERROR line in a folded global log
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                _line('2026-06-01T10:00:01Z', 'ERROR', '[STATUS] (x) off'),
            ],
        )

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # both parsed; the ERROR line surfaces in error_count
        assert result['logs_present'] is True
        assert result['folded_log_files'] == 1
        assert result['total_lines'] == 2
        assert result['error_count'] == 1

    def test_info_line_with_failure_marker_flagged(self, tmp_path):
        # INFO level but the body carries a fail marker (status: error)
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:x:x run -> status: error exit_code: 1')],
        )

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert result['error_count'] == 1

    def test_slow_call_flagged_at_ceiling(self, tmp_path):
        # a call at the slow ceiling (30.0s) and a fast call
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (30.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:b:b run (1.0s)'),
            ],
        )

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # only the >=ceiling call is slow
        assert result['slow_call_count'] == 1

    def test_fixture_leak_signature_flagged(self, tmp_path):
        # a synthetic test-fixture id leaked into the folded log
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'decision-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '(x) plan orphan-md-xyz123 resolved')],
        )

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert result['fixture_leak_count'] == 1
        assert 'orphan-md-xyz123' in result['fixture_leak_signatures']

    def test_malformed_lines_skipped(self, tmp_path):
        # only the first line matches the bracketed grammar
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                'no bracketed prefix here',
            ],
        )

        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # only the well-formed line counted
        assert result['total_lines'] == 1

    def test_cmd_run_surfaces_global_log_signals_and_fixture_leak_finding(self, tmp_path, monkeypatch):
        # a live plan whose folded-in global log carries a fixture leak
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-folded-leak')
        _write_folded_log(
            plan_dir / 'logs',
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] fake-test-bundle leaked')],
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')

        # the global_log_signals key is present and a leak finding fired
        assert result.success, result.stderr
        data = result.toon()
        assert 'global_log_signals' in data
        signals = data['global_log_signals']
        assert int(signals['fixture_leak_count']) == 1


class TestResolveFootprintTiers:
    """``resolve_footprint`` resolves live diff → realized-footprint capture →
    merge-commit → legacy key → empty. These tests exercise the tier-1/legacy/empty
    endpoints (the capture and merge-commit tiers reuse the shared helpers covered in
    test_footprint_resolver.py).

    Tier 1 reaches the worktree through the ONE plan-context resolver
    (``_references_core.resolve_live_worktree``), keyed on ``plan_id``. It no
    longer re-reads ``status.metadata.worktree_path`` out of the plan's own
    status file, so these tests stub the resolver rather than writing a
    ``status.json`` the function does not consult.
    """

    def test_tier1_live_diff_when_worktree_resolves(self, tmp_path, monkeypatch):
        """A resolvable git worktree yields the live ``{base}...HEAD`` ∪ porcelain set."""
        repo = tmp_path / 'wt'
        _init_repo(repo)
        (repo / 'base.txt').write_text('base\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'base')
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'committed.py').write_text('print("x")\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'plan change')
        (repo / 'uncommitted.py').write_text('print("y")\n')

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}))

        asked = []

        def _resolve(plan_id):
            asked.append(plan_id)
            return repo

        monkeypatch.setattr(_analyze_logs, 'resolve_live_worktree', _resolve)

        footprint = _analyze_logs.resolve_footprint(plan_dir, 'demo-plan')
        assert 'committed.py' in footprint
        assert 'uncommitted.py' in footprint
        assert 'base.txt' not in footprint
        assert asked == ['demo-plan'], (
            'tier 1 must reach the worktree through the resolver, keyed on plan_id'
        )

    def test_tier1_skipped_in_archived_mode(self, tmp_path, monkeypatch):
        """``plan_id=None`` skips tier 1 — an archived worktree no longer exists.

        The resolver is still called (it owns the ``None`` short-circuit), but it
        answers ``None``, so resolution falls through to the legacy key.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )

        asked = []

        def _resolve(plan_id):
            asked.append(plan_id)
            return None

        monkeypatch.setattr(_analyze_logs, 'resolve_live_worktree', _resolve)

        assert _analyze_logs.resolve_footprint(plan_dir, None) == ['legacy/a.py']
        assert asked == [None]

    def test_status_metadata_worktree_path_is_no_longer_consulted(self, tmp_path):
        """A recorded ``worktree_path`` alone must NOT produce a live footprint.

        This pins the removal of the hand-rolled re-derivation: before the
        migration a ``status.json`` carrying a resolvable ``worktree_path`` was
        enough to reach tier 1. Now only the resolver can, so the same status
        file falls through to the legacy key.
        """
        repo = tmp_path / 'wt'
        _init_repo(repo)
        (repo / 'base.txt').write_text('base\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'base')

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'base_branch': 'main', 'modified_files': ['legacy/a.py']})
        )
        (plan_dir / 'status.json').write_text(
            json.dumps({'metadata': {'worktree_path': str(repo)}})
        )

        assert _analyze_logs.resolve_footprint(plan_dir, None) == ['legacy/a.py']

    def test_tier2_legacy_key_when_no_worktree(self, tmp_path):
        """No worktree → fall back to the legacy ``modified_files`` key."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py', 'legacy/b.py']})
        )

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert sorted(footprint) == ['legacy/a.py', 'legacy/b.py']

    def test_unresolvable_when_no_tier_answers(self, tmp_path):
        """No worktree and no footprint key at all → ``None``, not an empty list.

        The empty list this used to return is a MEASURED answer ("the plan
        touched nothing"), and returning it here silently disabled the
        ARTIFACT-coverage floor that reads this footprint.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'domains': []}))

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert footprint is None

    def test_present_but_empty_key_is_a_resolved_empty_footprint(self, tmp_path):
        """A present, empty ``modified_files`` resolves to ``[]`` — measured, not unknown.

        The peer direction of the test above: emptiness that was actually
        observed must stay distinguishable from emptiness nobody observed.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'modified_files': []}))

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert footprint == []

    def test_tier2_fallback_when_worktree_not_a_git_dir(
        self, tmp_path, outside_repo_dir, monkeypatch
    ):
        """A resolved directory that is not a git tree falls through to the legacy key."""
        # ``plain`` must be OUTSIDE the repo: pytest's tmp_path now roots under
        # the repo-local --basetemp, where it IS a git tree and the tier-1 live
        # footprint would resolve instead of falling through to the legacy key.
        plain = outside_repo_dir / 'plain'
        plain.mkdir()

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )
        monkeypatch.setattr(_analyze_logs, 'resolve_live_worktree', lambda plan_id: plain)

        footprint = _analyze_logs.resolve_footprint(plan_dir, 'demo-plan')
        assert footprint == ['legacy/a.py']
