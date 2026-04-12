#!/usr/bin/env python3
"""
CI health verification script for detecting CI providers and verifying tool availability.

Subcommands:
    detect      Detect CI provider from repository configuration
    verify      Verify CLI tools are installed and authenticated
    status      Full health check (detect + verify)
    persist     Detect and persist CI configuration to marshal.json

Usage:
    python3 ci-health.py detect
    python3 ci-health.py verify [--tool TOOL]
    python3 ci-health.py status
    python3 ci-health.py persist

Output (JSON format):
    All subcommands return JSON with status field.
"""

import argparse
import re
from pathlib import Path

from ci_base import run_cli  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Tool definitions: {tool: requires_auth}
# Note: python3 not checked - if it wasn't available, this script couldn't run
TOOLS = {
    'git': False,
    'gh': True,
    'glab': True,
}

def _derive_provider_key(skill_name: str) -> str | None:
    """Derive provider key from skill_name dynamically.

    Pattern: 'plan-marshall:workflow-integration-{provider}' -> '{provider}'
    Also handles unprefixed: 'workflow-integration-{provider}' -> '{provider}'
    """
    name = skill_name.split(':')[-1] if ':' in skill_name else skill_name
    prefix = 'workflow-integration-'
    if name.startswith(prefix):
        return name[len(prefix):]
    return None


def _discover_provider_tools() -> dict[str, str | None]:
    """Build provider-to-tool mapping from CI category providers.

    Scans PYTHONPATH for *_provider.py modules with category 'ci'
    and derives the tool name from each provider's verify_command.

    Returns:
        Dict mapping provider name to CLI tool name.
    """
    from _list_providers import find_full_providers_by_category  # type: ignore[import-not-found]

    ci_providers = find_full_providers_by_category('ci')
    mapping: dict[str, str | None] = {'unknown': None}

    for p in ci_providers:
        provider_key = _derive_provider_key(p.get('skill_name', ''))
        if not provider_key:
            continue
        verify_cmd = p.get('verify_command', '')
        if verify_cmd:
            import shlex
            tool = shlex.split(verify_cmd)[0]
            mapping[provider_key] = tool

    return mapping


# Provider to required tool mapping (resolved at module load)
PROVIDER_TOOLS = _discover_provider_tools()


