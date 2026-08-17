#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The worktree contract's three-state machine has exactly one owner.

``manage-status get-worktree-path`` publishes an explicit ``worktree_state``
discriminator over a three-state contract. Consumers must branch on that
published value; re-deriving it from the primitive ``use_worktree`` /
``worktree_path`` pair cannot distinguish a plan that will NEVER have a worktree
(``disabled``) from one whose worktree does not exist YET (``pending``), and the
two route differently.

:func:`file_ops.derive_worktree_state` is that owner. The producer publishes from
it, and a consumer that reads ``status.json`` metadata directly rather than
shelling out calls it instead of re-implementing the rule — which is what keeps
one definition of the machine in the tree rather than one per reader.

The parser tests below pin the OTHER half of the same contract: the payload
reader takes the published discriminator and fails closed when it is absent,
rather than reconstructing a state from the primitives that ride alongside it.
"""

import pytest
from file_ops import (
    VALID_WORKTREE_STATES,
    WORKTREE_STATE_DISABLED,
    WORKTREE_STATE_MATERIALIZED,
    WORKTREE_STATE_PENDING,
    WorktreeResolutionError,
    _parse_get_worktree_path_output,
    derive_worktree_state,
)

STUB_WORKTREE = '/tmp/test-worktree-state-discriminator'


def _payload(**fields: str) -> str:
    """Render a flat TOON payload from ``key: value`` pairs."""
    return '\n'.join(f'{key}: {value}' for key, value in fields.items()) + '\n'


# =============================================================================
# The state machine
# =============================================================================


class TestDeriveWorktreeState:
    """Every metadata shape maps to exactly one of the three published states."""

    @pytest.mark.parametrize(
        ('metadata', 'expected_state', 'expected_path'),
        [
            ({}, WORKTREE_STATE_DISABLED, ''),
            ({'use_worktree': False}, WORKTREE_STATE_DISABLED, ''),
            # A disabled plan that still carries a stale path is disabled: the
            # flag decides, and the leftover path must not resurrect a worktree
            # the plan opted out of.
            (
                {'use_worktree': False, 'worktree_path': STUB_WORKTREE},
                WORKTREE_STATE_DISABLED,
                '',
            ),
            ({'use_worktree': True}, WORKTREE_STATE_PENDING, ''),
            ({'use_worktree': True, 'worktree_path': ''}, WORKTREE_STATE_PENDING, ''),
            (
                {'use_worktree': True, 'worktree_path': STUB_WORKTREE},
                WORKTREE_STATE_MATERIALIZED,
                STUB_WORKTREE,
            ),
        ],
        ids=[
            'absent-metadata',
            'flag-false',
            'flag-false-with-stale-path',
            'flag-true-no-path-key',
            'flag-true-empty-path',
            'flag-true-with-path',
        ],
    )
    def test_metadata_maps_to_its_state(self, metadata, expected_state, expected_path):
        assert derive_worktree_state(metadata) == (expected_state, expected_path)

    @pytest.mark.parametrize(
        'metadata', [None, [], 'not-a-mapping', 42], ids=['none', 'list', 'str', 'int']
    )
    def test_non_mapping_metadata_is_disabled(self, metadata):
        """Absent or malformed metadata is a plan with no worktree, not an error."""
        assert derive_worktree_state(metadata) == (WORKTREE_STATE_DISABLED, '')

    @pytest.mark.parametrize(
        'worktree_path', [None, 0, [], {}], ids=['none', 'int', 'list', 'dict']
    )
    def test_non_string_path_is_pending_not_materialized(self, worktree_path):
        """A path that is not a usable string has not materialized a worktree."""
        state, path = derive_worktree_state(
            {'use_worktree': True, 'worktree_path': worktree_path}
        )

        assert (state, path) == (WORKTREE_STATE_PENDING, '')

    def test_every_returned_state_is_in_the_closed_vocabulary(self):
        """The machine cannot emit a state outside the published set.

        Enumerated over the cross-product of both input axes rather than over a
        chosen sample: the guarantee is about the function's whole range, and a
        sample of inputs can only ever evidence a sample of the range.
        """
        flags = [True, False, None, 'true', 0]
        paths = [None, '', STUB_WORKTREE, 0, []]
        observed = {
            derive_worktree_state({'use_worktree': flag, 'worktree_path': path})[0]
            for flag in flags
            for path in paths
        }

        assert observed, 'the enumeration produced no states'
        assert observed <= set(VALID_WORKTREE_STATES), (
            f'states outside the vocabulary: {observed - set(VALID_WORKTREE_STATES)}'
        )


# =============================================================================
# The payload reader
# =============================================================================


class TestParseGetWorktreePathOutput:
    """The reader takes the published discriminator and never rebuilds it."""

    @pytest.mark.parametrize(
        'state', list(VALID_WORKTREE_STATES), ids=list(VALID_WORKTREE_STATES)
    )
    def test_published_state_is_returned_verbatim(self, state):
        stdout = _payload(
            status='success', worktree_state=state, worktree_path=f'"{STUB_WORKTREE}"'
        )

        assert _parse_get_worktree_path_output(stdout)[0] == state

    def test_published_state_wins_over_the_primitives_it_rides_with(self):
        """The primitives are ignored, so a stale one cannot re-derive a state.

        This is the whole point of the discriminator: a payload whose
        ``use_worktree`` says one thing and whose ``worktree_state`` says another
        must be read as the state the producer published. An implementation that
        still consulted the primitives would answer ``materialized`` here.
        """
        stdout = _payload(
            status='success',
            use_worktree='true',
            worktree_state=WORKTREE_STATE_DISABLED,
            worktree_path=f'"{STUB_WORKTREE}"',
        )

        state, _path = _parse_get_worktree_path_output(stdout)

        assert state == WORKTREE_STATE_DISABLED

    def test_absent_state_fails_closed(self):
        """A payload with no discriminator is a contract break, not a guess.

        Falling back to the primitives here is exactly the re-derivation the
        discriminator exists to remove, so their presence must not rescue the
        payload.
        """
        stdout = _payload(status='success', use_worktree='true', worktree_path='"/tmp/wt"')

        with pytest.raises(WorktreeResolutionError, match='no recognised'):
            _parse_get_worktree_path_output(stdout)

    def test_unrecognised_state_fails_closed(self):
        stdout = _payload(status='success', worktree_state='half-built', worktree_path='""')

        with pytest.raises(WorktreeResolutionError, match='no recognised'):
            _parse_get_worktree_path_output(stdout)

    def test_non_success_payload_still_raises_first(self):
        """An error payload is reported as the error, not as a missing state."""
        stdout = _payload(status='error', error='worktree_unresolved', message='nope')

        with pytest.raises(WorktreeResolutionError, match='non-success'):
            _parse_get_worktree_path_output(stdout)
