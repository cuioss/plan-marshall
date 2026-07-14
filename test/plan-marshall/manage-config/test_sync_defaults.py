#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the sync-defaults command in manage-config.

Covers the non-destructive deep-merge contract:
- empty marshal.json gains all defaults
- user-set keys are preserved while missing ones are added
- deeply-nested missing sub-keys are added (including the keyed-map step structure)
- idempotency (re-running adds nothing)
- TOON output enumerates added dotted paths correctly
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_sync_mod = _load_module('_cmd_sync_defaults', '_cmd_sync_defaults.py')
_config_defaults_mod = _load_module('_config_defaults_for_sync_provisioning_test', '_config_defaults.py')

cmd_sync_defaults = _sync_mod.cmd_sync_defaults


# =============================================================================
# Keyed-map serial-form helpers
# =============================================================================
#
# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize on disk as the canonical keyed map: an id-keyed object
# `{step_id: {params}}` (`{}` for a config-less step). The default seed is
# therefore a dict, which the deep-merge recurses into: a present step key keeps
# its value while missing sibling step keys (and missing per-step params) are
# back-filled from the default keyed map.


def _params_for(steps_map: dict, step_id: str):
    """Return a step's params from a keyed-map steps object.

    Returns the step's nested param object (``{}`` for a config-less step).
    Raises ``KeyError`` when the step id is absent.
    """
    return steps_map[step_id]


def _write_marshal(fixture_dir: Path, config: dict) -> Path:
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return marshal_path


def _read_marshal(fixture_dir: Path) -> dict:
    return json.loads((fixture_dir / 'marshal.json').read_text(encoding='utf-8'))


def test_sync_defaults_errors_when_uninitialized(plan_context):
    """sync-defaults fails cleanly when marshal.json does not exist."""
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'error'
    assert 'marshal.json' in result['error'].lower()


def test_sync_defaults_empty_marshal_gains_all_defaults(plan_context):
    """An empty marshal.json gains every key present in get_default_config()."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    assert result['added_count'] > 0
    config = _read_marshal(plan_context.fixture_dir)
    # the steps default is the keyed-map form; auto_rebase_threshold nests in
    # the nested param object for default:branch-cleanup
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert config['project']['default_base_branch'] == 'main'
    # Top-level default keys are added
    assert 'plan' in result['added']
    assert 'project' in result['added']


def test_sync_defaults_preserves_user_set_param_in_keyed_map(plan_context):
    """A user-set per-step param survives the sync; missing siblings are back-filled.

    The steps default is the keyed map, which the deep-merge recurses into: a
    present step key keeps its pinned param, while missing sibling params (and
    missing sibling steps) are back-filled from the default keyed map.
    """
    # user pinned pr_merge_strategy on the branch-cleanup step
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:branch-cleanup': {'pr_merge_strategy': 'merge'}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    # the user's pinned param survives the deep-merge
    assert branch_cleanup['pr_merge_strategy'] == 'merge'
    # the missing sibling param is back-filled from the default keyed map
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    # the per-step dotted path is reported for the back-filled sibling
    assert 'plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold' in result['added']


def test_sync_defaults_preserves_user_set_true_in_keyed_map(plan_context):
    """A user-set True survives even though the default value is False (keyed-map merge).

    final_merge_without_asking is a nested param of default:branch-cleanup in the
    keyed map. The deep-merge preserves the present param key, so an explicit True
    survives the False default.
    """
    # user explicitly opted into merge-without-asking (default is False)
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:branch-cleanup': {'final_merge_without_asking': True}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the user's True override survives the deep-merge
    assert _params_for(steps, 'default:branch-cleanup')['final_merge_without_asking'] is True
    # the present param key is not re-added
    assert 'plan.phase-6-finalize.steps.default:branch-cleanup.final_merge_without_asking' not in result['added']


def test_sync_defaults_deep_merges_missing_siblings_into_keyed_map_steps(plan_context):
    """The default keyed map deep-merges missing siblings into a present user keyed map.

    Under the keyed-map merge, a user `steps` map that omits a sibling param gets
    it back-filled from the default — the merge recurses into the keyed map. This
    pins the behavioral consequence of restoring the keyed-map form (the LIST
    atomic-merge is gone).
    """
    # the branch-cleanup step is present but lacks auto_rebase_threshold
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:branch-cleanup': {'pr_merge_strategy': 'squash'}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['pr_merge_strategy'] == 'squash'
    # the missing sibling IS back-filled — the keyed map recurses per-step
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert 'plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold' in result['added']


def test_sync_defaults_backfills_missing_steps_into_pruned_keyed_map(plan_context):
    """A user's pruned single-entry steps map gains the missing default steps.

    The schema default is the keyed map, and the deep-merge recurses into it, so a
    user who pruned steps to a single entry gets the missing default step keys
    back-filled (each as a new top-level step key).
    """
    # user pruned the finalize steps to a single config-less entry
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:push': {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    # the user's pruned entry survives
    assert 'default:push' in steps
    # a missing default step is back-filled and reported as a new step key
    assert 'default:archive-plan' in steps
    assert 'plan.phase-6-finalize.steps.default:archive-plan' in result['added']


def test_sync_defaults_is_idempotent(plan_context):
    """Re-running sync-defaults immediately produces an empty added list."""
    _write_marshal(plan_context.fixture_dir, {})
    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'
    assert first['added_count'] > 0

    # second run
    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    assert second['added'] == []
    assert second['added_count'] == 0


def test_sync_defaults_reports_added_paths_sorted(plan_context):
    """The TOON report enumerates added dotted paths in sorted order."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    assert result['added'] == sorted(result['added'])
    assert result['added_count'] == len(result['added'])


