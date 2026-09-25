# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_census_fixtures import (
    Path,
    _census,
    _cohort,
    _write_plan,
    status_query,
    store,
)


class TestTheWorktreeSegmentHasOneDefinition:
    """``worktrees`` is one scalar, consumed by both builders that compose the container path.

    ``file_ops.get_worktree_root()`` and this verb anchor on DIFFERENT bases by design
    — cwd-relative versus main-anchored — so they cannot be collapsed into one
    function, and substituting one for the other would be wrong. The SEGMENT is the
    only thing they genuinely share. Two independently-spelled copies of it is what
    would let a re-spelling send this cohort scanning an absent path while it published
    ``coverage: complete`` with ``population: 0``.

    The identity cell pins the single definition; the behavioural pair pins that the
    census really keys on it, because an identity assertion alone would pass against a
    builder that imported the name and then ignored it.
    """

    def test_both_builders_read_the_same_definition(self) -> None:
        """One object, reached by identity from both consumers and from its home."""
        import file_ops
        import marketplace_paths

        assert file_ops.WORKTREES_DIRNAME is marketplace_paths.WORKTREES_DIRNAME, (
            'file_ops must consume the shared segment, not a local copy of the literal.'
        )
        assert status_query.WORKTREES_DIRNAME is marketplace_paths.WORKTREES_DIRNAME, (
            'The census must consume the shared segment, not a local copy of the literal.'
        )

    def test_the_census_finds_a_store_placed_under_the_shared_segment(self, store: Path) -> None:
        """The cohort path is composed from the shared name, so a store there is seen."""
        import marketplace_paths

        plans = store / marketplace_paths.WORKTREES_DIRNAME / 'wt-0' / '.plan' / 'local' / 'plans'
        _write_plan(plans / 'wt-plan-0', {'1-init': 'done', '5-execute': 'in_progress'})

        worktree = _cohort(_census(), 'worktree')

        assert worktree['coverage'] == 'complete', worktree
        assert worktree['population'] == 1, f'A store under the shared segment must be enumerated; got {worktree!r}.'

    def test_a_store_under_a_different_segment_reads_as_a_confident_zero(self, store: Path) -> None:
        """Matched control: the shape a divergent spelling would produce.

        Deliberately NOT an assertion that the census is wrong — it is right to report
        an empty store here. The cell exists to make the FAILURE MODE visible: this
        ``population: 0`` is byte-identical to the one the cell above would produce if
        the two builders ever spelled the segment differently, which is exactly why the
        scalar has a single home.
        """
        import marketplace_paths

        divergent = f'{marketplace_paths.WORKTREES_DIRNAME}-renamed'
        assert divergent != marketplace_paths.WORKTREES_DIRNAME
        plans = store / divergent / 'wt-0' / '.plan' / 'local' / 'plans'
        _write_plan(plans / 'wt-plan-0', {'1-init': 'done', '5-execute': 'in_progress'})

        worktree = _cohort(_census(), 'worktree')

        assert worktree['coverage'] == 'complete', worktree
        assert worktree['population'] == 0, (
            f'A store outside the composed path is invisible AND indistinguishable from '
            f'an empty machine; got {worktree!r}.'
        )
