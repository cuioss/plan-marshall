"""
System and plan command handlers for plan-marshall-config.

Handles: system, plan
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
    """Handle plan noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    plan_config = config.get('plan', {})

    if args.sub_noun == 'defaults':
        defaults = plan_config.get('defaults', {})

        if args.verb == 'list':
            return success_exit({'defaults': defaults})

        elif args.verb == 'get':
            field = getattr(args, 'field', None)
            if not field:
                # No field specified - return all defaults
                return success_exit({'defaults': defaults})
            if field not in defaults:
                return error_exit(f'Unknown default field: {field}')
            return success_exit({'field': field, 'value': defaults[field]})

        elif args.verb == 'set':
            field = args.field
            value = args.value

            # Type coercion
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False

            defaults[field] = value
            plan_config['defaults'] = defaults
            config['plan'] = plan_config
            save_config(config)
            return success_exit({'field': field, 'value': value})

    return EXIT_ERROR
