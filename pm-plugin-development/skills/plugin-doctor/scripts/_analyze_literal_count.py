#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Literal-count-drift analyzer for the ``literal-count-drift`` rule.

This module detects drift between a manually-maintained numeric-literal count
token in plugin-doctor-governed skill text and the machine-derivable count of
the items that token describes. Two surfaces are governed:

1. The ``extension-api`` ``SKILL.md`` "Extension Points" table, whose
   "Implementations" column states, per extension point, how many concrete
   implementations exist. That count is a hand-maintained mirror of the on-disk
   implementer set: when a bundle adds or drops an extension-point
   implementation without editing the table, the count silently rots.
2. The ``persona-security-expert`` ``SKILL.md`` standards index, which restates
   the same set THREE times — a prose count in the REFERENCE MODE paragraph,
   the "Available Standards" table, and the "Standards Reference" table — while
   the set itself lives on disk under that skill's ``standards/`` directory.
   Adding or removing a standards document requires three hand edits and
   nothing fails when one is missed. See "Persona-security-expert standards
   index" below.

Source of truth
---------------
Each row of the "Extension Points" table is keyed by its "Hook Method" column,
which names the machine-derivable implementer set the "Implementations" count
mirrors:

- ``discover_modules()`` — Build System: the count of bundles whose
  ``plan-marshall-plugin`` ``extension.py`` carries a *real override* of
  ``discover_modules`` (a body that returns something other than the
  ``ExtensionBase`` default ``[]``).
- ``provides_triage()`` — Triage: the count of bundles whose ``extension.py``
  really overrides ``provides_triage`` (non-``None`` return).
- ``provides_outline_skill()`` — Outline: the count of bundles really
  overriding ``provides_outline_skill`` (non-``None`` return).
- ``provides_recipes()`` — Recipe: the count of bundles really overriding
  ``provides_recipes`` (non-empty-list return).
- ``*_provider.py`` — Provider: the count of ``*_provider.py`` files under any
  bundle's ``skills/*/scripts/`` tree.

The real-override classification mirrors ``_analyze_provides_method_table.py``
exactly (same ``_is_default_return`` semantics) so the two manually-maintained
mirrors of the same ``extension.py`` overrides agree on what an override is.

Structural discriminator (no false positives)
---------------------------------------------
A count token is checkable ONLY when it is the "Implementations" cell of a
markdown TABLE row whose "Hook Method" cell carries a *recognised* hook token
(one of the five above). A row whose hook token is unrecognised — or any prose
or bullet-list count elsewhere in the file — is out of scope and never flagged.
Restricting to recognised hook tokens in the structured table is what separates
a real machine-checkable mirror from incidental numbers in prose, so the rule
fires only where a stale count genuinely exists.

Detection
---------
For ``marketplace_root/plan-marshall/skills/extension-api/SKILL.md``:

1. Locate the "Extension Points" section table (bounded by the next heading).
2. For each data row, read the "Hook Method" cell and the "Implementations"
   cell. Skip rows whose hook token is unrecognised or whose implementations
   cell is not a bare integer.
3. Compute the actual implementer count for the recognised hook from the bundle
   tree and emit a warning-severity, non-fixable finding when the stated count
   differs from the actual count.

Findings have the shape::

    {
        'rule_id': 'literal-count-drift',
        'type': 'literal-count-drift',
        'rule': 'analyze_literal_count',
        'file': '<absolute SKILL.md path>',
        'line': <int, 1-based row line>,
        'severity': 'warning',
        'fixable': False,
        'description': '<human-readable drift description>',
        'details': {
            'hook': '<hook token>',
            'stated': <int>,
            'actual': <int>,
        },
    }

Persona-security-expert standards index
---------------------------------------
The population is DERIVED, never restated: it is the ``*.md`` listing of
``plan-marshall/skills/persona-security-expert/standards/``. Every finding this
surface emits publishes that derived population size in its ``details``, so a
clean result can never be read as a pass over an unread population. Three
claims are checked against it:

- the anchored prose counts in the skill body (``N `standards/` sub-documents``
  and ``load all N at once``), compared against the population size rendered as
  both a digit and an English number word;
