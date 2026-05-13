#!/usr/bin/env python3
"""Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks.

The subcommand runs six deterministic Q-Gate checks (coverage,
skill-resolution, acyclic, files-exist, keyword-drift,
structural-token-drift) over the tasks and parent deliverables of a
plan, emitting one finding per failure under ``--source qgate`` so the
existing phase-4-plan aggregate consumes them without modification.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from conftest import PROJECT_ROOT, PlanContext

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
        'steps': steps or [{'number': 1, 'target': 'src/A.java', 'status': 'pending'}],
        'verification': {'commands': [], 'criteria': '', 'manual': False},
    }
    path = task_dir / f'TASK-{number:03d}.json'
    path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    return path


def _write_outline(plan_dir: Path, deliverables: list[dict[str, Any]]) -> None:
    """Write a minimal solution_outline.md with the given deliverables."""
    lines: list[str] = ['# Solution Outline', '', '## Deliverables', '']
    for d in deliverables:
        lines.append(f'### {d["number"]}. {d["title"]}')
        lines.append('')
        if 'affected_files' in d:
            lines.append('**Affected files:**')
            for f in d['affected_files']:
                lines.append(f'- `{f}`')
            lines.append('')
        if 'metadata' in d:
            lines.append('**Metadata:**')
            for k, v in d['metadata'].items():
                lines.append(f'- {k}: {v}')
            lines.append('')
    (plan_dir / 'solution_outline.md').write_text('\n'.join(lines), encoding='utf-8')


# =============================================================================
# Smoke / happy-path
# =============================================================================


def test_qgate_mechanical_clean_plan_passes_all_checks():
    """A consistent plan with two deliverables × one task each reports zero failures."""
    with PlanContext(plan_id='qgate-clean') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [
                {'number': 1, 'title': 'Add foo', 'affected_files': ['src/A.java']},
                {'number': 2, 'title': 'Add bar', 'affected_files': ['src/B.java']},
            ],
        )
        # Use real repo files so files_exist passes.
        existing_file = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        task_dir = ctx.plan_dir / 'tasks'
        _write_task(
            task_dir,
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing_file, 'status': 'pending'}],
        )
        _write_task(
            task_dir,
            2,
            deliverable=2,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing_file, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-clean'))

        assert result['status'] == 'success'
        assert result['total_failed'] == 0
        assert result['findings_emitted'] == 0  # --no-emit path
        assert result['ambiguous'] is False
        for name in (
            'coverage',
            'skill_resolution',
            'acyclic',
            'files_exist',
            'keyword_drift',
            'structural_token_drift',
        ):
            assert result['checks'][name]['failed'] == 0, name


# =============================================================================
# Coverage check
# =============================================================================


def test_qgate_mechanical_coverage_missing_deliverable():
    """A deliverable with no tasks is flagged."""
    with PlanContext(plan_id='qgate-cov-missing') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [
                {'number': 1, 'title': 'Add foo', 'affected_files': ['src/A.java']},
                {'number': 2, 'title': 'Add bar', 'affected_files': ['src/B.java']},
            ],
        )
        # Only deliverable 1 has a task; deliverable 2 is uncovered.
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-cov-missing'))
        assert result['checks']['coverage']['failed'] == 1


def test_qgate_mechanical_coverage_orphan_task():
    """A task referencing a non-existent deliverable is flagged."""
    with PlanContext(plan_id='qgate-cov-orphan') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'Add foo', 'affected_files': ['src/A.java']}],
        )
        # deliverable=2 references unknown deliverable -> orphan.
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            2,
            deliverable=42,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-cov-orphan'))
        # One orphan task; deliverable 1 is covered.
        assert result['checks']['coverage']['failed'] == 1


def test_qgate_mechanical_holistic_task_not_orphan():
    """deliverable=0 (holistic) does not count as an orphan."""
    with PlanContext(plan_id='qgate-cov-holistic') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'Add foo', 'affected_files': ['src/A.java']}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            2,
            deliverable=0,
            profile='verification',
            domain='',
            skills=[],
            steps=[{'number': 1, 'target': 'pw verify', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-cov-holistic'))
        assert result['checks']['coverage']['failed'] == 0


# =============================================================================
# Skill resolution check
# =============================================================================


def test_qgate_mechanical_skill_resolution_missing_domain():
    """Non-verification tasks without a domain are flagged."""
    with PlanContext(plan_id='qgate-skill-nodomain') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            domain='',  # missing
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-skill-nodomain'))
        assert result['checks']['skill_resolution']['failed'] >= 1


def test_qgate_mechanical_skill_resolution_bad_shape():
    """Skill strings not matching ``bundle:skill`` shape are flagged."""
    with PlanContext(plan_id='qgate-skill-shape') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['no-colon-here', 'plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-skill-shape'))
        # Exactly one bad skill.
        assert result['checks']['skill_resolution']['failed'] == 1


def test_qgate_mechanical_skill_resolution_empty_skills_allowed():
    """Empty skills list is permitted (Step 5 records its own finding)."""
    with PlanContext(plan_id='qgate-skill-empty') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=[],
            steps=[{'number': 1, 'target': 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-skill-empty'))
        assert result['checks']['skill_resolution']['failed'] == 0


# =============================================================================
# Acyclic check
# =============================================================================


def test_qgate_mechanical_acyclic_simple_cycle():
    """TASK-1 -> TASK-2 -> TASK-1 produces one finding."""
    with PlanContext(plan_id='qgate-cycle') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            depends_on=['TASK-2'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            2,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            depends_on=['TASK-1'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-cycle'))
        assert result['checks']['acyclic']['failed'] == 1


def test_qgate_mechanical_acyclic_dag_passes():
    """A linear dependency chain is a DAG and passes."""
    with PlanContext(plan_id='qgate-dag') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            2,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            depends_on=['TASK-1'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-dag'))
        assert result['checks']['acyclic']['failed'] == 0


# =============================================================================
# Files-exist check
# =============================================================================


def test_qgate_mechanical_files_exist_missing_step_target():
    """A step target that doesn't exist on disk is flagged."""
    with PlanContext(plan_id='qgate-files-missing') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/Missing.java']}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': 'src/does-not-exist.java', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-files-missing'))
        assert result['checks']['files_exist']['failed'] == 1


