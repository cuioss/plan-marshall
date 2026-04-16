#!/usr/bin/env python3
"""Provider-agnostic CI router.

Resolves the CI provider by scanning providers[] in marshal.json for
category=ci and deriving the provider key from skill_name. Delegates to the
matching provider script ({provider}_ops.py). All arguments are passed through.

Usage:
    python3 ci.py [--project-dir PATH] pr create --title "Title" --plan-id my-plan
    python3 ci.py [--project-dir PATH] pr view
    python3 ci.py [--project-dir PATH] ci status --pr-number 123
    python3 ci.py [--project-dir PATH] issue create --title "Bug" --plan-id my-plan

Top-level flags (consumed by the router before provider dispatch):
    --project-dir PATH   Run every gh/glab subprocess with ``cwd=PATH``. Required
                         when invoking from a checkout whose HEAD is not the
                         branch the caller wants to operate on — e.g., phase-6
                         finalize running from the main checkout against a
                         worktree-isolated plan branch. When omitted, subprocesses
                         inherit the Python process cwd (current behaviour).

The provider is determined automatically from marshal.json configuration.
This eliminates the need for eval or jq in skill instructions.

Output: TOON format (from provider script)
"""

import importlib
import json
import sys
from pathlib import Path

from ci_base import (  # type: ignore[import-not-found]
    extract_project_dir,
    output_error,
    safe_main,
    set_default_cwd,
)


def find_plan_dir() -> Path | None:
    """Find .plan directory by walking up from current directory."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        plan_dir = parent / '.plan'
        if plan_dir.is_dir() and (plan_dir / 'marshal.json').exists():
            return plan_dir
    return None


def _derive_provider_key(skill_name: str) -> str | None:
    """Derive provider key from skill_name dynamically.

    Pattern: 'plan-marshall:workflow-integration-{provider}' -> '{provider}'
    Also handles unprefixed: 'workflow-integration-{provider}' -> '{provider}'
    """
    # Strip bundle prefix if present
    name = skill_name.split(':')[-1] if ':' in skill_name else skill_name
    prefix = 'workflow-integration-'
    if name.startswith(prefix):
        return name[len(prefix):]
    return None


def get_provider() -> str | None:
    """Find CI provider from marshal.json.

    Scans providers[] for the entry with category=ci and derives the provider
    key from its skill_name. This is the canonical (and only) resolution path.
    """
    plan_dir = find_plan_dir()
    if not plan_dir:
        return None

    marshal_path = plan_dir / 'marshal.json'
    try:
        with open(marshal_path) as f:
            config = json.load(f)

            for entry in config.get('providers', []):
                if not isinstance(entry, dict) or entry.get('category') != 'ci':
                    continue
                skill_name = entry.get('skill_name', '')
                key = _derive_provider_key(skill_name)
                if key:
                    return key
            return None
    except (OSError, json.JSONDecodeError) as e:
        print(f'Warning: Failed to read marshal.json: {e}', file=sys.stderr)
        return None


def main() -> int:
    # Consume top-level router flags (currently only --project-dir) before
    # delegating to the provider module. sys.argv is rewritten in place so the
    # downstream provider parser sees only its own arguments.
    project_dir, remaining = extract_project_dir(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    provider = get_provider()
    if not provider:
        return output_error('router', 'CI provider not configured. Run /marshall-steward first.')

    # Dynamic import via executor PYTHONPATH — provider scripts use
    # {provider}_ops.py naming convention to avoid module collisions
    module_name = f'{provider}_ops'
    try:
        provider_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return output_error('router', f'No provider module found: {module_name}')

    return provider_module.main()  # type: ignore[no-any-return]


if __name__ == '__main__':
    safe_main(main)()
