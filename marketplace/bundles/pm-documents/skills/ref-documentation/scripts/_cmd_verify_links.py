#!/usr/bin/env python3
"""Verify-links subcommand for checking AsciiDoc links."""

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from plan_logging import log_entry  # type: ignore[import-not-found]

# Exit codes
EXIT_SUCCESS = 0
EXIT_NON_COMPLIANT = 1
EXIT_ERROR = 2


@dataclass
class Link:
    file: str
    line_num: int
    link_text: str
    link_type: str
    target: str = ''
    anchor: str = ''
    label: str = ''


@dataclass
class Issue:
    file: str
    line_num: int
    link_text: str
    issue_type: str
    description: str
    context: str = ''
    suggested_fix: str = ''


def extract_anchors_from_file(filepath: str) -> set[str]:
    """Extract all valid anchors from an AsciiDoc file."""
    anchors = set()
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        anchors.update(re.findall(r'\[\[([^\]]+)\]\]', line))
        anchors.update(re.findall(r'\[#([^\]]+)\]', line))
        section_match = re.match(r'^(={1,6})\s+(.+)$', line.strip())
        if section_match:
            title = section_match.group(2)
            title = re.sub(r'\{[^\}]+\}', '', title)
            title = re.sub(r'link:https?://[^\[]+\[[^\]]+\]', '', title)
            anchor = title.strip().lower()
            anchor = re.sub(r'[^\w\s-]', '', anchor)
            anchor = re.sub(r'\s+', '-', anchor)
            anchor = re.sub(r'-+', '-', anchor).strip('-')
            if anchor:
                anchors.add(anchor)
    return anchors


def extract_links_from_file(filepath: str) -> list[Link]:
    """Extract all links from an AsciiDoc file."""
    links = []
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith('----') or line.strip().startswith('....'):
            in_code_block = not in_code_block
            continue

        for match in re.finditer(r'<<([^,>]+)(?:,([^>]+))?>>', line):
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=match.group(0),
                    link_type='cross-ref',
                    anchor=match.group(1).strip(),
                    label=match.group(2).strip() if match.group(2) else '',
                )
            )

        for match in re.finditer(r'xref:([^\[]+)\[([^\]]*)\]', line):
            target_full = match.group(1).strip()
            target, anchor = (target_full.split('#', 1) + [''])[:2] if '#' in target_full else (target_full, '')
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=match.group(0),
                    link_type='xref',
                    target=target,
                    anchor=anchor,
                    label=match.group(2).strip(),
                )
            )

        for match in re.finditer(r'<<([^>]*\.adoc[^>]*)>>', line):
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=match.group(0),
                    link_type='deprecated',
                    target=match.group(1),
                )
            )

    return links


def verify_links(files: list[str]) -> tuple[list[Link], list[Issue]]:
    """Verify all links in all files."""
    all_links = []
    issues = []
    anchor_cache = {f: extract_anchors_from_file(f) for f in files}

    for filepath in files:
        links = extract_links_from_file(filepath)
        all_links.extend(links)

        for link in links:
            if link.link_type == 'cross-ref' and link.anchor not in anchor_cache[filepath]:
                issues.append(
                    Issue(
                        file=filepath,
                        line_num=link.line_num,
                        link_text=link.link_text,
                        issue_type='broken',
                        description=f"Anchor '{link.anchor}' not found",
                    )
                )
            elif link.link_type == 'xref':
                target_path = (
                    os.path.normpath(os.path.join(os.path.dirname(filepath), link.target)) if link.target else filepath
                )
                if not os.path.exists(target_path):
                    issues.append(
                        Issue(
                            file=filepath,
                            line_num=link.line_num,
                            link_text=link.link_text,
                            issue_type='broken',
                            description=f"Target file '{target_path}' not found",
                        )
                    )
                elif link.anchor:
                    if target_path not in anchor_cache:
                        anchor_cache[target_path] = extract_anchors_from_file(target_path)
                    if link.anchor not in anchor_cache[target_path]:
                        issues.append(
                            Issue(
                                file=filepath,
                                line_num=link.line_num,
                                link_text=link.link_text,
                                issue_type='broken',
                                description=f"Anchor '{link.anchor}' not found in '{target_path}'",
                            )
                        )
            elif link.link_type == 'deprecated':
                issues.append(
                    Issue(
                        file=filepath,
                        line_num=link.line_num,
                        link_text=link.link_text,
                        issue_type='format_violation',
                        description='Deprecated syntax - use xref:',
                        suggested_fix=f'xref:{link.target.rstrip("#,")}[Label]',
                    )
                )

    return all_links, issues


def cmd_verify_links(args):
    """Handle verify-links subcommand."""
    if args.file and args.directory:
        print('Error: Cannot specify both --file and --directory', file=sys.stderr)
        return EXIT_ERROR

    target_path = args.file if args.file else (args.directory if args.directory else '.')
    recursive = args.recursive if args.directory else (not args.file)

    path = Path(target_path)
    if not path.exists():
        print(f"Error: Path '{target_path}' not found", file=sys.stderr)
        return EXIT_ERROR

    files = []
    if path.is_file():
        files = [str(path)]
    elif recursive:
        files = [str(f) for f in path.rglob('*.adoc') if 'target' not in f.parts]
    else:
        files = [str(f) for f in path.glob('*.adoc')]

    if not files:
        print(f'No AsciiDoc files found in {target_path}', file=sys.stderr)
        return EXIT_ERROR

    all_links, issues = verify_links(files)
    broken = [i for i in issues if i.issue_type == 'broken']
    violations = [i for i in issues if i.issue_type == 'format_violation']

    if issues:
        log_entry(
            'script',
            'global',
            'INFO',
            f'[DOCS-LINKS] Found {len(broken)} broken links, {len(violations)} format violations in {len(files)} files',
        )

    output = {
        'status': 'success' if not issues else 'failure',
        'data': {
            'files_processed': len(files),
            'total_links': len(all_links),
            'broken_links': len(broken),
            'format_violations': len(violations),
            'issues': [
                {
                    'file': i.file,
                    'line': i.line_num,
                    'link': i.link_text,
                    'type': i.issue_type,
                    'description': i.description,
                }
                for i in issues
            ],
        },
        'metrics': {'valid_links': len(all_links) - len(issues)},
    }
    print(json.dumps(output, indent=2))

    if args.report:
        Path(args.report).write_text(json.dumps(output, indent=2))

    return EXIT_SUCCESS if not issues else EXIT_NON_COMPLIANT
