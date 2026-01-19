#!/usr/bin/env python3
"""
Structural verification script for workflow outputs.

Runs deterministic checks to verify:
- File existence
- Required sections present
- Basic format validation

Usage:
    python3 verify-structure.py --plan-id my-plan --test-case path/to/test-case
    python3 verify-structure.py --plan-id my-plan --test-case path/to/test-case --output results.toon

Output: TOON format with check results and findings.
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


# =============================================================================
# Validation Helpers (inline simplified versions)
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


def validate_solution_structure(content: str) -> tuple[list[str], list[str], dict[str, Any]]:
    """Validate solution outline structure. Returns (errors, warnings, stats)."""
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    sections = parse_document_sections(content)
    required_sections = ['Summary', 'Overview', 'Deliverables']

    for section in required_sections:
        if section not in sections:
            errors.append(f'Missing required section: {section}')

    if 'Deliverables' in sections:
        deliverables = extract_deliverables(sections['Deliverables'])
        stats['deliverable_count'] = len(deliverables)
        if not deliverables:
            errors.append('No deliverables found in Deliverables section')

    return errors, warnings, stats


# =============================================================================
# TOON Helpers
# =============================================================================


def parse_toon_simple(content: str) -> dict[str, Any]:
    """Parse simple TOON format (key: value pairs)."""
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Check for list header
        if '[' in line and line.endswith(':'):
            if current_list_key and current_list:
                result[current_list_key] = current_list
            key_part = line.split('[')[0]
            current_list_key = key_part
            current_list = []
            continue

        # Check if we're in a list
        if current_list_key:
            if ':' in line and not line.startswith(' '):
                result[current_list_key] = current_list
                current_list_key = None
                current_list = []
            else:
                current_list.append(line.strip())
                continue

        # Key-value pair
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()

    if current_list_key and current_list:
        result[current_list_key] = current_list

    return result


# =============================================================================
# Structural Checks
# =============================================================================


class StructuralChecker:
    """Runs structural verification checks."""

    def __init__(self, plan_id: str, test_case_dir: Path):
        self.plan_id = plan_id
        self.test_case_dir = test_case_dir
        self.checks: list[dict[str, str]] = []
        self.findings: list[dict[str, str]] = []

    def add_check(self, name: str, status: str, message: str) -> None:
        """Record a check result."""
        self.checks.append({'name': name, 'status': status, 'message': message})

    def add_finding(self, severity: str, message: str) -> None:
        """Record a finding."""
        self.findings.append({'severity': severity, 'message': message})

    def check_solution_outline_exists(self) -> bool:
        """Check if solution outline exists."""
        solution_path = get_solution_path(self.plan_id)

        if solution_path.exists():
            self.add_check('solution_outline_exists', 'pass', 'Solution outline exists')
            return True
        else:
            self.add_check('solution_outline_exists', 'fail', 'Solution outline not found')
            self.add_finding('error', f'Solution outline not found for plan {self.plan_id}')
            return False

    def check_solution_outline_valid(self) -> bool:
        """Validate solution outline structure."""
        solution_path = get_solution_path(self.plan_id)

        if not solution_path.exists():
            self.add_check('solution_outline_valid', 'fail', 'Solution outline not found')
            return False

        try:
            content = solution_path.read_text()
            errors, warnings, _stats = validate_solution_structure(content)

            if errors:
                self.add_check('solution_outline_valid', 'fail', 'Solution outline validation failed')
                for error in errors:
                    self.add_finding('error', error)
                return False
            else:
                self.add_check('solution_outline_valid', 'pass', 'Solution outline validates successfully')
                for warning in warnings:
                    self.add_finding('warning', warning)
                return True
        except Exception as e:
            self.add_check('solution_outline_valid', 'fail', f'Validation error: {e}')
            self.add_finding('error', str(e))
            return False

    def check_config_exists(self) -> bool:
        """Check if config.toon exists."""
        config_path = get_config_path(self.plan_id)

        if config_path.exists():
            self.add_check('config_exists', 'pass', 'Config file exists')
            return True
        else:
            self.add_check('config_exists', 'fail', 'Config file not found')
            self.add_finding('error', f'Config file not found for plan {self.plan_id}')
            return False

    def check_status_exists(self) -> bool:
        """Check if status.toon exists."""
        status_path = get_status_path(self.plan_id)

        if status_path.exists():
            self.add_check('status_exists', 'pass', 'Status file exists')
            return True
        else:
            self.add_check('status_exists', 'fail', 'Status file not found')
            self.add_finding('warning', f'Status file not found for plan {self.plan_id}')
            return False

    def check_references_exists(self) -> bool:
        """Check if references.toon exists."""
        refs_path = get_references_path(self.plan_id)

        if refs_path.exists():
            self.add_check('references_exists', 'pass', 'References file exists')
            return True
        else:
            self.add_check('references_exists', 'fail', 'References file not found')
            self.add_finding('warning', f'References file not found for plan {self.plan_id}')
            return False

    def check_deliverables_count(self, expected_count: int | None = None) -> bool:
        """Check deliverables can be listed and optionally verify count."""
        solution_path = get_solution_path(self.plan_id)

        if not solution_path.exists():
            self.add_check('deliverables_list', 'fail', 'Solution outline not found')
            self.add_finding('error', 'Could not list deliverables - solution outline missing')
            return False

        try:
            content = solution_path.read_text()
            sections = parse_document_sections(content)
            deliverables_section = sections.get('Deliverables', '')

            if not deliverables_section:
                self.add_check('deliverables_list', 'fail', 'No deliverables section found')
                self.add_finding('error', 'Solution outline has no Deliverables section')
                return False

            deliverables = extract_deliverables(deliverables_section)
            actual_count = len(deliverables)

            if actual_count == 0:
                self.add_check('deliverables_list', 'fail', 'No deliverables found')
                self.add_finding('error', 'Solution outline has no deliverables')
                return False

            if expected_count is not None and actual_count != expected_count:
                self.add_check(
                    'deliverables_count',
                    'fail',
                    f'Expected {expected_count} deliverables, found {actual_count}',
                )
                self.add_finding(
                    'error',
                    f'Deliverable count mismatch: expected {expected_count}, got {actual_count}',
                )
                return False

            self.add_check('deliverables_list', 'pass', f'Found {actual_count} deliverables')
            return True

        except Exception as e:
            self.add_check('deliverables_list', 'fail', f'Error listing deliverables: {e}')
            self.add_finding('error', str(e))
            return False

    def check_tasks_exist(self, phase: str = 'execute') -> bool:
        """Check if tasks exist for the plan."""
        try:
            plan_dir = base_path('plans', self.plan_id)

            if not plan_dir.exists():
                self.add_check('tasks_exist', 'fail', 'Plan directory not found')
                self.add_finding('warning', f'No tasks found for plan {self.plan_id}')
                return False

            # Count TASK-*.toon files
            task_files = list(plan_dir.glob('TASK-*.toon'))
            task_count = len(task_files)

            if task_count > 0:
                self.add_check('tasks_exist', 'pass', f'Found {task_count} tasks')
                return True
            else:
                self.add_check('tasks_exist', 'fail', 'No tasks found')
                self.add_finding('warning', f'No tasks found for plan {self.plan_id}')
                return False

        except Exception as e:
            self.add_check('tasks_exist', 'fail', f'Error checking tasks: {e}')
            return False

    def load_expected_artifacts(self) -> dict[str, Any]:
        """Load expected artifacts from test case."""
        expected_path = self.test_case_dir / 'expected-artifacts.toon'
        if not expected_path.exists():
            return {}

        content = expected_path.read_text()
        return parse_toon_simple(content)

    def run_all_checks(self, phases: list[str] | None = None) -> dict[str, Any]:
        """Run all structural checks.

        Args:
            phases: List of phases to verify ['2-outline', '3-plan']
        """
        if phases is None:
            phases = ['2-outline']

        # Basic existence checks
        self.check_solution_outline_exists()
        self.check_solution_outline_valid()
        self.check_config_exists()
        self.check_status_exists()
        self.check_references_exists()

        # Load expected artifacts for comparison
        expected = self.load_expected_artifacts()

        # Check deliverables
        expected_deliverable_count = None
        if 'deliverable_count' in expected:
            try:
                expected_deliverable_count = int(expected['deliverable_count'])
            except (ValueError, TypeError):
                pass
        self.check_deliverables_count(expected_deliverable_count)

        # Check tasks if planning phase included
        if '3-plan' in phases or 'both' in phases:
            self.check_tasks_exist()

        # Calculate overall status
        failed_checks = [c for c in self.checks if c['status'] == 'fail']
        overall_status = 'pass' if not failed_checks else 'fail'

        return {
            'status': overall_status,
            'plan_id': self.plan_id,
            'passed': len([c for c in self.checks if c['status'] == 'pass']),
            'failed': len(failed_checks),
            'checks': self.checks,
            'findings': self.findings,
        }


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description='Run structural verification checks')
    parser.add_argument('--plan-id', required=True, help='Plan identifier')
    parser.add_argument('--test-case', required=True, help='Path to test case directory')
    parser.add_argument('--output', help='Output file path (default: stdout)')
    parser.add_argument('--phases', default='2-outline', help='Phases to verify (comma-separated)')

    args = parser.parse_args()

    test_case_dir = Path(args.test_case)
    if not test_case_dir.exists():
        print(serialize_toon({'status': 'error', 'message': f'Test case not found: {args.test_case}'}))
        return 1

    phases = args.phases.split(',')

    checker = StructuralChecker(args.plan_id, test_case_dir)
    results = checker.run_all_checks(phases)

    output = serialize_toon(results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
        print(f'Results written to {args.output}')
    else:
        print(output)

    return 0 if results['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
