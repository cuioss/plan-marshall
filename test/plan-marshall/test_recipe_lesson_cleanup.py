#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for recipe-lesson-cleanup + phase-1-init lesson auto-suggest hook.

The recipe and the auto-suggest hook are workflow-driven (markdown skills with
no Python entry point of their own). These tests pin the contracts those
skills depend on:

- The auto-suggest "doc-shaped" predicate documented in
  ``phase-1-init/SKILL.md`` Step 5c — three rules that must all hold for the
  recipe to be auto-suggested.
- The fixed lesson-kind → change_type mapping documented in
  ``recipe-lesson-cleanup/SKILL.md`` Step 2 (the recipe's only branching
  decision).
- The slim end-to-end manifest produced by ``manage-execution-manifest
  compose`` when the recipe inputs are forwarded (scope_estimate=surgical,
  recipe_key=lesson_cleanup, derived change_type) — i.e. the cascade that
  makes the recipe worth the effort.

Tests in this module deliberately do NOT duplicate the broader manifest-rule
coverage living in ``test/plan-marshall/manage-execution-manifest/``. This
suite is scoped strictly to the recipe and auto-suggest contracts.
"""


from argparse import Namespace

import pytest
from _recipe_lesson_cleanup_fixtures import (
    _CODE_ACTION_VERBS,
    _CODE_FENCE_LANGS,
    CODE_SHAPED_LESSON_VIA_FENCE,
    CODE_SHAPED_LESSON_VIA_TEST_VERB,
    CODE_SHAPED_LESSON_VIA_VERB,
    DEFAULT_PHASE_6_STEPS,
    DOC_SHAPED_LESSON,
    DOC_SHAPED_MULTIPLE_DIRECTIVES,
    LESSON_KIND_TO_CHANGE_TYPE,
    LESSON_WITH_NO_DIRECTIVES,
    cmd_compose,
    derive_change_type,
    is_doc_shaped,
    read_manifest,
)

# =============================================================================
# Auto-suggest predicate tests
# =============================================================================


class TestAutoSuggestPredicate:
    """Pin the doc-shaped predicate from phase-1-init/SKILL.md Step 5c.

    The auto-suggest hook fires only when ALL three rules hold. Each test
    below targets one rule explicitly so a regression in the SKILL.md spec
    fails loudly with a pointer to the violated rule.
    """

    def test_fires_for_doc_shaped_lesson_with_markdown_fence(self):
        """Rule 1 + 2 + 3 all hold — markdown fence is fine, verb is 'update'."""
        assert is_doc_shaped(DOC_SHAPED_LESSON) is True

    def test_fires_for_lesson_with_multiple_directives(self):
        """Multiple directives are still doc-shaped when each first line is doc-shaped."""
        assert is_doc_shaped(DOC_SHAPED_MULTIPLE_DIRECTIVES) is True

    def test_does_not_fire_for_python_code_fence(self):
        """Rule 1: a python-tagged fence disqualifies — code touches Python source."""
        assert is_doc_shaped(CODE_SHAPED_LESSON_VIA_FENCE) is False

    def test_does_not_fire_for_refactor_verb(self):
        """Rule 2: 'refactor' as the directive verb is a primary code-action verb."""
        assert is_doc_shaped(CODE_SHAPED_LESSON_VIA_VERB) is False

    def test_does_not_fire_for_test_verb(self):
        """Rule 2: 'test' as the directive verb is also a primary code-action verb."""
        assert is_doc_shaped(CODE_SHAPED_LESSON_VIA_TEST_VERB) is False

    def test_does_not_fire_when_no_directive_heading(self):
        """Rule 3: a body without any ## Directive heading must not auto-suggest."""
        assert is_doc_shaped(LESSON_WITH_NO_DIRECTIVES) is False

    @pytest.mark.parametrize('lang', sorted(_CODE_FENCE_LANGS))
    def test_does_not_fire_for_any_code_language_fence(self, lang):
        """Rule 1: every language in the disqualified set must trip the predicate."""
        body = f'## Directive\n\nUpdate the foo.\n\n```{lang}\nsome code here\n```\n'
        assert is_doc_shaped(body) is False, f'lang={lang} should disqualify'

    @pytest.mark.parametrize('verb', _CODE_ACTION_VERBS)
    def test_does_not_fire_for_any_code_action_verb(self, verb):
        """Rule 2: every banned verb at the start of a directive must disqualify."""
        body = f'## Directive\n\n{verb} the bar.\n'
        assert is_doc_shaped(body) is False, f'verb={verb!r} should disqualify'

    def test_fires_for_doc_verbs(self):
        """Verbs from the doc-shaped allowlist (update/document/clarify/etc.) must fire."""
        for verb in ('update', 'document', 'clarify', 'record', 'note', 'mention', 'link'):
            body = f'## Directive\n\n{verb} the README to mention the new option.\n'
            assert is_doc_shaped(body) is True, f'verb={verb!r} should be doc-shaped'


