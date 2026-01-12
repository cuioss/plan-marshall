#!/usr/bin/env python3
"""Format subcommand for auto-fixing AsciiDoc formatting issues."""

import re
import shutil
from pathlib import Path
from typing import Tuple

from plan_logging import log_entry  # type: ignore[import-not-found]

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 2

# Color codes
GREEN = '\033[0;32m'
NC = '\033[0m'


def fix_lists(content: str) -> Tuple[str, int]:
    """Fix list formatting by adding blank lines before lists."""
    lines = content.split('\n')
    result = []
    fixed_count = 0
    in_code_block = False
    prev_was_blank = True
    in_list = False

    for i, line in enumerate(lines):
        if line == '----':
            in_code_block = not in_code_block
        current_is_blank = len(line.strip()) == 0

        starts_new_list = False
        if not in_code_block:
            if re.match(r'^[\*\-\+] ', line) or re.match(r'^[0-9]+\. ', line) or re.match(r'^[^:]+::', line) or (re.match(r'^\. ', line) and not in_list):
                starts_new_list = True

        continuing_list = False
        if not in_code_block and in_list:
            if re.match(r'^[\*\-\+] ', line) or re.match(r'^\*\* ', line) or re.match(r'^[0-9]+\. ', line) or current_is_blank:
                continuing_list = True

        if starts_new_list and not prev_was_blank and i > 0 and not in_list:
            result.append('')
            fixed_count += 1

        result.append(line)

        if starts_new_list:
            in_list = True
        elif not continuing_list and not current_is_blank:
            in_list = False

        prev_was_blank = current_is_blank

    return '\n'.join(result), fixed_count


def fix_xrefs(content: str) -> Tuple[str, int]:
    """Fix cross-references by converting <<>> syntax to xref:."""
    pattern = r'<<([^,>]*),([^>]*)>>'
    fixed_content, count = re.subn(pattern, r'xref:\1[\2]', content)
    return fixed_content, count


def fix_whitespace(content: str) -> Tuple[str, int]:
    """Fix whitespace issues."""
    original = content
    lines = [line.rstrip() for line in content.split('\n')]
    content = '\n'.join(lines)
    if not content.endswith('\n'):
        content += '\n'
    return content, 1 if content != original else 0


def cmd_format(args):
    """Handle format subcommand."""
    target_path = Path(args.path)

    if not target_path.exists():
        print(f"Error: Path '{target_path}' does not exist")
        return EXIT_ERROR

    files_processed = 0
    files_modified = 0
    issues_fixed = 0
    fix_types = args.fix_types if args.fix_types else ['all']

    def process_file(file_path: Path):
        nonlocal files_processed, files_modified, issues_fixed
        files_processed += 1
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        file_issues = 0

        if 'all' in fix_types or 'lists' in fix_types:
            content, count = fix_lists(content)
            file_issues += count
        if 'all' in fix_types or 'xref' in fix_types:
            content, count = fix_xrefs(content)
            file_issues += count
        if 'all' in fix_types or 'whitespace' in fix_types:
            content, count = fix_whitespace(content)
            file_issues += count

        if content != original_content:
            files_modified += 1
            issues_fixed += file_issues
            if not args.no_backup:
                shutil.copy2(file_path, file_path.with_suffix(file_path.suffix + '.bak'))
            file_path.write_text(content, encoding='utf-8')
            print(f"{GREEN}Fixed: {file_path}{NC}")

    if target_path.is_file():
        if target_path.suffix == '.adoc':
            process_file(target_path)
    else:
        for file_path in sorted(target_path.rglob('*.adoc')):
            process_file(file_path)

    if files_modified > 0:
        log_entry('script', 'global', 'INFO', f'[DOCS-FORMAT] Formatted {files_modified} files, fixed {issues_fixed} issues')

    print(f"\nSummary: {files_processed} processed, {files_modified} modified, {issues_fixed} issues fixed")
    return EXIT_SUCCESS
