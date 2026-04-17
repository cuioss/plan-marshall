#!/usr/bin/env python3
"""Manage Architectural Decision Records (ADRs) in doc/adr/ directory.

This script provides CRUD operations for ADRs with automatic numbering
and AsciiDoc formatting.

Operations:
    list        - List all ADRs with optional status filter
    create      - Create new ADR from template
    read        - Read ADR content by number
    update      - Update ADR status or content
    delete      - Delete ADR (requires --force)
    next-number - Get next available ADR number

Output format: TOON to stdout
"""

import argparse
import re
from pathlib import Path

from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

# ADR directory relative to project root
ADR_DIR = Path('doc/adr')

# Valid ADR statuses
VALID_STATUSES = ['Proposed', 'Accepted', 'Deprecated', 'Superseded']

# Template placeholders with defaults
TEMPLATE_DEFAULTS = {
    '{{STATUS}}': 'Proposed',
    '{{CONTEXT}}': '// Describe the context and problem',
    '{{DECISION}}': '// Describe the decision',
    '{{POSITIVE_CONSEQUENCES}}': '// List positive outcomes',
    '{{NEGATIVE_CONSEQUENCES}}': '// List negative outcomes',
    '{{RISKS}}': '// List risks',
    '{{ALTERNATIVES}}': '// Describe alternatives',
    '{{REFERENCES}}': '// Add references',
}


def get_template_path() -> Path:
    """Get path to ADR template."""
    script_dir = Path(__file__).parent
    return script_dir.parent / 'templates' / 'adr-template.adoc'


def sanitize_title(title: str) -> str:
    """Sanitize title for filename: remove special chars, replace spaces."""
    # Remove special characters except alphanumeric, spaces, and hyphens
    safe_title = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with underscores
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    return safe_title


def generate_filename(number: int, title: str) -> str:
    """Generate ADR filename from number and title."""
    safe_title = sanitize_title(title)
    return f'{number:03d}-{safe_title}.adoc'


def get_next_number() -> int:
    """Get next available ADR number."""
    if not ADR_DIR.exists():
        return 1

    existing = list(ADR_DIR.glob('*.adoc'))
    if not existing:
        return 1

    numbers = []
    for f in existing:
        match = re.match(r'^(\d{3})-', f.name)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1


