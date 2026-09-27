# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_validate_loadable_fixtures import _EMITTER, _compose_ns, _mem, cmd_compose


class TestComposeAscendingOrderGateWiring:
    """``cmd_compose`` consults the gate and fails loud without writing a manifest."""

    def test_compose_fails_loud_on_an_unresolvable_order(self, plan_context, monkeypatch):
        import _manifest_validation as _mv

        real_read = _mv._read_frontmatter_order
        monkeypatch.setattr(
            _mv,
            '_read_frontmatter_order',
            lambda path: None if path.name == f'{_EMITTER}.md' else real_read(path),
        )
        candidates = ['push', 'create-pr', 'branch-cleanup', _EMITTER, 'archive-plan']
        result = cmd_compose(_compose_ns('order-gate-unresolvable', phase_6_steps=','.join(candidates)))

        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'phase_6_order_violation'
        assert result['phase'] == 'phase_6'
        assert result['step_id'] == _EMITTER
        assert result['reason'] == 'unresolvable_order'
        # Like its sibling gates, the fail-loud path writes no manifest.
        assert _mem.read_manifest('order-gate-unresolvable') is None

    def test_missing_source_is_reported_by_the_resolution_gate_not_this_one(self, plan_context):
        """Gate ordering: a step with NO source file is a resolution defect.

        ``unresolvable_step`` names the missing doc far more usefully than an
        ordering error would, so it is given first refusal — this gate runs after
        it and never steals that diagnostic.
        """
        candidates = ['push', 'ghost-builtin-step', 'archive-plan']
        result = cmd_compose(_compose_ns('order-gate-defers', phase_6_steps=','.join(candidates)))

        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'unresolvable_step'

    def test_ordinary_compose_passes_the_gate(self, plan_context):
        """Anti-vacuity: the gate must not reject an ordinary, correct compose."""
        result = cmd_compose(_compose_ns('order-gate-clean'))

        assert result is not None
        assert result['status'] == 'success'
        manifest = _mem.read_manifest('order-gate-clean')
        assert manifest is not None
        assert _mem.check_emitted_steps_ascending_order(manifest['phase_6']['steps']) is None

    def test_emitter_is_composed_after_branch_cleanup(self, plan_context):
        """A post-run-review step composes AFTER the merge gate.

        The emitter declares ``post_run_review: true`` — it generalizes the
        finished run's operator gate-dispositions, and the merge gate
        ``branch-cleanup`` is where the last of those dispositions is taken. Both
        orders are RESOLVED from the live step docs rather than cited as literals,
        so this test cannot re-acquire the staleness it is being repaired for.
        """
        emitter_order = _mem._resolve_step_order(_EMITTER)
        gate_order = _mem._resolve_step_order('branch-cleanup')
        assert isinstance(emitter_order, int) and isinstance(gate_order, int), (
            'Both orders must resolve from the live docs, or the comparison below '
            f'asserts nothing: emitter={emitter_order!r}, gate={gate_order!r}'
        )
        assert emitter_order > gate_order, (
            f'{_EMITTER} declares post_run_review, so its order ({emitter_order}) '
            f'must be strictly greater than branch-cleanup ({gate_order}).'
        )

        # Candidates in the PRE-REORDER sequence: a composer that failed to sort
        # would read the emitter back ahead of the gate and fail this test.
        candidates = ['push', 'create-pr', _EMITTER, 'branch-cleanup', 'archive-plan']
        result = cmd_compose(_compose_ns('order-gate-emitter', phase_6_steps=','.join(candidates)))

        assert result is not None and result['status'] == 'success'
        steps = _mem.read_manifest('order-gate-emitter')['phase_6']['steps']
        assert steps.index(_EMITTER) > steps.index('branch-cleanup'), (
            f'{_EMITTER} (order {emitter_order}) must compose after branch-cleanup (order {gate_order}); got {steps!r}'
        )
