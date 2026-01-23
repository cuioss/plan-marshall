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
import sys
from pathlib import Path
from typing import Any

# Cross-skill imports (executor sets PYTHONPATH)
from _plan_parsing import (  # type: ignore[import-not-found]
    extract_deliverable_headings,
    parse_document_sections,
    parse_toon_simple,
)
from file_ops import base_path  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Validation Helpers
# =============================================================================


def validate_solution_structure(content: str) -> tuple[list[str], list[str], dict[str, Any]]:
    """Validate solution outline structure. Returns (errors, warnings, stats)."""
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    sections = parse_document_sections(content)
    # Section keys are lowercase (from shared parse_document_sections)
    required_sections = ['summary', 'overview', 'deliverables']

    for section in required_sections:
        if section not in sections:
            errors.append(f'Missing required section: {section.title()}')

    if 'deliverables' in sections:
        deliverables = extract_deliverable_headings(sections['deliverables'])
        stats['deliverable_count'] = len(deliverables)
        if not deliverables:
            errors.append('No deliverables found in Deliverables section')

    return errors, warnings, stats


# =============================================================================
# Structural Checks
# =============================================================================


class StructuralChecker:
    """Runs structural verification checks."""

    def __init__(self, plan_id: str, test_case_dir: Path, artifacts_dir: Path | None = None):
        self.plan_id = plan_id
        self.test_case_dir = test_case_dir
        self.artifacts_dir = artifacts_dir
        self.checks: list[dict[str, str]] = []
        self.findings: list[dict[str, str]] = []

    def _get_artifact_path(self, *parts: str) -> Path:
        """Get path to artifact - from artifacts_dir if set, else from plan dir."""
        if self.artifacts_dir:
            return self.artifacts_dir / Path(*parts)
        return base_path('plans', self.plan_id, *parts)

    def add_check(self, name: str, status: str, message: str) -> None:
        """Record a check result."""
        self.checks.append({'name': name, 'status': status, 'message': message})

    def add_finding(self, severity: str, message: str) -> None:
        """Record a finding."""
        self.findings.append({'severity': severity, 'message': message})

    def check_solution_outline_exists(self) -> bool:
        """Check if solution outline exists."""
        solution_path = self._get_artifact_path('solution_outline.md')

        if solution_path.exists():
            self.add_check('solution_outline_exists', 'pass', 'Solution outline exists')
            return True
        else:
            self.add_check('solution_outline_exists', 'fail', 'Solution outline not found')
            self.add_finding('error', f'Solution outline not found for plan {self.plan_id}')
            return False

    def check_solution_outline_valid(self) -> bool:
        """Validate solution outline structure."""
        solution_path = self._get_artifact_path('solution_outline.md')

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
        config_path = self._get_artifact_path('config.toon')

        if config_path.exists():
            self.add_check('config_exists', 'pass', 'Config file exists')
            return True
        else:
            self.add_check('config_exists', 'fail', 'Config file not found')
            self.add_finding('error', f'Config file not found for plan {self.plan_id}')
            return False

    def check_status_exists(self) -> bool:
        """Check if status.toon exists."""
        status_path = self._get_artifact_path('status.toon')

        if status_path.exists():
            self.add_check('status_exists', 'pass', 'Status file exists')
            return True
        else:
            self.add_check('status_exists', 'fail', 'Status file not found')
            self.add_finding('warning', f'Status file not found for plan {self.plan_id}')
            return False

    def check_references_exists(self) -> bool:
        """Check if references.toon exists."""
        refs_path = self._get_artifact_path('references.toon')

        if refs_path.exists():
            self.add_check('references_exists', 'pass', 'References file exists')
            return True
        else:
            self.add_check('references_exists', 'fail', 'References file not found')
            self.add_finding('warning', f'References file not found for plan {self.plan_id}')
            return False

    def check_deliverables_count(
        self, expected_count: int | None = None, count_check_mode: str = 'strict'
    ) -> bool:
        """Check deliverables can be listed and optionally verify count.

        Args:
            expected_count: Expected number of deliverables
            count_check_mode: 'strict' (fail on mismatch) or 'informational' (note only)
        """
        solution_path = self._get_artifact_path('solution_outline.md')

        if not solution_path.exists():
            self.add_check('deliverables_list', 'fail', 'Solution outline not found')
            self.add_finding('error', 'Could not list deliverables - solution outline missing')
            return False

        try:
            content = solution_path.read_text()
            sections = parse_document_sections(content)
            # Section keys are lowercase
            deliverables_section = sections.get('deliverables', '')

            if not deliverables_section:
                self.add_check('deliverables_list', 'fail', 'No deliverables section found')
                self.add_finding('error', 'Solution outline has no Deliverables section')
                return False

            deliverables = extract_deliverable_headings(deliverables_section)
            actual_count = len(deliverables)

            if actual_count == 0:
                self.add_check('deliverables_list', 'fail', 'No deliverables found')
                self.add_finding('error', 'Solution outline has no deliverables')
                return False

            if expected_count is not None and actual_count != expected_count:
                if count_check_mode == 'informational':
                    # Informational - note but don't fail
                    self.add_check(
                        'deliverables_count',
                        'info',
                        f'Expected {expected_count} deliverables, found {actual_count} (informational)',
                    )
                    self.add_finding(
                        'info',
                        f'Deliverable count differs: expected {expected_count}, got {actual_count} (packaging difference)',
                    )
                else:
                    # Strict - fail on mismatch
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

    def check_affected_files(self, expected_files: list[str]) -> bool:
        """Check affected files accuracy - the key correctness metric.

        Compares expected affected files against actual affected files in references.toon.
        """
        refs_path = self._get_artifact_path('references.toon')

        if not refs_path.exists():
            self.add_check('affected_files', 'fail', 'References file not found')
            self.add_finding('error', 'Cannot verify affected files - references.toon missing')
            return False

        try:
            content = refs_path.read_text()
            refs = parse_toon_simple(content)

            actual_files = refs.get('affected_files', [])
            if isinstance(actual_files, str):
                actual_files = [actual_files]

            # Clean TOON list formatting - strip leading '- ' if present
            def clean_path(p: str) -> str:
                p = p.strip()
                if p.startswith('- '):
                    p = p[2:]
                return p.strip()

            expected_set = {clean_path(f) for f in expected_files}
            actual_set = {clean_path(f) for f in actual_files}

            # Calculate accuracy metrics
            correct = expected_set & actual_set
            missing = expected_set - actual_set  # False negatives
            extra = actual_set - expected_set  # False positives

            accuracy = len(correct) / len(expected_set) * 100 if expected_set else 100

            # Record detailed results
            if missing:
                self.add_finding('error', f'Missing expected files ({len(missing)}): {sorted(missing)[:5]}...')
            if extra:
                self.add_finding('warning', f'Extra files included ({len(extra)}): {sorted(extra)[:5]}...')

            # Pass if recall >= 90% (found most expected files)
            # Note: precision (false positives) is less critical than recall (false negatives)
            if accuracy >= 90 and not missing:
                self.add_check(
                    'affected_files',
                    'pass',
                    f'Found {len(correct)}/{len(expected_set)} expected files (accuracy: {accuracy:.0f}%)',
                )
                return True
            elif accuracy >= 70:
                self.add_check(
                    'affected_files',
                    'partial',
                    f'Found {len(correct)}/{len(expected_set)} expected files (accuracy: {accuracy:.0f}%)',
                )
                return True  # Partial pass
            else:
                self.add_check(
                    'affected_files',
                    'fail',
                    f'Found only {len(correct)}/{len(expected_set)} expected files (accuracy: {accuracy:.0f}%)',
                )
                return False

        except Exception as e:
            self.add_check('affected_files', 'fail', f'Error checking affected files: {e}')
            self.add_finding('error', str(e))
            return False

    def check_tasks_exist(self, phase: str = 'execute') -> bool:
        """Check if tasks exist for the plan."""
        try:
            tasks_dir = self._get_artifact_path('tasks')

            if not tasks_dir.exists():
                self.add_check('tasks_exist', 'fail', 'Tasks directory not found')
                self.add_finding('warning', f'No tasks found for plan {self.plan_id}')
                return False

            # Count TASK-*.toon files in tasks/ subdirectory
            task_files = list(tasks_dir.glob('TASK-*.toon'))
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
            phases: List of phases to verify ['3-outline', '4-plan']
        """
        if phases is None:
            phases = ['3-outline']

        # Basic existence checks
        self.check_solution_outline_exists()
        self.check_solution_outline_valid()
        self.check_config_exists()
        self.check_status_exists()
        self.check_references_exists()

        # Load expected artifacts for comparison
        expected = self.load_expected_artifacts()

        # Check deliverables - determine if count check is informational
        expected_deliverable_count = None
        count_check_mode = expected.get('deliverable_count_check', 'strict')
        if 'deliverable_count' in expected:
            try:
                expected_deliverable_count = int(expected['deliverable_count'])
            except (ValueError, TypeError):
                pass
        self.check_deliverables_count(expected_deliverable_count, count_check_mode)

        # Check affected files - the key correctness metric
        expected_files = expected.get('affected_files', [])
        if isinstance(expected_files, str):
            expected_files = [expected_files]
        if expected_files:
            self.check_affected_files(expected_files)

        # Check tasks if planning phase included
        if '4-plan' in phases or 'both' in phases:
            self.check_tasks_exist()

        # Calculate overall status (excluding 'info' checks from failure count)
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
    parser.add_argument('--artifacts-dir', help='Directory containing collected artifacts (reads from here instead of plan dir)')
    parser.add_argument('--output', help='Output file path (default: stdout)')
    parser.add_argument('--phases', default='3-outline', help='Phases to verify (comma-separated)')

    args = parser.parse_args()

    test_case_dir = Path(args.test_case)
    if not test_case_dir.exists():
        print(serialize_toon({'status': 'error', 'message': f'Test case not found: {args.test_case}'}))
        return 1

    artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir else None
    if artifacts_dir and not artifacts_dir.exists():
        print(serialize_toon({'status': 'error', 'message': f'Artifacts directory not found: {args.artifacts_dir}'}))
        return 1

    phases = args.phases.split(',')

    checker = StructuralChecker(args.plan_id, test_case_dir, artifacts_dir)
    results = checker.run_all_checks(phases)

    output = serialize_toon(results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
        print(f'Results written to {args.output}')
    else:
        print(output)

    return 0  # Status modeled in output, not exit code


if __name__ == '__main__':
    sys.exit(main())
