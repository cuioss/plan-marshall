# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# adr-propose registration tests
#
# adr-propose is the writing-hook sibling of lessons-capture: both turn what
# the plan settled into a durable artefact. They no longer share a pipeline
# slot — lessons-capture declares ``post_run_review: true`` and composes behind
# the merge gate, while adr-propose declares no such fact and keeps its pre-gate
# slot. What they still share is membership: adr-propose is registered in
# DEFAULT_PHASE_6_STEPS plus the Rule 1 (early_terminate_analysis) and Rule 6
# (verification_no_files) minimal intersection sets, so an analysis/verification
# plan that settled a decision can still propose an ADR.
# =============================================================================


def test_adr_propose_in_default_phase_6_steps():
    """adr-propose is registered in DEFAULT_PHASE_6_STEPS, in a slot that agrees
    with the live frontmatter ``order`` facts.

    adr-propose reads the decisions the plan settled — evidence that is complete
    before the branch ships — so it keeps its slot after the Sonar roundtrip and
    BEFORE the merge gate ``branch-cleanup``. ``lessons-capture`` declares
    ``post_run_review: true`` and therefore composes AFTER that gate, inverting
    the lessons-capture-before-adr-propose relation this test used to assert.

    Every position below is RESOLVED from the live step docs through the
    composer's own ``_resolve_step_order``, never from an order literal or a
    hardcoded index relation — citing a number that later moves is exactly the
    staleness this test is being repaired for.
    """
    import _manifest_validation as _mv

    assert 'adr-propose' in DEFAULT_PHASE_6_STEPS
    steps = list(DEFAULT_PHASE_6_STEPS)

    # The neighbourhood the reorder moved through: the Sonar roundtrip, the
    # writing hook, the merge gate, and the post-run-review sibling behind it.
    neighbours = ('sonar-roundtrip', 'adr-propose', 'branch-cleanup', 'lessons-capture')
    missing = [step for step in neighbours if step not in steps]
    assert not missing, f'DEFAULT_PHASE_6_STEPS must carry every neighbour; missing {missing!r}'

    resolved = {step: _mv._resolve_step_order(step) for step in neighbours}
    unresolved = sorted(step for step, order in resolved.items() if not isinstance(order, int))
    assert not unresolved, (
        'Every neighbour order must resolve from the live docs, or the comparisons '
        f'below assert nothing: unresolved {unresolved!r} in {resolved!r}'
    )
    orders = {step: order for step, order in resolved.items() if isinstance(order, int)}

    # Source-of-truth premise: the frontmatter itself places adr-propose ahead of
    # the merge gate and lessons-capture behind it. The tuple sequence asserted
    # afterwards is only the consequence of these two facts.
    assert orders['sonar-roundtrip'] < orders['adr-propose'] < orders['branch-cleanup'], (
        f'adr-propose ({orders["adr-propose"]}) must sit between sonar-roundtrip '
        f'({orders["sonar-roundtrip"]}) and the merge gate branch-cleanup '
        f'({orders["branch-cleanup"]})'
    )
    assert orders['branch-cleanup'] < orders['lessons-capture'], (
        f'lessons-capture ({orders["lessons-capture"]}) declares post_run_review, so it '
        f'must compose after the merge gate branch-cleanup ({orders["branch-cleanup"]})'
    )

    # Consequence: DEFAULT_PHASE_6_STEPS is written in ascending order, so the
    # tuple's relative sequence must equal the one the resolved orders induce.
    # This fails in EITHER direction — a tuple that regresses to the pre-reorder
    # sequence and a tuple that overshoots both disagree with the derivation.
    expected = sorted(neighbours, key=lambda step: orders[step])
    actual = sorted(neighbours, key=steps.index)
    assert actual == expected, (
        'DEFAULT_PHASE_6_STEPS must be written in ascending frontmatter order: live '
        f'orders {orders!r} imply {expected!r}, tuple reads {actual!r}'
    )


def test_adr_propose_kept_in_rule_1_early_terminate_minimal_set(plan_context):
    """Rule 1 (early_terminate_analysis) keeps adr-propose alongside
    lessons-capture and archive-plan when it is in the candidate set."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-rule-1',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    manifest = read_manifest('adr-rule-1')
    assert manifest is not None
    assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'adr-propose', 'archive-plan'}


def test_adr_propose_kept_in_rule_6_verification_no_files_minimal_set(plan_context):
    """Rule 6 (verification_no_files) keeps adr-propose alongside
    lessons-capture and archive-plan when it is in the candidate set."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-rule-6',
            change_type='verification',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'verification_no_files'
    manifest = read_manifest('adr-rule-6')
    assert manifest is not None
    assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'adr-propose', 'archive-plan'}


def test_adr_propose_present_in_default_feature_phase_6(plan_context):
    """A default feature plan (Rule 7) carries adr-propose in its phase-6 set
    — the docs-only and surgical pre-filters pass it through unless explicitly
    subtracted."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-default-feature',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=12,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    manifest = read_manifest('adr-default-feature')
    assert manifest is not None
    assert 'adr-propose' in manifest['phase_6']['steps']


def test_adr_propose_kept_in_surgical_tech_debt_phase_6(plan_context):
    """The scope row passes phase_6_candidates through unchanged except
    the simplify/whole-tree gates, so adr-propose survives."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-docs-only',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=3,
            # docs-shaped candidate set: only quality-gate, no module-tests/coverage.
            phase_5_steps='quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('adr-docs-only')
    assert manifest is not None
    assert 'adr-propose' in manifest['phase_6']['steps']
