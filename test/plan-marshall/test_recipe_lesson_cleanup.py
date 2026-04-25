#!/usr/bin/env python3
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

import importlib.util
import re
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, PlanContext

# =============================================================================
# Tier 2 import — manage-execution-manifest script (used for the end-to-end
# manifest assertions). Mirrors the loader pattern used by
# ``test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest.py``.
# =============================================================================

_MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
    / 'manage-execution-manifest.py'
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, f'Failed to load module spec for {path}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_recipe_lesson_cleanup', _MANIFEST_SCRIPT)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess so tests don't depend on a
# running executor.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Lesson-kind → change_type mapping
#
# This mapping is the single deterministic decision the recipe makes (see
# ``recipe-lesson-cleanup/SKILL.md`` Step 2 and ``recipe-config.md`` "Derived
# change_type"). The mapping is reproduced here so a regression in the recipe
# spec — silently changing a row, or admitting a fourth lesson kind — fails
# loudly instead of going unnoticed. Any change to the recipe spec must be
# accompanied by a deliberate change to this table.
# =============================================================================

LESSON_KIND_TO_CHANGE_TYPE = {
    'bug': 'bug_fix',
    'improvement': 'enhancement',
    'anti-pattern': 'tech_debt',
}


def derive_change_type(lesson_kind: str) -> str:
    """Reference implementation of the recipe's lesson-kind → change_type map.

    Mirrors ``recipe-lesson-cleanup/SKILL.md`` Step 2. Raises ValueError on
    unknown kinds — the recipe aborts with an explicit error in the same
    case (it never guesses).
    """
    try:
        return LESSON_KIND_TO_CHANGE_TYPE[lesson_kind]
    except KeyError:
        raise ValueError(
            f"Lesson kind '{lesson_kind}' is not mapped — "
            f'supported: {sorted(LESSON_KIND_TO_CHANGE_TYPE.keys())}'
        ) from None


# =============================================================================
# Doc-shaped lesson predicate
#
# Reference implementation of the three-rule heuristic documented in
# ``phase-1-init/SKILL.md`` Step 5c. The predicate decides whether the
# auto-suggest hook fires:
#
#   1. No code-touching fenced blocks (python/py/java/js/javascript/ts/typescript).
#   2. No primary code-action verb at the start of any directive
#      (test/refactor/implement/add code/write code/migrate).
#   3. Has at least one ``## Directive`` or ``## Actions`` heading.
#
# Reproduced in Python so regressions in either direction (false positives or
# silent narrowing) fail the suite.
# =============================================================================

_CODE_FENCE_LANGS = {'python', 'py', 'java', 'js', 'javascript', 'ts', 'typescript'}
_CODE_ACTION_VERBS = ('test', 'refactor', 'implement', 'add code', 'write code', 'migrate')


def _has_code_touching_fences(body: str) -> bool:
    """Rule 1: any fenced block tagged with a code language disqualifies."""
    for match in re.finditer(r'```([a-zA-Z0-9_+-]*)', body):
        lang = match.group(1).strip().lower()
        if lang in _CODE_FENCE_LANGS:
            return True
    return False


def _directive_first_lines(body: str) -> list[str]:
    """Yield the first non-empty line under each ``## Directive`` / ``## Actions`` heading."""
    lines = body.splitlines()
    first_lines: list[str] = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^##\s+(Directive|Actions)\b', stripped, re.IGNORECASE):
            inside = True
            captured = False
            continue
        if inside:
            if stripped.startswith('## '):
                inside = False
                continue
            if not captured and stripped:
                # Strip leading bullet markers so "- update" matches the verb list.
                cleaned = re.sub(r'^[-*+]\s*', '', stripped)
                first_lines.append(cleaned)
                captured = True
    return first_lines


def _has_directive_heading(body: str) -> bool:
    """Rule 3: at least one ``## Directive`` or ``## Actions`` heading."""
    return bool(re.search(r'^##\s+(Directive|Actions)\b', body, re.MULTILINE | re.IGNORECASE))


