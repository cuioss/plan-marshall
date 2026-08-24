#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parse an epic's staged plan specs and classify each ``## Expected Surface``.

Stage 1 of the epic-surface derivation: turn prose specs into a typed claim
model the partition stage joins against the real ``test/`` tree.

The corpus is enumerated by GLOB (:data:`SPEC_GLOB`) and never by a hard-coded
plan list — a hard-coded list here would be the same defect the derivation
exists to close, one level down. A spec added to the corpus is picked up with no
edit to this module.

Each spec lands in exactly one of three classes, with the evidence for the
verdict recorded beside it:

- ``declarative`` — the Expected Surface resolves to at least one path entry.
- ``derived`` — the section declares its surface a function of other plans'.
- ``prose`` — a section is present but resolves to no path entry.

A spec whose class cannot be determined raises :class:`UnclassifiableSpecError`
naming the spec, rather than defaulting to a class.

This is NOT a second implementation of the pairwise collision matrix, which
``orchestrator corpus cross-check`` owns. That verb reuses
``manage-status:_cmd_sibling_collision._extract_paths``, whose regex requires a
``/`` and a trailing ``.ext`` — so it resolves named files only and can see
neither a directory, a recursive glob, an exclusion, nor an entry written
relative to a path named earlier in the same bullet. Those four shapes, and the
three-class verdict, are what this module adds.
"""

import re
from dataclasses import dataclass
from pathlib import Path

#: Filename glob the spec corpus is enumerated by.
SPEC_GLOB = 'PLAN-*.md'

#: The three classes a spec's Expected Surface lands in.
CLASS_DECLARATIVE = 'declarative'
CLASS_DERIVED = 'derived'
CLASS_PROSE = 'prose'

#: The four shapes a resolved entry takes.
KIND_RECURSIVE_GLOB = 'recursive_glob'
KIND_DIRECTORY = 'directory'
KIND_FILENAME_GLOB = 'filename_glob'
KIND_FILE = 'file'

# --- markdown line scanners -------------------------------------------------
#
# CommonMark bounds block-level leading indentation to 0-3 SPACES; a fourth
# column starts an indented code block instead. The bound is therefore written
# over the literal space character and never over ``\s``, which would readmit
# both the fourth space and a tab.

#: The two sections this module addresses, and the generic ATX heading that
#: TERMINATES a section body. Both addressed headings are matched
#: case-insensitively: a case variant is a spelling of the same heading, and
#: treating it as absent would halt a spec that declared its surface.
EXPECTED_SURFACE_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Expected Surface(?:[ \t]+#+)?[ \t]*$', re.IGNORECASE)
OUT_OF_SCOPE_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Out of Scope(?:[ \t]+#+)?[ \t]*$', re.IGNORECASE)
_HEADING_RE = re.compile(r'^ {0,3}#{1,6}(?:[ \t]|$)')
_FENCE_RE = re.compile(r'^ {0,3}(`{3,}|~{3,})')
_BULLET_RE = re.compile(r'^\s*[-*][ \t]+')

# --- within-line scanners ----------------------------------------------------

#: ``OBSERVED:`` / ``HYPOTHESIS:`` label prefixes, including the corpus's
#: qualified forms (``OBSERVED — **re-derive; ...**:``). Everything up to the
#: first colon is the label.
_LABEL_PREFIX_RE = re.compile(r'^(?:OBSERVED|HYPOTHESIS)\b[^:]*:[ \t]*')

#: A ``` `span` ``` of backticked text — the corpus's path notation.
_BACKTICK_RE = re.compile(r'`([^`\n]+)`')

#: Decoration a bullet may open with before its real text: bold/italic markers,
#: the ⛔ and ⚠/⚠️ markers, and whitespace.
_LEADING_DECORATION = r'[\s*_⛔⚠️]*'

#: A bullet stating what the plan does NOT touch. Its paths are exclusions.
_NEGATIVE_CLAIM_RE = re.compile(rf'^{_LEADING_DECORATION}no\b', re.IGNORECASE)

#: The em-dash separator between a bullet's claim and its trailing commentary.
_TAIL_SPLIT_RE = re.compile(r'\s—\s')

#: The carve-out keyword. Spans after it in the same segment are exclusions.
_EXCLUDING_RE = re.compile(r'\bexcluding\b', re.IGNORECASE)

#: The corpus's self-declaration that a surface is a function of other plans'.
#: Matched case-SENSITIVELY on the uppercase emphasis the corpus uses, so the
#: ordinary lowercase ``re-derive`` prose several specs carry is not a match.
_DERIVED_RE = re.compile(r'\bDERIVED\b')

#: The plan identifier a spec filename opens with.
_PLAN_ID_RE = re.compile(r'^(PLAN-[0-9]+)')

#: Characters that cannot appear in a repository path. Their presence in a
#: backticked span is what separates a path from the corpus's many other
#: backticked tokens — symbol names, notations, flags, quoted output.
_NON_PATH_CHARS = frozenset(' \t()[]{}<>:;,=!?|"\'`$%&^~#@\\')


class UnclassifiableSpecError(Exception):
    """A spec whose Expected-Surface class cannot be determined.

    Raised instead of defaulting to a class, so the run halts with the spec
    named. Carries ``spec`` and ``reason`` for the caller's structured report.
    """

    def __init__(self, spec: str, reason: str) -> None:
        super().__init__(f'{spec}: {reason}')
        self.spec = spec
        self.reason = reason


@dataclass(frozen=True)
class PathEntry:
    """One path a spec names, as written and as resolved."""

    raw: str
    path: str
    kind: str
    excluded: bool


@dataclass(frozen=True)
class SpecClaim:
    """One spec's parsed surface, its class, and the evidence for that class."""

    plan_id: str
    spec: str
    spec_class: str
    evidence: str
    claimed: tuple[PathEntry, ...]
    excluded: tuple[PathEntry, ...]
    unresolved: tuple[str, ...]


