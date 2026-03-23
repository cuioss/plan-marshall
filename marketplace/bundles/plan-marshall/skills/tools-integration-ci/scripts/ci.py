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


def find_plan_dir() -> Path | None:
    """Find .plan directory by walking up from current directory."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        plan_dir = parent / '.plan'
        if plan_dir.is_dir() and (plan_dir / 'marshal.json').exists():
            return plan_dir
    return None


def get_provider() -> str | None:
    """Read ci.provider from marshal.json."""
    plan_dir = find_plan_dir()
    if not plan_dir:
        return None

    marshal_path = plan_dir / 'marshal.json'
    try:
        with open(marshal_path) as f:
            config = json.load(f)
            return config.get('ci', {}).get('provider')
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    provider = get_provider()
    if not provider:
        print('status: error', file=sys.stderr)
        print('operation: router', file=sys.stderr)
        print('error: CI provider not configured. Run /marshall-steward first.', file=sys.stderr)
        return 1

    if provider == 'github':
        from github import main as provider_main
    elif provider == 'gitlab':
        from gitlab import main as provider_main
    else:
        print('status: error', file=sys.stderr)
        print('operation: router', file=sys.stderr)
        print(f'error: Unknown CI provider: {provider}', file=sys.stderr)
        return 1

    return provider_main()


if __name__ == '__main__':
    sys.exit(main())
