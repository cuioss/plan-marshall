# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``check artifact consistency`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for ``check-artifact-consistency.py``.
"""


from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


from _plan_retrospective_fixtures import (  # noqa: E402
    build_happy_plan_dir,
)

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-artifact-consistency.py'
)


def _check_by_name(checks: list, name: str) -> dict | None:
    for c in checks:
        if c.get('name') == name:
            return c
    return None


def _outline_with_deliverable_blocks(blocks: list[list[str] | None]) -> str:
    """Build a multi-deliverable outline mixing per-deliverable declaration states.

    Each entry of ``blocks`` selects the declaration state of the deliverable at
    that position (1-based in the emitted document):

    - a non-empty list — the ``**Affected files:**`` heading followed by one
      backticked bullet per path (a well-formed declaration);
    - an empty list — the heading with NO bullets beneath it (the
      heading-present-but-unparseable, loud-fail shape);
    - ``None`` — no ``**Affected files:**`` heading at all.
    """
    parts = [
        '# Solution: Mixed',
        'plan_id: mixed',
        '',
        '## Summary',
        '',
        'Mixed-declaration fixture.',
        '',
        '## Overview',
        '',
        'Overview.',
        '',
        '## Deliverables',
        '',
    ]
    for index, declared in enumerate(blocks, start=1):
        parts.append(f'### {index}. Deliverable {index}')
        parts.append('')
        if declared is None:
            continue
        parts.append('**Affected files:**')
        parts.extend(f'- `{path}`' for path in declared)
        parts.append('')
    return '\n'.join(parts) + '\n'


def _outline_with_affected_files(
    files: list[str], *, annotation: str | None = None, empty_heading: bool = False
) -> str:
    """Build a solution_outline.md string that declares ``files`` as a single
    deliverable's Affected files bullets. When ``files`` is empty the outline
    still contains a valid Deliverables section but no Affected files block —
    unless ``empty_heading`` is set, which emits the heading with no bullets
    beneath it (the heading-present-but-unparseable, loud-fail shape).

    ``annotation`` selects the bullet form. ``None`` emits the plain backticked
    form ``- `path```; a string emits the canonical annotated form
    ``- `path` (annotation)`` that real solution outlines use.
    """
    suffix = f' ({annotation})' if annotation else ''
    bullets = ''.join(f'- `{p}`{suffix}\n' for p in files)
    if files:
        affected_block = '\n**Affected files:**\n' + bullets
    elif empty_heading:
        affected_block = '\n**Affected files:**\n'
    else:
        affected_block = ''
    return (
        '# Solution: ExactMatch\n'
        'plan_id: exact-match\n\n'
        '## Summary\n\n'
        'Exact-match fixture.\n\n'
        '## Overview\n\n'
        'Overview.\n\n'
        '## Deliverables\n\n'
        '### 1. Deliverable one\n'
        f'{affected_block}'
    )


def _setup_exact_match_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    outline_files: list[str],
    references_files: list[str],
    plan_id: str = 'retro-exact-match',
    outline_annotation: str | None = None,
    outline_empty_heading: bool = False,
) -> tuple[str, Path]:
    """Create a live plan whose outline and references.json are seeded with
    caller-supplied file lists. Reuses ``build_happy_plan_dir`` to keep the
    surrounding structural checks (metrics, tasks, status) green, then
    overwrites the two files the exact-match check consults.

    The ``references.json`` is populated under the ``modified_files`` key
    because the production peer (``check_affected_files_recall``) now
    reads that key; the exact-match port in this branch was realigned to
    use the same key after the base-branch change to recall.
    """
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)

    # Overwrite outline with a variant whose deliverable count matches the
    # default tasks fixture (a single deliverable) so task_deliverable_match
    # does not go red and drown out the check under test.
    (plan_dir / 'solution_outline.md').write_text(
        _outline_with_affected_files(
            outline_files,
            annotation=outline_annotation,
            empty_heading=outline_empty_heading,
        ),
        encoding='utf-8',
    )
    # Trim tasks to a single deliverable to match the outline above.
    tasks_dir = plan_dir / 'tasks'
    for leftover in tasks_dir.glob('TASK-*.json'):
        leftover.unlink()
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'deliverable': 1, 'status': 'done'}),
        encoding='utf-8',
    )

    # Overwrite references.json with the caller's list, keyed on the
    # production-shape ``modified_files`` field (see peer recall check).
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': references_files, 'domains': []}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def _setup_multi_deliverable_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    blocks: list[list[str] | None],
    references_files: list[str],
    plan_id: str,
) -> tuple[str, Path]:
    """Create a live plan whose outline mixes per-deliverable declaration states.

    ``blocks`` is forwarded to :func:`_outline_with_deliverable_blocks`. The
    fixture writes one ``TASK-*.json`` per deliverable so
    ``task_deliverable_match`` stays green and cannot drown out the recall check
    under test — the multi-deliverable counterpart of what
    :func:`_setup_exact_match_plan` does for the single-deliverable case.
    """
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)

    (plan_dir / 'solution_outline.md').write_text(
        _outline_with_deliverable_blocks(blocks), encoding='utf-8'
    )

    tasks_dir = plan_dir / 'tasks'
    for leftover in tasks_dir.glob('TASK-*.json'):
        leftover.unlink()
    for index in range(1, len(blocks) + 1):
        (tasks_dir / f'TASK-{index:03d}.json').write_text(
            json.dumps({'number': index, 'deliverable': index, 'status': 'done'}),
            encoding='utf-8',
        )

    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': references_files, 'domains': []}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def _setup_archived_plan_with_references(tmp_path: Path, references: dict, *, name: str) -> Path:
    """Archived plan built from the happy fixture with ``references`` substituted.

    Archived mode passes ``plan_id=None``, so tier 1 is skipped exactly as it is
    for a real archived plan whose worktree finalize has already removed — which
    makes ``references`` the sole lever over the footprint's resolution state.
    """
    plan_dir = tmp_path / name
    build_happy_plan_dir(plan_dir)
    (plan_dir / 'references.json').write_text(json.dumps(references), encoding='utf-8')
    return plan_dir


def _run_archived(plan_dir: Path):
    return run_script(SCRIPT_PATH, 'run', '--archived-plan-path', str(plan_dir), '--mode', 'archived')


# =============================================================================
# Unit tests for the footprint resolver (_resolve_footprint delegates to the shared
# whole-chain resolver: live diff → realized-footprint capture → merge-commit →
# legacy key → unresolvable). These tests exercise the tier-1/legacy/unresolvable
# endpoints; the capture and merge-commit tiers are covered in test_footprint_resolver.py.
# =============================================================================

import importlib.util  # noqa: E402
import subprocess  # noqa: E402


def _load_check_module():
    spec = importlib.util.spec_from_file_location('_check_artifact_under_test', SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_check_mod = _load_check_module()


# ``_resolve_footprint`` now delegates to the shared ``_footprint_resolver`` module,
# which is where ``resolve_live_worktree`` is looked up — so tier-1 stubs patch THAT
# module (the same instance ``_check_mod`` imported), not ``_check_mod`` itself.
_fr_mod = sys.modules['_footprint_resolver']


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-b', 'main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test')