# =============================================================================
# Keyed-map back-fill on sync (steps / verification_steps copied as a keyed map)
# =============================================================================
#
# The steps / verification_steps defaults are the keyed-map form (`{}` for
# config-less steps, a non-empty param object for param-owning steps). When the
# whole `plan` block is absent, the default keyed map is copied wholesale under
# the top-level `plan` path. Config-less steps land as `{}`; param-owning steps
# land with their nested param object.


def test_sync_defaults_backfills_verification_steps_as_keyed_map(plan_context):
    """Syncing an empty marshal.json back-fills verification_steps as a keyed map of {}."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    # the whole keyed map is copied; config-less verify steps map to {}
    assert isinstance(verification_steps, dict)
    assert verification_steps, 'verification_steps backfill should not be empty'
    assert all(params == {} for params in verification_steps.values()), (
        f'config-less verify steps must map to {{}}, got {verification_steps!r}'
    )


def test_sync_defaults_materializes_all_finalize_steps_as_keyed_map_form(plan_context):
    """Syncing an empty marshal.json materializes EVERY finalize-step implementor.

    D1 changed `_seed_finalize_steps` to materialize every discovered built-in
    implementor (no `default_on` filter): exclusion is expressed as a `lane: off`
    override, never absence, and the two adversarial infra elements
    (`default:sonar-roundtrip` / `plan-marshall:automatic-review`) seed a
    `lane: ask` override. The four ceremony gates (qgate / self_review / simplify /
    security_audit) no longer ride a run-at-all param — `finalize-step-simplify`
    and `finalize-step-security-audit` are config-less, and
    `pre-submission-self-review` retains only its `drop_review_on_scope_gate` param.
    """
    from extension_discovery import find_implementors

    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    assert steps, 'finalize steps backfill should not be empty'

    # Every step value is a dict (the keyed-map shape).
    for _step_id, params in steps.items():
        assert isinstance(params, dict), f'every step value must be a dict; got {params!r}'

    # Materialize-all: every discovered built-in implementor is present in the seed.
    implementors = [
        rec
        for rec in find_implementors(_config_defaults_mod.FINALIZE_STEP_EXT_POINT)
        if rec.get('source') == 'built-in' and rec.get('name')
    ]
    built_in_names = {rec['name'] for rec in implementors}
    assert built_in_names <= set(steps), (
        f'materialize-all seed must carry every built-in implementor; '
        f'missing: {built_in_names - set(steps)!r}'
    )

    infra = {'default:sonar-roundtrip', 'plan-marshall:automatic-review'}
    # The two adversarial infra elements seed `lane: ask`.
    for name in infra:
        assert steps[name].get('lane') == 'ask', (
            f'{name} must seed lane:ask, got {steps[name]!r}'
        )

    # Every non-infra `default_on: false` step seeds `lane: off` (exclusion as
    # lane:off, never absence); infra elements are exempt (they seed lane:ask).
    for rec in implementors:
        name = rec['name']
        if name in infra or rec.get('default_on'):
            continue
        assert steps[name].get('lane') == 'off', (
            f'default_on:false step {name!r} must seed lane:off, got {steps[name]!r}'
        )

    # The retired ceremony run-at-all params are gone from their owning steps;
    # simplify / security-audit are config-less, self-review keeps only its
    # escape-hatch param.
    assert 'simplify' not in steps.get('default:finalize-step-simplify', {})
    assert 'security_audit' not in steps.get('default:finalize-step-security-audit', {})
    assert 'self_review' not in steps.get('default:pre-submission-self-review', {})
    assert 'drop_review_on_scope_gate' in steps.get('default:pre-submission-self-review', {})


def test_sync_defaults_preserves_present_steps_map_untouched(plan_context):
    """A present `steps` map's existing keys are preserved; missing default keys are back-filled.

    The deep-merge recurses into a present keyed map: a user-supplied step key is
    preserved verbatim, while every missing default step key is back-filled.
    """
    # a marshal.json whose finalize steps already carry a pruned keyed map
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:create-pr': {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the pre-existing entry is preserved
    assert 'default:create-pr' in steps
    # the present step key is NOT reported as added
    assert 'plan.phase-6-finalize.steps.default:create-pr' not in result['added']
    # a missing default step key IS back-filled
    assert 'default:archive-plan' in steps


def test_sync_defaults_is_idempotent_against_keyed_map_steps(plan_context):
    """A second sync adds nothing — the keyed-map back-fill is idempotent.

    The first sync copies the default keyed map; the second observes the
    `steps` / `verification_steps` keys already present and re-adds nothing,
    proving the merge is stable against the keyed map it just wrote.
    """
    _write_marshal(plan_context.fixture_dir, {})
    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'

    # second run observes the back-filled keyed map and adds nothing
    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    assert second['added'] == []
    assert second['added_count'] == 0
    # the verify steps remain the keyed map of {} after the idempotent re-sync
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    assert isinstance(verification_steps, dict)
    assert all(params == {} for params in verification_steps.values())


def test_sync_defaults_seeds_auto_route_recipe_knobs_into_legacy_config(plan_context):
    """A legacy phase-1-init block lacking the recipe-match knobs gains them non-destructively.

    The deep-merge back-fills `auto_route_recipe` (True) and
    `auto_route_recipe_threshold` (0.6) into a phase-1-init block that predates the
    knobs, while preserving the user's existing siblings. This pins the
    sync-defaults seeding contract for the recipe-match auto-route gate.
    """
    # legacy phase-1-init block present but missing the recipe-match knobs
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-1-init': {'branch_strategy': 'feature', 'deep_lane': 'auto'}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    init_block = config['plan']['phase-1-init']
    # the user's existing siblings survive
    assert init_block['branch_strategy'] == 'feature'
    assert init_block['deep_lane'] == 'auto'
    # the missing recipe-match knobs are back-filled with their defaults
    assert init_block['auto_route_recipe'] is True
    assert init_block['auto_route_recipe_threshold'] == 0.6
    assert 'plan.phase-1-init.auto_route_recipe' in result['added']
    assert 'plan.phase-1-init.auto_route_recipe_threshold' in result['added']


# =============================================================================
# Provisioning-stamp refresh on the reconcile path (this plan, D2)
# =============================================================================
#
# sync-defaults is the deep-merge reconcile marshall-steward invokes. Beyond
# back-filling missing default keys, it REFRESHES the two runtime provisioning
# stamps (system.provisioned_version / system.config_seed_fingerprint) so a stamp
# that predates a default-config change is re-derived — the deep-merge alone
# never touches an already-present key.


def test_sync_defaults_stamps_provisioning_fields(plan_context):
    """sync-defaults stamps the provisioning fields into a config that lacks them."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    system = config['system']
    assert 'provisioned_version' in system, 'sync-defaults must stamp system.provisioned_version'
    assert 'config_seed_fingerprint' in system, 'sync-defaults must stamp system.config_seed_fingerprint'
    # the stamped fingerprint matches the current seed fingerprint
    assert system['config_seed_fingerprint'] == _config_defaults_mod.compute_config_seed_fingerprint()


