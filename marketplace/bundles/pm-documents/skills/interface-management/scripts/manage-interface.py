#!/usr/bin/env python3
"""Manage Interface specifications in doc/interfaces/ directory.

This script provides CRUD operations for Interface documentation with
automatic numbering and AsciiDoc formatting.

Operations:
    list        - List all interfaces with optional type filter
    create      - Create new interface from template
    read        - Read interface content by number
    update      - Update interface content
    delete      - Delete interface (requires --force)
    next-number - Get next available interface number

Output format: JSON to stdout
"""

import argparse
import json
import re
import sys
from pathlib import Path

from plan_logging import log_entry  # type: ignore[import-not-found]

# Interface directory relative to project root
INTERFACE_DIR = Path("doc/interfaces")

# Valid interface types
VALID_TYPES = ["REST_API", "Event", "gRPC", "Database", "File", "Other"]

# Template placeholders with defaults
TEMPLATE_DEFAULTS = {
    "{{OVERVIEW}}": "// Describe the interface purpose",
    "{{INPUT_DEFINITION}}": "// Define input structure",
    "{{OUTPUT_DEFINITION}}": "// Define output structure",
    "{{ERROR_HANDLING}}": "// Document error scenarios",
    "{{AUTH_REQUIREMENTS}}": "// Specify authentication/authorization",
    "{{VERSIONING}}": "// Document versioning approach",
    "{{EXAMPLE_FORMAT}}": "json",
    "{{REQUEST_EXAMPLE}}": "// Add request example",
    "{{RESPONSE_EXAMPLE}}": "// Add response example",
    "{{CONSUMERS}}": "// List consuming systems",
    "{{PROVIDERS}}": "// List providing systems",
    "{{REFERENCES}}": "// Add references",
}


def output_json(data: dict, success: bool = True, to_stderr: bool = False):
    """Output JSON response."""
    data["success"] = success
    stream = sys.stderr if to_stderr else sys.stdout
    print(json.dumps(data, indent=2), file=stream)
    sys.exit(0 if success else 1)


def get_template_path() -> Path:
    """Get path to interface template."""
    script_dir = Path(__file__).parent
    return script_dir.parent / "templates" / "interface-template.adoc"


def sanitize_title(title: str) -> str:
    """Sanitize title for filename: remove special chars, replace spaces."""
    # Remove special characters except alphanumeric, spaces, and hyphens
    safe_title = re.sub(r"[^\w\s-]", "", title)
    # Replace spaces with underscores
    safe_title = re.sub(r"\s+", "_", safe_title.strip())
    return safe_title


def generate_filename(number: int, title: str) -> str:
    """Generate interface filename from number and title."""
    safe_title = sanitize_title(title)
    return f"{number:03d}-{safe_title}.adoc"


def get_next_number() -> int:
    """Get next available interface number."""
    if not INTERFACE_DIR.exists():
        return 1

    existing = list(INTERFACE_DIR.glob("*.adoc"))
    if not existing:
        return 1

    numbers = []
    for f in existing:
        match = re.match(r"^(\d{3})-", f.name)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1


