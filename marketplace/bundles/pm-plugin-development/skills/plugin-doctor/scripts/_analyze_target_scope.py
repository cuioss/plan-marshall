#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Component ``targets:`` frontmatter validity analyzer.

Implements the ``targets-scope-invalid`` rule. A component — an
``agents/*.md``, a ``commands/*.md``, or a skill's ``SKILL.md`` — may declare
the build-time field ``targets:`` naming the build targets it ships to. The
field is consumed by the multi-target generator
(``marketplace/targets/component_targets.py``); a value the generator rejects
fails the build, so this rule surfaces the same defect at authoring time,
where the author is still looking at the file.

What is flagged
---------------
- **Unknown target name** — a value naming no registered build target. Almost
  always a typo, and one that would otherwise silently narrow the component's
  reach.
- **Empty declaration** — ``targets: []`` or a ``targets:`` key with no items.
  A component that ships nowhere is an authoring error; omitting the field is
  how an author says "every target".
- **A value spanning more than one line** — the build reads a value from one
  physical line, so accepting one would silently narrow the scope to whatever
  fitted on that line. This is ONE condition; it is reported under three
  reasons because three YAML constructs produce it (``targets_multiline_scalar``
  for a plain scalar, ``targets_quoted_scalar`` for a quoted one, and
  ``targets_block_scalar`` for a ``>``/``|`` block scalar), and naming the
  wrong construct sends the author looking for a defect that is not in their
  file. Which name is chosen is a diagnosis made after the decision to flag.

What is NOT flagged
-------------------
An absent field is correct and common — it means "ship to every target" and
is the state of nearly every component in the marketplace.

The generator additionally rejects a declaration naming ONLY targets that
emit no component tree. That check asks each target class for its
``emits_bundle_tree`` capability. This analyzer does not import the target
classes — pattern-matching the method body to guess the answer would be a
second, weaker restatement of a contract the build can simply ask for — so
that check stays in the build and this rule covers every defect a static scan
settles outright.

Deriving the target set
-----------------------
The valid names are derived from the targets' own registrations —
``register_target('{name}', …)`` in ``marketplace/targets/*/__init__.py`` —
never from a list transcribed here, so a target registered later is honoured
with no edit to this module.

``marketplace/targets/`` is a meta-project tree: a consumer project installs
the bundles without it. When it cannot be located, the unknown-name check is
skipped (there is nothing to check names against) while the empty-declaration
check, which needs no registry, still runs. Skipping a check whose input is
absent is reported by silence rather than by a fabricated verdict.

Pattern alignment
-----------------
Mirrors ``_analyze_frontmatter.py``: pure static analysis, line-based
frontmatter parsing, stdlib-only, no mutation, ``Finding``-shaped output.

Public API
----------
- ``analyze_target_scope(marketplace_root)``: entry point.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'targets-scope-invalid'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='corpus-relational',
)
RULE_NAME = 'analyze_target_scope'

#: The three YAML constructs that can produce a value spanning more than one
#: line. Naming them is a DIAGNOSIS, never a decision — see
#: :func:`_multiline_shape`.
_SHAPE_BLOCK_SCALAR = 'block-scalar'
_SHAPE_QUOTED_SCALAR = 'quoted-scalar'
_SHAPE_PLAIN_SCALAR = 'plain-scalar'

#: Sentinel for a block whose indentation a line scan cannot read — see
#: ``_dedent_block``. Reported so the author sees at authoring time what the
#: build will refuse, rather than only at build time.
_AMBIGUOUS_INDENT = ['\x00ambiguous-indent']

#: One sentinel token list per shape. A sentinel is compared by IDENTITY, so
#: its string content is decoration: a component that literally declares
#: ``targets: ["\x00block-scalar"]`` is an unknown target name, not a block
#: scalar. Each list is a distinct object, which is what makes that true.
_MULTILINE_SENTINELS: dict[str, list[str]] = {
    _SHAPE_BLOCK_SCALAR: ['\x00block-scalar'],
    _SHAPE_QUOTED_SCALAR: ['\x00quoted-scalar'],
    _SHAPE_PLAIN_SCALAR: ['\x00multiline-plain-scalar'],
}

