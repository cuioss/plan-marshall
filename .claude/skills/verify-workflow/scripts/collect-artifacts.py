#!/usr/bin/env python3
"""
Artifact collection script for workflow verification.

Collects workflow artifacts for comparison against golden references
during verification.

Phases (7-phase model):
    1-init:     status.toon, request.md, references.toon
    2-refine:   request.md with clarifications, work.log with [REFINE:*] entries
    3-outline:  solution_outline.md, deliverables, references.toon
    4-plan:     TASK-*.toon files
    5-execute:  Modified files tracked in references.toon
    6-verify:   Quality checks (not collected by this script)
    7-finalize: Git commit, PR artifacts

Usage:
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/ --phases 3-outline,4-plan
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/ --phases 1-init,2-refine,3-outline

Output: Directory containing collected artifacts in original format.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

# Cross-skill imports (executor sets PYTHONPATH)
from _plan_parsing import (  # type: ignore[import-not-found]
    extract_deliverable_headings,
    parse_document_sections,
)
from file_ops import base_path  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Artifact Collector
# =============================================================================


class ArtifactCollector:
    """Collects workflow artifacts."""

    def __init__(self, plan_id: str, output_dir: Path):
        self.plan_id = plan_id
        self.output_dir = output_dir
        self.collected: list[dict[str, str]] = []
        self.errors: list[str] = []

    def collect_solution_outline(self) -> bool:
        """Collect solution_outline.md."""
        try:
            solution_path = base_path('plans', self.plan_id, 'solution_outline.md')

            if solution_path.exists():
                content = solution_path.read_text()
                output_path = self.output_dir / 'solution_outline.md'
                output_path.write_text(content)
                self.collected.append({'artifact': 'solution_outline.md', 'status': 'success'})
                return True
            else:
                self.errors.append('Solution outline not found')
                self.collected.append({'artifact': 'solution_outline.md', 'status': 'failed'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect solution_outline.md: {e}')
            self.collected.append({'artifact': 'solution_outline.md', 'status': 'failed'})
            return False

    def collect_deliverables(self) -> bool:
        """Collect deliverables list."""
        try:
            solution_path = base_path('plans', self.plan_id, 'solution_outline.md')

            if not solution_path.exists():
                self.errors.append('Solution outline not found for deliverables')
                self.collected.append({'artifact': 'deliverables.toon', 'status': 'failed'})
                return False

            content = solution_path.read_text()
            sections = parse_document_sections(content)
            # Section keys are lowercase
            deliverables_section = sections.get('deliverables', '')

            if not deliverables_section:
                self.errors.append('No deliverables section found')
                self.collected.append({'artifact': 'deliverables.toon', 'status': 'failed'})
                return False

            deliverables = extract_deliverable_headings(deliverables_section)

            # Format as TOON
            result = {
                'status': 'success',
                'plan_id': self.plan_id,
                'deliverable_count': len(deliverables),
                'deliverables': deliverables,
            }

            output_path = self.output_dir / 'deliverables.toon'
            output_path.write_text(serialize_toon(result))
            self.collected.append({'artifact': 'deliverables.toon', 'status': 'success'})
            return True

        except Exception as e:
            self.errors.append(f'Failed to collect deliverables: {e}')
            self.collected.append({'artifact': 'deliverables.toon', 'status': 'failed'})
            return False

    def collect_status(self) -> bool:
        """Collect status.toon."""
        try:
            status_path = base_path('plans', self.plan_id, 'status.toon')

            if status_path.exists():
                content = status_path.read_text()
                output_path = self.output_dir / 'status.toon'
                output_path.write_text(content)
                self.collected.append({'artifact': 'status.toon', 'status': 'success'})
                return True
            else:
                self.errors.append('Status file not found')
                self.collected.append({'artifact': 'status.toon', 'status': 'failed'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect status.toon: {e}')
            self.collected.append({'artifact': 'status.toon', 'status': 'failed'})
            return False

    def collect_references(self) -> bool:
        """Collect references.toon."""
        try:
            refs_path = base_path('plans', self.plan_id, 'references.toon')

            if refs_path.exists():
                content = refs_path.read_text()
                output_path = self.output_dir / 'references.toon'
                output_path.write_text(content)
                self.collected.append({'artifact': 'references.toon', 'status': 'success'})
                return True
            else:
                # References may not exist for all plans, treat as not_found
                self.collected.append({'artifact': 'references.toon', 'status': 'not_found'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect references.toon: {e}')
            self.collected.append({'artifact': 'references.toon', 'status': 'failed'})
            return False

    def collect_tasks(self, phase: str = 'execute') -> bool:
        """Collect tasks."""
        try:
            tasks_dir = base_path('plans', self.plan_id, 'tasks')

            if not tasks_dir.exists():
                self.collected.append({'artifact': 'tasks-list.toon', 'status': 'not_found'})
                return False

            # Find TASK-*.toon files
            task_files = sorted(tasks_dir.glob('TASK-*.toon'))

            if not task_files:
                self.collected.append({'artifact': 'tasks-list.toon', 'status': 'not_found'})
                return False

            # Create tasks list
            tasks = []
            for task_file in task_files:
                tasks.append({
                    'file': task_file.name,
                    'path': str(task_file),
                })

            result = {
                'status': 'success',
                'plan_id': self.plan_id,
                'task_count': len(tasks),
                'tasks': tasks,
            }

            output_path = self.output_dir / 'tasks-list.toon'
            output_path.write_text(serialize_toon(result))
            self.collected.append({'artifact': 'tasks-list.toon', 'status': 'success'})

            # Copy individual task files
            tasks_dir = self.output_dir / 'tasks'
            tasks_dir.mkdir(exist_ok=True)

            for task_file in task_files:
                content = task_file.read_text()
                (tasks_dir / task_file.name).write_text(content)

            return True

        except Exception as e:
            self.errors.append(f'Failed to collect tasks: {e}')
            self.collected.append({'artifact': 'tasks-list.toon', 'status': 'failed'})
            return False

    def collect_work_log(self) -> bool:
        """Collect work log."""
        try:
            # Work logs are now in logs/ subdirectory
            log_path = base_path('plans', self.plan_id, 'logs', 'work.log')

            if log_path.exists():
                content = log_path.read_text()
                output_path = self.output_dir / 'work.log'
                output_path.write_text(content)
                self.collected.append({'artifact': 'work.log', 'status': 'success'})
                return True
            else:
                self.collected.append({'artifact': 'work.log', 'status': 'not_found'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect work.log: {e}')
            self.collected.append({'artifact': 'work.log', 'status': 'failed'})
            return False

    def collect_decision_log(self) -> bool:
        """Collect decision log."""
        try:
            # Decision logs are in logs/ subdirectory
            log_path = base_path('plans', self.plan_id, 'logs', 'decision.log')

            if log_path.exists():
                content = log_path.read_text()
                output_path = self.output_dir / 'decision.log'
                output_path.write_text(content)
                self.collected.append({'artifact': 'decision.log', 'status': 'success'})
                return True
            else:
                self.collected.append({'artifact': 'decision.log', 'status': 'not_found'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect decision.log: {e}')
            self.collected.append({'artifact': 'decision.log', 'status': 'failed'})
            return False

    def collect_request(self) -> bool:
        """Collect request.md (for 1-init and 2-refine phases)."""
        try:
            request_path = base_path('plans', self.plan_id, 'request.md')

            if request_path.exists():
                content = request_path.read_text()
                output_path = self.output_dir / 'request.md'
                output_path.write_text(content)
                self.collected.append({'artifact': 'request.md', 'status': 'success'})
                return True
            else:
                self.errors.append('Request file not found')
                self.collected.append({'artifact': 'request.md', 'status': 'failed'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect request.md: {e}')
            self.collected.append({'artifact': 'request.md', 'status': 'failed'})
            return False

    def collect_all(self, phases: list[str] | None = None) -> dict[str, Any]:
        """Collect all artifacts based on requested phases.

        Args:
            phases: List of phases to collect artifacts for.
                    Valid phases: 1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-verify, 7-finalize
                    Default: ['3-outline']

        Phase artifact mapping:
            1-init:    status.toon, request.md, references.toon
            2-refine:  request.md (with clarifications), work.log
            3-outline: solution_outline.md, deliverables.toon, references.toon
            4-plan:    TASK-*.toon files
            5-execute: references.toon (with modified files)
            6-verify:   (quality check artifacts not collected by this script)
            7-finalize: (git artifacts not collected by this script)
        """
        if phases is None:
            phases = ['3-outline']

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Collect artifacts based on phases requested
        # 1-init artifacts: status, request, references
        if '1-init' in phases:
            self.collect_status()
            self.collect_request()
            self.collect_references()

        # 2-refine artifacts: request (with clarifications), work log
        if '2-refine' in phases:
            self.collect_request()
            self.collect_work_log()

        # 3-outline artifacts: solution outline, deliverables, references
        if '3-outline' in phases or 'both' in phases:
            self.collect_solution_outline()
            self.collect_deliverables()
            self.collect_status()
            self.collect_references()
            self.collect_work_log()
            self.collect_decision_log()

        # 4-plan artifacts: tasks
        if '4-plan' in phases or 'both' in phases:
            self.collect_tasks()
            # Also collect outline artifacts if not already collected
            if '3-outline' not in phases and 'both' not in phases:
                self.collect_solution_outline()
                self.collect_deliverables()

        # 5-execute artifacts: references with modified files
        if '5-execute' in phases:
            self.collect_references()
            self.collect_work_log()

        # 6-verify / 7-finalize: not collected here (use build/git commands)

        # Generate collection summary
        success_count = len([c for c in self.collected if c['status'] == 'success'])
        failed_count = len([c for c in self.collected if c['status'] == 'failed'])

        result: dict[str, Any] = {
            'status': 'success' if failed_count == 0 else 'partial',
            'plan_id': self.plan_id,
            'output_dir': str(self.output_dir),
            'collected_count': success_count,
            'failed_count': failed_count,
            'artifacts': self.collected,
        }

        if self.errors:
            result['errors'] = self.errors

        return result


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description='Collect workflow artifacts for verification')
    parser.add_argument('--plan-id', required=True, help='Plan identifier')
    parser.add_argument('--output', required=True, help='Output directory path')
    parser.add_argument('--phases', default='3-outline', help='Phases to collect (comma-separated)')

    args = parser.parse_args()

    output_dir = Path(args.output)
    phases = args.phases.split(',')

    collector = ArtifactCollector(args.plan_id, output_dir)
    results = collector.collect_all(phases)

    print(serialize_toon(results))

    return 0  # Status modeled in output, not exit code


if __name__ == '__main__':
    sys.exit(main())
