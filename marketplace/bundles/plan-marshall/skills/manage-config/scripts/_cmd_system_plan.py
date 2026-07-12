# SPDX-License-Identifier: FSL-1.1-ALv2
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
from _config_defaults import (
    DEFAULT_PROJECT,
    pr_compact_rides_existing_pr,
    validate_pr_compact_max_changed_files,
    validate_pr_strategy,
)

# Project fields whose value is a list serialized as JSON on the
# `manage-config project set` command line. _coerce_value only handles scalar
# coercion (bool/int/str), so these fields take a json.loads path instead so a
# list value round-trips through get.
_PROJECT_JSON_FIELDS = ('working_prefixes',)


def cmd_system(args) -> dict:
    """Handle system noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    system_config = config.get('system', {})
    if not isinstance(system_config, dict):
        return error_exit(
            f"system block in marshal.json is not a dict, got "
            f"{type(system_config).__name__}",
            error_type='invalid_type',
        )

    if args.sub_noun == 'retention':
        retention = system_config.get('retention', {})

        if args.verb == 'get':
            return success_exit({'retention': retention})

        elif args.verb == 'set':
            field = args.field
            value = _coerce_value(args.value)

            if not isinstance(retention, dict):
                return error_exit(
                    f"system.retention block in marshal.json is not a dict, got "
                    f"{type(retention).__name__}",
                    error_type='invalid_type',
                )
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
    if not isinstance(project_config, dict):
        return error_exit(
            f"project block in marshal.json is not a dict, got "
            f"{type(project_config).__name__}",
            error_type='invalid_type',
        )

    if args.verb == 'get':
        field = args.field
        if field in project_config:
            return success_exit({'field': field, 'value': project_config[field]})
        if field in DEFAULT_PROJECT:
            return success_exit({'field': field, 'value': DEFAULT_PROJECT[field]})
        return error_exit(f"Field '{field}' not found in project config", error_type='field_not_found')

    elif args.verb == 'set':
        field = args.field
        # List-valued JSON fields (working_prefixes) take a json.loads path so a
        # list value persists and round-trips through get; scalar fields use the
        # bool/int/str coercion.
        if field in _PROJECT_JSON_FIELDS:
            try:
                value = json.loads(args.value)
            except json.JSONDecodeError as e:
                return error_exit(
                    f"Field '{field}' expects a JSON value: {e}",
                    error_type='invalid_json',
                )
            # Validate the parsed shape at this system boundary. A wrong-typed
            # value would persist silently and crash downstream readers.
            # working_prefixes is a flat JSON array of strings.
            if not isinstance(value, list):
                return error_exit(
                    f"Field '{field}' expects a JSON array, got {type(value).__name__}",
                    error_type='invalid_type',
                )
            if not all(isinstance(item, str) for item in value):
                return error_exit(
                    f"Field '{field}' must be a JSON array of strings",
                    error_type='invalid_type',
                )
        else:
            value = _coerce_value(args.value)

        # Validate the two PR-batching knobs at this system boundary so an
        # invalid value returns a status: error rather than persisting garbage.
        if field == 'pr_strategy':
            try:
                validate_pr_strategy(value)
            except ValueError as e:
                return error_exit(str(e), error_type='invalid_value')
        elif field == 'pr_compact_max_changed_files':
            try:
                validate_pr_compact_max_changed_files(value)
            except ValueError as e:
                return error_exit(str(e), error_type='invalid_value')

        project_config[field] = value
        config['project'] = project_config
        save_config(config)
        return success_exit({'field': field, 'value': value})

    elif args.verb == 'pr-decision':
        # Resolve the two knobs (falling back to DEFAULT_PROJECT when absent,
        # exactly like `get`) and return a ride|split verdict. `max` is the
        # resolved compact ceiling; `threshold` is the first changed-file count
        # that forces a split under the compact strategy (max + 1).
        changed_files = args.changed_files
        if changed_files < 0:
            return error_exit(
                f"--changed-files must be an int >= 0, got {changed_files}",
                error_type='invalid_value',
            )
        strategy = project_config.get('pr_strategy', DEFAULT_PROJECT['pr_strategy'])
        max_changed_files = project_config.get(
            'pr_compact_max_changed_files',
            DEFAULT_PROJECT['pr_compact_max_changed_files'],
        )
        rides = pr_compact_rides_existing_pr(strategy, changed_files, max_changed_files)
        return success_exit({
            'decision': 'ride' if rides else 'split',
            'strategy': strategy,
            'changed_files': changed_files,
            'max': max_changed_files,
            'threshold': max_changed_files + 1,
        })

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
