#!/usr/bin/env python3
"""Shared utilities for architecture scripts.

Provides load/save operations, TOON output formatting, and error handling.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Plan directory name - configurable for test isolation
_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# Data directory for architecture files (relative to project_dir argument)
DATA_DIR = Path(_PLAN_DIR_NAME) / "project-architecture"

# File names
DERIVED_DATA_FILE = "derived-data.json"
LLM_ENRICHED_FILE = "llm-enriched.json"


# =============================================================================
# Exceptions
# =============================================================================

class ArchitectureError(Exception):
    """Base exception for architecture errors."""
    pass


class DataNotFoundError(ArchitectureError):
    """Raised when required data files are missing."""
    pass


class ModuleNotFoundError(ArchitectureError):
    """Raised when a module is not found in the data."""
    pass


class CommandNotFoundError(ArchitectureError):
    """Raised when a command is not found for a module."""
    pass


# =============================================================================
# File Operations
# =============================================================================

def get_data_dir(project_dir: str = '.') -> Path:
    """Get the data directory path."""
    return Path(project_dir) / DATA_DIR


def get_derived_path(project_dir: str = '.') -> Path:
    """Get path to derived-data.json."""
    return get_data_dir(project_dir) / DERIVED_DATA_FILE


def get_enriched_path(project_dir: str = '.') -> Path:
    """Get path to llm-enriched.json."""
    return get_data_dir(project_dir) / LLM_ENRICHED_FILE


def load_derived_data(project_dir: str = '.') -> dict[str, Any]:
    """Load derived-data.json.

    Args:
        project_dir: Project directory path

    Returns:
        Dict containing derived module data

    Raises:
        DataNotFoundError: If file does not exist
    """
    path = get_derived_path(project_dir)
    if not path.exists():
        raise DataNotFoundError(
            f"Derived data not found. Run 'architecture.py discover' first. "
            f"Expected: {path}"
        )
    with open(path) as f:
        result: dict[str, Any] = json.load(f)
        return result


def load_llm_enriched(project_dir: str = '.') -> dict[str, Any]:
    """Load llm-enriched.json.

    Args:
        project_dir: Project directory path

    Returns:
        Dict containing enriched module data, or empty structure if missing

    Raises:
        DataNotFoundError: If file does not exist
    """
    path = get_enriched_path(project_dir)
    if not path.exists():
        raise DataNotFoundError(
            f"Enrichment data not found. Run 'architecture.py init' first. "
            f"Expected: {path}"
        )
    with open(path) as f:
        result: dict[str, Any] = json.load(f)
        return result


def load_llm_enriched_or_empty(project_dir: str = '.') -> dict[str, Any]:
    """Load llm-enriched.json or return empty structure.

    Args:
        project_dir: Project directory path

    Returns:
        Dict containing enriched module data, or empty structure
    """
    path = get_enriched_path(project_dir)
    if not path.exists():
        return {"project": {}, "modules": {}}
    with open(path) as f:
        result: dict[str, Any] = json.load(f)
        return result


def save_derived_data(data: dict[str, Any], project_dir: str = '.') -> Path:
    """Save derived-data.json.

    Args:
        data: Dict to save
        project_dir: Project directory path

    Returns:
        Path to saved file
    """
    path = get_derived_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return path


def save_llm_enriched(data: dict[str, Any], project_dir: str = '.') -> Path:
    """Save llm-enriched.json.

    Args:
        data: Dict to save
        project_dir: Project directory path

    Returns:
        Path to saved file
    """
    path = get_enriched_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return path


# =============================================================================
# Module Operations
# =============================================================================

def get_module_names(derived: dict[str, Any]) -> list[str]:
    """Get list of module names from derived data.

    Args:
        derived: Derived data dict

    Returns:
        List of module names
    """
    return list(derived.get("modules", {}).keys())


def get_root_module(derived: dict[str, Any]) -> str | None:
    """Get the root module name (module at project root).

    Root module is determined by:
    1. Module with path "." or "" (at project root)
    2. Fallback: first module in the list

    For single-module projects, the root module is typically the only module.
    For multi-module projects, the root is usually the parent/aggregator module.

    Args:
        derived: Derived data dict

    Returns:
        Root module name, or None if no modules exist
    """
    modules: dict[str, Any] = derived.get("modules", {})
    for name, data in modules.items():
        paths = data.get("paths", {})
        module_path = paths.get("module", "")
        if module_path == "." or module_path == "":
            root_name: str = name
            return root_name
    # Fallback: first module
    result: str | None = next(iter(modules.keys()), None)
    return result


def get_module(derived: dict[str, Any], module_name: str) -> dict[str, Any]:
    """Get module data by name.

    Args:
        derived: Derived data dict
        module_name: Module name

    Returns:
        Module data dict

    Raises:
        ModuleNotFoundError: If module not found
    """
    modules = derived.get("modules", {})
    if module_name not in modules:
        available = list(modules.keys())
        raise ModuleNotFoundError(
            f"Module not found: {module_name}",
            available
        )
    result: dict[str, Any] = modules[module_name]
    return result


def merge_module_data(derived: dict[str, Any], enriched: dict[str, Any], module_name: str) -> dict[str, Any]:
    """Merge derived and enriched data for a module.

    Args:
        derived: Derived data dict
        enriched: Enriched data dict
        module_name: Module name to merge

    Returns:
        Merged module data dict
    """
    derived_modules = derived.get("modules", {})
    enriched_modules = enriched.get("modules", {})

    derived_module = derived_modules.get(module_name, {})
    enriched_module = enriched_modules.get(module_name, {})

    # Start with derived data
    merged = dict(derived_module)

    # Overlay enriched fields (they take precedence for fields they define)
    for key, value in enriched_module.items():
        if value:  # Only overlay non-empty values
            merged[key] = value

    return merged


# =============================================================================
# TOON Output Formatting
# =============================================================================

def format_toon_value(value) -> str:
    """Format a value for TOON output.

    Args:
        value: Value to format

    Returns:
        Formatted string
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "+".join(str(v) for v in value)
    return str(value)


