# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_status_census.py: main."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_census_fixtures import (
    _MAIN_PLAN,
    _WT_PLAN,
    Path,
    _census,
    _cohort,
    _records_for,
    real_geometry,
)


class TestMainAnchoredFromAWorktreeCwd:
    """Called from inside a worktree, the census still reports MAIN's stores."""

    def test_the_anchor_is_main_not_the_worktree_the_caller_stands_in(self, real_geometry: dict[str, Path]) -> None:
        """The resolved anchor is the main checkout's ``.plan/local``.

        This is the assertion a cwd-relative resolver fails: standing in the worktree,
        the uniform walk-up finds ``worktree/.plan/local`` first and anchors there.
        """
        result = _census()

        assert result['status'] == 'success', result
        assert result['anchor'] == 'main', (
            'Both override spellings were neutralised, so the production '
            f'git-common-dir branch must be the one that answered; got {result!r}.'
        )
        assert Path(result['anchor_path']) == real_geometry['main_local']
        assert Path(result['anchor_path']) != real_geometry['worktree'] / '.plan' / 'local', (
            'Anchoring on the cwd worktree is the defect this verb exists to avoid.'
        )

    def test_each_plan_is_reported_under_the_store_it_actually_lives_in(self, real_geometry: dict[str, Path]) -> None:
        """Main's plan is ``live``; the moved-in plan is ``worktree``.

        Under a cwd-relative resolution the moved-in plan would be the LIVE cohort (it
        is what ``{cwd}/.plan/local/plans`` holds) and main's plan would be invisible.
        Asserting which cohort each id lands in is what separates the two resolutions;
        a bare population count of 1 and 1 would not.
        """
        del real_geometry  # The fixture's effect is the cwd and the tree it built.

        result = _census()

        live = _cohort(result, 'live')
        worktree = _cohort(result, 'worktree')
        assert live['coverage'] == 'complete', live
        assert worktree['coverage'] == 'complete', worktree
        assert live['population'] == 1, live
        assert worktree['population'] == 1, worktree

        assert [record['id'] for record in _records_for(result, 'live')] == [_MAIN_PLAN]
        assert [record['id'] for record in _records_for(result, 'worktree')] == [_WT_PLAN]
        assert _WT_PLAN not in [record['id'] for record in _records_for(result, 'live')], (
            'The moved-in plan belongs to the worktree cohort; reporting it as live is '
            'precisely what a cwd-anchored enumeration does from this cwd.'
        )
