# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared constants and helpers for the split shared-harness collection units.

The helpers are consumed by every split unit at once, so a regression in them
is a regression everywhere. The module is underscore-prefixed to stay outside
pytest collection; each split unit imports what it needs explicitly.
"""

import ast
from pathlib import Path

# Resolved against the test-tree root, not this module's own directory: the
# constant was hoisted verbatim from test_shared_harness.py (where .parent was
# test/) into test/_shared/ (where .parent would be test/_shared).
TEST_ROOT = Path(__file__).resolve().parent.parent

#: A real script with a rich defaulted flag set, reached through the
#: main()-interception seam. Coupling the test to a real script is deliberate:
#: the property under test is that the PRODUCTION parser's defaults arrive, which
#: a synthetic parser could not demonstrate.
_DEFAULTS_CASE = ('plan-marshall', 'manage-findings', 'manage-findings.py')
_DEFAULTS_ARGV = ('list', '--plan-id', 'p1')

#: Flags the caller above does NOT name, which the real parser defaults anyway.
_UNNAMED_DEFAULTS = ('type', 'resolution', 'promoted', 'file_pattern', 'author', 'kind', 'bot_kind')

#: A real module that constructs an ``ArgumentParser`` but publishes no builder
#: and has no ``main()`` — a library module, not a CLI entry point.
_NO_SEAM_CASE = ('plan-marshall', 'tools-integration-ci', 'ci_base.py')

#: Directory names that never hold collectable test source. ``fixtures`` is in
#: ``norecursedirs`` (pyproject), so pytest never collects under it — a scan that
#: walked it would report a testless module pytest does not import.
EXCLUDED_DIR_NAMES = frozenset({'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'fixtures'})


def _is_collected_name(name: str) -> bool:
    """Whether a basename matches a pytest collection pattern.

    Deliberately a SUPERSET of this project's ``python_files`` setting, which is
    ``test_*.py`` alone: D3's done-when names both spellings, and a ``*_test.py``
    helper would be an offender the moment the setting widened. Over-collecting
    here only ever guards more.
    """
    return name.startswith('test_') or name.endswith('_test.py')


def _declares_a_test(tree: ast.Module) -> bool:
    """Whether a parsed module declares any test function or ``Test*`` class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith('test'):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            return True
    return False


def scan_for_testless_collected_modules(root: Path) -> tuple[list[str], int]:
    """Find modules pytest collects that declare no test.

    Read and parse failures are deliberately NOT swallowed: a file that cannot be
    read is a file that might be an offender and was never checked, which is a
    coverage gap rather than a clean result.

    Args:
        root: Directory to walk. A non-existent directory yields an empty
            population, which the caller's population assertion then catches.

    Returns:
        ``(offenders, scanned)`` — ``scanned`` is how many collected modules were
        parsed, returned alongside the list precisely so a caller can prove the
        scan had something to examine.
    """
    offenders: list[str] = []
    scanned = 0
    if not root.is_dir():
        return offenders, scanned

    for path in sorted(root.rglob('*.py')):
        if EXCLUDED_DIR_NAMES.intersection(path.parts):
            continue
        if not _is_collected_name(path.name):
            continue
        scanned += 1
        if not _declares_a_test(ast.parse(path.read_text(encoding='utf-8'))):
            offenders.append(str(path))

    return offenders, scanned
