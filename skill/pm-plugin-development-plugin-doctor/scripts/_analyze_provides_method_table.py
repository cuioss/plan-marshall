#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provides-method-table-drift analyzer for the ``provides-method-table-drift`` rule.

This module detects drift between a domain bundle's ``extension.py``
``provides_*()`` overrides (the machine-derivable source of truth) and the
manually-maintained ``provides_*()`` function-name column in that bundle's
``plan-marshall-plugin`` ``SKILL.md`` "Extension API" table.

The "Extension API" table is a hand-maintained mirror of the extension's
workflow-hook overrides. When an override is added or removed in
``extension.py`` without a matching table edit, the mirror silently rots: a
reader of the SKILL.md sees a stale capability list. This analyzer makes the
mirror machine-checkable.

Source of truth
---------------
The base class :class:`ExtensionBase` (``plan-marshall:script-shared``) declares
four workflow-hook methods with sensible defaults:

- ``provides_triage`` → ``None``
- ``provides_outline_skill`` → ``None``
- ``provides_recipes`` → ``[]``
- ``provides_retrospective_aspects`` → ``[]``

A concrete ``Extension`` subclass *overrides* a hook when it returns a value
other than the base default. An override is the machine-derivable fact the
table claims to mirror.

Structural discriminator (no false positives)
---------------------------------------------
The "Extension API" section is treated as a machine-checkable mirror ONLY when
it is a markdown TABLE carrying a ``provides_*()`` function-name column — the
form ``| `provides_x()` | ... |``. A bullet-list capability description
(``- `provides_x()` - Triage skill reference or None``) is generic API prose,
NOT a mirror, and is deliberately out of scope: such bullets describe the hook
contract abstractly and do not claim to enumerate THIS extension's concrete
overrides. Restricting to table rows is the structural discriminator that
separates a real mirror from benign generic documentation, so the rule fires
only where a stale mirror genuinely exists.

Detection
---------
For each ``marketplace_root/*/skills/plan-marshall-plugin/SKILL.md`` paired with
its sibling ``extension.py``:

1. AST-load ``extension.py`` and classify each ``provides_*`` method defined on
   the concrete ``Extension`` class as a *real override* (returns a non-default
   value) or a *default override* (its body returns only the base default —
   ``None`` for triage/outline, ``[]`` for recipes/retrospective).
2. Extract the ``provides_*()`` function-name tokens from the markdown-table
   rows in the SKILL.md "Extension API" section.
3. Emit a warning-severity, non-fixable finding for:

   - **override-missing-from-table** — a real override absent from the table.
   - **phantom-table-row** — a table row naming a ``provides_*()`` method that
     is NOT a real override (the method is undefined on the class, or its body
     returns the base-class default).

Findings have the shape::

    {
        'rule_id': 'provides-method-table-drift',
        'type': 'provides-method-table-drift',
        'rule': 'analyze_provides_method_table',
        'file': '<absolute SKILL.md path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'description': '<human-readable drift description>',
        'details': {
            'bundle': '<bundle name>',
            'method': 'provides_x',
            'reason': 'override_missing_from_table' | 'phantom_table_row',
            'extension_path': '<absolute extension.py path>',
        },
    }

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_declared_vs_disk.py``:

- pure static analysis (AST + regex + pathlib; no subprocess, no import of the
  target ``extension.py``);
- stdlib-only dependencies;
- no mutation of any file.

Public API
----------
- ``analyze_provides_method_table(marketplace_root)``: entry point — scans every
  ``*/skills/plan-marshall-plugin/SKILL.md`` paired with its sibling
  ``extension.py`` under ``marketplace_root`` and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from _dep_index import AstCache
from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'provides-method-table-drift'
RULE_NAME = 'analyze_provides_method_table'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='structural',
    scope='corpus-relational',
)

# The four workflow-hook methods declared on ExtensionBase, mapped to the base
# default each returns. A subclass override is a "real override" only when its
# body returns a value distinguishable from this default.
_HOOK_DEFAULTS: dict[str, object] = {
    'provides_triage': None,
    'provides_outline_skill': None,
    'provides_recipes': [],
    'provides_retrospective_aspects': [],
}

# A ``provides_*()`` token inside a markdown table cell. Matches the function
# name in the form ``provides_foo()`` (optionally backtick-wrapped). The table
# row is identified separately by the leading-pipe check in ``_table_methods``.
_PROVIDES_TOKEN_RE = re.compile(r'provides_(\w+)\(\)')

# The "Extension API" section heading (any heading level).
_EXTENSION_API_HEADING_RE = re.compile(r'^\s*#{1,6}\s+Extension API\s*$', re.IGNORECASE)

# Any markdown heading line (used to bound the Extension API section).
_HEADING_RE = re.compile(r'^\s*#{1,6}\s+\S')


