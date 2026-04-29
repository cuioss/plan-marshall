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

Output format: TOON to stdout
"""

import argparse
import re
from pathlib import Path

from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_field_arg,
    parse_args_with_toon_errors,
)
from plan_logging import log_entry  # type: ignore[import-not-found]

# Interface directory relative to project root
INTERFACE_DIR = Path('doc/interfaces')

# Valid interface types
VALID_TYPES = ['REST_API', 'Event', 'gRPC', 'Database', 'File', 'Other']

# Template placeholders with defaults
TEMPLATE_DEFAULTS = {
    '{{OVERVIEW}}': '// Describe the interface purpose',
    '{{INPUT_DEFINITION}}': '// Define input structure',
    '{{OUTPUT_DEFINITION}}': '// Define output structure',
    '{{ERROR_HANDLING}}': '// Document error scenarios',
    '{{AUTH_REQUIREMENTS}}': '// Specify authentication/authorization',
    '{{VERSIONING}}': '// Document versioning approach',
    '{{EXAMPLE_FORMAT}}': 'json',
    '{{REQUEST_EXAMPLE}}': '// Add request example',
    '{{RESPONSE_EXAMPLE}}': '// Add response example',
    '{{CONSUMERS}}': '// List consuming systems',
    '{{PROVIDERS}}': '// List providing systems',
    '{{REFERENCES}}': '// Add references',
}


def get_template_path() -> Path:
    """Get path to interface template."""
    script_dir = Path(__file__).parent
    return script_dir.parent / 'templates' / 'interface-template.adoc'


def sanitize_title(title: str) -> str:
    """Sanitize title for filename: remove special chars, replace spaces."""
    # Remove special characters except alphanumeric, spaces, and hyphens
    safe_title = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with underscores
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    return safe_title


def generate_filename(number: int, title: str) -> str:
    """Generate interface filename from number and title."""
    safe_title = sanitize_title(title)
    return f'{number:03d}-{safe_title}.adoc'


def get_next_number() -> int:
    """Get next available interface number."""
    if not INTERFACE_DIR.exists():
        return 1

    existing = list(INTERFACE_DIR.glob('*.adoc'))
    if not existing:
        return 1

    numbers = []
    for f in existing:
        match = re.match(r'^(\d{3})-', f.name)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1


def parse_interface_file(filepath: Path) -> dict:
    """Parse interface file and extract metadata."""
    content = filepath.read_text()

    # Extract number from filename
    match = re.match(r'^(\d{3})-(.+)\.adoc$', filepath.name)
    number = int(match.group(1)) if match else 0

    # Extract title from first line
    title_match = re.match(r'^= INTER-\d+: (.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else 'Unknown'

    # Extract interface type
    type_match = re.search(r'^== Interface Type\s*\n\n(.+?)(?:\n\n|$)', content, re.MULTILINE)
    interface_type = type_match.group(1).strip() if type_match else 'Unknown'

    return {
        'number': number,
        'title': title,
        'type': interface_type,
        'path': str(filepath),
        'filename': filepath.name,
    }


def cmd_list(args) -> dict:
    """List all interfaces."""
    if not INTERFACE_DIR.exists():
        return {'status': 'success', 'operation': 'list', 'count': 0, 'interfaces': []}

    interfaces = []
    for filepath in sorted(INTERFACE_DIR.glob('*.adoc')):
        iface = parse_interface_file(filepath)
        if args.type and iface['type'] != args.type:
            continue
        interfaces.append(iface)

    return {'status': 'success', 'operation': 'list', 'count': len(interfaces), 'interfaces': interfaces}


def cmd_create(args) -> dict:
    """Create new interface."""
    # Validate type
    if args.type not in VALID_TYPES:
        log_entry('script', 'global', 'ERROR', f'[IFACE] Invalid type: {args.type}')
        return {
            'status': 'error',
            'error': 'invalid_type',
            'operation': 'create',
            'message': f'Invalid type: {args.type}. Valid types: {VALID_TYPES}',
        }

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
        return {
            'status': 'error',
            'error': 'file_exists',
            'operation': 'create',
            'message': f'Interface file already exists: {filepath}',
        }

    # Load template
    template_path = get_template_path()
    if not template_path.exists():
        log_entry('script', 'global', 'ERROR', f'[IFACE] Template not found: {template_path}')
        return {
            'status': 'error',
            'error': 'template_not_found',
            'operation': 'create',
            'message': f'Template not found: {template_path}',
        }

    template_content = template_path.read_text()

    # Replace placeholders
    content = template_content.replace('{{NUMBER}}', f'{number:03d}')
    content = content.replace('{{TITLE}}', args.title)
    content = content.replace('{{INTERFACE_TYPE}}', args.type)

    # Replace remaining placeholders with defaults
    for placeholder, default in TEMPLATE_DEFAULTS.items():
        content = content.replace(placeholder, default)

    # Write file
    filepath.write_text(content)

    log_entry('script', 'global', 'INFO', f'[IFACE] Created INTER-{number:03d}: {args.title}')
    return {
        'status': 'success',
        'operation': 'create',
        'number': number,
        'path': str(filepath),
        'title': args.title,
        'type': args.type,
    }


def cmd_read(args) -> dict:
    """Read interface content."""
    if not INTERFACE_DIR.exists():
        return {
            'status': 'error',
            'error': 'dir_not_found',
            'operation': 'read',
            'message': 'Interface directory does not exist',
        }

    # Find interface by number
    pattern = f'{args.number:03d}-*.adoc'
    matches = list(INTERFACE_DIR.glob(pattern))

    if not matches:
        return {
            'status': 'error',
            'error': 'not_found',
            'operation': 'read',
            'message': f'Interface {args.number} not found',
        }

    filepath = matches[0]
    iface = parse_interface_file(filepath)
    iface['content'] = filepath.read_text()
    iface['status'] = 'success'
    iface['operation'] = 'read'

    return iface


def cmd_update(args) -> dict:
    """Update interface field."""
    if not INTERFACE_DIR.exists():
        log_entry('script', 'global', 'ERROR', '[IFACE] Directory does not exist')
        return {
            'status': 'error',
            'error': 'dir_not_found',
            'operation': 'update',
            'message': 'Interface directory does not exist',
        }

    # Find interface by number
    pattern = f'{args.number:03d}-*.adoc'
    matches = list(INTERFACE_DIR.glob(pattern))

    if not matches:
        log_entry('script', 'global', 'ERROR', f'[IFACE] Interface {args.number} not found')
        return {
            'status': 'error',
            'error': 'not_found',
            'operation': 'update',
            'message': f'Interface {args.number} not found',
        }

    filepath = matches[0]
    content = filepath.read_text()

    if args.field and args.value:
        # Map field names to section headers
        field_map = {
            'overview': 'Overview',
            'type': 'Interface Type',
            'input': 'Request/Input',
            'output': 'Response/Output',
            'errors': 'Error Handling',
            'auth': 'Authentication & Authorization',
            'versioning': 'Versioning',
            'consumers': 'Consumers',
            'providers': 'Providers',
        }

        if args.field.lower() not in field_map:
            log_entry('script', 'global', 'ERROR', f'[IFACE] Unknown field: {args.field}')
            return {
                'status': 'error',
                'error': 'unknown_field',
                'operation': 'update',
                'message': f'Unknown field: {args.field}. Valid: {list(field_map.keys())}',
            }

        section = field_map[args.field.lower()]
        # Update section content
        pattern = rf'(^== {section}\s*\n\n)(.+?)(\n\n)'
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            content = re.sub(
                pattern,
                rf'\g<1>{args.value}\g<3>',
                content,
                flags=re.MULTILINE | re.DOTALL,
            )
            filepath.write_text(content)

    log_entry(
        'script',
        'global',
        'INFO',
        f'[IFACE] Updated INTER-{args.number:03d} field={args.field if args.field else "none"}',
    )
    return {
        'status': 'success',
        'operation': 'update',
        'number': args.number,
        'path': str(filepath),
        'field': args.field if args.field else 'none',
    }


def cmd_delete(args) -> dict:
    """Delete interface."""
    if not args.force:
        return {
            'status': 'error',
            'error': 'force_required',
            'operation': 'delete',
            'message': 'Use --force to confirm deletion',
        }

    if not INTERFACE_DIR.exists():
        log_entry('script', 'global', 'ERROR', '[IFACE] Directory does not exist')
        return {
            'status': 'error',
            'error': 'dir_not_found',
            'operation': 'delete',
            'message': 'Interface directory does not exist',
        }

    # Find interface by number
    pattern = f'{args.number:03d}-*.adoc'
    matches = list(INTERFACE_DIR.glob(pattern))

    if not matches:
        log_entry('script', 'global', 'ERROR', f'[IFACE] Interface {args.number} not found')
        return {
            'status': 'error',
            'error': 'not_found',
            'operation': 'delete',
            'message': f'Interface {args.number} not found',
        }

    filepath = matches[0]
    filepath.unlink()

    log_entry('script', 'global', 'INFO', f'[IFACE] Deleted INTER-{args.number:03d}')
    return {
        'status': 'success',
        'operation': 'delete',
        'number': args.number,
        'path': str(filepath),
        'deleted': True,
    }


def cmd_next_number(args) -> dict:
    """Get next available interface number."""
    number = get_next_number()
    return {'status': 'success', 'operation': 'next-number', 'next_number': number}


@safe_main
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description='Manage Interface specifications in doc/interfaces/',
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

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List command
    list_parser = subparsers.add_parser('list', help='List all interfaces', allow_abbrev=False)
    list_parser.add_argument('--type', choices=VALID_TYPES, help='Filter by type')
    list_parser.set_defaults(func=cmd_list)

    # Create command
    create_parser = subparsers.add_parser('create', help='Create new interface', allow_abbrev=False)
    create_parser.add_argument('--title', required=True, help='Interface title')
    create_parser.add_argument('--type', required=True, choices=VALID_TYPES, help='Interface type')
    create_parser.set_defaults(func=cmd_create)

    # Read command
    read_parser = subparsers.add_parser('read', help='Read interface content', allow_abbrev=False)
    read_parser.add_argument('--number', type=int, required=True, help='Interface number')
    read_parser.set_defaults(func=cmd_read)

    # Update command
    update_parser = subparsers.add_parser('update', help='Update interface', allow_abbrev=False)
    update_parser.add_argument('--number', type=int, required=True, help='Interface number')
    add_field_arg(update_parser, required=False)
    update_parser.add_argument('--value', help='New value')
    update_parser.set_defaults(func=cmd_update)

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete interface', allow_abbrev=False)
    delete_parser.add_argument('--number', type=int, required=True, help='Interface number')
    delete_parser.add_argument('--force', action='store_true', help='Confirm deletion')
    delete_parser.set_defaults(func=cmd_delete)

    # Next-number command
    next_parser = subparsers.add_parser('next-number', help='Get next available number', allow_abbrev=False)
    next_parser.set_defaults(func=cmd_next_number)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
