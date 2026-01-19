#!/usr/bin/env python3
"""
Artifact collection script for workflow verification.

Collects workflow artifacts for comparison against golden references
during verification.

Usage:
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/
    python3 collect-artifacts.py --plan-id my-plan --output artifacts/ --phases 2-outline,3-plan

Output: Directory containing collected artifacts in original format.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# Cross-skill imports (executor sets PYTHONPATH)
from file_ops import base_path  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Path Helpers (inline to avoid hyphen-named module imports)
# =============================================================================


def get_solution_path(plan_id: str) -> Path:
    """Get path to solution_outline.md."""
    return base_path('plans', plan_id, 'solution_outline.md')


def get_config_path(plan_id: str) -> Path:
    """Get path to config.toon."""
    return base_path('plans', plan_id, 'config.toon')


def get_status_path(plan_id: str) -> Path:
    """Get path to status.toon."""
    return base_path('plans', plan_id, 'status.toon')


def get_references_path(plan_id: str) -> Path:
    """Get path to references.toon."""
    return base_path('plans', plan_id, 'references.toon')


def get_log_path(plan_id: str, log_type: str = 'work') -> Path:
    """Get path to log file."""
    return base_path('plans', plan_id, f'{log_type}.log')


# =============================================================================
# Parsing Helpers (inline simplified versions)
# =============================================================================


def parse_document_sections(content: str) -> dict[str, str]:
    """Parse markdown document into sections by ## headers."""
    sections: dict[str, str] = {}
    current_section = ''
    current_content: list[str] = []

    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_content)

    return sections


def extract_deliverables(content: str) -> list[dict[str, str]]:
    """Extract deliverables from Deliverables section content."""
    deliverables: list[dict[str, str]] = []
    pattern = re.compile(r'^###\s+(\d+)\.\s+(.+)$', re.MULTILINE)

    for match in pattern.finditer(content):
        deliverables.append({'id': match.group(1), 'title': match.group(2).strip()})

    return deliverables


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
            solution_path = get_solution_path(self.plan_id)

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
            solution_path = get_solution_path(self.plan_id)

            if not solution_path.exists():
                self.errors.append('Solution outline not found for deliverables')
                self.collected.append({'artifact': 'deliverables.toon', 'status': 'failed'})
                return False

            content = solution_path.read_text()
            sections = parse_document_sections(content)
            deliverables_section = sections.get('Deliverables', '')

            if not deliverables_section:
                self.errors.append('No deliverables section found')
                self.collected.append({'artifact': 'deliverables.toon', 'status': 'failed'})
                return False

            deliverables = extract_deliverables(deliverables_section)

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

    def collect_config(self) -> bool:
        """Collect config.toon."""
        try:
            config_path = get_config_path(self.plan_id)

            if config_path.exists():
                content = config_path.read_text()
                output_path = self.output_dir / 'config.toon'
                output_path.write_text(content)
                self.collected.append({'artifact': 'config.toon', 'status': 'success'})
                return True
            else:
                self.errors.append('Config file not found')
                self.collected.append({'artifact': 'config.toon', 'status': 'failed'})
                return False
        except Exception as e:
            self.errors.append(f'Failed to collect config.toon: {e}')
            self.collected.append({'artifact': 'config.toon', 'status': 'failed'})
            return False

    def collect_status(self) -> bool:
        """Collect status.toon."""
        try:
            status_path = get_status_path(self.plan_id)

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
            refs_path = get_references_path(self.plan_id)

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
            plan_dir = base_path('plans', self.plan_id)

            if not plan_dir.exists():
                self.collected.append({'artifact': 'tasks-list.toon', 'status': 'not_found'})
                return False

            # Find TASK-*.toon files
            task_files = sorted(plan_dir.glob('TASK-*.toon'))

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
            log_path = get_log_path(self.plan_id, 'work')

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
    parser.add_argument('--phases', default='2-outline', help='Phases to collect (comma-separated)')

    args = parser.parse_args()

    output_dir = Path(args.output)
    phases = args.phases.split(',')

    collector = ArtifactCollector(args.plan_id, output_dir)
    results = collector.collect_all(phases)

    print(serialize_toon(results))

    return 0 if results['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