def _is_default_return(node: ast.FunctionDef, default: object) -> bool:
    """Return True when ``node``'s body returns only the base-class default.

    A method whose entire body is ``return None`` (or a bare ``return`` /
    ``pass``) matches a ``None`` default; a method whose entire body is
    ``return []`` matches a ``[]`` default. Any other return value — a string
    literal, a non-empty list, a call, a name — is a real override.

    A method body containing control flow or multiple statements before the
    return is conservatively treated as a real override (it does more than echo
    the default), so the rule never spuriously flags a genuine override as a
    phantom row.
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
        # No explicit return — body is `pass` or only side effects → implicitly
        # returns None. Matches a None default; never matches a [] default.
        return default is None
    if len(returns) != 1:
        # Multiple returns imply branching logic → a real override.
        return False
    value = returns[0].value
    if value is None:
        # Bare ``return`` → returns None.
        return default is None
    if isinstance(value, ast.Constant) and value.value is None:
        return default is None
    if isinstance(value, ast.List) and not value.elts:
        # ``return []`` → empty-list default.
        return isinstance(default, list)
    return False


def _extension_overrides(extension_path: Path, cache: AstCache | None = None) -> dict[str, bool] | None:
    """Map each ``provides_*`` hook method to whether it is a real override.

    AST-parses ``extension_path`` and inspects every class that subclasses a
    name ending in ``ExtensionBase``. Returns a dict keyed by the four hook
    method names; the value is True when the class overrides the hook with a
    non-default return, False when the method is absent OR returns only the base
    default. Returns ``None`` when the file cannot be read or parsed (the
    structural / syntax rules cover that failure mode).
    """
    if cache is not None:
        tree = cache.get_tree(extension_path)
        if tree is None:
            return None
    else:
        try:
            source = extension_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            return None
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None

    overrides: dict[str, bool] = dict.fromkeys(_HOOK_DEFAULTS, False)
    for class_node in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        if not _subclasses_extension_base(class_node):
            continue
        for method in (m for m in class_node.body if isinstance(m, ast.FunctionDef)):
            if method.name not in _HOOK_DEFAULTS:
                continue
            default = _HOOK_DEFAULTS[method.name]
            overrides[method.name] = not _is_default_return(method, default)
    return overrides


def _subclasses_extension_base(class_node: ast.ClassDef) -> bool:
    """Return True when ``class_node`` lists an ``*ExtensionBase`` base class."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id.endswith('ExtensionBase'):
            return True
        if isinstance(base, ast.Attribute) and base.attr.endswith('ExtensionBase'):
            return True
    return False


def _table_methods(lines: list[str]) -> dict[str, int]:
    """Map each ``provides_*`` method named in an Extension-API TABLE row to its line.

    Scans the "Extension API" section (bounded by the next heading) for markdown
    TABLE rows — lines whose first non-whitespace character is ``|`` — and
    extracts every ``provides_*()`` token from them. Bullet-list lines
    (``- `provides_x()` - ...``) and prose are NOT table rows and are ignored,
    so generic API capability documentation never matches.

    Returns a dict keyed by hook method name with the 1-based line number of the
    table row that named it (first occurrence wins). An empty dict means the
    section is absent or carries no table rows naming a hook method.
    """
    in_section = False
    methods: dict[str, int] = {}
    for idx, line in enumerate(lines):
        if not in_section:
            if _EXTENSION_API_HEADING_RE.match(line):
                in_section = True
            continue
        # A new heading closes the Extension API section.
        if _HEADING_RE.match(line):
            break
        # Only markdown table rows are mirror rows; only the hook-name cell
        # (first cell) is parsed to avoid false matches from description text.
        if line.lstrip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if not cells:
                continue
            for match in _PROVIDES_TOKEN_RE.finditer(cells[0]):
                method = f'provides_{match.group(1)}'
                if method in _HOOK_DEFAULTS and method not in methods:
                    methods[method] = idx + 1
    return methods


def _scan_skill(skill_md: Path, cache: AstCache | None = None) -> list[dict]:
    """Scan one plan-marshall-plugin SKILL.md against its sibling extension.py."""
    extension_path = skill_md.parent / 'extension.py'
    if not extension_path.is_file():
        # No sibling extension — nothing to mirror against. Skip silently.
        return []
    overrides = _extension_overrides(extension_path, cache)
    if overrides is None:
        return []

    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    table = _table_methods(lines)
    if not table:
        # The Extension API section is absent or uses a non-table form
        # (generic bullet-list documentation). Not a machine-checkable mirror.
        return []

    bundle = skill_md.parent.parent.parent.name
    findings: list[Finding] = []

    # Direction A: a real override missing from the table.
    for method, is_override in overrides.items():
        if is_override and method not in table:
            findings.append(
                Finding(
                    type=RULE_ID,
                    file=str(skill_md),
                    line=1,
                    severity='warning',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        f'extension.py overrides `{method}()` but the '
                        f'"Extension API" table does not list it — the table is '
                        f'a stale mirror of the extension overrides '
                        f'(provides-method-table-drift)'
                    ),
                    details={
                        'bundle': bundle,
                        'method': method,
                        'reason': 'override_missing_from_table',
                        'extension_path': str(extension_path),
                    },
                    extra={'rule': RULE_NAME},
                )
            )

    # Direction B: a phantom table row naming a method that is not a real override.
    for method, line_no in table.items():
        if not overrides.get(method, False):
            findings.append(
                Finding(
                    type=RULE_ID,
                    file=str(skill_md),
                    line=line_no,
                    severity='warning',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        f'the "Extension API" table lists `{method}()` but '
                        f'extension.py does not override it with a non-default '
                        f'return — the table row is a phantom mirror entry '
                        f'(provides-method-table-drift)'
                    ),
                    details={
                        'bundle': bundle,
                        'method': method,
                        'reason': 'phantom_table_row',
                        'extension_path': str(extension_path),
                    },
                    extra={'rule': RULE_NAME},
                )
            )

    return [f.to_dict() for f in findings]


def analyze_provides_method_table(marketplace_root: Path, cache: AstCache | None = None) -> list[dict]:
    """Scan every plan-marshall-plugin SKILL.md for Extension-API table drift.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.). Every
        ``*/skills/plan-marshall-plugin/SKILL.md`` paired with a sibling
        ``extension.py`` is scanned.

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape). Returns an
        empty list when no matching SKILL.md / extension.py pairs exist.
    """
    findings: list[dict] = []
    try:
        skill_mds = sorted(marketplace_root.glob('*/skills/plan-marshall-plugin/SKILL.md'))
    except OSError:
        return findings
    for skill_md in skill_mds:
        if skill_md.is_file():
            findings.extend(_scan_skill(skill_md, cache))
    return findings
