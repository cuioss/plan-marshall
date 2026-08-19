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

An approximation, and deliberately so
-------------------------------------
The generator reads frontmatter with ``yaml.safe_load``. This analyzer cannot:
a plugin-doctor script is stdlib-only, because a consumer project installs the
bundles without ``marketplace/`` and without this repository's dependencies.
The two are therefore NOT mirrors, and this one does not pretend to be. It
line-scans for the shapes it can read with certainty and **stays silent on
everything else**, leaving those to the build.

That asymmetry is the design rather than a gap in it. A net that guessed would
report defects on files the build accepts, and a false positive in a lint rule
costs more than a missed one: it spends an author's time on a correct file and
teaches them to distrust the rule. What this rule promises is that anything it
DOES report is a real build failure — never that it reports every one.

What is flagged
---------------
- **Unknown target name** — a value naming no registered build target. Almost
  always a typo, and one that would otherwise silently narrow the component's
  reach.
- **Empty declaration** — ``targets: []``, or a ``targets:`` key with nothing
  after it. A component that ships nowhere is an authoring error; omitting the
  field is how an author says "every target".

What is NOT flagged
-------------------
An absent field is correct and common — it means "ship to every target" and is
the state of nearly every component in the marketplace.

Nor is any declaration this scanner cannot read with certainty: a flow
sequence spanning lines, a block scalar, a quoted value continued across
lines, an indented frontmatter block, a value carrying a nested structure.
Every one of those is legal YAML that the build reads correctly, so silence is
the accurate answer rather than a gap to be closed by guessing.

The generator additionally rejects a declaration naming ONLY targets that emit
no component tree, and one whose value is not a list of names at all. The
first asks each target class for its ``emits_bundle_tree`` capability; this
analyzer does not import the target classes — pattern-matching the method body
to guess the answer would be a second, weaker restatement of a contract the
build can simply ask for — so that check stays in the build.

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

#: Frontmatter field under inspection.
TARGET_SCOPE_FIELD = 'targets'

#: A frontmatter fence line: three hyphens, then only spaces or tabs. The
#: generator accepts the same, since trailing whitespace on a fence is
#: invisible in an editor.
_OPEN_FENCE_RE = re.compile(r'^---[ \t]*\n')
_CLOSE_FENCE_RE = re.compile(r'\n---[ \t]*(?:\n|$)')

#: Value openers this scanner will not read: block-scalar headers, quotes,
#: and YAML's structural sigils. Each is legal and the build reads it; what
#: this scanner cannot do is read it CORRECTLY, which is a different thing
#: from it being wrong.
_UNREADABLE_OPENERS = frozenset({'>', '|', '"', "'", '{', '&', '*', '!'})

#: How YAML spells null. A key holding one is present and declares nothing.
_NULL_SPELLINGS = frozenset({'~', 'null', 'Null', 'NULL'})

#: Captures the name in a ``register_target('claude', ClaudeTarget)`` call —
#: the targets' own registration, which is the source of truth for the set.
_REGISTER_TARGET_RE = re.compile(r'register_target\(\s*[\'"]([^\'"]+)[\'"]')

_DESCRIPTION_UNKNOWN = (
    'component `targets:` frontmatter names a target that is not registered — the '
    'multi-target build rejects the declaration, so until it is fixed the build fails '
    'rather than shipping the component anywhere.'
)

_DESCRIPTION_EMPTY = (
    'component `targets:` frontmatter declares an empty list — a component that ships '
    'to no target is an authoring error. Omit the field to ship to every target.'
)


def _frontmatter_block(text: str) -> str | None:
    """Return the leading ``---``-fenced block's inner text, or ``None``.

    A UTF-8 BOM is stripped first so a BOM'd file does not read as having no
    frontmatter at all. Each fence is matched as a whole LINE, so a value that
    itself contains three hyphens does not truncate the block.
    """
    text = text.lstrip('﻿')
    open_fence = _OPEN_FENCE_RE.match(text)
    if open_fence is None:
        return None
    start = open_fence.end()
    # From start - 1, so the newline ending the opening fence can also serve
    # as the newline opening the closing one: a block closed immediately.
    close_fence = _CLOSE_FENCE_RE.search(text, start - 1)
    if close_fence is None:
        return None
    return text[start:close_fence.start()]


def _strip_comment(value: str) -> str:
    """Drop a trailing YAML comment from a scalar or flow-sequence value.

    A ``#`` opens a comment only when it opens a token, which is what YAML
    requires. That keeps an UNQUOTED ``#`` intact (``[cla#ude]``). It does not
    track quote state — but a quoted value is one this scanner declines to
    read at all, so it never reaches a case where that would matter.
    """
    head, sep, _tail = value.partition('#')
    if not sep:
        return value
    if head and not head[-1].isspace():
        return value
    return head.rstrip()


def _unquote_key(key: str) -> str:
    """Return ``key`` with a MATCHED pair of surrounding quotes removed.

    ``"targets": [claude]`` is the same declaration as ``targets: [claude]``
    to any YAML reader. The pair must MATCH: ``str.strip`` takes a character
    set rather than a prefix, so stripping quotes with it also turns
    ``targets"`` into ``targets`` — a different key to YAML, and reading it as
    this one would report a defect against a component that declared nothing.
    """
    key = key.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        return key[1:-1]
    return key


