"""
Core utilities for plan-marshall-config.

Shared functions for configuration loading, saving, output formatting,
and error handling used by all command modules.
"""

import json
import os
import sys
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
        raise MarshalNotInitializedError(
            f"marshal.json not found. Run command /marshall-steward first"
        )


def load_config() -> dict:
    """Load marshal.json."""
    return json.loads(MARSHAL_PATH.read_text(encoding='utf-8'))


def save_config(config: dict) -> None:
    """Save config to marshal.json with ordered keys."""
    MARSHAL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Canonical key order for marshal.json
    # Note: module_config replaces modules for command configuration
    key_order = ["ci", "plan", "skill_domains", "module_config", "system"]

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
        return json.loads(RUN_CONFIG_PATH.read_text(encoding='utf-8'))
    return {"version": 1, "commands": {}, "ci": {"authenticated_tools": [], "verified_at": None}}


def save_run_config(config: dict) -> None:
    """Save config to run-configuration.json."""
    RUN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding='utf-8')


def output(data: dict) -> None:
    """Output TOON result to stdout."""
    print(serialize_toon(data))


def error_exit(message: str, **extra) -> int:
    """Output error and return error exit code."""
    output({"status": "error", "error": message, **extra})
    return EXIT_ERROR


def success_exit(data: dict) -> int:
    """Output success and return success exit code."""
    output({"status": "success", **data})
    return EXIT_SUCCESS


def get_skill_description(skill_notation: str) -> str:
    """Extract description from SKILL.md frontmatter.

    Args:
        skill_notation: e.g., "pm-dev-java:java-core"

    Returns:
        Description string or skill name as fallback
    """
    try:
        parts = skill_notation.split(":")
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
                if (desc.startswith('"') and desc.endswith('"')) or \
                   (desc.startswith("'") and desc.endswith("'")):
                    desc = desc[1:-1]
                return desc

        return skill_notation
    except Exception:
        return skill_notation


def is_nested_domain(domain_config: dict) -> bool:
    """Check if domain config uses nested structure (with core, profiles).

    Nested domains have one of:
    - 'core' key (technical domains with profile-based skills)
    - 'workflow_skills' key (system domain with 5-phase workflow)
    - 'workflow_skill_extensions' key (domain extensions for outline/triage)
    """
    return ('core' in domain_config or
            'workflow_skills' in domain_config or
            'workflow_skill_extensions' in domain_config)


# ===========================================================================
# Raw Project Data (Module Source of Truth)
# ===========================================================================

RAW_PROJECT_DATA_PATH = PLAN_BASE_DIR / 'raw-project-data.json'


def load_raw_project_data() -> dict:
    """Load raw-project-data.json (module source of truth).

    Returns:
        Parsed raw data dict, or empty dict if not found.
    """
    if not RAW_PROJECT_DATA_PATH.exists():
        return {}
    try:
        content = RAW_PROJECT_DATA_PATH.read_text(encoding='utf-8')
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {}


def get_modules() -> list:
    """Get module list from raw-project-data.json.

    Returns:
        List of module dicts with: name, path, parent, build_systems, packaging.
        Empty list if raw-project-data.json doesn't exist.
    """
    raw_data = load_raw_project_data()
    return raw_data.get('modules', [])


def get_module_by_name(module_name: str) -> dict:
    """Get specific module info from raw-project-data.json.

    Args:
        module_name: Name of the module.

    Returns:
        Module dict or None if not found.
    """
    modules = get_modules()
    for module in modules:
        if module.get('name') == module_name:
            return module
    return None


# ===========================================================================
# Command Resolution (module_config)
# ===========================================================================

def get_module_command(module: str, label: str, build_system: str = None) -> dict:
    """Resolve command for module using module_config with fallback chain.

    Resolution order:
    1. Module-specific command (module_config.{module}.commands.{label})
    2. Default command (module_config.default.commands.{label})
    3. None if not found

    For hybrid modules (multiple build_systems), commands can be:
    - String: Same command for all build systems
    - Dict: Per-build-system commands {"maven": "...", "npm": "..."}

    Args:
        module: Module name.
        label: Canonical command name (module-tests, verify, quality-gate, etc.).
        build_system: Optional filter for hybrid modules.

    Returns:
        Dict with: command, source, build_system (if applicable).
        Returns None if command not found.
    """
    config = load_config()
    module_config = config.get('module_config', {})

    def resolve_command(cmd_value, source):
        """Resolve command value which may be string or dict."""
        if isinstance(cmd_value, str):
            # Simple command - substitute ${module} placeholder
            resolved = cmd_value.replace('${module}', module)
            return {'command': resolved, 'source': source}
        elif isinstance(cmd_value, dict):
            # Per-build-system commands
            if build_system and build_system in cmd_value:
                resolved = cmd_value[build_system].replace('${module}', module)
                return {'command': resolved, 'source': source, 'build_system': build_system}
            elif build_system:
                return None  # Requested build_system not available
            else:
                # Return all available commands
                resolved = {}
                for bs, cmd in cmd_value.items():
                    resolved[bs] = cmd.replace('${module}', module)
                return {'commands': resolved, 'source': source, 'multi_build_system': True}
        return None

    # 1. Check module-specific command
    if module in module_config:
        commands = module_config[module].get('commands', {})
        if label in commands:
            result = resolve_command(commands[label], 'module')
            if result:
                result['module'] = module
                result['label'] = label
                return result

    # 2. Fall back to default
    if 'default' in module_config:
        commands = module_config['default'].get('commands', {})
        if label in commands:
            result = resolve_command(commands[label], 'default')
            if result:
                result['module'] = module
                result['label'] = label
                return result

    return None


def list_module_commands(module: str) -> dict:
    """List all available commands for a module.

    Merges default commands with module-specific overrides.

    Args:
        module: Module name.

    Returns:
        Dict with: module, commands (list of available labels).
    """
    config = load_config()
    module_config = config.get('module_config', {})

    commands = set()

    # Add default commands
    if 'default' in module_config:
        default_cmds = module_config['default'].get('commands', {})
        commands.update(default_cmds.keys())

    # Add/override module-specific commands
    if module in module_config:
        module_cmds = module_config[module].get('commands', {})
        commands.update(module_cmds.keys())

    return {
        'module': module,
        'commands': sorted(commands)
    }
