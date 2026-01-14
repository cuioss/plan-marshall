#!/usr/bin/env python3
"""Inventory subcommand for scanning skill directories."""

import json
import sys
from collections import defaultdict
from pathlib import Path


def count_lines(file_path: Path) -> int:
    """Count lines in a file."""
    try:
        with open(file_path, encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    try:
        return file_path.stat().st_size
    except OSError:
        return 0


def should_skip_directory(dir_name: str, include_hidden: bool) -> bool:
    """Check if directory should be skipped."""
    skip_dirs = {'__pycache__', 'node_modules', '.git'}
    if dir_name in skip_dirs:
        return True
    if not include_hidden and dir_name.startswith('.'):
        return True
    return False


def should_skip_file(file_name: str, include_hidden: bool) -> bool:
    """Check if file should be skipped."""
    if not include_hidden and file_name.startswith('.'):
        return True
    return False


def scan_directory(skill_path: Path, include_hidden: bool) -> dict:
    """Scan skill directory and return inventory."""
    skill_name = skill_path.name
    abs_skill_path = str(skill_path.resolve())

    directories = []
    root_files = []
    total_dirs = 0
    total_files = 0
    total_lines = 0
    extensions: defaultdict[str, int] = defaultdict(int)

    try:
        for entry in sorted(skill_path.iterdir()):
            if entry.is_dir():
                dir_name = entry.name

                if should_skip_directory(dir_name, include_hidden):
                    continue

                total_dirs += 1
                dir_files = []

                for file_entry in sorted(entry.iterdir()):
                    if not file_entry.is_file():
                        continue

                    file_name = file_entry.name
                    if should_skip_file(file_name, include_hidden):
                        continue

                    total_files += 1
                    lines = count_lines(file_entry)
                    total_lines += lines
                    size = get_file_size(file_entry)

                    if '.' in file_name:
                        ext = '.' + file_name.rsplit('.', 1)[1]
                        extensions[ext] += 1

                    rel_path = str(file_entry.relative_to(skill_path))

                    dir_files.append({'name': file_name, 'path': rel_path, 'lines': lines, 'size_bytes': size})

                directories.append({'name': dir_name, 'path': f'{dir_name}/', 'files': dir_files})

            elif entry.is_file():
                file_name = entry.name
                if should_skip_file(file_name, include_hidden):
                    continue

                total_files += 1
                lines = count_lines(entry)
                total_lines += lines
                size = get_file_size(entry)

                if '.' in file_name:
                    ext = '.' + file_name.rsplit('.', 1)[1]
                    extensions[ext] += 1

                root_files.append({'name': file_name, 'path': file_name, 'lines': lines, 'size_bytes': size})

    except OSError as e:
        return {'error': f'Failed to scan directory: {e}'}

    return {
        'skill_name': skill_name,
        'skill_path': abs_skill_path,
        'directories': directories,
        'root_files': root_files,
        'statistics': {
            'total_directories': total_dirs,
            'total_files': total_files,
            'total_lines': total_lines,
            'by_extension': dict(sorted(extensions.items())),
        },
    }


def cmd_inventory(args) -> int:
    """Scan skill directory and return structured inventory."""
    skill_path = Path(args.skill_path)

    if not skill_path.exists():
        print(json.dumps({'error': f'Directory not found: {args.skill_path}'}), file=sys.stderr)
        return 1

    if not skill_path.is_dir():
        print(json.dumps({'error': f'Not a directory: {args.skill_path}'}), file=sys.stderr)
        return 1

    skill_path = skill_path.resolve()
    result = scan_directory(skill_path, args.include_hidden)

    if 'error' in result:
        print(json.dumps(result), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0
