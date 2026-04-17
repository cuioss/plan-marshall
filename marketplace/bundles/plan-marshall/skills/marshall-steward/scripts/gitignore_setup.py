#!/usr/bin/env python3
"""
Configure .gitignore for the planning system.

Ensures .plan/* contents are ignored while tracked files (marshal.json,
project-architecture/) remain visible. Runtime state (plans,
archived-plans, run-configuration.json, lessons-learned, memory, logs)
lives at ``<root>/.plan/local/`` — already covered by the ``.plan/*``
rule, but an adjacent documentation comment is emitted so readers of
the generated .gitignore understand the layout.

Uses .plan/* (not .plan/) to allow exceptions - .plan/ ignores the entire
directory making exceptions impossible.

Usage:
    python3 gitignore_setup.py [--dry-run]

Options:
    --dry-run              Show what would be done without making changes

Output (TOON format):
    status	created
    gitignore_path	/path/to/.gitignore
    entries_added	4

    status	updated
    gitignore_path	/path/to/.gitignore
    entries_added	1

    status	unchanged
    gitignore_path	/path/to/.gitignore
    entries_added	0
"""

import argparse
import sys
from pathlib import Path

# Bootstrap sys.path — this script runs before the executor sets up PYTHONPATH.
# Step 1: locate script-shared/scripts via identity walk so we can import the
# shared anchor helper. Step 2: use resolve_skills_root to derive _SKILLS_DIR.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _shared_scripts = str(_ancestor / 'script-shared' / 'scripts')
        if _shared_scripts not in sys.path:
            sys.path.insert(0, _shared_scripts)
        break

from marketplace_bundles import resolve_skills_root  # type: ignore[import-not-found]  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format',):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402

# Lines to add to .gitignore
# Use .plan/* (not .plan/) to allow exceptions - .plan/ ignores entire directory
GITIGNORE_COMMENT = '# Planning system (managed by /marshall-steward)'
GITIGNORE_LOCAL_COMMENT = (
    '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
    '— managed by plan-marshall)'
)
GITIGNORE_PLAN_DIR = '.plan/*'
GITIGNORE_MARSHAL_EXCEPTION = '!.plan/marshal.json'
GITIGNORE_ARCHITECTURE_EXCEPTION = '!.plan/project-architecture/'
GITIGNORE_CLAUDE_WORKTREES = '.claude/worktrees/'


def check_gitignore_status(gitignore_path: Path) -> dict:
    """
    Check current state of .gitignore regarding .plan/ entries.

    Args:
        gitignore_path: Path to .gitignore file

    Returns:
        Dict with:
        - exists: bool
        - has_plan_dir: bool
        - has_marshal_exception: bool
        - has_architecture_exception: bool
        - content: str (if exists)
    """
    exists = gitignore_path.exists()
    has_plan_dir = False
    has_marshal_exception = False
    has_architecture_exception = False
    has_claude_worktrees = False
    has_local_comment = False
    content = ''

    if exists:
        content = gitignore_path.read_text()
        lines = content.splitlines()

        for line in lines:
            stripped = line.strip()
            # Accept .plan/* (preferred) and .plan/ or .plan (older format)
            if stripped in ('.plan/*', '.plan/', '.plan'):
                has_plan_dir = True
            if stripped == GITIGNORE_MARSHAL_EXCEPTION:
                has_marshal_exception = True
            if stripped == GITIGNORE_ARCHITECTURE_EXCEPTION:
                has_architecture_exception = True
            # Accept .claude/worktrees/ (preferred) and .claude/worktrees (no trailing slash)
            if stripped in ('.claude/worktrees/', '.claude/worktrees'):
                has_claude_worktrees = True
            if stripped == GITIGNORE_LOCAL_COMMENT:
                has_local_comment = True

    return {
        'exists': exists,
        'has_plan_dir': has_plan_dir,
        'has_marshal_exception': has_marshal_exception,
        'has_architecture_exception': has_architecture_exception,
        'has_claude_worktrees': has_claude_worktrees,
        'has_local_comment': has_local_comment,
        'content': content,
    }


def setup_gitignore(project_root: Path, dry_run: bool = False) -> dict:
    """
    Configure .gitignore for planning system.

    Args:
        project_root: Project root directory containing .gitignore
        dry_run: If True, don't make changes

    Returns:
        Dict with status, path, and entries_added count
    """
    gitignore_path = project_root / '.gitignore'
    status = check_gitignore_status(gitignore_path)

    entries_to_add = []

    if not status['has_plan_dir']:
        entries_to_add.append(GITIGNORE_PLAN_DIR)
    if not status['has_marshal_exception']:
        entries_to_add.append(GITIGNORE_MARSHAL_EXCEPTION)
    if not status['has_architecture_exception']:
        entries_to_add.append(GITIGNORE_ARCHITECTURE_EXCEPTION)
    if not status['has_claude_worktrees']:
        entries_to_add.append(GITIGNORE_CLAUDE_WORKTREES)

    needs_local_comment = not status['has_local_comment']

    result = {
        'gitignore_path': str(gitignore_path.absolute()),
        'entries_added': len(entries_to_add),
        'dry_run': dry_run,
    }

    if not entries_to_add and not needs_local_comment:
        result['status'] = 'unchanged'
        return result

    if not status['exists']:
        # Create new .gitignore
        result['status'] = 'created'
        new_content = (
            f'{GITIGNORE_COMMENT}\n'
            f'{GITIGNORE_LOCAL_COMMENT}\n'
            f'{GITIGNORE_PLAN_DIR}\n'
            f'{GITIGNORE_MARSHAL_EXCEPTION}\n'
            f'{GITIGNORE_ARCHITECTURE_EXCEPTION}\n'
            f'{GITIGNORE_CLAUDE_WORKTREES}\n'
        )
    else:
        # Update existing .gitignore
        result['status'] = 'updated'
        content = status['content']

        # Ensure content ends with newline
        if content and not content.endswith('\n'):
            content += '\n'

        # Add blank line before comment if content exists and doesn't end with blank line
        if content and not content.endswith('\n\n'):
            content += '\n'

        # Add comment and entries (include the local-state doc comment too)
        content += f'{GITIGNORE_COMMENT}\n'
        if needs_local_comment:
            content += f'{GITIGNORE_LOCAL_COMMENT}\n'
        for entry in entries_to_add:
            content += f'{entry}\n'

        new_content = content

    if not dry_run:
        gitignore_path.write_text(new_content)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Configure .gitignore for planning system', allow_abbrev=False
    )
    parser.add_argument(
        '--project-root', type=str, default='.', help='Project root directory (default: current directory)'
    )
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()
    project_root = Path(args.project_root)

    if not project_root.exists():
        result = {'status': 'error', 'error': 'project_root_not_found', 'path': str(project_root)}
    else:
        result = setup_gitignore(project_root, args.dry_run)
        result.setdefault('status', 'success')

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
