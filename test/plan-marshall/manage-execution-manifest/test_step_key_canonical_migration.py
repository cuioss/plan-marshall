#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression coverage for the manifest-bundle canonicalize_step_key migration.

Deliverable 2 DELETED ``_manifest_core._strip_default_prefix`` and migrated every
manifest-bundle call site to the shared ``canonicalize_step_key`` resolver. Because
``canonicalize_step_key`` subsumes the full ``_strip_default_prefix`` semantics
(``default:`` strip + ``PROMOTED_BUILTIN_STEP_IDS`` alias map), the migration is
behaviour-preserving. These tests pin that invariant at every migrated surface so a
future edit that diverges the two is caught:

- ``_role_of`` and ``owner_of`` / ``_owner_classification_key`` classify
  ``default:`` / ``project:``-prefixed ids identically to their bare forms;
- ``_manifest_lanes._lane_override_for`` resolves a ``default:``-prefixed marshal
  key identically to its bare form;
- ``_manifest_rules._snapshot_step_params`` and
  ``_apply_unresolved_ask_provider_drop`` stay prefix-agnostic;
- the promoted ``plan-marshall:automatic-review`` id still normalizes to bare
  ``automatic-review`` (the alias behaviour ``_strip_default_prefix`` used to own),
  including at the ``_discovered_implementor_names`` surface;
- the removed symbol is gone from ``_manifest_core`` and the shared resolver is
  re-exported in its place.
