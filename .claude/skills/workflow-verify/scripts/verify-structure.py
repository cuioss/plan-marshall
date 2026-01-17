#!/usr/bin/env python3
"""
Structural verification script for workflow outputs.

Runs deterministic checks via manage-* tool interfaces to verify:
- File existence
- Format/schema validation
- Required sections present
- Cross-references valid

Usage:
    python3 verify-structure.py --plan-id my-plan --test-case path/to/test-case
    python3 verify-structure.py --plan-id my-plan --test-case path/to/test-case --output results.toon

Output: TOON format with check results and findings.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# TOON Output Helpers
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
                # Uniform array format
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
            # Parse: key[N]: or key[N]{fields}:
            key_part = line.split('[')[0]
            current_list_key = key_part
            current_list = []
            continue

        # Check if we're in a list
        if current_list_key:
            if ':' in line and not line.startswith(' '):
                # End of list, new key-value
                result[current_list_key] = current_list
                current_list_key = None
                current_list = []
            else:
                # List item
                current_list.append(line.strip())
                continue

        # Key-value pair
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()

    # Handle final list
    if current_list_key and current_list:
        result[current_list_key] = current_list

    return result


# =============================================================================
# Script Runner
# =============================================================================


def run_manage_script(notation: str, subcommand: str, *args: str) -> tuple[int, str, str]:
    """
    Run a manage-* script via the executor.

    Args:
        notation: Script notation (e.g., 'pm-workflow:manage-solution-outline:manage-solution-outline')
        subcommand: Subcommand to run (e.g., 'validate')
        *args: Additional arguments

    Returns:
        (returncode, stdout, stderr)
    """
    # Find executor
    executor_path = Path('.plan/execute-script.py')
    if not executor_path.exists():
        # Try from project root
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
        """Check if solution outline exists via manage-solution-outline."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-solution-outline:manage-solution-outline',
            'exists',
            '--plan-id',
            self.plan_id,
        )

        if code == 0 and 'exists: true' in stdout.lower():
            self.add_check('solution_outline_exists', 'pass', 'Solution outline exists')
            return True
        else:
            self.add_check('solution_outline_exists', 'fail', 'Solution outline not found')
            self.add_finding('error', f'Solution outline not found for plan {self.plan_id}')
            return False

    def check_solution_outline_valid(self) -> bool:
        """Validate solution outline structure via manage-solution-outline."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-solution-outline:manage-solution-outline',
            'validate',
            '--plan-id',
            self.plan_id,
        )

        if code == 0 and 'status: success' in stdout:
            self.add_check('solution_outline_valid', 'pass', 'Solution outline validates successfully')
            # Check for warnings
            if 'warnings:' in stdout:
                # Extract warnings and add as findings
                for line in stdout.split('\n'):
                    if line.strip().startswith('-') and 'warning' not in line.lower():
                        self.add_finding('warning', line.strip().lstrip('- '))
            return True
        else:
            self.add_check('solution_outline_valid', 'fail', 'Solution outline validation failed')
            # Extract errors from output
            if 'issues:' in stdout:
                for line in stdout.split('\n'):
                    if line.strip().startswith('-'):
                        self.add_finding('error', line.strip().lstrip('- '))
            return False

    def check_config_exists(self) -> bool:
        """Check if config.toon exists via manage-config."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-config:manage-config', 'exists', '--plan-id', self.plan_id
        )

        if code == 0 and 'exists: true' in stdout.lower():
            self.add_check('config_exists', 'pass', 'Config file exists')
            return True
        else:
            self.add_check('config_exists', 'fail', 'Config file not found')
            self.add_finding('error', f'Config file not found for plan {self.plan_id}')
            return False

    def check_status_exists(self) -> bool:
        """Check if status.toon exists via manage-lifecycle."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-lifecycle:manage-lifecycle', 'status', '--plan-id', self.plan_id
        )

        if code == 0 and 'status:' in stdout:
            self.add_check('status_exists', 'pass', 'Status file exists')
            return True
        else:
            self.add_check('status_exists', 'fail', 'Status file not found')
            self.add_finding('warning', f'Status file not found for plan {self.plan_id}')
            return False

    def check_references_exists(self) -> bool:
        """Check if references.toon exists via manage-references."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-references:manage-references', 'exists', '--plan-id', self.plan_id
        )

        if code == 0 and 'exists: true' in stdout.lower():
            self.add_check('references_exists', 'pass', 'References file exists')
            return True
        else:
            self.add_check('references_exists', 'fail', 'References file not found')
            self.add_finding('warning', f'References file not found for plan {self.plan_id}')
            return False

    def check_deliverables_count(self, expected_count: int | None = None) -> bool:
        """Check deliverables can be listed and optionally verify count."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-solution-outline:manage-solution-outline',
            'list-deliverables',
            '--plan-id',
            self.plan_id,
        )

        if code != 0:
            self.add_check('deliverables_list', 'fail', 'Failed to list deliverables')
            self.add_finding('error', 'Could not list deliverables')
            return False

        # Parse count from output
        actual_count = 0
        for line in stdout.split('\n'):
            if 'deliverable_count:' in line:
                try:
                    actual_count = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass

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

    def check_tasks_exist(self, phase: str = 'execute') -> bool:
        """Check if tasks exist for the plan."""
        code, stdout, stderr = run_manage_script(
            'pm-workflow:manage-tasks:manage-tasks',
            'list',
            '--plan-id',
            self.plan_id,
            '--phase',
            phase,
        )

        if code != 0:
            self.add_check('tasks_exist', 'fail', f'Failed to list tasks for phase {phase}')
            return False

        # Check for task count
        task_count = 0
        for line in stdout.split('\n'):
            if 'task_count:' in line:
                try:
                    task_count = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass

        if task_count > 0:
            self.add_check('tasks_exist', 'pass', f'Found {task_count} tasks')
            return True
        else:
            self.add_check('tasks_exist', 'fail', 'No tasks found')
            self.add_finding('warning', f'No tasks found for plan {self.plan_id}')
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
