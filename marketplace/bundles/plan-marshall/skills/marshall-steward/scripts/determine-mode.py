#!/usr/bin/env python3
"""
Plan-marshall helper script for mode detection and documentation checks.

Subcommands:
    mode            Determine wizard vs menu mode based on existing files
    check-docs      Check if project docs need .plan/temp documentation
    check-structure Check if project-architecture directory exists

Usage:
    python3 determine-mode.py mode
    python3 determine-mode.py check-docs
    python3 determine-mode.py check-structure

Output (TOON format):
    mode subcommand:
        mode	wizard
        reason	executor_missing

    check-docs subcommand:
        status	ok
        files_needing_update	0

        status	needs_update
        files_needing_update	2
        missing	CLAUDE.md,agents.md

    check-structure subcommand:
        status	exists
        path	.plan/project-architecture

        status	missing
        path	.plan/project-architecture
"""

import argparse
import sys
from pathlib import Path


def determine_mode(plan_dir: Path) -> tuple[str, str]:
    """
    Determine operational mode based on existing files.

    Args:
        plan_dir: Path to the .plan directory

    Returns:
        Tuple of (mode, reason) where mode is 'wizard' or 'menu'
    """
    executor_path = plan_dir / 'execute-script.py'
    marshal_path = plan_dir / 'marshal.json'

    executor_exists = executor_path.exists()
    marshal_exists = marshal_path.exists()

    if not executor_exists:
        return 'wizard', 'executor_missing'
    elif not marshal_exists:
        return 'wizard', 'marshal_missing'
    else:
        return 'menu', 'both_exist'


def check_structure(plan_dir: Path) -> tuple[str, Path]:
    """
    Check if project-architecture directory exists with derived-data.json.

    Args:
        plan_dir: Path to the .plan directory

    Returns:
        Tuple of (status, path) where status is 'exists' or 'missing'
    """
    arch_dir = plan_dir / 'project-architecture'
    derived_path = arch_dir / 'derived-data.json'

    if derived_path.exists():
        return 'exists', arch_dir
    else:
        return 'missing', arch_dir


def check_docs(project_root: Path) -> tuple[str, list[str]]:
    """
    Check if project documentation files need .plan/temp documentation.

    Args:
        project_root: Path to the project root

    Returns:
        Tuple of (status, list of files needing update)
    """
    docs_to_check = ['CLAUDE.md', 'agents.md']
    pattern = '.plan/temp'
    missing = []

    for doc_name in docs_to_check:
        doc_path = project_root / doc_name
        if doc_path.exists():
            content = doc_path.read_text()
            if pattern not in content:
                missing.append(doc_name)

    if missing:
        return 'needs_update', missing
    else:
        return 'ok', []


def cmd_mode(args: argparse.Namespace) -> int:
    """Handle the 'mode' subcommand."""
    plan_dir = Path(args.plan_dir)
    mode, reason = determine_mode(plan_dir)

    print(f'mode\t{mode}')
    print(f'reason\t{reason}')
    return 0


def cmd_check_docs(args: argparse.Namespace) -> int:
    """Handle the 'check-docs' subcommand."""
    project_root = Path(args.project_root)
    status, missing = check_docs(project_root)

    print(f'status\t{status}')
    print(f'files_needing_update\t{len(missing)}')
    if missing:
        print(f'missing\t{",".join(missing)}')
    return 0


def cmd_check_structure(args: argparse.Namespace) -> int:
    """Handle the 'check-structure' subcommand."""
    plan_dir = Path(args.plan_dir)
    status, path = check_structure(plan_dir)

    print(f'status\t{status}')
    print(f'path\t{path}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Plan-marshall helper for mode detection and documentation checks')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # mode subcommand
    mode_parser = subparsers.add_parser('mode', help='Determine wizard vs menu mode')
    mode_parser.add_argument('--plan-dir', type=str, default='.plan', help='Directory to check (default: .plan)')

    # check-docs subcommand
    docs_parser = subparsers.add_parser('check-docs', help='Check if project docs need .plan/temp documentation')
    docs_parser.add_argument('--project-root', type=str, default='.', help='Project root directory (default: .)')

    # check-structure subcommand
    structure_parser = subparsers.add_parser('check-structure', help='Check if project-architecture directory exists')
    structure_parser.add_argument('--plan-dir', type=str, default='.plan', help='Directory to check (default: .plan)')

    args = parser.parse_args()

    if args.command == 'mode':
        return cmd_mode(args)
    elif args.command == 'check-docs':
        return cmd_check_docs(args)
    elif args.command == 'check-structure':
        return cmd_check_structure(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