"""

import importlib.util
from pathlib import Path

# The shared resolver imports by bare name (script-shared/scripts on PYTHONPATH).
from _step_key_canonical import PROMOTED_BUILTIN_STEP_IDS, canonicalize_step_key

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


_core = _load_module('_mig_core', '_manifest_core.py')
_lanes = _load_module('_mig_lanes', '_manifest_lanes.py')
_rules = _load_module('_mig_rules', '_manifest_rules.py')
_validation = _load_module('_mig_validation', '_manifest_validation.py')


# =============================================================================
# The removed symbol is gone; the shared resolver is re-exported in its place.
# =============================================================================


def test_strip_default_prefix_symbol_is_removed_from_manifest_core():
    """``_manifest_core`` no longer defines/re-exports ``_strip_default_prefix``."""
    assert not hasattr(_core, '_strip_default_prefix')


def test_manifest_core_reexports_shared_resolver_and_alias_map():
    """``_manifest_core`` re-exports the shared ``canonicalize_step_key`` +
    ``PROMOTED_BUILTIN_STEP_IDS`` so existing consumers keep importing them."""
    assert _core.canonicalize_step_key is canonicalize_step_key
    assert _core.PROMOTED_BUILTIN_STEP_IDS == PROMOTED_BUILTIN_STEP_IDS


# =============================================================================
# _role_of — prefix-agnostic role derivation
# =============================================================================


def test_role_of_default_and_bare_verify_are_identical():
    """A ``default:verify:{canonical}`` id derives the same role as its bare form."""
    for canonical, role in (
        ('quality-gate', 'quality-gate'),
        ('module-tests', 'module-tests'),
        ('verify', 'module-tests'),
        ('coverage', 'coverage'),
    ):
        default_role = _core._role_of(f'default:verify:{canonical}', {})
        bare_role = _core._role_of(f'verify:{canonical}', {})
        assert default_role == bare_role == role


# =============================================================================
# owner_of / _owner_classification_key — prefix-agnostic ownership routing
# =============================================================================


def test_owner_of_default_and_bare_are_identical():
    """``default:``-prefixed and bare finalize step ids classify identically."""
    assert _core.owner_of('default:finalize-step-simplify') == _core.owner_of('finalize-step-simplify')
    assert _core.owner_of('finalize-step-simplify') == 'orchestrator-owned'


def test_owner_of_project_prefixed_classifies_as_bare():
    """A ``project:``-prefixed step classifies identically to its bare name."""
    assert _core.owner_of('project:finalize-step-plugin-doctor') == 'orchestrator-owned'
    assert _core.owner_of('finalize-step-plugin-doctor') == 'orchestrator-owned'


def test_owner_classification_key_strips_default_then_project():
    """The classification key reduces ``default:`` and ``project:`` to the bare name."""
    assert _core._owner_classification_key('default:pre-submission-self-review') == (
        'pre-submission-self-review'
    )
    assert _core._owner_classification_key('project:finalize-step-plugin-doctor') == (
        'finalize-step-plugin-doctor'
    )


def test_owner_classification_key_maps_promoted_alias():
    """The promoted ``plan-marshall:automatic-review`` reduces to bare ``automatic-review``."""
    assert _core._owner_classification_key('plan-marshall:automatic-review') == 'automatic-review'


# =============================================================================
# _manifest_lanes._lane_override_for — prefixed marshal keys resolve under bare
# =============================================================================


def test_lane_override_for_default_marshal_key_resolves_under_bare_query():
    """A ``default:``-prefixed marshal key resolves for the bare in-manifest id."""
    overrides = {'default:push': {'lane': 'off'}}
    assert _lanes._lane_override_for('push', overrides) == 'off'


def test_lane_override_for_bare_marshal_key_still_resolves():
    """A bare marshal key resolves identically (behaviour preserved)."""
    overrides = {'push': {'lane': 'minimal'}}
    assert _lanes._lane_override_for('push', overrides) == 'minimal'


def test_lane_override_for_promoted_alias_key_resolves_under_bare():
    """A promoted ``plan-marshall:automatic-review`` marshal key resolves under bare."""
    overrides = {'plan-marshall:automatic-review': {'lane': 'off'}}
    assert _lanes._lane_override_for('automatic-review', overrides) == 'off'


# =============================================================================
# _manifest_rules._snapshot_step_params — bare in-manifest id ↔ default: marshal key
# =============================================================================


def test_snapshot_step_params_matches_bare_id_to_default_marshal_key():
    """A bare in-manifest id snapshots the params of its ``default:``-prefixed marshal key."""
    snapshot = _rules._snapshot_step_params(['push'], {'default:push': {'pr_merge_strategy': 'squash'}})
    assert snapshot == {'push': {'pr_merge_strategy': 'squash'}}


def test_snapshot_step_params_ownerless_step_snapshots_none():
    """A step with no marshal-side entry snapshots as ``None`` (unchanged)."""
    snapshot = _rules._snapshot_step_params(['create-pr'], {'default:push': {'x': 1}})
    assert snapshot == {'create-pr': None}


# =============================================================================
# _manifest_rules._apply_unresolved_ask_provider_drop — prefix-agnostic
# =============================================================================


def test_unresolved_ask_provider_drop_drops_promoted_automatic_review_when_ci_absent():
    """A promoted ``plan-marshall:automatic-review`` candidate with an unresolved
    ``lane:ask`` and no CI provider drops — the step is canonicalized to bare
    before the lane-override lookup."""
    kept, dropped = _rules._apply_unresolved_ask_provider_drop(
        ['plan-marshall:automatic-review'],
        {'plan-marshall:automatic-review': {'lane': 'ask'}},
        None,  # ci_provider absent
        None,  # sonar_provider absent
    )
    assert dropped == ['plan-marshall:automatic-review']
    assert kept == []


def test_unresolved_ask_provider_drop_keeps_automatic_review_when_ci_present():
    """With a CI provider configured, the unresolved-ask automatic-review survives."""
    kept, dropped = _rules._apply_unresolved_ask_provider_drop(
        ['plan-marshall:automatic-review'],
        {'plan-marshall:automatic-review': {'lane': 'ask'}},
        'github',
        None,
    )
    assert kept == ['plan-marshall:automatic-review']
    assert dropped == []


# =============================================================================
# _discovered_implementor_names — promoted alias present in both forms
# =============================================================================


def test_discovered_implementor_names_folds_promoted_alias_both_forms():
    """The promoted automatic-review id appears in BOTH its bundle-prefixed and
    bare forms (the alias behaviour the removed _strip_default_prefix owned)."""
    names = _validation._discovered_implementor_names('phase_6')
    assert 'plan-marshall:automatic-review' in names
    assert 'automatic-review' in names