- the "Available Standards" table's ``standards/<name>.md`` link set;
- the "Standards Reference" table's ``<name>.md`` first-column set.

The surface fails CLOSED on every way the check could go vacuous: an empty or
unreadable ``standards/`` directory, a missing index section, and a body that
carries no anchored prose count at all each emit a finding rather than passing
silently. Only the governed ``SKILL.md`` being absent short-circuits to "out of
scope", exactly as the Extension Points surface does.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_provides_method_table.py``:

- pure static analysis (AST + regex + pathlib; no subprocess, no import of the
  target ``extension.py``);
- stdlib-only dependencies;
- no mutation of any file.

Public API
----------
- ``analyze_literal_count(marketplace_root)``: entry point — scans the
  ``extension-api`` ``SKILL.md`` "Extension Points" table and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from _dep_index import AstCache
from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'literal-count-drift'
RULE_NAME = 'analyze_literal_count'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='content',
    scope='corpus-relational',
)

# The ``provides_*`` / ``discover_modules`` hooks declared on ExtensionBase,
# mapped to the base default each returns. A subclass override is a "real
# override" only when its body returns a value distinguishable from this
# default. Kept in sync with ``_analyze_provides_method_table.py`` so the two
# mirrors of the same overrides agree on what an override is.
_AST_HOOK_DEFAULTS: dict[str, object] = {
    'discover_modules': [],
    'provides_triage': None,
    'provides_outline_skill': None,
    'provides_recipes': [],
}

# The "Extension Points" section heading (any heading level).
_EXTENSION_POINTS_HEADING_RE = re.compile(r'^\s*#{1,6}\s+Extension Points\s*$', re.IGNORECASE)

# Any markdown heading line (used to bound the Extension Points section).
_HEADING_RE = re.compile(r'^\s*#{1,6}\s+\S')

# A recognised AST-hook token in a Hook Method cell, e.g. ``provides_triage()``.
_AST_HOOK_TOKEN_RE = re.compile(r'(discover_modules|provides_\w+)\(\)')

# The provider hook token in a Hook Method cell: ``*_provider.py``.
_PROVIDER_TOKEN_RE = re.compile(r'\*_provider\.py')

# A bare integer (the only form the Implementations cell may carry to be
# checkable). Surrounding whitespace / backticks / emphasis are stripped first.
_BARE_INT_RE = re.compile(r'^\d+$')

# --- Second governed surface: the persona-security-expert standards index. ---

# The governed skill, relative to the marketplace bundles root. Its
# ``standards/`` directory listing IS the population every claim is checked
# against; nothing about the set is restated here.
_PSE_SKILL_PARTS = ('plan-marshall', 'skills', 'persona-security-expert')

# English number words, so a prose count spelled as a word ("the ten
# `standards/` sub-documents") is comparable against the derived population
# size. Covers 0-20; a larger population compares against the digit form only.
_NUMBER_WORDS: dict[int, str] = {
    0: 'zero',
    1: 'one',
    2: 'two',
    3: 'three',
    4: 'four',
    5: 'five',
    6: 'six',
    7: 'seven',
    8: 'eight',
    9: 'nine',
    10: 'ten',
    11: 'eleven',
    12: 'twelve',
    13: 'thirteen',
    14: 'fourteen',
    15: 'fifteen',
    16: 'sixteen',
    17: 'seventeen',
    18: 'eighteen',
    19: 'nineteen',
    20: 'twenty',
}

# The count token a prose claim may carry: a digit run, or one of the number
# words above. Longest-first so ``sixteen`` cannot be consumed as ``six``. A
# token that is neither — an ordinary word such as "The" or "centralized" that
# happens to precede the anchor phrase — is NOT a count claim, so the anchor
# does not match it at all.
_PSE_COUNT_TOKEN = '|'.join(
    [r'\d+', *sorted(_NUMBER_WORDS.values(), key=len, reverse=True)],
)