#: A whole YAML block-scalar header — see ``component_targets``. The
#: fixed set of the six chomping spellings this replaced misdiagnosed 90 of
#: the 96 spellings the grammar admits — every header carrying an
#: indentation indicator (``|2``, ``>3-``) among them.
_BLOCK_SCALAR_HEADER_RE = re.compile(r'^[>|](?:[0-9][-+]?|[-+][0-9]?)?$')

#: A frontmatter fence line: three hyphens, then only spaces or tabs — see
#: ``component_targets``. ``_dep_detection.extract_frontmatter`` (owned by the
#: ``tools-marketplace-inventory`` skill, imported by this one) already accepts
#: a space-suffixed fence, so refusing it here made two parsers in one tree
#: disagree about whether a file has frontmatter at all. Parity is restored for
#: trailing whitespace only: that reader matches ``\n---`` as a PREFIX and so
#: also closes on ``----``, where this one does not; and it does not strip a
#: UTF-8 BOM, so it reports no frontmatter for a BOM'd file this one reads.
_OPEN_FENCE_RE = re.compile(r'^---[ \t]*\n')
_CLOSE_FENCE_RE = re.compile(r'\n---[ \t]*(?:\n|$)')

#: Frontmatter field under inspection.
TARGET_SCOPE_FIELD = 'targets'

#: Captures the name in a ``register_target('claude', ClaudeTarget)`` call —
#: the targets' own registration, which is the source of truth for the set.
_REGISTER_TARGET_RE = re.compile(r'register_target\(\s*[\'"]([^\'"]+)[\'"]')

#: Approximates "a new key starts here" — an unquoted, letter-or-underscore
#: initial identifier at column 0 followed by a colon. It bounds the fold of
#: an unclosed flow sequence.
#:
#: Requiring an identifier before the colon is what distinguishes this from
#: the looser ``^[^\s#][^:]*:`` it replaced, which matched any non-indented,
#: non-comment line containing a colon anywhere. That looser form broke two
#: VALID declarations: a continuation line carrying a trailing comment with a
#: URL in it, and one whose value is a quoted string containing a colon. Both
#: are ordinary YAML, and both were then rejected naming a target nobody
#: wrote — the defect the fold exists to prevent. This form is still only an
#: approximation of a YAML key; see :func:`_join_flow_sequence` for what it
#: misses and why that is safe here.
_TOP_LEVEL_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.-]*\s*:')

_DESCRIPTION_UNKNOWN = (
    'component `targets:` frontmatter names a target that is not registered — the '
    'multi-target build rejects the declaration, so until it is fixed the build fails '
    'rather than shipping the component anywhere.'
)

_DESCRIPTION_MULTILINE = (
    'component `targets:` frontmatter is a plain scalar continued across lines. That is one '
    'YAML value spanning several lines, and the build reads a value from one physical line, '
    'so the declared scope would be silently narrowed rather than read as written. '
    'Write the list explicitly — `targets: [a, b]` or a `- ` block.'
)

_DESCRIPTION_BLOCK_SCALAR = (
    'component `targets:` frontmatter uses a YAML block scalar (`>` or `|`), whose value is '
    'the indented lines beneath it. The build reads a value from one physical line, so it '
    'would narrow the declared scope to whatever fitted on the first. '
    'Write the list explicitly — `targets: [a, b]` or a `- ` block.'
)

_DESCRIPTION_QUOTED_SCALAR = (
    'component `targets:` frontmatter is a quoted scalar continued across lines. That is one '
    'YAML value spanning several lines, and the build reads a value from one physical line, '
    'so the declared scope would be silently narrowed rather than read as written. '
    'Write the list explicitly — `targets: [a, b]` or a `- ` block.'
)

