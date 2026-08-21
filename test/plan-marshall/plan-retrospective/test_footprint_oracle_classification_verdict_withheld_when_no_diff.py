# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks.

Its one section: A verdict over no evidence is not a clean result.
"""


from __future__ import annotations

from _footprint_oracle_classification_fixtures import MANIFEST_SCRIPT, _check, _setup, _write_diff

from conftest import run_script  # noqa: E402

# =============================================================================
# A verdict over no evidence is not a clean result
# =============================================================================


class TestVerdictWithheldWhenNoDiffEvidenceExists:
    """An ABSENT diff observation and a RESOLVED empty one are different states.

    The zero-evidence sibling of the majority-discarded case, and the filtering
    logic cannot see it: nothing was discarded, so the reduction is empty, yet the
    rule evaluated an empty footprint it never received and said "all 0 entries are
    docs-shaped".
    """

    _MANIFEST = {
        'manifest_version': 1,
        'plan_id': 'oracle-plan',
        'phase_5': {'early_terminate': False, 'verification_steps': []},
        'phase_6': {'steps': ['push']},
    }

    def test_no_diff_file_and_no_base_ref_withholds_the_verdict(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(tmp_path, monkeypatch, self._MANIFEST)

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is False
        docs_only = _check(data['checks'], 'docs_only_diff')
        assert docs_only['status'] == 'indeterminate', docs_only
        assert 'no diff evidence was available' in docs_only['message']

    def test_a_supplied_empty_diff_file_is_evidence_and_still_passes(self, tmp_path, monkeypatch):
        """The negative control, and the distinction that matters.

        A supplied file naming nothing is a RESOLVED empty footprint — the run
        really did change nothing — so a rule may pass on it. Inferring absence
        from `len(files) == 0` would collapse this into the case above.
        """
        plan_id, _ = _setup(tmp_path, monkeypatch, self._MANIFEST)
        diff = _write_diff(tmp_path, [])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is True
        assert data['diff']['files_total'] == 0
        assert _check(data['checks'], 'docs_only_diff')['status'] == 'pass'
