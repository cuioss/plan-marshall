#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Resolver-matrix-coverage analyzer for the ``resolver-matrix-coverage`` rule.

This module implements a deterministic AST scanner that detects N-input
skip-on-miss resolver chains (≥3 tiers) in marketplace scripts and surfaces
a ``tip``-severity finding when the corresponding test file's parametrize
matrix is under-covered.

Motivation
----------
A "skip-on-miss" resolver is a function whose body is a sequence of
``if {guard}: return {early_value}`` statements followed by a final
``return {default}`` — i.e., a partial-order resolution chain where each
tier either short-circuits or falls through to the next. When such a
resolver has ≥3 tiers, the test surface needs to cover every
``tier × {hit, miss}`` cell (``tier_count * 2`` cells minimum) so the
contract between tiers does not drift silently on future edits. This
analyzer flags resolvers whose test file does not declare enough
parametrize cells / distinct test functions to cover the full matrix.

Generalises the recurrence guard codified by Deliverable 5 of the
``fix-terminal-title-integration`` plan: the lesson there (the post-D2
``session_render_title`` chain has five guarded-return tiers and was
covered by point tests rather than a matrix) is the canonical real-world
detection target.

Pattern alignment
-----------------
Mirrors ``_analyze_role_field.py`` and ``_analyze_test_conventions.py``:

- pure static analysis (no subprocess execution, no imports of target
  scripts)
