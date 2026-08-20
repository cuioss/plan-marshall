# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``compile-report.py``."""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from _compile_report_behavior_fixtures import _cr


class TestSkippedFragmentPartitionCharacterization:
    """CHARACTERIZATION — pins SHIPPED behaviour. NOT a regression proof.

    These assertions pass against the pre-change tree, so they cannot witness
    anything this plan fixed. They are recorded (rather than dropped) because
    they pin a boundary the partition's calibration turns on, and because the
    second one documents an anomaly this plan is explicitly scoped OUT of
    fixing: a ``status: skipped`` fragment that NAMES its skip reason is
    classified as a DROP, and a drop raises the compiled run's status to
    ``warning``. Nothing was lost — the aspect declared it had nothing to say —
    so the loud half of the partition fires on a benign outcome.

    ``skip_reason`` is a non-empty, non-envelope value, so
    ``_fragment_has_payload`` reports payload for it; a bare skipped fragment
    with no such field is correctly a benign omission. Whether the drop branch
    should exempt a self-declared skip belongs to whichever plan owns that
    scope — this test only makes the current answer visible.
    """

    def test_a_bare_skipped_fragment_is_a_benign_omission(self, tmp_path):
        fragment = {'status': 'skipped', 'aspect': 'script_failure_analysis', 'findings': []}
        _c, _w, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'script-failure-analysis': fragment}
        )
        assert 'Script Failure Analysis' in omitted
        assert 'Script Failure Analysis' not in dropped

    def test_a_skipped_fragment_naming_its_reason_is_classified_as_a_drop(self, tmp_path):
        # The anomaly, pinned as it currently behaves — see the class docstring.
        fragment = {
            'status': 'skipped',
            'aspect': 'script_failure_analysis',
            'skip_reason': 'no script-execution.log for this plan',
            'findings': [],
        }
        _c, _w, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'script-failure-analysis': fragment}
        )
        assert 'Script Failure Analysis' in dropped
        assert 'Script Failure Analysis' not in omitted


class TestFragmentHasPayload:
    def test_non_dict_is_false(self):
        assert _cr._fragment_has_payload('nope') is False
        assert _cr._fragment_has_payload(None) is False

    def test_envelope_only_fragment_is_false(self):
        assert _cr._fragment_has_payload({'status': 'success', 'aspect': 'x'}) is False

    def test_empty_payload_values_are_false(self):
        fragment = {'status': 'success', 'findings': [], 'summary': '', 'extra': None, 'flag': False}
        assert _cr._fragment_has_payload(fragment) is False

    def test_any_non_empty_non_envelope_value_is_true(self):
        assert _cr._fragment_has_payload({'status': 'error', 'findings': [{'severity': 'x'}]}) is True

    def test_numeric_zero_counts_as_payload(self):
        # ``False == 0`` and ``False == 0.0`` in Python, so an equality-based
        # sentinel tuple would misclassify a zero-valued count or ratio as
        # carrying no payload — silently dropping the very content this
        # discriminator exists to make loud.
        assert _cr._fragment_has_payload({'status': 'success', 'aspect': 'probe', 'unknown_count': 0}) is True
        assert _cr._fragment_has_payload({'status': 'success', 'aspect': 'probe', 'pass_ratio': 0.0}) is True


class TestCmdRunInProcess:
    def _write_bundle(self, path: Path) -> Path:
        path.write_text(
            '_executive-summary:\n'
            '  summary: "Probe run."\n'
            'artifact-consistency:\n'
            '  status: success\n'
            '  aspect: artifact_consistency\n',
            encoding='utf-8',
        )
        return path

    def test_archived_run_writes_audit_report_and_deletes_bundle(self, tmp_path):
        plan_dir = tmp_path / 'archived-plan'
        plan_dir.mkdir()
        bundle = self._write_bundle(tmp_path / 'fragments.toon')
        args = Namespace(
            command='run',
            plan_id=None,
            archived_plan_path=str(plan_dir),
            mode='archived',
            fragments_file=str(bundle),
            session_id=None,
        )

        result = _cr.cmd_run(args)

        assert result['status'] == 'success'
        assert result['mode'] == 'archived'
        output_path = Path(result['output_path'])
        assert output_path.exists()
        assert output_path.name.startswith('quality-verification-report-audit-')
        assert 'Executive Summary' in result['sections_written']
        # Successful compile auto-deletes the fragments bundle.
        assert not bundle.exists()

    def test_missing_plan_dir_raises(self, tmp_path):
        bundle = self._write_bundle(tmp_path / 'fragments.toon')
        args = Namespace(
            command='run',
            plan_id=None,
            archived_plan_path=str(tmp_path / 'no-such-plan'),
            mode='archived',
            fragments_file=str(bundle),
            session_id=None,
        )
        with pytest.raises(ValueError, match='Plan directory does not exist'):
            _cr.cmd_run(args)
