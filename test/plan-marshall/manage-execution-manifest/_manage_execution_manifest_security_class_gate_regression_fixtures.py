#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression coverage for the ``security_class_inactive`` pre-filter.

Every test here composes a REAL manifest through ``cmd_compose`` and asserts the
operator-visible outcome — what lands in ``phase_6.steps``, what the compose
result reports, what reaches ``decision.log`` — rather than the pre-filter
helper's return tuple. The unit-level truth table lives in
``test_decision_rules.py``; this module exists to pin the four behaviours the
incident turned on, at the boundary an operator actually observes.

**The incident.** ``finalize-step-security-audit`` was silently dropped from a
large multi-file code change. The old ``security_audit_inactive`` pre-filter
gated on ``change_type ∉ {feature, bug_fix, tech_debt, enhancement}``, and at the
time ``change_type`` reached the composer FIRST-DELIVERABLE-WINS from
``solution_outline.md`` deliverable metadata (since reconciled against the plan's
settled classification — see plan 350). A plan opening with a read-only discovery
deliverable therefore forwarded ``verification`` however much production code its
later deliverables mutated, and the proactive security sweep vanished. Nothing
user-visible said so: the drop was reported only into ``decision.log``, which no
phase reads back.

The fix removes the change-type leg entirely (the gate fails toward INCLUSION),
evaluates the remaining zero-surface leg against BOTH the declared and the live
change surface, derives the protected population from the frontmatter scalar
``persona: persona-security-expert`` instead of a hardcoded step id, and reports
every drop as a ``security_class_omitted`` ``{step, reason}`` record plus a
``[STATUS]`` decision-log line.

Each test's docstring records the failure it produced against pre-fix HEAD. Those
records are observed, not derived: the whole module was run against the pre-fix
production sources (the three ``manage-execution-manifest`` scripts reverted, the
tests left in place) and every test in it failed. The recorded message is the
first assertion or attribute lookup each test actually tripped on.
"""

import json
from argparse import Namespace

import pytest

from conftest import PlanContext, load_script_module

# =============================================================================
# Module loading (the script filename has hyphens, so it is loaded by identity)
# =============================================================================


_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_script_security_class_regression',
)

# ⛔ Vacuity guard — the vocabulary belongs to the loaded production module, so emptying
# it there collects zero cases at the parametrize below and still reports green.
assert _mem.VALID_CHANGE_TYPES, 'manage-execution-manifest.VALID_CHANGE_TYPES is empty'
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess wrappers. ``_emit_decision_log``
# is deliberately NOT silenced here — the capture fixture below replaces it, and
# the [STATUS] line it carries is itself under test.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_kept_unknown = lambda *a, **kw: None
_mem._log_scope_gated_finalize_subtraction = lambda *a, **kw: None
_mem._log_ceremony_finalize_selection = lambda *a, **kw: None
_mem._log_candidate_source = lambda *a, **kw: None
_mem._log_prefilter_omitted = lambda *a, **kw: None
_mem._log_execution_tier_routing = lambda *a, **kw: None
_mem._log_step_execution_tier_stamping = lambda *a, **kw: None

# The step under protection, and its structural peer that declares no persona.
_SECURITY_STEP = 'finalize-step-security-audit'
_PEER_STEP = 'finalize-step-simplify'

# A large multi-file change: the incident's shape. The exact count is not
# load-bearing — any non-zero declared surface keeps the step — but a realistic
# magnitude keeps the scenario recognisable.
_LARGE_FOOTPRINT = [f'marketplace/bundles/plan-marshall/skills/x/scripts/mod_{i}.py' for i in range(12)]


# =============================================================================
# Fixtures and helpers
# =============================================================================


# Seams these tests patch, as ``(module, attribute)`` pairs.
_PATCHED_SEAMS = (
    (_mem, '_resolve_footprint'),
    (_mem, '_emit_decision_log'),
    (_mem, '_read_frontmatter_scalar'),
)

_ABSENT = object()


@pytest.fixture(autouse=True)
def _restore_patched_seams():
    """Snapshot + restore every seam these tests patch so nothing leaks across tests.

    Snapshot and restore go through ``getattr``/``setattr`` with an ``_ABSENT``
    sentinel rather than direct attribute access, so a seam the module under test
    does not declare cannot raise at FIXTURE SETUP. That matters for a regression
    module: an attribute error here would abort every test before its own
    assertion ran, masking each test's real failure behind one collection-time
    error and making the pre-fix failure record unreadable.
    """
    import extension_base

    seams = (*_PATCHED_SEAMS, (extension_base, '_resolve_plan_footprint'))
    originals = [(mod, name, getattr(mod, name, _ABSENT)) for mod, name in seams]
    yield
    for mod, name, value in originals:
        if value is _ABSENT:
            if hasattr(mod, name):
                delattr(mod, name)
        else:
            setattr(mod, name, value)


def _stub_footprint(footprint: list[str] | None) -> None:
    """Pin both live-footprint seams to ``footprint``.

    The security-class pre-filter reads the manifest module's
    ``_resolve_footprint``; the pre-push-quality-gate pre-filter resolves through
    ``extension_base._resolve_plan_footprint``. Both are pinned so the injected
    state drives every activation decision deterministically.

    ``footprint`` carries the resolvers' three-state return verbatim: ``None``
    (unresolvable — no evidence), ``[]`` (resolvable and genuinely empty), or a
    non-empty path list. The gate treats the two falsy states DIFFERENTLY, so
    ``None`` must not be collapsed into ``[]`` on the way in.
    """
    import extension_base

    def _resolve(_plan_id):
        return None if footprint is None else list(footprint)

    _mem._resolve_footprint = _resolve
    extension_base._resolve_plan_footprint = _resolve


def _capture_decision_log() -> list[tuple[str, str]]:
    """Replace ``_emit_decision_log`` with a recorder and return its backing list."""
    captured: list[tuple[str, str]] = []
    _mem._emit_decision_log = lambda plan_id, message: captured.append((plan_id, message))
    return captured


def _seed_marshal(candidates: list[str]) -> None:
    """Write a marshal.json whose phase-6 steps map IS the candidate list.

    The composer treats a marshal.json ``steps`` map as the authoritative phase-6
    candidate list, so the map written here must carry the full candidate set (each
    key ownerless — these tests set no per-element ``lane`` override, leaving every
    ceremony gate at its ``auto`` default so the pre-filter's own behaviour is what
    the assertions observe).
    """
    from file_ops import get_marshal_path

    marshal = {
        'plan': {'phase-6-finalize': {'steps': dict.fromkeys(candidates)}},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))


def _compose_ns(
    plan_id: str,
    change_type: str = 'feature',
    affected_files_count: int = 12,
    phase_6_steps: list[str] | None = None,
) -> Namespace:
    steps = list(DEFAULT_PHASE_6_STEPS) if phase_6_steps is None else list(phase_6_steps)
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=affected_files_count,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=','.join(steps),
        commit_and_push=None,
    )


def _compose(plan_id: str, **kwargs) -> dict:
    """Seed marshal from the effective candidate list, compose, and assert success."""
    ns = _compose_ns(plan_id, **kwargs)
    _seed_marshal(ns.phase_6_steps.split(','))
    result: dict = cmd_compose(ns)
    assert result is not None, 'cmd_compose returned no result'
    assert result['status'] == 'success', result
    return result


def _composed_steps(plan_id: str) -> list[str]:
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest['phase_6']['steps'])