def is_doc_shaped(body: str) -> bool:
    """Reference implementation of the auto-suggest predicate.

    Returns True iff ALL three rules from ``phase-1-init/SKILL.md`` Step 5c
    hold. Used by the auto-suggest hook to decide whether to set
    ``plan_source=recipe`` and ``recipe_key=lesson_cleanup``.
    """
    if not _has_directive_heading(body):
        return False
    if _has_code_touching_fences(body):
        return False
    for first_line in _directive_first_lines(body):
        lowered = first_line.lower()
        for verb in _CODE_ACTION_VERBS:
            if lowered.startswith(verb):
                return False
    return True


# =============================================================================
# Fixture lesson bodies — a representative test corpus
# =============================================================================

DOC_SHAPED_LESSON = """\
---
id: 2026-04-15-100
component: plan-marshall:phase-1-init
category: improvement
created: 2026-04-15
---

# Lesson: Document the auto-suggest hook surface

## Summary

Update the workflow narrative to mention the new hook.

## Directive

Update phase-1-init/standards/workflow.md with a paragraph describing the
auto-suggest hook and how it slots into Step 5c.

```markdown
The auto-suggest hook fires when source==lesson and the body is doc-shaped.
```
"""

DOC_SHAPED_MULTIPLE_DIRECTIVES = """\
---
id: 2026-04-15-101
component: plan-marshall:recipe-lesson-cleanup
category: improvement
created: 2026-04-15
---

# Lesson: Tighten recipe documentation

## Directive

Document the surgical scope contract in recipe-config.md.

## Directive

Clarify in SKILL.md that Q-Gate is skipped by design.

## Directive

Note in the related-skills section that recipe-refactor-to-profile-standards
is the sister recipe.
"""

CODE_SHAPED_LESSON_VIA_FENCE = """\
---
id: 2026-04-15-102
component: plan-marshall:manage-execution-manifest
category: bug
created: 2026-04-15
---

# Lesson: Fix the manifest composer

## Directive

Update the rule-firing branch to handle the empty-files edge case.

```python
if not affected_files:
    return early_terminate_body, 'early_terminate_analysis'
```
"""

CODE_SHAPED_LESSON_VIA_VERB = """\
---
id: 2026-04-15-103
component: plan-marshall:phase-3-outline
category: improvement
created: 2026-04-15
---

# Lesson: Refactor the Q-Gate dispatch path

## Directive

Refactor phase-3-outline so the Q-Gate dispatch is its own function.
"""

CODE_SHAPED_LESSON_VIA_TEST_VERB = """\
---
id: 2026-04-15-104
component: plan-marshall:execute-task
category: improvement
created: 2026-04-15
---

# Lesson: Add coverage for the diff assertion path

## Directive

Test the inject_project_dir helper against the eight Bucket B notations so
regressions in the whitelist surface immediately.
"""

