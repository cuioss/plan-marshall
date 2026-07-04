#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    entries_added	5

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

from marketplace_bundles import resolve_skills_root  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format',):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

from toon_parser import serialize_toon  # noqa: E402

# Lines to add to .gitignore
# Use .plan/* (not .plan/) to allow exceptions - .plan/ ignores entire directory
GITIGNORE_COMMENT = '# Planning system (managed by /marshall-steward)'
GITIGNORE_LOCAL_COMMENT = (
    '# Runtime state (plans, run-configuration, lessons-learned, memory, logs — managed by plan-marshall)'
)
GITIGNORE_PLAN_DIR = '.plan/*'
GITIGNORE_MARSHAL_EXCEPTION = '!.plan/marshal.json'
GITIGNORE_ARCHITECTURE_EXCEPTION = '!.plan/project-architecture/'
GITIGNORE_PLUGIN_DOCTOR_EXCEPTION = '!.plan/plugin-doctor.yml'
GITIGNORE_PLAN_LOCAL_WORKTREES = '.plan/local/worktrees/'

# Lines that belong to the managed block: the two header comments plus every
# recognized managed rule (including the older accepted variants). Any line
# whose stripped form is in this set is part of the managed block and is
# subject to consolidation; everything else is user-authored content that is
# preserved verbatim.
_MANAGED_COMMENT_LINES = frozenset({GITIGNORE_COMMENT, GITIGNORE_LOCAL_COMMENT})
_MANAGED_RULE_LINES = frozenset({
    GITIGNORE_PLAN_DIR,
    '.plan/',
    '.plan',
    GITIGNORE_MARSHAL_EXCEPTION,
    GITIGNORE_ARCHITECTURE_EXCEPTION,
    GITIGNORE_PLUGIN_DOCTOR_EXCEPTION,
    GITIGNORE_PLAN_LOCAL_WORKTREES,
    '.plan/local/worktrees',
})


def consolidate_managed_blocks(content: str) -> str:
    """
    Merge every managed ``.gitignore`` block into a single managed block.

    A managed line is one whose stripped form is either a managed header
    comment (``_MANAGED_COMMENT_LINES``) or a recognized managed rule
    (``_MANAGED_RULE_LINES``). Pre-PR#666 projects accumulated several
    ``GITIGNORE_COMMENT`` headers (one per re-run); this pass collects the
    union of managed rules across all blocks, de-duplicated and order-stable,
    and re-emits a single managed block at the position of the first managed
    line. User-authored content outside the managed lines is preserved
    verbatim in its original relative order.

    An already-single-block file is left byte-stable: the rebuilt content is
    identical to the input, so callers can compare for the ``unchanged``
    status contract.

    Args:
        content: Current ``.gitignore`` text.

    Returns:
        The consolidated ``.gitignore`` text.
    """
    if not content:
        return content

    trailing_newline = content.endswith('\n')
    lines = content.splitlines()

    seen_rules: set[str] = set()
    ordered_rules: list[str] = []
    first_managed_index: int | None = None
    user_lines: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped in _MANAGED_COMMENT_LINES:
            if first_managed_index is None:
                first_managed_index = index
            continue
        if stripped in _MANAGED_RULE_LINES:
            if first_managed_index is None:
                first_managed_index = index
            if stripped not in seen_rules:
                seen_rules.add(stripped)
                ordered_rules.append(stripped)
            continue
        user_lines.append((index, line))

    # No managed lines at all — nothing to consolidate.
    if first_managed_index is None:
        return content

    # Canonical managed block: both header comments, then the managed rules in
    # the canonical order they were first encountered across all blocks.
    managed_block = [GITIGNORE_COMMENT, GITIGNORE_LOCAL_COMMENT, *ordered_rules]

    # Splice: emit user lines that appeared before the first managed line,
    # then the single consolidated managed block, then the remaining user
    # lines — preserving the user content's relative order.
    before = [line for idx, line in user_lines if idx < first_managed_index]
    after = [line for idx, line in user_lines if idx > first_managed_index]

    rebuilt_lines = [*before, *managed_block, *after]
    rebuilt = '\n'.join(rebuilt_lines)
    if trailing_newline and rebuilt:
        rebuilt += '\n'
    return rebuilt


