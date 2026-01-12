#!/usr/bin/env python3
"""Stats subcommand for documentation statistics."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 2

# Color codes
BLUE = '\033[0;34m'
NC = '\033[0m'


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    if size > 1048576:
        return f"{size // 1048576} MB"
    elif size > 1024:
        return f"{size // 1024} KB"
    else:
        return f"{size} B"


def analyze_file_stats(file_path: Path) -> dict:
    """Analyze a single AsciiDoc file and return statistics."""
    content = file_path.read_text(encoding='utf-8', errors='replace')
    lines = content.split('\n')

    stats = {
        'file': str(file_path),
        'lines': len(lines),
        'words': len(content.split()),
        'size': file_path.stat().st_size,
        'sections': 0,
        'max_depth': 0,
        'xrefs': 0,
        'images': 0,
        'code_blocks': 0,
        'tables': 0,
        'lists': 0,
    }

    section_pattern = re.compile(r'^(=+) ')
    for line in lines:
        match = section_pattern.match(line)
        if match:
            stats['sections'] += 1
            depth = len(match.group(1))
            if depth > stats['max_depth']:
                stats['max_depth'] = depth

    stats['xrefs'] = len(re.findall(r'xref:', content))
    stats['images'] = len(re.findall(r'image::', content))
    stats['code_blocks'] = len(re.findall(r'^\[source', content, re.MULTILINE))
    stats['tables'] = len(re.findall(r'^\|===', content, re.MULTILINE))
    stats['lists'] = len(re.findall(r'^[[:space:]]*(\*|[0-9]+\.|.*::)', content, re.MULTILINE))

    return stats


def cmd_stats(args):
    """Handle stats subcommand."""
    target_dir = Path(args.directory)

    if not target_dir.is_dir():
        print(f"Error: Directory '{target_dir}' does not exist")
        return EXIT_ERROR

    file_stats = []
    dir_stats = {}
    totals = {'lines': 0, 'words': 0, 'sections': 0, 'xrefs': 0, 'images': 0, 'code_blocks': 0, 'tables': 0, 'lists': 0}

    for file_path in sorted(target_dir.rglob('*.adoc')):
        stats = analyze_file_stats(file_path)
        file_stats.append(stats)

        for key in totals:
            totals[key] += stats.get(key, 0)

        dir_name = str(file_path.parent)
        if dir_name not in dir_stats:
            dir_stats[dir_name] = {'files': 0, 'lines': 0, 'words': 0, 'size': 0}
        dir_stats[dir_name]['files'] += 1
        dir_stats[dir_name]['lines'] += stats['lines']
        dir_stats[dir_name]['words'] += stats['words']
        dir_stats[dir_name]['size'] += stats['size']

    total_files = len(file_stats)

    if args.format == 'json':
        output = {
            'metadata': {'directory': str(target_dir), 'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'total_files': total_files},
            'summary': {**totals, 'averages': {'lines_per_file': totals['lines'] // total_files if total_files else 0, 'words_per_file': totals['words'] // total_files if total_files else 0}},
            'directories': dir_stats,
        }
        if args.details:
            output['files'] = {s['file']: {k: v for k, v in s.items() if k != 'file'} for s in file_stats}
        print(json.dumps(output, indent=2))
    else:
        print(f"{BLUE}Documentation Statistics{NC}")
        print("=" * 30)
        print(f"Directory: {target_dir}")
        print(f"Total files: {total_files}")
        print(f"Total lines: {totals['lines']:,}")
        print(f"Total words: {totals['words']:,}")

    return EXIT_SUCCESS
