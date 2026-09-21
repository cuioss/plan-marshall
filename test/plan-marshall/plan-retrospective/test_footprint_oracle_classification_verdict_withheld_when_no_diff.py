# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks.

Its one section: A verdict over no evidence is not a clean result.
"""

from __future__ import annotations

from _footprint_oracle_classification_fixtures import MANIFEST_SCRIPT, _check, _setup, _write_diff
from _plan_retrospective_fixtures import stage_evidence_free_references

from conftest import load_script_module, run_script

_cmc = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_withheld_no_diff_mod'
)

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

    def test_no_diff_file_and_no_resolvable_tier_withholds_the_verdict(self, tmp_path, monkeypatch):
        plan_id, plan_dir = _setup(tmp_path, monkeypatch, self._MANIFEST)
        # The happy-path fixture carries a POPULATED legacy ``modified_files``
        # key for the artifact-consistency recall check, and that key is itself a
        # resolving tier — inheriting it would make this the RESOLVED-footprint
        # case and leave the evidence-free path untested. The scenario is
        # repaired; the assertions below are not.
        stage_evidence_free_references(plan_dir)

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        # That no tier answered is read from the production sentinel, not assumed
        # from the fixture: a references payload that accidentally kept a
        # resolving key would label the base with that key's name instead.
        assert data['diff']['base'] == 'unresolved', data['diff']
        assert data['diff']['diff_available'] is False
        docs_only = _check(data['checks'], 'docs_only_diff')
        assert docs_only['status'] == _cmc.STATUS_INCONCLUSIVE, docs_only
        assert 'could not be resolved from any tier' in docs_only['message']

    def test_a_supplied_empty_diff_file_is_evidence_and_still_passes(self, tmp_path, monkeypatch):
        """The negative control, and the distinction that matters.

        A supplied file naming nothing is a RESOLVED empty footprint — the run
        really did change nothing — so a rule may pass on it. Inferring absence
        from `len(files) == 0` would collapse this into the case above.
        """
        plan_id, _ = _setup(tmp_path, monkeypatch, self._MANIFEST)
        diff = _write_diff(tmp_path, [])

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff))
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is True
        assert data['diff']['files_total'] == 0
        assert _check(data['checks'], 'docs_only_diff')['status'] == 'pass'