_DESCRIPTION_AMBIGUOUS_INDENT = (
    'component frontmatter is indented, and a line inside it is indented less than the '
    'block\'s own keys. That is either a value continued across lines or malformed YAML, and '
    'the build cannot tell which, so it refuses the component rather than read `targets:` '
    'wrongly or miss it entirely. Unindent the frontmatter block so its keys start at column 1.'
)

_DESCRIPTION_EMPTY = (
    'component `targets:` frontmatter declares an empty list — a component that ships '
    'to no target is an authoring error. Omit the field to ship to every target.'
)

#: Description and reason code per multi-line shape. One table, so a shape
#: cannot be added to the parser without a finding to report it.
_MULTILINE_FINDING: dict[str, tuple[str, str]] = {
    _SHAPE_BLOCK_SCALAR: (_DESCRIPTION_BLOCK_SCALAR, 'targets_block_scalar'),
    _SHAPE_QUOTED_SCALAR: (_DESCRIPTION_QUOTED_SCALAR, 'targets_quoted_scalar'),
    _SHAPE_PLAIN_SCALAR: (_DESCRIPTION_MULTILINE, 'targets_multiline_scalar'),
}


def _frontmatter_block(text: str) -> str | None:
    """Return the leading ``---``-fenced block's inner text, or ``None``.

    A UTF-8 BOM is stripped first so a BOM'd file does not read as having no
    frontmatter at all. Each fence is matched as a whole LINE, so a value that
    itself contains three hyphens does not truncate the block, and trailing
    spaces or tabs on a fence are accepted \u2014 see :data:`_OPEN_FENCE_RE`.
    """
    text = text.lstrip('\ufeff')
    open_fence = _OPEN_FENCE_RE.match(text)
    if open_fence is None:
        return None
    start = open_fence.end()
    # From start - 1, so the newline ending the opening fence can also serve
    # as the newline opening the closing one. What that changes is a block
    # closed immediately (`---` / `---` / more text): the block is EMPTY, and
    # where a LATER fence closes it the body would otherwise be read as fields.
    close_fence = _CLOSE_FENCE_RE.search(text, start - 1)
    if close_fence is None:
        return None
    return text[start:close_fence.start()]


def _strip_comment(value: str) -> str:
    """Drop a trailing YAML comment from a scalar or flow-sequence value.

    Mirrors the generator's own parser (``component_targets._strip_comment``)
    so the two agree on what a declaration says: a ``#`` opens a comment only
    when it opens a token. That keeps an UNQUOTED ``#`` intact but not a
    quoted one — see ``component_targets`` for what that costs.
    """
    head, sep, _tail = value.partition('#')
    if not sep:
        return value
    if head and not head[-1].isspace():
        return value
    return head.rstrip()


def _join_flow_sequence(value: str, rest: list[str]) -> str:
    """Return ``value``, extended across the lines a flow sequence spans.

    Mirrors ``component_targets._join_flow_sequence``: a ``targets: [claude,``
    continued on the next line is one value, and reading only the first
    physical line would report ``[claude`` as an unknown target. The fold
    stops at the first non-indented line matching :data:`_TOP_LEVEL_KEY_RE`,
    so an unclosed sequence cannot absorb the fields that follow it. That
    pattern approximates "a new key starts here" and is wrong in both
    directions — see ``component_targets._join_flow_sequence`` for what it
    misses. There, every misread is REJECTED by the build. Here the outcome
    is weaker by design: a misread yields a token no registry name matches,
    and the unknown-name check needs a ``marketplace/targets/`` tree to run
    at all (see the module docstring), so where that tree is absent the
    misread is silently ignored rather than surfaced. The empty-declaration
    check is unaffected — it needs no registry and still runs.
    """
    head = _strip_comment(value)
    if not head.startswith('[') or ']' in head:
        return head
    parts = [head]
    for line in rest:
        if _TOP_LEVEL_KEY_RE.match(line):
            break
        segment = _strip_comment(line.strip())
        if segment:
            parts.append(segment)
        if ']' in segment:
            break
    return ' '.join(parts)


