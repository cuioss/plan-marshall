#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Shared preamble for the ``remove`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


from pathlib import Path


from _lessons_helpers import _mod


# The verdicts that assert a weaker claim than ``completely_covered`` and
# therefore require no evidence pair. Derived from the production vocabulary so
# a new verdict cannot be added without this test set being reconsidered.
_NON_EVIDENCE_VERDICTS = [v for v in _mod.COVERAGE_VERDICTS if v != _mod.EVIDENCE_REQUIRED_VERDICT]


_CLAUSE = 'manage-lessons/SKILL.md Canonical invocations -> remove'


_INPUT = 'remove --coverage-verdict completely_covered with no --covering-clause'


def _seed_lesson_file(lessons_dir: Path, lesson_id: str) -> Path:
    """Write a minimal, canonically-shaped lesson file and return its path."""
    content = (
        f'id={lesson_id}\n'
        'component=test\n'
        'category=bug\n'
        'status=active\n'
        'created=2025-01-01\n\n'
        f'# {lesson_id} Title\n\nBody.\n'
    )
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(content, encoding='utf-8')
    return path
