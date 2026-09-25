# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_census_fixtures import (
    Path,
    _census,
    _cohort,
    _write_plan,
    store,
)


class TestPartialCoverage:
    """An unreadable member degrades its cohort without erasing what WAS counted."""

    def test_an_unparseable_status_json_is_counted_and_named(self, store: Path) -> None:
        """Population keeps the member; ``unreadable_count`` and ``reason`` expose it.

        The shortfall must be visible rather than absorbed: a cohort that silently
        dropped the unreadable plan would report ``complete`` over a population it had
        not fully read.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        broken = store / 'plans' / 'broken-plan'
        broken.mkdir(parents=True)
        (broken / 'status.json').write_text('{not json\n')

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'partial', live
        assert live['population'] == 2, f'The unreadable plan is still a member; got {live!r}.'
        assert live['unreadable_count'] == 1, live
        assert 'broken-plan' in live['reason'], live
        assert live['open_phase_count'] == 1, live

    def test_a_directory_without_a_status_json_is_not_a_plan(self, store: Path) -> None:
        """Matched control: an orphan directory is neither a member nor unreadable.

        Without this, the cell above is consistent with the census counting every
        directory it sees and calling the ones it cannot parse unreadable — which would
        report the orphan population (``list-orphans``' surface) as broken plans.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done'})
        (store / 'plans' / 'orphan-dir').mkdir(parents=True)

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 1, f'The orphan directory is not a plan; got {live!r}.'
        assert live['unreadable_count'] == 0, live
