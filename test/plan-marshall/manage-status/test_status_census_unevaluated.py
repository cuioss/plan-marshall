# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_census_fixtures import Path, _census, _cohort, store


class TestUnevaluatedIsNotZero:
    """Matched pair: a cohort nobody could enumerate vs one that is verifiably empty.

    Both cells ask about the SAME cohort and differ only in what sits at its path, so
    the contrast is attributable to that and nothing else.
    """

    def test_an_unlistable_cohort_omits_the_population_key_entirely(self, store: Path) -> None:
        """A regular FILE at the cohort path ⇒ ``unevaluated``, with no counts at all.

        ``iterdir`` raises ``NotADirectoryError`` (an ``OSError``), so nothing was
        enumerated. Publishing ``population: 0`` here would be byte-identical to the
        control below, where the store really is empty — which is the confusion the
        key's ABSENCE exists to make unreachable.
        """
        (store / 'plans').write_text('not a directory\n')

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'unevaluated', live
        assert 'population' not in live, f'An unevaluated cohort must publish no population at all, got {live!r}.'
        assert 'open_phase_count' not in live, live
        assert 'unreadable_count' not in live, (
            'On a store that was never enumerated, "zero unreadable members" is a '
            f'claim about members nobody examined; got {live!r}.'
        )
        assert live['reason'], 'An unevaluated cohort must name the condition.'

    def test_a_genuinely_absent_cohort_reports_a_real_zero_population(self, store: Path) -> None:
        """Matched control: directory absent, anchor resolved ⇒ ``complete``, ``0``.

        The load-bearing half. Without it, the assertion above is equally consistent
        with a verb that omits the counts for every cohort, evaluated or not — so the
        honesty property would be untested and a verb reporting nothing anywhere would
        pass. Here the anchor resolved and the store demonstrably holds nothing, which
        is the one case where a zero IS evidence.
        """
        assert not (store / 'plans').exists(), 'The control must leave the cohort path absent.'

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 0, (
            f'An absent cohort under a resolved anchor is a verified empty store; got {live!r}.'
        )
        assert live['open_phase_count'] == 0, live
        assert live['unreadable_count'] == 0, live
        assert 'reason' not in live, f'A complete cohort has no shortfall to name; got {live!r}.'
