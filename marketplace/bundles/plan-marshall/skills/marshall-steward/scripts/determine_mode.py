#!/usr/bin/env python3
"""
Plan-marshall helper script for mode detection and documentation checks.

Subcommands:
    mode            Determine wizard vs menu mode based on existing files
    check-docs      Check if project docs need .plan/temp documentation
    fix-docs        Deterministically fix missing documentation content
    check-structure Check if project-architecture directory exists

Note: check-docs and check-structure overlap with menu-healthcheck steps 2 and 5.
The healthcheck runs these same checks via the menu path; this script provides
direct CLI access for the wizard flow and first-run bootstrap (before the
executor exists).

Usage:
    python3 determine_mode.py mode
    python3 determine_mode.py check-docs
    python3 determine_mode.py fix-docs
    python3 determine_mode.py check-structure

Output (TOON format):
    mode subcommand:
        mode	wizard
        reason	executor_missing

    check-docs subcommand:
        status	ok
        missing_count	0

        status	needs_update
        missing_count	2
        plan_temp	CLAUDE.md,agents.md
        file_ops	CLAUDE.md
        workflow_discipline	CLAUDE.md

    fix-docs subcommand:
        status	ok
        fixed_count	0

        status	fixed
        fixed_count	2
        fixes	plan_temp:CLAUDE.md,file_ops:CLAUDE.md

    check-structure subcommand:
        status	exists
        path	.plan/project-architecture

        status	missing
        path	.plan/project-architecture
"""

import argparse
import sys
from pathlib import Path

# Bootstrap sys.path — this script runs before the executor sets up PYTHONPATH.
# Resolve shared library paths relative to this script's location in the plugin tree:
#   skills/marshall-steward/scripts/ → skills/{lib}/scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPTS_DIR.parent.parent
for _lib in ('ref-toon-format',):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

# Content checks applied to project documentation files.
# Each check has a key, the files it applies to, and a substring marker
# to search for (plain string match, not regex).
CONTENT_CHECKS: list[dict[str, str | list[str]]] = [
    {
        'key': 'plan_temp',
        'files': ['CLAUDE.md', 'agents.md'],
        'pattern': '.plan/temp',
    },
    {
        'key': 'file_ops',
        'files': ['CLAUDE.md'],
        'pattern': 'use Glob, Read, Grep',
    },
    {
        'key': 'workflow_discipline',
        'files': ['CLAUDE.md'],
        'pattern': 'Workflow Discipline',
    },
]

# Verbatim content blocks appended by fix-docs when a check is missing.
# Keys must match CONTENT_CHECKS keys. Values are the exact text to append.
FIX_CONTENT: dict[str, str] = {
    'plan_temp': (
        '\n## Temporary Files\n'
        '\n'
        'Use `.plan/temp/` for ALL temporary and generated files '
        '(covered by `Write(.plan/**)` permission — avoids permission prompts).\n'
    ),
    'file_ops': (
        '\n## Tool Usage\n'
        '\n'
        '- Use proper tools (Edit, Read, Write) instead of shell commands (echo, cat)\n'
        '- Never use Bash for file operations (find, grep, cat, ls) — use Glob, Read, Grep tools instead\n'
    ),
    'workflow_discipline': (
        '\n### Workflow Discipline (Hard Rules)\n'
        '\n'
        '- **Bash: one command per call** — Each Bash call must contain exactly ONE command. '
        'Never combine with `&&`, `;`, `&`, or newlines.\n'
        '- **Bash: no shell constructs** — No `for`/`while` loops, no `$()` substitution, '
        'no subshells, no heredocs with `#` lines. These trigger security prompts. '
        'Use dedicated tools or multiple Bash calls instead.\n'
        '- **Workflow steps: no improvisation** — When following a skill or workflow, '
        'execute ONLY the commands documented in it. Never add discovery steps, '
        'invent arguments, or skip documented steps.\n'
    ),
}


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


def check_docs(project_root: Path) -> tuple[str, list[dict[str, str]]]:
    """
    Check if project documentation files contain all required content.

    Checks multiple content patterns across documentation files.
    Each check has a key, target files, and a marker pattern.

    Args:
        project_root: Path to the project root

    Returns:
        Tuple of (status, list of missing check dicts with 'file' and 'check' keys)
    """
    missing: list[dict[str, str]] = []

    for check in CONTENT_CHECKS:
        pattern = str(check['pattern'])
        files = check['files']
        assert isinstance(files, list)
        for file_name in files:
            file_path = project_root / str(file_name)
            if not file_path.exists():
                continue  # Skip non-existent files — only check content in existing files
            else:
                content = file_path.read_text()
                if pattern not in content:
                    missing.append({'file': str(file_name), 'check': str(check['key']), 'reason': 'content_missing'})

    if missing:
        return 'needs_update', missing
    else:
        return 'ok', []


