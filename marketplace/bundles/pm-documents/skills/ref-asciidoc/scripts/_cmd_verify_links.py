#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Verify-links subcommand for checking AsciiDoc links."""

import json
import re
from collections.abc import Callable
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

#: The class name for a target that is not relative to the containing file
#: (``/etc/hosts``, ``\\server\share.adoc``). The checker does not open it:
#: joining it onto the file's directory discards that directory and addresses
#: the host root, so it is neither verified nor broken.
_ABSOLUTE_PATH_CLASS = 'absolute-path'

#: One class name per inline mask that hides a ``link:`` macro from the checker.
#: A masked example is still counted, so the report says what the checker did
#: not examine instead of implying it verified a zero.
_CODE_SPAN_CLASS = 'code-span'
_INLINE_PASSTHROUGH_CLASS = 'inline-passthrough'
_PASSTHROUGH_CLASS = 'passthrough'
_PASS_MACRO_CLASS = 'pass-macro'

#: The issue type for a target the checker could not read (a directory named
#: like an ``.adoc`` file, a permission error, a non-UTF-8 file) or could not
#: resolve (a NUL byte in the target). It is not ``broken``: the link was never
#: examined.
_UNREADABLE_ISSUE = 'unreadable'

#: AsciiDoc delimited blocks whose contents are literal (a listing or literal
#: block), a passthrough block, or a comment. Links and anchors inside them are
#: never rendered, so they are not checked.
_BLOCK_DELIMITER_RE = re.compile(r'-{4,}|\.{4,}|/{4,}|\+{4,}')

#: An inline monospace code span (`` `link:target[label]` ``).
_CODE_SPAN_RE = re.compile(r'`[^`\n]*`')

#: A macro passthrough (``pass:[link:target[label]]``). Its content is emitted
#: verbatim, so it is an example, not a live macro. One nesting level of square
#: brackets is matched, because the content of a pass macro commonly carries a
#: link macro's own ``[…]`` label.
_PASS_MACRO_RE = re.compile(r'pass:\[(?:[^\[\]\n]|\[[^\]\n]*\])*\]')

#: An unconstrained passthrough (``++link:target[label]++``). Its content is
#: emitted verbatim, so it is an example, not a live macro. The boundary guards
#: keep a ``C++`` in prose from consuming the closer of a later construct.
_PASSTHROUGH_RE = re.compile(r'(?<![\w+])\+\+[^+\n]*?\+\+(?![\w+])')

#: An inline passthrough (``+link:target[label]+``). Its content is emitted
#: verbatim, so it is an example, not a live macro.
_INLINE_PASSTHROUGH_RE = re.compile(r'(?<![\w+])\+[^+\s][^+\n]*?\+(?![\w+])')

#: The inline masks, outermost first. A link inside a code span is counted under
#: ``code-span`` even when the span also matches a later pattern, because the
#: first mask that covers it blanks the text the later ones would scan.
_MASKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (_CODE_SPAN_CLASS, _CODE_SPAN_RE),
    (_PASS_MACRO_CLASS, _PASS_MACRO_RE),
    (_PASSTHROUGH_CLASS, _PASSTHROUGH_RE),
    (_INLINE_PASSTHROUGH_CLASS, _INLINE_PASSTHROUGH_RE),
)


