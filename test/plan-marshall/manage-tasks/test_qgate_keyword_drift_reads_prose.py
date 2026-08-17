#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The keyword-drift haystack includes the deliverable's own prose body.

The check asks whether a task description says something its parent deliverable
does not. A deliverable says things in prose — the intent gloss, the
change-per-file narrative, the success criteria — not only in its structured
fields, so a haystack assembled from title + metadata + profiles + affected files
+ verification alone answered a narrower question than the one being asked: a
task faithfully quoting its own deliverable's analysis was reported as drift.

That narrowness was also a disagreement between siblings. The
structural-token-drift recipe already reads the whole deliverable body, so the
two checks did not mean the same thing by "the deliverable".

Each case below places the keyword ONLY in the prose. A haystack that skips the
prose reaches the opposite verdict on every one of them.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_qgate_mod = _load_module('_cmd_qgate_mechanical_prose_haystack', '_cmd_qgate_mechanical.py')
cmd_qgate_mechanical = _qgate_mod.cmd_qgate_mechanical
_build_haystack = _qgate_mod._build_haystack

#: A real repository path, so the unrelated files-exist check stays green and
#: cannot be mistaken for the keyword-drift verdict under test.
EXISTING_FILE = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'


def _write_outline_with_prose(plan_dir: Path, prose: str) -> None:
    """Write an outline whose single deliverable carries a prose body.

    The structured fields deliberately mention no planning vocabulary, so the
    only place a keyword can be found is the prose.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution Outline\n\n'
        '## Deliverables\n\n'
        '### 1. Harden the gate\n\n'
        f'{prose}\n\n'
        '**Affected files:**\n'
        f'- `{EXISTING_FILE}` (write-replace)\n\n'
        '**Metadata:**\n'
        '- change_type: enhancement\n',
        encoding='utf-8',
    )


def _write_task(plan_dir: Path, description: str) -> None:
    task_dir = plan_dir / 'tasks'
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / 'TASK-001.json').write_text(
        json.dumps(
            {
                'number': 1,
                'title': 'Task',
                'status': 'pending',
                'profile': 'implementation',
                'domain': 'python',
                'origin': 'plan',
                'deliverable': 1,
                'depends_on': [],
                'skills': ['plan-marshall:manage-tasks'],
                'description': description,
                'steps': [
                    {
                        'number': 1,
                        'target': EXISTING_FILE,
                        'status': 'pending',
                        'intent': 'read',
                    }
                ],
                'verification': {'commands': [], 'criteria': '', 'manual': False},
            },
            indent=2,
        ),
        encoding='utf-8',
    )


class TestHaystackIncludesProse:
    """``_build_haystack`` folds the deliverable body in alongside the fields."""

    def test_prose_text_reaches_the_haystack(self):
        deliverable = {'title': 'Harden the gate', 'affected_files': []}

        haystack = _build_haystack(deliverable, 'Re-run the CI pipeline after each push.')

        assert 'CI pipeline' in haystack

    def test_absent_prose_still_yields_the_structured_haystack(self):
        """The prose argument is additive — omitting it removes nothing."""
        deliverable = {'title': 'Harden the gate', 'affected_files': ['a.py']}

        haystack = _build_haystack(deliverable)

        assert 'Harden the gate' in haystack
        assert 'a.py' in haystack


def test_keyword_present_only_in_prose_is_not_flagged(plan_context):
    """The positive arm: the deliverable's prose names the keyword, the fields do not."""
    plan_dir = Path(plan_context.plan_dir_for('qgate-prose-ok'))
    _write_outline_with_prose(
        plan_dir,
        'The gate currently re-runs on every push, so the CI pipeline is the '
        'surface this deliverable hardens.',
    )
    _write_task(plan_dir, "'Harden the gate'. Tighten the CI pipeline trigger.")

    result = cmd_qgate_mechanical(Namespace(plan_id='qgate-prose-ok', no_emit=True))

    assert result['checks']['keyword_drift']['failed'] == 0, (
        'a task quoting its own deliverable prose was reported as drift'
    )


def test_heading_less_deliverables_section_is_unparseable(plan_context):
    """A Deliverables section with no `### N.` heading must not read as parseable.

    ``extract_deliverables`` returns an empty list for it, and every downstream
    check then passes vacuously — coverage finds nothing uncovered, keyword-drift
    finds no drift — while ``ambiguous`` stays False and reports the mechanical
    pass as authoritative. An outline nobody could parse has to reach the LLM
    dispatch instead of receiving a clean bill of health.
    """
    plan_dir = Path(plan_context.plan_dir_for('qgate-no-headings'))
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution Outline\n\n## Deliverables\n\nProse with no numbered heading.\n',
        encoding='utf-8',
    )
    _write_task(plan_dir, "'Something'. Tighten the CI pipeline trigger.")

    result = cmd_qgate_mechanical(Namespace(plan_id='qgate-no-headings', no_emit=True))

    assert result['ambiguous'] is True, (
        'an unparseable outline was reported as an authoritative mechanical pass'
    )


def test_keyword_absent_everywhere_is_still_flagged(plan_context):
    """The paired negative: the same task text over a deliverable that never says it.

    Changing only the prose flips the verdict, so the positive arm above is
    carried by the prose and not by a check that stopped firing.
    """
    plan_dir = Path(plan_context.plan_dir_for('qgate-prose-drift'))
    _write_outline_with_prose(
        plan_dir,
        'The gate currently re-runs on every push, so the trigger condition is '
        'the surface this deliverable hardens.',
    )
    _write_task(plan_dir, "'Harden the gate'. Tighten the CI pipeline trigger.")

    result = cmd_qgate_mechanical(Namespace(plan_id='qgate-prose-drift', no_emit=True))

    assert result['checks']['keyword_drift']['failed'] > 0, (
        'a keyword absent from every part of the deliverable was not flagged'
    )
