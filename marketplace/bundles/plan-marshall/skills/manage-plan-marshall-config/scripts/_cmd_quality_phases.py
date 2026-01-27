"""
Quality phases command handler for plan-marshall-config.

Handles: verification, finalize (top-level pipeline sections)
"""

from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)
from _config_defaults import DEFAULT_FINALIZE_STEPS, DEFAULT_VERIFICATION_STEPS


def cmd_quality_phases(args, section: str) -> int:
    """Handle verification/finalize noun.

    Args:
        args: Parsed arguments
        section: 'verification' or 'finalize'
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    section_config = config.get(section, {})

    if args.verb == 'get':
        return success_exit({section: section_config})

    elif args.verb == 'set-max-iterations':
        value = int(args.value)
        section_config['max_iterations'] = value
        config[section] = section_config
        save_config(config)
        return success_exit({'section': section, 'max_iterations': value})

    elif args.verb == 'set-steps':
        step_names = [s.strip() for s in args.steps.split(',')]
        defaults = DEFAULT_VERIFICATION_STEPS if section == 'verification' else DEFAULT_FINALIZE_STEPS
        valid_names = {s['name'] for s in defaults}
        unknown = [n for n in step_names if n not in valid_names]
        if unknown:
            return error_exit(f'Unknown step names: {", ".join(unknown)}')
        selected = [s for s in defaults if s['name'] in step_names]
        section_config['steps'] = selected
        config[section] = section_config
        save_config(config)
        return success_exit({'section': section, 'steps': [s['name'] for s in selected]})

    return EXIT_ERROR
