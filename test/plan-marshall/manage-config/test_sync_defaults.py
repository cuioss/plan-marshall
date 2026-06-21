#!/usr/bin/env python3
"""Tests for the sync-defaults command in manage-config.

Covers the non-destructive deep-merge contract:
- empty marshal.json gains all defaults
- user-set keys are preserved while missing ones are added
- deeply-nested missing sub-keys are added
- lists are treated as atomic (user's list survives)
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

cmd_sync_defaults = _sync_mod.cmd_sync_defaults


# =============================================================================
# LIST serial-form helpers
# =============================================================================
#
# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize on disk as the canonical LIST form: a JSON array whose elements are
# bare strings (ownerless steps) or single-key objects `{step_id: {params}}`
# (param-bearing steps). The default seed is therefore a LIST, which the
# deep-merge treats as an ATOMIC value — it is copied wholesale when the key is
# absent and preserved verbatim when present (no per-step dict recursion).


def _step_ids(steps_list: list) -> list:
    """Return the ordered step-id list from a LIST-form steps array."""
    ids = []
    for element in steps_list:
        if isinstance(element, str):
            ids.append(element)
        elif isinstance(element, dict) and len(element) == 1:
            ids.append(next(iter(element)))
    return ids


def _params_for(steps_list: list, step_id: str):
    """Return a step's params from a LIST-form steps array.

    Returns the nested param dict for a param-bearing single-key object, or
    ``None`` for an ownerless bare-string element. Raises ``KeyError`` when the
    step id is absent.
    """
    for element in steps_list:
        if isinstance(element, str) and element == step_id:
            return None
        if isinstance(element, dict) and len(element) == 1 and step_id in element:
            return element[step_id]
    raise KeyError(step_id)


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
    # the steps default is the LIST serial form; auto_rebase_threshold nests in
    # the single-key object for default:branch-cleanup
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, list)
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert config['project']['default_base_branch'] == 'main'
    # Top-level default keys are added
    assert 'plan' in result['added']
    assert 'project' in result['added']


def test_sync_defaults_preserves_user_set_list_steps_atomically(plan_context):
    """A user-set LIST-form steps value survives the sync verbatim (lists are atomic).

    The steps default is now the LIST serial form, which the deep-merge treats as
    an ATOMIC value: a present `steps` key is preserved verbatim with NO per-step
    recursion. A user who pinned pr_merge_strategy via a single-key object keeps
    that override, and the default list does NOT overwrite or deep-merge missing
    siblings into it.
    """
    # user pinned pr_merge_strategy via the LIST form's single-key object
    user_steps = [{'default:branch-cleanup': {'pr_merge_strategy': 'merge'}}]
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': user_steps}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the user's LIST is preserved verbatim — atomic, no per-step merge
    assert steps == user_steps
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['pr_merge_strategy'] == 'merge'
    # no missing sibling is deep-merged into the user's single-key object
    assert 'auto_rebase_threshold' not in branch_cleanup
    # the atomic steps key is not reported as added (it was present)
    assert 'plan.phase-6-finalize.steps' not in result['added']
    # and no per-step dotted path is reported (no recursion into the list)
    assert not any(p.startswith('plan.phase-6-finalize.steps.') for p in result['added'])


def test_sync_defaults_preserves_user_set_true_in_list_form(plan_context):
    """A user-set True survives even though the default value is False (LIST atomic).

    final_merge_without_asking is a nested param of default:branch-cleanup in the
    LIST form. The deep-merge preserves the present `steps` key (the whole list)
    verbatim, so an explicit True survives the False default and the list is not
    reported as added.
    """
    # user explicitly opted into merge-without-asking (default is False) via the LIST form
    user_steps = [{'default:branch-cleanup': {'final_merge_without_asking': True}}]
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': user_steps}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the user's LIST is preserved verbatim — the True override survives
    assert steps == user_steps
    assert _params_for(steps, 'default:branch-cleanup')['final_merge_without_asking'] is True
    # the present atomic steps key is not re-added
    assert 'plan.phase-6-finalize.steps' not in result['added']


def test_sync_defaults_does_not_deep_merge_into_list_steps(plan_context):
    """The default LIST does NOT deep-merge missing siblings into a present user LIST.

    Under the LIST atomic contract, a user `steps` list that omits a sibling param
    keeps it omitted — the merge never recurses into the list to back-fill
    per-step params. This pins the behavioral consequence of the serial-form
    change (the former keyed-map deep-merge of per-step params is gone).
    """
    # the branch-cleanup step is present (LIST form) but lacks auto_rebase_threshold
    user_steps = [{'default:branch-cleanup': {'pr_merge_strategy': 'squash'}}]
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': user_steps}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['pr_merge_strategy'] == 'squash'
    # the missing sibling is NOT added — the list is atomic, no per-step recursion
    assert 'auto_rebase_threshold' not in branch_cleanup
    assert not any(p.startswith('plan.phase-6-finalize.steps.') for p in result['added'])


def test_sync_defaults_pruned_list_steps_are_atomic(plan_context):
    """A user's pruned single-element steps list is kept verbatim (lists are atomic).

    The schema default is now the LIST serial form, and the deep-merge treats a
    user-supplied list value as atomic (no recursion), so a user who pruned steps
    to a single bare-string element keeps it verbatim and the default list does
    not overwrite it.
    """
    # user pruned the finalize steps to a single bare-string element
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': ['default:commit-push']}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # list preserved verbatim (atomic — not merged against the default list)
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['plan']['phase-6-finalize']['steps'] == ['default:commit-push']
    assert 'plan.phase-6-finalize.steps' not in result['added']


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
# LIST serial-form back-fill on sync (steps / verification_steps copied atomically)
# =============================================================================
#
# The steps / verification_steps defaults are now the LIST serial form (bare
# strings for ownerless steps, single-key objects for param-bearing steps). The
# deep-merge treats a missing `steps` / `verification_steps` key as an atomic
# back-fill: the whole default LIST is copied wholesale and reported as a single
# added dotted path, with NO per-step recursion. Ownerless steps land as bare
# strings (never a {step_id: null} / {step_id: {}} object); param-owning steps
# land as their single-key object.


def test_sync_defaults_backfills_verification_steps_as_list_of_bare_strings(plan_context):
    """Syncing an empty marshal.json back-fills verification_steps as a LIST of bare strings."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    # the whole LIST is copied atomically; ownerless verify steps are bare strings
    assert isinstance(verification_steps, list)
    assert all(isinstance(element, str) for element in verification_steps), (
        f'ownerless verify steps must be bare strings, got {verification_steps!r}'
    )
    # the LIST is never split into per-step dotted paths (atomic, no recursion);
    # when the whole `plan` block is absent it is added as the top-level `plan`
    # path, so no per-step verification_steps path is ever reported
    assert not any(
        p.startswith('plan.phase-5-execute.verification_steps.') for p in result['added']
    )


