"""
Build systems command handlers for plan-marshall-config.

Handles: build-systems

NOTE: Build systems are determined at runtime via BUILD_SYSTEM_DEFAULTS,
not persisted in marshal.json. Commands are stored in modules, not at the
top level. This module provides read-only access to available build systems.
"""

from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    require_initialized,
    error_exit,
    success_exit,
)
from _config_defaults import BUILD_SYSTEM_DEFAULTS
from _config_detection import detect_build_systems


def cmd_build_systems(args) -> int:
    """Handle build-systems noun.

    Build systems are defined in BUILD_SYSTEM_DEFAULTS (static configuration).
    This provides read-only access - add/remove operations are not supported
    as build systems are not persisted in marshal.json.
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    if args.verb == 'list':
        # Return all known build systems from defaults
        systems = [
            {"system": name, "skill": config["skill"]}
            for name, config in BUILD_SYSTEM_DEFAULTS.items()
        ]
        return success_exit({"build_systems": systems, "count": len(systems)})

    elif args.verb == 'get':
        system = args.system
        if system in BUILD_SYSTEM_DEFAULTS:
            return success_exit({
                "system": system,
                "skill": BUILD_SYSTEM_DEFAULTS[system]["skill"],
                "commands": {}  # Commands are per-module, not global
            })
        return error_exit(f"Unknown build system: {system}")

    elif args.verb == 'get-command':
        # Build system commands are per-module now, use modules get-command
        return error_exit(
            "Build commands are per-module. Use: modules get-command --module <name> --label <label>"
        )

    elif args.verb == 'add':
        system = args.system
        if system in BUILD_SYSTEM_DEFAULTS:
            return error_exit(f"Build system already exists: {system}")
        # Can't add dynamically - build systems are defined in code
        return error_exit(
            f"Cannot add build system '{system}'. "
            "Build systems are defined in BUILD_SYSTEM_DEFAULTS."
        )

    elif args.verb == 'remove':
        system = args.system
        if system not in BUILD_SYSTEM_DEFAULTS:
            return error_exit(f"Unknown build system: {system}")
        # Can't remove - build systems are defined in code
        return error_exit(
            f"Cannot remove build system '{system}'. "
            "Build systems are defined in BUILD_SYSTEM_DEFAULTS."
        )

    elif args.verb == 'detect':
        # Detect which build systems are present in the project
        detected = detect_build_systems()
        detected_names = [bs["system"] for bs in detected]
        return success_exit({
            "detected": detected_names,
            "count": len(detected_names),
            "note": "Build systems detected from project files. "
                    "Use 'modules detect' to configure module-level build systems."
        })

    return EXIT_ERROR
