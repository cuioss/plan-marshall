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

What is NOT flagged
-------------------
An absent field is correct and common — it means "ship to every target" and
is the state of nearly every component in the marketplace.

The generator additionally rejects a declaration naming ONLY targets that
emit no component tree. That check asks each target class for its
``emits_bundle_tree`` capability. This analyzer does not import the target
classes — pattern-matching the method body to guess the answer would be a
second, weaker restatement of a contract the build can simply ask for — so
that check stays in the build and this rule covers the two defects a static
scan settles outright.

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

_DESCRIPTION_EMPTY = (
    'component `targets:` frontmatter declares an empty list — a component that ships '
    'to no target is an authoring error. Omit the field to ship to every target.'
)


def _frontmatter_block(text: str) -> str | None:
    """Return the leading ``---``-fenced block's inner text, or ``None``.

    A UTF-8 BOM is stripped first so a BOM'd file does not read as having no
    frontmatter at all. The closing fence is matched as a whole ``---`` line,
    so a value that itself contains three hyphens does not truncate the block.
    """
    text = text.lstrip('\ufeff')
    if not text.startswith('---\n'):
        return None
    end = text.find('\n---\n', 4)
    if end != -1:
        return text[4:end]
    if text.endswith('\n---'):
        return text[4: len(text) - len('\n---')]
    return None


def _strip_comment(value: str) -> str:
    """Drop a trailing YAML comment from a scalar or flow-sequence value.

    Mirrors the generator's own parser (``component_targets._strip_comment``)
    so the two agree on what a declaration says: a ``#`` opens a comment only
    when it opens a token.
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
    misses and why every misread is rejected rather than mis-accepted.
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


def declared_targets(text: str) -> tuple[list[str], int] | None:
    """Return ``(tokens, line_number)`` for a top-level ``targets:`` declaration.

    ``None`` means the field is absent, which is the correct default. An empty
    token list means the field is present but names nothing. Only a TOP-LEVEL
    key counts — an indented ``targets:`` belongs to a nested mapping and is a
    different field. The line number is 1-based within the whole file.
    """
    block = _frontmatter_block(text)
    if block is None:
        return None
    lines = block.split('\n')
    for index, line in enumerate(lines):
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(':')
        if not separator or key.strip() != TARGET_SCOPE_FIELD:
            continue
        # +2: the opening fence occupies line 1, so block line 0 is file line 2.
        line_number = index + 2
        value = value.strip()
        rest = lines[index + 1:]
        if value:
            return _split_inline(_join_flow_sequence(value, rest)), line_number
        return _collect_block_items(rest), line_number
    return None


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
