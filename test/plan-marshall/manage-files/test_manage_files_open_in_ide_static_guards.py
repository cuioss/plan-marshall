#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Static invariant tests for the manage-files open-in-ide surface."""

import ast
import re

from _manage_files_open_in_ide_fixtures import _MANAGE_FILES_SCRIPT

# =============================================================================
# Static guards — enforce hard invariants from solution_outline.md
# =============================================================================


def test_manage_files_source_does_not_import_tempfile():
    """AST guard: `tempfile` MUST NOT appear in any import statement."""
    source = _MANAGE_FILES_SCRIPT.read_text(encoding='utf-8')
    tree = ast.parse(source)

    bad_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'tempfile' or alias.name.startswith('tempfile.'):
                    bad_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == 'tempfile' or (node.module or '').startswith('tempfile.'):
                bad_imports.append(node.module or '')

    assert bad_imports == [], f'manage-files.py must not import tempfile, found: {bad_imports}'


def test_manage_files_source_has_no_temp_file_tokens():
    """Regex guard: source must not contain tempfile-related identifiers."""
    source = _MANAGE_FILES_SCRIPT.read_text(encoding='utf-8')

    # Strip module-level docstring lines that may legitimately mention the token
    # for documentation purposes. We do this by stripping the leading docstring.
    tree = ast.parse(source)
    module_doc = ast.get_docstring(tree)
    if module_doc is not None:
        # Re-emit the source with the docstring removed by replacing it once.
        source_without_doc = source.replace(module_doc, '')
    else:
        source_without_doc = source

    forbidden = ('tempfile', 'NamedTemporaryFile', 'mkstemp', 'mkdtemp')

    hits: list[str] = []
    for token in forbidden:
        # Use word-boundary regex so partial matches inside other identifiers
        # are not counted.
        if re.search(rf'\b{re.escape(token)}\b', source_without_doc):
            hits.append(token)

    assert hits == [], f'manage-files.py contains forbidden temp-file tokens (outside docstring): {hits}'


def test_open_in_ide_path_and_plan_id_share_mutex_group():
    """AST guard: --path and --plan-id MUST be added to the same mutex group."""
    source = _MANAGE_FILES_SCRIPT.read_text(encoding='utf-8')

    # locate the open-in-ide subparser block and verify both
    # --path and --plan-id are added via the SAME mutex variable.
    # The simplest deterministic check: scan for a block that contains both
    # `open_mutex.add_argument('--path'` and `open_mutex.add_argument('--plan-id'`
    # (or `add_argument(\n        '--plan-id'` style — match flexibly).
    has_path_in_mutex = re.search(
        r"open_mutex\.add_argument\(\s*['\"]--path['\"]",
        source,
    )
    has_plan_id_in_mutex = re.search(
        r"open_mutex\.add_argument\(\s*['\"]--plan-id['\"]",
        source,
    )
    assert has_path_in_mutex, '--path must be added to the open-in-ide mutex group'
    assert has_plan_id_in_mutex, '--plan-id must be added to the open-in-ide mutex group'
