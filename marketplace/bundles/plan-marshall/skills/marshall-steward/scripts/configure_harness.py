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
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from antigravity_runtime import (
    STANDING_RULES_BRIDGE_MARKER as _ANTIGRAVITY_BRIDGE_MARKER,
)
from antigravity_runtime import (
    _bridge_rules_path as _antigravity_bridge_path,
)
from antigravity_runtime import (
    installed_rules_clobbered as _antigravity_installed_rules_clobbered,
)
from determine_mode import (
    check_harness_paths_valid,
    compute_current_harness_sha,
    resolve_harness_config_path,
)
from file_ops import atomic_write_file, safe_main
from input_validation import parse_args_with_toon_errors
from opencode_runtime import (
    STANDING_RULES_BRIDGE_MARKER as _OPENCODE_BRIDGE_MARKER,
)
from opencode_runtime import _bridge_rules_path as _opencode_bridge_path
from opencode_runtime import (
    installed_rules_clobbered as _opencode_installed_rules_clobbered,
)
from target_context import SOURCE_EXPLICIT, resolve_target
from toon_parser import parse_toon, serialize_toon

#: Command surfaced when a bridge stub is damaged (marker mismatch) or missing,
#: so the condition is never silent. Re-running project initial-setup re-emits
#: the bridge-owned file only.
BRIDGE_REEMIT_COMMAND_TEMPLATE = (
    'python3 {plan_dir}/execute-script.py plan-marshall:platform-runtime:platform_runtime'
    ' project initial-setup --project-dir {project_dir} --target {harness}'
)

#: Command that restores the installed target rules a previous setup clobbered
#: by writing its bridge stub into that file.
TARGET_RULES_RESTORE_COMMAND = './install.sh --emit-rules'


def bridge_reemit_command(harness: str, plan_dir: Path, project_dir: Path) -> str:
    """Return the re-emit command for a damaged or missing bridge stub."""
    return BRIDGE_REEMIT_COMMAND_TEMPLATE.format(
        harness=shlex.quote(harness),
        plan_dir=shlex.quote(str(plan_dir)),
        project_dir=shlex.quote(str(project_dir)),
    )


def installed_rules_clobbered(harness: str, project_dir: Path) -> bool:
    """Report whether a previous setup left its bridge stub in the installed rules.

    Read-only. The installed target rules belong to the ``install.sh`` emit
    path (``--workspace`` / ``--emit-rules``); a file carrying the bridge
    marker was clobbered by an older setup and is restored with that emit
    command. Claude has no such file, so its answer is always False.
    """
    if harness == 'antigravity':
        return _antigravity_installed_rules_clobbered(project_dir)
    if harness == 'opencode':
        return _opencode_installed_rules_clobbered(project_dir)
    return False


def _reconcile_standing_rules_bridge(harness: str, project_dir: Path) -> bool:
    """Observe standing-rules bridge state without writing through.

    Owned-file invariant: the bridge writes land only in the bridge-owned
    file (``.opencode/rules/plan-marshall-standing-rules.md`` on OpenCode,
    ``.agents/rules/plan-marshall-standing-rules.md`` on Antigravity) and
    never in the installed target-rules file (``plan-marshall-target-rules.md``)
    shipped by the bundles. Bridge paths and the version marker are derived
    from the runtime modules (never retyped here), so an outdated stub fails
    the marker check. This reconcile performs no writes at all — it only
    observes. A damaged stub (bridge present without its version marker) is
    reported as not reconciled, so the caller can surface
    :func:`bridge_reemit_command` for a stub that survived the setup writers;
    the installed target rules are never judged damaged for lacking a bridge
    marker. Claude carries no bridge file — its CLAUDE.md baseline is
    authoritative — so the reconcile is a no-op success there. Returns True
    only when the bridge is current.
    """
    proj = project_dir.resolve()
    if harness == 'claude':
        return (proj / 'CLAUDE.md').is_file()
    if harness == 'antigravity':
        bridge = _antigravity_bridge_path(proj)
        marker = _ANTIGRAVITY_BRIDGE_MARKER
    elif harness == 'opencode':
        bridge = _opencode_bridge_path(proj)
        marker = _OPENCODE_BRIDGE_MARKER
    else:
        return (proj / 'AGENTS.md').is_file() or (proj / 'CLAUDE.md').is_file()
    if bridge.is_file():
        try:
            text = bridge.read_text(encoding='utf-8')
        except OSError:
            return False
        # Boundary-aware marker match: the setup-written bridge embeds the
        # marker inside its heading line, so an exact-line match never fires;
        # a trailing-digit guard still rejects an outdated version marker.
        if re.search(re.escape(marker) + r'(?!\d)', text) is None:
            return False
        return True
    return False


