# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``check artifact consistency behavior`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

In-process behavioral tests for ``check-artifact-consistency.py``.

The existing ``test_check_artifact_consistency.py`` drives the script through
the ``run_script`` subprocess harness (which exercises the real argparse path
but does not count for in-process coverage) plus a handful of direct
``_resolve_footprint`` unit calls. This module complements it by calling
``cmd_run`` and the individual ``check_*`` analyzers IN-PROCESS against crafted
``tmp_path`` plan directories, asserting the structural verdicts each branch
produces — including the manifest-aware downgrade branch, the task/recall/
exact-match edge cases, and the ``resolve_plan_dir`` error paths that the
subprocess suite never reaches in-process.
"""


from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

# Unique module name so this in-process load never collides with the
# ``_check_artifact_under_test`` instance the sibling subprocess suite loads.
_cac = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-artifact-consistency.py', 'cac_behavior_mod'
)


# The FOOTPRINT_UNRESOLVED sentinel now lives in the shared ``_footprint_resolver``
# module (the same instance ``_cac`` imported), which is its canonical home.
_fr = sys.modules['_footprint_resolver']


# Markdown fragments shaped like the production solution_outline.md the
# retrospective parses. ``parse_document_sections`` lowercases ``## Heading``
# names, and ``extract_affected_files_per_deliverable`` collects bullets under
# each ``**Affected files:**`` block.
def _outline(
    deliverables: int = 1,
    affected: list[str] | None = None,
    *,
    annotation: str | None = None,
    empty_affected_heading: bool = False,
) -> str:
    """Build an outline fragment.

    ``annotation`` selects the ``Affected files:`` bullet form: ``None`` emits
    the plain backticked ``- `path``` form, a string emits the canonical
    annotated ``- `path` (annotation)`` form real outlines use.

    ``empty_affected_heading`` emits deliverable 1 with the
    ``**Affected files:**`` heading and NO bullets beneath it — the loud-fail
    shape. It is independent of the heading-absent shape (the default, where
    the deliverable carries no ``Affected files`` heading at all), so the two
    branches of the per-deliverable rule can be pinned separately.
    """
    suffix = f' ({annotation})' if annotation else ''
    parts = [
        '# Solution: Behavior',
        '',
        '## Summary',
        '',
        'A crafted plan.',
        '',
        '## Overview',
        '',
        'Overview prose.',
        '',
        '## Deliverables',
        '',
    ]
    for i in range(1, deliverables + 1):
        parts.append(f'### {i}. Deliverable {i}')
        parts.append('')
        if affected and i == 1:
            parts.append('**Affected files:**')
            parts.extend(f'- `{p}`{suffix}' for p in affected)
            parts.append('')
        elif empty_affected_heading and i == 1:
            # Heading present, zero bullets beneath it — the loud-fail shape.
            parts.append('**Affected files:**')
            parts.append('')
    return '\n'.join(parts) + '\n'


def _run_args(plan_dir: Path) -> Namespace:
    """Build the archived-mode ``argparse.Namespace`` ``cmd_run`` consumes."""
    return Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
    )


def _check(checks: list[dict], name: str) -> dict | None:
    return next((c for c in checks if c.get('name') == name), None)


_ONE_DELIVERABLE = [{'number': '1', 'title': 'Deliverable 1'}]


def _build_consistent_plan(plan_dir: Path, affected: list[str]) -> None:
    """Write a structurally-complete plan directory whose checks all pass."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'solution_outline.md').write_text(_outline(affected=affected), encoding='utf-8')
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': affected}), encoding='utf-8'
    )
    (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
    tasks = plan_dir / 'tasks'
    tasks.mkdir()
    (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')


def _recall_verdict(result: dict) -> tuple[str, str]:
    """Return ``(check_status, finding_severity)`` for ``affected_files_recall``.

    The finding is paired to the check by the check's OWN message rather than by
    a substring literal, so the pairing survives a message rewording and can
    never latch onto the exact-match peer's finding by accident.
    """
    recall = _check(result['checks'], 'affected_files_recall')
    assert recall is not None, 'cmd_run must always emit the affected_files_recall check'
    severities = [f['severity'] for f in result['findings'] if f['message'] == recall['message']]
    assert len(severities) == 1, (
        f'Expected exactly one finding raised by affected_files_recall '
        f'({recall["message"]!r}), got {severities!r} from {result["findings"]!r}'
    )
    return recall['status'], severities[0]