# The anchored prose claims about the standards population. Anchoring on BOTH
# the surrounding phrase and the count-token shape is the same structural
# discriminator the Extension Points surface applies: an incidental number
# elsewhere in the file, and ordinary prose that merely mentions the
# ``standards/`` directory, are never checked.
_PSE_PROSE_ANCHOR_RES = (
    re.compile(rf'\b(?P<count>{_PSE_COUNT_TOKEN})\s+`standards/`\s+sub-documents'),
    re.compile(rf'\bload all\s+(?P<count>{_PSE_COUNT_TOKEN})\s+at once'),
)

# The two index tables, keyed by the heading text that opens their section.
_PSE_LOAD_TABLE_HEADING = 'Available Standards'
_PSE_REFERENCE_TABLE_HEADING = 'Standards Reference'

# A ``standards/<name>.md`` link inside an "Available Standards" row.
_PSE_TABLE_LINK_RE = re.compile(r'standards/([\w.-]+\.md)')

# A bare ``<name>.md`` first-column cell in a "Standards Reference" row.
_PSE_TABLE_NAME_RE = re.compile(r'^[\w.-]+\.md$')


def _is_default_return(node: ast.FunctionDef, default: object) -> bool:
    """Return True when ``node``'s body returns only the base-class default.

    Mirrors ``_analyze_provides_method_table.py::_is_default_return`` exactly: a
    method whose entire body is ``return None`` (or a bare ``return`` / ``pass``)
    matches a ``None`` default; a method whose entire body is ``return []``
    matches a ``[]`` default. Any other single return — or branching logic —
    is a real override.
    """
    returns = []
    stack: list[ast.AST] = list(node.body)
    while stack:
        curr = stack.pop()
        if isinstance(curr, ast.Return):
            returns.append(curr)
        elif isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        else:
            stack.extend(ast.iter_child_nodes(curr))
    if not returns:
        return default is None
    if len(returns) != 1:
        return False
    value = returns[0].value
    if value is None:
        return default is None
    if isinstance(value, ast.Constant) and value.value is None:
        return default is None
    if isinstance(value, ast.List) and not value.elts:
        return isinstance(default, list)
    return False


def _subclasses_extension_base(class_node: ast.ClassDef) -> bool:
    """Return True when ``class_node`` lists an ``*ExtensionBase`` base class."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id.endswith('ExtensionBase'):
            return True
        if isinstance(base, ast.Attribute) and base.attr.endswith('ExtensionBase'):
            return True
    return False


def _extension_overrides(extension_path: Path, cache: AstCache | None = None) -> dict[str, bool]:
    """Map each AST hook method to whether ``extension_path`` really overrides it.

    Returns a dict keyed by the four AST hook names; the value is True when the
    concrete ``*ExtensionBase`` subclass overrides the hook with a non-default
    return, False when the method is absent OR returns only the base default.
    Returns all-False when the file cannot be read or parsed (the structural /
    syntax rules cover that failure mode separately).
    """
    overrides: dict[str, bool] = dict.fromkeys(_AST_HOOK_DEFAULTS, False)
    if cache is not None:
        tree = cache.get_tree(extension_path)
        if tree is None:
            return overrides
    else:
        try:
            source = extension_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            return overrides
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return overrides
    for class_node in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        if not _subclasses_extension_base(class_node):
            continue
        for method in (m for m in class_node.body if isinstance(m, ast.FunctionDef)):
            if method.name not in _AST_HOOK_DEFAULTS:
                continue
            default = _AST_HOOK_DEFAULTS[method.name]
            overrides[method.name] = not _is_default_return(method, default)
    return overrides


def _ast_hook_counts(marketplace_root: Path, cache: AstCache | None = None) -> dict[str, int]:
    """Count bundles whose ``extension.py`` really overrides each AST hook.

    Walks every ``*/skills/plan-marshall-plugin/extension.py`` under
    ``marketplace_root`` and tallies, per AST hook, the number of bundles whose
    extension carries a real override.
    """
    counts: dict[str, int] = dict.fromkeys(_AST_HOOK_DEFAULTS, 0)
    try:
        extensions = sorted(marketplace_root.glob('*/skills/plan-marshall-plugin/extension.py'))
    except OSError:
        return counts
    for ext in extensions:
        if not ext.is_file():
            continue
        for hook, is_override in _extension_overrides(ext, cache).items():
            if is_override:
                counts[hook] += 1
    return counts


def _provider_count(marketplace_root: Path) -> int:
    """Count ``*_provider.py`` files under any bundle's ``skills/*/scripts/`` tree."""
    try:
        return sum(1 for p in marketplace_root.glob('*/skills/*/scripts/*_provider.py') if p.is_file())
    except OSError:
        return 0


