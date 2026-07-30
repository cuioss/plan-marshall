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
gated on ``change_type ∉ {feature, bug_fix, tech_debt, enhancement}``, and
``change_type`` reaches the composer from ``solution_outline.md`` deliverable
metadata — FIRST DELIVERABLE WINS (``phase-4-plan/SKILL.md`` § Step 7b Inputs).
A plan opening with a read-only discovery deliverable therefore forwards
``verification`` however much production code its later deliverables mutate, and
the proactive security sweep vanished. Nothing user-visible said so: the drop was
reported only into ``decision.log``, which no phase reads back.

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

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext  # noqa: F401  (re-exported for fixture discovery)

# =============================================================================
# Module loading (script has hyphens in filename → load via importlib)
# =============================================================================

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


_mem = _load_module('_mem_script_security_class_regression', 'manage-execution-manifest.py')
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


# =============================================================================
# (a) A large multi-file change with an excluded change_type keeps the sweep
# =============================================================================


@pytest.mark.parametrize('change_type', sorted(_mem.VALID_CHANGE_TYPES))
def test_large_change_keeps_security_audit_for_every_change_type(plan_context, change_type):
    """The incident, reproduced: a 12-file change keeps the sweep whatever its change_type.

    The parametrization sweeps the WHOLE ``VALID_CHANGE_TYPES`` vocabulary rather
    than sampling ``analysis`` / ``verification`` — the two values the incident
    happened to involve. ``cmd_compose`` rejects anything outside that enum before
    the pre-filter runs, so the enum IS the reachable population, and a change type
    added later is covered the moment it joins it.

    Pre-fix failure (observed against pre-fix HEAD, all six parameters):
    ``KeyError: 'security_class_omitted'`` — the pre-fix compose result carried a
    bare ``security_audit_omitted`` boolean instead. That assertion is reached
    first, so it masks the second defect, which is present for ``analysis`` and
    ``verification``: those two are outside ``_SIMPLIFY_CHANGE_TYPES``, so
    ``_apply_security_audit_inactive`` dropped the step and the membership
    assertion would have failed too.
    """
    plan_id = f'secclass-large-{change_type}'.replace('_', '-')
    _stub_footprint(_LARGE_FOOTPRINT)
    _capture_decision_log()

    result = _compose(plan_id, change_type=change_type, affected_files_count=12)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)


# =============================================================================
# (b) An absent / unusable change-shape signal fails toward inclusion
# =============================================================================


def test_stale_declared_surface_fails_toward_inclusion(plan_context):
    """A stale (empty) DECLARED surface keeps the sweep when the worktree has one.

    ``affected_files_count`` comes from ``references.json::affected_files``, which
    is legitimately empty early in a plan's life while the worktree already carries
    the change. The gate reads both surfaces, so either one alone keeps the step —
    the fail-toward-inclusion contract on the second leg.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``, reached first. Behind it, the old gate
    never consulted the live footprint at all, so ``affected_files_count == 0`` was
    an independent drop leg and the membership assertion would have failed too.
    """
    plan_id = 'secclass-stale-declared-surface'
    _stub_footprint(_LARGE_FOOTPRINT)
    _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)


def test_change_type_is_not_a_parameter_of_the_security_gate(plan_context):
    """Structural pin: the security gate's signature carries no change_type.

    The behavioural tests above can only sample change-type values. This one
    closes the sampling gap — the parameter is absent, so no value can reach the
    gate.

    Pre-fix failure (observed against pre-fix HEAD): ``AttributeError: module
    '_mem_script_security_class_regression' has no attribute
    '_apply_security_class_inactive'. Did you mean: '_apply_security_audit_inactive'?``
    — the pre-fix helper's signature DID carry ``change_type``.
    """
    varnames = _mem._apply_security_class_inactive.__code__.co_varnames
    assert 'change_type' not in varnames
    assert 'affected_files_count' in varnames
    assert 'live_footprint_count' in varnames


# =============================================================================
# (c) A genuine drop names its gating reason, loudly
# =============================================================================


