# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_subtraction_visibility_population_fixtures import _SITE_INVOCATIONS, pytest

# =============================================================================
# The invariant — every site reports exactly what it removed
# =============================================================================


class TestEverySiteReportsItsSubtraction:
    """No compose-time subtraction may leave the candidate list unaccounted for."""

    @pytest.mark.parametrize('site_name', sorted(_SITE_INVOCATIONS))
    def test_site_actually_drops_something(self, site_name, monkeypatch):
        """Each invocation must FIRE, or its report assertion proves nothing.

        A site driven with inputs that happen not to trigger the drop reports an
        empty record list, which trivially "accounts for" the empty removed set.
        Pinning that the drop fired first is what keeps the invariant below from
        passing vacuously.
        """
        run = _SITE_INVOCATIONS[site_name](monkeypatch)

        assert run.removed, f'{site_name} was not driven into a firing drop'

    @pytest.mark.parametrize('site_name', sorted(_SITE_INVOCATIONS))
    def test_every_site_reports_every_step_it_removed(self, site_name, monkeypatch):
        run = _SITE_INVOCATIONS[site_name](monkeypatch)

        if run.kind == 'records':
            assert all(set(r) == {'step', 'reason'} for r in run.report), (
                f'{site_name} emitted a malformed subtraction record: {run.report}'
            )
            assert all(r['reason'] for r in run.report), f'{site_name} emitted a record with no reason: {run.report}'
            assert {r['step'] for r in run.report} == set(run.removed)
        elif run.kind == 'ids':
            assert set(run.report) == set(run.removed)
        elif run.kind == 'gate_records':
            assert all('step' in r and 'gate' in r for r in run.report)
            assert {r['step'] for r in run.report} == set(run.removed)
        elif run.kind == 'flag':
            # A single-step gate: identity is fixed by the site's own parameter,
            # so the report is the fired flag rather than a named record.
            assert run.report is True
            assert run.removed == [run.single_step]
        elif run.kind == 'verdict':
            decision, reason = run.report
            assert decision == 'not_necessary'
            assert reason, f'{site_name} dropped a step without the authority reason'
            assert run.removed == [run.single_step]
        else:  # pragma: no cover — a new kind must be given an assertion arm
            pytest.fail(f'{site_name} declares an unknown report kind {run.kind!r}')

    @pytest.mark.parametrize('site_name', sorted(_SITE_INVOCATIONS))
    def test_site_reports_nothing_it_did_not_remove(self, site_name, monkeypatch):
        """The other direction: a report may not name a step that survived.

        A site that reported its whole candidate list would satisfy a
        "names every removed step" check while telling the operator that steps
        which are still in the manifest were dropped.
        """
        run = _SITE_INVOCATIONS[site_name](monkeypatch)

        if run.kind in ('records', 'gate_records'):
            reported = {r['step'] for r in run.report}
        elif run.kind == 'ids':
            reported = set(run.report)
        else:
            reported = {run.single_step}
        survivors = reported & set(run.after)
        assert not survivors, f'{site_name} reported surviving step(s) as dropped: {survivors}'