def test_sync_defaults_refreshes_stale_provisioning_fields(plan_context):
    """sync-defaults REFRESHES a stale config_seed_fingerprint even when it is already present.

    The deep-merge only adds MISSING keys, so a pre-existing (stale) stamp would
    otherwise survive untouched. The reconcile path re-stamps unconditionally, so
    a stale fingerprint is re-derived to the current seed hash.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {'system': {'provisioned_version': '0.0.0', 'config_seed_fingerprint': 'staaaale'}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    system = config['system']
    # the stale fingerprint is refreshed to the current seed fingerprint
    assert system['config_seed_fingerprint'] == _config_defaults_mod.compute_config_seed_fingerprint()
    assert system['config_seed_fingerprint'] != 'staaaale', 'the stale stamp must be refreshed, not preserved'


# =============================================================================
# Retired step-key rename migration (this plan, D2)
# =============================================================================
#
# sync-defaults migrates retired step keys to their canonicals BEFORE the
# deep-merge, across the two keyed-map step containers
# (plan.phase-6-finalize.steps and plan.phase-5-execute.verification_steps). The
# first (and currently only) rename maps both the built-in-prefixed and the bare
# legacy review-step forms — default:automated-review / automated-review — to the
# promoted bundle:skill canonical plan-marshall:automatic-review. The migration
# preserves each step's nested knob block byte-identically and its insertion
# order, drops a retired duplicate when the canonical is already present, and is
# idempotent.

_CANONICAL_REVIEW = 'plan-marshall:automatic-review'


def test_sync_defaults_migrates_retired_review_key_preserving_knob_block(plan_context):
    """default:automated-review migrates to the canonical with its knob block preserved.

    The retired key carries a populated knob block with custom values; after the
    migration the canonical carries those exact values, the retired key is gone,
    and the migration is reported in renamed[].
    """
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:automated-review': {
                            'enabled_bots': 'coderabbit',
                            'review_bot_buffer_seconds': 42,
                        },
                        'default:archive-plan': {},
                    }
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the retired key is gone and the canonical is present
    assert 'default:automated-review' not in steps
    assert 'automated-review' not in steps
    assert _CANONICAL_REVIEW in steps
    # the user's custom knob values survive byte-identically (no double step)
    canonical_params = _params_for(steps, _CANONICAL_REVIEW)
    assert canonical_params['enabled_bots'] == 'coderabbit'
    assert canonical_params['review_bot_buffer_seconds'] == 42
    # the migration is reported
    assert result['renamed_count'] == 1
    assert any('default:automated-review' in entry and _CANONICAL_REVIEW in entry for entry in result['renamed'])


def test_sync_defaults_migrates_bare_retired_review_key(plan_context):
    """The bare legacy form automated-review also migrates to the canonical."""
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'automated-review': {'enabled_bots': 'sourcery'},
                    }
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert 'automated-review' not in steps
    assert _CANONICAL_REVIEW in steps
    assert _params_for(steps, _CANONICAL_REVIEW)['enabled_bots'] == 'sourcery'
    assert result['renamed_count'] == 1


def test_sync_defaults_retired_key_migration_preserves_position(plan_context):
    """The canonical takes the retired key's insertion position (order preserved).

    The retired key sits between default:push and default:archive-plan; after
    migration the canonical occupies that same middle slot (the deep-merge only
    appends the remaining default steps AFTER the present ones).
    """
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:automated-review': {'enabled_bots': 'coderabbit'},
                        'default:archive-plan': {},
                    }
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    ordered = list(config['plan']['phase-6-finalize']['steps'])
    # the canonical sits where the retired key was — between push and archive-plan
    assert ordered.index(_CANONICAL_REVIEW) == 1
    assert ordered[0] == 'default:push'
    assert ordered[2] == 'default:archive-plan'


def test_sync_defaults_drops_retired_duplicate_when_canonical_present(plan_context):
    """A config carrying BOTH the retired and canonical keys drops the retired duplicate.

    The canonical's own knob block wins; the retired duplicate is removed so no
    double review step survives.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:automated-review': {'enabled_bots': 'RETIRED'},
                        _CANONICAL_REVIEW: {'enabled_bots': 'CANONICAL'},
                    }
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the retired duplicate is dropped; the canonical's own block wins
    assert 'default:automated-review' not in steps
    assert _params_for(steps, _CANONICAL_REVIEW)['enabled_bots'] == 'CANONICAL'
    # the drop is reported as a rename entry
    assert result['renamed_count'] == 1
    assert any('dropped duplicate' in entry for entry in result['renamed'])


