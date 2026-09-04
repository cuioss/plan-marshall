# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-artifact-consistency.py``.

Scope: what an unresolvable footprint makes of each verdict — inconclusive rather
than a zero percent or a set mismatch — and that the summary reconciles across pass,
warn, inconclusive and failing plans alike.
"""


from __future__ import annotations

import json

from _check_artifact_consistency_fixtures import (
    SCRIPT_PATH,
    _check_by_name,
    _check_mod,
    _fr_mod,
    _git,
    _init_repo,
    _run_archived,
    _setup_archived_plan_with_references,
)
from _plan_retrospective_fixtures import (
    setup_broken_plan,
    setup_live_plan,
)

from conftest import run_script


class TestUnresolvableFootprintIsUnmeasurable:
    """An unresolvable footprint yields ``inconclusive`` from BOTH peers.

    The pair ``affected_files_recall`` / ``affected_files_exact_match`` consumes
    one resolver, so hardening one alone leaves the other reporting confidently
    from the same unmeasured input. Each peer is asserted separately, and the
    resolved-but-empty control below proves the sentinel is not satisfied by
    making every footprint unmeasurable.
    """

    def test_recall_reports_inconclusive_not_zero_percent(self, tmp_path):
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-unresolvable-recall'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'inconclusive'
        assert 'could not be resolved' in recall['message']

        details = data['details']['affected_files_recall']
        assert details['footprint_resolved'] is False
        assert 'recall_pct' not in details, (
            'An unresolved footprint must yield NO percentage — a reported 0% is '
            'the confident-zero defect this check exists to remove.'
        )

    def test_exact_match_peer_reports_inconclusive_not_set_mismatch(self, tmp_path):
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-unresolvable-exact'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        exact = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'inconclusive', (
            'The exact-match peer consumes the same resolver; a confident '
            '"Set mismatch" here would leave the pair half-hardened.'
        )
        assert data['affected_files_exact_match']['status'] == 'inconclusive'
        assert data['affected_files_exact_match']['outline_only'] == []
        assert data['affected_files_exact_match']['references_only'] == []

    def test_both_inconclusive_verdicts_reach_findings(self, tmp_path):
        """Neither verdict may be dropped into silence on the way to the report."""
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-unresolvable-findings'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        unresolvable_findings = [
            f
            for f in data['findings']
            if f.get('severity') == 'warning' and 'could not be resolved' in f.get('message', '')
        ]
        assert len(unresolvable_findings) == 2, (
            f'Expected one warning finding per affected_files_* peer, got {data["findings"]}'
        )

    def test_resolved_but_empty_footprint_still_yields_a_measured_verdict(self, tmp_path):
        """Negative control: ``modified_files: []`` RESOLVED, so both peers measure.

        Without this control the deliverable could be satisfied by reporting
        everything as unmeasurable. A present-but-empty key is a real answer:
        recall measures 0% and fails, and the exact-match peer reports genuine
        one-sided drift.
        """
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'modified_files': [], 'domains': []}, name='archived-resolved-empty'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        details = data['details']['affected_files_recall']
        assert details['footprint_resolved'] is True
        assert float(details['recall_pct']) == 0.0

        exact = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'warn'


class TestSummaryCountsEveryEmittedStatus:
    """``summary`` buckets reconcile against ``len(checks)`` — no verdict vanishes.

    A status that lands in no bucket reads to a summary consumer as a check that
    does not exist, which is the same unmeasurable-rendered-as-absent shape the
    ``inconclusive`` footprint verdict removes. The reconciliation is derived
    from the emitted ``checks``, never from a hardcoded status list, so a status
    introduced later is covered without editing this test.
    """

    def _assert_reconciles(self, data) -> None:
        summary = data['summary']
        assert sum(int(v) for v in summary.values()) == len(data['checks']), (
            f'Summary buckets {summary} do not reconcile against '
            f'{len(data["checks"])} checks: '
            f'{[(c["name"], c["status"]) for c in data["checks"]]}'
        )

    def test_reconciles_when_every_check_passes(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        self._assert_reconciles(result.toon())

    def test_reconciles_when_inconclusive_verdicts_are_emitted(self, tmp_path):
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-summary-inconclusive'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        assert int(data['summary']['inconclusive']) == 2
        self._assert_reconciles(data)

    def test_reconciles_when_a_warn_verdict_is_emitted(self, tmp_path):
        """``warn`` had no bucket either — the repair covers the whole map."""
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'modified_files': [], 'domains': []}, name='archived-summary-warn'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        assert int(data['summary']['warn']) == 1
        self._assert_reconciles(data)

    def test_reconciles_when_a_broken_plan_fails_checks(self, tmp_path, monkeypatch):
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        self._assert_reconciles(result.toon())


class TestResolveFootprintTiers:
    """``_resolve_footprint`` delegates to the shared whole-chain resolver (live diff →
    realized-footprint capture → merge-commit → legacy key → unresolvable). These tests
    exercise the tier-1/legacy/unresolvable endpoints.

    Tier 1 reaches the worktree through the ONE plan-context resolver
    (``_references_core.resolve_live_worktree``), keyed on ``plan_id``. It no
    longer re-reads ``status.metadata.worktree_path`` out of the plan's own
    status file, so these tests stub the resolver rather than writing a
    ``status.json`` the function does not consult.

    Tier 3 is UNRESOLVABLE, not empty: "resolved to a genuinely empty set" and
    "could not be resolved at all" are different answers, and the resolution
    state is read through :func:`footprint_resolved` rather than by testing
    emptiness. The resolved-empty control below is the negative half of that
    pair — without it, a sentinel that made everything unmeasurable would still
    satisfy the unresolvable assertions.
    """

    def test_tier1_live_diff_when_worktree_resolves(self, tmp_path, monkeypatch):
        """A resolvable worktree yields the live ``{base}...HEAD`` ∪ porcelain set."""
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

        monkeypatch.setattr(_fr_mod, 'resolve_live_worktree', _resolve)

        footprint = _check_mod._resolve_footprint(plan_dir, 'demo-plan')
        assert 'committed.py' in footprint
        assert 'uncommitted.py' in footprint
        assert 'base.txt' not in footprint
        assert asked == ['demo-plan'], (
            'tier 1 must reach the worktree through the resolver, keyed on plan_id'
        )

    def test_tier1_skipped_in_archived_mode(self, tmp_path, monkeypatch):
        """``plan_id=None`` skips tier 1 — an archived worktree no longer exists."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )

        asked = []

        def _resolve(plan_id):
            asked.append(plan_id)
            return None

        monkeypatch.setattr(_fr_mod, 'resolve_live_worktree', _resolve)

        assert _check_mod._resolve_footprint(plan_dir, None) == {'legacy/a.py'}
        assert asked == [None]

    def test_status_metadata_worktree_path_is_no_longer_consulted(self, tmp_path):
        """A recorded ``worktree_path`` alone must NOT produce a live footprint.

        This pins the removal of the hand-rolled re-derivation: before the
        migration a ``status.json`` carrying a resolvable ``worktree_path`` was
        enough to reach tier 1. Now only the resolver can.
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

        assert _check_mod._resolve_footprint(plan_dir, None) == {'legacy/a.py'}

    def test_tier2_legacy_key_when_no_worktree(self, tmp_path):
        """No worktree → fall back to the legacy ``modified_files`` key."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py', 'legacy/b.py']})
        )
        # No status.json at all → no worktree path resolvable.

        footprint = _check_mod._resolve_footprint(plan_dir)
        assert footprint == {'legacy/a.py', 'legacy/b.py'}

    def test_tier3_unresolvable_when_neither_resolves(self, tmp_path):
        """No worktree and no legacy key → UNRESOLVABLE, never an empty set.

        This is the confident-zero source: collapsing "could not resolve" into
        ``set()`` is what let a plan with a 21/21 exact footprint score a
        confident ``Recall 0%`` once ``branch-cleanup`` had deleted the
        worktree the resolver measures.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'domains': []}))

        footprint = _check_mod._resolve_footprint(plan_dir)
        assert footprint is _fr_mod.FOOTPRINT_UNRESOLVED
        assert not _check_mod.footprint_resolved(footprint)

    def test_present_but_empty_legacy_key_is_a_resolved_empty_footprint(self, tmp_path):
        """Negative control: ``modified_files: []`` RESOLVED — to an empty set.

        The positive sibling of the tier-3 assertion above. A present-but-empty
        key is a measured answer ("the plan touched no files"), so it must stay
        distinguishable from the absent key, and ``footprint_resolved`` — not
        emptiness — is what tells them apart.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'modified_files': []}))

        footprint = _check_mod._resolve_footprint(plan_dir)
        assert footprint == set()
        assert _check_mod.footprint_resolved(footprint)

    def test_tier1_diff_failure_reports_unresolvable_without_legacy_fallback(
        self, tmp_path, outside_repo_dir, monkeypatch
    ):
        """A resolved directory that is not a git tree reports UNRESOLVABLE.

        The worktree resolved but the diff did not, so the legacy key would
        answer a different question while presenting as the same measurement.
        The legacy key is deliberately populated here: the assertion is that it
        is NOT consulted, which is only checkable when it holds a value that
        would have been returned under the old fall-through.
        """
        # ``plain`` must be OUTSIDE the repo: pytest's tmp_path now roots under
        # the repo-local --basetemp, where it IS a git tree and the tier-1 live
        # footprint would resolve instead of failing.
        plain = outside_repo_dir / 'plain'
        plain.mkdir()

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )
        monkeypatch.setattr(_fr_mod, 'resolve_live_worktree', lambda plan_id: plain)

        footprint = _check_mod._resolve_footprint(plan_dir, 'demo-plan')
        assert footprint is _fr_mod.FOOTPRINT_UNRESOLVED
        assert not _check_mod.footprint_resolved(footprint)