def parse_adr_file(filepath: Path) -> dict:
    """Parse ADR file and extract metadata."""
    content = filepath.read_text()

    # Extract number from filename
    match = re.match(r'^(\d{3})-(.+)\.adoc$', filepath.name)
    number = int(match.group(1)) if match else 0

    # Extract title from first line
    title_match = re.match(r'^= ADR-\d+: (.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else 'Unknown'

    # Extract status
    status_match = re.search(r'^== Status\s*\n\n(.+?)(?:\n\n|$)', content, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else 'Unknown'

    return {
        'number': number,
        'title': title,
        'status': status,
        'path': str(filepath),
        'filename': filepath.name,
    }


def cmd_list(args) -> dict:
    """List all ADRs."""
    if not ADR_DIR.exists():
        return {'status': 'success', 'operation': 'list', 'count': 0, 'adrs': []}

    adrs = []
    for filepath in sorted(ADR_DIR.glob('*.adoc')):
        adr = parse_adr_file(filepath)
        if args.status and adr['status'] != args.status:
            continue
        adrs.append(adr)

    return {'status': 'success', 'operation': 'list', 'count': len(adrs), 'adrs': adrs}


def cmd_create(args) -> dict:
    """Create new ADR."""
    # Ensure ADR directory exists
    ADR_DIR.mkdir(parents=True, exist_ok=True)

    # Get next number
    number = get_next_number()

    # Generate filename
    filename = generate_filename(number, args.title)
    filepath = ADR_DIR / filename

    # Check if file already exists
    if filepath.exists():
        log_entry('script', 'global', 'ERROR', f'[ADR] File already exists: {filepath}')
        return {
            'status': 'error',
            'error': 'file_exists',
            'operation': 'create',
            'message': f'ADR file already exists: {filepath}',
        }

    # Load template
    template_path = get_template_path()
    if not template_path.exists():
        log_entry('script', 'global', 'ERROR', f'[ADR] Template not found: {template_path}')
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

    status = args.status if args.status else 'Proposed'
    if status not in VALID_STATUSES:
        log_entry('script', 'global', 'ERROR', f'[ADR] Invalid status: {status}')
        return {
            'status': 'error',
            'error': 'invalid_status',
            'operation': 'create',
            'message': f'Invalid status: {status}. Valid: {VALID_STATUSES}',
        }

    content = content.replace('{{STATUS}}', status)

    # Replace remaining placeholders with defaults
    for placeholder, default in TEMPLATE_DEFAULTS.items():
        if placeholder != '{{STATUS}}':
            content = content.replace(placeholder, default)

    # Write file
    filepath.write_text(content)

    log_entry('script', 'global', 'INFO', f'[ADR] Created ADR-{number:03d}: {args.title}')
    return {
        'status': 'success',
        'operation': 'create',
        'number': number,
        'path': str(filepath),
        'title': args.title,
        'adr_status': status,
    }


def cmd_read(args) -> dict:
    """Read ADR content."""
    if not ADR_DIR.exists():
        return {
            'status': 'error',
            'error': 'dir_not_found',
            'operation': 'read',
            'message': 'ADR directory does not exist',
        }

    # Find ADR by number
    pattern = f'{args.number:03d}-*.adoc'
    matches = list(ADR_DIR.glob(pattern))

    if not matches:
        return {
            'status': 'error',
            'error': 'not_found',
            'operation': 'read',
            'message': f'ADR {args.number} not found',
        }

    filepath = matches[0]
    adr = parse_adr_file(filepath)
    adr['content'] = filepath.read_text()
    adr['status'] = 'success'
    adr['operation'] = 'read'

    return adr


def cmd_update(args) -> dict:
    """Update ADR status or field."""
    if not ADR_DIR.exists():
        log_entry('script', 'global', 'ERROR', '[ADR] Directory does not exist')
        return {
            'status': 'error',
            'error': 'dir_not_found',
            'operation': 'update',
            'message': 'ADR directory does not exist',
        }

    # Find ADR by number
    pattern = f'{args.number:03d}-*.adoc'
    matches = list(ADR_DIR.glob(pattern))

    if not matches:
        log_entry('script', 'global', 'ERROR', f'[ADR] ADR {args.number} not found')
        return {
            'status': 'error',
            'error': 'not_found',
            'operation': 'update',
            'message': f'ADR {args.number} not found',
        }

    filepath = matches[0]
    content = filepath.read_text()

    if args.status:
        if args.status not in VALID_STATUSES:
            log_entry('script', 'global', 'ERROR', f'[ADR] Invalid status: {args.status}')
            return {
                'status': 'error',
                'error': 'invalid_status',
                'operation': 'update',
                'message': f'Invalid status: {args.status}. Valid: {VALID_STATUSES}',
            }

        # Update status section
        content = re.sub(
            r'(^== Status\s*\n\n)(.+?)(\n\n)',
            rf'\g<1>{args.status}\g<3>',
            content,
            flags=re.MULTILINE,
        )
        filepath.write_text(content)

    log_entry(
        'script',
        'global',
        'INFO',
        f'[ADR] Updated ADR-{args.number:03d} status={args.status if args.status else "unchanged"}',
    )
    return {
        'status': 'success',
        'operation': 'update',
        'number': args.number,
        'path': str(filepath),
        'adr_status': args.status if args.status else 'unchanged',
    }


def cmd_delete(args) -> dict:
    """Delete ADR."""
    if not args.force:
        return {
            'status': 'error',
            'error': 'force_required',
            'operation': 'delete',
            'message': 'Use --force to confirm deletion',
        }

    if not ADR_DIR.exists():
        log_entry('script', 'global', 'ERROR', '[ADR] Directory does not exist')
        return {
            'status': 'error',
            'error': 'dir_not_found',
            'operation': 'delete',
            'message': 'ADR directory does not exist',
        }

    # Find ADR by number
    pattern = f'{args.number:03d}-*.adoc'
    matches = list(ADR_DIR.glob(pattern))

    if not matches:
        log_entry('script', 'global', 'ERROR', f'[ADR] ADR {args.number} not found')
        return {
            'status': 'error',
            'error': 'not_found',
            'operation': 'delete',
            'message': f'ADR {args.number} not found',
        }

    filepath = matches[0]
    filepath.unlink()

    log_entry('script', 'global', 'INFO', f'[ADR] Deleted ADR-{args.number:03d}')
    return {
        'status': 'success',
        'operation': 'delete',
        'number': args.number,
        'path': str(filepath),
        'deleted': True,
    }


def cmd_next_number(args) -> dict:
    """Get next available ADR number."""
    number = get_next_number()
    return {'status': 'success', 'operation': 'next-number', 'next_number': number}


@safe_main
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description='Manage Architectural Decision Records (ADRs) in doc/adr/',
        epilog="""
Examples:
  # List all ADRs
  %(prog)s list

  # List only accepted ADRs
  %(prog)s list --status Accepted

  # Create new ADR
  %(prog)s create --title "Use PostgreSQL for persistence"

  # Read ADR by number
  %(prog)s read --number 3

  # Update ADR status
  %(prog)s update --number 3 --status Accepted

  # Delete ADR (requires --force)
  %(prog)s delete --number 3 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List command
    list_parser = subparsers.add_parser('list', help='List all ADRs', allow_abbrev=False)
    list_parser.add_argument('--status', choices=VALID_STATUSES, help='Filter by status')
    list_parser.set_defaults(func=cmd_list)

    # Create command
    create_parser = subparsers.add_parser('create', help='Create new ADR', allow_abbrev=False)
    create_parser.add_argument('--title', required=True, help='ADR title')
    create_parser.add_argument('--status', choices=VALID_STATUSES, default='Proposed', help='Initial status')
    create_parser.set_defaults(func=cmd_create)

    # Read command
    read_parser = subparsers.add_parser('read', help='Read ADR content', allow_abbrev=False)
    read_parser.add_argument('--number', type=int, required=True, help='ADR number')
    read_parser.set_defaults(func=cmd_read)

    # Update command
    update_parser = subparsers.add_parser('update', help='Update ADR', allow_abbrev=False)
    update_parser.add_argument('--number', type=int, required=True, help='ADR number')
    update_parser.add_argument('--status', choices=VALID_STATUSES, help='New status')
    update_parser.set_defaults(func=cmd_update)

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete ADR', allow_abbrev=False)
    delete_parser.add_argument('--number', type=int, required=True, help='ADR number')
    delete_parser.add_argument('--force', action='store_true', help='Confirm deletion')
    delete_parser.set_defaults(func=cmd_delete)

    # Next-number command
    next_parser = subparsers.add_parser('next-number', help='Get next available number', allow_abbrev=False)
    next_parser.set_defaults(func=cmd_next_number)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
