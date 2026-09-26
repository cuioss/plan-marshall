#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402


"""Tests for the ``compose`` subcommand of manage-execution-manifest.py.

Split from test_manage_execution_manifest.py — tier 2 direct-import tests for
the compose path (decision matrix, boundary normalization, commit-and-push,
pre-push-quality-gate, frontmatter-order sort, and marshal.json
source-of-truth) plus the relevant CLI plumbing tests.
"""

import contextlib
import json
import re
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

import pytest
from _execution_manifest_fixtures import fake_lane_blocks

from conftest import create_marshal_json, get_script_path, load_script_module, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports, resolved by (bundle, skill, script).


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_script'
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
get_manifest_path = _mem.get_manifest_path
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
DEFAULT_ENVELOPE_COUNT = _mem.DEFAULT_ENVELOPE_COUNT
_role_of = _mem._role_of

# Execution-profile lane resolver surface.
cmd_lanes_preview = _mem.cmd_lanes_preview
_apply_lane_resolution = _mem._apply_lane_resolution
_lane_keep_decision = _mem._lane_keep_decision
_effective_lane_tier = _mem._effective_lane_tier
_read_execution_profile = _mem._read_execution_profile
_parse_cost_magnitude = _mem._parse_cost_magnitude
_sum_lane_cost = _mem._sum_lane_cost

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor. The handler is wrapped in try/except so failures are
# already silent, but we replace it with a no-op for clarity and speed.
_mem._log_decision = lambda *a, **kw: None


# =============================================================================
# Boundary-Normalization Regression Tests
#
# `phase_6_candidates` may arrive prefixed (`default:foo` from marshal.json's
# step registry) or bare (`foo` from DEFAULT_PHASE_6_STEPS). The composer
# normalizes both
# ``phase_5_candidates`` and ``phase_6_candidates`` once at the
# ``cmd_compose`` boundary — every leading ``default:`` is stripped a single
# time at intake, so the six-row matrix and the pre-filter helpers all see
# bare names. Manifest output and result fields are bare strings throughout.
#
# These tests feed prefixed candidates and assert the resulting manifest
# carries bare-name entries, with each cascade rule (Rule 1, 2, 4, 5, 6)
# dropping or including the right steps. They previously asserted that the
# prefix survived verbatim into the manifest output — that contract has been
# retired in favor of the boundary-normalization contract pinned by
# ``test_boundary_normalization_strips_prefix_for_all_downstream_consumers``.
# =============================================================================


_PREFIXED_PHASE_6 = (
    'default:pre-push-quality-gate',
    'default:push',
    'default:create-pr',
    'plan-marshall:automatic-review',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:archive-plan',
)


#: (status.json metadata to seed, or None for no status.json; compose-arg overrides
#: on top of a plain feature/multi_module/4-file plan with no --recipe-key; the rule
#: that must fire). The `default` rows are the load-bearing negatives: a detector
#: that fired on the presence of ANY metadata would pass every `recipe` row here.
_RECIPE_PROVENANCE_CASES = [
    (
        {'plan_source': '2026-06-01-10-001'},
        {'change_type': 'enhancement', 'scope_estimate': 'single_module', 'affected_files_count': 3},
        'recipe',
    ),
    ({'recipe_key': 'lesson_cleanup'}, {}, 'recipe'),
    ({'plan_source': 'recipe'}, {}, 'recipe'),
    ({'change_type': 'feature'}, {}, 'default'),
    (None, {}, 'default'),
    (None, {'recipe_key': 'lesson_cleanup'}, 'recipe'),
]


# =============================================================================
# commit_and_push pre-filter tests
# =============================================================================


#: The three steps ``commit_push_disabled`` subtracts. ``push`` is directly
#: disabled; the two gates go because both are only meaningful when a downstream
#: push exists. All three must be NAMED when present — the former aggregate
#: reporting named only ``push``, so the two gates vanished unrecorded.
#:
#: The gate removes the INTERSECTION of this set with the candidate list, so a
#: test that wants to observe all three drops must put all three in the
#: candidates. ``DEFAULT_PHASE_6_STEPS`` carries only ``push``, which is exactly
#: how the old aggregate reporting looked adequate: the common fixture drops one
#: step, and one step is all an aggregate line can name.
_COMMIT_PUSH_DROP_SET = {'push', 'pre-push-quality-gate', 'pre-submission-self-review'}


# =============================================================================
# scope_gated_finalize pre-filter tests
#
# The composer drops heavyweight phase-6 review/audit steps by
# scope. surgical drops the three review/audit steps (plan-retrospective,
# pre-submission-self-review, plugin-doctor) but RETAINS automatic-review by
# default (the implicit scope gate never drops it — its presence is governed by
# its configured lane); drop_review_on_scope_gate=true additionally drops
# automatic-review; single_module drops only plan-retrospective.
# multi_module/broad retain the full set. One decision-log line per subtraction.
# =============================================================================


# Candidate set covering the three scope-gated steps in their canonical
# prefixed forms plus the review gates and a few baseline steps. The composer
# boundary-normalizes only the `default:` namespace, so `project:` /
# `plan-marshall:` prefixes survive intake and the scope gate matches them
# against its match-sets.
_SCOPE_GATE_PHASE_6 = (
    'push',
    'create-pr',
    'automatic-review',
    'sonar-roundtrip',
    'default:pre-submission-self-review',
    'project:finalize-step-plugin-doctor',
    'lessons-capture',
    'plan-marshall:plan-retrospective',
    'branch-cleanup',
    'archive-plan',
)


