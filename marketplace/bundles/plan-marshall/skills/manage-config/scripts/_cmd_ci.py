"""
CI command handlers for manage-config.

Handles: ci noun for reading/writing CI provider configuration.

Storage split:
- marshal.json (shared via git): provider, repo_url, detected_at
- run-configuration.json (local): authenticated_tools, verified_at
"""

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
    from file_ops import now_utc_iso  # type: ignore[import-not-found]

    return now_utc_iso()


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


def _handle_persist(args, config: dict, ci_config: dict) -> int:
    """Handle 'persist' verb - full CI config persistence."""
    ci_config['provider'] = args.provider
    ci_config['repo_url'] = args.repo_url
    ci_config['detected_at'] = _get_timestamp()

    # Remove legacy ci.commands if present (commands are resolved by ci.py router)
    ci_config.pop('commands', None)

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
        {'provider': args.provider, 'repo_url': args.repo_url}
    )


def cmd_ci(args) -> int:
    """Handle ci noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    ci_config = config.get('ci', {})

    # Handlers that need only ci_config
    simple_handlers = {
        'get': lambda: _handle_get(ci_config),
        'get-provider': lambda: _handle_get_provider(ci_config),
        'set-provider': lambda: _handle_set_provider(args, config, ci_config),
        'set-tools': lambda: _handle_set_tools(args),
        'get-tools': lambda: _handle_get_tools(),
        'persist': lambda: _handle_persist(args, config, ci_config),
    }
    handler = simple_handlers.get(args.verb)
    if handler:
        return handler()

    return EXIT_ERROR