# =============================================================================
# Lesson-kind → change_type mapping tests
# =============================================================================


class TestLessonKindMapping:
    """Pin the deterministic mapping documented in recipe-lesson-cleanup/SKILL.md Step 2.

    The mapping is the contract that drives the manifest composer's cascade
    selection downstream. A silent change here would change the entire
    Phase 5/6 shape of every recipe-driven plan.
    """

    @pytest.mark.parametrize('kind,expected', sorted(LESSON_KIND_TO_CHANGE_TYPE.items()))
    def test_supported_kinds_map_to_documented_change_types(self, kind, expected):
        assert derive_change_type(kind) == expected

    def test_unknown_kind_raises_value_error(self):
        """Recipe Step 2 aborts with an explicit error on unknown kinds."""
        with pytest.raises(ValueError, match='not mapped'):
            derive_change_type('feature')

    def test_kind_mapping_is_exhaustive(self):
        """Guard against silent additions to the mapping outside this test file."""
        assert set(LESSON_KIND_TO_CHANGE_TYPE.keys()) == {'bug', 'improvement', 'anti-pattern'}


# =============================================================================
# End-to-end recipe path → slim manifest assertions
#
# The recipe sets ``scope_estimate=surgical`` and forwards the derived
# ``change_type`` plus ``recipe_key=lesson_cleanup`` to the manifest composer.
# These tests assert the resulting manifest is the documented slim shape:
#
#   Phase 5: quality-gate (and module-tests when present in the candidates)
#   Phase 6: push, create-pr, lessons-capture, branch-cleanup, archive-plan
#            (drops automatic-review, sonar-roundtrip)
#
# When ``recipe_key`` is set, the recipe rule (rule 2) fires for ALL three
# derived change_types — bug_fix / enhancement / tech_debt — because the
# recipe rule is checked before the surgical+change_type rules. This is the
# key behavior: the recipe path drives a uniform slim manifest regardless of
# the lesson kind.
# =============================================================================


