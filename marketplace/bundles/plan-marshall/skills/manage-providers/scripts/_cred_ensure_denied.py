# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Add deny rules to Claude Code settings for credential directory protection.

Defense-in-depth: chmod 700 on the credentials directory is the primary
security boundary. These deny rules are an additional layer that is
fundamentally incomplete (blocklist approach).
"""

import argparse
import os
import sys

from _providers_core import CREDENTIALS_DIR
from file_ops import output_toon
from marketplace_paths import resolve_home

# Single-source every deny rule from CREDENTIALS_DIR so the deny surface follows
# the credentials location automatically. Both the absolute path and its
# ~-relative spelling are covered.
CREDENTIALS_DIR_ABS = str(CREDENTIALS_DIR)
_HOME_PREFIX = str(resolve_home())
CREDENTIALS_DIR_TILDE = (
    '~' + CREDENTIALS_DIR_ABS[len(_HOME_PREFIX):]
    if CREDENTIALS_DIR_ABS.startswith(_HOME_PREFIX)
    else CREDENTIALS_DIR_ABS
)
# Distinctive path tail (the segment after ``~/``) used by the ``python3 -c``
# substring vector so it matches the credentials path in an inline script under
# either spelling.
_DISTINCTIVE_SEGMENT = (
    CREDENTIALS_DIR_TILDE[2:] if CREDENTIALS_DIR_TILDE.startswith('~/') else CREDENTIALS_DIR_ABS
)
# Bash exfiltration binaries guarded in BOTH the tilde and absolute path forms.
_BASH_VECTORS = ('cat', 'head', 'tail', 'less', 'more', 'cp', 'grep', 'base64')


def _build_deny_rules() -> list[str]:
    """Build the deny-rule list, single-sourced from ``CREDENTIALS_DIR``.

    Every rule names the credentials dir in BOTH the tilde and absolute forms;
    the ``python3 -c`` vector uses the distinctive path tail so it matches either
    spelling in an inline script. No rule names only the retired
    ``~/.plan-marshall-credentials`` path.
    """
    rules = [
        # Read tool — both tilde and absolute path forms.
        f'Read({CREDENTIALS_DIR_TILDE}/**)',
        f'Read({CREDENTIALS_DIR_ABS}/**)',
    ]
    for vec in _BASH_VECTORS:
        rules.append(f'Bash({vec} {CREDENTIALS_DIR_TILDE}/*)')
        rules.append(f'Bash({vec} {CREDENTIALS_DIR_ABS}/*)')
    # python3 -c inline-script substring vector — matches either path form.
    rules.append(f'Bash(python3 -c *{_DISTINCTIVE_SEGMENT}*)')
    return rules


DENY_RULES = _build_deny_rules()


def run_ensure_denied(args: argparse.Namespace) -> int:
    """Execute the ensure-denied subcommand."""
    target = args.target

    # Import permission utilities
    try:
        from permission_common import (
            get_settings_path,
            load_settings_path,
            save_settings,
        )
    except ImportError:
        output_toon(
            {
                'status': 'error',
                'message': 'permission_common not available (missing from PYTHONPATH)',
            }
        )
        return 0

    # Verify credentials directory permissions first
    if CREDENTIALS_DIR.exists():
        current_mode = CREDENTIALS_DIR.stat().st_mode & 0o777
        if current_mode != 0o700:
            print(
                f'WARNING: Credentials directory has permissions {oct(current_mode)}, expected 0o700. Fixing...',
                file=sys.stderr,
            )
            os.chmod(str(CREDENTIALS_DIR), 0o700)

    settings_path = get_settings_path(target)
    settings = load_settings_path(settings_path)

    deny_list = settings.get('permissions', {}).get('deny', [])
    added = []

    for rule in DENY_RULES:
        if rule not in deny_list:
            deny_list.append(rule)
            added.append(rule)

    if added:
        settings.setdefault('permissions', {})['deny'] = deny_list
        save_settings(str(settings_path), settings)

    output_toon(
        {
            'status': 'success',
            'target': target,
            'rules_added': len(added),
            'rules_existing': len(DENY_RULES) - len(added),
            'total_deny_rules': len(deny_list),
        }
    )
    return 0