def _split_inline(value: str) -> list[str]:
    """Split an inline scalar or flow-sequence value into tokens."""
    inner = _strip_comment(value)
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1]
    return [token.strip().strip('"').strip("'") for token in inner.split(',') if token.strip()]


def _collect_block_items(lines: list[str]) -> list[str]:
    """Collect a YAML block sequence's items, stopping at the first non-item.

    A blank line and a whole-line ``#`` comment are skipped rather than ending
    the sequence, so a commented list is not misread as an EMPTY one and
    reported as a component that ships nowhere.
    """
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if not stripped.startswith('-'):
            break
        item = _strip_comment(stripped[1:].strip()).strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _unquote_key(key: str) -> str:
    """Return ``key`` with a MATCHED pair of surrounding quotes removed.

    ``"targets": [claude]`` is the same declaration as ``targets: [claude]``
    to any YAML reader, and not recognising it fails OPEN — the component
    ships everywhere with its declaration unread.

    The pair must MATCH. ``str.strip`` takes a character set rather than a
    prefix, so stripping quotes with it also turns ``targets"`` into
    ``targets`` — and that key is NOT ``targets`` to YAML, so a component
    that declared no scope would be silently narrowed to someone else's
    list. That is the same defect in the opposite direction, and the one the
    module docstring calls prohibited, so the quotes are removed only when
    they genuinely surround the key.
    """
    key = key.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        return key[1:-1]
    return key


class _AmbiguousIndent(Exception):
    """Internal marker: the block's indentation cannot be read by a line scan.

    Mirrors ``component_targets._AmbiguousIndent``. Turned into the
    ``_AMBIGUOUS_INDENT`` sentinel by :func:`declared_targets`.
    """


def _first_meaningful(lines: list[str]) -> tuple[int, str]:
    """Return ``(index, line)`` of the first line that carries structure.

    Blank lines and whole-line ``#`` comments carry none. ``(-1, '')`` when
    there is no such line.
    """
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            return index, line
    return -1, ''


def _dedent_block(block: str) -> list[str]:
    """Split ``block`` into lines, dedented by the indent its keys sit at.

    Mirrors ``component_targets._dedent_block``, including its refusal to
    guess at an ambiguous indent.

    Top-level is relative to the BLOCK, not to column zero: a frontmatter
    block whose every key is indented by the same amount has all of them at
    top level, and YAML reads it that way. Scanning for column-zero keys
    instead reported "no declaration" — the component then shipped to every
    target with its declaration unread, and an INVALID declaration passed the
    build unreported.

    The base indent is the FIRST structural line's, because that is what sets
    a YAML block mapping's indentation. Two earlier rules were wrong here and
    each re-opened the same hole one shape over: ``textwrap.dedent`` counts
    comment lines, so one ``# note`` at column zero pinned the prefix at zero;
    and a ``min()`` over structural lines counts the CONTINUATION of a
    multi-line value, so ``description: "one`` / ``two"`` did the same.

    Ambiguity is refused rather than guessed. Below an indented base, a
    shallower structural line is either a continuation of a multi-line value
    or malformed YAML, and a line scanner cannot tell which — so it raises
    :class:`_AmbiguousIndent` instead of silently picking one. That is a
    deliberate move from failing OPEN to failing CLOSED: the previous three
    rules all answered this shape by shipping the component everywhere with
    its declaration unread. A block whose base indent is zero — every
    component in this marketplace — cannot reach the guard at all.
    """
    lines = block.split('\n')
    structural = [
        line for line in lines if line.strip() and not line.strip().startswith('#')
    ]
    if not structural:
        return lines
    base = len(structural[0]) - len(structural[0].lstrip())
    if not base:
        return lines
    if any(len(line) - len(line.lstrip()) < base for line in structural):
        raise _AmbiguousIndent
    return [line[base:] if line[:base].isspace() else line.lstrip() for line in lines]