def _cells(line: str) -> list[str]:
    """Split a markdown table row into trimmed cell strings.

    Drops the leading / trailing empty cells produced by the bounding pipes.
    """
    parts = line.split('|')
    return [p.strip() for p in parts[1:-1]] if len(parts) >= 3 else []


def _strip_cell(value: str) -> str:
    """Strip markdown emphasis / inline-code wrappers from a cell value."""
    return value.strip().strip('`').strip('*').strip()


def _scan_extension_points_table(
    skill_md: Path, ast_counts: dict[str, int], provider_count: int
) -> list[dict]:
    """Scan the Extension Points table in ``skill_md`` for stale Implementations counts."""
    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()

    findings: list[Finding] = []
    in_section = False
    for idx, line in enumerate(lines):
        if not in_section:
            if _EXTENSION_POINTS_HEADING_RE.match(line):
                in_section = True
            continue
        if _HEADING_RE.match(line):
            break
        if not line.lstrip().startswith('|'):
            continue
        cells = _cells(line)
        if not cells:
            continue
        # Identify the hook cell and the implementations cell. The hook token is
        # the structural discriminator; the implementations cell is the bare
        # integer count token to verify.
        hook_token = None
        for cell in cells:
            ast_match = _AST_HOOK_TOKEN_RE.search(cell)
            if ast_match and ast_match.group(1) in _AST_HOOK_DEFAULTS:
                hook_token = ast_match.group(1)
                break
            if _PROVIDER_TOKEN_RE.search(cell):
                hook_token = '*_provider.py'
                break
        if hook_token is None:
            continue
        # The implementations cell is the 4th column (index 3).
        if len(cells) < 4:
            continue
        impl_cell = cells[3]
        if not _BARE_INT_RE.match(_strip_cell(impl_cell)):
            continue
        stated = int(_strip_cell(impl_cell))
        actual = provider_count if hook_token == '*_provider.py' else ast_counts.get(hook_token, 0)
        if stated == actual:
            continue
        findings.append(
            Finding(
                type=RULE_ID,
                file=str(skill_md),
                line=idx + 1,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'the "Extension Points" table states {stated} implementation(s) '
                    f'for hook `{hook_token}` but the bundle tree enumerates {actual} — '
                    f'the count is a stale mirror of the implementer set (literal-count-drift)'
                ),
                details={
                    'hook': hook_token,
                    'stated': stated,
                    'actual': actual,
                },
                extra={'rule': RULE_NAME},
            )
        )
    return [f.to_dict() for f in findings]


def _standards_population(standards_dir: Path) -> list[str]:
    """Return the sorted ``*.md`` filenames under ``standards_dir``.

    This listing is the population every persona-security-expert index claim is
    checked against. An unreadable directory yields the empty list, which the
    caller treats as a finding (fail-closed) rather than as a silent pass.
    """
    try:
        return sorted(p.name for p in standards_dir.glob('*.md') if p.is_file())
    except OSError:
        return []


def _section_body(lines: list[str], heading_text: str) -> list[tuple[int, str]] | None:
    """Return the ``(index, line)`` pairs of the section opened by ``heading_text``.

    The section runs from the first heading whose text starts with
    ``heading_text`` up to (but excluding) the next heading of any level.
    Returns ``None`` when no such heading exists, which the caller treats as a
    finding — a missing index section is drift, not an exemption.
    """
    start: int | None = None
    for idx, line in enumerate(lines):
        if _HEADING_RE.match(line) and line.lstrip('#').strip().startswith(heading_text):
            start = idx + 1
            break
    if start is None:
        return None
    body: list[tuple[int, str]] = []
    for idx in range(start, len(lines)):
        if _HEADING_RE.match(lines[idx]):
            break
        body.append((idx, lines[idx]))
    return body


