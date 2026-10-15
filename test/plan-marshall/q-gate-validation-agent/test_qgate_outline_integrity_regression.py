#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression coverage for outline Q-Gate integrity.

Exercises the deliverable-1 fix from a user-visible angle — the three defects
this plan repairs, each asserted so it FAILS on the pre-fix tree and PASSES on
the fixed tree:

1. **Empty assessment store yields not_run, not per-file fail** — the
   assessment-coverage check (§2.2) and the missing-coverage check (Step 5)
   document the not-run branch, and the Output block carries the
   ``not_run_validators`` return field. A pre-fix tree flags every deliverable
   and carries no such field.
2. **Phase-keyed whole-outline skip runs the correct phase validators** — the
   aggregate hash row is keyed ``__whole_outline__:{phase}`` in both the writer
   (q-gate-validation Step 3.5) and the reader (planning-outline.md), and the
   deterministic ``deliverable-hashes`` verb backs the skip. Functionally, the
   verb returns identical content hashes under either phase while echoing the
   requested phase, so a 4-plan first pass after a 3-outline pass finds no
   stored row for its own phase and runs every 4-plan validator.
3. **domain-narrow would_empty leaves domains unwritten** — narrowing that
   would retain no user domain returns ``would_empty`` and writes nothing, even
   under ``--apply``. A pre-fix tree either returns success with an empty
   retained set or has no such guard at all.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import cast

import pytest
from _manage_config_fixtures import create_marshal_json

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

_BUNDLE = 'plan-marshall'
_CONFIG_SKILL = 'manage-config'
_CONFIG_SCRIPT = 'manage-config.py'
_OUTLINE_SKILL = 'manage-solution-outline'
_OUTLINE_SCRIPT = 'manage-solution-outline.py'

_narrow_mod = load_script_module(
    _BUNDLE, _CONFIG_SKILL, '_cmd_domain_narrow.py', module_name='_cmd_domain_narrow_regression'
)
cmd_domain_narrow = _narrow_mod.cmd_domain_narrow

_outline_mod = load_script_module(
    _BUNDLE, _OUTLINE_SKILL, _OUTLINE_SCRIPT, module_name='manage_solution_outline_regression'
)

_QGATE_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'q-gate-validation.md'
_PLANNING_OUTLINE_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'planning-outline.md'
)

_DOMAINS_CONFIG = {
    'skill_domains': {
        'system': {'defaults': []},
        'documentation': {'bundle': 'pm-documents'},
    }
}

_VALID_OUTLINE = """# Solution: Regression Example

compatibility: breaking

## Summary

A minimal outline for the regression.

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


def _seed_outline(plan_context, plan_id: str) -> None:
    """Write a minimal solution outline into the plan dir."""
    path = cast(Path, plan_context.plan_dir_for(plan_id) / 'solution_outline.md')
    path.write_text(_VALID_OUTLINE)


def _seed_domains(plan_context, plan_id: str) -> Path:
    """Seed marshal.json plus a references.json holding a single droppable domain."""
    plan_dir = cast(Path, plan_context.fixture_dir / 'plans' / plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    create_marshal_json(plan_context.fixture_dir, _DOMAINS_CONFIG)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'domains': ['documentation']}), encoding='utf-8'
    )
    return plan_dir


def _ns(plan_id: str, *extra: str) -> Namespace:
    """Args for ``manage-config domain-narrow`` built by the script's own parser."""
    return cast(
        Namespace,
        parse_ns(_BUNDLE, _CONFIG_SKILL, _CONFIG_SCRIPT, 'domain-narrow', '--plan-id', plan_id, *extra),
    )


# -----------------------------------------------------------------------------
# Defect 1 — empty assessment store yields not_run, not per-file fail.
# -----------------------------------------------------------------------------


def test_empty_store_reports_not_run_with_validators_field() -> None:
    """The workflow documents the not-run branch and its return field."""
    text = _QGATE_DOC.read_text(encoding='utf-8')
    assert 'not run' in text
    assert 'not_run_validators' in text


