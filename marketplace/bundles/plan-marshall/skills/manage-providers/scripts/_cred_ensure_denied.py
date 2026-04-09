"""
Add deny rules to Claude Code settings for credential directory protection.

Defense-in-depth: chmod 700 on the credentials directory is the primary
security boundary. These deny rules are an additional layer that is
fundamentally incomplete (blocklist approach).
"""

import os
import sys

from _providers_core import CREDENTIALS_DIR
from file_ops import output_toon  # type: ignore[import-not-found]

# Expand ~ to absolute path to cover both forms
CREDENTIALS_DIR_ABS = str(CREDENTIALS_DIR)

DENY_RULES = [
    # Read tool — both tilde and absolute path forms
    'Read(~/.plan-marshall-credentials/**)',
    f'Read({CREDENTIALS_DIR_ABS}/**)',
    # Common Bash exfiltration vectors
    'Bash(cat ~/.plan-marshall-credentials/*)',
    f'Bash(cat {CREDENTIALS_DIR_ABS}/*)',
    'Bash(head ~/.plan-marshall-credentials/*)',
    'Bash(tail ~/.plan-marshall-credentials/*)',
    'Bash(less ~/.plan-marshall-credentials/*)',
    'Bash(more ~/.plan-marshall-credentials/*)',
    'Bash(cp ~/.plan-marshall-credentials/*)',
    'Bash(grep ~/.plan-marshall-credentials/*)',
    'Bash(python3 -c *plan-marshall-credentials*)',
    'Bash(base64 ~/.plan-marshall-credentials/*)',
]


def run_ensure_denied(args) -> int:
    """Execute the ensure-denied subcommand."""
    target = args.target

    # Import permission utilities
    try:
        from permission_common import (  # type: ignore[import-not-found]
            get_settings_path,
            load_settings_path,
            save_settings,
        )
    except ImportError:
        output_toon({
            'status': 'error',
            'message': 'permission_common not available (missing from PYTHONPATH)',
        })
        return 0

    # Verify credentials directory permissions first
    if CREDENTIALS_DIR.exists():
        current_mode = CREDENTIALS_DIR.stat().st_mode & 0o777
        if current_mode != 0o700:
            print(
                f'WARNING: Credentials directory has permissions {oct(current_mode)}, '
                f'expected 0o700. Fixing...',
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

    output_toon({
        'status': 'success',
        'target': target,
        'rules_added': len(added),
        'rules_existing': len(DENY_RULES) - len(added),
        'total_deny_rules': len(deny_list),
    })
    return 0
