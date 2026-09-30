#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic script-only local harness configuration.

Usage:
    python3 configure_harness.py [--harness {claude,opencode,antigravity}]
                                 [--auto-sandbox-elevation | --no-auto-sandbox-elevation]
                                 [--plan-dir PATH] [--project-dir PATH]

Output (TOON format):
    status: success
    harness: antigravity
    target_source: env
    configured: true
    config_path: /abs/path/to/.plan/local/harness/antigravity.json
    dist_manifest_sha: <sha256>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from determine_mode import (
    check_harness_paths_valid,
    compute_current_harness_sha,
    resolve_harness_config_path,
)
from file_ops import atomic_write_file, safe_main
from input_validation import parse_args_with_toon_errors
from target_context import SOURCE_EXPLICIT, resolve_target
from toon_parser import serialize_toon


def dispatch_platform_runtime_setup(harness: str, project_dir: Path) -> bool:
    """Dispatch the active target's platform-runtime setup hooks and verify rule emission."""
    proj = project_dir.resolve()
    rules_emitted = False

    try:
        from platform_runtime import _make_runtime

        rt = _make_runtime(harness)
        if rt is not None:
            if hasattr(rt, 'project_initial_setup'):
                rt.project_initial_setup(str(proj), harness)
            if hasattr(rt, 'project_install_hook'):
                rt.project_install_hook(harness)
            if hasattr(rt, 'opencode_enforcement_apply'):
                rt.opencode_enforcement_apply(str(proj))
    except Exception:
        pass

    if harness == 'antigravity':
        rules_emitted = (proj / '.agents' / 'rules' / 'plan-marshall-target-rules.md').is_file() or (
            proj / 'AGENTS.md'
        ).is_file()
    elif harness == 'opencode':
        rules_emitted = (proj / '.opencode' / 'rules' / 'plan-marshall-target-rules.md').is_file() or (
            proj / 'AGENTS.md'
        ).is_file()
    elif harness == 'claude':
        rules_emitted = (proj / 'CLAUDE.md').is_file()
    else:
        rules_emitted = (proj / 'AGENTS.md').is_file() or (proj / 'CLAUDE.md').is_file()

    return rules_emitted


def configure_harness(
    harness_override: str | None = None,
    auto_sandbox_elevation: bool = False,
    plan_dir: Path | None = None,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Configure local harness state deterministically and persist .plan/local/harness/{harness}.json.

    Args:
        harness_override: Optional harness identifier override.
        auto_sandbox_elevation: Boolean flag for settings.auto_sandbox_elevation.
        plan_dir: Path to .plan directory (default: .plan).
        project_dir: Path to project root directory (default: cwd).

    Returns:
        TOON dict with configuration result.
    """
    if plan_dir is None:
        plan_dir = Path('.plan')
    proj = (project_dir or Path.cwd()).resolve()

    if harness_override is not None:
        harness = harness_override
        target_source = SOURCE_EXPLICIT
    else:
        resolved = resolve_target(proj)
        harness = resolved['target']
        target_source = resolved['target_source']

    executor_file = plan_dir / 'execute-script.py'
    executor_ready = executor_file.is_file()

    harness_paths_valid = check_harness_paths_valid(harness, proj)

    rules_emitted = dispatch_platform_runtime_setup(harness, proj)

    current_sha = compute_current_harness_sha(plan_dir, harness)

    config_path = resolve_harness_config_path(harness)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    harness_payload = {
        'schema_version': 1,
        'harness': harness,
        'target_source': target_source,
        'dist_manifest_sha': current_sha,
        'checks': {
            'rules_emitted': bool(rules_emitted),
            'harness_paths_valid': bool(harness_paths_valid),
            'executor_ready': bool(executor_ready),
        },
        'settings': {
            'auto_sandbox_elevation': bool(auto_sandbox_elevation),
        },
    }

    atomic_write_file(config_path, json.dumps(harness_payload, indent=2) + '\n')

    return {
        'status': 'success',
        'harness': harness,
        'target_source': target_source,
        'configured': True,
        'config_path': str(config_path),
        'dist_manifest_sha': current_sha,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Deterministic script-only local harness configuration',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--harness',
        choices=['claude', 'opencode', 'antigravity'],
        default=None,
        help='Harness to configure (default: resolved from environment/config)',
    )
    parser.add_argument(
        '--auto-sandbox-elevation',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable or disable auto sandbox elevation in settings (default: False)',
    )
    parser.add_argument(
        '--plan-dir',
        type=str,
        default='.plan',
        help='Directory containing execute-script.py (default: .plan)',
    )
    parser.add_argument(
        '--project-dir',
        type=str,
        default='.',
        help='Project root directory (default: .)',
    )

    args = parse_args_with_toon_errors(parser)

    result = configure_harness(
        harness_override=args.harness,
        auto_sandbox_elevation=args.auto_sandbox_elevation,
        plan_dir=Path(args.plan_dir),
        project_dir=Path(args.project_dir),
    )

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
