"""
Modules command handlers for plan-marshall-config.

Handles: modules

Module facts (name, path, build_systems) come from raw-project-data.json.
Command configuration uses module_config section of marshal.json.
"""

import json
from pathlib import Path

from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    require_initialized,
    load_config,
    save_config,
    error_exit,
    success_exit,
    get_modules,
    get_module_by_name,
    get_module_command,
    list_module_commands,
)


def infer_domains_from_build_systems(build_systems: list) -> list:
    """Infer skill domains from build systems configuration.

    Mapping:
    - maven, gradle -> java
    - npm -> javascript

    Args:
        build_systems: List of build system names

    Returns:
        List of inferred domain names
    """
    domains = []
    for bs in build_systems:
        bs_lower = bs.lower()
        if bs_lower in ('maven', 'gradle') and 'java' not in domains:
            domains.append('java')
        elif bs_lower == 'npm' and 'javascript' not in domains:
            domains.append('javascript')
    return domains


def cmd_modules(args) -> int:
    """Handle modules noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    # Module facts from raw-project-data.json
    all_modules = get_modules()

    # Command config from marshal.json
    config = load_config()
    module_config = config.get('module_config', {})

    if args.verb == 'list':
        # List modules from raw-project-data.json
        module_list = []
        for mod in all_modules:
            module_list.append({
                "name": mod.get("name"),
                "path": mod.get("path"),
                "build_systems": mod.get("build_systems", []),
                "packaging": mod.get("packaging")
            })
        return success_exit({"modules": module_list, "count": len(module_list)})

    elif args.verb == 'get':
        module_name = args.module
        mod = get_module_by_name(module_name)
        if not mod:
            return error_exit(f"Unknown module: {module_name}")

        # Combine facts with command config
        cmd_list = list_module_commands(module_name)
        return success_exit({
            "module": module_name,
            "path": mod.get("path"),
            "build_systems": mod.get("build_systems", []),
            "packaging": mod.get("packaging"),
            "commands": cmd_list.get("commands", [])
        })

    elif args.verb == 'get-build-systems':
        module_name = args.module
        mod = get_module_by_name(module_name)
        if not mod:
            return error_exit(f"Unknown module: {module_name}")
        return success_exit({
            "module": module_name,
            "build_systems": mod.get("build_systems", [])
        })

    elif args.verb == 'get-command':
        module_name = args.module
        label = args.label
        build_system = getattr(args, 'build_system', None)

        result = get_module_command(module_name, label, build_system)
        if result is None:
            return error_exit(f"Command not found: {module_name}.{label}")

        return success_exit(result)

    elif args.verb == 'list-commands':
        module_name = args.module
        result = list_module_commands(module_name)
        return success_exit(result)

    elif args.verb == 'set-command':
        module_name = args.module
        label = args.label
        command = args.command
        build_system = getattr(args, 'build_system', None)

        # Initialize module_config entry if needed
        if module_name not in module_config:
            module_config[module_name] = {"commands": {}}
        elif "commands" not in module_config[module_name]:
            module_config[module_name]["commands"] = {}

        # Handle hybrid modules (per-build-system commands)
        if build_system:
            existing = module_config[module_name]["commands"].get(label)
            if isinstance(existing, str):
                # Convert from simple string to dict
                module_config[module_name]["commands"][label] = {build_system: command}
            elif isinstance(existing, dict):
                existing[build_system] = command
            else:
                module_config[module_name]["commands"][label] = {build_system: command}
        else:
            module_config[module_name]["commands"][label] = command

        config['module_config'] = module_config
        save_config(config)

        return success_exit({
            "module": module_name,
            "label": label,
            "command": command,
            "build_system": build_system,
            "action": "set"
        })

    elif args.verb == 'set-default-command':
        # Set a default command (applies to all modules without override)
        label = args.label
        command = args.command

        if 'default' not in module_config:
            module_config['default'] = {"commands": {}}
        elif "commands" not in module_config['default']:
            module_config['default']["commands"] = {}

        module_config['default']["commands"][label] = command
        config['module_config'] = module_config
        save_config(config)

        return success_exit({
            "label": label,
            "command": command,
            "action": "set-default"
        })

    elif args.verb == 'persist-all':
        # Replace entire module_config section with provided JSON
        # Used by project-structure to persist detected modules with commands
        try:
            new_module_config = json.loads(args.modules_json)
        except json.JSONDecodeError as e:
            return error_exit(f"Invalid JSON for --modules-json: {e}")

        config['module_config'] = new_module_config
        save_config(config)
        return success_exit({
            "modules_count": len(new_module_config),
            "action": "persist-all"
        })

    elif args.verb == 'infer-domains':
        # Infer domains from build_systems for all modules
        # Uses raw-project-data.json for build_systems, updates module_config for domains
        updated = []
        skipped = []

        for mod in all_modules:
            mod_name = mod.get('name')
            if mod_name == 'default':
                continue

            # Get existing domains from module_config
            existing_domains = []
            if mod_name in module_config:
                existing_domains = module_config[mod_name].get('domains', [])

            # Skip if domains already populated (unless --force)
            if existing_domains and not getattr(args, 'force', False):
                skipped.append(mod_name)
                continue

            # Infer from build_systems (from raw-project-data.json)
            build_systems = mod.get('build_systems', [])
            inferred = infer_domains_from_build_systems(build_systems)

            if inferred:
                if mod_name not in module_config:
                    module_config[mod_name] = {}
                module_config[mod_name]['domains'] = inferred
                updated.append({
                    'module': mod_name,
                    'domains': inferred,
                    'from_build_systems': build_systems
                })

        if updated:
            config['module_config'] = module_config
            save_config(config)

        return success_exit({
            "updated": updated,
            "updated_count": len(updated),
            "skipped": skipped,
            "skipped_count": len(skipped)
        })

    return error_exit(f"Unknown verb: {args.verb}")
