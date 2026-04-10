"""
CI command handlers for manage-config.

Handles: ci noun for reading/writing CI provider configuration.

Storage split:
- marshal.json providers[] (shared via git): provider, repo_url, detected_at on matching entry
- run-configuration.json (local): authenticated_tools, verified_at

CI data is stored as metadata on the matching provider entry in config['providers'].
The CI provider is identified by auth_type=system and skill_name starting with
'workflow-integration-gi' (covers github/gitlab).
"""

from _config_core import (
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


_CI_PROVIDER_SKILLS = frozenset({
    'workflow-integration-github',
    'workflow-integration-gitlab',
})


def _find_ci_provider(providers: list[dict]) -> dict | None:
    """Find the CI provider entry from the providers list.

    CI providers have auth_type=system and skill_name matching a known
    CI provider (workflow-integration-github or workflow-integration-gitlab).

    Returns:
        The matching provider dict, or None if not found.
    """
    for p in providers:
        if (
            p.get('auth_type') == 'system'
            and p.get('skill_name', '') in _CI_PROVIDER_SKILLS
        ):
            return p
    return None


def _get_ci_data(providers: list[dict]) -> dict:
    """Extract CI-relevant data from the providers list.

    Returns a dict with provider, repo_url, detected_at keys
    (matching the old ci section shape for backward-compatible output).
    """
    entry = _find_ci_provider(providers)
    if entry is None:
        return {}
    return {
        'provider': entry.get('provider', 'unknown'),
        'repo_url': entry.get('repo_url'),
        'detected_at': entry.get('detected_at'),
    }


def _handle_get(providers: list[dict]) -> dict:
    """Handle 'get' verb."""
    ci_data = _get_ci_data(providers)
    return success_exit({'ci': ci_data})


def _handle_get_provider(providers: list[dict]) -> dict:
    """Handle 'get-provider' verb."""
    ci_data = _get_ci_data(providers)
    return success_exit(
        {
            'provider': ci_data.get('provider', 'unknown'),
            'repo_url': ci_data.get('repo_url'),
            'confidence': 'persisted' if ci_data.get('detected_at') else 'unknown',
        }
    )


def _handle_set_provider(args, config: dict, providers: list[dict]) -> dict:
    """Handle 'set-provider' verb."""
    entry = _find_ci_provider(providers)
    if entry is None:
        return error_exit('No CI provider found in providers list. Run discover-and-persist first.')

    entry['provider'] = args.provider
    entry['repo_url'] = args.repo_url
    entry['detected_at'] = _get_timestamp()
    save_config(config)
    return success_exit({'provider': args.provider, 'repo_url': args.repo_url})


def _handle_set_tools(args) -> dict:
    """Handle 'set-tools' verb."""
    run_config = load_run_config()
    run_ci = run_config.get('ci', {})
    tools = [t.strip() for t in args.tools.split(',') if t.strip()]
    run_ci['authenticated_tools'] = tools
    run_ci['verified_at'] = _get_timestamp()
    run_config['ci'] = run_ci
    save_run_config(run_config)
    return success_exit({'authenticated_tools': tools})


def _handle_get_tools() -> dict:
    """Handle 'get-tools' verb."""
    run_config = load_run_config()
    run_ci = run_config.get('ci', {})
    return success_exit({'authenticated_tools': run_ci.get('authenticated_tools', [])})


def _handle_persist(args, config: dict, providers: list[dict]) -> dict:
    """Handle 'persist' verb - full CI config persistence."""
    entry = _find_ci_provider(providers)
    if entry is None:
        return error_exit('No CI provider found in providers list. Run discover-and-persist first.')

    entry['provider'] = args.provider
    entry['repo_url'] = args.repo_url
    entry['detected_at'] = _get_timestamp()

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

    return success_exit({'provider': args.provider, 'repo_url': args.repo_url})


def cmd_ci(args) -> dict:
    """Handle ci noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    providers = config.get('providers', [])

    # Handlers that need only providers list
    simple_handlers = {
        'get': lambda: _handle_get(providers),
        'get-provider': lambda: _handle_get_provider(providers),
        'set-provider': lambda: _handle_set_provider(args, config, providers),
        'set-tools': lambda: _handle_set_tools(args),
        'get-tools': lambda: _handle_get_tools(),
        'persist': lambda: _handle_persist(args, config, providers),
    }
    handler = simple_handlers.get(args.verb)
    if handler:
        return handler()

    return error_exit('Unknown ci verb')
