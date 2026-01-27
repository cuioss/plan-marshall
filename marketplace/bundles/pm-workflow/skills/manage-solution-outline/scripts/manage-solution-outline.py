#!/usr/bin/env python3
"""
Manage solution outline documents.

Solution outlines support ASCII diagrams with box-drawing characters.
Use heredoc with write command to handle special characters properly.

Usage:
    python3 manage-solution-outline.py write --plan-id my-plan <<'EOF'
    # Solution content here
    EOF

    python3 manage-solution-outline.py validate --plan-id my-plan
    python3 manage-solution-outline.py list-deliverables --plan-id my-plan
    python3 manage-solution-outline.py read --plan-id my-plan [--raw]
    python3 manage-solution-outline.py exists --plan-id my-plan
    python3 manage-solution-outline.py get-module-context
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, cast

from _plan_parsing import (  # type: ignore[import-not-found]
    extract_deliverables,
    parse_document_sections,
)
from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

SOLUTION_FILE = 'solution_outline.md'
ARCHITECTURE_DIR = 'project-architecture'
DERIVED_DATA_FILE = 'derived-data.json'
LLM_ENRICHED_FILE = 'llm-enriched.json'


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def get_solution_path(plan_id: str) -> Path:
    """Get the solution outline file path."""
    return cast(Path, base_path('plans', plan_id, SOLUTION_FILE))


def validate_solution_structure(content: str) -> tuple[list[str], list[str], dict[str, Any]]:
    """Validate solution outline document structure against deliverable contract.

    Returns (errors, warnings, info) where:
    - errors: Contract violations that must be fixed
    - warnings: Issues that should be addressed but don't block
    - info: Validation metadata
    """
    errors: list[str] = []
    warnings: list[str] = []
    info: dict[str, Any] = {'sections_found': [], 'deliverable_count': 0, 'deliverables': []}

    sections = parse_document_sections(content)

    # Required sections
    required_sections = ['summary', 'overview', 'deliverables']
    for section in required_sections:
        if section in sections:
            info['sections_found'].append(section)
        else:
            errors.append(f'Missing required section: {section.replace("_", " ").title()}')

    # Optional sections
    optional_sections = ['approach', 'dependencies', 'risks_and_mitigations', 'risks']
    for section in optional_sections:
        if section in sections:
            info['sections_found'].append(section)

    # Extract compatibility from header metadata
    header = sections.get('_header', '')
    for line in header.split('\n'):
        if line.startswith('compatibility:'):
            info['compatibility'] = line.split(':', 1)[1].strip()
            break

    # Validate deliverables section
    if 'deliverables' in sections:
        deliverables = extract_deliverables(sections['deliverables'])
        info['deliverable_count'] = len(deliverables)
        info['deliverables'] = [d['reference'] for d in deliverables]

        if not deliverables:
            errors.append('No numbered deliverables found (expected ### N. Title)')
        else:
            # Validate each deliverable against contract
            for d in deliverables:
                d_errors, d_warnings = validate_deliverable_contract(d)
                errors.extend(d_errors)
                warnings.extend(d_warnings)

    return errors, warnings, info


def validate_deliverable_contract(deliverable: dict) -> tuple[list[str], list[str]]:
    """Validate a single deliverable against the deliverable contract.

    Contract requires:
    - Metadata block with required fields
    - Profiles block with valid profiles
    - Affected files with explicit paths
    - Verification section
    - Success criteria
    """
    errors = []
    warnings = []
    num = deliverable['number']

    # Check 1: Metadata block exists
    metadata = deliverable.get('metadata', {})
    if not metadata:
        errors.append(f'D{num}: Missing **Metadata:** block')
    else:
        # Check 1a: All required metadata fields
        # module is required for skill resolution from architecture
        # Note: profile is now in separate **Profiles:** block, not in metadata
        required_fields = ['change_type', 'execution_mode', 'domain', 'module', 'depends']
        for field in required_fields:
            if field not in metadata:
                errors.append(f'D{num}: Missing metadata field: {field}')

        # Check 1b: Valid change_type
        valid_change_types = ['create', 'modify', 'refactor', 'migrate', 'delete']
        if metadata.get('change_type') and metadata['change_type'] not in valid_change_types:
            errors.append(
                f"D{num}: Invalid change_type '{metadata['change_type']}' (must be one of: {', '.join(valid_change_types)})"
            )

        # Check 1c: Valid execution_mode
        valid_modes = ['automated', 'manual', 'mixed']
        if metadata.get('execution_mode') and metadata['execution_mode'] not in valid_modes:
            errors.append(
                f"D{num}: Invalid execution_mode '{metadata['execution_mode']}' (must be one of: {', '.join(valid_modes)})"
            )

    # Check 2: Profiles block (separate from metadata)
    profiles = deliverable.get('profiles', [])
    valid_profiles = ['implementation', 'testing']
    if not profiles:
        errors.append(f'D{num}: Missing **Profiles:** block')
    else:
        for profile in profiles:
            if profile not in valid_profiles:
                errors.append(
                    f"D{num}: Invalid profile '{profile}' (must be one of: {', '.join(valid_profiles)})"
                )

    # Check 3: Affected files section
    affected_files = deliverable.get('affected_files', [])
    if not affected_files:
        errors.append(f'D{num}: Missing **Affected files:** section')
    else:
        # Check 3a: No wildcards or vague references
        for f in affected_files:
            if '*' in f:
                errors.append(f'D{num}: Wildcard in affected files: {f}')
            if '...' in f:
                errors.append(f'D{num}: Ellipsis in affected files: {f}')
            if 'all ' in f.lower():
                errors.append(f'D{num}: Vague reference in affected files: {f}')
            # Check for reasonable path structure
            if not ('/' in f or f.endswith('.md') or f.endswith('.py')):
                warnings.append(f'D{num}: Unusual file path format: {f}')

    # Check 4: Verification section
    verification = deliverable.get('verification', {})
    if not verification:
        errors.append(f'D{num}: Missing **Verification:** section')
    else:
        if 'command' not in verification:
            warnings.append(f'D{num}: Verification missing Command')
        if 'criteria' not in verification:
            warnings.append(f'D{num}: Verification missing Criteria')

    # Check 5: Success criteria
    if not deliverable.get('has_success_criteria'):
        warnings.append(f'D{num}: Missing **Success Criteria:** section')

    return errors, warnings


# =============================================================================
# Commands
# =============================================================================


def cmd_validate(args) -> int:
    """Validate solution outline structure against deliverable contract."""
    if not validate_plan_id(args.plan_id):
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'invalid_plan_id',
                    'plan_id': args.plan_id,
                    'message': 'Plan ID must be kebab-case (lowercase, hyphens only)',
                }
            )
        )
        return 1

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'document_not_found',
                    'plan_id': args.plan_id,
                    'file': SOLUTION_FILE,
                    'suggestions': [
                        "Write solution using: manage-solution-outline write --plan-id X <<'EOF'",
                        'Check plan_id spelling',
                    ],
                }
            )
        )
        return 1

    content = file_path.read_text(encoding='utf-8')
    errors, warnings, info = validate_solution_structure(content)

    if errors:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'validation_failed',
                    'plan_id': args.plan_id,
                    'issues': errors,
                    'warnings': warnings,
                    'deliverable_count': info['deliverable_count'],
                }
            )
        )
        return 1

    validation = {
        'sections_found': ','.join(info['sections_found']),
        'deliverable_count': info['deliverable_count'],
        'deliverables': info['deliverables'],
    }

    if 'compatibility' in info:
        validation['compatibility'] = info['compatibility']

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': SOLUTION_FILE,
        'validation': validation,
    }

    if warnings:
        result['warnings'] = warnings

    print(serialize_toon(result))
    return 0


def cmd_list_deliverables(args) -> int:
    """List deliverables from solution outline."""
    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        print(
            serialize_toon(
                {'status': 'error', 'error': 'document_not_found', 'plan_id': args.plan_id, 'file': SOLUTION_FILE}
            )
        )
        return 1

    content = file_path.read_text(encoding='utf-8')
    sections = parse_document_sections(content)

    if 'deliverables' not in sections:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'plan_id': args.plan_id,
                    'error': 'section_not_found',
                    'message': 'Deliverables section not found',
                }
            )
        )
        return 1

    deliverables = extract_deliverables(sections['deliverables'])

    print(
        serialize_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'deliverable_count': len(deliverables),
                'deliverables': deliverables,
            }
        )
    )
    return 0


def cmd_read(args) -> int:
    """Read solution outline."""
    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'document_not_found',
                    'plan_id': args.plan_id,
                    'file': SOLUTION_FILE,
                    'suggestions': [
                        "Write solution using: manage-solution-outline write --plan-id X <<'EOF'",
                        'Check plan_id spelling',
                    ],
                }
            )
        )
        return 1

    content = file_path.read_text(encoding='utf-8')

    # Handle --deliverable-number: read specific deliverable
    deliverable_number = getattr(args, 'deliverable_number', None)
    if deliverable_number is not None:
        sections = parse_document_sections(content)
        if 'deliverables' not in sections:
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': 'section_not_found',
                        'plan_id': args.plan_id,
                        'message': 'Deliverables section not found',
                    }
                )
            )
            return 1

        deliverables = extract_deliverables(sections['deliverables'])

        for d in deliverables:
            if d['number'] == deliverable_number:
                print(
                    serialize_toon(
                        {
                            'status': 'success',
                            'plan_id': args.plan_id,
                            'deliverable': d,
                        }
                    )
                )
                return 0

        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'deliverable_not_found',
                    'plan_id': args.plan_id,
                    'number': deliverable_number,
                    'available': [d['number'] for d in deliverables],
                }
            )
        )
        return 1

    if getattr(args, 'raw', False):
        print(content)
    else:
        sections = parse_document_sections(content)
        print(
            serialize_toon({'status': 'success', 'plan_id': args.plan_id, 'file': SOLUTION_FILE, 'content': sections})
        )

    return 0


def cmd_exists(args) -> int:
    """Check if solution outline exists."""
    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    file_path = get_solution_path(args.plan_id)
    exists = file_path.exists()

    print(serialize_toon({'status': 'success', 'plan_id': args.plan_id, 'file': SOLUTION_FILE, 'exists': exists}))

    return 0 if exists else 1


def cmd_write(args) -> int:
    """Write solution outline from stdin with automatic contract validation.

    Reads content from stdin to support ASCII diagrams with box-drawing characters.
    ALWAYS validates against the deliverable contract before writing.
    Returns error if validation fails (file is NOT written).
    """
    if not validate_plan_id(args.plan_id):
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'invalid_plan_id',
                    'plan_id': args.plan_id,
                    'message': 'Plan ID must be kebab-case (lowercase, hyphens only)',
                }
            )
        )
        return 1

    # Read content from stdin
    content = sys.stdin.read()

    if not content.strip():
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'empty_content',
                    'plan_id': args.plan_id,
                    'message': 'Content cannot be empty',
                }
            )
        )
        return 1

    # ALWAYS validate before writing
    errors, warnings, info = validate_solution_structure(content)

    if errors:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'validation_failed',
                    'plan_id': args.plan_id,
                    'issues': errors,
                    'warnings': warnings,
                    'deliverable_count': info['deliverable_count'],
                }
            )
        )
        return 1

    file_path = get_solution_path(args.plan_id)
    existed_before = file_path.exists()

    # Check if exists and --force not specified
    if existed_before and not getattr(args, 'force', False):
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'file_exists',
                    'plan_id': args.plan_id,
                    'file': SOLUTION_FILE,
                    'message': 'Solution outline already exists. Use --force to overwrite.',
                }
            )
        )
        return 1

    # Ensure plan directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically
    atomic_write_file(file_path, content)

    validation = {
        'deliverable_count': info['deliverable_count'],
        'sections_found': ','.join(info['sections_found']),
    }

    if 'compatibility' in info:
        validation['compatibility'] = info['compatibility']

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': SOLUTION_FILE,
        'action': 'updated' if existed_before else 'created',
        'validation': validation,
    }

    if warnings:
        result['warnings'] = warnings

    print(serialize_toon(result))
    return 0


def cmd_get_module_context(args) -> int:
    """Get project architecture context for placement decisions.

    Reads .plan/project-architecture/ files and returns module information
    to help with file placement decisions during solution outline creation.
    """
    plan_base = base_path()
    arch_dir = plan_base / ARCHITECTURE_DIR
    derived_path = arch_dir / DERIVED_DATA_FILE
    enriched_path = arch_dir / LLM_ENRICHED_FILE

    if not derived_path.exists():
        print(
            serialize_toon(
                {
                    'status': 'not_found',
                    'file': str(arch_dir),
                    'message': 'Project architecture not discovered. Run architecture discovery first.',
                    'suggestion': 'Run: python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture discover',
                }
            )
        )
        return 0  # Not an error - just means no architecture available

    try:
        import json

        with open(derived_path, encoding='utf-8') as f:
            derived_data = json.load(f)

        enriched_data = {}
        if enriched_path.exists():
            with open(enriched_path, encoding='utf-8') as f:
                enriched_data = json.load(f)
    except Exception as e:
        print(serialize_toon({'status': 'error', 'error': 'parse_error', 'file': str(arch_dir), 'message': str(e)}))
        return 1

    # Extract modules from derived data
    derived_modules = derived_data.get('modules', {})
    enriched_modules = enriched_data.get('modules', {})

    # Build context for LLM
    modules_list: list[dict] = []
    context = {'status': 'success', 'module_count': len(derived_modules), 'modules': modules_list}

    for name, mod in derived_modules.items():
        enriched = enriched_modules.get(name, {})
        paths = mod.get('paths', {})
        module_info = {
            'name': name,
            'path': paths.get('module', '.'),
            'purpose': enriched.get('purpose', 'unknown'),
            'responsibility': enriched.get('responsibility', ''),
        }
        if enriched.get('key_packages'):
            module_info['key_packages'] = list(enriched['key_packages'].keys())
        if enriched.get('tips'):
            module_info['tips'] = enriched['tips']
        if enriched.get('insights'):
            module_info['insights'] = enriched['insights']
        if enriched.get('skills_by_profile'):
            module_info['skills_by_profile'] = enriched['skills_by_profile']
        modules_list.append(module_info)

    print(serialize_toon(context))
    return 0


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='Manage solution outline documents')
    subparsers = parser.add_subparsers(dest='command', help='Command')

    # validate
    validate_parser = subparsers.add_parser('validate', help='Validate solution structure')
    validate_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    validate_parser.set_defaults(func=cmd_validate)

    # list-deliverables
    list_parser = subparsers.add_parser('list-deliverables', help='Extract deliverables')
    list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    list_parser.set_defaults(func=cmd_list_deliverables)

    # read
    read_parser = subparsers.add_parser('read', help='Read solution outline')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    read_parser.add_argument('--raw', action='store_true', help='Output raw content')
    read_parser.add_argument('--deliverable-number', type=int, help='Read specific deliverable by number')
    read_parser.set_defaults(func=cmd_read)

    # exists
    exists_parser = subparsers.add_parser('exists', help='Check if solution exists')
    exists_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    exists_parser.set_defaults(func=cmd_exists)

    # write
    write_parser = subparsers.add_parser('write', help='Write solution outline from stdin (validates automatically)')
    write_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    write_parser.add_argument('--force', action='store_true', help='Overwrite existing file')
    write_parser.set_defaults(func=cmd_write)

    # get-module-context
    context_parser = subparsers.add_parser('get-module-context', help='Get project structure context for placement')
    context_parser.set_defaults(func=cmd_get_module_context)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
