#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Literal-count-drift analyzer for the ``literal-count-drift`` rule.

This module detects drift between a manually-maintained numeric-literal count
token in plugin-doctor-governed skill text and the machine-derivable count of
the items that token describes. The initial (and currently only) governed
surface is the ``extension-api`` ``SKILL.md`` "Extension Points" table, whose
"Implementations" column states, per extension point, how many concrete
implementations exist. That count is a hand-maintained mirror of the on-disk
implementer set: when a bundle adds or drops an extension-point implementation
without editing the table, the count silently rots.

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

RULE_ID = 'literal-count-drift'
RULE_NAME = 'analyze_literal_count'

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


def _is_default_return(node: ast.FunctionDef, default: object) -> bool:
    """Return True when ``node``'s body returns only the base-class default.

    Mirrors ``_analyze_provides_method_table.py::_is_default_return`` exactly: a
    method whose entire body is ``return None`` (or a bare ``return`` / ``pass``)
    matches a ``None`` default; a method whose entire body is ``return []``
    matches a ``[]`` default. Any other single return — or branching logic —
    is a real override.
    """
    returns = [stmt for stmt in ast.walk(node) if isinstance(stmt, ast.Return)]
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


def _extension_overrides(extension_path: Path) -> dict[str, bool]:
    """Map each AST hook method to whether ``extension_path`` really overrides it.

    Returns a dict keyed by the four AST hook names; the value is True when the
    concrete ``*ExtensionBase`` subclass overrides the hook with a non-default
    return, False when the method is absent OR returns only the base default.
    Returns all-False when the file cannot be read or parsed (the structural /
    syntax rules cover that failure mode separately).
    """
    overrides: dict[str, bool] = dict.fromkeys(_AST_HOOK_DEFAULTS, False)
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


def _ast_hook_counts(marketplace_root: Path) -> dict[str, int]:
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
        for hook, is_override in _extension_overrides(ext).items():
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

    findings: list[dict] = []
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
        # The implementations cell is the bare-integer cell on the row.
        int_cells = [c for c in cells if _BARE_INT_RE.match(_strip_cell(c))]
        if not int_cells:
            continue
        stated = int(_strip_cell(int_cells[-1]))
        actual = provider_count if hook_token == '*_provider.py' else ast_counts.get(hook_token, 0)
        if stated == actual:
            continue
        findings.append(
            {
                'rule_id': RULE_ID,
                'type': RULE_ID,
                'rule': RULE_NAME,
                'file': str(skill_md),
                'line': idx + 1,
                'severity': 'warning',
                'fixable': False,
                'description': (
                    f'the "Extension Points" table states {stated} implementation(s) '
                    f'for hook `{hook_token}` but the bundle tree enumerates {actual} — '
                    f'the count is a stale mirror of the implementer set (literal-count-drift)'
                ),
                'details': {
                    'hook': hook_token,
                    'stated': stated,
                    'actual': actual,
                },
            }
        )
    return findings


def analyze_literal_count(marketplace_root: Path) -> list[dict]:
    """Scan the extension-api Extension Points table for stale Implementations counts.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.). The governed surface is
        ``plan-marshall/skills/extension-api/SKILL.md``.

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape). Returns an
        empty list when the governed file is absent.
    """
    skill_md = marketplace_root / 'plan-marshall' / 'skills' / 'extension-api' / 'SKILL.md'
    if not skill_md.is_file():
        return []
    ast_counts = _ast_hook_counts(marketplace_root)
    provider_count = _provider_count(marketplace_root)
    return _scan_extension_points_table(skill_md, ast_counts, provider_count)
