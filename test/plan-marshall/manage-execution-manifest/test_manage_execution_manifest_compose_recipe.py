# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_recipe_path_retains_review_gates_drops_only_legacy_ci_wait(plan_context):
    """Row 2 — recipe_key present → ONLY defensively drop legacy 'ci-wait'.

    Review gates (automatic-review, sonar-roundtrip) are NEVER silently
    suppressed by the planner — the recipe label is exactly the case
    where the bots' job is to catch what humans miss. CI completion is
    now a dispatcher-resolved precondition declared via requires:
    [ci-complete] on consumer step frontmatters, not a sibling step.
    """
    # Inject the legacy ci-wait into the candidate list to assert the
    # defensive narrowing still drops it. The default candidate set no
    # longer contains it.
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-recipe',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'
    manifest = read_manifest('matrix-recipe')
    assert manifest is not None
    # Review gates RETAINED — never silently suppressed.
    assert 'automatic-review' in manifest['phase_6']['steps']
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    # Legacy ci-wait still defensively narrowed out.
    assert 'ci-wait' not in manifest['phase_6']['steps']
    assert 'push' in manifest['phase_6']['steps']



def test_recipe_wins_over_the_scope_row_when_both_match(plan_context):
    """The recipe row evaluates first — recipe_key short-circuits the scope row."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-precedence-rd',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            # Docs-only candidate set; recipe rule should still win.
            phase_5_steps='quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'



def test_recipe_with_partial_phase_5_candidates_filters_to_known_steps(plan_context):
    """Recipe rule intersects phase_5 candidates by role ∈ {quality-gate, module-tests}.

    See decision-rules.md § Role-Field Intersection. ``verify:coverage``
    (role ``coverage``) and ``exotic-step`` (no role) are dropped;
    ``verify:quality-gate`` (role ``quality-gate``) and ``verify:module-tests``
    (role ``module-tests``) are kept.
    """
    cmd_compose(
        _compose_ns(
            plan_id='matrix-recipe-filter',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            # Pass an unknown candidate alongside the known ones.
            phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage,exotic-step',
        )
    )
    manifest = read_manifest('matrix-recipe-filter')
    assert manifest is not None
    # Recipe keeps candidates whose role ∈ {quality-gate, module-tests};
    # verify:coverage (role: coverage) and exotic-step (no role) dropped.
    assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']