def parse_interface_file(filepath: Path) -> dict:
    """Parse interface file and extract metadata."""
    content = filepath.read_text()

    # Extract number from filename
    match = re.match(r"^(\d{3})-(.+)\.adoc$", filepath.name)
    number = int(match.group(1)) if match else 0

    # Extract title from first line
    title_match = re.match(r"^= INTER-\d+: (.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Unknown"

    # Extract interface type
    type_match = re.search(
        r"^== Interface Type\s*\n\n(.+?)(?:\n\n|$)", content, re.MULTILINE
    )
    interface_type = type_match.group(1).strip() if type_match else "Unknown"

    return {
        "number": number,
        "title": title,
        "type": interface_type,
        "path": str(filepath),
        "filename": filepath.name,
    }


def cmd_list(args):
    """List all interfaces."""
    if not INTERFACE_DIR.exists():
        output_json({"operation": "list", "count": 0, "interfaces": []})

    interfaces = []
    for filepath in sorted(INTERFACE_DIR.glob("*.adoc")):
        iface = parse_interface_file(filepath)
        if args.type and iface["type"] != args.type:
            continue
        interfaces.append(iface)

    output_json({"operation": "list", "count": len(interfaces), "interfaces": interfaces})


def cmd_create(args):
    """Create new interface."""
    # Validate type
    if args.type not in VALID_TYPES:
        log_entry('script', 'global', 'ERROR', f'[IFACE] Invalid type: {args.type}')
        output_json(
            {
                "operation": "create",
                "error": f"Invalid type: {args.type}. Valid types: {VALID_TYPES}",
            },
            success=False,
            to_stderr=True,
        )

    # Ensure interface directory exists
    INTERFACE_DIR.mkdir(parents=True, exist_ok=True)

    # Get next number
    number = get_next_number()

    # Generate filename
    filename = generate_filename(number, args.title)
    filepath = INTERFACE_DIR / filename

    # Check if file already exists
    if filepath.exists():
        log_entry('script', 'global', 'ERROR', f'[IFACE] File already exists: {filepath}')
        output_json(
            {
                "operation": "create",
                "error": f"Interface file already exists: {filepath}",
            },
            success=False,
            to_stderr=True,
        )

    # Load template
    template_path = get_template_path()
    if not template_path.exists():
        log_entry('script', 'global', 'ERROR', f'[IFACE] Template not found: {template_path}')
        output_json(
            {"operation": "create", "error": f"Template not found: {template_path}"},
            success=False,
            to_stderr=True,
        )

    template_content = template_path.read_text()

    # Replace placeholders
    content = template_content.replace("{{NUMBER}}", f"{number:03d}")
    content = content.replace("{{TITLE}}", args.title)
    content = content.replace("{{INTERFACE_TYPE}}", args.type)

    # Replace remaining placeholders with defaults
    for placeholder, default in TEMPLATE_DEFAULTS.items():
        content = content.replace(placeholder, default)

    # Write file
    filepath.write_text(content)

    log_entry('script', 'global', 'INFO', f'[IFACE] Created INTER-{number:03d}: {args.title}')
    output_json(
        {
            "operation": "create",
            "number": number,
            "path": str(filepath),
            "title": args.title,
            "type": args.type,
        }
    )


def cmd_read(args):
    """Read interface content."""
    if not INTERFACE_DIR.exists():
        output_json(
            {"operation": "read", "error": "Interface directory does not exist"},
            success=False,
            to_stderr=True,
        )

    # Find interface by number
    pattern = f"{args.number:03d}-*.adoc"
    matches = list(INTERFACE_DIR.glob(pattern))

    if not matches:
        output_json(
            {"operation": "read", "error": f"Interface {args.number} not found"},
            success=False,
            to_stderr=True,
        )

    filepath = matches[0]
    iface = parse_interface_file(filepath)
    iface["content"] = filepath.read_text()
    iface["operation"] = "read"

    output_json(iface)


def cmd_update(args):
    """Update interface field."""
    if not INTERFACE_DIR.exists():
        log_entry('script', 'global', 'ERROR', '[IFACE] Directory does not exist')
        output_json(
            {"operation": "update", "error": "Interface directory does not exist"},
            success=False,
            to_stderr=True,
        )

    # Find interface by number
    pattern = f"{args.number:03d}-*.adoc"
    matches = list(INTERFACE_DIR.glob(pattern))

    if not matches:
        log_entry('script', 'global', 'ERROR', f'[IFACE] Interface {args.number} not found')
        output_json(
            {"operation": "update", "error": f"Interface {args.number} not found"},
            success=False,
            to_stderr=True,
        )

    filepath = matches[0]
    content = filepath.read_text()

    if args.field and args.value:
        # Map field names to section headers
        field_map = {
            "overview": "Overview",
            "type": "Interface Type",
            "input": "Request/Input",
            "output": "Response/Output",
            "errors": "Error Handling",
            "auth": "Authentication & Authorization",
            "versioning": "Versioning",
            "consumers": "Consumers",
            "providers": "Providers",
        }

        if args.field.lower() not in field_map:
            log_entry('script', 'global', 'ERROR', f'[IFACE] Unknown field: {args.field}')
            output_json(
                {
                    "operation": "update",
                    "error": f"Unknown field: {args.field}. Valid: {list(field_map.keys())}",
                },
                success=False,
                to_stderr=True,
            )

        section = field_map[args.field.lower()]
        # Update section content
        pattern = rf"(^== {section}\s*\n\n)(.+?)(\n\n)"
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            content = re.sub(
                pattern,
                rf"\g<1>{args.value}\g<3>",
                content,
                flags=re.MULTILINE | re.DOTALL,
            )
            filepath.write_text(content)

    log_entry('script', 'global', 'INFO', f'[IFACE] Updated INTER-{args.number:03d} field={args.field if args.field else "none"}')
    output_json(
        {
            "operation": "update",
            "number": args.number,
            "path": str(filepath),
            "field": args.field if args.field else "none",
        }
    )


def cmd_delete(args):
    """Delete interface."""
    if not args.force:
        output_json(
            {
                "operation": "delete",
                "error": "Use --force to confirm deletion",
            },
            success=False,
            to_stderr=True,
        )

    if not INTERFACE_DIR.exists():
        log_entry('script', 'global', 'ERROR', '[IFACE] Directory does not exist')
        output_json(
            {"operation": "delete", "error": "Interface directory does not exist"},
            success=False,
            to_stderr=True,
        )

    # Find interface by number
    pattern = f"{args.number:03d}-*.adoc"
    matches = list(INTERFACE_DIR.glob(pattern))

    if not matches:
        log_entry('script', 'global', 'ERROR', f'[IFACE] Interface {args.number} not found')
        output_json(
            {"operation": "delete", "error": f"Interface {args.number} not found"},
            success=False,
            to_stderr=True,
        )

    filepath = matches[0]
    filepath.unlink()

    log_entry('script', 'global', 'INFO', f'[IFACE] Deleted INTER-{args.number:03d}')
    output_json(
        {
            "operation": "delete",
            "number": args.number,
            "path": str(filepath),
            "deleted": True,
        }
    )


def cmd_next_number(args):
    """Get next available interface number."""
    number = get_next_number()
    output_json({"operation": "next-number", "next_number": number})


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Interface specifications in doc/interfaces/",
        epilog="""
Examples:
  # List all interfaces
  %(prog)s list

  # List only REST API interfaces
  %(prog)s list --type REST_API

  # Create new interface
  %(prog)s create --title "User Service API" --type REST_API

  # Read interface by number
  %(prog)s read --number 2

  # Update interface field
  %(prog)s update --number 2 --field overview --value "New description"

  # Delete interface (requires --force)
  %(prog)s delete --number 2 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    list_parser = subparsers.add_parser("list", help="List all interfaces")
    list_parser.add_argument("--type", choices=VALID_TYPES, help="Filter by type")
    list_parser.set_defaults(func=cmd_list)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new interface")
    create_parser.add_argument("--title", required=True, help="Interface title")
    create_parser.add_argument(
        "--type", required=True, choices=VALID_TYPES, help="Interface type"
    )
    create_parser.set_defaults(func=cmd_create)

    # Read command
    read_parser = subparsers.add_parser("read", help="Read interface content")
    read_parser.add_argument(
        "--number", type=int, required=True, help="Interface number"
    )
    read_parser.set_defaults(func=cmd_read)

    # Update command
    update_parser = subparsers.add_parser("update", help="Update interface")
    update_parser.add_argument(
        "--number", type=int, required=True, help="Interface number"
    )
    update_parser.add_argument("--field", help="Field to update")
    update_parser.add_argument("--value", help="New value")
    update_parser.set_defaults(func=cmd_update)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete interface")
    delete_parser.add_argument(
        "--number", type=int, required=True, help="Interface number"
    )
    delete_parser.add_argument(
        "--force", action="store_true", help="Confirm deletion"
    )
    delete_parser.set_defaults(func=cmd_delete)

    # Next-number command
    next_parser = subparsers.add_parser(
        "next-number", help="Get next available number"
    )
    next_parser.set_defaults(func=cmd_next_number)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