def dispatch_platform_runtime_setup(harness: str, project_dir: Path) -> dict[str, Any]:
    """Observe rule emission without bridge-to-installed-target writes.

    Runs the runtime setup writers first (session-boundary enforcement) and
    surfaces their persisted-approval warnings on stderr. The
    bridge-to-installed-target write path stays retired: setup writes land
    only in the bridge-owned file, never in the installed target-rules file.
    Bridge paths and the version marker are derived from the runtime modules
    (never retyped here), and bare file existence never overrides a failed
    reconcile. The setup writers always run — a bridge verdict never returns
    before them — so session-boundary enforcement is never skipped by a
    bridge verdict; only a failing setup stops them (the install hook keeps
    its pre-existing cwd gate), and the failure is reported as such.

    Returns a dict with:

    - ``bridge_verdict``: `current`, `damaged` (bridge present without its
      version marker or unreadable), or `missing` (no bridge file). Judged
      after the setup writers ran, so a stub those writers heal reconciles
      to `current`; `damaged` means a stub survived a failed write. When
      setup itself fails, the verdict is `missing` and ``setup_failed`` is
      True.
    - ``setup_failed``: whether the setup itself raised or reported failure.
    - ``installed_rules_clobbered``: whether a previous setup left its stub
      in the installed target rules.
    - ``persisted_approval_warnings``: the setup's persisted-approval
      contradiction entries, also printed to stderr.

    The caller surfaces :func:`bridge_reemit_command` for the damaged or
    missing verdict and :data:`TARGET_RULES_RESTORE_COMMAND` for a clobbered
    installed file.
    """
    proj = project_dir.resolve()
    clobbered = installed_rules_clobbered(harness, proj)
    setup_ok = True
    persisted_warnings: list[dict[str, Any]] = []

    try:
        from platform_runtime import _make_runtime

        rt = _make_runtime(harness)
        if rt is not None:
            if hasattr(rt, 'project_initial_setup'):
                setup_result = rt.project_initial_setup(str(proj), harness)
                if setup_result is not None:
                    try:
                        setup_payload = parse_toon(setup_result) if isinstance(setup_result, str) else setup_result
                        if isinstance(setup_payload, dict) and setup_payload.get('status') != 'success':
                            setup_ok = False
                        if isinstance(setup_payload, dict):
                            for entry in setup_payload.get('persisted_approval_warnings') or []:
                                if not isinstance(entry, dict):
                                    continue
                                persisted_warnings.append(entry)
                                warning = entry.get('warning')
                                if warning:
                                    print(f'persisted approval warning: {warning}', file=sys.stderr)
                    except Exception:
                        setup_ok = False
            if hasattr(rt, 'project_install_hook') and proj == Path.cwd().resolve():
                rt.project_install_hook(harness)
            if hasattr(rt, 'opencode_enforcement_apply'):
                rt.opencode_enforcement_apply(str(proj))
    except Exception:
        setup_ok = False

    if not setup_ok:
        # Setup itself failed: emission is not established. Report missing so
        # the caller surfaces the re-emit command; re-running setup converges.
        return {
            'bridge_verdict': 'missing',
            'setup_failed': True,
            'installed_rules_clobbered': clobbered,
            'persisted_approval_warnings': persisted_warnings,
        }
    if harness == 'claude':
        verdict = 'current' if (proj / 'CLAUDE.md').is_file() else 'missing'
    elif harness in ('antigravity', 'opencode'):
        bridge = _antigravity_bridge_path(proj) if harness == 'antigravity' else _opencode_bridge_path(proj)
        if _reconcile_standing_rules_bridge(harness, proj):
            verdict = 'current'
        else:
            verdict = 'damaged' if bridge.is_file() else 'missing'
    else:
        exists = (proj / 'AGENTS.md').is_file() or (proj / 'CLAUDE.md').is_file()
        verdict = 'current' if exists else 'missing'
    return {
        'bridge_verdict': verdict,
        'setup_failed': False,
        'installed_rules_clobbered': clobbered,
        'persisted_approval_warnings': persisted_warnings,
    }


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

    dispatch_result = dispatch_platform_runtime_setup(harness, proj)
    bridge_verdict = dispatch_result['bridge_verdict']
    rules_emitted = bridge_verdict == 'current'

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

    result: dict[str, Any] = {
        'status': 'success',
        'harness': harness,
        'target_source': target_source,
        'configured': True,
        'config_path': str(config_path),
        'dist_manifest_sha': current_sha,
        'bridge_verdict': bridge_verdict,
        'setup_failed': dispatch_result['setup_failed'],
        'installed_rules_clobbered': dispatch_result['installed_rules_clobbered'],
        'persisted_approval_warnings': dispatch_result['persisted_approval_warnings'],
    }
    if dispatch_result['installed_rules_clobbered']:
        result['installed_rules_restore_command'] = TARGET_RULES_RESTORE_COMMAND
    if bridge_verdict in ('damaged', 'missing'):
        result['bridge_reemit_command'] = bridge_reemit_command(harness, plan_dir, proj)
    return result


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