# =============================================================================
# Execution-profile lane resolution
# =============================================================================
#
# The lane resolver projects the operator posture (minimal / standard / full) over
# each phase-6 element's self-declared ``lane:`` frontmatter block. The unit
# cases below exercise the pure resolution helpers with canned lane blocks; the
# integration cases drive ``cmd_compose`` / ``cmd_lanes_preview`` end-to-end with
# the element-lane resolver monkeypatched to deterministic blocks.

# Canned lane blocks spanning all four classes + both tier deviations (shared
# fixture in _execution_manifest_fixtures.py).
_LANE_BLOCKS = fake_lane_blocks()
_LANE_STEPS = list(_LANE_BLOCKS)


#: (element lane, operator override, posture, kept?, fragments the warning must carry).
#: An empty fragment tuple means the decision carries NO warning. The immune rows
#: are the reason the warning is asserted at all: a floor element silently ignoring
#: an `off` override, with nothing said, is indistinguishable from one that honoured it.
_LANE_OVERRIDE_DECISIONS = [
    ({'class': 'derived-state', 'tier': 'minimal'}, 'off', 'minimal', True, ('derived-state', 'immune')),
    ({'class': 'core', 'tier': 'minimal'}, 'off', 'minimal', True, ('core', 'immune')),
    ({'class': 'adversarial', 'tier': 'standard'}, 'off', 'standard', False, ()),
    ({'class': 'prunable', 'tier': 'standard'}, 'off', 'standard', False, ()),
    ({'class': 'adversarial', 'tier': 'full'}, 'minimal', 'minimal', True, ()),
]


# --- cmd_lanes_preview: the declared-vs-effective report ---------------------
#
# ``lane_report[]`` answers the question an operator otherwise cannot ask without
# running a plan: is the lane I stored actually in force? A stored value and an
# effective value are DIFFERENT facts, and the pair that motivates the report is
# the inert one — a declaration that was accepted and stored but neutralized on
# resolution. Every control below therefore asserts the two values TOGETHER with
# ``binds`` and ``reason``, because ``declared`` alone cannot distinguish an
# override that took effect from one that was overruled.
#
# These cases source their candidate list from a marshal.json fixture rather than
# the ``--phase-6-steps`` CSV the section above uses: a declaration channel can
# only be read off a config that exists on disk, so a CSV-driven preview has no
# declaration to report on at all.

#: The project-wide declaration fixture. Two of the six steps carry an ``off``,
#: chosen to sit on opposite sides of the floor-immunity rule so the report's two
#: outcomes are both exercised against a real resolution rather than one being
#: asserted in isolation:
#:
#: * ``sonar-roundtrip`` is ``prunable`` — a non-floor class, so its ``off`` is a
#:   real opt-out that BINDS.
#: * ``project:finalize-step-deploy-target`` is ``derived-state`` — a floor class
#:   immune to a weakening ``off``, so its ``off`` is stored but INERT.
#:
#: The remaining four declare nothing, and are the matched negative control: a
#: row with no declaration must be distinguishable from a row whose declaration
#: was neutralized, and both report ``binds: false``.
_LANE_REPORT_MARSHAL_STEPS: dict[str, dict] = {
    'default:push': {},
    'default:archive-plan': {},
    'default:sonar-roundtrip': {'lane': 'off'},
    'default:finalize-step-security-audit': {},
    'plan-marshall:plan-retrospective': {},
    'project:finalize-step-deploy-target': {'lane': 'off'},
}


# =============================================================================
# Compose-result subtraction-record surface
#
# "Every subtraction is reported" is the normative contract: each site that
# removes a step surfaces its removals on the compose result in the shared
# ``{step, reason}`` shape, so no drop is visible only as an absence from
# ``phase_6.steps``. These cases pin the FIELD SET rather than any one site's
# behaviour — a new subtraction site that forgets to surface its records, or an
# old field left behind by a clean break, fails here.
# =============================================================================


#: Every compose-result field carrying subtraction records, in the shared
#: ``{step, reason}`` shape. Kept as one set so a site added without a
#: corresponding result field is a visible omission rather than a silent one.
_SUBTRACTION_RECORD_FIELDS = (
    'commit_push_dropped',
    'decision_matrix_dropped',
    'security_class_omitted',
    'lane_dropped',
)

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_candidate_phase import (
    _pinned_footprint,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_capture_decision import (
    _compose_ns,
    _compose_ns_with_envelope_count,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_compose_ns import (
    _write_status_metadata,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_dropped_steps import (
    _lanes_preview_ns,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_lane_report import (
    _seed_marshal_with_finalize_steps,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_lanes_preview import (
    _seed_lane_report_marshal,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_make_tier import (
    _write_drop_review_marshal,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_module import _capture_decision_log
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_patch_element import _dropped_steps
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_phase_6 import (
    _write_marshal,
    _write_marshal_with_ci,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_pinned_footprint import (
    _write_full_marshal,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_read_task import _make_tier_stub
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_restore_footprint import (
    _candidate_phase_6_with_pre_push,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_seed_lane import (
    _seed_plan_local_lane,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_seed_plan import (
    _lane_report_ns,
    _lane_report_row,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_stub_footprint import (
    _restore_footprint_seams_module_wide,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_write_drop import _patch_element_lane
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_write_full import _write_task
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_write_marshal import _stub_footprint
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_write_status import (
    _phase_6_with_every_commit_push_gate,
)
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures_surface_write_task import _read_task