def test_sync_defaults_retired_key_migration_is_idempotent(plan_context):
    """A second sync after migrating a retired key reports no further renames."""
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:automated-review': {'enabled_bots': 'coderabbit'},
                    }
                }
            }
        },
    )

    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'
    assert first['renamed_count'] == 1

    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    # the retired key is already migrated — the second run renames nothing
    assert second['renamed'] == []
    assert second['renamed_count'] == 0


def test_sync_defaults_migrates_retired_key_in_verification_steps_container(plan_context):
    """The phase-5-execute.verification_steps keyed map is also walked by the migration.

    The rename table applies to both step containers; a retired key placed in
    verification_steps is migrated exactly as in the finalize steps map, proving
    _STEP_MAP_LOCATIONS covers both.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-5-execute': {
                    'verification_steps': {
                        'default:automated-review': {'enabled_bots': 'coderabbit'},
                    }
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    assert 'default:automated-review' not in verification_steps
    assert _CANONICAL_REVIEW in verification_steps
    assert result['renamed_count'] == 1
    assert any('phase-5-execute.verification_steps' in entry for entry in result['renamed'])


def test_sync_defaults_no_renames_reported_for_clean_config(plan_context):
    """An empty marshal.json sync reports zero renames (no retired keys present)."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    assert result['renamed'] == []
    assert result['renamed_count'] == 0