def test_genuine_drop_reports_step_and_reason_in_result_and_decision_log(plan_context):
    """The one real drop case is reported in the compose result AND as a [STATUS] line.

    A plan with no declared affected files and an empty live footprint has nothing
    to audit. That drop is legitimate — but it must be loud: the compose result
    carries a ``{step, reason}`` record (which ``phase-4-plan`` Step 7b surfaces in
    its phase return) and ``decision.log`` carries a ``[STATUS]`` line naming both.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``. The pre-fix result reported a bare
    ``security_audit_omitted: True`` boolean that named neither the step nor the
    reason, and the decision-log line it emitted read
    ``finalize-step-security-audit omitted — change_type=analysis
    affected_files_count=0`` — quoting the inputs rather than the gating reason,
    with no ``[STATUS]`` prefix.
    """
    plan_id = 'secclass-genuine-drop'
    _stub_footprint([])
    captured = _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    assert result['security_class_omitted'] == [
        {
            'step': _SECURITY_STEP,
            'reason': 'no declared affected files and empty live footprint',
        }
    ]
    assert _SECURITY_STEP not in _composed_steps(plan_id)

    status_lines = [msg for pid, msg in captured if 'security_class_inactive' in msg]
    assert status_lines == [
        '(plan-marshall:manage-execution-manifest:compose) [STATUS] security_class_inactive — '
        f'dropped {_SECURITY_STEP} from phase_6.steps: '
        'no declared affected files and empty live footprint'
    ]


def test_unresolvable_footprint_keeps_the_step(plan_context):
    """An UNRESOLVABLE live footprint is no evidence, so the step is KEPT.

    The gate's drop requires BOTH signals to be genuinely empty. A footprint that
    could not be resolved at all (the normal state at phase-4-plan compose, before
    the worktree is materialised) is not "nothing to audit" — it is "we could not
    look" — so it fails toward inclusion, the same discipline the absent
    change-type leg follows.

    This is the one falsy footprint state that does NOT drop, which is exactly why
    it needs its own case: the sibling above pins ``[]`` dropping the step, and
    both states are falsy. A predicate written as ``not live_footprint`` would
    satisfy that sibling and silently drop a security audit on every plan whose
    worktree was not yet inspectable.
    """
    plan_id = 'secclass-unresolvable'
    _stub_footprint(None)
    captured = _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)
    assert [msg for pid, msg in captured if 'security_class_inactive' in msg] == []


def test_unresolvable_and_resolvable_empty_footprints_diverge(plan_context):
    """The paired opposite: identical inputs but for the footprint STATE.

    Comparing the two outcomes against each other is what fails if a future change
    re-collapses ``None`` into ``[]`` at this seam — each case asserted alone would
    still pass against a gate that had lost the distinction in one direction.
    """
    _stub_footprint(None)
    _capture_decision_log()
    unresolvable = _compose('secclass-div-unresolvable', change_type='feature', affected_files_count=0)

    _stub_footprint([])
    _capture_decision_log()
    resolvable_empty = _compose('secclass-div-empty', change_type='feature', affected_files_count=0)

    assert unresolvable['security_class_omitted'] == []
    assert [r['step'] for r in resolvable_empty['security_class_omitted']] == [_SECURITY_STEP]
    assert _SECURITY_STEP in _composed_steps('secclass-div-unresolvable')
    assert _SECURITY_STEP not in _composed_steps('secclass-div-empty')


def test_no_omission_report_when_the_step_is_kept(plan_context):
    """The report is drop-only — a kept step produces no record and no [STATUS] line.

    Without this, ``security_class_omitted`` could be populated unconditionally and
    the drop-naming assertion above would still pass, making the loudness signal
    meaningless.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``.
    """
    plan_id = 'secclass-kept-no-report'
    _stub_footprint(_LARGE_FOOTPRINT)
    captured = _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=12)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)
    assert [msg for pid, msg in captured if 'security_class_inactive' in msg] == []


# =============================================================================
# (d) The protected population is derived from step metadata, not a step id
# =============================================================================