def run_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Delegates to ci_base.run_cli for the actual execution.
    Falls back to subprocess for cwd support (run_cli doesn't accept cwd).
    """
    if cwd is not None:
        import subprocess

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=10)
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return 127, '', f'Command not found: {cmd[0]}'
        except subprocess.TimeoutExpired:
            return 124, '', 'Command timed out'
        except Exception as e:
            return 1, '', str(e)
    return run_cli(cmd[0], cmd[1:], timeout=10, not_found_msg=f'Command not found: {cmd[0]}')


def parse_version(output: str) -> str | None:
    """Extract version string from command output."""
    # Common patterns: "git version 2.43.0", "gh version 2.45.0", "Python 3.12.0"
    patterns = [
        r'version\s+(\d+\.\d+(?:\.\d+)?)',
        r'Python\s+(\d+\.\d+(?:\.\d+)?)',
        r'(\d+\.\d+\.\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    return None


def verify_tool(tool: str) -> dict:
    """
    Verify a tool is installed and authenticated.

    Returns: {"installed": bool, "authenticated": bool, "version": str | None}
    """
    # Check installed
    returncode, stdout, stderr = run_command([tool, '--version'])
    if returncode != 0:
        return {'installed': False, 'authenticated': False, 'version': None}

    version = parse_version(stdout + stderr)

    # Check authenticated (if applicable)
    requires_auth = TOOLS.get(tool, False)
    if requires_auth:
        auth_returncode, _, _ = run_command([tool, 'auth', 'status'])
        authenticated = auth_returncode == 0
    else:
        authenticated = True  # No auth needed

    return {'installed': True, 'authenticated': authenticated, 'version': version}


def _discover_detection_patterns() -> list[dict]:
    """Build detection patterns from CI provider declarations.

    Scans PYTHONPATH for *_provider.py modules with category 'ci'
    and collects their 'detection' dicts alongside the derived
    provider key.

    Returns:
        List of dicts with 'provider_key' and detection fields
        (url_patterns, directory_markers, enterprise_patterns).
    """
    from _list_providers import find_full_providers_by_category  # type: ignore[import-not-found]

    ci_providers = find_full_providers_by_category('ci')
    patterns: list[dict] = []

    for p in ci_providers:
        provider_key = _derive_provider_key(p.get('skill_name', ''))
        detection = p.get('detection', {})
        if not provider_key or not detection:
            continue
        patterns.append({
            'provider_key': provider_key,
            'url_patterns': detection.get('url_patterns', []),
            'directory_markers': detection.get('directory_markers', []),
            'enterprise_patterns': detection.get('enterprise_patterns', []),
        })

    return patterns


# Detection patterns resolved at module load
DETECTION_PATTERNS = _discover_detection_patterns()


def _match_url(repo_url: str, patterns: list[dict]) -> dict | None:
    """Match a repo URL against provider detection patterns.

    Checks url_patterns first, then enterprise_patterns.

    Returns:
        Matching pattern dict, or None.
    """
    url_lower = repo_url.lower()
    for p in patterns:
        for url_pat in p['url_patterns']:
            if re.search(url_pat, url_lower):
                return p
        for ent_pat in p.get('enterprise_patterns', []):
            if re.search(ent_pat, url_lower):
                return p
    return None


def _match_directory(check_path: Path, patterns: list[dict]) -> dict | None:
    """Match directory markers against the filesystem.

    Returns:
        First matching pattern dict, or None.
    """
    for p in patterns:
        for marker in p['directory_markers']:
            if (check_path / marker).exists():
                return p
    return None


def detect_provider(cwd: str | None = None) -> dict:
    """
    Detect CI provider from repository configuration.

    Uses detection patterns declared by CI providers (via find_by_category).
    No hardcoded provider knowledge — patterns come from *_provider.py files.

    Returns: {"provider": str, "repo_url": str | None, "confidence": str}
    """
    check_path = Path(cwd) if cwd else Path.cwd()

    # Get remote URL
    returncode, stdout, _ = run_command(['git', 'remote', 'get-url', 'origin'], cwd=cwd)
    if returncode != 0:
        # No remote URL — fall back to directory markers
        match = _match_directory(check_path, DETECTION_PATTERNS)
        if match:
            return {'provider': match['provider_key'], 'repo_url': None, 'confidence': 'medium'}
        return {'provider': 'unknown', 'repo_url': None, 'confidence': 'none'}

    repo_url = stdout.strip()

    # Check URL patterns (including enterprise patterns)
    match = _match_url(repo_url, DETECTION_PATTERNS)
    if match:
        return {'provider': match['provider_key'], 'repo_url': repo_url, 'confidence': 'high'}

    # Fall back to directory markers
    match = _match_directory(check_path, DETECTION_PATTERNS)
    if match:
        return {'provider': match['provider_key'], 'repo_url': repo_url, 'confidence': 'medium'}

    return {'provider': 'unknown', 'repo_url': repo_url, 'confidence': 'none'}


def get_required_ci_tool(provider: str) -> str | None:
    """Return required CI CLI tool for provider."""
    return PROVIDER_TOOLS.get(provider)


def determine_overall_health(provider: str, tools: dict) -> str:
    """Determine overall health status."""
    required_tool = get_required_ci_tool(provider)

    if provider == 'unknown':
        return 'unknown'

    if required_tool is None:
        return 'healthy'

    tool_status = tools.get(required_tool, {})
    if not tool_status.get('installed', False):
        return 'degraded'
    if not tool_status.get('authenticated', False):
        return 'degraded'

    return 'healthy'


def cmd_detect(args: argparse.Namespace) -> dict:
    """Handle the 'detect' subcommand."""
    result = detect_provider()
    return {
        'status': 'success',
        'provider': result['provider'],
        'repo_url': result['repo_url'],
        'confidence': result['confidence'],
    }


def cmd_verify(args: argparse.Namespace) -> dict:
    """Handle the 'verify' subcommand."""
    if args.tool:
        # Verify specific tool
        if args.tool not in TOOLS:
            return {'status': 'error', 'error': f'Unknown tool: {args.tool}', 'known_tools': list(TOOLS.keys())}
        tool_result = verify_tool(args.tool)
        return {
            'status': 'success',
            'tools': {args.tool: tool_result},
            'all_required_available': tool_result['installed'] and tool_result['authenticated'],
        }
    else:
        # Verify all tools
        tools_result = {}
        all_available = True
        for tool in TOOLS:
            tools_result[tool] = verify_tool(tool)
            if TOOLS[tool]:  # Only check auth-required tools for "all available"
                if not tools_result[tool]['installed'] or not tools_result[tool]['authenticated']:
                    all_available = False

        return {
            'status': 'success',
            'tools': tools_result,
            'all_required_available': all_available,
        }


def cmd_status(args: argparse.Namespace) -> dict:
    """Handle the 'status' subcommand."""
    # Detect provider
    provider_result = detect_provider()

    # Verify all tools
    tools_result = {}
    for tool in TOOLS:
        tools_result[tool] = verify_tool(tool)

    # Determine required tool and readiness
    required_tool = get_required_ci_tool(provider_result['provider'])
    if required_tool:
        tool_status = tools_result.get(required_tool, {})
        required_tool_ready = tool_status.get('installed', False) and tool_status.get('authenticated', False)
    else:
        required_tool_ready = True  # No required tool means ready

    # Determine overall health
    overall = determine_overall_health(provider_result['provider'], tools_result)

    return {
        'status': 'success',
        'provider': {
            'name': provider_result['provider'],
            'repo_url': provider_result['repo_url'],
            'confidence': provider_result['confidence'],
        },
        'tools': tools_result,
        'required_tool': required_tool,
        'required_tool_ready': required_tool_ready,
        'overall': overall,
    }


def _load_ci_modules():
    """Lazy-load config modules (PYTHONPATH set by executor)."""
    from _config_core import load_config, load_run_config, save_config, save_run_config  # type: ignore[import-not-found]  # noqa: I001
    return load_config, save_config, load_run_config, save_run_config


def cmd_ci_get(args: argparse.Namespace) -> dict:
    """Handle 'ci-get' subcommand — read config['ci']."""
    load_config, _, _, _ = _load_ci_modules()
    import os
    if hasattr(args, 'plan_dir'):
        os.environ['PLAN_BASE_DIR'] = str(args.plan_dir)
    config = load_config()
    ci_data = config.get('ci', {})
    return {'status': 'success', 'ci': ci_data}


def cmd_ci_get_provider(args: argparse.Namespace) -> dict:
    """Handle 'ci-get-provider' subcommand — read config['ci']['provider']."""
    load_config, _, _, _ = _load_ci_modules()
    import os
    if hasattr(args, 'plan_dir'):
        os.environ['PLAN_BASE_DIR'] = str(args.plan_dir)
    config = load_config()
    ci_data = config.get('ci', {})
    return {
        'status': 'success',
        'provider': ci_data.get('provider', 'unknown'),
        'repo_url': ci_data.get('repo_url'),
    }


def cmd_ci_set_tools(args: argparse.Namespace) -> dict:
    """Handle 'ci-set-tools' subcommand — write run-config['ci']['authenticated_tools']."""
    _, _, load_run_config, save_run_config = _load_ci_modules()
    import os
    if hasattr(args, 'plan_dir'):
        os.environ['PLAN_BASE_DIR'] = str(args.plan_dir)
    run_config = load_run_config()
    run_ci = run_config.get('ci', {})
    tools = [t.strip() for t in args.tools.split(',') if t.strip()]
    run_ci['authenticated_tools'] = tools
    run_config['ci'] = run_ci
    save_run_config(run_config)
    return {'status': 'success', 'authenticated_tools': tools}


def cmd_ci_get_tools(args: argparse.Namespace) -> dict:
    """Handle 'ci-get-tools' subcommand — read run-config['ci']['authenticated_tools']."""
    _, _, load_run_config, _ = _load_ci_modules()
    import os
    if hasattr(args, 'plan_dir'):
        os.environ['PLAN_BASE_DIR'] = str(args.plan_dir)
    run_config = load_run_config()
    run_ci = run_config.get('ci', {})
    return {'status': 'success', 'authenticated_tools': run_ci.get('authenticated_tools', [])}


def cmd_persist(args: argparse.Namespace) -> dict:
    """Handle the 'persist' subcommand.

    Self-contained CI config persistence — no cross-skill imports.
    Writes config['ci'] (provider, repo_url) and run-config['ci'] (authenticated_tools).
    """
    import os

    plan_dir = Path(args.plan_dir)
    marshal_path = plan_dir / 'marshal.json'

    if not marshal_path.exists():
        return {'status': 'error', 'error': f'marshal.json not found at {marshal_path}. Run /marshall-steward first.'}

    os.environ['PLAN_BASE_DIR'] = str(plan_dir)

    # Detect provider
    provider_result = detect_provider()

    # Verify all tools and collect authenticated ones
    authenticated_tools = []
    git_present = False
    for tool in TOOLS:
        tool_status = verify_tool(tool)
        if tool_status['installed'] and tool_status['authenticated']:
            authenticated_tools.append(tool)
        if tool == 'git' and tool_status['installed']:
            git_present = True

    # Persist to config['ci'] (marshal.json)
    load_config, save_config, load_run_config, save_run_config = _load_ci_modules()
    config = load_config()
    config['ci'] = {
        'provider': provider_result['provider'],
        'repo_url': provider_result['repo_url'] or '',
    }
    save_config(config)

    # Persist to run-config['ci'] (run-configuration.json)
    if authenticated_tools:
        run_config = load_run_config()
        run_ci = run_config.get('ci', {})
        run_ci['authenticated_tools'] = authenticated_tools
        run_ci['git_present'] = git_present
        run_config['ci'] = run_ci
        save_run_config(run_config)

    return {
        'status': 'success',
        'persisted_to': 'marshal.json',
        'provider': provider_result['provider'],
        'repo_url': provider_result['repo_url'] or 'none',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='CI health verification for detecting providers and verifying tools')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # detect subcommand
    subparsers.add_parser('detect', help='Detect CI provider from repository configuration')

    # verify subcommand
    verify_parser = subparsers.add_parser('verify', help='Verify CLI tools are installed and authenticated')
    verify_parser.add_argument('--tool', type=str, help='Specific tool to verify (git, gh, glab)')

    # status subcommand
    subparsers.add_parser('status', help='Full health check (detect + verify)')

    # persist subcommand
    persist_parser = subparsers.add_parser('persist', help='Detect and persist CI configuration to marshal.json')
    persist_parser.add_argument(
        '--plan-dir', type=str, default='.plan', help='Path to .plan directory (default: .plan)'
    )

    # ci-get subcommand
    ci_get_parser = subparsers.add_parser('ci-get', help='Read CI config from marshal.json')
    ci_get_parser.add_argument('--plan-dir', type=str, default='.plan')

    # ci-get-provider subcommand
    ci_gp_parser = subparsers.add_parser('ci-get-provider', help='Read CI provider from marshal.json')
    ci_gp_parser.add_argument('--plan-dir', type=str, default='.plan')

    # ci-set-tools subcommand
    ci_st_parser = subparsers.add_parser('ci-set-tools', help='Write authenticated tools to run-config')
    ci_st_parser.add_argument('--tools', required=True, help='Comma-separated tool names')
    ci_st_parser.add_argument('--plan-dir', type=str, default='.plan')

    # ci-get-tools subcommand
    ci_gt_parser = subparsers.add_parser('ci-get-tools', help='Read authenticated tools from run-config')
    ci_gt_parser.add_argument('--plan-dir', type=str, default='.plan')

    args = parser.parse_args()

    handlers = {
        'detect': cmd_detect,
        'verify': cmd_verify,
        'status': cmd_status,
        'persist': cmd_persist,
        'ci-get': cmd_ci_get,
        'ci-get-provider': cmd_ci_get_provider,
        'ci-set-tools': cmd_ci_set_tools,
        'ci-get-tools': cmd_ci_get_tools,
    }

    handler = handlers.get(args.command)
    if handler:
        result = handler(args)
        print(serialize_toon(result))
        return 0

    parser.print_help()
    return 1


if __name__ == '__main__':
    from file_ops import safe_main  # type: ignore[import-not-found]

    safe_main(main)()