def check_gitignore_status_from_content(content: str, exists: bool = True) -> dict:
    """
    Classify managed-entry presence from already-loaded ``.gitignore`` text.

    Shared parser behind :func:`check_gitignore_status` and the
    post-consolidation re-check in :func:`setup_gitignore`. Operating on a
    string lets the consolidation pass re-derive presence flags without a
    second filesystem read.

    Args:
        content: ``.gitignore`` text (empty string when the file is absent).
        exists: Whether the source file exists on disk.

    Returns:
        Dict with the same presence flags as :func:`check_gitignore_status`.
    """
    has_plan_dir = False
    has_marshal_exception = False
    has_architecture_exception = False
    has_plugin_doctor_exception = False
    has_plan_local_worktrees = False
    has_managed_comment = False
    has_local_comment = False

    for line in content.splitlines():
        stripped = line.strip()
        # Accept .plan/* (preferred) and .plan/ or .plan (older format)
        if stripped in ('.plan/*', '.plan/', '.plan'):
            has_plan_dir = True
        if stripped == GITIGNORE_MARSHAL_EXCEPTION:
            has_marshal_exception = True
        if stripped == GITIGNORE_ARCHITECTURE_EXCEPTION:
            has_architecture_exception = True
        if stripped == GITIGNORE_PLUGIN_DOCTOR_EXCEPTION:
            has_plugin_doctor_exception = True
        # Accept .plan/local/worktrees/ (preferred) and .plan/local/worktrees (no trailing slash)
        if stripped in ('.plan/local/worktrees/', '.plan/local/worktrees'):
            has_plan_local_worktrees = True
        if stripped == GITIGNORE_COMMENT:
            has_managed_comment = True
        if stripped == GITIGNORE_LOCAL_COMMENT:
            has_local_comment = True

    return {
        'exists': exists,
        'has_plan_dir': has_plan_dir,
        'has_marshal_exception': has_marshal_exception,
        'has_architecture_exception': has_architecture_exception,
        'has_plugin_doctor_exception': has_plugin_doctor_exception,
        'has_plan_local_worktrees': has_plan_local_worktrees,
        'has_managed_comment': has_managed_comment,
        'has_local_comment': has_local_comment,
        'content': content,
    }


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
        - has_plugin_doctor_exception: bool
        - content: str (if exists)
    """
    exists = gitignore_path.exists()
    content = gitignore_path.read_text() if exists else ''
    return check_gitignore_status_from_content(content, exists=exists)


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

    result = {
        'gitignore_path': str(gitignore_path.absolute()),
        'dry_run': dry_run,
    }

    if not status['exists']:
        # Create new .gitignore — a fresh file is a single managed block.
        new_content = (
            f'{GITIGNORE_COMMENT}\n'
            f'{GITIGNORE_LOCAL_COMMENT}\n'
            f'{GITIGNORE_PLAN_DIR}\n'
            f'{GITIGNORE_MARSHAL_EXCEPTION}\n'
            f'{GITIGNORE_ARCHITECTURE_EXCEPTION}\n'
            f'{GITIGNORE_PLUGIN_DOCTOR_EXCEPTION}\n'
            f'{GITIGNORE_PLAN_LOCAL_WORKTREES}\n'
        )
        result['status'] = 'created'
        result['entries_added'] = 5
        if not dry_run:
            gitignore_path.write_text(new_content)
        return result

    original_content = status['content']

    # Consolidation pass (unconditional): merge any duplicate managed blocks
    # into one before adding missing entries. An already-single-block file is
    # left byte-stable by this pass.
    consolidated = consolidate_managed_blocks(original_content)

    # Re-derive managed-rule presence against the consolidated content so the
    # missing-entry computation reflects the post-consolidation state (a rule
    # present in any of the duplicate blocks survives consolidation).
    consolidated_status = check_gitignore_status_from_content(consolidated)

    entries_to_add = []
    if not consolidated_status['has_plan_dir']:
        entries_to_add.append(GITIGNORE_PLAN_DIR)
    if not consolidated_status['has_marshal_exception']:
        entries_to_add.append(GITIGNORE_MARSHAL_EXCEPTION)
    if not consolidated_status['has_architecture_exception']:
        entries_to_add.append(GITIGNORE_ARCHITECTURE_EXCEPTION)
    if not consolidated_status['has_plugin_doctor_exception']:
        entries_to_add.append(GITIGNORE_PLUGIN_DOCTOR_EXCEPTION)
    if not consolidated_status['has_plan_local_worktrees']:
        entries_to_add.append(GITIGNORE_PLAN_LOCAL_WORKTREES)

    needs_managed_comment = not consolidated_status['has_managed_comment']
    needs_local_comment = not consolidated_status['has_local_comment']

    content = consolidated

    if entries_to_add or needs_managed_comment or needs_local_comment:
        # Ensure content ends with newline
        if content and not content.endswith('\n'):
            content += '\n'

        # Add blank line before comment if content exists and doesn't end with blank line
        if content and not content.endswith('\n\n'):
            content += '\n'

        # Add comment and entries (include the local-state doc comment too).
        # Emit the managed-comment header only when it is not already present so
        # a re-run does not duplicate it.
        if needs_managed_comment:
            content += f'{GITIGNORE_COMMENT}\n'
        if needs_local_comment:
            content += f'{GITIGNORE_LOCAL_COMMENT}\n'
        for entry in entries_to_add:
            content += f'{entry}\n'

        # Re-consolidate so freshly-appended managed entries are pulled into the
        # single canonical managed block in THIS run. Without this, a newly-added
        # managed rule lands after a blank-line separator and the NEXT run's
        # consolidation pass would relocate it into the block — making the add
        # non-idempotent (the second run reports 'updated'). Re-consolidating here
        # makes the first run's output already-canonical and every later run
        # byte-stable.
        content = consolidate_managed_blocks(content)

    result['entries_added'] = len(entries_to_add)

    if content == original_content:
        # No consolidation drift and no missing entries — byte-stable.
        result['status'] = 'unchanged'
        return result

    result['status'] = 'updated'
    if not dry_run:
        gitignore_path.write_text(content)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Configure .gitignore for planning system', allow_abbrev=False)
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
