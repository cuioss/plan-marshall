#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Verify-links subcommand for checking AsciiDoc links."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from plan_logging import log_entry

#: The AsciiDoc ``link:target[label]`` macro. ``\b`` keeps ``backlink:...`` from
#: matching, and the target may carry no whitespace, so prose such as
#: "see link: <<anchor>>" is not read as a macro at all.
_LINK_MACRO_RE = re.compile(r'(?<!\\)\blink:([^\s\[]+?)\[([^\]]*)\]')

#: A target the checker does not open: a URI scheme (``https:``, ``mailto:``,
#: ``file:``) or a protocol-relative target (``//host/path``). No network access is
#: performed, so every one of these is an unchecked class rather than a broken or
#: a verified link.
_URI_SCHEME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*:')

#: The class name reported under ``unchecked_link_classes`` for an unopened target.
_EXTERNAL_URL_CLASS = 'external-url'

#: The class name for a fragment on a non-AsciiDoc target, which this checker
#: cannot read for anchors.
_FRAGMENT_UNCHECKED_CLASS = 'fragment'

#: The class name for a target carrying an AsciiDoc attribute reference
#: (``{docs-base}/guide.adoc``). The checker does not substitute attributes, so
#: the literal target cannot be resolved to a path.
_ATTRIBUTE_REFERENCE_CLASS = 'attribute-reference'

#: AsciiDoc delimited blocks whose contents are literal (a listing or literal
#: block), a passthrough block, or a comment. Links and anchors inside them are
#: never rendered, so they are not checked.
_BLOCK_DELIMITER_RE = re.compile(r'-{4,}|\.{4,}|/{4,}|\+{4,}')

#: An inline passthrough (``+link:target[label]+``). Its content is emitted
#: verbatim, so it is an example, not a live macro.
_INLINE_PASSTHROUGH_RE = re.compile(r'(?<![\w+])\+[^+\s][^+\n]*?\+(?![\w+])')


def _block_delimiter(line: str) -> str | None:
    """The delimited-block delimiter a line carries, when it opens or closes one.

    Only a line that is nothing but four-or-more of one delimiter character
    qualifies; ``----`` followed by prose is content, not a delimiter. The run is
    reduced to its first four characters so a longer closing run still closes the
    block it matches.
    """
    stripped = line.strip()
    if _BLOCK_DELIMITER_RE.fullmatch(stripped):
        return stripped[:4]
    return None


def _advance_block_state(delimiter: str | None, open_delimiter: str | None) -> str | None:
    """Track which delimiter opened a delimited block; a block closes only on its own."""
    if delimiter is None:
        return open_delimiter
    if open_delimiter is None:
        return delimiter
    return None if delimiter == open_delimiter else open_delimiter


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
    """Extract all valid anchors from an AsciiDoc file.

    Anchors inside a delimited literal or comment block are never rendered, so
    they are not collected. A section title contributes both the hyphenated slug
    this checker has always derived and Asciidoctor's default auto-generated ID
    (``_`` prefix, ``_`` separator), so a link to either form resolves.
    """
    anchors = set()
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    open_delimiter = None
    for line in lines:
        delimiter = _block_delimiter(line)
        if delimiter is not None:
            open_delimiter = _advance_block_state(delimiter, open_delimiter)
            continue
        if open_delimiter is not None:
            continue
        if line.strip().startswith('//'):
            continue

        # Anchor markers inside a monospace/passthrough example are not rendered;
        # the section title keeps its own text for the slug.
        marker_line = re.sub(r'`[^`]*`', lambda match: ' ' * len(match.group(0)), line)
        marker_line = _INLINE_PASSTHROUGH_RE.sub(lambda match: ' ' * len(match.group(0)), marker_line)
        anchors.update(re.findall(r'\[\[([^\]]+)\]\]', marker_line))
        anchors.update(re.findall(r'\[#([^\]]+)\]', marker_line))
        section_match = re.match(r'^(={1,6})\s+(.+)$', line.strip())
        if section_match:
            title = section_match.group(2)
            title = re.sub(r'\{[^\}]+\}', '', title)
            title = re.sub(r'link:https?://[^\[]+\[[^\]]+\]', '', title)
            title = re.sub(r'link:[^\[]+\[([^\]]*)\]', r'\1', title)
            anchor = title.strip().lower()
            anchor = re.sub(r'[^\w\s-]', '', anchor)
            anchor = re.sub(r'\s+', '-', anchor)
            anchor = re.sub(r'-+', '-', anchor).strip('-')
            if anchor:
                anchors.add(anchor)
            auto_id = '_' + re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
            if auto_id != '_':
                anchors.add(auto_id)
    return anchors