def _has_continuation(rest: list[str]) -> bool:
    """Whether the next meaningful line continues the value rather than ending it.

    Mirrors ``component_targets._has_continuation``. An indented line after a
    plain-scalar value is YAML's multi-line plain scalar; reading only the
    first physical line would silently narrow the declared scope, which the
    build rejects outright.
    """
    return _first_meaningful(rest)[1][:1].isspace()


def _multiline_shape(value: str) -> str:
    """Name the YAML construct a flagged multi-line value is written in.

    Mirrors ``component_targets._multiline_shape``. Diagnosis only: the caller
    has already decided to flag, so a misclassification changes the reason
    code and the sentence, never whether the component is reported. A value
    carrying an escaped quote reads as terminated and is named a plain scalar
    — valid YAML with the wrong noun on it, flagged either way.
    """
    if _BLOCK_SCALAR_HEADER_RE.match(_strip_comment(value)):
        return _SHAPE_BLOCK_SCALAR
    if value[:1] in {'"', "'"} and value.count(value[0]) < 2:
        return _SHAPE_QUOTED_SCALAR
    return _SHAPE_PLAIN_SCALAR


def declared_targets(text: str) -> tuple[list[str], int] | None:
    """Return ``(tokens, line_number)`` for a top-level ``targets:`` declaration.

    ``None`` means the field is absent, which is the correct default. An empty
    token list means the field is present but names nothing. The line number is
    1-based within the whole file.

    Only a TOP-LEVEL key counts, where top-level is relative to the BLOCK
    rather than to column zero: a frontmatter block whose every line is
    indented by the same amount has all its keys at top level, and YAML reads
    it that way. The block is dedented by its common prefix first — scanning
    for column-zero keys instead reported "no declaration" for such a file,
    which is how the build ships a component everywhere with its declaration
    unread. A ``targets:`` indented BEYOND its siblings still belongs to a
    nested mapping and is still a different field.
    """
    block = _frontmatter_block(text)
    if block is None:
        return None
    try:
        lines = _dedent_block(block)
    except _AmbiguousIndent:
        # Line 2 is the block's first line; the whole block is the problem,
        # so the finding anchors there rather than on a key it cannot find.
        return _AMBIGUOUS_INDENT, 2
    for index, line in enumerate(lines):
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(':')
        if not separator or _unquote_key(key) != TARGET_SCOPE_FIELD:
            continue
        # +2: the opening fence occupies line 1, so block line 0 is file line 2.
        line_number = index + 2
        head = _strip_comment(value.strip())
        rest = lines[index + 1:]
        if head:
            # ONE condition, three diagnoses — see the module docstring.
            if not head.startswith('[') and _has_continuation(rest):
                return _MULTILINE_SENTINELS[_multiline_shape(value.strip())], line_number
            return _split_inline(_join_flow_sequence(head, rest)), line_number
        return _continued_value(rest), line_number
    return None


def _continued_value(rest: list[str]) -> list[str]:
    """Read the value of a ``targets:`` key that carries none on its own line.

    Mirrors ``component_targets._continued_value``: a ``- `` block, a flow
    sequence opening on the next line, an empty declaration, or an indented
    line that is none of those — a plain scalar whose content begins on the
    next line, which "declares an empty list" would misname.
    """
    items = _collect_block_items(rest)
    if items:
        return items
    index, line = _first_meaningful(rest)
    if not line[:1].isspace():
        return items
    head = _strip_comment(line.strip())
    if head.startswith('['):
        return _split_inline(_join_flow_sequence(head, rest[index + 1:]))
    # Diagnosed from the line, never assumed - see ``component_targets``.
    return _MULTILINE_SENTINELS[_multiline_shape(line.strip())]


