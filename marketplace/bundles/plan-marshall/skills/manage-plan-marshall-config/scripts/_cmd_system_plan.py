"""
System and plan command handlers for plan-marshall-config.

Handles: system, plan

Plan sub-nouns delegate to phase handlers in _cmd_quality_phases:
  phase-1-init, phase-2-refine, phase-5-execute, phase-6-verify, phase-7-finalize
"""

from _cmd_quality_phases import PHASE_SECTIONS, cmd_phase
from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)


def cmd_system(args) -> int:
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
            value = args.value

            # Type coercion
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)

            retention[field] = value
            system_config['retention'] = retention
            config['system'] = system_config
            save_config(config)
            return success_exit({'field': field, 'value': value})

    return EXIT_ERROR


def cmd_plan(args) -> int:
    """Handle plan noun.

    Delegates to phase handlers for phase-based sub-nouns.
    """
    sub_noun = args.sub_noun

    # Phase-based sub-nouns delegate to cmd_phase
    if sub_noun in PHASE_SECTIONS:
        return cmd_phase(args, sub_noun)

    return EXIT_ERROR
