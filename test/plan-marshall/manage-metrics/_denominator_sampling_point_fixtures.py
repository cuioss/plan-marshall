#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``denominator sampling point`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the persisted denominators and their sampling-point discriminator.

``metrics.toon`` otherwise persists NUMERATORS only, so a script reading it
supports exactly one verdict: "this got more expensive". Every denominator a
ratio needs lived outside the record and was re-derived at render time — a
figure nobody can check.

Each denominator is also a MOVING quantity (``affected_files`` grows during
execute, the task count grows as triage appends fix-tasks, the deliverable count
can change on a Q-Gate re-entry), so the same numerator over the same plan
yields a different ratio depending on WHEN the denominator was read. That is why
these tests pin the PAIR — count plus ``{denominator}_sampling_point`` — and why
the absent case is pinned as hard as the present one: a denominator whose source
cannot be read is absent from the record, never a guessed ``0``.
"""


import importlib.util
import json
import re
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, parse_ns

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')


# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics_denominators', SCRIPT_PATH)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


cmd_generate = manage_metrics.cmd_generate


# The SIBLING producer of the same count. Loaded as the real command function so
# the agreement test exercises `manage-solution-outline list-deliverables`
# end-to-end (`extract_deliverables` → `split_deliverable_blocks`) rather than
# re-evaluating the metrics side's own expression.
_OUTLINE_SCRIPT_PATH = get_script_path('plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py')


_outline_spec = importlib.util.spec_from_file_location('manage_solution_outline_denominators', _OUTLINE_SCRIPT_PATH)


assert _outline_spec is not None and _outline_spec.loader is not None


manage_solution_outline = importlib.util.module_from_spec(_outline_spec)


_outline_spec.loader.exec_module(manage_solution_outline)


cmd_list_deliverables = manage_solution_outline.cmd_list_deliverables


def ns_list_deliverables(plan_id: str) -> Namespace:
    """A ``list-deliverables`` namespace from manage-solution-outline.py's parser.

    The handler under test belongs to ``manage-solution-outline``, not to
    ``manage-metrics``, so the namespace comes from that script's parser.
    """
    parsed: Namespace = parse_ns(
        'plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py',
        'list-deliverables', '--plan-id', plan_id,
    )
    return parsed


def _recorded_row() -> dict:
    """A closed phase row — enough for `generate` to produce a report."""
    return {
        'start_time': '2020-01-01T00:00:00+00:00',
        'end_time': '2020-01-01T00:10:00+00:00',
        'duration_seconds': 600,
        'total_tokens': 1000,
    }


def _seed_phases(plan_id: str) -> Path:
    """Materialise the plan directory with a closed six-phase metrics.toon.

    ``status.json`` is seeded because ``cmd_generate``'s ``_guard_plan_exists``
    refuses a plan directory without one — and a refused generate writes
    nothing, which would make every denominator assertion fail for a
    reason unrelated to denominators.
    """
    phases = {name: _recorded_row() for name in manage_metrics.PHASE_NAMES}
    manage_metrics.write_metrics(plan_id, {'phases': phases})
    plan_dir = Path(manage_metrics.get_plan_dir(plan_id))
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    return plan_dir


def _write_outline(plan_dir: Path, deliverables: int) -> None:
    """Write a solution_outline.md carrying *deliverables* countable headings.

    The headings live under a ``## Deliverables`` H2, which is where the
    solution-outline standard puts them and the only place the authoritative
    extractor looks. Two decoys are written into every fixture so the count is
    never satisfied by a laxer grammar: a bare ``### Notes`` (level-3 but not
    numbered) inside the section, and a fully well-formed ``### 99. Decoy``
    under a DIFFERENT H2 — the out-of-section case that a whole-file scan
    counts and the authoritative extractor does not.
    """
    lines = ['# Solution: fixture', '', '## Deliverables', '']
    for index in range(1, deliverables + 1):
        lines.append(f'### {index}. Deliverable {index}')
        lines.append('')
        lines.append('### Notes')
        lines.append('')
    lines += ['## Approach', '', '### 99. Decoy heading outside Deliverables', '']
    (plan_dir / 'solution_outline.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _write_references(plan_dir: Path, files: list[str]) -> None:
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'affected_files': files}), encoding='utf-8'
    )


def _write_tasks(plan_dir: Path, statuses: list[str]) -> None:
    tasks = plan_dir / 'tasks'
    tasks.mkdir(parents=True, exist_ok=True)
    for index, status in enumerate(statuses, start=1):
        (tasks / f'TASK-{index:03d}.json').write_text(
            json.dumps({'number': index, 'status': status}), encoding='utf-8'
        )


# =============================================================================
# One deliverable grammar, not two producers of one number
# =============================================================================

# The grammar `_count_deliverables` used to carry privately: unscoped to any
# section, and satisfied by a numbered heading with no title at all.
_RETIRED_WHOLE_FILE_RE = re.compile(r'^###\s+\d+\.\s')


# Outlines chosen so that retired grammar and the authoritative section-scoped
# extractor give DIFFERENT answers. If `_count_deliverables` ever reverts to a
# private grammar, the agreement assertion fails on these — which is what
# makes it non-vacuous.
_DIVERGENT_OUTLINES = {
    'numbered-heading-under-approach': (
        '# Solution: fixture\n\n'
        '## Deliverables\n\n'
        '### 1. Real deliverable\n\n'
        '## Approach\n\n'
        '### 2. Not a deliverable\n'
    ),
    'numbered-heading-inside-a-fenced-example': (
        '# Solution: fixture\n\n'
        '## Deliverables\n\n'
        '### 1. Real deliverable\n\n'
        '## Notes\n\n'
        'Deliverable headings look like this:\n\n'
        '```markdown\n'
        '### 7. Example heading in a fenced block\n'
        '```\n'
    ),
    'degenerate-heading-with-no-title': (
        '# Solution: fixture\n\n'
        '## Deliverables\n\n'
        '### 1. Real deliverable\n\n'
        '### 2. \n'
    ),
    'headings-only-outside-the-section': (
        '# Solution: fixture\n\n## Approach\n\n### 1. Not a deliverable\n'
    ),
}