# =============================================================================
# Finalize-lane materialization (this plan, D1)
# =============================================================================
#
# sync-defaults materializes an explicit `lane` on every lane-less
# `plan.phase-6-finalize.steps` entry AFTER the deep-merge and BEFORE the
# provisioning re-stamp. The fill rule is provenance-driven:
#   - a PRE-EXISTING lane-less step (not in `added`) is filled with its
#     frontmatter-class effective lane (a semantic no-op: `core` /
#     `derived-state` → `minimal`, `adversarial` / `prunable` → `auto`);
#   - a FRESHLY deep-merged default row (in `added`) that lacks a lane is filled
#     with `lane: off` (opt-in);
#   - a step already carrying an explicit `lane` is left untouched (idempotent);
#   - a pre-existing step whose frontmatter lane is unresolvable is left
#     lane-less and NOT reported.
# Scope is `plan.phase-6-finalize.steps` ONLY. Each materialized step is reported
# as an annotated dotted-path string in `materialized` / `materialized_count`.

# Frontmatter-class anchors (pinned to the real phase-6-finalize step docs):
#   default:push                        → class core       → effective minimal
#   default:pre-submission-self-review  → class adversarial → effective auto
#   default:archive-plan                → class core       → effective minimal
_CORE_STEP = 'default:push'
_ADVERSARIAL_STEP = 'default:pre-submission-self-review'


def _materialized_entry(step_id: str, lane: str) -> str:
    """Render the expected `materialized` report string for a step + fill value."""
    return f'plan.phase-6-finalize.steps.{step_id} -> lane={lane}'


