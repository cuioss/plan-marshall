# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import (
    _ORDER_RESOLVABLE_CANDIDATES,
    _SHUFFLED_SEED_ORDERINGS,
    _check_ascending_order,
    _compose_ns,
    _resolve_step_order,
    cmd_compose,
    read_manifest,
)


def test_composed_phase_6_steps_hold_ascending_order_barrier_for_every_seed(plan_context):
    """The ascending-order barrier holds for every shuffled seed of the same set.

    General invariant regression (order-independent): whatever order the candidate
    steps are fed to cmd_compose, the composed phase_6.steps must (a) survive
    _check_ascending_order with no inversion, and (b) place no order-resolvable
    step whose resolved order is below archive-plan's after archive-plan. Because
    archive-plan carries the highest resolvable order among finalize steps, this
    is the plan-mutating barrier: nothing order-resolvable may follow it.
    """
    archive_order = _resolve_step_order('archive-plan')
    assert archive_order is not None, 'archive-plan must resolve to a frontmatter order'

    for seed_index, seed in enumerate(_SHUFFLED_SEED_ORDERINGS):
        # Self-check: every seed is a permutation of the same candidate set, so
        # differences in the composed output are attributable to compose-time
        # sorting alone, not to a differing input set.
        assert sorted(seed) == sorted(_ORDER_RESOLVABLE_CANDIDATES), (
            f'seed {seed_index} is not a permutation of the candidate set'
        )

        plan_id = f'order-barrier-seed-{seed_index}'
        result = cmd_compose(_compose_ns(plan_id=plan_id, phase_6_steps=','.join(seed)))
        assert result is not None and result['status'] == 'success', f'compose failed for seed {seed_index}: {result}'

        manifest = read_manifest(plan_id)
        assert manifest is not None
        composed = manifest['phase_6']['steps']

        # (a) No inversion survives — the resolvable subsequence is non-decreasing.
        assert _check_ascending_order(composed) is None, f'inversion survived for seed {seed_index}: {composed}'

        # (b) No order-resolvable step below archive-plan's order appears after it.
        archive_idx = composed.index('archive-plan')
        for later in composed[archive_idx + 1 :]:
            later_order = _resolve_step_order(later)
            assert not (later_order is not None and later_order < archive_order), (
                f'seed {seed_index}: `{later}` (order={later_order}) follows '
                f'archive-plan (order={archive_order}) — barrier violated in {composed}'
            )