def test_sync_defaults_backfills_finalize_steps_as_list_serial_form(plan_context):
    """Syncing an empty marshal.json back-fills finalize steps as the LIST serial form.

    Param-owning steps (sonar-roundtrip / automated-review / branch-cleanup /
    finalize-step-simplify) land as single-key objects with a non-empty param
    dict; the remaining ownerless steps land as bare strings.
    """
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, list)

    param_owning = {
        'default:sonar-roundtrip',
        'default:automated-review',
        'default:branch-cleanup',
        # default:finalize-step-simplify owns the folded `simplify` run-at-all gate
        'default:finalize-step-simplify',
    }
    for element in steps:
        if isinstance(element, dict):
            assert len(element) == 1, 'a param-bearing element must be a single-key object'
            step_id, params = next(iter(element.items()))
            assert step_id in param_owning, (
                f'only param-owning steps may be single-key objects; got {step_id!r}'
            )
            assert isinstance(params, dict) and params, (
                f'param-owning step {step_id!r} must carry a non-empty nested dict'
            )
        else:
            assert isinstance(element, str), 'an ownerless element must be a bare string'
            assert element not in param_owning, (
                f'param-owning step {element!r} must be a single-key object, not a bare string'
            )
    # the LIST is never split into per-step dotted paths (atomic, no recursion);
    # when the whole `plan` block is absent it is added as the top-level `plan`
    # path, so no per-step steps path is ever reported
    assert not any(p.startswith('plan.phase-6-finalize.steps.') for p in result['added'])


def test_sync_defaults_preserves_present_steps_list_untouched(plan_context):
    """A present `steps` LIST is preserved verbatim (present-key, atomic, no rewrite).

    The deep-merge preserves a present key by key-existence (no recursion into the
    list), so a user-supplied LIST survives the sync verbatim and the default
    LIST does not overwrite it.
    """
    # a marshal.json whose finalize steps already carry a pruned LIST
    user_steps = ['default:create-pr']
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': user_steps}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the pre-existing LIST is preserved verbatim (present-key, no rewrite)
    assert steps == user_steps
    # the present atomic steps key is NOT reported as added
    assert 'plan.phase-6-finalize.steps' not in result['added']


def test_sync_defaults_is_idempotent_against_list_form_steps(plan_context):
    """A second sync adds nothing — the LIST-form back-fill is idempotent.

    The first sync copies the atomic default LIST; the second observes the
    `steps` / `verification_steps` keys already present and re-adds nothing,
    proving the merge is stable against the LIST form it just wrote.
    """
    _write_marshal(plan_context.fixture_dir, {})
    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'

    # second run observes the back-filled LIST values and adds nothing
    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    assert second['added'] == []
    assert second['added_count'] == 0
    # the verify steps remain the LIST of bare strings after the idempotent re-sync
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    assert isinstance(verification_steps, list)
    assert all(isinstance(element, str) for element in verification_steps)
