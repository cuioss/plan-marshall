"""
Core utilities for plan-marshall-config.

Shared functions for configuration loading, saving, output formatting,
and error handling used by all command modules.
"""

import json
import os
from pathlib import Path

# Direct imports - PYTHONPATH set by executor
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Bundle path for skill description resolution
BUNDLES_DIR = Path(__file__).parent.parent.parent.parent.parent  # .../bundles/

EXIT_SUCCESS = 0
EXIT_ERROR = 1

# File location
PLAN_BASE_DIR = Path(os.environ.get('PLAN_BASE_DIR', '.plan'))
MARSHAL_PATH = PLAN_BASE_DIR / 'marshal.json'
RUN_CONFIG_PATH = PLAN_BASE_DIR / 'run-configuration.json'


class MarshalNotInitializedError(Exception):
    """Raised when marshal.json doesn't exist and operation requires it."""

    pass


def is_initialized() -> bool:
    """Check if marshal.json exists."""
    return MARSHAL_PATH.exists()


def require_initialized() -> None:
    """Raise exception if marshal.json doesn't exist."""
    if not PLAN_BASE_DIR.exists():
        raise MarshalNotInitializedError(
            f"Directory '{PLAN_BASE_DIR}' does not exist. Run command /marshall-steward first"
        )
    if not MARSHAL_PATH.exists():
        raise MarshalNotInitializedError('marshal.json not found. Run command /marshall-steward first')


def load_config() -> dict:
    """Load marshal.json."""
    config: dict = json.loads(MARSHAL_PATH.read_text(encoding='utf-8'))
    return config


def save_config(config: dict) -> None:
    """Save config to marshal.json with ordered keys."""
    MARSHAL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Canonical key order for marshal.json
    key_order = ['ci', 'extension_defaults', 'finalize', 'plan', 'skill_domains', 'system', 'verification']

    # Build ordered dict: known keys first in order, then any remaining keys
    ordered = {}
    for key in key_order:
        if key in config:
            ordered[key] = config[key]
    for key in config:
        if key not in ordered:
            ordered[key] = config[key]

    MARSHAL_PATH.write_text(json.dumps(ordered, indent=2), encoding='utf-8')


def load_run_config() -> dict:
    """Load run-configuration.json (local, not shared via git)."""
    if RUN_CONFIG_PATH.exists():
        config: dict = json.loads(RUN_CONFIG_PATH.read_text(encoding='utf-8'))
        return config
    return {'version': 1, 'commands': {}, 'ci': {'authenticated_tools': [], 'verified_at': None}}


def save_run_config(config: dict) -> None:
    """Save config to run-configuration.json."""
    RUN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding='utf-8')


def output(data: dict) -> None:
    """Output TOON result to stdout."""
    print(serialize_toon(data))


def error_exit(message: str, **extra) -> int:
    """Output error and return error exit code."""
    output({'status': 'error', 'error': message, **extra})
    return EXIT_ERROR


def success_exit(data: dict) -> int:
    """Output success and return success exit code."""
    output({'status': 'success', **data})
    return EXIT_SUCCESS


def get_skill_description(skill_notation: str) -> str:
    """Extract description from SKILL.md frontmatter.

    Args:
        skill_notation: e.g., "pm-dev-java:java-core"

    Returns:
        Description string or skill name as fallback
    """
    try:
        parts = skill_notation.split(':')
        if len(parts) != 2:
            return skill_notation
        bundle, skill = parts
        skill_path = BUNDLES_DIR / bundle / 'skills' / skill / 'SKILL.md'

        if not skill_path.exists():
            return skill_notation

        content = skill_path.read_text(encoding='utf-8')

        # Parse YAML frontmatter (between --- markers)
        if not content.startswith('---'):
            return skill_notation

        end_marker = content.find('---', 3)
        if end_marker == -1:
            return skill_notation

        frontmatter = content[3:end_marker].strip()

        # Simple YAML parsing for description field
        for line in frontmatter.split('\n'):
            if line.startswith('description:'):
                desc = line[12:].strip()
                # Remove quotes if present
                if (desc.startswith('"') and desc.endswith('"')) or (desc.startswith("'") and desc.endswith("'")):
                    desc = desc[1:-1]
                return desc

        return skill_notation
    except Exception:
        return skill_notation


def is_nested_domain(domain_config: dict) -> bool:
    """Check if domain config uses nested structure.

    Nested domains have one of:
    - 'bundle' key (technical domains with profiles in extension.py)
    - 'workflow_skills' key (system domain with 7-phase workflow)
    - 'workflow_skill_extensions' key (domain extensions for outline/triage)
    """
    return (
        'bundle' in domain_config or 'workflow_skills' in domain_config or 'workflow_skill_extensions' in domain_config
    )


# =============================================================================
# Extension Defaults API
# =============================================================================


def get_extension_defaults(config: dict) -> dict:
    """Get extension_defaults section from config, ensuring it exists."""
    if 'extension_defaults' not in config:
        config['extension_defaults'] = {}
    ext: dict = config['extension_defaults']
    return ext


def ext_defaults_get(key: str, project_dir: str = '.') -> str | None:
    """Get extension default value by key.

    Args:
        key: The key to retrieve
        project_dir: Project directory containing .plan/

    Returns:
        The value if found, None otherwise
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    if not marshal_path.exists():
        return None

    config: dict = json.loads(marshal_path.read_text(encoding='utf-8'))
    ext = get_extension_defaults(config)
    result: str | None = ext.get(key)
    return result


def ext_defaults_set(key: str, value: str, project_dir: str = '.') -> None:
    """Set extension default value (always overwrites).

    Args:
        key: The key to set
        value: The value to store
        project_dir: Project directory containing .plan/
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    config: dict = json.loads(marshal_path.read_text(encoding='utf-8')) if marshal_path.exists() else {}
    ext = get_extension_defaults(config)
    ext[key] = value

    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def ext_defaults_set_default(key: str, value: str, project_dir: str = '.') -> bool:
    """Set extension default value only if key doesn't exist (write-once).

    Args:
        key: The key to set
        value: The value to store
        project_dir: Project directory containing .plan/

    Returns:
        True if value was set, False if key already existed
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    config: dict = json.loads(marshal_path.read_text(encoding='utf-8')) if marshal_path.exists() else {}
    ext = get_extension_defaults(config)

    if key in ext:
        return False

    ext[key] = value
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return True


def ext_defaults_list(project_dir: str = '.') -> dict:
    """List all extension defaults.

    Args:
        project_dir: Project directory containing .plan/

    Returns:
        Dictionary of all extension defaults
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    if not marshal_path.exists():
        return {}

    config: dict = json.loads(marshal_path.read_text(encoding='utf-8'))
    result: dict = get_extension_defaults(config)
    return result
