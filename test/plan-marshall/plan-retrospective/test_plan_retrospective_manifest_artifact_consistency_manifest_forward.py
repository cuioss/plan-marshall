# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manifest-aware forward in ``check-artifact-consistency.py``.

Two halves, and the second is the one that matters. The producer's half proves the
flag is SET; the receiver's half proves the forwarded finding is RECEIVED. A forward
asserted only at its sending end is exactly how this contract broke: the downgrade
traded a real ``warn`` for a promise that another aspect would report the drift, and
for as long as no rule read the flag the finding was DROPPED on every
manifest-bearing plan rather than re-routed.
"""

from __future__ import annotations

from _plan_retrospective_fixtures import build_happy_plan_dir
from _plan_retrospective_manifest_fixtures import (
    ARTIFACT_SCRIPT,
    MANIFEST_SCRIPT,
    _check_by_name,
    _finding_by_code,
    _manifest_default,
    _write_manifest,
)

from conftest import run_script

# =============================================================================
# Forward in check-artifact-consistency
# =============================================================================


class TestArtifactConsistencyManifestForward:
    """When execution.toon exists, the legacy exact_match warn is downgraded
    to info and forwarded to the manifest aspect."""

    def test_warn_downgraded_when_manifest_present(self, tmp_path, monkeypatch):
        # Build a happy plan whose outline declares foo/bar/baz but whose
        # references.json only has foo, producing an exact_match warn.
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / 'forward-plan'
        build_happy_plan_dir(plan_dir)
        # Trim references.json so outline > references → warn.
        import json as _json  # local alias to avoid module-level pollution

        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )
        _write_manifest(plan_dir, _manifest_default())
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(
            ARTIFACT_SCRIPT,
            'run',
            '--plan-id',
            'forward-plan',
            '--mode',
            'live',
        )
        assert result.success, result.stderr
        data = result.toon()
        exact = data['affected_files_exact_match']
        # Top-level payload retains the original warn status as ground truth
        # for tooling, but adds the forwarding flag.
        assert exact['status'] == 'warn'
        assert exact['manifest_present'] is True
        assert exact['forwarded_to_manifest'] is True

        # The check entry visible to the report renderer is downgraded to info.
        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'info'
        assert 'deferred to manifest aspect' in check['message']

        # The corresponding finding is severity=info (not warning) so the
        # report renderer routes the reader to the manifest section instead
        # of double-counting the drift.
        forwarded = [f for f in data['findings'] if 'deferred to manifest aspect' in f['message']]
        assert len(forwarded) == 1
        assert forwarded[0]['severity'] == 'info'

    def test_warn_retained_when_manifest_absent(self, tmp_path, monkeypatch):
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / 'legacy-warn'
        build_happy_plan_dir(plan_dir)
        import json as _json

        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )
        # No execution.toon written.
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(
            ARTIFACT_SCRIPT,
            'run',
            '--plan-id',
            'legacy-warn',
            '--mode',
            'live',
        )
        assert result.success, result.stderr
        data = result.toon()
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['manifest_present'] is False
        assert exact['forwarded_to_manifest'] is False

        # Existing behavior preserved: the check entry is warn and the
        # finding severity stays warning.
        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'warn'
        warning_findings = [f for f in data['findings'] if f.get('severity') == 'warning']
        # At least the exact_match warning is present.
        assert any('mismatch' in f['message'].lower() for f in warning_findings)


# =============================================================================
# The RECEIVING half — the forward actually arrives
# =============================================================================


class TestForwardedFindingIsReceived:
    """End-to-end: producer downgrades, receiver picks the drift up.

    ⛔ Asserting the producer's ``forwarded_to_manifest`` flag proves only that a
    handoff was ATTEMPTED. These tests run BOTH aspects in sequence — the real
    producer's emitted fragment is what the real receiver reads — so they fail if
    the receiving rule is removed, renamed, or stops reading the fragment, which
    the producer-side assertions above cannot detect.
    """

    def _stage(self, tmp_path, monkeypatch, *, with_manifest: bool):
        import json as _json

        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / 'forward-e2e'
        build_happy_plan_dir(plan_dir)
        # outline declares more than references carries → exact_match drift.
        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )
        if with_manifest:
            _write_manifest(plan_dir, _manifest_default())
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        return 'forward-e2e', plan_dir

    def _run_producer_and_persist(self, plan_id: str, plan_dir):
        """Run the producer and persist its fragment where the receiver reads it."""
        from toon_parser import serialize_toon  # local import — script-test PYTHONPATH

        result = run_script(ARTIFACT_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        payload = result.toon()

        work = plan_dir / 'work'
        work.mkdir(parents=True, exist_ok=True)
        (work / 'fragment-artifact-consistency.toon').write_text(serialize_toon(payload) + '\n', encoding='utf-8')
        return payload

    def test_the_downgraded_drift_reaches_the_manifest_aspect(self, tmp_path, monkeypatch):
        plan_id, plan_dir = self._stage(tmp_path, monkeypatch, with_manifest=True)
        produced = self._run_producer_and_persist(plan_id, plan_dir)

        # Precondition: the producer really did downgrade and forward, and the
        # drift it forwarded is non-empty — otherwise the receiver assertion
        # below would pass over an empty comparison and prove nothing.
        assert produced['affected_files_exact_match']['forwarded_to_manifest'] is True
        assert produced['affected_files_exact_match']['outline_only']

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        received = result.toon()

        block = received['declared_vs_realized']
        assert block['received'] is True
        assert block['forwarded_to_manifest'] is True
        assert int(block['outline_only_count']) == len(produced['affected_files_exact_match']['outline_only'])

        check = _check_by_name(received['checks'], 'declared_vs_realized_set')
        assert check is not None
        assert check['status'] == 'fail', check

        finding = _finding_by_code(received['findings'], 'declared_vs_realized_set_mismatch')
        assert finding is not None, (
            'the producer downgraded its own warn on the promise that this aspect '
            'would report the drift — a receiver that raises nothing turns the '
            'downgrade into a silent drop'
        )
        assert finding['severity'] == 'warning'

    def test_no_fragment_means_the_receiver_reports_an_unread_input(self, tmp_path, monkeypatch):
        """The matched control: a receiver that always failed would pass the test above.

        Same plan, same manifest, but the producer's fragment is never persisted.
        The receiver must then report an UNREAD input rather than a mismatch it
        never received — and must publish no counts.
        """
        plan_id, _plan_dir = self._stage(tmp_path, monkeypatch, with_manifest=True)

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        received = result.toon()

        assert received['declared_vs_realized']['received'] is False
        check = _check_by_name(received['checks'], 'declared_vs_realized_set')
        assert check is not None
        assert check['status'] == 'inconclusive', check
        assert _finding_by_code(received['findings'], 'declared_vs_realized_set_mismatch') is None
