#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Shared preamble for the ``manage lessons main dispatch`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


import sys
from pathlib import Path
import pytest
from conftest import load_script_module
from toon_parser import parse_toon


# Loaded once with a UNIQUE module name so coverage of manage-lessons.py is
# attributed to the real source file without colliding with the
# ``_lessons_helpers`` ``manage_lessons`` registration used by sibling suites.
_mod = load_script_module(
    'plan-marshall', 'manage-lessons', 'manage-lessons.py', 'manage_lessons_main_dispatch'
)


def _run_main(monkeypatch, capsys, argv: list[str]) -> tuple[int, dict]:
    """Invoke ``main()`` in-process with ``argv`` and return (exit_code, toon).

    ``main()`` reads ``sys.argv`` via ``parse_args_with_toon_errors`` and always
    terminates via ``sys.exit`` (``safe_main`` wrapper), so the call is made
    under ``pytest.raises(SystemExit)``. stdout is captured and parsed as TOON;
    an empty stdout (pure argparse-usage failure) yields an empty dict.
    """
    monkeypatch.setattr(sys, 'argv', ['manage-lessons.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    code = exc.value.code if isinstance(exc.value.code, int) else 1
    out = capsys.readouterr().out
    parsed = parse_toon(out) if out.strip() else {}
    return code, parsed


def _seed_lesson(
    base: Path,
    lesson_id: str,
    title: str = 'Seed Title',
    component: str = 'plan-marshall:phase-5-execute',
    category: str = 'bug',
    status: str = 'active',
    body: str = 'Seed body.\n',
) -> Path:
    """Write a canonically-shaped lesson markdown file under the corpus dir."""
    lessons_dir = base / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(
        f'id={lesson_id}\n'
        f'component={component}\n'
        f'category={category}\n'
        f'status={status}\n'
        'created=2025-01-01\n\n'
        f'# {title}\n\n{body}',
        encoding='utf-8',
    )
    return path
