#!/usr/bin/env python3
"""Shared utilities for doctor-marketplace subcommands."""

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from marketplace_bundles import resolve_bundles_root

# =============================================================================
# Constants
# =============================================================================

MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'

_BUNDLES_FROM_SCRIPT = resolve_bundles_root(Path(__file__))
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
        timestamp = datetime.now(UTC).strftime('%Y%m%d-%H%M%S')
    if scope:
        return f'{timestamp}-{scope}-report.json'
    return f'{timestamp}-report.json'


def ensure_report_dir(report_dir: Path) -> Path:
    """Ensure report directory exists and return path."""
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


# =============================================================================
# Discovery Functions
# =============================================================================


def find_marketplace_root() -> Path | None:
    """Find the marketplace root directory deterministically.

    Discovery order (deterministic, not cwd-sensitive by default):

    1. ``PM_MARKETPLACE_ROOT`` environment variable — explicit override used
       by callers that cannot rely on script-relative resolution (tests with
       fake marketplaces, CLI invocations against alternate trees).
    2. Script-relative resolution — walks up from ``__file__`` to the
       ancestor ``marketplace`` directory. This is the canonical path when
       the script lives inside a marketplace checkout.
    3. cwd fallback — only reached when the script is executed from outside
       a marketplace source tree (e.g. installed plugin cache). Kept last
       so production behavior does not depend on the caller's cwd.
    """
    override = os.environ.get('PM_MARKETPLACE_ROOT')
    if override:
        override_path = Path(override)
        if override_path.is_dir():
            return override_path
    # Script-relative path is the canonical source-of-truth discovery.
    if _BUNDLES_FROM_SCRIPT.is_dir():
        return _BUNDLES_FROM_SCRIPT
    # Last-resort cwd fallback for out-of-tree execution (plugin cache).
    cwd = Path.cwd()
    if (cwd / MARKETPLACE_BUNDLES_PATH).is_dir():
        return cwd / MARKETPLACE_BUNDLES_PATH
    if (cwd.parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return cwd.parent / MARKETPLACE_BUNDLES_PATH
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
# Fix Constants
# =============================================================================

# Issue types that can be fixed automatically or with user confirmation
FIXABLE_ISSUE_TYPES = {
    # Safe fixes (auto-applicable)
    'missing-frontmatter',
    'invalid-yaml',
    'missing-name-field',
    'missing-description-field',
    'missing-tools-field',
    'array-syntax-tools',
    'trailing-whitespace',
    'improper-indentation',
    'missing-blank-line-before-list',
    'agent-skill-tool-visibility',
    'subdoc-forbidden-metadata',
    'unsupported-skill-tools-field',
    'misspelled-user-invocable',
    'missing-user-invocable',
    'checklist-pattern',
    'subdoc-checklist-pattern',
    # Risky fixes (require confirmation)
    'unused-tool-declared',
    'tool-not-declared',
    'agent-task-tool-prohibited',
    'agent-maven-restricted',
    'agent-lessons-via-skill',
    'backup-file-pattern',
    'ci-rule-self-update',
    'skill-invokable-mismatch',
}

# Safe fix types - can be auto-applied without user confirmation
SAFE_FIX_TYPES = {
    'missing-frontmatter',
    'invalid-yaml',
    'missing-name-field',
    'missing-description-field',
    'missing-tools-field',
    'array-syntax-tools',
    'trailing-whitespace',
    'improper-indentation',
    'missing-blank-line-before-list',
    'agent-skill-tool-visibility',
    'subdoc-forbidden-metadata',
    'unsupported-skill-tools-field',
    'misspelled-user-invocable',
    'missing-user-invocable',
    'checklist-pattern',
    'subdoc-checklist-pattern',
}

# Risky fix types - require user confirmation
RISKY_FIX_TYPES = {
    'unused-tool-declared',
    'tool-not-declared',
    'agent-task-tool-prohibited',
    'agent-maven-restricted',
    'agent-lessons-via-skill',
    'backup-file-pattern',
    'ci-rule-self-update',
    'subdoc-hardcoded-script-path',
    'skill-invokable-mismatch',
}


# =============================================================================
# Fix Utility Functions
# =============================================================================


def extract_frontmatter(content: str) -> tuple[bool, str]:
    """Extract YAML frontmatter from content."""
    if not content.startswith('---'):
        return False, ''

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        return True, match.group(1)
    return False, ''


def read_json_input(input_file: str) -> tuple[dict | None, str | None]:
    """Read and parse JSON from file or stdin."""
    try:
        if input_file == '-':
            content = sys.stdin.read()
        else:
            with open(input_file, encoding='utf-8') as f:
                content = f.read()

        if not content.strip():
            return {}, None

        return json.loads(content), None
    except FileNotFoundError:
        return None, f'File not found: {input_file}'
    except json.JSONDecodeError as e:
        return None, f'Invalid JSON: {str(e)}'
    except Exception as e:
        return None, f'Unexpected error: {str(e)}'


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

        issue_type = issue.get('type', '')
        if issue_type in SAFE_FIX_TYPES:
            safe.append(issue)
        else:
            risky.append(issue)

    return {'safe': safe, 'risky': risky, 'unfixable': unfixable}
