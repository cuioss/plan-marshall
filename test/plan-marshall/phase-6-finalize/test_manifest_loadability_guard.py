#!/usr/bin/env python3
"""Tests for phase-6-finalize Step 1.5 (Manifest Loadability Check).

phase-6-finalize is a workflow-driven skill — it has no Python entry point of
its own. The loadability guard is implemented by ``manage-execution-manifest
validate-loadable`` and consumed by SKILL.md Step 1.5. These tests pin two
contracts:

1. **SKILL.md narrative** — Step 1.5 is documented inline (with the exact
   subcommand invocation and the canonical actionable failure message), and
   ``standards/required-steps.md`` carries the matching "Loadability
   Contract" section. A future edit that drops the guard from prose without
   also dropping it from the underlying script must fail this test before it
   can land.

2. **Loadability simulation** — using ``cmd_validate_loadable`` directly as
   the dispatcher would, a manifest whose ``phase_6.steps`` contains a
   non-existent built-in step yields ``unloadable_count > 0`` and a per-step
   message that matches the canonical phrasing surfaced by the SKILL.md
   error log line.

Hard contract: a missing standards file MUST be detected at phase entry
(Step 1.5) — the dispatcher MUST NOT enter Step 3 in that state. The
simulator below mirrors what the dispatcher would compute from the
``validate-loadable --all`` payload.
"""

# ruff: noqa: I001, E402

import importlib.util
from argparse import Namespace

from conftest import MARKETPLACE_ROOT

# ---------------------------------------------------------------------------
# Manifest module (Tier 2 direct import via importlib because of the hyphen)
# ---------------------------------------------------------------------------

_MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
    / 'manage-execution-manifest.py'
)
_spec = importlib.util.spec_from_file_location('mem_for_loadability', str(_MANIFEST_SCRIPT))
assert _spec is not None
_mem = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mem)

cmd_compose = _mem.cmd_compose
cmd_validate_loadable = _mem.cmd_validate_loadable
read_manifest = _mem.read_manifest
write_manifest = _mem.write_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Skill prose anchors
# ---------------------------------------------------------------------------

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_SKILL_MD = _SKILL_DIR / 'SKILL.md'
_REQUIRED_STEPS_MD = _SKILL_DIR / 'standards' / 'required-steps.md'


def _compose_ns(plan_id: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
        phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
        commit_strategy=None,
    )


def _validate_loadable_ns(plan_id: str, *, step_id: str | None = None, use_all: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, step_id=step_id, all=use_all)


# ===========================================================================
# SKILL.md narrative contract — Step 1.5 is documented inline
# ===========================================================================


class TestSkillNarrativeContract:
    """The dispatcher invokes ``validate-loadable`` per SKILL.md prose.

    These tests treat the SKILL.md document as part of the public interface:
    a future edit that removes Step 1.5, drops the canonical actionable
    message, or stops dispatching to ``manage-execution-manifest
    validate-loadable`` MUST fail here so the contract drift is visible
    before the change lands.
    """

    def test_skill_md_documents_step_1_5_manifest_loadability_check(self):
        body = _SKILL_MD.read_text(encoding='utf-8')
        assert 'Step 1.5: Manifest Loadability Check' in body, (
            'phase-6-finalize SKILL.md MUST document Step 1.5 (Manifest Loadability Check) '
            'between Step 2 (Read Manifest) and Step 3 (Execute Step Pipeline).'
        )

    def test_skill_md_invokes_validate_loadable_subcommand(self):
        body = _SKILL_MD.read_text(encoding='utf-8')
        assert 'validate-loadable' in body, (
            'SKILL.md must reference the validate-loadable subcommand by name so a '
            "future grep / refactor can't silently drop the dispatch."
        )
        # Both single-step and bulk forms are documented as valid invocations.
        assert '--step-id' in body
        assert '--all' in body

    def test_skill_md_carries_canonical_actionable_message(self):
        body = _SKILL_MD.read_text(encoding='utf-8')
        # The canonical phrase surfaced to the user / work.log on guard failure.
        # Matches the exact wording emitted by ``_check_step_loadable``.
        assert 'missing standards file' in body
        assert 'deleted the file without sweeping' in body

    def test_required_steps_md_documents_loadability_contract(self):
        body = _REQUIRED_STEPS_MD.read_text(encoding='utf-8')
        assert '## Loadability Contract' in body, (
            'standards/required-steps.md MUST carry a "Loadability Contract" section '
            'cross-referencing the validate-loadable subcommand.'
        )
        assert 'validate-loadable' in body


# ===========================================================================
# Loadability simulation — mirror what Step 1.5 computes from the
# ``validate-loadable --all`` payload.
# ===========================================================================


class TestLoadabilityGuardSimulation:
    """Simulate phase-6-finalize Step 1.5 directly via cmd_validate_loadable.

    The dispatcher reads the manifest, calls ``validate-loadable --all``, and
    aborts when ``unloadable_count > 0``. We compute the same payload via the
    in-process command handler so the abort condition is testable without a
    live subprocess.
    """

    def test_clean_manifest_passes_loadability_check(self, plan_context):
        cmd_compose(_compose_ns('loadability-clean'))
        result = cmd_validate_loadable(_validate_loadable_ns('loadability-clean', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 0, (
            'A composed default manifest must report every step loadable; '
            'otherwise phase-6-finalize Step 1.5 would refuse to enter Step 3 '
            'on every healthy plan.'
        )

    def test_manifest_with_deleted_standards_file_fails_check(self, plan_context):
        cmd_compose(_compose_ns('loadability-deleted'))
        manifest = read_manifest('loadability-deleted')
        assert manifest is not None
        # Simulate a self-modifying plan that deleted a step's standards
        # file but forgot to sweep marshal.json — the manifest still
        # references the now-orphaned step.
        manifest['phase_6']['steps'].append('orphaned-step-no-standards-file')
        write_manifest('loadability-deleted', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('loadability-deleted', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 1
        failing = [r for r in result['results'] if not r['loadable']]
        assert len(failing) == 1
        assert failing[0]['step_id'] == 'orphaned-step-no-standards-file'
        # The actionable message mirrors the SKILL.md error-log line.
        assert 'missing standards file' in failing[0]['message']

    def test_external_step_never_triggers_unloadable(self, plan_context):
        """project:/skill: steps short-circuit — the guard MUST NOT abort on them."""
        cmd_compose(_compose_ns('loadability-external'))
        manifest = read_manifest('loadability-external')
        assert manifest is not None
        manifest['phase_6']['steps'].insert(0, 'project:finalize-step-deploy-target')
        manifest['phase_6']['steps'].insert(0, 'plan-marshall:plan-retrospective')
        write_manifest('loadability-external', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('loadability-external', use_all=True))
        assert result is not None
        assert result['unloadable_count'] == 0, (
            'External steps must short-circuit to loadable=true so the guard '
            "doesn't false-positive on project:/bundle:skill entries."
        )
