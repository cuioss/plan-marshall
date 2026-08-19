#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``aggregate`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


import importlib.util
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from conftest import MARKETPLACE_ROOT

# Tier 2 direct import — load hyphenated module via importlib.
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-lessons' / 'scripts' / 'manage-lessons.py'


_spec = importlib.util.spec_from_file_location('manage_lessons_aggregate', str(SCRIPT_PATH))


assert _spec is not None and _spec.loader is not None


_mod = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(_mod)


cmd_aggregate = _mod.cmd_aggregate


AGGREGATE_PREVIEW_CHARS = _mod.AGGREGATE_PREVIEW_CHARS


_derive_standards_dir = _mod._derive_standards_dir


MARKETPLACE_BUNDLES_PATH = _mod.MARKETPLACE_BUNDLES_PATH


# =============================================================================
# Test fixture helpers
# =============================================================================


def _seed_lesson(
    lessons_dir: Path,
    lesson_id: str,
    title: str,
    component: str = 'plan-marshall:phase-5-execute',
    body: str = '',
    status: str = 'active',
    extra_metadata: str = '',
) -> Path:
    """Create a lesson markdown file in the canonical on-disk shape.

    The shape mirrors what ``cmd_add`` produces: ``key=value`` frontmatter
    lines, a blank separator line, the ``# {title}`` H1, a blank line, and
    the body content.
    """
    path = lessons_dir / f'{lesson_id}.md'
    frontmatter = (
        f'id={lesson_id}\n'
        f'component={component}\n'
        'category=improvement\n'
        'created=2025-01-01\n'
        f'status={status}\n'
    )
    if extra_metadata:
        frontmatter += extra_metadata
    content = f'{frontmatter}\n# {title}\n\n{body}'
    path.write_text(content, encoding='utf-8')
    return path


def _make_lessons_dir(tmp_path: Path) -> Path:
    """Create the canonical ``lessons-learned/`` subdirectory under tmp_path."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    return lessons_dir


def _run_aggregate(tmp_path: Path, top_n: int = 5) -> dict:
    """Invoke ``cmd_aggregate`` with PLAN_BASE_DIR pointing at tmp_path."""
    with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
        result: dict = cmd_aggregate(Namespace(top_n=top_n))
        return result


def _group_by_primary(result: dict) -> dict[str, dict]:
    """Index ``result['groups']`` by ``primary_id`` for assertion lookup."""
    return {group['primary_id']: group for group in result['groups']}
