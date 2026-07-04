#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process ``main()`` dispatcher tests for ``manage-solution-outline.py``.

The sibling ``test_manage_solution_outline.py`` exercises the ``cmd_*``
handlers directly and drives CLI plumbing through subprocess (``run_script``).
Subprocess runs do not count for coverage, so the ``main()`` argparse builder,
every ``set_defaults(func=...)`` route, the ``output_toon`` emission, and the
``get-module-context`` two-state ``--project-dir`` routing block were
uncovered.

These tests invoke ``main()`` in-process with a patched ``sys.argv`` so
coverage records the dispatcher, and assert the real CLI contract (routing,
TOON content, error discriminator, raw-content emission, exit code, and the
mutually-exclusive ``--plan-id``/``--project-dir`` rejection).
"""

from __future__ import annotations

import sys

import pytest
from toon_parser import parse_toon

from conftest import load_script_module

# Distinct sys.modules name so this load never clobbers the
# 'manage_solution_outline' module the sibling test files register.
_mod = load_script_module(
    'plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py', 'manage_solution_outline_maincli'
)

# Compact contract-compliant solution outline (one deliverable). Kept local so
# this file does not depend on a same-directory sibling test module import.
VALID_SOLUTION = """# Solution: Compact Example

compatibility: breaking

## Summary

A compact valid solution outline.

## Solution Metadata

- scope_estimate: surgical

## Overview

```
[A] -> [B]
```

## Deliverables

### 1. Build the thing

Implement the thing.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: python
- module: core
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/Foo.py` (write-new)

**Verification:**
- Command: `pytest`
- Criteria: tests pass

**Success Criteria:**
- The thing works
"""


def _run_main(monkeypatch, capsys, argv):
    """Drive ``main()`` with a patched argv and return (exit_code, stdout)."""
    monkeypatch.setattr(sys, 'argv', ['manage-solution-outline', *argv])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    code = exc.value.code if exc.value.code is not None else 0
    captured = capsys.readouterr()
    return code, captured.out


def _seed_outline(plan_context, plan_id, content=VALID_SOLUTION):
    """Write a solution_outline.md into the plan dir and return its path."""
    path = plan_context.plan_dir_for(plan_id) / 'solution_outline.md'
    path.write_text(content)
    return path


# =============================================================================
# main() dispatch — one path per verb
# =============================================================================


def test_main_resolve_path_routes(plan_context, monkeypatch, capsys):
    """``resolve-path`` routes to cmd_resolve_path and returns the target path."""
    code, out = _run_main(monkeypatch, capsys, ['resolve-path', '--plan-id', 'so-cli-resolve'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'solution_outline.md' in data['path']
    assert data['exists'] is False


def test_main_exists_routes(plan_context, monkeypatch, capsys):
    """``exists`` routes to cmd_exists and reflects on-disk presence."""
    _seed_outline(plan_context, 'so-cli-exists')
    code, out = _run_main(monkeypatch, capsys, ['exists', '--plan-id', 'so-cli-exists'])
    assert code == 0
    assert parse_toon(out)['exists'] is True


def test_main_validate_success(plan_context, monkeypatch, capsys):
    """``validate`` routes to cmd_validate and reports the deliverable count."""
    _seed_outline(plan_context, 'so-cli-validate')
    code, out = _run_main(monkeypatch, capsys, ['validate', '--plan-id', 'so-cli-validate'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['validation']['deliverable_count'] == 1


def test_main_validate_document_not_found(plan_context, monkeypatch, capsys):
    """``validate`` with no document on disk emits document_not_found."""
    code, out = _run_main(monkeypatch, capsys, ['validate', '--plan-id', 'so-cli-novalidate'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert data['error'] == 'document_not_found'


def test_main_list_deliverables_routes(plan_context, monkeypatch, capsys):
    """``list-deliverables`` routes to cmd_list_deliverables."""
    _seed_outline(plan_context, 'so-cli-deliv')
    code, out = _run_main(monkeypatch, capsys, ['list-deliverables', '--plan-id', 'so-cli-deliv'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['deliverable_count'] == 1


def test_main_read_raw_emits_markdown(plan_context, monkeypatch, capsys):
    """``read --raw`` prints the raw markdown body before the TOON result."""
    _seed_outline(plan_context, 'so-cli-rawread')
    code, out = _run_main(monkeypatch, capsys, ['read', '--plan-id', 'so-cli-rawread', '--raw'])
    assert code == 0
    assert '# Solution: Compact Example' in out
    assert '## Deliverables' in out


def test_main_read_section_routes(plan_context, monkeypatch, capsys):
    """``read --section summary`` returns the Summary body in the content field."""
    _seed_outline(plan_context, 'so-cli-section')
    code, out = _run_main(monkeypatch, capsys, ['read', '--plan-id', 'so-cli-section', '--section', 'summary'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['section'] == 'summary'


def test_main_write_validates_on_disk(plan_context, monkeypatch, capsys):
    """``write`` validates the on-disk document and stamps action=created."""
    _seed_outline(plan_context, 'so-cli-write')
    code, out = _run_main(monkeypatch, capsys, ['write', '--plan-id', 'so-cli-write'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['action'] == 'created'


def test_main_update_validates_on_disk(plan_context, monkeypatch, capsys):
    """``update`` validates the on-disk document and stamps action=updated."""
    _seed_outline(plan_context, 'so-cli-update')
    code, out = _run_main(monkeypatch, capsys, ['update', '--plan-id', 'so-cli-update'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['action'] == 'updated'


def test_main_get_field_scope_estimate(plan_context, monkeypatch, capsys):
    """``get-field --field scope_estimate`` returns the persisted value."""
    _seed_outline(plan_context, 'so-cli-getfield')
    code, out = _run_main(
        monkeypatch, capsys, ['get-field', '--plan-id', 'so-cli-getfield', '--field', 'scope_estimate']
    )
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['value'] == 'surgical'


# =============================================================================
# get-module-context — two-state --project-dir routing block
# =============================================================================


def test_main_get_module_context_not_found(plan_context, monkeypatch, capsys, tmp_path):
    """``get-module-context --project-dir <empty>`` resolves the dir then returns not_found.

    Exercises the ``hasattr(args, 'project_dir')`` routing branch in main() and
    the absent-``_project.json`` path in cmd_get_module_context.
    """
    code, out = _run_main(monkeypatch, capsys, ['get-module-context', '--project-dir', str(tmp_path)])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'not_found'


def test_main_get_module_context_plan_id_and_project_dir_mutually_exclusive(
    plan_context, monkeypatch, capsys, tmp_path
):
    """Passing both --plan-id and an explicit --project-dir is rejected with exit 2."""
    code, out = _run_main(
        monkeypatch,
        capsys,
        ['get-module-context', '--plan-id', 'so-cli-mutex', '--project-dir', str(tmp_path)],
    )
    assert code == 2
    data = parse_toon(out)
    assert data['status'] == 'error'


# =============================================================================
# Argparse boundary
# =============================================================================


def test_main_missing_subcommand_exits_2(plan_context, monkeypatch, capsys):
    """No subcommand → argparse required-subparser error exits 2."""
    code, _ = _run_main(monkeypatch, capsys, [])
    assert code == 2