def _fenced_mask(lines: list[str]) -> list[bool]:
    """Mark every line that sits inside a fenced code block (fences included)."""
    mask = [False] * len(lines)
    fence: str | None = None
    for index, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)[0]
                mask[index] = True
            continue
        mask[index] = True
        if match and match.group(1)[0] == fence:
            fence = None
    return mask


def _section_span(lines: list[str], heading_re: re.Pattern[str], fenced: list[bool]) -> tuple[int, int]:
    """Return the ``[start, end)`` body span of one section, or ``(-1, -1)``.

    The body ends at the next heading of any level, so a subsection never leaks
    into the parent. Both heading scans skip fenced lines.
    """
    start = -1
    for index, line in enumerate(lines):
        if not fenced[index] and heading_re.match(line):
            start = index + 1
            break
    if start < 0:
        return (-1, -1)
    for index in range(start, len(lines)):
        if not fenced[index] and _HEADING_RE.match(lines[index]):
            return (start, index)
    return (start, len(lines))


def _iter_bullets(lines: list[str], fenced: list[bool], start: int, end: int) -> list[str]:
    """Return each ``- `` bullet in a section span as one joined logical line.

    A bullet runs until the next bullet, a blank line, or the section end, so a
    surface entry wrapped across source lines is parsed whole. Non-bullet
    paragraph text is section preamble and contributes no entry.
    """
    bullets: list[str] = []
    current: list[str] = []
    for index in range(start, end):
        if fenced[index]:
            continue
        line = lines[index]
        if _BULLET_RE.match(line):
            if current:
                bullets.append(' '.join(current))
            current = [_BULLET_RE.sub('', line).strip()]
        elif not line.strip():
            if current:
                bullets.append(' '.join(current))
                current = []
        elif current:
            current.append(line.strip())
    if current:
        bullets.append(' '.join(current))
    return bullets


def _is_path_candidate(span: str, repo_root: Path) -> bool:
    """Whether a backticked span denotes a repository path.

    A multi-segment span is a path. A single-segment span is one only when it
    globs or actually exists at ``repo_root`` — which is what keeps
    ``monkeypatch.delitem`` and the corpus's other dotted symbol names out,
    while admitting ``pyproject.toml`` and ``test_*.py``.
    """
    if not span or span.startswith('-'):
        return False
    if any(char in _NON_PATH_CHARS for char in span):
        return False
    if '/' in span:
        return True
    return '*' in span or (repo_root / span).exists()


def _is_rooted(span: str, repo_root: Path) -> bool:
    """Whether a candidate's first segment is a real top-level entry.

    Derived from the tree rather than from a hand-listed set of roots, so a new
    top-level directory needs no edit here.
    """
    first = span.split('/', 1)[0]
    if not first or first == '...':
        return False
    return (repo_root / first).exists()


def _base_from(rooted: str) -> str:
    """The directory a bullet's relative entries resolve against.

    A recursive glob names the directory its entries live under; every other
    shape names a sibling, so the base is that entry's parent.
    """
    if rooted.endswith('**'):
        stem = rooted[:-2]
    else:
        trimmed = rooted.rstrip('/')
        stem = trimmed.rsplit('/', 1)[0] if '/' in trimmed else ''
    if stem and not stem.endswith('/'):
        stem += '/'
    return stem


def _entry_kind(path: str) -> str:
    """Classify a resolved path into one of the four entry shapes."""
    if path.endswith('**'):
        return KIND_RECURSIVE_GLOB
    if path.endswith('/'):
        return KIND_DIRECTORY
    if '*' in path:
        return KIND_FILENAME_GLOB
    return KIND_FILE


def _spans_with_exclusion(segment: str) -> list[tuple[str, bool]]:
    """Return each backticked span with whether it follows an ``excluding``."""
    match = _EXCLUDING_RE.search(segment)
    cut = match.end() if match else None
    return [
        (found.group(1), cut is not None and found.start() >= cut)
        for found in _BACKTICK_RE.finditer(segment)
    ]


