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

import re
import sys

import pytest
from _resolve_project_dir_fixtures import (
    assert_sentinel_accepted,
    assert_worktree_face_routes_through_resolver,
)
from toon_parser import parse_toon, serialize_toon

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

# Two-deliverable outline for the phase-keyed artifact tests: editing ONE
# deliverable must leave the other deliverable's row and skip decision intact.
TWO_DELIVERABLE_SOLUTION = """# Solution: Two Deliverables

compatibility: breaking

## Summary

A two-deliverable outline for the phase-keyed hash skip.

## Solution Metadata

- scope_estimate: surgical

## Overview

```
[A] -> [B]
```

## Deliverables

### 1. Build the first thing

Implement the first thing.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: python
- module: core
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/First.py` (write-new)

**Verification:**
- Command: `pytest`
- Criteria: tests pass

**Success Criteria:**
- The first thing works

### 2. Build the second thing

Implement the second thing.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: python
- module: core
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/Second.py` (write-new)

**Verification:**
- Command: `pytest`
- Criteria: tests pass

**Success Criteria:**
- The second thing works
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


# =============================================================================
# Resolver-migration contract
# =============================================================================
#
# ``get-module-context`` is this CLI's working-tree-binding verb. Its worktree
# face must come from the ONE resolver rather than a private re-derivation, and
# the ``NO_PLAN`` sentinel must be accepted so a genuinely plan-less caller
# resolves against the main checkout.


def _resolve_project_dir_via_cli(plan_id):
    """Resolve exactly as ``main`` does, through the CLI's own imported symbol."""
    return _mod._routing.resolve_project_dir(plan_id, '.', default='.')


def test_worktree_binding_routes_through_the_resolver():
    """The worktree face reaches the single ``get-worktree-path`` seam."""
    assert_worktree_face_routes_through_resolver(_resolve_project_dir_via_cli)


def test_no_plan_sentinel_is_accepted():
    """``NO_PLAN`` resolves to the main checkout without shelling out."""
    assert_sentinel_accepted(_resolve_project_dir_via_cli)


def test_get_module_context_accepts_the_no_plan_sentinel(plan_context, monkeypatch, capsys, tmp_path):
    """``get-module-context --plan-id NO_PLAN`` routes without a resolution error.

    End-to-end through ``main``: the sentinel must reach the command handler and
    produce the handler's own verdict (``not_found`` for a checkout with no
    architecture data), never a ``worktree_resolution_failed`` envelope.
    """
    monkeypatch.chdir(tmp_path)
    code, out = _run_main(monkeypatch, capsys, ['get-module-context', '--plan-id', 'NO_PLAN'])
    data = parse_toon(out)
    assert data.get('error') != 'worktree_resolution_failed', (
        f'the NO_PLAN sentinel was rejected by worktree resolution: {data!r}'
    )
    assert code in (0, 1), f'unexpected exit code {code} for the sentinel path: {data!r}'


# =============================================================================
# deliverable-hashes — deterministic per-deliverable content hashes
# =============================================================================
#
# The verb reuses _plan_parsing as its read-only shared helper: the deliverable
# population comes from the parser's own block split, so the hashed set cannot
# drift from the listed set. q-gate-validation Step 3.5 calls it for its
# phase-keyed whole-outline skip.


def test_main_deliverable_hashes_routes(plan_context, monkeypatch, capsys):
    """``deliverable-hashes`` routes and returns one hash per deliverable."""
    _seed_outline(plan_context, 'so-cli-hashes')
    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-hashes'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['deliverable_count'] == 1
    assert len(data['hashes']) == 1
    assert data['hashes'][0]['deliverable'] == '1'
    assert re.fullmatch(r'[0-9a-f]{64}', data['hashes'][0]['hash']) is not None
    assert re.fullmatch(r'[0-9a-f]{64}', data['whole_outline_hash']) is not None


