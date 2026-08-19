#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``recipe lesson cleanup`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


import importlib.util
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

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
_mem._log_decision = lambda *a, **kw: None


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
            f"Lesson kind '{lesson_kind}' is not mapped — supported: {sorted(LESSON_KIND_TO_CHANGE_TYPE.keys())}"
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
