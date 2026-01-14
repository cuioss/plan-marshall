#!/usr/bin/env python3
"""
Manage JSON configuration files with field-level operations.

Provides read, write, and update operations for JSON files (both .claude/
and .plan/ directories) using JSON path notation for field access.

Output: JSON to stdout with operation results.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def parse_json_path(path: str) -> list[str | int]:
    """Parse a JSON path string into components.

    Supports:
    - Dot notation: 'a.b.c'
    - Array indices: 'a[0].b', 'a[-1]'
    - Quoted keys: 'a."my-key".b'
    """
    components: list[str | int] = []
    current = ""
    i = 0
    in_quotes = False

    while i < len(path):
        char = path[i]

        if char == '"' and not in_quotes:
            in_quotes = True
            i += 1
            continue
        elif char == '"' and in_quotes:
            in_quotes = False
            i += 1
            continue
        elif char == '.' and not in_quotes:
            if current:
                components.append(current)
                current = ""
            i += 1
            continue
        elif char == '[' and not in_quotes:
            if current:
                components.append(current)
                current = ""
            # Parse array index
            i += 1
            index_str = ""
            while i < len(path) and path[i] != ']':
                index_str += path[i]
                i += 1
            if index_str.lstrip('-').isdigit():
                components.append(int(index_str))
            i += 1  # Skip closing bracket
            continue

        current += char
        i += 1

    if current:
        components.append(current)

    return components


def get_nested_value(data: Any, path_components: list) -> Any:
    """Get a value from nested data using path components."""
    current = data
    for component in path_components:
        if isinstance(component, int):
            if not isinstance(current, list):
                raise KeyError(f"Cannot index non-list with [{component}]")
            if component < 0:
                component = len(current) + component
            if component < 0 or component >= len(current):
                raise KeyError(f"Index {component} out of range")
            current = current[component]
        elif isinstance(current, dict):
            if component not in current:
                raise KeyError(f"Key '{component}' not found")
            current = current[component]
        else:
            raise KeyError(f"Cannot access '{component}' on non-object")
    return current


def set_nested_value(data: Any, path_components: list, value: Any) -> None:
    """Set a value in nested data using path components."""
    current = data
    for i, component in enumerate(path_components[:-1]):
        if isinstance(component, int):
            if not isinstance(current, list):
                raise KeyError(f"Cannot index non-list with [{component}]")
            if component < 0:
                component = len(current) + component
            current = current[component]
        elif isinstance(current, dict):
            if component not in current:
                # Auto-create intermediate objects
                next_comp = path_components[i + 1]
                current[component] = [] if isinstance(next_comp, int) else {}
            current = current[component]
        else:
            raise KeyError(f"Cannot access '{component}' on non-object")

    final = path_components[-1]
    if isinstance(final, int):
        if not isinstance(current, list):
            raise KeyError(f"Cannot index non-list with [{final}]")
        if final < 0:
            final = len(current) + final
        current[final] = value
    elif isinstance(current, dict):
        current[final] = value
    else:
        raise KeyError(f"Cannot set '{final}' on non-object")


def delete_nested_value(data: Any, path_components: list) -> Any:
    """Delete a value from nested data and return deleted value."""
    current = data
    for component in path_components[:-1]:
        if isinstance(component, int):
            current = current[component]
        else:
            current = current[component]

    final = path_components[-1]
    if isinstance(final, int):
        return current.pop(final)
    else:
        return current.pop(final)


def read_json_file(file_path: Path) -> dict[str, Any]:
    """Read and parse a JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, encoding='utf-8') as f:
        data: dict[str, Any] = json.load(f)
        return data


