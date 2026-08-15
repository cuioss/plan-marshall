#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Workflow-lint guard (D9): assert the D1 env-passing form and the D2 permissions block.

Two structural invariants over ``.github/workflows/*.yml``, asserted here so they
cannot silently regress on review alone — this is the guard that stops the D1 and
D2 fixes from quietly returning:

- **D1 — no context interpolation in a shell.** No GitHub Actions context
  expression (``${{ ... }}``) may appear inside a ``run:`` block. A context value
  spliced into a shell is a template-injection surface (a ref name can carry shell
  metacharacters); the safe form passes the value through ``env:`` and references
  it as a quoted shell variable. This is the regression guard for the
  ``claude-distribute.yml`` fix.
- **D2 — no implicit token scope.** Every workflow declares a top-level
  ``permissions:`` block, so no job silently inherits the repository/organisation
  default ``GITHUB_TOKEN`` scope.

The linter is text-based on purpose: PyYAML is not in the project's locked dev
environment (``uv.lock`` carries no PyYAML), so the sibling structural guards in
``test/plan-marshall/manage-config/`` already parse these files without it. This
guard does the same, so it runs identically on a developer machine and in CI.
"""

import re
from pathlib import Path

# repo_root/test/default/test_workflow_lint.py -> parents[2] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO_ROOT / '.github' / 'workflows'

# A GitHub Actions context expression opener. Its presence inside a run: body is
# the violation; the safe env-passing form keeps it on an env: line instead.
_CONTEXT_EXPR = re.compile(r'\$\{\{')
# A ``run:`` mapping key, with or without the ``- `` step-list dash on the same line.
_RUN_LINE = re.compile(r'^(?P<lead>\s*)(?P<dash>- )?run:(?P<after>.*)$')
_EXPR_LABEL = '${{ ... }}'


def _run_block_context_violations(text: str) -> list[str]:
    """Return one message per ``run:`` block that carries a context expression.

    Handles both the inline ``run: cmd`` form and the block-scalar ``run: |`` /
    ``run: >`` form. A block-scalar body is every following line that is blank or
    indented more deeply than the column at which ``run`` begins, up to the first
    line that dedents to or past it.
    """
    lines = text.splitlines()
    violations: list[str] = []
    i = 0
    while i < len(lines):
        match = _RUN_LINE.match(lines[i])
        if match is None:
            i += 1
            continue
        key_col = len(match.group('lead')) + (2 if match.group('dash') else 0)
        after = match.group('after').strip()
        line_no = i + 1
        is_block = after == '' or after.startswith('|') or after.startswith('>')
        if is_block:
            body: list[str] = []
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                if candidate.strip() == '':
                    body.append(candidate)
                    j += 1
                    continue
                indent = len(candidate) - len(candidate.lstrip())
                if indent > key_col:
                    body.append(candidate)
                    j += 1
                    continue
                break
            if any(_CONTEXT_EXPR.search(line) for line in body):
                violations.append(
                    f'run: block starting at line {line_no} contains a {_EXPR_LABEL} '
                    'context expression; pass the value via env: and reference it as a '
                    'quoted shell variable instead.'
                )
            i = j
            continue
        if _CONTEXT_EXPR.search(after):
            violations.append(
                f'run: at line {line_no} contains a {_EXPR_LABEL} context expression; '
                'pass the value via env: and reference it as a quoted shell variable instead.'
            )
        i += 1
    return violations


def _has_top_level_permissions(text: str) -> bool:
    """True when the workflow declares a top-level (column-0) ``permissions:`` key."""
    return any(line.startswith('permissions:') for line in text.splitlines())


def _workflow_files() -> list[Path]:
    return sorted(_WORKFLOWS_DIR.glob('*.yml')) + sorted(_WORKFLOWS_DIR.glob('*.yaml'))


# --- guards over the real .github/workflows/ tree -------------------------------


def test_workflows_have_no_context_expression_in_run_blocks() -> None:
    """D1: no workflow interpolates a context expression inside a run: block."""
    offenders: dict[str, list[str]] = {}
    for workflow in _workflow_files():
        found = _run_block_context_violations(workflow.read_text(encoding='utf-8'))
        if found:
            offenders[workflow.name] = found

    assert not offenders, (
        'A GitHub Actions context expression (${{ ... }}) appears inside a run: '
        'block — a template-injection surface, since a context value (e.g. a ref '
        'name) can carry shell metacharacters. Pass the value via env: and '
        f'reference it as a quoted shell variable.\n{offenders}'
    )


def test_workflows_declare_top_level_permissions() -> None:
    """D2: every workflow declares a top-level permissions: block."""
    missing = [
        workflow.name
        for workflow in _workflow_files()
        if not _has_top_level_permissions(workflow.read_text(encoding='utf-8'))
    ]

    assert not missing, (
        'Workflow(s) without a top-level permissions: block inherit the '
        'repository/organisation default GITHUB_TOKEN scope. Declare an explicit '
        f'least-privilege permissions: block.\n  missing: {missing}'
    )


def test_workflow_tree_is_non_empty() -> None:
    """Guard the guard: a mislocated workflows dir must not make the checks vacuous."""
    assert _workflow_files(), (
        f'no workflow files found under {_WORKFLOWS_DIR}; the D1/D2 guards would '
        'pass vacuously'
    )


# --- linter behaviour: it must FAIL a bad workflow and PASS the fixed form (D9) --

_BAD_INJECTION_WF = """\
name: Bad
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Create tag
        run: |
          git tag -a "${{ github.ref_name }}" -m "release"
"""

_GOOD_ENV_WF = """\
name: Good
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Create tag
        env:
          REF_NAME: ${{ github.ref_name }}
        run: |
          git tag -a "${REF_NAME}" -m "release"
"""

_NO_PERMISSIONS_WF = """\
name: NoPerms
on:
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


def test_linter_flags_interpolation_in_run_block() -> None:
    """The linter must FAIL a run: block that interpolates a context expression."""
    assert _run_block_context_violations(_BAD_INJECTION_WF), (
        'linter did not flag a ${{ github.ref_name }} interpolation inside a run: block'
    )


def test_linter_passes_env_passed_form() -> None:
    """The linter must PASS the env-passing form the D1 fix uses.

    The ``env:`` line legitimately carries the context expression; it must not be
    mistaken for a run-block interpolation.
    """
    assert _run_block_context_violations(_GOOD_ENV_WF) == []


def test_linter_flags_inline_run_interpolation() -> None:
    """The linter must also catch the inline ``run: cmd`` form, not only block scalars."""
    inline = (
        'jobs:\n  j:\n    steps:\n'
        '      - run: echo "${{ github.event.issue.title }}"\n'
    )
    assert _run_block_context_violations(inline)


def test_linter_flags_missing_top_level_permissions() -> None:
    """The permissions guard must FAIL a workflow with no top-level permissions:."""
    assert not _has_top_level_permissions(_NO_PERMISSIONS_WF)


def test_linter_passes_declared_permissions() -> None:
    """The permissions guard must PASS a workflow that declares permissions:."""
    assert _has_top_level_permissions(_GOOD_ENV_WF)
