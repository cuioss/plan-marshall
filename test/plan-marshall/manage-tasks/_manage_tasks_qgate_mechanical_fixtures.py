#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage tasks qgate mechanical`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks.

The subcommand runs the deterministic Q-Gate checks over the tasks and parent
deliverables of a plan, emitting one finding per failure under ``--source
qgate`` so the existing phase-4-plan aggregate consumes them without
modification. The check names those tests assert against are enumerated once here, in
:data:`_ALL_CHECKS`, and read from the result rather than restated per test.

The CLOSURE checks (``declared_set_closure``,
``declared_scope_reconciliation``) have their own suite in
``test_qgate_closure*.py``; here they are exercised only as members of the full
result — a fixture in this file must be a well-formed plan except for the one
fault the test injects.
"""


from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT

#: A real repository file, used as BOTH the declared path and the step target
#: in every fixture that is not deliberately injecting a fault. Declaring one
#: path while targeting another leaves the plan's declared set unclosed, which
#: the declared_set_closure check now reports — correctly. The corpus is aligned
#: rather than exempted: a fixture that quietly carried an unclosed set would
#: pin that shape as expected behaviour, which is how a characterization corpus
#: turns a latent defect into a green test certifying it.
_EXISTING_FILE = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'


_MISSING_FILE = 'src/does-not-exist.java'


#: Every check the subcommand reports. Named here once, and cross-checked
#: against the live result's own key set so a check added to the script without
#: a corresponding entry here fails loudly instead of going unasserted — a
#: hard-coded name list silently stops covering whatever is added after it.
_ALL_CHECKS = (
    'coverage',
    'skill_resolution',
    'acyclic',
    'files_exist',
    'keyword_drift',
    'structural_token_drift',
    'declared_set_closure',
    'declared_scope_reconciliation',
)


# Load the cmd module via importlib (mirrors the batch-add test bootstrap).
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_qgate_mod = _load_module('_cmd_qgate_mechanical_under_test', '_cmd_qgate_mechanical.py')


cmd_qgate_mechanical = _qgate_mod.cmd_qgate_mechanical


def _ns(plan_id: str, no_emit: bool = True) -> Namespace:
    return Namespace(plan_id=plan_id, no_emit=no_emit)


# =============================================================================
# Fixture builders
# =============================================================================


def _write_task(
    task_dir: Path,
    number: int,
    *,
    title: str = 'Task',
    deliverable: int = 1,
    domain: str = 'java',
    profile: str = 'implementation',
    skills: list[str] | None = None,
    steps: list[dict[str, Any]] | None = None,
    depends_on: list[str] | None = None,
    description: str = '',
) -> Path:
    """Write a TASK-NNN.json file directly (bypasses validators).

    Tests use this to seed both legal and intentionally-malformed inputs so
    every mechanical check has at least one positive and one negative case.
    """
    task_dir.mkdir(parents=True, exist_ok=True)
    raw_steps = steps or [{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}]
    # intent is a required step member; default omitting fixtures to 'read'
    # (existence-required) so legacy files_exist cases keep their semantics.
    normalized_steps = [
        ({'intent': 'read', **s} if isinstance(s, dict) else s) for s in raw_steps
    ]
    record = {
        'number': number,
        'title': title,
        'status': 'pending',
        'profile': profile,
        'domain': domain,
        'origin': 'plan',
        'deliverable': deliverable,
        'depends_on': depends_on or [],
        'skills': skills or [],
        'description': description,
        'steps': normalized_steps,
        'verification': {'commands': [], 'criteria': '', 'manual': False},
    }
    path = task_dir / f'TASK-{number:03d}.json'
    path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    return path


def _write_outline(plan_dir: Path, deliverables: list[dict[str, Any]]) -> None:
    """Write a minimal solution_outline.md with the given deliverables.

    An ``affected_files`` entry may be a bare path or a ``path (intent)`` string;
    the marker is emitted OUTSIDE the backticks, in the canonical annotated form
    the parser reads. Fixtures need it to declare a read-only path, which owes no
    task step and so keeps a single-fault fixture single-fault.
    """
    lines: list[str] = ['# Solution Outline', '', '## Deliverables', '']
    for d in deliverables:
        lines.append(f'### {d["number"]}. {d["title"]}')
        lines.append('')
        if 'affected_files' in d:
            lines.append('**Affected files:**')
            for f in d['affected_files']:
                path, _, marker = str(f).partition(' (')
                lines.append(f'- `{path}` ({marker}' if marker else f'- `{path}`')
            lines.append('')
        if 'metadata' in d:
            lines.append('**Metadata:**')
            for k, v in d['metadata'].items():
                lines.append(f'- {k}: {v}')
            lines.append('')
    (plan_dir / 'solution_outline.md').write_text('\n'.join(lines), encoding='utf-8')


# =============================================================================
# Files-exist check
# =============================================================================

def _files_exist_failed(plan_context, slug, target, intent):
    """Seed one task with a single (target, intent) step and return failed count."""
    plan_dir = plan_context.plan_dir_for(slug)
    _write_outline(plan_dir, [{'number': 1, 'title': 'X', 'affected_files': [target]}])
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': target, 'status': 'pending', 'intent': intent}],
    )
    result = cmd_qgate_mechanical(_ns(slug))
    return result['checks']['files_exist']['failed']


# =============================================================================
# Rejected persist (P3) — a rejection never lands in the no-op bucket
# =============================================================================


def _seed_one_coverage_failure(plan_context, slug: str) -> Path:
    """Seed a plan whose only mechanical failure is one uncovered deliverable."""
    plan_dir: Path = plan_context.plan_dir_for(slug)
    _write_outline(
        plan_dir,
        [
            {'number': 1, 'title': 'Has tasks', 'affected_files': [_EXISTING_FILE]},
            {'number': 2, 'title': 'No tasks', 'affected_files': ['src/B.java (read)']},
        ],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )
    return plan_dir