def test_qgate_mechanical_files_exist_skips_verification_profile():
    """Verification profile steps are commands, not files, so are skipped."""
    with PlanContext(plan_id='qgate-files-verify') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )
        _write_task(
            ctx.plan_dir / 'tasks',
            2,
            deliverable=0,
            profile='verification',
            domain='',
            skills=[],
            steps=[{'number': 1, 'target': 'pw verify --module plan-marshall', 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-files-verify'))
        assert result['checks']['files_exist']['failed'] == 0


# =============================================================================
# Keyword drift check
# =============================================================================


def test_qgate_mechanical_keyword_drift_planning_keyword_in_description():
    """A planning-domain keyword absent from the deliverable haystack is flagged."""
    with PlanContext(plan_id='qgate-kw-drift') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'Implement foo', 'affected_files': ['src/A.java']}],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            description="'Implement foo'. Update PR review workflow for CI compliance.",
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-kw-drift'))
        # "PR review" and "CI" both fire.
        assert result['checks']['keyword_drift']['failed'] >= 2


def test_qgate_mechanical_keyword_drift_keyword_in_haystack_is_ok():
    """A planning keyword present in the deliverable haystack is not flagged."""
    with PlanContext(plan_id='qgate-kw-ok') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [
                {
                    'number': 1,
                    'title': 'Wire CI pipeline',
                    'affected_files': ['ci/main.yml'],
                    'metadata': {'change_type': 'feature'},
                }
            ],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            description="'Wire CI pipeline'. Update CI configuration to use the new runner.",
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-kw-ok'))
        assert result['checks']['keyword_drift']['failed'] == 0


# =============================================================================
# Structural-token drift (TASK-N numbering monotonic) check
# =============================================================================


def test_qgate_mechanical_structural_token_gap():
    """A gap in TASK-NNN numbering is flagged."""
    with PlanContext(plan_id='qgate-numbering-gap') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )
        # Skip TASK-2 to leave a gap.
        _write_task(
            ctx.plan_dir / 'tasks',
            3,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-numbering-gap'))
        assert result['checks']['structural_token_drift']['failed'] >= 1


def test_qgate_mechanical_structural_token_does_not_start_at_001():
    """Lowest task being TASK-002 is flagged."""
    with PlanContext(plan_id='qgate-numbering-start') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [{'number': 1, 'title': 'X', 'affected_files': ['src/A.java']}],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            2,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-numbering-start'))
        # Both "doesn't start at 001" and the gap at TASK-001 are reported.
        assert result['checks']['structural_token_drift']['failed'] >= 1


# =============================================================================
# Ambiguous flag + plan-dir handling
# =============================================================================


def test_qgate_mechanical_missing_outline_marks_ambiguous():
    """When solution_outline.md is missing, ``ambiguous`` flips to True."""
    with PlanContext(plan_id='qgate-no-outline') as ctx:
        assert ctx.plan_dir is not None
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-no-outline'))
        assert result['ambiguous'] is True


def test_qgate_mechanical_plan_dir_not_found_errors():
    """Missing plan dir returns a structured error."""
    with PlanContext(plan_id='qgate-clean-2'):
        # PlanContext creates the plan dir; query a different id that doesn't exist.
        result = cmd_qgate_mechanical(_ns('does-not-exist'))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Emission path (writes findings to the Q-Gate JSONL store)
# =============================================================================


def test_qgate_mechanical_emit_writes_findings():
    """With emit=True (default), failures land in the phase-4-plan Q-Gate findings store."""
    with PlanContext(plan_id='qgate-emit') as ctx:
        assert ctx.plan_dir is not None
        _write_outline(
            ctx.plan_dir,
            [
                {'number': 1, 'title': 'Has tasks', 'affected_files': ['src/A.java']},
                {'number': 2, 'title': 'No tasks', 'affected_files': ['src/B.java']},
            ],
        )
        existing = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
        _write_task(
            ctx.plan_dir / 'tasks',
            1,
            deliverable=1,
            skills=['plan-marshall:manage-tasks'],
            steps=[{'number': 1, 'target': existing, 'status': 'pending'}],
        )

        result = cmd_qgate_mechanical(_ns('qgate-emit', no_emit=False))
        assert result['status'] == 'success'
        assert result['findings_emitted'] == 1
        assert result['emit'] is True
        # The Q-Gate JSONL store records the finding under phase 4-plan.
        findings_path = ctx.plan_dir / 'artifacts' / 'findings' / 'qgate-4-plan.jsonl'
        assert findings_path.exists(), 'qgate findings file was not created'
        records = [json.loads(line) for line in findings_path.read_text().splitlines() if line.strip()]
        assert len(records) == 1
        assert records[0]['source'] == 'qgate'
        assert records[0]['type'] == 'triage'
        assert 'coverage' in records[0]['title']


# =============================================================================
# Dispatch via manage-tasks.py registry
# =============================================================================


def test_qgate_mechanical_registered_in_manage_tasks_dispatch():
    """The subcommand is wired in ``COMMANDS`` so the dispatcher routes to it."""
    manage_tasks = _load_module('_manage_tasks_dispatch_check', 'manage-tasks.py')
    assert 'qgate-mechanical-checks' in manage_tasks.COMMANDS
    assert manage_tasks.COMMANDS['qgate-mechanical-checks'] is cmd_qgate_mechanical or callable(
        manage_tasks.COMMANDS['qgate-mechanical-checks']
    )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