def _bullet_segments(body: str) -> list[str]:
    """The parts of a bullet that carry surface entries.

    The head — everything before the first em dash — is the claim. The trailing
    commentary is dropped, because it cites paths as reasons rather than
    claiming them, EXCEPT when it carries the carve-out keyword: several specs
    write their exclusion after the dash.
    """
    parts = _TAIL_SPLIT_RE.split(body, maxsplit=1)
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ''
    if tail and _EXCLUDING_RE.search(tail):
        return [head, tail]
    return [head]


def _collect_bullet(
    bullet: str,
    repo_root: Path,
    force_excluded: bool,
    claimed: list[PathEntry],
    excluded: list[PathEntry],
    unresolved: list[str],
) -> None:
    """Resolve one bullet's entries into the caller's three accumulators."""
    body = _LABEL_PREFIX_RE.sub('', bullet, count=1)
    negative = bool(_NEGATIVE_CLAIM_RE.match(body))

    spans: list[tuple[str, bool]] = []
    for segment in _bullet_segments(body):
        spans.extend(_spans_with_exclusion(segment))

    candidates = [(span, after) for span, after in spans if _is_path_candidate(span, repo_root)]
    base = ''
    for span, _ in candidates:
        if _is_rooted(span, repo_root):
            base = _base_from(span)
            break

    for span, after_excluding in candidates:
        raw = span[2:] if span.startswith('./') else span
        if _is_rooted(raw, repo_root):
            path = raw
        else:
            relative = raw[4:] if raw.startswith('.../') else raw
            if not base:
                unresolved.append(span)
                continue
            path = base + relative
        entry = PathEntry(
            raw=span,
            path=path,
            kind=_entry_kind(path),
            excluded=force_excluded or negative or after_excluding,
        )
        (excluded if entry.excluded else claimed).append(entry)


def _evidence_line(body: str, position: int) -> str:
    """The source line containing ``position``, as the recorded evidence."""
    line_start = body.rfind('\n', 0, position) + 1
    line_end = body.find('\n', position)
    if line_end < 0:
        line_end = len(body)
    return body[line_start:line_end].strip()


def plan_id_of(spec_name: str) -> str:
    """The plan identifier a spec filename opens with, or the bare filename."""
    match = _PLAN_ID_RE.match(spec_name)
    return match.group(1) if match else spec_name


def classify_spec(spec_path: Path, repo_root: Path) -> SpecClaim:
    """Parse one spec's surface and assign it exactly one class with evidence.

    Raises:
        UnclassifiableSpecError: when the spec cannot be read, or carries no
            ``## Expected Surface`` section — the two states in which no class
            can be determined.
    """
    try:
        text = spec_path.read_text(encoding='utf-8')
    except OSError as error:
        raise UnclassifiableSpecError(spec_path.name, f'unreadable: {error}') from error

    lines = text.splitlines()
    fenced = _fenced_mask(lines)
    start, end = _section_span(lines, EXPECTED_SURFACE_HEADING_RE, fenced)
    if start < 0:
        raise UnclassifiableSpecError(spec_path.name, 'no "## Expected Surface" section')

    claimed: list[PathEntry] = []
    excluded: list[PathEntry] = []
    unresolved: list[str] = []

    for bullet in _iter_bullets(lines, fenced, start, end):
        _collect_bullet(bullet, repo_root, False, claimed, excluded, unresolved)

    scope_start, scope_end = _section_span(lines, OUT_OF_SCOPE_HEADING_RE, fenced)
    if scope_start >= 0:
        for bullet in _iter_bullets(lines, fenced, scope_start, scope_end):
            _collect_bullet(bullet, repo_root, True, claimed, excluded, unresolved)

    body = '\n'.join(lines[start:end])
    derived = _DERIVED_RE.search(body)
    if derived is not None:
        spec_class = CLASS_DERIVED
        evidence = _evidence_line(body, derived.start())
    elif claimed:
        spec_class = CLASS_DECLARATIVE
        evidence = f'{len(claimed)} resolved path entries; first: {claimed[0].path}'
    else:
        spec_class = CLASS_PROSE
        evidence = 'Expected Surface present; no entry the parser resolves to a path'

    return SpecClaim(
        plan_id=plan_id_of(spec_path.name),
        spec=spec_path.name,
        spec_class=spec_class,
        evidence=evidence,
        claimed=tuple(claimed),
        excluded=tuple(excluded),
        unresolved=tuple(unresolved),
    )


def classify_corpus(plans_dir: Path, repo_root: Path) -> list[SpecClaim]:
    """Classify every spec in an epic's ``plans/`` directory, in filename order."""
    return [classify_spec(spec, repo_root) for spec in sorted(plans_dir.glob(SPEC_GLOB))]
