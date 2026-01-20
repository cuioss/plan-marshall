"""
CI command handlers for plan-marshall-config.

Handles: ci noun for reading/writing CI provider configuration.

Storage split:
- marshal.json (shared via git): provider, repo_url, detected_at
- run-configuration.json (local): authenticated_tools, verified_at
"""

import json
from datetime import UTC, datetime

from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    error_exit,
    load_config,
    load_run_config,
    require_initialized,
    save_config,
    save_run_config,
    success_exit,
)


def _get_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _handle_get(ci_config: dict) -> int:
    """Handle 'get' verb."""
    return success_exit({'ci': ci_config})


def _handle_get_provider(ci_config: dict) -> int:
    """Handle 'get-provider' verb."""
    return success_exit(
        {
            'provider': ci_config.get('provider', 'unknown'),
            'repo_url': ci_config.get('repo_url'),
            'confidence': 'persisted' if ci_config.get('detected_at') else 'unknown',
        }
    )


def _handle_set_provider(args, config: dict, ci_config: dict) -> int:
    """Handle 'set-provider' verb."""
    ci_config['provider'] = args.provider
    ci_config['repo_url'] = args.repo_url
    ci_config['detected_at'] = _get_timestamp()
    config['ci'] = ci_config
    save_config(config)
    return success_exit({'provider': args.provider, 'repo_url': args.repo_url})


def _handle_set_tools(args) -> int:
    """Handle 'set-tools' verb."""
    run_config = load_run_config()
    run_ci = run_config.get('ci', {})
    tools = [t.strip() for t in args.tools.split(',') if t.strip()]
    run_ci['authenticated_tools'] = tools
    run_ci['verified_at'] = _get_timestamp()
    run_config['ci'] = run_ci
    save_run_config(run_config)
    return success_exit({'authenticated_tools': tools})


def _handle_get_tools() -> int:
    """Handle 'get-tools' verb."""
    run_config = load_run_config()
    run_ci = run_config.get('ci', {})
    return success_exit({'authenticated_tools': run_ci.get('authenticated_tools', [])})


def _handle_get_command(args, ci_config: dict) -> int:
    """Handle 'get-command' verb - get single CI command by name."""
    commands = ci_config.get('commands', {})
    command_name = args.name

    if command_name not in commands:
        available = ', '.join(sorted(commands.keys()))
        return error_exit(f'Unknown command: {command_name}. Available: {available}')

    print('status: success')
    print(f'name: {command_name}')
    print(f'command: {commands[command_name]}')
    return 0


def _handle_persist(args, config: dict, ci_config: dict) -> int:
    """Handle 'persist' verb - full CI config persistence."""
    ci_config['provider'] = args.provider
    ci_config['repo_url'] = args.repo_url
    ci_config['detected_at'] = _get_timestamp()

    # Parse commands JSON if provided
    if args.commands:
        try:
            ci_config['commands'] = json.loads(args.commands)
        except json.JSONDecodeError as e:
            return error_exit(f'Invalid JSON for --commands: {e}')
    else:
        ci_config['commands'] = {}

    config['ci'] = ci_config
    save_config(config)

    # Also update run-configuration.json if tools provided
    if args.tools:
        run_config = load_run_config()
        run_ci = run_config.get('ci', {})
        tools = [t.strip() for t in args.tools.split(',') if t.strip()]
        run_ci['authenticated_tools'] = tools
        run_ci['verified_at'] = _get_timestamp()
        if args.git_present is not None:
            run_ci['git_present'] = args.git_present.lower() == 'true'
        run_config['ci'] = run_ci
        save_run_config(run_config)

    return success_exit(
        {'provider': args.provider, 'repo_url': args.repo_url, 'commands_count': len(ci_config.get('commands', {}))}
    )


def cmd_ci(args) -> int:
    """Handle ci noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    ci_config = config.get('ci', {})

    if args.verb == 'get':
        return _handle_get(ci_config)
    elif args.verb == 'get-provider':
        return _handle_get_provider(ci_config)
    elif args.verb == 'set-provider':
        return _handle_set_provider(args, config, ci_config)
    elif args.verb == 'set-tools':
        return _handle_set_tools(args)
    elif args.verb == 'get-tools':
        return _handle_get_tools()
    elif args.verb == 'get-command':
        return _handle_get_command(args, ci_config)
    elif args.verb == 'persist':
        return _handle_persist(args, config, ci_config)

    return EXIT_ERROR
