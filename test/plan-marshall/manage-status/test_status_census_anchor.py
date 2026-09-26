# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_status_census_fixtures import _census, pytest, status_query


class TestAnchorUnresolvedFailsClosed:
    """No anchor ⇒ no cohort rows, rather than three thoroughly-surveyed zeros."""

    def test_an_unresolvable_anchor_returns_no_cohorts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The resolver raising must surface as ``anchor_unresolved`` with no rows.

        Emitting ``population: 0`` for all three cohorts here would report an empty
        machine on the strength of a resolution that never happened — the same
        false-zero the ``unevaluated`` coverage state exists to prevent, one level up.
        """
        monkeypatch.setattr(
            status_query,
            'resolve_main_anchored_path',
            lambda _subpath: (_ for _ in ()).throw(RuntimeError('cannot resolve main checkout')),
        )

        result = _census()

        assert result['status'] == 'error', result
        assert result['error'] == 'anchor_unresolved', result
        assert 'cohorts' not in result, f'A failed anchor resolution may report no cohort rows; got {result!r}.'
        assert 'open_phase_records' not in result, result
        assert 'cannot resolve main checkout' in result['message'], (
            "The resolver's own diagnosis must survive into the message."
        )