def _table_link_set(body: list[tuple[int, str]]) -> set[str]:
    """Collect the ``standards/<name>.md`` link targets in an index-table body.

    Only table rows are considered, mirroring :func:`_table_first_cell_set`. A
    prose link to ``standards/<name>.md`` that sits in the section but outside
    the table is NOT an index entry — counting it would mask a genuinely
    missing table row and let the surface report a clean pass (fail-open).
    """
    names: set[str] = set()
    for _, line in body:
        if not line.lstrip().startswith('|'):
            continue
        names.update(_PSE_TABLE_LINK_RE.findall(line))
    return names


def _table_first_cell_set(body: list[tuple[int, str]]) -> set[str]:
    """Collect the bare ``<name>.md`` first-column cells in an index-table body."""
    names: set[str] = set()
    for _, line in body:
        if not line.lstrip().startswith('|'):
            continue
        cells = _cells(line)
        if not cells:
            continue
        candidate = _strip_cell(cells[0])
        if _PSE_TABLE_NAME_RE.match(candidate):
            names.add(candidate)
    return names


def _index_table_findings(
    skill_md: Path,
    lines: list[str],
    heading_text: str,
    listed: set[str] | None,
    population: list[str],
) -> list[Finding]:
    """Compare one index table's file set against the derived population.

    ``listed`` is ``None`` when the section itself is absent — reported as its
    own finding so a deleted index section cannot masquerade as agreement.
    """
    size = len(population)
    if listed is None:
        return [
            Finding(
                type=RULE_ID,
                file=str(skill_md),
                line=1,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'the persona-security-expert SKILL.md has no "{heading_text}" section, so the '
                    f'{size} document(s) enumerated on disk under standards/ are indexed nowhere '
                    f'checkable (literal-count-drift)'
                ),
                details={
                    'surface': heading_text,
                    'population_size': size,
                    'missing': population,
                    'unknown': [],
                },
                extra={'rule': RULE_NAME},
            )
        ]
    expected = set(population)
    missing = sorted(expected - listed)
    unknown = sorted(listed - expected)
    if not missing and not unknown:
        return []
    heading_line = next(
        (
            idx + 1
            for idx, line in enumerate(lines)
            if _HEADING_RE.match(line) and line.lstrip('#').strip().startswith(heading_text)
        ),
        1,
    )
    return [
        Finding(
            type=RULE_ID,
            file=str(skill_md),
            line=heading_line,
            severity='warning',
            fixable=False,
            rule_id=RULE_ID,
            description=(
                f'the persona-security-expert "{heading_text}" table indexes {len(listed)} '
                f'document(s) but standards/ enumerates {size} — missing from the table: '
                f'{missing}; indexed but absent from standards/: {unknown} (literal-count-drift)'
            ),
            details={
                'surface': heading_text,
                'population_size': size,
                'missing': missing,
                'unknown': unknown,
            },
            extra={'rule': RULE_NAME},
        )
    ]


def _prose_count_findings(skill_md: Path, lines: list[str], population: list[str]) -> list[Finding]:
    """Check every anchored prose count against the derived population size.

    Fails closed when NO anchored count is found: a body that states the count
    in an unrecognised phrasing is unverified, not verified-clean.
    """
    size = len(population)
    accepted = {str(size), _NUMBER_WORDS.get(size, str(size))}
    findings: list[Finding] = []
    matched = 0
    for idx, line in enumerate(lines):
        for anchor in _PSE_PROSE_ANCHOR_RES:
            for match in anchor.finditer(line):
                matched += 1
                stated = match.group('count')
                if stated.lower() in accepted:
                    continue
                findings.append(
                    Finding(
                        type=RULE_ID,
                        file=str(skill_md),
                        line=idx + 1,
                        severity='warning',
                        fixable=False,
                        rule_id=RULE_ID,
                        description=(
                            f'the persona-security-expert prose states {stated!r} standards '
                            f'sub-document(s) but standards/ enumerates {size} '
                            f'(literal-count-drift)'
                        ),
                        details={
                            'surface': 'prose',
                            'population_size': size,
                            'stated': stated,
                            'actual': size,
                        },
                        extra={'rule': RULE_NAME},
                    )
                )
    if matched == 0:
        findings.append(
            Finding(
                type=RULE_ID,
                file=str(skill_md),
                line=1,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'the persona-security-expert SKILL.md carries no anchored prose count for its '
                    f'{size} standards sub-document(s), so the prose claim is unverifiable — state '
                    f'it as "N `standards/` sub-documents" (literal-count-drift)'
                ),
                details={
                    'surface': 'prose',
                    'population_size': size,
                    'stated': None,
                    'actual': size,
                },
                extra={'rule': RULE_NAME},
            )
        )
    return findings


