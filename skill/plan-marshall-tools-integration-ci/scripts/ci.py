#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provider-agnostic CI router.

Resolves the CI provider by scanning providers[] in marshal.json for
category=ci and deriving the provider key from skill_name. Delegates to the
matching provider script ({provider}_ops.py). All arguments are passed through.

Usage:
    python3 ci.py [--project-dir PATH] pr create --title "Title" --plan-id EXAMPLE-PLAN
    python3 ci.py [--project-dir PATH] pr view
    python3 ci.py [--project-dir PATH] ci status --pr-number 123
    python3 ci.py [--project-dir PATH] issue create --title "Bug" --plan-id EXAMPLE-PLAN

Top-level flags (consumed by the router before provider dispatch):
    --project-dir PATH   Run every gh/glab subprocess with ``cwd=PATH``. Required
                         when invoking from a checkout whose HEAD is not the
                         branch the caller wants to operate on — e.g., phase-6-finalize
                         finalize running from the main checkout against a
                         worktree-isolated plan branch. When omitted, subprocesses
                         inherit the Python process cwd (current behaviour).

Provider-agnostic verbs (handled by the router, no provider dispatch):
    barrier              Concurrent finalize-wait barrier coordinator —
                         per-signal-proceed + bounded re-settle over the
                         {CI, review, sonar} signals off one settled HEAD.
                         Pure computation; needs no CI provider and no worktree
                         resolution. See ``_ci_barrier.py`` and
                         ``phase-6-finalize/SKILL.md`` § "Wait-region".

The provider is determined automatically from marshal.json configuration.
This eliminates the need for eval or jq in skill instructions.

Output: TOON format (from provider script)
"""

import importlib
import json
import sys
from pathlib import Path

from ci_base import (
    extract_project_dir,
    extract_routing_args,
    output_error,
    safe_main,
    set_default_cwd,
)

# ``extract_project_dir`` is kept as a re-export for backward compatibility
# with tests and external callers that imported it from ``ci`` directly.
# New code should prefer ``extract_routing_args`` which also consumes
# ``--plan-id`` and enforces the two-state contract.
__all__ = ['extract_project_dir', 'extract_routing_args']


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
        return name[len(prefix) :]
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
        with open(marshal_path, encoding='utf-8') as f:
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
    # Provider-agnostic barrier coordinator — intercepted BEFORE provider
    # routing because it computes over caller-supplied signal state and needs
    # no CI provider, no worktree resolution, and no gh/glab subprocess. Keeping
    # it ahead of extract_routing_args also keeps it usable when no CI provider
    # is configured (the barrier is a pure state machine, not a provider call).
    argv = sys.argv[1:]
    if argv and argv[0] == 'barrier':
        from _ci_barrier import run_barrier_cli

        return run_barrier_cli(argv[1:])

    # Consume top-level router flags (--project-dir and --plan-id) before
    # delegating to the provider module. sys.argv is rewritten in place so the
    # downstream provider parser sees only its own arguments. The two flags
    # implement the two-state contract: --plan-id auto-resolves via
    # manage-status; --project-dir is the explicit override; both together
    # is a hard error (handled inside extract_routing_args).
    project_dir, remaining = extract_routing_args(argv)
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
