#!/usr/bin/env python3
"""
Artifact collection script for workflow verification.

Collects workflow artifacts via manage-* tool interfaces for comparison
against golden references during verification.

Usage:
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/ --phases 2-outline,3-plan

Output: Directory containing collected artifacts in original format.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# TOON Helpers
# =============================================================================


def serialize_toon(data: dict[str, Any], indent: int = 0) -> str:
    """Serialize dict to TOON format."""
    lines: list[str] = []
    prefix = '  ' * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f'{prefix}{key}:')
            lines.append(serialize_toon(value, indent + 1))
        elif isinstance(value, list):
            if not value:
                lines.append(f'{prefix}{key}[0]:')
            elif all(isinstance(item, dict) for item in value):
                if value:
                    keys = list(value[0].keys())
                    lines.append(f'{prefix}{key}[{len(value)}]{{{",".join(keys)}}}:')
                    for item in value:
                        vals = [str(item.get(k, '')) for k in keys]
                        lines.append(f'{prefix}  {",".join(vals)}')
            else:
                lines.append(f'{prefix}{key}[{len(value)}]:')
                for item in value:
                    lines.append(f'{prefix}  {item}')
        elif isinstance(value, bool):
            lines.append(f'{prefix}{key}: {str(value).lower()}')
        else:
            lines.append(f'{prefix}{key}: {value}')

    return '\n'.join(lines)


# =============================================================================
# Script Runner
# =============================================================================


def run_manage_script(notation: str, subcommand: str, *args: str) -> tuple[int, str, str]:
    """
    Run a manage-* script via the executor.

    Args:
        notation: Script notation (e.g., 'pm-workflow:manage-solution-outline:manage-solution-outline')
        subcommand: Subcommand to run (e.g., 'read')
        *args: Additional arguments

    Returns:
        (returncode, stdout, stderr)
    """
    executor_path = Path('.plan/execute-script.py')
    if not executor_path.exists():
        project_root = Path(__file__).parent.parent.parent.parent.parent
        executor_path = project_root / '.plan' / 'execute-script.py'

    if not executor_path.exists():
        return 1, '', f'Executor not found at {executor_path}'

    cmd = [sys.executable, str(executor_path), notation, subcommand] + list(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd(),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, '', 'Script execution timed out'
    except Exception as e:
        return 1, '', str(e)


# =============================================================================
# Artifact Collector
# =============================================================================


class ArtifactCollector:
    """Collects workflow artifacts via manage-* interfaces."""

    def __init__(self, plan_id: str, output_dir: Path):
        self.plan_id = plan_id
        self.output_dir = output_dir
        self.collected: list[dict[str, str]] = []
        self.errors: list[str] = []

    def collect_solution_outline(self) -> bool:
        """Collect solution_outline.md via manage-solution-outline."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-solution-outline:manage-solution-outline',
            'read',
            '--plan-id',
            self.plan_id,
            '--raw',
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'solution_outline.md'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'solution_outline.md', 'status': 'success'})
            return True
        else:
            self.errors.append(f'Failed to collect solution_outline.md: {stderr}')
            self.collected.append({'artifact': 'solution_outline.md', 'status': 'failed'})
            return False

    def collect_deliverables(self) -> bool:
        """Collect deliverables list via manage-solution-outline."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-solution-outline:manage-solution-outline',
            'list-deliverables',
            '--plan-id',
            self.plan_id,
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'deliverables.toon'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'deliverables.toon', 'status': 'success'})
            return True
        else:
            self.errors.append(f'Failed to collect deliverables: {stderr}')
            self.collected.append({'artifact': 'deliverables.toon', 'status': 'failed'})
            return False

    def collect_config(self) -> bool:
        """Collect config.toon via manage-config."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-config:manage-config', 'read', '--plan-id', self.plan_id
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'config.toon'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'config.toon', 'status': 'success'})
            return True
        else:
            self.errors.append(f'Failed to collect config.toon: {stderr}')
            self.collected.append({'artifact': 'config.toon', 'status': 'failed'})
            return False

    def collect_status(self) -> bool:
        """Collect status.toon via manage-lifecycle."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-lifecycle:manage-lifecycle', 'status', '--plan-id', self.plan_id
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'status.toon'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'status.toon', 'status': 'success'})
            return True
        else:
            self.errors.append(f'Failed to collect status.toon: {stderr}')
            self.collected.append({'artifact': 'status.toon', 'status': 'failed'})
            return False

    def collect_references(self) -> bool:
        """Collect references.toon via manage-references."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-references:manage-references', 'read', '--plan-id', self.plan_id
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'references.toon'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'references.toon', 'status': 'success'})
            return True
        else:
            # References may not exist for all plans, treat as warning
            self.collected.append({'artifact': 'references.toon', 'status': 'not_found'})
            return False

    def collect_tasks(self, phase: str = 'execute') -> bool:
        """Collect tasks via manage-tasks."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-tasks:manage-tasks',
            'list',
            '--plan-id',
            self.plan_id,
            '--phase',
            phase,
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'tasks-list.toon'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'tasks-list.toon', 'status': 'success'})

            # Also collect individual task details if we can parse task numbers
            # Parse task count from list output
            task_count = 0
            for line in stdout.split('\n'):
                if 'task_count:' in line:
                    try:
                        task_count = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass

            # Create tasks subdirectory
            tasks_dir = self.output_dir / 'tasks'
            tasks_dir.mkdir(exist_ok=True)

            # Collect individual tasks
            for i in range(1, task_count + 1):
                self._collect_single_task(i, tasks_dir, phase)

            return True
        else:
            self.collected.append({'artifact': 'tasks-list.toon', 'status': 'not_found'})
            return False

    def _collect_single_task(self, task_number: int, tasks_dir: Path, phase: str) -> bool:
        """Collect a single task detail."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-tasks:manage-tasks',
            'get',
            '--plan-id',
            self.plan_id,
            '--number',
            str(task_number),
            '--phase',
            phase,
        )

        if code == 0 and stdout.strip():
            output_path = tasks_dir / f'TASK-{task_number:02d}.toon'
            output_path.write_text(stdout)
            return True
        return False

    def collect_work_log(self) -> bool:
        """Collect work log via manage-logging."""
        code, stdout, stderr = run_manage_script(
            'plan-marshall:manage-logging:manage-log',
            'read',
            '--plan-id',
            self.plan_id,
            '--type',
            'work',
        )

        if code == 0 and stdout.strip():
            output_path = self.output_dir / 'work.log'
            output_path.write_text(stdout)
            self.collected.append({'artifact': 'work.log', 'status': 'success'})
            return True
        else:
            self.collected.append({'artifact': 'work.log', 'status': 'not_found'})
            return False

    def collect_all(self, phases: list[str] | None = None) -> dict[str, Any]:
        """Collect all artifacts.

        Args:
            phases: List of phases to collect artifacts for ['2-outline', '3-plan']
        """
        if phases is None:
            phases = ['2-outline']

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Always collect core artifacts
        self.collect_solution_outline()
        self.collect_deliverables()
        self.collect_config()
        self.collect_status()
        self.collect_references()
        self.collect_work_log()

        # Collect tasks if planning phase included
        if '3-plan' in phases or 'both' in phases:
            self.collect_tasks()

        # Generate collection summary
        success_count = len([c for c in self.collected if c['status'] == 'success'])
        failed_count = len([c for c in self.collected if c['status'] == 'failed'])

        return {
            'status': 'success' if failed_count == 0 else 'partial',
            'plan_id': self.plan_id,
            'output_dir': str(self.output_dir),
            'collected_count': success_count,
            'failed_count': failed_count,
            'artifacts': self.collected,
            'errors': self.errors if self.errors else None,
        }


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description='Collect workflow artifacts for verification')
    parser.add_argument('--plan-id', required=True, help='Plan identifier')
    parser.add_argument('--output', required=True, help='Output directory path')
    parser.add_argument('--phases', default='2-outline', help='Phases to collect (comma-separated)')

    args = parser.parse_args()

    output_dir = Path(args.output)
    phases = args.phases.split(',')

    collector = ArtifactCollector(args.plan_id, output_dir)
    results = collector.collect_all(phases)

    # Filter out None values for clean output
    results = {k: v for k, v in results.items() if v is not None}

    print(serialize_toon(results))

    return 0 if results['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