def print_toon_kv(key: str, value, indent: int = 0):
    """Print a key-value pair in TOON format.

    Args:
        key: Key name
        value: Value (can be str, int, bool, list, dict)
        indent: Indentation level
    """
    prefix = "  " * indent
    if isinstance(value, dict):
        print(f"{prefix}{key}:")
        for k, v in value.items():
            print_toon_kv(k, v, indent + 1)
    elif isinstance(value, list) and value and isinstance(value[0], dict):
        # List of dicts - use table format
        print(f"{prefix}{key}[{len(value)}]:")
        for item in value:
            print(f"{prefix}  - {item}")
    elif isinstance(value, list):
        print(f"{prefix}{key}[{len(value)}]:")
        for item in value:
            print(f"{prefix}  - {item}")
    else:
        formatted = format_toon_value(value)
        print(f"{prefix}{key}: {formatted}")


def print_toon_table(name: str, items: list, fields: list):
    """Print a TOON table.

    Args:
        name: Table name
        items: List of dicts
        fields: List of field names to include
    """
    field_spec = ",".join(fields)
    print(f"{name}[{len(items)}]{{{field_spec}}}:")
    for item in items:
        values = [format_toon_value(item.get(f, "")) for f in fields]
        print("\t".join(values))


def print_toon_list(name: str, items: list):
    """Print a TOON list.

    Args:
        name: List name
        items: List of values
    """
    print(f"{name}[{len(items)}]:")
    for item in items:
        print(f"  - {item}")


# =============================================================================
# Error Handling
# =============================================================================

def error_exit(message: str, context: dict[str, Any] | None = None) -> None:
    """Print error in TOON format and exit with code 1.

    Args:
        message: Error message
        context: Optional context dict with key-value pairs
    """
    print(f"error: {message}")
    if context:
        for key, value in context.items():
            if isinstance(value, list):
                print_toon_list(key, value)
            else:
                print(f"{key}: {value}")
    sys.exit(1)


def error_module_not_found(module_name: str, available: list):
    """Print module not found error and exit.

    Args:
        module_name: Requested module name
        available: List of available module names
    """
    print("error: Module not found")
    print(f"module: {module_name}")
    print_toon_list("available", available)
    sys.exit(1)


def error_command_not_found(module_name: str, command_name: str, available: list):
    """Print command not found error and exit.

    Args:
        module_name: Module name
        command_name: Requested command name
        available: List of available command names
    """
    print("error: Command not found")
    print(f"module: {module_name}")
    print(f"command: {command_name}")
    print_toon_list("available", available)
    sys.exit(1)


def error_data_not_found(expected_file: str, resolution: str):
    """Print data not found error and exit.

    Args:
        expected_file: Path to expected file
        resolution: How to fix
    """
    print("error: Data not found")
    print(f"expected_file: {expected_file}")
    print(f"resolution: {resolution}")
    sys.exit(1)