def extract_links_from_file(filepath: str) -> list[Link]:
    """Extract all links from an AsciiDoc file."""
    links = []
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    open_delimiter = None
    for line_num, line in enumerate(lines, 1):
        delimiter = _block_delimiter(line)
        if delimiter is not None:
            open_delimiter = _advance_block_state(delimiter, open_delimiter)
            continue
        if open_delimiter is not None:
            continue
        if line.strip().startswith('//'):
            continue

        # An inline monospace/passthrough example is not a live link. Match on a
        # masked copy (same length, so offsets still address the original line) and
        # slice the ORIGINAL line for the recorded text, so a report never shows a
        # mangled link.
        original_line = line
        masked = re.sub(r'`[^`]*`', lambda match: ' ' * len(match.group(0)), line)
        masked = _INLINE_PASSTHROUGH_RE.sub(lambda match: ' ' * len(match.group(0)), masked)

        for match in re.finditer(r'<<([^,>]+)(?:,([^>]+))?>>', masked):
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=original_line[match.start() : match.end()],
                    link_type='cross-ref',
                    anchor=match.group(1).strip(),
                    label=match.group(2).strip() if match.group(2) else '',
                )
            )

        for match in re.finditer(r'xref:([^\[]+)\[([^\]]*)\]', masked):
            target_full = match.group(1).strip()
            target, anchor = (target_full.split('#', 1) + [''])[:2] if '#' in target_full else (target_full, '')
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=original_line[match.start() : match.end()],
                    link_type='xref',
                    target=target,
                    anchor=anchor,
                    label=match.group(2).strip(),
                )
            )

        for match in re.finditer(r'<<([^>]*\.adoc[^>]*)>>', masked):
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=original_line[match.start() : match.end()],
                    link_type='deprecated',
                    target=match.group(1),
                )
            )

        for match in re.finditer(_LINK_MACRO_RE, masked):
            links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=original_line[match.start() : match.end()],
                    link_type='link',
                    target=match.group(1).strip(),
                    label=match.group(2).strip(),
                )
            )

    return links


def _link_macro_class(target: str) -> str:
    """The class a ``link:`` target belongs to.

    ``internal-anchor`` for a ``#anchor`` target; ``external-url`` for a target a
    URI scheme or a ``//`` prefix puts out of reach (``file:`` and a drive letter
    included, since neither is opened); ``relative-file`` for everything else.
    """
    if target.startswith('#'):
        return 'internal-anchor'
    if target.startswith('//') or _URI_SCHEME_RE.match(target):
        return _EXTERNAL_URL_CLASS
    if '{' in target:
        return _ATTRIBUTE_REFERENCE_CLASS
    return 'relative-file'


def _split_relative_target(target: str) -> tuple[str, str]:
    """Split a relative ``link:`` target into (filesystem path, fragment).

    The query component is dropped and percent-encoding decoded, so both the
    verifier and the unchecked-class summary read the same path.
    """
    target_file, _, fragment = target.partition('#')
    return unquote(target_file.split('?', 1)[0]), fragment


def _unchecked_class(link: Link) -> str | None:
    """The unchecked class a ``link:`` macro belongs to, or ``None`` when verified."""
    if link.link_type != 'link':
        return None
    link_class = _link_macro_class(link.target)
    if link_class in {_EXTERNAL_URL_CLASS, _ATTRIBUTE_REFERENCE_CLASS}:
        return link_class
    if link_class == 'relative-file':
        target_file, fragment = _split_relative_target(link.target)
        if fragment and not target_file.lower().endswith('.adoc'):
            if (Path(link.file).parent / target_file).exists():
                return _FRAGMENT_UNCHECKED_CLASS
    return None


def summarise_unchecked_link_classes(links: list[Link]) -> list[dict]:
    """One row per class the checker deliberately does not verify.

    A ``link:`` target carrying a URI scheme is never fetched, and a fragment on a
    non-AsciiDoc target is never read for anchors, so both are counted here
    instead of being reported as verified. A file with no such link yields an
    empty list — a measured zero, not a missing field.
    """
    rows: dict[str, dict] = {}
    for link in links:
        link_class = _unchecked_class(link)
        if link_class is None:
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
                    target_file, fragment = _split_relative_target(link.target)
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
                    elif fragment and target_file.lower().endswith('.adoc'):
                        if target_path not in anchor_cache:
                            anchor_cache[target_path] = extract_anchors_from_file(target_path)
                        if fragment not in anchor_cache[target_path]:
                            issues.append(
                                Issue(
                                    file=filepath,
                                    line_num=link.line_num,
                                    link_text=link.link_text,
                                    issue_type='broken',
                                    description=f"Anchor '{fragment}' not found in '{target_path}'",
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
    unchecked = summarise_unchecked_link_classes(all_links)

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
            'unchecked_link_classes': unchecked,
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
        'metrics': {'valid_links': len(all_links) - len(issues) - sum(row['count'] for row in unchecked)},
    }

    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2))

    return result