def test_main_deliverable_hashes_is_deterministic(plan_context, monkeypatch, capsys):
    """Two runs over unchanged content return byte-identical digests."""
    _seed_outline(plan_context, 'so-cli-hashes-determinism')
    _, first = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-hashes-determinism'])
    _, second = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-hashes-determinism'])
    assert parse_toon(first)['hashes'] == parse_toon(second)['hashes']
    assert parse_toon(first)['whole_outline_hash'] == parse_toon(second)['whole_outline_hash']


def test_main_deliverable_hashes_changes_with_content(plan_context, monkeypatch, capsys):
    """An edited deliverable block changes its digest — the skip predicate's signal."""
    path = _seed_outline(plan_context, 'so-cli-hashes-change')
    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-hashes-change'])
    assert code == 0
    before = parse_toon(out)['hashes'][0]['hash']
    path.write_text(path.read_text().replace('Implement the thing.', 'Implement the other thing.'))
    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-hashes-change'])
    assert code == 0
    assert parse_toon(out)['hashes'][0]['hash'] != before


def test_main_deliverable_hashes_echoes_phase(plan_context, monkeypatch, capsys):
    """The default mode echoes ``--phase`` back to the caller."""
    _seed_outline(plan_context, 'so-cli-hashes-phase')
    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-hashes-phase', '--phase', '4-plan']
    )
    assert code == 0
    assert parse_toon(out)['phase'] == '4-plan'


def test_main_deliverable_hashes_document_not_found(plan_context, monkeypatch, capsys):
    """``deliverable-hashes`` with no document on disk emits document_not_found."""
    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-nohashes'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert data['error'] == 'document_not_found'


def test_main_deliverable_hashes_document_unreadable(plan_context, monkeypatch, capsys):
    """``deliverable-hashes`` over undecodable bytes emits document_unreadable, not an exception."""
    path = _seed_outline(plan_context, 'so-cli-badhashes')
    path.write_bytes(b'\xff\xfe\x00not-utf8')
    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', 'so-cli-badhashes'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert data['error'] == 'document_unreadable'


# =============================================================================
# deliverable-hashes — the phase-keyed artifact: --write / --check
# =============================================================================
#
# The verb owns work/deliverable-hashes.toon: --write persists the phase-keyed
# rows (one per deliverable plus the __whole_outline__:{phase} aggregate), and
# --check reads them back into per-row skip/run decisions applying the
# same-phase rule. These tests encode the completion plan's Done-when clauses:
# an edit changes exactly one row plus the aggregate; a 3-outline artifact
# makes a 4-plan check run every row; a same-phase unchanged check skips (with
# the cached-skip note); and --write writes the artifact --check reads.


def test_main_deliverable_hashes_write_then_edit_changes_exactly_one_row_and_the_aggregate(
    plan_context, monkeypatch, capsys
):
    """Editing one of two deliverables changes exactly that row and the aggregate."""
    plan_id = 'so-cli-hashes-edit-one'
    path = _seed_outline(plan_context, plan_id, TWO_DELIVERABLE_SOLUTION)

    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--phase', '3-outline', '--write']
    )
    assert code == 0
    assert parse_toon(out)['status'] == 'success'

    _, before = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id])
    path.write_text(path.read_text().replace('Implement the second thing.', 'Implement the edited second thing.'))
    _, after = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id])

    rows_before = {row['deliverable']: row['hash'] for row in parse_toon(before)['hashes']}
    rows_after = {row['deliverable']: row['hash'] for row in parse_toon(after)['hashes']}
    assert rows_before['1'] == rows_after['1']
    assert rows_before['2'] != rows_after['2']
    assert parse_toon(before)['whole_outline_hash'] != parse_toon(after)['whole_outline_hash']

    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--phase', '3-outline', '--check']
    )
    assert code == 0
    data = parse_toon(out)
    assert {row['deliverable']: row['decision'] for row in data['deliverables']} == {'1': 'skip', '2': 'run'}
    assert data['whole_outline_decision'] == 'run'


