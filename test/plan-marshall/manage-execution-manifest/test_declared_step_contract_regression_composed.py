# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_declared_step_contract_regression_fixtures import (
    _EMITTER,
    _compose_ns,
    _mem,
    _persisted_phase_6_steps,
    _seed_marshal,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# (b) Ascending frontmatter order in the composed manifest
# =============================================================================


class TestComposedPhase6IsAscending:
    """The composed ``phase_6.steps`` is in ascending frontmatter ``order``."""

    #: Seeded in the DEFECTIVE sequence: the emitter is appended after
    #: ``archive-plan`` — the terminal barrier and the highest order in the set —
    #: reproducing what ``manage-config sync-defaults`` produces when it back-fills
    #: a default-on step by appending it. The emitter is seeded with its BARE id —
    #: never the ``default:``-prefixed form.
    _INVERTED_SEED: dict[str, dict | None] = {
        'default:create-pr': None,
        'default:lessons-capture': None,
        'default:branch-cleanup': None,
        'default:archive-plan': None,
        _EMITTER: None,
    }

    #: Seeded with the emitter BEFORE the merge gate — the pre-reorder sequence.
    #: The composer must move it behind the gate, so the ordering assertion below
    #: observes the sort doing work rather than reading back its own seed.
    _EMITTER_AHEAD_OF_GATE_SEED: dict[str, dict | None] = {
        'default:create-pr': None,
        _EMITTER: None,
        'default:branch-cleanup': None,
        'default:archive-plan': None,
    }

    def test_emitter_is_emitted_after_branch_cleanup(self, plan_context):
        """A post-run-review step composes AFTER the merge gate.

        ``finalize-step-preference-emitter`` declares ``post_run_review: true``:
        it generalizes the just-finished run's operator gate-dispositions into
        durable hints, and the merge gate ``branch-cleanup`` is where the last of
        those dispositions is taken (the pre-merge review barrier, the bot
        re-review wait, triage and loop-back all live there). Ordered ahead of the
        gate it would emit a confident verdict over evidence the gate had not yet
        produced, so its place is behind it.

        Both orders are RESOLVED from the live step docs through the composer's own
        ``_resolve_step_order``, never from an order literal — the staleness this
        test is being repaired for came from citing a number that later moved.
        """
        import _manifest_validation as _mv

        emitter_order = _mv._resolve_step_order(_EMITTER)
        gate_order = _mv._resolve_step_order('branch-cleanup')
        assert isinstance(emitter_order, int) and isinstance(gate_order, int), (
            'Both orders must resolve from the live docs, or the comparison below '
            f'asserts nothing: emitter={emitter_order!r}, gate={gate_order!r}'
        )
        assert emitter_order > gate_order, (
            f'{_EMITTER} declares post_run_review, so its order ({emitter_order}) '
            f'must be strictly greater than the merge gate branch-cleanup '
            f'({gate_order}). This is the source-of-truth premise the composed '
            'sequence below is only the consequence of.'
        )

        # Seeded in the PRE-REORDER sequence, so a composer that failed to sort
        # would read back the emitter ahead of the gate and fail this test.
        _seed_marshal(self._EMITTER_AHEAD_OF_GATE_SEED)
        result = cmd_compose(_compose_ns('dsc-order-emitter'))

        assert result is not None and result['status'] == 'success'
        steps = _persisted_phase_6_steps('dsc-order-emitter')
        assert _EMITTER in steps and 'branch-cleanup' in steps
        assert steps.index(_EMITTER) > steps.index('branch-cleanup'), (
            f'{_EMITTER} (order {emitter_order}) must compose after branch-cleanup (order {gate_order}); got {steps!r}'
        )

    def test_emitter_is_carried_as_the_bare_id(self, plan_context):
        """The fixture and the emitted manifest both use the BARE id."""
        _seed_marshal(self._INVERTED_SEED)
        cmd_compose(_compose_ns('dsc-order-bare'))

        steps = _persisted_phase_6_steps('dsc-order-bare')
        assert _EMITTER in steps
        assert f'default:{_EMITTER}' not in steps
        assert not any(s.startswith('default:') for s in steps)

    def test_whole_composed_list_is_ascending(self, plan_context):
        """The invariant over the entire persisted list, not just the one pair."""
        _seed_marshal(self._INVERTED_SEED)
        cmd_compose(_compose_ns('dsc-order-whole'))

        steps = _persisted_phase_6_steps('dsc-order-whole')
        assert _mem.check_emitted_steps_ascending_order(steps) is None
        # archive-plan (order 1100, the terminus) is the terminal barrier.
        assert steps[-1] == 'archive-plan'

    def test_discriminator_unverifiable_order_is_rejected_where_the_legacy_walk_passed(self, plan_context, monkeypatch):
        """Non-vacuity: the pre-fix and post-fix verdicts diverge inside one run.

        With the emitter's ``order:`` unreadable, the composer's sort PINS it at
        whatever index the seed happened to give it — a position nothing verified —
        and the legacy ``_check_ascending_order`` skips the pinned entry and
        reports NO offender: the precise silent pass that let the defect ship. The
        compose must now fail loud instead. Both halves are asserted here, so the
        test cannot pass under the old behaviour.
        """
        import _manifest_validation as _mv

        real_read = _mv._read_frontmatter_order
        monkeypatch.setattr(
            _mv,
            '_read_frontmatter_order',
            lambda path: None if path.name == f'{_EMITTER}.md' else real_read(path),
        )

        # Pre-fix verdict on the pinned list: silent pass.
        pinned = _mv._sort_steps_by_frontmatter_order(['create-pr', 'branch-cleanup', _EMITTER, 'archive-plan'])
        assert pinned.index(_EMITTER) > pinned.index('branch-cleanup')
        assert _mv._check_ascending_order(pinned) is None

        # Post-fix verdict on the same inputs, through the real entry point.
        _seed_marshal(self._INVERTED_SEED)
        result = cmd_compose(_compose_ns('dsc-order-unverifiable'))

        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'phase_6_order_violation'
        assert result['step_id'] == _EMITTER
        assert result['reason'] == 'unresolvable_order'
        # A rejected compose persists nothing.
        assert read_manifest('dsc-order-unverifiable') is None