def registered_target_names(marketplace_root: Path) -> frozenset[str] | None:
    """Derive the registered build-target names, or ``None`` when unavailable.

    ``marketplace_root`` is the bundles root, so the targets tree is its
    sibling. ``None`` means the tree is absent (a consumer project installed
    the bundles without it) and names cannot be validated.
    """
    targets_root = marketplace_root.parent / 'targets'
    if not targets_root.is_dir():
        return None
    names: set[str] = set()
    try:
        packages = sorted(targets_root.iterdir())
    except OSError:
        return None
    for package in packages:
        init_py = package / '__init__.py'
        if not (package.is_dir() and init_py.is_file()):
            continue
        try:
            text = init_py.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        names.update(match.group(1) for match in _REGISTER_TARGET_RE.finditer(text))
    return frozenset(names) if names else None


def component_files(marketplace_root: Path) -> list[Path]:
    """Enumerate every component file that may carry a ``targets:`` declaration."""
    files: list[Path] = []
    try:
        bundle_dirs = sorted(marketplace_root.iterdir())
    except OSError:
        return files
    for bundle_dir in bundle_dirs:
        if not bundle_dir.is_dir():
            continue
        for subdir_name in ('agents', 'commands'):
            subdir = bundle_dir / subdir_name
            if not subdir.is_dir():
                continue
            files.extend(
                path
                for path in sorted(subdir.glob('*.md'))
                if path.is_file() and not path.name.startswith('.')
            )
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_md = skill_dir / 'SKILL.md'
            if skill_dir.is_dir() and skill_md.is_file():
                files.append(skill_md)
    return files


def _scan_component(path: Path, registered: frozenset[str] | None) -> list[dict]:
    """Return findings for one component's ``targets:`` declaration."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    declaration = declared_targets(text)
    if declaration is None:
        return []
    tokens, line_number = declaration

    if tokens is _AMBIGUOUS_INDENT:
        return [
            Finding(
                type=RULE_ID,
                file=str(path),
                line=line_number,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=_DESCRIPTION_AMBIGUOUS_INDENT,
                details={'reason': 'targets_ambiguous_indent'},
                extra={'rule': RULE_NAME},
            ).to_dict()
        ]

    for shape, sentinel in _MULTILINE_SENTINELS.items():
        # IDENTITY, not equality: a component whose declaration literally
        # spells a sentinel's content is an unknown target name, not a
        # multi-line value.
        if tokens is sentinel:
            description, reason = _MULTILINE_FINDING[shape]
            return [
                Finding(
                    type=RULE_ID,
                    file=str(path),
                    line=line_number,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=description,
                    details={'reason': reason},
                    extra={'rule': RULE_NAME},
                ).to_dict()
            ]

    if not tokens:
        return [
            Finding(
                type=RULE_ID,
                file=str(path),
                line=line_number,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=_DESCRIPTION_EMPTY,
                details={'reason': 'targets_empty'},
                extra={'rule': RULE_NAME},
            ).to_dict()
        ]

    if registered is None:
        return []

    unknown = sorted(token for token in tokens if token not in registered)
    if not unknown:
        return []
    return [
        Finding(
            type=RULE_ID,
            file=str(path),
            line=line_number,
            severity='error',
            fixable=False,
            rule_id=RULE_ID,
            description=(
                f'{_DESCRIPTION_UNKNOWN} Unknown: {", ".join(unknown)}. '
                f'Registered targets are: {", ".join(sorted(registered))}.'
            ),
            details={
                'reason': 'targets_unknown',
                'declared_targets': tokens,
                'unknown_targets': unknown,
                'registered_targets': sorted(registered),
            },
            extra={'rule': RULE_NAME},
        ).to_dict()
    ]


def analyze_target_scope(marketplace_root: Path) -> list[dict]:
    """Scan every component for an invalid ``targets:`` declaration.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).

    Returns
    -------
    list[dict]
        A list of finding dicts (see the module docstring for the shape).
    """
    registered = registered_target_names(marketplace_root)
    findings: list[dict] = []
    for path in component_files(marketplace_root):
        findings.extend(_scan_component(path, registered))
    return findings