def test_main_deliverable_hashes_check_cross_phase_returns_run_for_every_row(plan_context, monkeypatch, capsys):
    """A 3-outline artifact makes a 4-plan check return run for every row.

    Rows recorded under another phase's key never satisfy this phase's lookup,
    so the first 4-plan pass over a 3-outline artifact fully re-validates.
    """
    plan_id = 'so-cli-hashes-cross-phase'
    _seed_outline(plan_context, plan_id, TWO_DELIVERABLE_SOLUTION)

    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--phase', '3-outline', '--write']
    )
    assert code == 0

    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--phase', '4-plan', '--check']
    )
    assert code == 0
    data = parse_toon(out)
    assert data['artifact'] == 'present'
    assert {row['decision'] for row in data['deliverables']} == {'run'}
    assert data['whole_outline_decision'] == 'run'


def test_main_deliverable_hashes_check_same_phase_unchanged_returns_skip(plan_context, monkeypatch, capsys):
    """A same-phase check over an unchanged outline and inputs returns skip."""
    plan_id = 'so-cli-hashes-same-phase'
    _seed_outline(plan_context, plan_id, TWO_DELIVERABLE_SOLUTION)

    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--write'])
    assert code == 0

    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--check'])
    assert code == 0
    data = parse_toon(out)
    assert [row['decision'] for row in data['deliverables']] == ['skip', 'skip']
    assert data['deliverables'][0]['note'] == 'not run (cached from phase 3-outline)'
    assert data['whole_outline_decision'] == 'skip'
    assert data['validator_inputs_unchanged'] is True


def test_main_deliverable_hashes_write_persists_the_artifact_check_reads(plan_context, monkeypatch, capsys):
    """``--write`` persists the artifact whose rows ``--check`` consumes."""
    plan_id = 'so-cli-hashes-write-artifact'
    _seed_outline(plan_context, plan_id, TWO_DELIVERABLE_SOLUTION)

    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--phase', '3-outline', '--write']
    )
    assert code == 0

    artifact_path = plan_context.plan_dir_for(plan_id) / 'work' / 'deliverable-hashes.toon'
    assert artifact_path.exists()
    artifact = parse_toon(artifact_path.read_text(encoding='utf-8'))
    keys = [row['deliverable'] for row in artifact['hashes']]
    assert set(keys) == {'3-outline:1', '3-outline:2', '__whole_outline__:3-outline'}

    code, out = _run_main(
        monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--phase', '3-outline', '--check']
    )
    assert code == 0
    assert {row['decision'] for row in parse_toon(out)['deliverables']} == {'skip'}


def test_main_deliverable_hashes_hashless_aggregate_row_never_allows_a_skip(plan_context, monkeypatch, capsys):
    """A present-but-hashless aggregate row is no completed-pass record.

    The artifact reader does not validate row shape, so a row can survive with a
    missing or empty ``hash``. Presence alone must not stand in for the phase's
    full-pass marker: with the aggregate hash blanked, every per-deliverable
    decision must read ``run`` (and the whole-outline gate ``run``), never a skip
    a malformed record earned.
    """
    plan_id = 'so-cli-hashes-hashless-aggregate'
    _seed_outline(plan_context, plan_id, TWO_DELIVERABLE_SOLUTION)

    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--write'])
    assert code == 0
    assert parse_toon(out)['status'] == 'success'

    artifact_path = plan_context.plan_dir_for(plan_id) / 'work' / 'deliverable-hashes.toon'
    artifact = parse_toon(artifact_path.read_text(encoding='utf-8'))
    for row in artifact['hashes']:
        if row['deliverable'] == '__whole_outline__:3-outline':
            row['hash'] = ''
    artifact_path.write_text(serialize_toon(artifact), encoding='utf-8')

    code, out = _run_main(monkeypatch, capsys, ['deliverable-hashes', '--plan-id', plan_id, '--check'])
    assert code == 0
    data = parse_toon(out)
    assert data['artifact'] == 'present'
    # The inputs are unchanged, so the blanked aggregate is the ONLY reason the
    # skip predicate may not fire — which keeps this test non-vacuous.
    assert data['validator_inputs_unchanged'] is True
    assert {row['decision'] for row in data['deliverables']} == {'run'}
    assert data['whole_outline_decision'] == 'run'
