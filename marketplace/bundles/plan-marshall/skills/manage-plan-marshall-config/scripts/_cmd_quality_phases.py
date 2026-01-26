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

    return EXIT_ERROR