def _is_readable(value: str) -> bool:
    """Whether ``value`` is a shape this scanner can read with certainty.

    Readable: a flow sequence that opens and closes on the one line with no
    nesting, and a plain unquoted scalar carrying no structural character.
    Everything else is left to the build — see the module docstring.
    """
    if not value:
        return False
    if value[0] in _UNREADABLE_OPENERS:
        return False
    if value.startswith('['):
        return value.endswith(']') and '[' not in value[1:] and '{' not in value
    return not any(character in value for character in '[]{}:')


def _split_names(value: str) -> list[str]:
    """Split a readable value into target names.

    Accepts the closed flow form (``[a, b]``) and the bare form (``a, b``).
    The generator splits a bare string on commas too — that convenience is the
    build's own rule rather than YAML's, and this follows it.
    """
    inner = value
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1]
    return [token.strip() for token in inner.split(',') if token.strip()]


def _is_continued(rest: list[str]) -> bool:
    """Whether the next line carrying structure continues the value above it.

    An indented line after an inline value is part of that value in YAML —
    ``targets: claude,`` / ``  opencode`` is the one string ``claude,
    opencode``. This scanner cannot join them, so it declines: reading only
    the first line would report on a fragment of the real value.
    """
    for line in rest:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        return line[:1].isspace()
    return False


def declared_targets(text: str) -> tuple[list[str], int] | None:
    """Return ``(names, line_number)`` for a declaration this scanner can read.

    ``None`` covers three cases that are the same to the caller: there is no
    frontmatter, there is no ``targets:`` key, or there is one whose value this
    scanner will not read. Only a shape it is certain of yields a tuple, and an
    empty ``names`` list there is a genuine empty declaration.

    EVERY column-zero ``targets:`` key is examined, not the first. YAML resolves
    a duplicate key to the LAST one, so reading the first meant reporting on a
    declaration the build does not use — a finding against a component that is
    correct. If any occurrence is unreadable the whole file is, because the
    scanner then cannot know which declaration wins.

    A key needs whitespace (or nothing) after its colon, which is YAML's own
    rule: ``targets:#c`` and ``targets:[claude]`` are plain scalars, not
    mappings, and the build sees no key in either.

    Only a column-zero key counts. The build resolves an indented frontmatter
    block correctly and this does not, so such a block yields ``None`` —
    silence, not a wrong answer.

    The line number is 1-based within the whole file.
    """
    block = _frontmatter_block(text)
    if block is None:
        return None
    lines = block.split('\n')
    found: tuple[list[str], int] | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or line[:1].isspace() or stripped.startswith('#'):
            continue
        key, separator, value = line.partition(':')
        if not separator or _unquote_key(key) != TARGET_SCOPE_FIELD:
            continue
        if value and not value[:1].isspace():
            # `targets:#c` / `targets:[a]` - no space after the colon, so YAML
            # reads the whole line as a plain scalar and there is no key here.
            continue
        # +2: the opening fence occupies line 1, so block line 0 is file line 2.
        line_number = index + 2
        head = _strip_comment(value.strip()).strip()
        rest = lines[index + 1:]
        if head:
            if _is_continued(rest):
                # An indented line after an inline value continues it, so the
                # value is not the text on this line. Reading that text would
                # be reading a fragment of the real value.
                return None
            if head in _NULL_SPELLINGS:
                # YAML's null. The key is PRESENT and declares nothing, which
                # is the empty declaration the build rejects - not a target
                # named "null".
                found = ([], line_number)
                continue
            if not _is_readable(head):
                return None
            found = (_split_names(head), line_number)
            continue
        below = _readable_block_items(rest, line_number)
        if below is None:
            return None
        found = below
    return found


def _readable_block_items(
    rest: list[str], line_number: int
) -> tuple[list[str], int] | None:
    """Read a ``- `` block sequence beneath a valueless key, or give up.

    An empty result means the key genuinely declares nothing — YAML's null, or
    a key followed straight by the next field — which the build rejects. Any
    other continuation (a scalar, a flow sequence opening below the key, an
    item this scanner will not read) yields ``None``.

    A sequence item may sit at COLUMN ZERO. ``targets:`` / ``- claude`` is
    idiomatic YAML and is what an author writes first; treating a column-zero
    line as the next field regardless made this rule fail the quality gate on a
    valid component, which is the one thing it exists not to do.
    """
    items: list[str] = []
    for line in rest:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if not stripped.startswith('-'):
            # A non-item at column zero is the next field; an indented one is
            # a shape this scanner cannot read.
            return (items, line_number) if not line[:1].isspace() else None
        item = _strip_comment(stripped[1:].strip()).strip()
        if not _is_readable(item):
            return None
        items.append(item)
    return items, line_number


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
    names, line_number = declaration

    if not names:
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

    unknown = sorted(name for name in names if name not in registered)
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
                'declared_targets': names,
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
