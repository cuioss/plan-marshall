#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402


"""Tests for the ``ceremony_finalize_selection`` post-matrix transform.

The transform applies the four finalize ceremony gates (``self_review`` /
``qgate`` / ``simplify`` / ``security_audit``) to the matrix-produced
``phase_6.steps``. Each gate is governed by its owning finalize step's
per-element ``lane`` override (``steps[<owner>].lane`` ∈ ``off``/``minimal``/
``auto``), which ``_read_finalize_gates`` maps to the run-at-all decision the
transform consumes:

- lane ``auto`` (or absent) → ``auto`` (the default) defers to the existing
  machinery — no-op.
- lane ``off`` → ``never`` drops the gate's finalize step.
- lane ``minimal`` → ``always`` force-includes the gate's finalize step, re-adding
  it even when the ``scope_gated_finalize`` pre-filter dropped it.

The transform NEVER touches ``automatic-review`` — the bot-review invariant is
orthogonal and preserved.

Every ceremony gate's ``lane`` override folds under its owning finalize step's
nested param object in ``phase-6-finalize.steps``: ``qgate`` →
``default:pre-push-quality-gate``; ``self_review`` →
``default:pre-submission-self-review``; ``simplify`` →
``default:finalize-step-simplify``; ``security_audit`` →
``default:finalize-step-security-audit``. There is no flat phase-level ``qgate``
sibling. The internal transform name retains the ``ceremony_finalize`` prefix for
continuity.

**Two declaration channels, one merged source.** That ``steps[<owner>].lane``
override is resolved from the MERGED plan-local-over-marshal step map, not from
marshal.json alone: a plan-scoped answer persisted to that plan's
``status.metadata.finalize_step_overrides`` governs the ceremony gate exactly as
a project-wide marshal declaration does. The obligation is a SYMMETRIC PAIR — the
same merged map feeds ``_read_step_owned_knob`` (this transform's run-at-all
knob) and ``_lane_override_for`` (the scope gate's declared-lane immunity
predicate) — so a declaration can never reach one reader and be invisible to the
other. ``TestCeremonyFinalizePlanLocalChannel`` asserts the two channels resolve
identically, which is the assertion that fails if the two readers ever diverge
again.

``always`` is the only path that RE-ADDS a step a pre-filter already dropped, and
it covers only these four gates. It is not the only way an operator declaration
survives an implicit gate: ``scope_gated_finalize``'s declared-lane immunity keeps
a step carrying an explicit non-``standard`` ``lane`` from being dropped at all. That
mechanism (prevent the drop) is distinct from this one (undo the drop), and it is
the only one available to the steps this transform does not cover — see
``test_decision_rules.py`` for its coverage.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext, load_script_module

# =============================================================================
# Module loading (the script filename has hyphens, so it is loaded by identity)
# =============================================================================


_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_script_ceremony_finalize',
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess in tests.
#
# Every assignment MUST name an emitter that still exists: ``setattr`` on a module
# succeeds for a name that was never defined, so a stale entry would silently
# re-create a removed attribute instead of failing loudly.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_kept_unknown = lambda *a, **kw: None
_mem._log_scope_gated_finalize_subtraction = lambda *a, **kw: None
_mem._log_ceremony_finalize_selection = lambda *a, **kw: None
_mem._log_candidate_source = lambda *a, **kw: None
_mem._log_prefilter_omitted = lambda *a, **kw: None
_mem._log_execution_tier_routing = lambda *a, **kw: None

# =============================================================================
# Helpers
# =============================================================================

# The full candidate set including the ceremony-gated finalize steps in
# their canonical (project-prefixed / bare) form. The composer strips the
# `default:` prefix at intake but preserves `project:` prefixes verbatim.
_CEREMONY_FINALIZE_STEPS = [
    'pre-push-quality-gate',
    'default:pre-submission-self-review',
]


# Owning finalize step id for each step-folded knob. Every ceremony gate is
# owned — ``qgate`` now rides ``default:pre-push-quality-gate``'s ``lane`` override
# (there is no flat phase-level ``qgate`` sibling).
_GATE_OWNER_STEP = {
    'qgate': 'default:pre-push-quality-gate',
    'simplify': 'default:finalize-step-simplify',
    'security_audit': 'default:finalize-step-security-audit',
    'self_review': 'default:pre-submission-self-review',
}

# The four ceremony gates whose value is written as the owning step's ``lane``
# override (``off``/``minimal``/``standard``). Any other step-folded knob a caller
# passes is written under its own param key verbatim.
_CEREMONY_LANE_GATES = frozenset({'qgate', 'self_review', 'simplify', 'security_audit'})


_FOOTPRINT = ['marketplace/bundles/x/skills/y/foo.py']


# =============================================================================
# Test: compose-time immune-off floor (D2)
#
# A hand-written ``lane: off`` on a ``class: core`` / ``derived-state`` finalize
# step is IMMUNE — the composer ignores the weakening ``off`` and KEEPS the step
# at its class-default (``minimal``) tier, surfacing an informational warning in
# ``lane_warnings``. A ``lane: off`` on a ``class: adversarial`` / ``prunable``
# step remains a real opt-out that DROPS it. The retired "off honored-but-warning"
# drop of a floor element is gone. Composed under each pruning posture
# (``minimal`` / ``standard``); ``full`` is a no-op lane pass (verified separately).
# =============================================================================


# Canned lane blocks keyed by step id, mirroring the real frontmatter classes of
# the mandatory finalize ceremony floor plus two opt-out peers. The blocks are
# monkeypatched onto ``_resolve_element_lane`` so the immune-off behaviour is
# exercised deterministically without depending on the shipped frontmatter.
_IMMUNE_OFF_LANE_BLOCKS = {
    'push': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'create-pr': {'class': 'core', 'tier': 'minimal', 'cost_size': 'M'},
    'ci-verify': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'branch-cleanup': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'record-metrics': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'archive-plan': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'project:finalize-step-deploy-target': {'class': 'derived-state', 'tier': 'minimal', 'cost_size': 'XS'},
    'project:finalize-step-sync-plugin-cache': {'class': 'derived-state', 'tier': 'minimal', 'cost_size': 'XS'},
    'sonar-roundtrip': {'class': 'adversarial', 'tier': 'standard', 'cost_size': 'L'},
    'plan-marshall:plan-retrospective': {'class': 'prunable', 'tier': 'standard', 'cost_size': 'L'},
}

# The mandatory floor: every ``core`` / ``derived-state`` step named in the D2
# success criteria. Immune to a weakening ``off``.
_IMMUNE_FLOOR_STEPS = [
    'push',
    'create-pr',
    'ci-verify',
    'branch-cleanup',
    'record-metrics',
    'archive-plan',
    'project:finalize-step-deploy-target',
    'project:finalize-step-sync-plugin-cache',
]

# The opt-out peers: a ``lane: off`` here is honoured (drops cleanly).
_OPT_OUT_STEPS = ['sonar-roundtrip', 'plan-marshall:plan-retrospective']

from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_bare import _restore_footprint_resolver
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_compose_ns import (
    _seed_marshal,
    _seed_marshal_lane_overrides,
)
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_lane_dropped import _bare
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_manifest_phase import _lane_dropped_reasons
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_module import _phase_6_with_ceremony_steps
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_patch_immune import (
    _write_execution_profile,
)
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_phase_6 import _compose_ns
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_restore_footprint import (
    _write_plan_local_overrides,
)
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_seed_marshal import _stub_footprint
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_stub_footprint import (
    _manifest_phase_6_steps,
)
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_write_plan import _patch_immune_off_lanes