class TestRecipePathEndToEnd:
    """Pin the slim-manifest contract for every supported lesson kind."""

    @pytest.mark.parametrize(
        'lesson_kind,change_type,plan_id',
        [
            ('bug', 'bug_fix', 'recipe-e2e-bug'),
            ('improvement', 'enhancement', 'recipe-e2e-improvement'),
            ('anti-pattern', 'tech_debt', 'recipe-e2e-antipattern'),
        ],
    )
    def test_recipe_path_emits_slim_manifest(self, lesson_kind, change_type, plan_id, plan_context):
        """End-to-end: recipe inputs → manifest with the documented shape.

        Under the precondition-resolver contract,
        Row 2 (recipe) RETAINS review gates — ``automatic-review`` and
        ``sonar-roundtrip`` are present in the composed manifest. Only the
        legacy ``ci-wait`` step ID is defensively narrowed out when present
        in the candidate list. The recipe contract still produces a slim
        Phase 5 (bounded to quality-gate + module-tests) and retains the
        must-run bookkeeping steps (push, lessons-capture).
        """
        # Sanity: derive_change_type produces the expected change_type.
        assert derive_change_type(lesson_kind) == change_type

        # Inject legacy ci-wait into the candidate list to assert the
        # defensive narrowing still drops it.
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        ns = Namespace(
            plan_id=plan_id,
            change_type=change_type,
            track='complex',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            phase_5_steps='quality-gate,module-tests',
            phase_6_steps=','.join(candidates),
            commit_and_push=None,
        )
        result = cmd_compose(ns)
        assert result is not None and result['status'] == 'success'
        assert result['rule_fired'] == 'recipe', (
            f'lesson_kind={lesson_kind} should fire the recipe rule, not {result["rule_fired"]!r}'
        )

        manifest = read_manifest(plan_id)
        assert manifest is not None

        # Phase 5 keeps the bounded verification set.
        assert manifest['phase_5']['early_terminate'] is False
        for step in manifest['phase_5']['verification_steps']:
            assert step in {'quality-gate', 'module-tests'}, f'unexpected Phase 5 step {step!r} for {lesson_kind}'

        # Phase 6 RETAINS review gates under the new contract.
        phase_6 = manifest['phase_6']['steps']
        for retained in ('automatic-review', 'sonar-roundtrip'):
            assert retained in phase_6, (
                f'recipe path MUST retain {retained!r} under the new contract '
                f'(lesson_kind={lesson_kind})'
            )
        # Legacy ci-wait still defensively narrowed out.
        assert 'ci-wait' not in phase_6, (
            f'recipe path MUST defensively drop legacy ci-wait (lesson_kind={lesson_kind})'
        )
        # And keeps the must-run steps from the recipe contract.
        for required in ('push', 'lessons-capture'):
            assert required in phase_6, f'recipe path must keep {required!r} in Phase 6 (lesson_kind={lesson_kind})'

    def test_recipe_path_takes_precedence_over_surgical_rule(self, plan_context):
        """When recipe_key is set, the recipe rule fires before the surgical rule.

        Both rules would emit a similar slim manifest for surgical+bug_fix /
        surgical+tech_debt, but the recipe rule is the documented source of
        truth for recipe-driven plans. This test pins the rule precedence.
        """
        ns = Namespace(
            plan_id='recipe-precedence-bug',
            change_type='bug_fix',
            track='complex',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=1,
            phase_5_steps='quality-gate,module-tests',
            phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
            commit_and_push=None,
        )
        result = cmd_compose(ns)
        assert result is not None
        assert result['rule_fired'] == 'recipe', (
            f'recipe_key must take precedence over surgical_bug_fix; got {result["rule_fired"]!r}'
        )

    def test_surgical_scope_without_recipe_still_trims_for_bug_fix(self, plan_context):
        """Sanity check: even without recipe_key, surgical+bug_fix defensively
        drops the legacy ``ci-wait`` step ID from Phase 6.

        Under the precondition-resolver contract,
        Row 5 (surgical_bug_fix / surgical_tech_debt) RETAINS the review
        gates — only the legacy ``ci-wait`` step ID is defensively narrowed
        out. The failsafe ensures that a recipe that forgets to set
        ``recipe_key`` still gets the legacy-ID cleanup via Row 5.
        """
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        ns = Namespace(
            plan_id='recipe-surgical-failsafe',
            change_type='bug_fix',
            track='complex',
            scope_estimate='surgical',
            recipe_key=None,  # recipe key intentionally missing
            affected_files_count=1,
            phase_5_steps='quality-gate,module-tests',
            phase_6_steps=','.join(candidates),
            commit_and_push=None,
        )
        result = cmd_compose(ns)
        assert result is not None
        assert result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('recipe-surgical-failsafe')
        assert manifest is not None
        # Review gates RETAINED under the new contract.
        for retained in ('automatic-review', 'sonar-roundtrip'):
            assert retained in manifest['phase_6']['steps']
        # Legacy ci-wait defensively dropped.
        assert 'ci-wait' not in manifest['phase_6']['steps']

    def test_surgical_scope_without_recipe_still_trims_for_tech_debt(self, plan_context):
        """Companion to the bug_fix failsafe: surgical+tech_debt also
        defensively drops the legacy ``ci-wait`` step ID while retaining
        the review gates.

        Uses ``verify:module-tests`` in the phase-5 candidate set so its derived
        ``role: module-tests`` is picked up by Row 5's role intersection
        (``{quality-gate, module-tests}``) alongside ``verify:quality-gate``
        — see manage-execution-manifest decision-rules.md § Role-Field
        Intersection.
        """
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        ns = Namespace(
            plan_id='recipe-surgical-failsafe-td',
            change_type='tech_debt',
            track='complex',
            scope_estimate='surgical',
            recipe_key=None,
            affected_files_count=2,
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(candidates),
            commit_and_push=None,
        )
        result = cmd_compose(ns)
        assert result is not None
        assert result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('recipe-surgical-failsafe-td')
        assert manifest is not None
        # Review gates RETAINED under the new contract.
        for retained in ('automatic-review', 'sonar-roundtrip'):
            assert retained in manifest['phase_6']['steps']
        # Legacy ci-wait defensively dropped.
        assert 'ci-wait' not in manifest['phase_6']['steps']
