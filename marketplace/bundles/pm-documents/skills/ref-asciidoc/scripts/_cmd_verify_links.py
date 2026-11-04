#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Verify-links subcommand for checking AsciiDoc links."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from plan_logging import log_entry

#: The AsciiDoc ``link:target[label]`` macro. The target must start with a
#: non-space character, so prose such as "see link: <<anchor>>" is not read as a
#: macro whose target is " <<anchor>>".
_LINK_MACRO_RE = re.compile(r'link:([^\[\s][^\[]*?)\[([^\]]*)\]')

#: A target that carries a URI scheme (``https:``, ``mailto:``, ``file:``). The
#: checker performs no network access, so every one of these is an unchecked
#: class rather than a broken or a verified link.
_URI_SCHEME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*:')

#: The class name reported under ``unchecked_link_classes`` for a scheme target.
_EXTERNAL_URL_CLASS = 'external-url'


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

        for match in re.finditer(_LINK_MACRO_RE, line):
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=match.group(0),
                    link_type='link',
                    target=match.group(1).strip(),
                    label=match.group(2).strip(),
                )
            )

    return links


def _link_macro_class(target: str) -> str:
    """The class a ``link:`` target belongs to.

    ``internal-anchor`` for a ``#anchor`` target, ``external-url`` for a target
    carrying a URI scheme, and ``relative-file`` for everything else.
    """
    if target.startswith('#'):
        return 'internal-anchor'
    if _URI_SCHEME_RE.match(target):
        return _EXTERNAL_URL_CLASS
    return 'relative-file'


def summarise_unchecked_link_classes(links: list[Link]) -> list[dict]:
    """One row per class the checker saw but did not verify.

    A ``link:`` target carrying a URI scheme is never fetched, so it is counted
    here instead of being reported as verified. A file with no such link yields
    an empty list — a measured zero, not a missing field.
    """
    rows: dict[str, dict] = {}
    for link in links:
        if link.link_type != 'link':
            continue
        link_class = _link_macro_class(link.target)
        if link_class != _EXTERNAL_URL_CLASS:
            continue
        row = rows.get(link_class)
        if row is None:
            row = rows[link_class] = {
                'class': link_class,
                'count': 0,
                'first': {'file': link.file, 'line': link.line_num, 'link': link.link_text},
            }
        row['count'] += 1
    return [rows[key] for key in sorted(rows)]


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
                target_path = str((Path(filepath).parent / link.target).resolve()) if link.target else filepath
                if not Path(target_path).exists():
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
            elif link.link_type == 'link':
                link_class = _link_macro_class(link.target)
                if link_class == 'internal-anchor':
                    anchor = link.target[1:]
                    if anchor not in anchor_cache[filepath]:
                        issues.append(
                            Issue(
                                file=filepath,
                                line_num=link.line_num,
                                link_text=link.link_text,
                                issue_type='broken',
                                description=f"Anchor '{anchor}' not found",
                            )
                        )
                elif link_class == 'relative-file':
                    target_file = link.target.split('#', 1)[0]
                    target_path = str((Path(filepath).parent / target_file).resolve())
                    if not Path(target_path).exists():
                        issues.append(
                            Issue(
                                file=filepath,
                                line_num=link.line_num,
                                link_text=link.link_text,
                                issue_type='broken',
                                description=f"Target file '{target_path}' not found",
                            )
                        )
                # A URI-scheme target is not fetched. It is reported through
                # summarise_unchecked_link_classes() rather than as broken.

    return all_links, issues


def cmd_verify_links(args) -> dict:
    """Handle verify-links subcommand."""
    if args.file and args.directory:
        return {'status': 'error', 'error': 'invalid_args', 'message': 'Cannot specify both --file and --directory'}

    target_path = args.file if args.file else (args.directory if args.directory else '.')
    recursive = args.recursive if args.directory else (not args.file)

    path = Path(target_path)
    if not path.exists():
        return {'status': 'error', 'error': 'path_not_found', 'message': f"Path '{target_path}' not found"}

    files = []
    if path.is_file():
        if path.suffix != '.adoc':
            # File mode applies the AsciiDoc grammar. A Markdown file parsed with
            # it yields no links and a clean ``total_links: 0`` — a pass over a
            # file that was never read. Refuse with the same no_files-class error
            # the directory mode returns, so a caller sees "nothing was checked"
            # rather than a verified zero.
            return {
                'status': 'error',
                'error': 'no_files',
                'message': (
                    f"No AsciiDoc files found in {target_path}: '{path.suffix or path.name}' is not an "
                    'AsciiDoc file (only .adoc files are checked)'
                ),
            }
        files = [str(path)]
    elif recursive:
        files = [str(f) for f in path.rglob('*.adoc') if 'target' not in f.parts]
    else:
        files = [str(f) for f in path.glob('*.adoc')]

    if not files:
        return {
            'status': 'error',
            'error': 'no_files',
            'message': f'No AsciiDoc files found in {target_path}',
        }

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

    result = {
        'status': 'success' if not issues else 'failure',
        'data': {
            'files_processed': len(files),
            'total_links': len(all_links),
            'broken_links': len(broken),
            'format_violations': len(violations),
            'unchecked_link_classes': summarise_unchecked_link_classes(all_links),
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

    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2))

    return result
