#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the compose-time canonical-step-key structural guard.

The guard (``_manifest_validation.check_emitted_steps_canonical``, wired into
``cmd_compose`` right after the resolution gate) fails a compose loud when any
FINAL emitted phase-5/6 step id is not in canonical form
(``canonicalize_step_key(step_id) != step_id`` — a leftover ``default:`` prefix or
a promoted-alias bundle spelling). It is the structural sibling of the
``unresolvable_step`` gate and never writes a partial manifest.

Two layers of coverage:

- unit: ``check_emitted_steps_canonical`` returns the first offender (or ``None``);
- end-to-end: a compose whose intake boundary-normalization is defeated (so a
  ``default:``-prefixed id survives into the final list) is rejected with
  ``non_canonical_step`` and writes no manifest; a canonical-form compose is clean.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_canon_gate', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
get_manifest_path = _mem.get_manifest_path
check_emitted_steps_canonical = _mem.check_emitted_steps_canonical
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence best-effort decision-log writes.
_mem._log_decision = lambda *a, **kw: None
_mem._log_execution_tier_routing = lambda *a, **kw: None
_mem._log_candidate_source = lambda *a, **kw: None


def _compose_ns(
    plan_id: str = 'canon-gate',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'verify:quality-gate,verify:module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


# =============================================================================
# Unit: check_emitted_steps_canonical
# =============================================================================


def test_canonical_lists_return_none():
    """All-canonical phase-5/6 lists produce no offender."""
    assert (
        check_emitted_steps_canonical(
            ['verify:quality-gate', 'verify:module-tests'],
            ['push', 'create-pr', 'archive-plan'],
        )
        is None
    )


def test_default_prefixed_phase_6_step_is_flagged():
    """A ``default:``-prefixed phase-6 id is the first offender."""
    offender = check_emitted_steps_canonical(['verify:quality-gate'], ['push', 'default:create-pr'])
    assert offender is not None
    assert offender['phase'] == 'phase_6'
    assert offender['step_id'] == 'default:create-pr'
    assert offender['canonical'] == 'create-pr'
    assert 'not in canonical form' in offender['message']


def test_default_prefixed_phase_5_step_is_flagged_first():
    """A non-canonical phase-5 id is reported before any phase-6 id (list order)."""
    offender = check_emitted_steps_canonical(['default:verify:coverage'], ['default:push'])
    assert offender is not None
    assert offender['phase'] == 'phase_5'
    assert offender['step_id'] == 'default:verify:coverage'
    assert offender['canonical'] == 'verify:coverage'


def test_promoted_alias_spelling_is_flagged():
    """A promoted-alias bundle spelling is non-canonical (it canonicalizes to bare)."""
    offender = check_emitted_steps_canonical([], ['plan-marshall:automatic-review'])
    assert offender is not None
    assert offender['step_id'] == 'plan-marshall:automatic-review'
    assert offender['canonical'] == 'automatic-review'


def test_non_string_entries_are_skipped():
    """Non-string entries never trip the guard (they are not step ids)."""
    assert check_emitted_steps_canonical([None, 123], ['push']) is None


# =============================================================================
# End-to-end: compose rejects a non-canonical emitted id, writes no manifest
# =============================================================================


def test_compose_rejects_non_canonical_emitted_step(plan_context, monkeypatch):
    """When the intake boundary-normalization is defeated so a ``default:``-prefixed
    id survives into the final phase-6 list, compose fails ``non_canonical_step``
    and writes NO manifest."""
    plan_id = 'canon-gate-reject'
    # Defeat the compose-side intake normalization ONLY (the validation helper
    # imports its own canonicalize_step_key in _manifest_validation, unaffected by
    # this patch), so a default:-prefixed candidate survives to the final list and
    # the structural guard catches it.
    monkeypatch.setattr(_mem, 'canonicalize_step_key', lambda step: step)

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            phase_6_steps='default:push,archive-plan',
        )
    )

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'non_canonical_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'default:push'
    assert result['canonical'] == 'push'
    # No partial manifest written — the gate returns before write_manifest.
    assert not get_manifest_path(plan_id).exists()
    assert read_manifest(plan_id) is None


def test_compose_canonical_step_list_composes_cleanly(plan_context):
    """A canonical-form step list composes successfully (no false positive)."""
    plan_id = 'canon-gate-clean'
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            phase_6_steps='push,create-pr,lessons-capture,archive-plan',
        )
    )

    assert result is not None
    assert result['status'] == 'success'
    assert result.get('error') != 'non_canonical_step'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    # Every emitted step is canonical (no default: prefix survived).
    assert not any(s.startswith('default:') for s in manifest['phase_6']['steps'])
    assert not any(s.startswith('default:') for s in manifest['phase_5']['verification_steps'])