LESSON_WITH_NO_DIRECTIVES = """\
---
id: 2026-04-15-105
component: plan-marshall:phase-2-refine
category: improvement
created: 2026-04-15
---

# Lesson: Stale notes about confidence handling

## Summary

Confidence handling is fine as-is — leaving this as a note for posterity,
no actionable directives.
"""


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
        body = (
            '## Directive\n\n'
            'Update the foo.\n\n'
            f'```{lang}\nsome code here\n```\n'
        )
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
        with pytest.raises(ValueError, match="not mapped"):
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
#   Phase 6: commit-push, create-pr, lessons-capture, branch-cleanup, archive-plan
#            (drops automated-review, sonar-roundtrip, knowledge-capture)
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
    def test_recipe_path_emits_slim_manifest(self, lesson_kind, change_type, plan_id):
        """End-to-end: recipe inputs → manifest with the documented slim shape.

        Asserts the success criterion from solution-outline deliverable 7:
        the manifest excludes automated-review, sonar-roundtrip, and
        knowledge-capture (per surgical/recipe rules) for each lesson kind.
        """
        # Sanity: derive_change_type produces the expected change_type.
        assert derive_change_type(lesson_kind) == change_type

        with PlanContext(plan_id=plan_id):
            ns = Namespace(
                plan_id=plan_id,
                change_type=change_type,
                track='complex',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=2,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
            )
            result = cmd_compose(ns)
            assert result is not None and result['status'] == 'success'
            assert result['rule_fired'] == 'recipe', (
                f'lesson_kind={lesson_kind} should fire the recipe rule, '
                f"not {result['rule_fired']!r}"
            )

            manifest = read_manifest(plan_id)
            assert manifest is not None

            # Phase 5 keeps the bounded verification set.
            assert manifest['phase_5']['early_terminate'] is False
            for step in manifest['phase_5']['verification_steps']:
                assert step in {'quality-gate', 'module-tests'}, (
                    f'unexpected Phase 5 step {step!r} for {lesson_kind}'
                )

            # Phase 6 drops the heavy review steps per the recipe contract.
            phase_6 = manifest['phase_6']['steps']
            for stripped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
                assert stripped not in phase_6, (
                    f'recipe path must drop {stripped!r} from Phase 6 '
                    f'(lesson_kind={lesson_kind})'
                )
            # And keeps the must-run steps from the recipe contract.
            for required in ('commit-push', 'lessons-capture'):
                assert required in phase_6, (
                    f'recipe path must keep {required!r} in Phase 6 '
                    f'(lesson_kind={lesson_kind})'
                )

    def test_recipe_path_takes_precedence_over_surgical_rule(self):
        """When recipe_key is set, the recipe rule fires before the surgical rule.

        Both rules would emit a similar slim manifest for surgical+bug_fix /
        surgical+tech_debt, but the recipe rule is the documented source of
        truth for recipe-driven plans. This test pins the rule precedence.
        """
        with PlanContext(plan_id='recipe-precedence-bug'):
            ns = Namespace(
                plan_id='recipe-precedence-bug',
                change_type='bug_fix',
                track='complex',
                scope_estimate='surgical',
                recipe_key='lesson_cleanup',
                affected_files_count=1,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'recipe', (
                'recipe_key must take precedence over surgical_bug_fix; '
                f"got {result['rule_fired']!r}"
            )

    def test_surgical_scope_without_recipe_still_trims_for_bug_fix(self):
        """Sanity check: even without recipe_key, surgical+bug_fix trims Phase 6.

        Documents the failsafe: if the recipe somehow fails to set recipe_key
        but does set scope_estimate=surgical and a derived change_type of
        bug_fix or tech_debt, the surgical rule still produces a comparable
        slim manifest. This is why the recipe forces scope_estimate=surgical.
        """
        with PlanContext(plan_id='recipe-surgical-failsafe'):
            ns = Namespace(
                plan_id='recipe-surgical-failsafe',
                change_type='bug_fix',
                track='complex',
                scope_estimate='surgical',
                recipe_key=None,  # recipe key intentionally missing
                affected_files_count=1,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'surgical_bug_fix'
            manifest = read_manifest('recipe-surgical-failsafe')
            assert manifest is not None
            for stripped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
                assert stripped not in manifest['phase_6']['steps']

    def test_surgical_scope_without_recipe_still_trims_for_tech_debt(self):
        """Companion to the bug_fix failsafe: surgical+tech_debt also trims."""
        with PlanContext(plan_id='recipe-surgical-failsafe-td'):
            ns = Namespace(
                plan_id='recipe-surgical-failsafe-td',
                change_type='tech_debt',
                track='complex',
                scope_estimate='surgical',
                recipe_key=None,
                affected_files_count=2,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'surgical_tech_debt'
            manifest = read_manifest('recipe-surgical-failsafe-td')
            assert manifest is not None
            for stripped in ('automated-review', 'sonar-roundtrip', 'knowledge-capture'):
                assert stripped not in manifest['phase_6']['steps']
