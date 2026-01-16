#!/usr/bin/env python3
"""Shared utilities for doctor-marketplace subcommands."""

import os
from datetime import datetime
from pathlib import Path

# Import fix categorization from fix modules
from _cmd_categorize import categorize_fix

# =============================================================================
# Constants
# =============================================================================

MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'

# Script-relative path discovery (works regardless of cwd)
# Script is at: marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/
# So bundles directory is 5 levels up from script
SCRIPT_DIR = Path(__file__).resolve().parent
_BUNDLES_FROM_SCRIPT = SCRIPT_DIR.parent.parent.parent.parent.parent
REPORT_SUBDIR = 'plugin-doctor-report'


def _get_plan_dir() -> Path:
    """Get the .plan directory path, respecting PLAN_BASE_DIR override."""
    base = os.environ.get('PLAN_BASE_DIR', '.plan')
    return Path(base)


def _get_temp_dir(subdir: str | None = None) -> Path:
    """Get temp directory under .plan/temp/{subdir}."""
    temp_path = _get_plan_dir() / 'temp'
    if subdir:
        return temp_path / subdir
    return temp_path


def get_report_dir() -> Path:
    """Get the fixed report directory path: .plan/temp/plugin-doctor-report/."""
    return _get_temp_dir(REPORT_SUBDIR)


def get_report_filename(timestamp: str | None = None, scope: str | None = None) -> str:
    """Generate timestamped report filename.

    Args:
        timestamp: Optional timestamp string. Generated if not provided.
        scope: Optional scope identifier (e.g., bundle name or "marketplace").
               Included in filename if provided.

    Returns:
        Filename like "{timestamp}-report.json" or "{timestamp}-{scope}-report.json"
    """
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    if scope:
        return f'{timestamp}-{scope}-report.json'
    return f'{timestamp}-report.json'


def get_default_report_dir() -> Path:
    """Get the fixed report directory path.

    Deprecated: Use get_report_dir() instead. Kept for backward compatibility.
    """
    return get_report_dir()


def ensure_report_dir(report_dir: Path) -> Path:
    """Ensure report directory exists and return path."""
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


# =============================================================================
# Discovery Functions
# =============================================================================


def find_marketplace_root() -> Path | None:
    """Find the marketplace/bundles directory.

    First checks cwd-based discovery (supports test fixtures),
    then falls back to script-relative path (works regardless of cwd).
    """
    # First try cwd-based discovery (allows tests to use fixture directories)
    cwd = Path.cwd()
    if (cwd / MARKETPLACE_BUNDLES_PATH).is_dir():
        return cwd / MARKETPLACE_BUNDLES_PATH
    if (cwd.parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return cwd.parent / MARKETPLACE_BUNDLES_PATH
    # Fallback to script-relative path (works regardless of cwd)
    if _BUNDLES_FROM_SCRIPT.is_dir():
        return _BUNDLES_FROM_SCRIPT
    return None


def find_bundles(base_path: Path, bundle_filter: set[str] | None = None) -> list[Path]:
    """Find all bundle directories by locating plugin.json files."""
    bundles = []
    for plugin_json in base_path.rglob('.claude-plugin/plugin.json'):
        bundle_dir = plugin_json.parent.parent
        if bundle_filter and bundle_dir.name not in bundle_filter:
            continue
        if bundle_dir not in bundles:
            bundles.append(bundle_dir)
    return sorted(bundles, key=lambda p: p.name)


def discover_components(bundle_dir: Path) -> dict[str, list[dict]]:
    """Discover all components in a bundle."""
    components: dict[str, list[dict]] = {'agents': [], 'commands': [], 'skills': [], 'scripts': []}

    # Agents
    agents_dir = bundle_dir / 'agents'
    if agents_dir.is_dir():
        for f in sorted(agents_dir.glob('*.md')):
            if f.is_file():
                components['agents'].append({'name': f.stem, 'path': str(f), 'type': 'agent'})

    # Commands
    commands_dir = bundle_dir / 'commands'
    if commands_dir.is_dir():
        for f in sorted(commands_dir.glob('*.md')):
            if f.is_file():
                components['commands'].append({'name': f.stem, 'path': str(f), 'type': 'command'})

    # Skills
    skills_dir = bundle_dir / 'skills'
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
            skill_dir = skill_md.parent
            components['skills'].append(
                {'name': skill_dir.name, 'path': str(skill_dir), 'skill_md_path': str(skill_md), 'type': 'skill'}
            )

    # Scripts
    if skills_dir.is_dir():
        for script_file in sorted(skills_dir.rglob('scripts/*.py')):
            if script_file.is_file():
                skill_dir = script_file.parent.parent
                components['scripts'].append(
                    {'name': script_file.stem, 'path': str(script_file), 'skill': skill_dir.name, 'type': 'script'}
                )
        for script_file in sorted(skills_dir.rglob('scripts/*.sh')):
            if script_file.is_file():
                skill_dir = script_file.parent.parent
                components['scripts'].append(
                    {'name': script_file.stem, 'path': str(script_file), 'skill': skill_dir.name, 'type': 'script'}
                )

    return components


def find_bundle_for_file(file_path: Path, marketplace_root: Path) -> Path | None:
    """Find the bundle directory containing a file."""
    current = file_path.parent
    while current != current.parent and marketplace_root in current.parents or current == marketplace_root:
        plugin_json = current / '.claude-plugin' / 'plugin.json'
        if plugin_json.exists():
            return current
        current = current.parent
    return None


def extract_bundle_name(path: str) -> str:
    """Extract bundle name from a file path."""
    parts = path.split('/')
    try:
        bundles_idx = parts.index('bundles')
        if bundles_idx + 1 < len(parts):
            return parts[bundles_idx + 1]
    except ValueError:
        pass
    return 'unknown'


# =============================================================================
# Issue Categorization
# =============================================================================


def categorize_all_issues(issues: list[dict]) -> dict[str, list[dict]]:
    """Categorize issues into safe and risky."""
    safe = []
    risky = []
    unfixable = []

    for issue in issues:
        if not issue.get('fixable', False):
            unfixable.append(issue)
            continue

        category = categorize_fix(issue)
        if category == 'safe':
            safe.append(issue)
        else:
            risky.append(issue)

    return {'safe': safe, 'risky': risky, 'unfixable': unfixable}
