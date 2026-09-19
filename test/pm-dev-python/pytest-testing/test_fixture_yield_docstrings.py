#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A fixture docstring says yield only when the fixture yields."""

import ast
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent.parent.parent


def _is_fixture_decorator(decorator: ast.expr) -> bool:
    """Decide whether a decorator expression marks a pytest fixture."""
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id == 'fixture'
    return isinstance(target, ast.Attribute) and target.attr == 'fixture'


def _fixture_defs(tree: ast.AST) -> list:
    """Return the fixture function definitions selected from a parsed tree."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_is_fixture_decorator(decorator) for decorator in node.decorator_list)
    ]


def _body_yields(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Decide whether the fixture body itself yields, ignoring nested scopes."""
    stack: list[ast.AST] = list(node.body)
    while stack:
        child = stack.pop()
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
        stack.extend(ast.iter_child_nodes(child))
    return False


def _fixture_yield_mismatches(source: str) -> list:
    """Return the names of fixtures whose docstring says yield but whose body never yields."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mismatches = []
    for node in _fixture_defs(tree):
        docstring = ast.get_docstring(node) or ''
        if 'yield' not in docstring.lower():
            continue
        if not _body_yields(node):
            mismatches.append(node.name)
    return mismatches


def test_detector_fires_on_a_return_form_fixture_saying_yield():
    """A return-form fixture documented as yielding is reported."""
    source = (
        'import pytest\n'
        '\n'
        '\n'
        '@pytest.fixture()\n'
        'def call_log():\n'
        '    """Collect the calls and yield the log."""\n'
        '    calls = []\n'
        '    return calls\n'
    )
    assert _fixture_yield_mismatches(source) == ['call_log']


def test_detector_accepts_a_genuine_yield_fixture():
    """A fixture that actually yields keeps its yield wording."""
    source = (
        'import pytest\n'
        '\n'
        '\n'
        '@pytest.fixture()\n'
        'def call_log():\n'
        '    """Collect the calls and yield the log."""\n'
        '    calls = []\n'
        '    yield calls\n'
    )
    assert _fixture_yield_mismatches(source) == []


def test_detector_accepts_return_wording_on_a_return_form_fixture():
    """A return-form fixture documented as returning is not reported."""
    source = (
        'import pytest\n'
        '\n'
        '\n'
        '@pytest.fixture()\n'
        'def isolated_root(tmp_path, monkeypatch):\n'
        '    """Point the base directory at an isolated tmp_path and return that root."""\n'
        '    monkeypatch.setenv("BASE_DIR", str(tmp_path))\n'
        '    return tmp_path\n'
    )
    assert _fixture_yield_mismatches(source) == []


def test_no_fixture_docstring_says_yield_without_yielding():
    """No fixture docstring says yield unless the fixture yields."""
    fixture_count = 0
    mismatches = []
    unreadable = []
    unparsable = []
    for path in sorted(TEST_ROOT.rglob('*.py')):
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            unreadable.append(str(path.relative_to(TEST_ROOT)))
            continue
        if 'fixture' not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            unparsable.append(str(path.relative_to(TEST_ROOT)))
            continue
        for node in _fixture_defs(tree):
            fixture_count += 1
            docstring = ast.get_docstring(node) or ''
            if 'yield' in docstring.lower() and not _body_yields(node):
                mismatches.append(f'{path.relative_to(TEST_ROOT)}::{node.name}')
    assert unreadable == [], f'fixture files that could not be read: {unreadable}'
    assert unparsable == [], f'fixture files that could not be parsed: {unparsable}'
    assert fixture_count > 0, 'expected the scan to select at least one fixture'
    assert mismatches == [], f'fixtures documented as yielding without yielding: {mismatches}'