- AST-driven detection
- stdlib-only dependencies
- no mutation of any file
- path-scoped: only files under
  ``marketplace_root/{bundle}/skills/{skill}/scripts/*.py`` are inspected

Detection — Production side
---------------------------
A function (top-level ``def``, async ``def``, or method) is a skip-on-miss
resolver iff:

1. its body is a sequence of zero-or-more ``ast.If`` statements WITHOUT
   ``orelse`` whose body is a single ``ast.Return`` (the "tier" guards),
2. followed by a final ``ast.Return`` (the fallback),
3. non-tier statements (assignments, expression statements, ``try`` /
   ``with`` blocks, etc.) may appear interleaved between tiers but are
   ignored — only the sequence of guarded-returns is counted.

The threshold ``MIN_TIER_COUNT = 3`` rules 2-tier resolvers out of scope
(they are trivially testable as ``hit / miss``).

Detection — Test side
---------------------
The corresponding test file lives at
``{project_root}/test/{bundle}/{skill}/test_{module}.py``. The analyzer
counts:

- ``@pytest.mark.parametrize`` decorator cell counts — each ``ast.List`` /
  ``ast.Tuple`` of cells contributes ``len(cells)`` to the cell count, ALL
  parametrize decorators on test functions in the file are summed (the
  matrix may be spread across multiple parametrized test functions),
- distinct ``def test_*`` functions whose body or decorator mentions the
  resolver function name — each adds 1 to the cell count.

The two counters are summed. When ``cell_count < tier_count * 2``, a
finding is emitted with ``severity: tip`` and ``category:
resolver-matrix-coverage``.

When the test file does not exist, the analyzer emits a finding with the
``test_file_missing: true`` detail — under-coverage is structurally
guaranteed when no test file exists.

Findings have the shape::

    {
        'rule_id': 'resolver-matrix-coverage',
        'type': 'resolver-matrix-coverage',
        'rule': 'analyze_resolver_matrix_coverage',
        'file': '<absolute production-script path>',
        'line': <function lineno>,
        'severity': 'tip',
        'fixable': False,
        'snippet': '<bundle>:<skill>:<function_name>',
        'description': '...',
        'details': {
            'bundle': <bundle>,
            'skill': <skill>,
            'function_name': <name>,
            'tier_count': <int>,
            'required_cells': <tier_count * 2>,
            'actual_cells': <int>,
            'test_file': <path or None>,
            'test_file_missing': <bool>,
        },
    }

Public API
----------
- ``analyze_resolver_matrix_coverage(marketplace_root, project_root=None)``:
  entry point. ``marketplace_root`` is the bundles root (the directory that
  contains ``plan-marshall``, ``pm-plugin-development``, etc.).
  ``project_root`` defaults to ``marketplace_root.parent`` and is the root
  used to resolve the ``test/`` directory.
"""

from __future__ import annotations

import ast
from pathlib import Path

RULE_ID = 'resolver-matrix-coverage'
RULE_NAME = 'analyze_resolver_matrix_coverage'
FINDING_TYPE = 'resolver-matrix-coverage'

MIN_TIER_COUNT = 3

_DESCRIPTION_TEMPLATE = (
    'N-input skip-on-miss resolver `{name}` has {tier_count} tiers but the '
    'corresponding test file declares only {actual_cells} parametrize cells / '
    'test methods (required: {required_cells} = tier_count * 2). Cover every '
    'tier x {{hit, miss}} cell via a `@pytest.mark.parametrize` matrix so the '
    'inter-tier contract cannot drift silently on future edits.'
)

_DESCRIPTION_MISSING_TEMPLATE = (
    'N-input skip-on-miss resolver `{name}` has {tier_count} tiers but no '
    'corresponding test file exists at `{test_file}`. Add a '
    '`@pytest.mark.parametrize` matrix covering every tier x {{hit, miss}} '
    'cell (required: {required_cells} cells).'
)


# ---------------------------------------------------------------------------
# Production-side detection (skip-on-miss resolver chain)
# ---------------------------------------------------------------------------


def _is_guarded_return(node: ast.stmt) -> bool:
    """Return True iff ``node`` is an ``if {guard}: return X`` with no ``else``.

    The guard tier shape we care about is a single-armed ``if`` whose body
    contains exactly one statement (a ``return``). Multi-statement bodies
    (e.g., logging + return) and ``if/else`` branches are NOT treated as
    skip-on-miss tiers — they encode richer control flow that is out of
    scope for the matrix-coverage heuristic.
    """
    if not isinstance(node, ast.If):
        return False
    if node.orelse:
        return False
    if len(node.body) != 1:
        return False
    return isinstance(node.body[0], ast.Return)


def _count_skip_on_miss_tiers(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count the skip-on-miss tiers in ``func``'s body.

    A tier is a top-level ``if {guard}: return X`` (per ``_is_guarded_return``).
    The function body MUST also end with an unguarded ``ast.Return`` (the
    fallback). When no final fallback exists, the function is not a
    skip-on-miss resolver and 0 is returned regardless of how many guarded
    returns it contains.
    """
    body = func.body
    if not body:
        return 0
    # Final statement MUST be an unguarded return (the fallback). Otherwise
    # this is not a skip-on-miss resolver — it's some other control-flow
    # shape that happens to contain guarded returns.
    if not isinstance(body[-1], ast.Return):
        return 0
    return sum(1 for stmt in body[:-1] if _is_guarded_return(stmt))


def _iter_resolver_functions(
    tree: ast.AST,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield every function / method in ``tree`` that is a ≥N-tier resolver.

    Walks the entire module tree (including methods nested inside classes)
    and returns the AST nodes whose tier count meets ``MIN_TIER_COUNT``.
    """
    resolvers: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        tier_count = _count_skip_on_miss_tiers(node)
        if tier_count >= MIN_TIER_COUNT:
            resolvers.append(node)
    return resolvers


# ---------------------------------------------------------------------------
# Test-side detection (parametrize-matrix coverage)
# ---------------------------------------------------------------------------


def _resolve_test_file(
    project_root: Path,
    production_path: Path,
    marketplace_root: Path,
) -> Path | None:
    """Resolve the test file path for ``production_path``.

    Production layout::

        {marketplace_root}/{bundle}/skills/{skill}/scripts/{module}.py

    Test layout::

        {project_root}/test/{bundle}/{skill}/test_{module}.py

    Returns ``None`` when ``production_path`` does not fit the expected
    layout (path is outside ``marketplace_root/{bundle}/skills/{skill}/
    scripts/``). The returned path is NOT guaranteed to exist — the caller
    checks ``.is_file()`` separately so it can emit the
    ``test_file_missing`` variant of the finding.
    """
    try:
        rel = production_path.relative_to(marketplace_root)
    except ValueError:
        return None
    parts = rel.parts
    # Expected: ({bundle}, 'skills', {skill}, 'scripts', {module}.py)
    if len(parts) < 5:
        return None
    bundle, skills_dir, skill, scripts_dir = parts[0], parts[1], parts[2], parts[3]
    if skills_dir != 'skills' or scripts_dir != 'scripts':
        return None
    module_name = production_path.stem
    test_name = f'test_{module_name}.py'
    return project_root / 'test' / bundle / skill / test_name


def _parse_test_file(test_path: Path) -> ast.AST | None:
    """Read and parse ``test_path``; return ``None`` on unreadable / unparseable."""
    try:
        source = test_path.read_text(encoding='utf-8')
    except OSError:
        return None
    try:
        return ast.parse(source, filename=str(test_path))
    except SyntaxError:
        return None


def _decorator_is_parametrize(decorator: ast.expr) -> bool:
    """Return True iff ``decorator`` is a ``@pytest.mark.parametrize(...)`` call."""
    if not isinstance(decorator, ast.Call):
        return False
    func = decorator.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != 'parametrize':
        return False
    parent = func.value
    if not isinstance(parent, ast.Attribute):
        return False
    if parent.attr != 'mark':
        return False
    grandparent = parent.value
    return isinstance(grandparent, ast.Name) and grandparent.id == 'pytest'


def _count_parametrize_cells(decorator: ast.Call) -> int:
    """Count the cell rows in a ``@pytest.mark.parametrize(names, values)`` call.

    The cell-bearing argument is the SECOND positional argument (the
    ``values`` iterable) or, when callers pass it by keyword, the
    ``argvalues=...`` keyword argument. When the values argument is an
    ``ast.List`` or ``ast.Tuple``, returns ``len(values.elts)``. Otherwise
    (dynamic expression — comprehension, function call, name reference),
    returns 0 so the analyzer falls back to counting distinct test methods
    instead.
    """
    values: ast.expr | None = None
    if len(decorator.args) >= 2:
        values = decorator.args[1]
    else:
        for kw in decorator.keywords:
            if kw.arg == 'argvalues':
                values = kw.value
                break
    if values is None:
        return 0
    if isinstance(values, ast.List | ast.Tuple):
        return len(values.elts)
    return 0


def _count_test_coverage(test_tree: ast.AST, function_name: str) -> int:
    """Count parametrize cells + distinct test methods mentioning ``function_name``.

    Walks ``test_tree`` looking for ``def test_*`` (sync or async) at any
    nesting level. A test function contributes to coverage ONLY if it
    references ``function_name`` (via ``ast.Name`` / ``ast.Attribute``
    lookups in the function body or its decorators). For each such
    referencing test function:

    - sum the cell counts of its ``@pytest.mark.parametrize`` decorators,
    - add 1 (a discrete test method directly exercises the resolver).

    Test functions that do not reference ``function_name`` are ignored —
    their parametrize cells do not inflate coverage for the resolver
    under review.

    Returns the sum.
    """
    total_cells = 0
    for node in ast.walk(test_tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith('test_'):
            continue
        # Only count test functions that reference the resolver name.
        # Otherwise unrelated parametrize matrices in the same file would
        # inflate this resolver's coverage count.
        if not _references_name(node, function_name):
            continue
        # Sum parametrize cells across all parametrize decorators.
        parametrize_total = 0
        for decorator in node.decorator_list:
            if _decorator_is_parametrize(decorator):
                # _decorator_is_parametrize guarantees decorator is ast.Call.
                assert isinstance(decorator, ast.Call)
                parametrize_total += _count_parametrize_cells(decorator)
        total_cells += parametrize_total
        # Count this test function as one discrete coverage point. This
        # handles the transitional state where a parametrize matrix has
        # not yet been introduced but per-scenario point tests already
        # exist.
        total_cells += 1
    return total_cells


def _references_name(func_node: ast.AST, target_name: str) -> bool:
    """Return True iff any ``ast.Name`` / ``ast.Attribute`` in ``func_node`` matches ``target_name``."""
    for child in ast.walk(func_node):
        if isinstance(child, ast.Name) and child.id == target_name:
            return True
        if isinstance(child, ast.Attribute) and child.attr == target_name:
            return True
    return False


# ---------------------------------------------------------------------------
# Finding construction
# ---------------------------------------------------------------------------


def _build_finding(
    production_path: Path,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    tier_count: int,
    actual_cells: int,
    test_file: Path | None,
    test_file_missing: bool,
    bundle: str,
    skill: str,
) -> dict:
    required_cells = tier_count * 2
    if test_file_missing:
        description = _DESCRIPTION_MISSING_TEMPLATE.format(
            name=func_node.name,
            tier_count=tier_count,
            test_file=test_file,
            required_cells=required_cells,
        )
    else:
        description = _DESCRIPTION_TEMPLATE.format(
            name=func_node.name,
            tier_count=tier_count,
            actual_cells=actual_cells,
            required_cells=required_cells,
        )
    return {
        'rule_id': RULE_ID,
        'type': FINDING_TYPE,
        'rule': RULE_NAME,
        'file': str(production_path),
        'line': func_node.lineno,
        'severity': 'tip',
        'fixable': False,
        'snippet': f'{bundle}:{skill}:{func_node.name}',
        'description': description,
        'category': 'resolver-matrix-coverage',
        'details': {
            'bundle': bundle,
            'skill': skill,
            'function_name': func_node.name,
            'tier_count': tier_count,
            'required_cells': required_cells,
            'actual_cells': actual_cells,
            'test_file': str(test_file) if test_file is not None else None,
            'test_file_missing': test_file_missing,
        },
    }


# ---------------------------------------------------------------------------
# Module / script discovery
# ---------------------------------------------------------------------------


def _iter_script_files(marketplace_root: Path) -> list[Path]:
    """Yield every ``*.py`` file under ``marketplace_root/{bundle}/skills/{skill}/scripts/``."""
    if not marketplace_root.is_dir():
        return []
    results: list[Path] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            scripts_dir = skill_dir / 'scripts'
            if not scripts_dir.is_dir():
                continue
            for script_path in sorted(scripts_dir.glob('*.py')):
                if script_path.is_file():
                    results.append(script_path)
    return results


def _parse_script(path: Path) -> ast.AST | None:
    """Read and parse ``path``; return ``None`` on unreadable / unparseable."""
    try:
        source = path.read_text(encoding='utf-8')
    except OSError:
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError:
        return None


def _bundle_skill_for(path: Path, marketplace_root: Path) -> tuple[str, str] | None:
    """Return ``(bundle, skill)`` for ``path`` or ``None`` when path is outside layout."""
    try:
        rel = path.relative_to(marketplace_root)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 5:
        return None
    if parts[1] != 'skills' or parts[3] != 'scripts':
        return None
    return parts[0], parts[2]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_resolver_matrix_coverage(
    marketplace_root: Path, project_root: Path | None = None
) -> list[dict]:
    """Scan marketplace scripts for under-covered N-input skip-on-miss resolvers.

    ``marketplace_root`` is the bundles root (the directory that contains
    ``plan-marshall``, ``pm-plugin-development``, etc.). ``project_root``
    defaults to ``marketplace_root.parent`` and is the root used to
    resolve the ``test/`` directory; pass it explicitly when the test tree
    lives elsewhere (e.g., synthetic test fixtures).

    Returns a list of ``tip``-severity findings, one per under-covered
    resolver function. Files outside the expected layout are silently
    skipped (no findings emitted).
    """
    if project_root is None:
        project_root = marketplace_root.parent

    findings: list[dict] = []
    for script_path in _iter_script_files(marketplace_root):
        bundle_skill = _bundle_skill_for(script_path, marketplace_root)
        if bundle_skill is None:
            continue
        bundle, skill = bundle_skill
        tree = _parse_script(script_path)
        if tree is None:
            continue
        resolvers = _iter_resolver_functions(tree)
        if not resolvers:
            continue
        test_file = _resolve_test_file(project_root, script_path, marketplace_root)
        test_tree: ast.AST | None = None
        test_file_missing = test_file is None or not test_file.is_file()
        if not test_file_missing:
            # test_file is not None here (verified by test_file_missing check).
            assert test_file is not None
            test_tree = _parse_test_file(test_file)
        for func_node in resolvers:
            tier_count = _count_skip_on_miss_tiers(func_node)
            required = tier_count * 2
            if test_tree is None:
                actual = 0
            else:
                actual = _count_test_coverage(test_tree, func_node.name)
            if actual >= required:
                continue
            findings.append(
                _build_finding(
                    production_path=script_path,
                    func_node=func_node,
                    tier_count=tier_count,
                    actual_cells=actual,
                    test_file=test_file,
                    test_file_missing=test_file_missing,
                    bundle=bundle,
                    skill=skill,
                )
            )
    findings.sort(key=lambda f: (f['file'], f.get('line', 0)))
    return findings
