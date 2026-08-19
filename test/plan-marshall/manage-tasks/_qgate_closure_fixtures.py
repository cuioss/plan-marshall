#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``qgate closure`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
import os
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT, load_script_module

_closure = load_script_module('plan-marshall', 'manage-tasks', '_qgate_closure.py', '_qgate_closure')


_qgate = load_script_module(
    'plan-marshall', 'manage-tasks', '_cmd_qgate_mechanical.py', '_cmd_qgate_mechanical_closure'
)


check_declared_set_closure = _closure.check_declared_set_closure


check_declared_scope_reconciliation = _closure.check_declared_scope_reconciliation


compute_projection_gaps = _closure.compute_projection_gaps


compute_referrer_gaps = _closure.compute_referrer_gaps


expand_declared_glob = _closure.expand_declared_glob


declared_paths = _closure.declared_paths


normalize_declared_path = _closure.normalize_declared_path


is_glob = _closure.is_glob


cmd_qgate_mechanical = _qgate.cmd_qgate_mechanical


_parsing = load_script_module(
    'plan-marshall', 'manage-solution-outline', '_plan_parsing.py', '_plan_parsing_closure'
)


extract_deliverables = _parsing.extract_deliverables


parse_document_sections = _parsing.parse_document_sections


#: Two real repository files. Paired with ``read``-intent steps (see
#: :func:`_task`), they make ``files_exist`` run its existence predicate and
#: pass, so a closure finding in the same result can never be an existence
#: finding wearing another name.
_REAL_A = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'


_REAL_B = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_qgate_closure.py'


#: A glob whose expansion is stable and small, used for the claim-vs-index
#: cases. Its enumeration is re-derived from the tree at assert time rather
#: than hard-coded, so the test cannot go stale when a file is added.
_STANDARDS_GLOB = 'marketplace/bundles/plan-marshall/skills/manage-tasks/standards/*.md'


#: A glob matching MANY files. Every other glob fixture here expands to exactly
#: one, which cannot exercise a ceiling, a remainder summary, or a truncation
#: disclosure — a fixture set sharing the implementation's scale cannot see a
#: scale defect. Its cardinality is re-derived from the tree at assert time,
#: never written as a literal.
_MULTI_HIT_GLOB = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py'


#: Trees the independent oracle's walk skips — VCS internals, the virtualenv,
#: dependency and build output, caches, and the git-ignored plan state. None of
#: them holds a file any pattern under test targets. Pruning keeps the walk
#: cheap; the exclusion is stated rather than silent because it bounds where the
#: oracle is faithful.
_WALK_PRUNED_DIRS = frozenset({'.git', '.venv', 'node_modules', 'target', '__pycache__', '.plan'})


@lru_cache(maxsize=1)
def _repo_file_index() -> tuple[str, ...]:
    """Every repo-relative file path, walked once per session.

    Cached because :func:`_independent_expansion` is called by several tests and
    a full-tree walk each time dominates the suite's runtime.
    """
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _WALK_PRUNED_DIRS]
        for name in filenames:
            paths.append((Path(dirpath) / name).relative_to(PROJECT_ROOT).as_posix())
    return tuple(sorted(paths))


def _independent_expansion(pattern: str) -> list[str]:
    """Enumerate a pattern's matching files WITHOUT calling ``Path.glob``.

    The production expander is ``repo_root.glob(pattern)``. A test expectation
    computed with that same call agrees with the implementation by construction
    — it cannot disagree, so it verifies nothing about the expansion. This walks
    the tree and matches with :func:`fnmatch` instead, so the two computations
    are genuinely independent and CAN contradict each other.

    ⚠ It is a faithful oracle under TWO stated bounds, both of which every
    caller here satisfies:

    1. The walk prunes :data:`_WALK_PRUNED_DIRS`, so a pattern rooted inside one
       of those trees would see fewer files than ``Path.glob`` does. Every
       caller targets ``marketplace/bundles/…``, which no pruned directory
       contains.
    2. ``fnmatch``'s ``*`` crosses ``/`` while ``Path.glob``'s does not, so the
       two agree only while no SUBDIRECTORY under the pattern's parent holds a
       match. Both patterns used here name a single directory of files
       (``…/standards/*.md``, ``…/scripts/*.py``); a pattern over a nested tree
       would need a different oracle.
    """
    return [rel for rel in _repo_file_index() if fnmatch(rel, pattern)]


def _deliverable(
    number: int,
    *,
    title: str = 'D',
    affected: list[str] | None = None,
    survey: list[str] | None = None,
    mutate: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deliverable record in the shape ``extract_deliverables`` returns."""
    return {
        'number': number,
        'title': title,
        'affected_files': [{'path': p, 'intent': 'write-replace'} for p in (affected or [])],
        'survey_scope': [{'path': p, 'intent': 'read'} for p in (survey or [])],
        'mutation_scope': [{'path': p, 'intent': None} for p in (mutate or [])],
    }


def _task(
    number: int,
    deliverable: int,
    targets: list[str],
    *,
    profile: str = 'implementation',
    title: str = 'T',
    intent: str = 'read',
) -> dict[str, Any]:
    """Build a task record whose steps carry an EXISTENCE-CHECKED intent.

    ``read`` is the default deliberately. ``write-replace`` — the obvious choice
    for a step that edits a file — is the one intent ``files_exist`` skips
    entirely, so a fixture built on it reports ``files_exist: 0`` for absent
    paths just as readily as for present ones, and any test asserting that zero
    would be measuring nothing.
    """
    return {
        'number': number,
        'title': title,
        'profile': profile,
        'deliverable': deliverable,
        'steps': [
            {'number': i + 1, 'target': t, 'intent': intent} for i, t in enumerate(targets)
        ],
    }


# =============================================================================
# End-to-end through the mechanical Q-Gate
# =============================================================================


def _write_task_file(task_dir: Path, task: dict[str, Any]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    record = {
        'number': task['number'],
        'title': task['title'],
        'status': 'pending',
        'profile': task['profile'],
        'domain': 'plan-marshall-plugin-dev',
        'origin': 'plan',
        'deliverable': task['deliverable'],
        'depends_on': [],
        'skills': ['plan-marshall:manage-tasks'],
        'description': '',
        'steps': [{**s, 'status': 'pending'} for s in task['steps']],
        'verification': {'commands': [], 'criteria': '', 'manual': False},
    }
    (task_dir / f'TASK-{task["number"]:03d}.json').write_text(
        json.dumps(record, indent=2), encoding='utf-8'
    )


def _write_outline(plan_dir: Path, body: str) -> None:
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution Outline\n\n## Deliverables\n\n' + body, encoding='utf-8'
    )
