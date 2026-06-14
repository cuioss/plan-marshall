#!/usr/bin/env python3
"""High-precision cross-reference scanner for the
``MARKDOWN_LINK_BARE_FILENAME`` rule.

This module implements a deterministic, filesystem-verified static analyzer
that flags only two **high-precision** cross-reference defects in skill / agent
/ command markdown across **all** bundles. Both patterns are narrow by design —
an earlier blanket "any bare ``.md`` token in prose" matcher produced a flood of
false positives on legitimate descriptive mentions (e.g. naming ``SKILL.md`` in
a sentence) and has been dropped.

1. **Broken parent-relative link (filesystem-verified)** — a markdown link of
   the form ``[text](TARGET)`` where ``TARGET`` ends in ``.md`` and contains NO
   path separator (``/``). The target is resolved relative to the referencing
   file's own directory:

   - If ``{dir}/{TARGET}`` does NOT exist on disk AND ``{parentdir}/{TARGET}``
     DOES exist on disk → FLAG. The link is missing the ``../`` parent-escape
     prefix; the author meant the sibling-of-parent doc but wrote a same-dir
     target that resolves nowhere.
   - If ``{dir}/{TARGET}`` exists (a correct same-dir link) → do NOT flag.
   - If neither exists → do NOT flag. That target is some other concern
     (external, renamed, or about-to-be-created) and is outside this rule's
     scope. Verifying against the filesystem this way yields effectively zero
     false positives.

2. **Odd-one-out plain-text cross-reference in a link list** — a bare
   ``[word].md`` filename token (NOT already inside a ``[...](...)`` markdown
   link, NOT inside an inline-code span / fenced block / HTML comment) that
   appears on a markdown list-item line, WHERE at least one OTHER item in the
   SAME contiguous list block is a markdown link whose target ends in ``.md``.
   This catches the "one plain-text sibling among a list of navigable links"
   defect — a list that is clearly a cross-reference list, with a single item
   left un-linked — without flagging prose mentions anywhere else.

   A "contiguous list block" is the run of consecutive list-item lines (lines
   matching ``^\\s*([-*+]|\\d+\\.)\\s``), allowing blank lines and nested
   continuation lines between items.

The rule mirrors the sibling ``_analyze_*.py`` modules:

- pure static analysis (no subprocess execution, no imports of target scripts)
- stdlib-only dependencies
- no mutation of any file
- pattern 1 reads sibling-directory listings from disk (read-only ``Path``
  existence checks) to verify a link is genuinely broken

Context exemptions
------------------
Three contexts are exempt from BOTH patterns — a ``.md`` token inside any of
them is never flagged:

1. Fenced code blocks of any info-string (```` ```python ````, ```` ```toon ````,
   bare ```` ``` ````, etc.).
2. Markdown inline-code spans (backtick-delimited, e.g. `` `foo.md` ``).
3. HTML comments (``<!-- ... -->``), which may span multiple lines.

Findings have the shape::

    {
        'rule_id': 'MARKDOWN_LINK_BARE_FILENAME',
        'type': 'MARKDOWN_LINK_BARE_FILENAME',
        'rule': 'analyze_markdown_link_bare_filename',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_markdown_link_bare_filename(marketplace_root)``: entry point — scans
  every ``*.md`` under ``marketplace_root/*/{skills,agents,commands}/`` for ALL
  bundles.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'MARKDOWN_LINK_BARE_FILENAME'
RULE_NAME = 'analyze_markdown_link_bare_filename'
FINDING_TYPE = 'MARKDOWN_LINK_BARE_FILENAME'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r'^\s*```')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Inline-code span: a backtick-delimited run. Masked out of a line before the
# patterns run so a ``.md`` token inside an inline-code span is never flagged.
_INLINE_CODE_RE = re.compile(r'`[^`]*`')

# A markdown link: ``[text](target)``. Both the text and the target are
# captured. Used to find link targets (pattern 1 / list-item link detection)
# and to mask out whole links so a bare ``name.md`` inside ``[text](name.md)``
# is never treated as a plain-text token by pattern 2.
_MD_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]*)\)')

# A bare ``.md`` filename token: word-boundary-delimited ``name.md`` where
# ``name`` is a filename-safe run (letters, digits, ``_``, ``-``, ``.``). The
# leading ``(?<![\w/.-])`` negative lookbehind ensures the match starts at a
# token boundary; the trailing ``(?![\w-])`` stops ``.md`` from matching inside
# ``.mdx`` / ``.md5`` etc.
_BARE_MD_TOKEN_RE = re.compile(r'(?<![\w/.-])([\w.-]+\.md)(?![\w-])')

# A markdown list-item line: ``- ``, ``* ``, ``+ `` or ``1. `` after optional
# leading whitespace.
_LIST_ITEM_RE = re.compile(r'^\s*([-*+]|\d+\.)\s')

# A ``.md`` link target (target ends in ``.md``).
_MD_TARGET_RE = re.compile(r'\.md$')


# ---------------------------------------------------------------------------
# Context map
# ---------------------------------------------------------------------------


def _build_fence_lines(lines: list[str]) -> set[int]:
    """Return the set of 0-based line indices that fall inside a fenced block.

    Both the fence delimiter lines and the lines between them are included, so
    the caller can skip every line that is part of any fenced code block
    regardless of info-string.
    """
    fenced: set[int] = set()
    in_fence = False
    for idx, line in enumerate(lines):
        if not in_fence:
            if _FENCE_OPEN_RE.match(line):
                in_fence = True
                fenced.add(idx)
        else:
            fenced.add(idx)
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
    return fenced


def _strip_html_comments(text: str) -> str:
    """Replace every ``<!-- ... -->`` span with same-shape whitespace.

    Newlines inside a comment are preserved so 1-based line numbers stay
    correct; every other character becomes a space. This neutralises any ``.md``
    token inside an HTML comment (which may span multiple lines) without
    shifting line boundaries.
    """

    def _blank(match: re.Match[str]) -> str:
        return ''.join('\n' if ch == '\n' else ' ' for ch in match.group(0))

    return re.sub(r'<!--.*?-->', _blank, text, flags=re.DOTALL)


def _mask_inline_code(line: str) -> str:
    """Replace inline-code spans with same-length whitespace.

    Preserves column positions while removing any ``.md`` token that lives
    inside backticks from the patterns' view.
    """
    return _INLINE_CODE_RE.sub(lambda m: ' ' * len(m.group(0)), line)


def _mask_links(line: str) -> str:
    """Replace whole ``[text](target)`` markdown links with same-length space.

    Masking the entire link (text + target) prevents pattern 2 from treating a
    ``.md`` token inside a well-formed ``[text](name.md)`` link as a plain-text
    cross-reference.
    """
    return _MD_LINK_RE.sub(lambda m: ' ' * len(m.group(0)), line)


# ---------------------------------------------------------------------------
# Finding construction
# ---------------------------------------------------------------------------


def _make_finding(path: Path, line_no: int, snippet: str, description: str) -> dict:
    return {
        'rule_id': RULE_ID,
        'type': FINDING_TYPE,
        'rule': RULE_NAME,
        'file': str(path),
        'line': line_no,
        'severity': 'error',
        'fixable': False,
        'snippet': snippet.strip()[:80],
        'description': description,
    }


_BROKEN_PARENT_DESC = (
    'Broken parent-relative markdown link. The link target ends in ``.md`` and '
    'has no path separator; it does not resolve in the referencing file\'s own '
    'directory, but the same-named doc exists one directory up. The ``../`` '
    'parent-escape prefix is missing — use ``[text](../sibling.md)`` so the link '
    'navigates to the sibling-of-parent document.'
)

_ODD_ONE_OUT_DESC = (
    'Odd-one-out plain-text cross-reference in a link list. This list item names '
    'a bare ``name.md`` document as plain text while at least one other item in '
    'the same list block is a navigable ``[text](...md)`` markdown link. Make the '
    'cross-reference list uniform — wrap this filename in a navigable markdown '
    'link too.'
)


# ---------------------------------------------------------------------------
# List-block detection
# ---------------------------------------------------------------------------


def _list_blocks(lines: list[str], fenced: set[int]) -> list[list[int]]:
    """Return contiguous list blocks as lists of 0-based line indices.

    A list block is a run of consecutive list-item lines, allowing blank lines
    and nested continuation lines (indented, non-list) between items. A block
    ends at the first non-blank, non-continuation, non-list line. Fenced lines
    are treated as block terminators and never belong to a block.
    """
    blocks: list[list[int]] = []
    current: list[int] = []
    pending_gap: list[int] = []  # blank / continuation lines held since last item

    def _flush() -> None:
        if current:
            blocks.append(list(current))
        current.clear()
        pending_gap.clear()

    for idx, line in enumerate(lines):
        if idx in fenced:
            _flush()
            continue
        if _LIST_ITEM_RE.match(line):
            # A list item continues (or starts) a block; absorb any held gap.
            pending_gap.clear()
            current.append(idx)
            continue
        if not current:
            # No open block — non-list lines are irrelevant.
            continue
        if line.strip() == '':
            # Blank line: tentatively part of the gap; one blank still allows
            # the list to continue (loose lists), but two consecutive blanks
            # terminate it.
            if pending_gap and lines[pending_gap[-1]].strip() == '':
                _flush()
            else:
                pending_gap.append(idx)
            continue
        if line.startswith((' ', '\t')):
            # Indented continuation line of the current item.
            pending_gap.append(idx)
            continue
        # A flush-worthy non-list, non-indented line terminates the block.
        _flush()
    _flush()
    return blocks


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_broken_parent_links(path: Path, lines: list[str], fenced: set[int]) -> list[dict]:
    """Pattern 1: filesystem-verified broken parent-relative links."""
    findings: list[dict] = []
    dir_path = path.parent
    parent_path = dir_path.parent
    for idx, line in enumerate(lines):
        if idx in fenced:
            continue
        prose = _mask_inline_code(line)
        for match in _MD_LINK_RE.finditer(prose):
            target = match.group(1).strip()
            if not _MD_TARGET_RE.search(target):
                continue
            if '/' in target:
                continue
            if target.startswith('#'):
                continue
            same_dir = dir_path / target
            parent_dir = parent_path / target
            if (not same_dir.exists()) and parent_dir.exists():
                findings.append(
                    _make_finding(path, idx + 1, line, _BROKEN_PARENT_DESC)
                )
    return findings


def _scan_odd_one_out_lists(path: Path, lines: list[str], fenced: set[int]) -> list[dict]:
    """Pattern 2: odd-one-out plain-text cross-reference in a link list."""
    findings: list[dict] = []
    for block in _list_blocks(lines, fenced):
        # Does this block contain at least one navigable ``.md`` link?
        has_md_link = False
        for idx in block:
            for match in _MD_LINK_RE.finditer(_mask_inline_code(lines[idx])):
                if _MD_TARGET_RE.search(match.group(1).strip()):
                    has_md_link = True
                    break
            if has_md_link:
                break
        if not has_md_link:
            continue
        # Flag each list-item line that carries a bare ``.md`` plain-text token
        # outside any markdown link / inline-code span.
        for idx in block:
            if not _LIST_ITEM_RE.match(lines[idx]):
                continue
            plain = _mask_links(_mask_inline_code(lines[idx]))
            if _BARE_MD_TOKEN_RE.search(plain):
                findings.append(
                    _make_finding(path, idx + 1, lines[idx], _ODD_ONE_OUT_DESC)
                )
    return findings


def _scan_file(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            {
                'rule_id': RULE_ID,
                'type': 'file_read_error',
                'rule': RULE_NAME,
                'file': str(path),
                'line': 0,
                'severity': 'error',
                'fixable': False,
                'snippet': '',
                'description': f'Could not read file: {exc}',
            }
        ]

    # HTML comments are neutralised before line splitting so multi-line comments
    # are handled in one pass; newlines are preserved to keep line numbers exact.
    text = _strip_html_comments(text)
    lines = text.splitlines()
    fenced = _build_fence_lines(lines)

    findings: list[dict] = []
    findings.extend(_scan_broken_parent_links(path, lines, fenced))
    findings.extend(_scan_odd_one_out_lists(path, lines, fenced))
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _markdown_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``*.md`` under ``{skills,agents,commands}`` of ALL bundles."""
    targets: list[Path] = []
    if not marketplace_root.is_dir():
        return targets
    for bundle in sorted(p for p in marketplace_root.iterdir() if p.is_dir()):
        for subdir in ('skills', 'agents', 'commands'):
            root = bundle / subdir
            if root.is_dir():
                targets.extend(
                    sorted(p for p in root.rglob('*.md') if p.is_file())
                )
    return targets


def analyze_markdown_link_bare_filename(marketplace_root: Path) -> list[dict]:
    """Scan all-bundle skill/agent/command markdown for cross-reference defects.

    Walks ``marketplace_root/*/{skills,agents,commands}/**/*.md`` for every
    bundle and reports two high-precision defects: (1) a filesystem-verified
    broken parent-relative link (a no-separator ``.md`` target that resolves in
    the parent directory but not the file's own directory — the ``../`` prefix
    is missing); and (2) an odd-one-out plain-text ``name.md`` cross-reference
    in a list block that otherwise contains navigable ``.md`` links. Fenced
    code, inline-code, and HTML-comment contexts are exempt.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace root (the directory that contains the
        ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for md_path in _markdown_targets(marketplace_root):
        findings.extend(_scan_file(md_path))
    return findings