def fix_docs(project_root: Path) -> tuple[str, list[str]]:
    """
    Deterministically fix missing documentation content.

    Runs check_docs to find missing content, then appends the exact
    verbatim text from FIX_CONTENT to the appropriate files.

    Args:
        project_root: Path to the project root

    Returns:
        Tuple of (status, list of fix descriptions like 'plan_temp:CLAUDE.md')
    """
    status, missing = check_docs(project_root)
    if status == 'ok':
        return 'ok', []

    fixes: list[str] = []
    for entry in missing:
        check_key = entry['check']
        file_name = entry['file']
        content_block = FIX_CONTENT.get(check_key)
        if content_block is None:
            continue

        file_path = project_root / file_name
        if not file_path.exists():
            continue

        existing = file_path.read_text()
        # Ensure trailing newline before appending
        if existing and not existing.endswith('\n'):
            existing += '\n'
        file_path.write_text(existing + content_block)
        fixes.append(f'{check_key}:{file_name}')

    return 'fixed' if fixes else 'ok', fixes


def cmd_fix_docs(args: argparse.Namespace) -> dict:
    """Handle the 'fix-docs' subcommand."""
    project_root = Path(args.project_root)
    status, fixes = fix_docs(project_root)

    result: dict = {'status': 'success', 'fix_status': status, 'fixed_count': len(fixes)}
    if fixes:
        result['fixes'] = ','.join(fixes)
    return result


def cmd_mode(args: argparse.Namespace) -> dict:
    """Handle the 'mode' subcommand."""
    plan_dir = Path(args.plan_dir)
    mode, reason = determine_mode(plan_dir)

    return {'status': 'success', 'mode': mode, 'reason': reason}


def cmd_check_docs(args: argparse.Namespace) -> dict:
    """Handle the 'check-docs' subcommand."""
    project_root = Path(args.project_root)
    status, missing = check_docs(project_root)

    result: dict = {'status': 'success', 'check_status': status, 'missing_count': len(missing)}
    if missing:
        # Group by check key for easy consumption
        checks_by_key: dict[str, list[str]] = {}
        for entry in missing:
            key = entry['check']
            if key not in checks_by_key:
                checks_by_key[key] = []
            checks_by_key[key].append(entry['file'])
        for key, files in checks_by_key.items():
            result[key] = ','.join(files)
    return result


def cmd_check_structure(args: argparse.Namespace) -> dict:
    """Handle the 'check-structure' subcommand."""
    plan_dir = Path(args.plan_dir)
    status, path = check_structure(plan_dir)

    return {'status': 'success', 'check_status': status, 'path': str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description='Plan-marshall helper for mode detection and documentation checks')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # mode subcommand
    mode_parser = subparsers.add_parser('mode', help='Determine wizard vs menu mode')
    mode_parser.add_argument('--plan-dir', type=str, default='.plan', help='Directory to check (default: .plan)')

    # check-docs subcommand
    docs_parser = subparsers.add_parser('check-docs', help='Check if project docs need .plan/temp documentation')
    docs_parser.add_argument('--project-root', type=str, default='.', help='Project root directory (default: .)')

    # fix-docs subcommand
    fix_parser = subparsers.add_parser('fix-docs', help='Deterministically fix missing documentation content')
    fix_parser.add_argument('--project-root', type=str, default='.', help='Project root directory (default: .)')

    # check-structure subcommand
    structure_parser = subparsers.add_parser('check-structure', help='Check if project-architecture directory exists')
    structure_parser.add_argument('--plan-dir', type=str, default='.plan', help='Directory to check (default: .plan)')

    args = parser.parse_args()

    if args.command == 'mode':
        result = cmd_mode(args)
    elif args.command == 'check-docs':
        result = cmd_check_docs(args)
    elif args.command == 'fix-docs':
        result = cmd_fix_docs(args)
    elif args.command == 'check-structure':
        result = cmd_check_structure(args)
    else:
        parser.print_help()
        return 1

    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