def write_json_file(file_path: Path, data: Any) -> None:
    """Write JSON data to file atomically."""
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then rename (atomic on most systems)
    fd, temp_path = tempfile.mkstemp(
        suffix='.json',
        prefix='.tmp_',
        dir=file_path.parent
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def output_success(operation: str, **kwargs) -> None:
    """Output success result as JSON."""
    result = {"success": True, "operation": operation}
    result.update(kwargs)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def output_error(operation: str, error: str) -> None:
    """Output error result as JSON to stderr."""
    result = {"success": False, "operation": operation, "error": error}
    print(json.dumps(result, indent=2), file=sys.stderr)


def cmd_read(args) -> int:
    """Read entire JSON file."""
    try:
        file_path = Path(args.file_path)
        data = read_json_file(file_path)
        output_success("read", path=str(file_path), value=data)
        return 0
    except Exception as e:
        output_error("read", str(e))
        return 1


def cmd_read_field(args) -> int:
    """Read specific field from JSON file."""
    try:
        file_path = Path(args.file_path)
        data = read_json_file(file_path)
        components = parse_json_path(args.field)
        value = get_nested_value(data, components)

        output_success("read-field", path=str(file_path), field=args.field, value=value)
        return 0
    except Exception as e:
        output_error("read-field", str(e))
        return 1


def cmd_write(args) -> int:
    """Write entire JSON content to file."""
    try:
        file_path = Path(args.file_path)
        data = json.loads(args.value)
        write_json_file(file_path, data)

        output_success("write", path=str(file_path))
        return 0
    except json.JSONDecodeError as e:
        output_error("write", f"Invalid JSON: {e}")
        return 1
    except Exception as e:
        output_error("write", str(e))
        return 1


def cmd_update_field(args) -> int:
    """Update specific field in JSON file."""
    try:
        file_path = Path(args.file_path)

        # Read existing or start fresh
        if file_path.exists():
            data = read_json_file(file_path)
        else:
            data = {}

        value = json.loads(args.value)
        components = parse_json_path(args.field)
        set_nested_value(data, components, value)

        write_json_file(file_path, data)

        output_success("update-field", path=str(file_path), field=args.field, value=value)
        return 0
    except json.JSONDecodeError as e:
        output_error("update-field", f"Invalid JSON value: {e}")
        return 1
    except Exception as e:
        output_error("update-field", str(e))
        return 1


def cmd_add_entry(args) -> int:
    """Add entry to array or object in JSON file."""
    try:
        file_path = Path(args.file_path)
        data = read_json_file(file_path) if file_path.exists() else {}
        value = json.loads(args.value)
        components = parse_json_path(args.field)

        try:
            target = get_nested_value(data, components)
        except KeyError:
            # Create the array/object if it doesn't exist
            set_nested_value(data, components, [])
            target = get_nested_value(data, components)

        if isinstance(target, list):
            target.append(value)
        elif isinstance(target, dict):
            if not isinstance(value, dict):
                output_error("add-entry", "Value must be an object when adding to object")
                return 1
            target.update(value)
        else:
            output_error("add-entry", f"Cannot add to {type(target).__name__}")
            return 1

        write_json_file(file_path, data)

        output_success("add-entry", path=str(file_path), field=args.field, added=value)
        return 0
    except json.JSONDecodeError as e:
        output_error("add-entry", f"Invalid JSON value: {e}")
        return 1
    except Exception as e:
        output_error("add-entry", str(e))
        return 1


def cmd_remove_entry(args) -> int:
    """Remove entry from array or object in JSON file."""
    try:
        file_path = Path(args.file_path)
        data = read_json_file(file_path)
        components = parse_json_path(args.field)

        if args.value:
            # Remove specific value from array
            target = get_nested_value(data, components)
            if isinstance(target, list):
                value = json.loads(args.value)
                if value in target:
                    target.remove(value)
                    removed = value
                else:
                    output_error("remove-entry", "Value not found in array")
                    return 1
            elif isinstance(target, dict):
                key = args.value.strip('"\'')
                if key in target:
                    removed = target.pop(key)
                else:
                    output_error("remove-entry", f"Key '{key}' not found")
                    return 1
            else:
                output_error("remove-entry", f"Cannot remove from {type(target).__name__}")
                return 1
        else:
            # Remove the field itself
            removed = delete_nested_value(data, components)

        write_json_file(file_path, data)

        output_success("remove-entry", path=str(file_path), field=args.field, removed=removed)
        return 0
    except json.JSONDecodeError as e:
        output_error("remove-entry", f"Invalid JSON value: {e}")
        return 1
    except Exception as e:
        output_error("remove-entry", str(e))
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Manage JSON configuration files with field-level operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read entire file
  %(prog)s read .plan/run-configuration.json

  # Read specific field
  %(prog)s read-field .plan/run-configuration.json --field "commands.setup-project-permissions"

  # Update field
  %(prog)s update-field .plan/run-configuration.json --field "commands.my-cmd.status" --value '"SUCCESS"'

  # Add to array
  %(prog)s add-entry .plan/run-configuration.json --field "commands.my-cmd.lessons" --value '"New lesson"'

  # Remove field
  %(prog)s remove-entry .plan/run-configuration.json --field "commands.old-cmd"

  # Also works with .claude/ (for settings)
  %(prog)s read .claude/settings.json
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # read command
    p_read = subparsers.add_parser('read', help='Read entire JSON file')
    p_read.add_argument('file_path', help='Path to JSON file')
    p_read.set_defaults(func=cmd_read)

    # read-field command
    p_read_field = subparsers.add_parser('read-field', help='Read specific field')
    p_read_field.add_argument('file_path', help='Path to JSON file')
    p_read_field.add_argument('--field', required=True, help='JSON path to field')
    p_read_field.set_defaults(func=cmd_read_field)

    # write command
    p_write = subparsers.add_parser('write', help='Write entire JSON content')
    p_write.add_argument('file_path', help='Path to JSON file')
    p_write.add_argument('--value', required=True, help='JSON content to write')
    p_write.set_defaults(func=cmd_write)

    # update-field command
    p_update = subparsers.add_parser('update-field', help='Update specific field')
    p_update.add_argument('file_path', help='Path to JSON file')
    p_update.add_argument('--field', required=True, help='JSON path to field')
    p_update.add_argument('--value', required=True, help='JSON value to set')
    p_update.set_defaults(func=cmd_update_field)

    # add-entry command
    p_add = subparsers.add_parser('add-entry', help='Add entry to array or object')
    p_add.add_argument('file_path', help='Path to JSON file')
    p_add.add_argument('--field', required=True, help='JSON path to array/object')
    p_add.add_argument('--value', required=True, help='JSON value to add')
    p_add.set_defaults(func=cmd_add_entry)

    # remove-entry command
    p_remove = subparsers.add_parser('remove-entry', help='Remove entry from array or object')
    p_remove.add_argument('file_path', help='Path to JSON file')
    p_remove.add_argument('--field', required=True, help='JSON path to field')
    p_remove.add_argument('--value', help='Value to remove (for arrays) or key (for objects)')
    p_remove.set_defaults(func=cmd_remove_entry)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