def _scan_persona_security_expert_index(skill_md: Path, standards_dir: Path) -> list[dict]:
    """Check the persona-security-expert standards index against its derived population."""
    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        # The caller already gated on is_file(), so this path means the governed
        # file EXISTS but cannot be read or is not valid UTF-8. Only an ABSENT
        # governed file is out of scope; an unreadable one must fail closed, or
        # a broken index is indistinguishable from a clean one.
        return [
            Finding(
                type=RULE_ID,
                file=str(skill_md),
                line=1,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'the persona-security-expert SKILL.md exists but could not be read '
                    f'({type(exc).__name__}), so none of its standards-index claims are '
                    f'verifiable (literal-count-drift)'
                ),
                details={'surface': 'unreadable', 'error': type(exc).__name__},
                extra={'rule': RULE_NAME},
            ).to_dict()
        ]
    lines = text.splitlines()
    population = _standards_population(standards_dir)
    if not population:
        return [
            Finding(
                type=RULE_ID,
                file=str(skill_md),
                line=1,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'the persona-security-expert standards index is checked against '
                    f'{standards_dir}, which enumerates 0 document(s) — the derived population is '
                    f'empty, so no index claim is verifiable (literal-count-drift)'
                ),
                details={'surface': 'population', 'population_size': 0},
                extra={'rule': RULE_NAME},
            ).to_dict()
        ]

    load_body = _section_body(lines, _PSE_LOAD_TABLE_HEADING)
    reference_body = _section_body(lines, _PSE_REFERENCE_TABLE_HEADING)
    findings: list[Finding] = []
    findings.extend(_prose_count_findings(skill_md, lines, population))
    findings.extend(
        _index_table_findings(
            skill_md,
            lines,
            _PSE_LOAD_TABLE_HEADING,
            None if load_body is None else _table_link_set(load_body),
            population,
        )
    )
    findings.extend(
        _index_table_findings(
            skill_md,
            lines,
            _PSE_REFERENCE_TABLE_HEADING,
            None if reference_body is None else _table_first_cell_set(reference_body),
            population,
        )
    )
    return [f.to_dict() for f in findings]


def analyze_literal_count(marketplace_root: Path, cache: AstCache | None = None) -> list[dict]:
    """Scan both governed count surfaces for drift against their derived populations.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.). The governed surfaces are
        ``plan-marshall/skills/extension-api/SKILL.md`` (the Extension Points
        table) and ``plan-marshall/skills/persona-security-expert/SKILL.md``
        (the standards index, checked against that skill's ``standards/``
        directory listing).

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape). A governed
        file that is absent contributes no findings; every other failure mode on
        the standards-index surface — empty population, missing index section,
        unanchored prose count — emits a finding rather than passing silently.
    """
    findings: list[dict] = []
    extension_api_md = marketplace_root / 'plan-marshall' / 'skills' / 'extension-api' / 'SKILL.md'
    if extension_api_md.is_file():
        ast_counts = _ast_hook_counts(marketplace_root, cache)
        provider_count = _provider_count(marketplace_root)
        findings.extend(_scan_extension_points_table(extension_api_md, ast_counts, provider_count))
    persona_dir = marketplace_root.joinpath(*_PSE_SKILL_PARTS)
    persona_md = persona_dir / 'SKILL.md'
    if persona_md.is_file():
        findings.extend(_scan_persona_security_expert_index(persona_md, persona_dir / 'standards'))
    return findings