def test_missing_coverage_step_documents_the_not_run_branch() -> None:
    """Step 5 shares the not-run outcome instead of flagging missing coverage."""
    text = _QGATE_DOC.read_text(encoding='utf-8')
    step_5 = text.index('### Step 5')
    step_6 = text.index('### Step 6')
    assert 'not run' in text[step_5:step_6]


# -----------------------------------------------------------------------------
# Defect 2 — phase-keyed whole-outline skip runs the correct phase validators.
# -----------------------------------------------------------------------------


def test_aggregate_row_is_keyed_by_phase_in_writer_and_reader() -> None:
    """Writer and reader agree on the phase-suffixed aggregate row key."""
    assert '__whole_outline__:{phase}' in _QGATE_DOC.read_text(encoding='utf-8')
    assert '__whole_outline__:{phase}' in _PLANNING_OUTLINE_DOC.read_text(encoding='utf-8')


def test_hash_verb_is_phase_stable_but_phase_echoing(plan_context) -> None:
    """Same content hashes under either phase; the phase echo differs.

    Stability is what makes the skip deterministic; the differing echo is what
    the caller stores the aggregate row under, so a 4-plan pass never matches a
    3-outline row.
    """
    _seed_outline(plan_context, 'qir-phase-key')
    plan_id = 'qir-phase-key'
    first = _outline_mod.cmd_deliverable_hashes(_outline_ns(plan_id, '3-outline'))
    second = _outline_mod.cmd_deliverable_hashes(_outline_ns(plan_id, '4-plan'))
    assert first['status'] == 'success'
    assert second['status'] == 'success'
    assert first['hashes'] == second['hashes']
    assert first['whole_outline_hash'] == second['whole_outline_hash']
    assert first['phase'] == '3-outline'
    assert second['phase'] == '4-plan'


def _outline_ns(plan_id: str, phase: str) -> Namespace:
    """Args for ``manage-solution-outline deliverable-hashes``."""
    ns = Namespace()
    ns.plan_id = plan_id
    ns.phase = phase
    return cast(Namespace, ns)


# -----------------------------------------------------------------------------
# Defect 3 — domain-narrow would_empty leaves domains unwritten.
# -----------------------------------------------------------------------------


def test_would_empty_reports_and_writes_nothing(plan_context) -> None:
    """Narrowing to no user domain refuses, even under --apply."""
    plan_dir = _seed_domains(plan_context, 'qir-would-empty')
    before = (plan_dir / 'references.json').read_bytes()

    result = cmd_domain_narrow(_ns('qir-would-empty', '--affected-files', 'src/main/Foo.py', '--apply'))

    assert result['status'] == 'error'
    assert result['error'] == 'would_empty'
    assert (plan_dir / 'references.json').read_bytes() == before


def test_deliverable_leg_retains_a_declared_domain(plan_context) -> None:
    """A deliverable-declared domain survives a footprint no other leg claims."""
    plan_dir = cast(Path, plan_context.fixture_dir / 'plans' / 'qir-deliverable-leg')
    plan_dir.mkdir(parents=True, exist_ok=True)
    create_marshal_json(plan_context.fixture_dir, _DOMAINS_CONFIG)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'domains': ['documentation']}), encoding='utf-8'
    )
    (plan_dir / 'solution_outline.md').write_text(
        _VALID_OUTLINE.replace('- domain: python', '- domain: documentation'), encoding='utf-8'
    )

    result = cmd_domain_narrow(_ns('qir-deliverable-leg', '--affected-files', 'src/main/Foo.py'))

    assert result['status'] == 'success'
    assert 'documentation' in result['retained']


def test_main_routes_deliverable_hashes(monkeypatch) -> None:
    """The deliverable-hashes verb is reachable through main() dispatch."""
    received: list = []

    def _recording_handler(args):
        received.append(args)
        return {'status': 'success'}

    monkeypatch.setattr(_outline_mod, 'cmd_deliverable_hashes', _recording_handler)
    monkeypatch.setattr(
        sys,
        'argv',
        ['manage-solution-outline.py', 'deliverable-hashes', '--plan-id', 'qir-dispatch', '--phase', '4-plan'],
    )
    with pytest.raises(SystemExit) as exit_info:
        _outline_mod.main()

    assert exit_info.value.code == 0
    assert len(received) == 1
    assert received[0].phase == '4-plan'
