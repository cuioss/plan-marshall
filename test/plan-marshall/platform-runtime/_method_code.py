# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extract a shipped function or method's CODE, with its docstring removed.

A delegation guard asserts that a method no longer contains the logic it
delegated away. A whole-function text match cannot make that assertion: the
docstring of a delegating method normally QUOTES the retired logic to say what
the delegation replaced, so ``'isinstance(steps, list)' in body`` reads a
well-written explanation of the fix as the fix having been undone.

Prose about a behaviour and the behaviour are different evidence, and a guard
that cannot tell them apart either false-alarms on every good docstring or has
to give up on prose entirely. So the docstring is removed here, once, and the
guards assert over what is left. Comments go with it for the same reason: a
comment that names a retired guard is documentation, not a call to it.
"""

from __future__ import annotations

import ast
from pathlib import Path

from conftest import get_script_path


def method_code(bundle: str, skill: str, script: str, name: str) -> str:
    """Return the CODE of the named function/method, docstring and comments dropped.

    Args:
        bundle: Bundle name, e.g. ``'plan-marshall'``.
        skill: Skill name, e.g. ``'platform-runtime'``.
        script: Script filename under the skill's ``scripts/``.
        name: The ``def`` name to extract — a module-level function or a method,
            both addressed by their bare ``def`` name.

    Returns:
        The normalised code lines, whitespace-collapsed, joined by newlines.

    Raises:
        AssertionError: when the file has no top-level ``def`` with that name.
            Raised rather than returned as an empty string because an empty
            string would satisfy every "this text is absent" assertion in the
            caller — the guard would pass on a file that never contained the
            method at all, which is the same silent-green failure the guards
            exist to prevent.
    """
    path: Path = get_script_path(bundle, skill, script)
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()

    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    assert nodes, f'{script} declares no function or method named {name!r}'

    node = nodes[0]
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    body = lines[node.lineno - 1 : end]

    first = node.body[0] if node.body else None
    docstring_lines: set[int] = set()
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and first.end_lineno is not None
    ):
        docstring_lines = set(range(first.lineno - 1, first.end_lineno))

    kept: list[str] = []
    for offset, line in enumerate(body):
        if (node.lineno - 1 + offset) in docstring_lines:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        kept.append(' '.join(stripped.split()))
    return '\n'.join(kept)