def _mask_inline_constructs(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Blank the inline example constructs on a line, naming each masked link.

    Returns the masked line — same length, so offsets still address the original
    — and every ``link:`` macro the masking hid, as ``(class, source text)``
    pairs. Masking is what keeps a documented syntax example from being reported
    as a live, broken link; counting the hidden macros is what keeps the
    unchecked-class report honest about what was skipped.
    """
    masked = line
    hidden: list[tuple[str, str]] = []

    def _masker(link_class: str) -> Callable[[re.Match[str]], str]:
        def _blank(match: re.Match[str]) -> str:
            hidden.extend((link_class, found.group(0)) for found in _LINK_MACRO_RE.finditer(match.group(0)))
            return ' ' * len(match.group(0))

        return _blank

    for link_class, pattern in _MASKS:
        masked = pattern.sub(_masker(link_class), masked)
    return masked, hidden


def _block_delimiter(line: str) -> str | None:
    """The delimited-block delimiter a line carries, when it opens or closes one.

    Only a line that is nothing but four-or-more of one delimiter character
    qualifies; ``----`` followed by prose is content, not a delimiter. The whole
    run is returned, because a block closes only on a delimiter of the same
    length that opened it: a nested ``----`` inside a ``-----`` listing is
    content, not a close.
    """
    stripped = line.strip()
    if _BLOCK_DELIMITER_RE.fullmatch(stripped):
        return stripped
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
    #: Set only for a ``link_type == 'masked'`` row: the inline construct that
    #: hid the macro, which is also the unchecked class it is reported under.
    unchecked_class: str = ''


@dataclass
class Issue:
    file: str
    line_num: int
    link_text: str
    issue_type: str
    description: str
    context: str = ''
    suggested_fix: str = ''
    #: False for a file-level issue that has no link behind it, so a metric that
    #: counts verified links does not subtract it.
    link_backed: bool = True


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

        # Anchor markers inside an example are not rendered; the same masks the
        # link extractor applies are applied here, so a ``pass:[[[ghost]]]``
        # example does not register ``ghost`` as a real anchor. The section title
        # keeps its own text for the slug.
        marker_line, _hidden = _mask_inline_constructs(line)
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


def _extract_from_file(filepath: str) -> tuple[list[Link], list[Link]]:
    """Extract the live links and the masked examples from an AsciiDoc file.

    Masked examples are returned separately, so a caller that counts links does
    not count them as live while the unchecked-class summary still sees them.
    """
    links = []
    masked_links = []
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
        # mangled link. The masked macros are named by their own class, so the
        # report says what the checker did not examine.
        original_line = line
        masked, hidden = _mask_inline_constructs(line)
        for link_class, hidden_text in hidden:
            masked_links.append(
                Link(
                    file=filepath,
                    line_num=line_num,
                    link_text=hidden_text,
                    link_type='masked',
                    unchecked_class=link_class,
                )
            )

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

    return links, masked_links


def extract_links_from_file(filepath: str) -> list[Link]:
    """Extract all live links from an AsciiDoc file."""
    return _extract_from_file(filepath)[0]


def _link_macro_class(target: str) -> str:
    """The class a ``link:`` target belongs to.

    ``attribute-reference`` for a target carrying an unresolved ``{attribute}``
    — tested before the ``#`` test, so ``link:#{section-id}[x]`` is not looked up
    as the literal anchor ``{section-id}``. ``internal-anchor`` for a ``#anchor``
    target; ``external-url`` for a target a URI scheme or a ``//`` prefix puts
    out of reach (``file:`` and a drive letter included, since neither is
    opened); ``absolute-path`` for a target a leading ``/`` or ``\\`` anchors
    outside the file's directory; ``relative-file`` for everything else.
    """
    if '{' in target:
        return _ATTRIBUTE_REFERENCE_CLASS
    if target.startswith('#'):
        return 'internal-anchor'
    if target.startswith('//') or _URI_SCHEME_RE.match(target):
        return _EXTERNAL_URL_CLASS
    if target.startswith('/') or target.startswith('\\'):
        return _ABSOLUTE_PATH_CLASS
    return 'relative-file'


def _split_relative_target(target: str) -> tuple[str, str]:
    """Split a relative ``link:`` target into (filesystem path, fragment).

    The query component is dropped and percent-encoding decoded — the fragment
    included — so both the verifier and the unchecked-class summary read the
    same path and the same anchor.
    """
    target_file, _, fragment = target.partition('#')
    return unquote(target_file.split('?', 1)[0]), unquote(fragment)


def _unchecked_class(link: Link) -> str | None:
    """The unchecked class a ``link:`` macro belongs to, or ``None`` when verified."""
    if link.link_type == 'masked':
        return link.unchecked_class
    if link.link_type != 'link':
        return None
    link_class = _link_macro_class(link.target)
    if link_class in {_EXTERNAL_URL_CLASS, _ATTRIBUTE_REFERENCE_CLASS, _ABSOLUTE_PATH_CLASS}:
        return link_class
    if link_class == 'relative-file':
        target_file, fragment = _split_relative_target(link.target)
        if fragment and not target_file.lower().endswith('.adoc'):
            try:
                exists = (Path(link.file).parent / target_file).exists()
            except (OSError, ValueError):
                exists = False
            if exists:
                return _FRAGMENT_UNCHECKED_CLASS
    return None


def summarise_unchecked_link_classes(links: list[Link]) -> list[dict]:
    """One row per class the checker deliberately does not verify.

    An external or absolute ``link:`` target is never opened, an attribute-bearing
    one is never substituted, a fragment on a non-AsciiDoc target is never read for
    anchors, and a macro inside an inline example mask is never examined — so each
    is counted here instead of being reported as verified. A file with no such link
    yields an empty list — a measured zero, not a missing field.
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


def _safe_anchors(filepath: str) -> tuple[set[str] | None, str | None]:
    """The anchors of one file, or ``None`` and the reason it could not be read."""
    try:
        return extract_anchors_from_file(filepath), None
    except (OSError, UnicodeError) as exc:
        return None, f'{type(exc).__name__}: {exc}'


def _resolve_target(filepath: str, target_file: str) -> tuple[str | None, str | None]:
    """The resolved target path, or ``None`` and the reason it could not be resolved."""
    try:
        return str((Path(filepath).parent / target_file).resolve()), None
    except (OSError, ValueError) as exc:
        return None, f'{type(exc).__name__}: {exc}'


def verify_links(files: list[str]) -> tuple[list[Link], list[Issue]]:
    """Verify all links in all files.

    A file or target the checker cannot read is reported as an issue on that
    link and the run continues, so one bad target never aborts a multi-file
    verification and leaves the other files' results unread. The returned link
    list carries the masked examples too, each with its own unchecked class, so
    the caller can say what was skipped; ``link_type == 'masked'`` marks them.
    """
    all_links: list[Link] = []
    issues: list[Issue] = []
    anchor_cache: dict[str, tuple[set[str] | None, str | None]] = {}

    for filepath in files:
        anchors, reason = _safe_anchors(filepath)
        anchor_cache[filepath] = (anchors, reason)
        if anchors is None:
            issues.append(
                Issue(
                    file=filepath,
                    line_num=0,
                    link_text='',
                    issue_type=_UNREADABLE_ISSUE,
                    description=f"File '{filepath}' could not be read: {reason}",
                    link_backed=False,
                )
            )

    for filepath in files:
        anchors, _reason = anchor_cache[filepath]
        if anchors is None:
            continue
        links, masked_links = _extract_from_file(filepath)
        all_links.extend(links)
        all_links.extend(masked_links)

        for link in links:
            if link.link_type == 'cross-ref' and link.anchor not in anchors:
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
                target_path, reason = _resolve_target(filepath, link.target) if link.target else (filepath, None)
                if target_path is None:
                    issues.append(_unresolvable_issue(filepath, link, reason))
                elif not Path(target_path).exists():
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
                    target_anchors, reason = _anchors_at(target_path, anchor_cache)
                    if target_anchors is None:
                        issues.append(_unreadable_issue(filepath, link, target_path, reason))
                    elif unquote(link.anchor) not in target_anchors:
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
                    anchor = unquote(link.target[1:])
                    if anchor not in anchors:
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
                    target_path, reason = _resolve_target(filepath, target_file)
                    if target_path is None:
                        issues.append(_unresolvable_issue(filepath, link, reason))
                    elif not Path(target_path).exists():
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
                        target_anchors, reason = _anchors_at(target_path, anchor_cache)
                        if target_anchors is None:
                            issues.append(_unreadable_issue(filepath, link, target_path, reason))
                        elif fragment not in target_anchors:
                            issues.append(
                                Issue(
                                    file=filepath,
                                    line_num=link.line_num,
                                    link_text=link.link_text,
                                    issue_type='broken',
                                    description=f"Anchor '{fragment}' not found in '{target_path}'",
                                )
                            )
                # An external, absolute or attribute-bearing target is not
                # opened. It is reported through
                # summarise_unchecked_link_classes() rather than as broken.

    return all_links, issues


def _anchors_at(
    target_path: str, cache: dict[str, tuple[set[str] | None, str | None]]
) -> tuple[set[str] | None, str | None]:
    """The anchors of a target file, read once and cached, with its failure reason."""
    if target_path not in cache:
        cache[target_path] = _safe_anchors(target_path)
    return cache[target_path]


def _unreadable_issue(filepath: str, link: Link, target_path: str, reason: str | None) -> Issue:
    """The issue for a link whose `.adoc` target could not be read for anchors."""
    return Issue(
        file=filepath,
        line_num=link.line_num,
        link_text=link.link_text,
        issue_type=_UNREADABLE_ISSUE,
        description=f"Target '{target_path}' could not be read: {reason}",
    )


def _unresolvable_issue(filepath: str, link: Link, reason: str | None) -> Issue:
    """The issue for a link whose target cannot be turned into a path."""
    return Issue(
        file=filepath,
        line_num=link.line_num,
        link_text=link.link_text,
        issue_type=_UNREADABLE_ISSUE,
        description=f"Target '{link.target}' could not be resolved: {reason}",
    )


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

    live_links = [link for link in all_links if link.link_type != 'masked']
    unchecked_live = sum(1 for link in live_links if _unchecked_class(link) is not None)
    total_links = len(live_links)
    # A file-level `unreadable` issue has no link behind it, so it is not
    # subtracted from a link population it is absent from.
    link_issues = sum(1 for issue in issues if issue.link_backed)

    result = {
        'status': 'success' if not issues else 'failure',
        'data': {
            'files_processed': len(files),
            'total_links': total_links,
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
        # A masked example is not a live link and an unchecked target is not a
        # verified one, so neither is subtracted from a population it is absent
        # from.
        'metrics': {'valid_links': total_links - link_issues - unchecked_live},
    }

    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2))

    return result