def test_sync_defaults_materializes_preexisting_steps_to_effective_lane(plan_context):
    """A pre-existing lane-less core / adversarial step gets its frontmatter-class effective lane.

    `default:push` (class core) materializes to `minimal`; the pre-existing
    `default:pre-submission-self-review` (class adversarial) materializes to
    `auto`. Both are pre-existing (present in the input, not freshly merged), so
    the fill surfaces the composer's own default — a semantic no-op — never `off`.
    Both are reported in `materialized`.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {_CORE_STEP: {}, _ADVERSARIAL_STEP: {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # pre-existing core → minimal (a no-op surfacing of the class default)
    assert steps[_CORE_STEP]['lane'] == 'minimal'
    # pre-existing adversarial → auto (never off, because it pre-existed)
    assert steps[_ADVERSARIAL_STEP]['lane'] == 'auto'
    # both are reported with their annotated dotted-path fill entry
    assert _materialized_entry(_CORE_STEP, 'minimal') in result['materialized']
    assert _materialized_entry(_ADVERSARIAL_STEP, 'auto') in result['materialized']
    assert result['materialized_count'] == len(result['materialized'])


def test_sync_defaults_materializes_freshly_merged_default_step_to_off(plan_context):
    """A freshly deep-merged default step that lacks a lane is materialized to `off`.

    `default:archive-plan` is a default_on:true step absent from the sparse input
    config; the deep-merge back-fills it (its dotted path lands in `added`), so
    the materializer fills it with `lane: off` (opt-in) — NOT its core effective
    lane. This is why the D2 compose-time immunity net exists: a freshly-merged
    core floor step can carry `off`, and the composer must ignore it.
    """
    # sparse input: one pre-existing step; every other default step is fresh
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {_CORE_STEP: {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # freshly-merged default step → off (opt-in), reported
    assert steps['default:archive-plan']['lane'] == 'off'
    assert _materialized_entry('default:archive-plan', 'off') in result['materialized']
    # the pre-existing core step still materializes to its effective lane, not off
    assert steps[_CORE_STEP]['lane'] == 'minimal'


def test_sync_defaults_preserves_explicit_lane_untouched(plan_context):
    """A step carrying an explicit `lane` is preserved byte-identically and NOT reported.

    An explicit `ask` on the infra review gate and an explicit resolved tier
    (`full`) on a core step both survive the materialization pass untouched, and
    neither is reported in `materialized`.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'plan-marshall:automatic-review': {'lane': 'ask'},
                        _CORE_STEP: {'lane': 'full'},
                    }
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the explicit lanes survive untouched
    assert steps['plan-marshall:automatic-review']['lane'] == 'ask'
    assert steps[_CORE_STEP]['lane'] == 'full'
    # neither explicit-lane step is reported as materialized
    assert not any('plan-marshall:automatic-review' in entry for entry in result['materialized'])
    assert not any(_CORE_STEP in entry for entry in result['materialized'])


def test_sync_defaults_lane_materialization_is_idempotent(plan_context):
    """A second sync materializes nothing — every step already carries an explicit lane.

    The first sync fills a lane on every lane-less finalize step; the second
    observes them all explicit and reports `materialized == []`.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {_CORE_STEP: {}, _ADVERSARIAL_STEP: {}}}}},
    )

    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'
    assert first['materialized_count'] > 0

    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    assert second['materialized'] == []
    assert second['materialized_count'] == 0


def test_sync_defaults_leaves_unresolvable_frontmatter_step_lane_less(plan_context):
    """A pre-existing step whose frontmatter lane is unresolvable is left lane-less and unreported.

    An external `bundle:skill` step has no project-local source doc, so its
    frontmatter lane cannot be resolved to a concrete lattice tier. The
    materializer leaves it untouched (materializing a value it cannot resolve
    would not be a no-op) and does NOT report it.
    """
    unresolvable = 'external-bundle:custom-finalize-step'
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {unresolvable: {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the unresolvable external step is left lane-less
    assert 'lane' not in steps[unresolvable]
    # and is NOT reported in materialized
    assert not any(unresolvable in entry for entry in result['materialized'])
