"""
System, project, and plan command handlers for manage-config.

Handles: system, project, plan

Plan sub-nouns delegate to phase handlers in _cmd_quality_phases:
  phase-1-init, phase-2-refine, phase-5-execute, phase-6-finalize
"""

import json

from _cmd_quality_phases import PHASE_SECTIONS, cmd_phase
from _config_core import (
    MarshalNotInitializedError,
    _coerce_value,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)
from _config_defaults import DEFAULT_PROJECT

# Project fields whose value is a nested dict/list serialized as JSON on the
# `manage-config project set` command line. _coerce_value only handles scalar
# coercion (bool/int/str), so these fields take a json.loads path instead so a
# list/dict value round-trips through get.
_PROJECT_JSON_FIELDS = ('branch_naming',)


def read_branch_naming(config: dict) -> dict:
    """Return the canonical branch-naming block, with fail-closed default.

    The single read accessor for `project.branch_naming` consumed by the
    create-verb guard (Deliverable 2) and the workflow-allowlist structural
    test (Deliverable 3), so the fail-closed default lives in exactly one
    place. Returns the live `project.branch_naming` block when present,
    otherwise `DEFAULT_PROJECT['branch_naming']` (sourced from the constants
    fallback).

    Args:
        config: Parsed marshal.json dict.

    Returns:
        The branch-naming block: ``{'working_prefixes': [...], 'ci_allowlist': [...]}``.
    """
    result: dict = config.get('project', {}).get('branch_naming', DEFAULT_PROJECT['branch_naming'])
    return result


def cmd_system(args) -> dict:
    """Handle system noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    system_config = config.get('system', {})

    if args.sub_noun == 'retention':
        retention = system_config.get('retention', {})

        if args.verb == 'get':
            return success_exit({'retention': retention})

        elif args.verb == 'set':
            field = args.field
            value = _coerce_value(args.value)

            retention[field] = value
            system_config['retention'] = retention
            config['system'] = system_config
            save_config(config)
            return success_exit({'field': field, 'value': value})

    return error_exit('Unknown system sub-noun or verb')


def cmd_project(args) -> dict:
    """Handle project noun.

    Exposes the project-level `project.*` block in marshal.json
    (currently `default_base_branch`). On a fresh marshal.json that lacks
    the `project` block, `get` returns the value from
    :data:`DEFAULT_PROJECT` so consumers always observe the canonical
    default — mirroring the implicit-default semantics of the other
    `DEFAULT_PLAN_*` blocks.
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    project_config = config.get('project', {})

    if args.verb == 'get':
        field = args.field
        if field in project_config:
            return success_exit({'field': field, 'value': project_config[field]})
        if field in DEFAULT_PROJECT:
            return success_exit({'field': field, 'value': DEFAULT_PROJECT[field]})
        return error_exit(f"Field '{field}' not found in project config", error_type='field_not_found')

    elif args.verb == 'set':
        field = args.field
        # Nested JSON fields (e.g. branch_naming) take a json.loads path so a
        # list/dict value persists and round-trips through get; scalar fields
        # use the bool/int/str coercion.
        if field in _PROJECT_JSON_FIELDS:
            try:
                value = json.loads(args.value)
            except json.JSONDecodeError as e:
                return error_exit(
                    f"Field '{field}' expects a JSON value: {e}",
                    error_type='invalid_json',
                )
        else:
            value = _coerce_value(args.value)

        project_config[field] = value
        config['project'] = project_config
        save_config(config)
        return success_exit({'field': field, 'value': value})

    return error_exit('Unknown project verb')


def cmd_plan(args) -> dict:
    """Handle plan noun.

    Delegates to phase handlers for phase-based sub-nouns.
    """
    sub_noun = args.sub_noun

    # Phase-based sub-nouns delegate to cmd_phase
    if sub_noun in PHASE_SECTIONS:
        return cmd_phase(args, sub_noun)

    return error_exit('Unknown plan sub-noun')
