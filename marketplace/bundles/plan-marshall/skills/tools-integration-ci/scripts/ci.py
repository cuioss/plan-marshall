#!/usr/bin/env python3
"""Provider-agnostic CI router.

Reads ci.provider from marshal.json and delegates to the correct
provider script (github.py or gitlab.py). All arguments are passed
through transparently.

Usage:
    python3 ci.py pr create --title "Title" --body "Body"
    python3 ci.py pr view
    python3 ci.py ci status --pr-number 123
    python3 ci.py issue create --title "Bug" --body "Description"

The provider is determined automatically from marshal.json configuration.
This eliminates the need for eval or jq in skill instructions.

Output: TOON format (from provider script)
"""

import json
import sys
from pathlib import Path

from ci_base import output_error  # type: ignore[import-not-found]

KNOWN_PROVIDERS = ('github', 'gitlab')


def find_plan_dir() -> Path | None:
    """Find .plan directory by walking up from current directory."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        plan_dir = parent / '.plan'
        if plan_dir.is_dir() and (plan_dir / 'marshal.json').exists():
            return plan_dir
    return None


def get_provider() -> str | None:
    """Read ci.provider from marshal.json and validate against known providers."""
    plan_dir = find_plan_dir()
    if not plan_dir:
        return None

    marshal_path = plan_dir / 'marshal.json'
    try:
        with open(marshal_path) as f:
            config = json.load(f)
            provider = config.get('ci', {}).get('provider')
            if not provider:
                return None
            provider_str = str(provider)
            if provider_str not in KNOWN_PROVIDERS:
                print(f'Warning: Unknown CI provider in marshal.json: {provider_str}', file=sys.stderr)
                return None
            return provider_str
    except (OSError, json.JSONDecodeError) as e:
        print(f'Warning: Failed to read marshal.json: {e}', file=sys.stderr)
        return None


PROVIDER_SKILLS = {
    'github': 'workflow-integration-github',
    'gitlab': 'workflow-integration-gitlab',
}


def main() -> int:
    provider = get_provider()
    if not provider:
        return output_error('router', 'CI provider not configured. Run /marshall-steward first.')

    skill = PROVIDER_SKILLS.get(provider)
    if not skill:
        return output_error('router', f'Unknown CI provider: {provider}')

    # Direct import via executor PYTHONPATH — provider scripts use unique
    # {provider}_ops.py names to avoid module collisions
    if provider == 'github':
        from github_ops import main as provider_main  # type: ignore[import-not-found]
    elif provider == 'gitlab':
        from gitlab_ops import main as provider_main  # type: ignore[import-not-found]
    else:
        return output_error('router', f'No import mapping for provider: {provider}')

    return provider_main()


if __name__ == '__main__':
    from file_ops import safe_main  # type: ignore[import-not-found]

    safe_main(main)()
