# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Protect the credentials directory through the platform-runtime permission layer.

Defense-in-depth: chmod 700 on the credentials directory is the primary
security boundary. The permission rules are an additional layer that is
fundamentally incomplete (blocklist approach).

This module states the GOAL — protect the credentials directory — and the
active target's runtime decides what rules express that on its own permission
model, renders them, and writes them. No permission grammar is built here and
none is received back: a target whose permission model cannot express the
protection declines with ``no-op``, which this module reports rather than
treating as success.
"""

import argparse
import os
import sys
from typing import Any

from _providers_core import CREDENTIALS_DIR
from file_ops import output_toon
from marketplace_paths import _read_runtime_target
from platform_runtime import _make_runtime
from toon_parser import parse_toon


def _resolve_runtime() -> Any | None:
    """Return the active target's ``Runtime``, or ``None`` for an unknown target.

    Instantiates through the router's own registration block
    (``platform_runtime._make_runtime``) so this module never names a runtime
    class or enumerates targets.

    An unregistered target yields ``None`` and the caller reports an error. That
    is deliberately stricter than ``marketplace_paths._invoke_layout_op``, which
    substitutes the default runtime: a layout lookup has no error channel and
    must answer with something, while writing a security control has one and
    should not guess which target it is writing for.
    """
    return _make_runtime(_read_runtime_target())


def _ensure_credentials_dir_mode() -> None:
    """Re-assert 0700 on the credentials directory — the primary boundary.

    Both `stat` and `chmod` can fail on a directory this process does not own
    or on a read-only mount. That failure is reported and swallowed rather than
    raised: it must not cost the caller the deny rules, which are the
    defence-in-depth layer and are worth applying precisely when the primary
    boundary cannot be re-asserted. Raising here would also replace the
    subcommand's TOON payload with a traceback.
    """
    if not CREDENTIALS_DIR.exists():
        return
    try:
        current_mode = CREDENTIALS_DIR.stat().st_mode & 0o777
        if current_mode != 0o700:
            print(
                f'WARNING: Credentials directory has permissions {oct(current_mode)}, expected 0o700. Fixing...',
                file=sys.stderr,
            )
            os.chmod(str(CREDENTIALS_DIR), 0o700)
    except OSError as exc:
        print(
            f'WARNING: Could not enforce 0o700 on {CREDENTIALS_DIR}: {exc}',
            file=sys.stderr,
        )


def run_ensure_denied(args: argparse.Namespace) -> int:
    """Execute the ensure-denied subcommand."""
    target = args.target

    _ensure_credentials_dir_mode()

    runtime = _resolve_runtime()
    if runtime is None:
        output_toon(
            {
                'status': 'error',
                'error': 'unknown_target',
                'target': target,
                'message': 'No runtime is registered for the configured target',
            }
        )
        return 0

    payload = parse_toon(
        runtime.permission_fix(target, 'protect-path', [str(CREDENTIALS_DIR)], False)
    )
    status = payload.get('status')

    if status == 'no-op':
        # The no-op policy's caller obligation: report it and continue. The
        # directory mode above is still in force, so the primary boundary holds
        # on a target with no permission backend.
        output_toon(
            {
                'status': 'no-op',
                'target': target,
                'reason': payload.get('reason', ''),
                'alternative': payload.get('alternative', ''),
            }
        )
        return 0

    if status != 'success':
        # Forward the runtime's OWN error code rather than only its prose: a
        # caller branching on `error` needs the code the runtime produced.
        output_toon(
            {
                'status': 'error',
                'error': payload.get('error', 'protect_path_failed'),
                'target': target,
                'message': payload.get('message', 'permission fix protect-path failed'),
            }
        )
        return 0

    rules_added = int(payload.get('changes_applied', 0) or 0)
    rules_total = int(payload.get('rules_total', 0) or 0)
    output_toon(
        {
            'status': 'success',
            'target': target,
            'rules_added': rules_added,
            'rules_existing': rules_total - rules_added,
            'protection_rules_total': rules_total,
        }
    )
    return 0