def test_population_discriminator_reads_real_frontmatter(plan_context):
    """``persona: persona-security-expert`` is what puts a step in the class — read live.

    No stubbing: this reads the two real standards docs. It is the anchor the
    stubbed test below depends on — if the discriminator ever stops matching the
    shipped frontmatter, this fails first and names why.

    Pre-fix failure (observed against pre-fix HEAD): ``AttributeError: module
    '_mem_script_security_class_regression' has no attribute
    '_is_security_class_step'`` — the pre-fix population was the hardcoded step id
    ``'finalize-step-security-audit'`` passed into ``_apply_code_step_inactive``.
    """
    assert _mem._is_security_class_step(_SECURITY_STEP) is True
    # The structural peer declares no ``persona`` key at all — it is NOT protected,
    # which is what keeps the out-of-scope simplify gate out of this class.
    assert _mem._is_security_class_step(_PEER_STEP) is False
    # An external bundle:skill step has no project-local source and is never in the class.
    assert _mem._is_security_class_step('plan-marshall:plan-retrospective') is False


def test_a_second_step_declaring_the_persona_inherits_the_treatment(plan_context):
    """Any step declaring the persona gets the identical treatment — no production change.

    The population is derived per compose from each candidate's frontmatter, so a
    future second security-class finalize step is protected by declaring the same
    persona. This is pinned by making an ALREADY-RESOLVABLE candidate
    (``adr-propose``) read as security-class through the frontmatter-read seam —
    the derivation in ``_is_security_class_step`` stays under test, only the file
    read is stubbed — and asserting it receives the same fail-toward-inclusion and
    loud-omission treatment. Using an existing step id keeps the composed manifest
    past the step-resolution and ascending-order gates.

    Pre-fix failure (observed against pre-fix HEAD): ``AttributeError: module
    '_mem_script_security_class_regression' has no attribute
    '_read_frontmatter_scalar'. Did you mean: '_read_frontmatter_lane'?`` — the
    frontmatter-scalar seam this derivation depends on did not exist at all, and
    the population was a hardcoded step id no second step could join.
    """
    synthetic = 'adr-propose'
    original_reader = _mem._read_frontmatter_scalar

    def _reader(path, key):
        if key == 'persona' and path.stem == synthetic:
            return 'persona-security-expert'
        return original_reader(path, key)

    _mem._read_frontmatter_scalar = _reader

    # Fail toward inclusion: an excluded change type with a real change surface
    # keeps BOTH class members.
    _stub_footprint(_LARGE_FOOTPRINT)
    _capture_decision_log()
    kept = _compose('secclass-synthetic-kept', change_type='verification', affected_files_count=12)
    assert kept['security_class_omitted'] == []
    kept_steps = _composed_steps('secclass-synthetic-kept')
    assert _SECURITY_STEP in kept_steps
    assert synthetic in kept_steps

    # Loud omission: with no change surface, BOTH class members drop and BOTH are
    # named — while the personaless peer is governed by its own separate gate.
    _stub_footprint([])
    captured = _capture_decision_log()
    dropped = _compose('secclass-synthetic-dropped', change_type='feature', affected_files_count=0)
    dropped_steps = {record['step'] for record in dropped['security_class_omitted']}
    assert dropped_steps == {_SECURITY_STEP, synthetic}
    assert all(
        record['reason'] == 'no declared affected files and empty live footprint'
        for record in dropped['security_class_omitted']
    )
    composed = _composed_steps('secclass-synthetic-dropped')
    assert _SECURITY_STEP not in composed
    assert synthetic not in composed
    status_lines = [msg for pid, msg in captured if 'security_class_inactive' in msg]
    assert len(status_lines) == 2
    assert any(synthetic in msg for msg in status_lines)


def test_personaless_peer_is_not_in_the_security_class(plan_context):
    """``finalize-step-simplify`` is never reported by the security gate.

    The out-of-scope sibling keeps its own ``simplify_inactive`` gate and its own
    boolean result field. If the population ever widened to catch it, this fails.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``.
    """
    plan_id = 'secclass-peer-excluded'
    _stub_footprint([])
    _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    reported = {record['step'] for record in result['security_class_omitted']}
    assert reported == {_SECURITY_STEP}
    assert _PEER_STEP not in reported
    # The peer's own gate still owns it, and still reports through its own field.
    assert result['simplify_omitted'] is True
