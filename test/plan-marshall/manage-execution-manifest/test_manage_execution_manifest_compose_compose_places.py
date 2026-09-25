# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _mem,
    _stub_footprint,
    _write_marshal,
    cmd_compose,
    read_manifest,
)


def test_compose_places_settle_steps_before_push_and_wait_steps_after(plan_context):
    """D3 mutation-settling reorder: the composer's ``_sort_steps_by_frontmatter_order``
    places every local-settleable HEAD-changing step (order < 11) BEFORE
    ``default:push`` (order 11) and every post-push WAIT step (order > 11) AFTER
    it — the settle → push once → wait contract expressed purely via step-doc
    ``order:`` frontmatter. Pins the D3 move of ``architecture-refresh`` from the
    post-push region (order 25) into the pre-push settle band (order 10, after
    plan 300 D2's de-collision).
    """
    # Deliberately SCRAMBLED input: push first, wait steps and architecture-refresh
    # ahead of the other settle steps — the composer must re-sort by resolved
    # frontmatter order so the barrier holds regardless of candidate-list order.
    scrambled = [
        'push',  # order 11 (the single push barrier)
        'ci-verify',  # wait (> 11)
        'sonar-roundtrip',  # wait (> 11)
        'architecture-refresh',  # settle (order 10, de-collided; last in band) — the D3 move
        'finalize-step-security-audit',  # settle (order 9)
        'finalize-step-simplify',  # settle (order 8)
        'pre-push-quality-gate',  # settle (order 5)
        'finalize-step-sync-baseline',  # settle (order 3)
        'create-pr',  # wait (> 11)
        'automatic-review',  # wait (> 11)
        'branch-cleanup',  # merge (order 70)
    ]
    # ``pre-push-quality-gate`` is order-band-3 settle, but it is also governed by
    # the orthogonal build-necessity pre-filter (``should_execute_build``): a
    # footprint-less compose would drop it before the sort can place it. To assert
    # the ORDERING of the settle step it must survive, so seed a build_map glob and
    # a matching live footprint. The two monkeypatched seams are restored in the
    # ``finally`` block so the stub never leaks to sibling tests.
    import extension_base

    _original_resolve_footprint = _mem._resolve_footprint
    _original_plan_footprint = extension_base._resolve_plan_footprint
    _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
    _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])
    try:
        result = cmd_compose(
            _compose_ns(
                plan_id='settle-before-push',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_6_steps=','.join(scrambled),
            )
        )
    finally:
        _mem._resolve_footprint = _original_resolve_footprint
        extension_base._resolve_plan_footprint = _original_plan_footprint
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('settle-before-push')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    push_idx = steps.index('push')
    # Every local-settleable HEAD-changing step sorts BEFORE the single push.
    for settle in (
        'finalize-step-sync-baseline',
        'pre-push-quality-gate',
        'finalize-step-simplify',
        'finalize-step-security-audit',
        'architecture-refresh',
    ):
        assert steps.index(settle) < push_idx, f'{settle!r} must sort before push; got {steps!r}'
    # architecture-refresh (order 10, last in the settle band) sits in the settle
    # band, not the post-push region it occupied at order 25.
    assert steps.index('architecture-refresh') < push_idx
    # Every post-push WAIT step sorts AFTER the single push.
    for wait in ('create-pr', 'ci-verify', 'automatic-review', 'sonar-roundtrip'):
        assert steps.index(wait) > push_idx, f'{wait!r} must sort after push; got {steps!r}'
