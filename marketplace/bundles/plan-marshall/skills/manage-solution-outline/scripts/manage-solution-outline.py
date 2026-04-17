#!/usr/bin/env python3
"""
Manage solution outline documents.

Solution outlines support ASCII diagrams with box-drawing characters.
Content is written externally via Write tool, then validated by this script.

Usage:
    # Get target path for direct file write
    python3 manage-solution-outline.py resolve-path --plan-id my-plan

    # Validate existing file on disk
    python3 manage-solution-outline.py write --plan-id my-plan [--force]
    python3 manage-solution-outline.py update --plan-id my-plan

    python3 manage-solution-outline.py validate --plan-id my-plan
    python3 manage-solution-outline.py list-deliverables --plan-id my-plan
    python3 manage-solution-outline.py read --plan-id my-plan [--raw]
    python3 manage-solution-outline.py exists --plan-id my-plan
    python3 manage-solution-outline.py get-module-context
"""

import argparse
from pathlib import Path
from typing import Any, cast

from _plan_parsing import (  # type: ignore[import-not-found]
    extract_deliverables,
    parse_document_sections,
)
from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg, require_valid_plan_id  # type: ignore[import-not-found]

SOLUTION_FILE = 'solution_outline.md'
ARCHITECTURE_DIR = 'project-architecture'
DERIVED_DATA_FILE = 'derived-data.json'
LLM_ENRICHED_FILE = 'llm-enriched.json'


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

        # Check 1b: Valid change_type (canonical vocabulary from change-types.md)
        valid_change_types = [
            'analysis',
            'feature',
            'enhancement',
            'bug_fix',
            'tech_debt',
            'verification',
        ]
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
    valid_profiles = ['implementation', 'module_testing', 'integration_testing', 'verification']
    if not profiles:
        errors.append(f'D{num}: Missing **Profiles:** block')
    else:
        for profile in profiles:
            if profile not in valid_profiles:
                errors.append(f"D{num}: Invalid profile '{profile}' (must be one of: {', '.join(valid_profiles)})")

    # Check 2b: Warn when module_testing profile but no test files in affected files
    affected_files = deliverable.get('affected_files', [])
    if 'module_testing' in profiles and affected_files:
        test_indicators = ('test/', 'Test.', '_test.', 'test_', '.test.', 'spec/', '/tests/')
        has_test_files = any(any(indicator in f for indicator in test_indicators) for f in affected_files)
        if not has_test_files:
            warnings.append(
                f'D{num}: module_testing profile but no test files detected in affected files '
                f'(expected paths containing: test/, Test., _test., test_, .test., spec/)'
            )

    # Check 3: Affected files section
    affected_files = deliverable.get('affected_files', [])
    is_verification_only = 'verification' in profiles
    if not affected_files and not is_verification_only:
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


def cmd_validate(args) -> dict:
    """Validate solution outline structure against deliverable contract."""
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        return {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'suggestions': [
                'Use resolve-path to get the target path, then Write tool to create the file',
                'Check plan_id spelling',
            ],
        }

    content = file_path.read_text(encoding='utf-8')
    errors, warnings, info = validate_solution_structure(content)

    if errors:
        return {
            'status': 'error',
            'error': 'validation_failed',
            'plan_id': args.plan_id,
            'issues': errors,
            'warnings': warnings,
            'deliverable_count': info['deliverable_count'],
        }

    validation = {
        'sections_found': ','.join(info['sections_found']),
        'deliverable_count': info['deliverable_count'],
        'deliverables': info['deliverables'],
    }

    if 'compatibility' in info:
        validation['compatibility'] = info['compatibility']

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': SOLUTION_FILE,
        'validation': validation,
    }

    if warnings:
        result['warnings'] = warnings

    return result


def cmd_list_deliverables(args) -> dict:
    """List deliverables from solution outline."""
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        return {'status': 'error', 'error': 'document_not_found', 'plan_id': args.plan_id, 'file': SOLUTION_FILE}

    content = file_path.read_text(encoding='utf-8')
    sections = parse_document_sections(content)

    if 'deliverables' not in sections:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'section_not_found',
            'message': 'Deliverables section not found',
        }

    deliverables = extract_deliverables(sections['deliverables'])

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'deliverable_count': len(deliverables),
        'deliverables': deliverables,
    }


def cmd_read(args) -> dict:
    """Read solution outline."""
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        return {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'suggestions': [
                'Use resolve-path to get the target path, then Write tool to create the file',
                'Check plan_id spelling',
            ],
        }

    content = file_path.read_text(encoding='utf-8')

    # Handle --deliverable-number: read specific deliverable
    deliverable_number = getattr(args, 'deliverable_number', None)
    if deliverable_number is not None:
        sections = parse_document_sections(content)
        if 'deliverables' not in sections:
            return {
                'status': 'error',
                'error': 'section_not_found',
                'plan_id': args.plan_id,
                'message': 'Deliverables section not found',
            }

        deliverables = extract_deliverables(sections['deliverables'])

        for d in deliverables:
            if d['number'] == deliverable_number:
                return {
                    'status': 'success',
                    'plan_id': args.plan_id,
                    'deliverable': d,
                }

        return {
            'status': 'error',
            'error': 'deliverable_not_found',
            'plan_id': args.plan_id,
            'number': deliverable_number,
            'available': [d['number'] for d in deliverables],
        }

    if getattr(args, 'raw', False):
        print(content)
        return {'status': 'success', 'plan_id': args.plan_id, 'file': SOLUTION_FILE, 'raw': True}
    else:
        sections = parse_document_sections(content)
        return {'status': 'success', 'plan_id': args.plan_id, 'file': SOLUTION_FILE, 'content': sections}


def cmd_exists(args) -> dict:
    """Check if solution outline exists."""
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)
    exists = file_path.exists()

    return {'status': 'success', 'plan_id': args.plan_id, 'file': SOLUTION_FILE, 'exists': exists}


def _validate_file_on_disk(plan_id: str, file_path: Path) -> tuple[int, dict[str, Any]]:
    """Validate solution outline file already on disk.

    Returns (exit_code, result_dict). exit_code 0 means success.
    Does NOT print - caller is responsible for output.
    """
    if not file_path.exists():
        return 1, {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': plan_id,
            'file': SOLUTION_FILE,
            'suggestions': [
                'Use resolve-path to get the target path, then Write tool to create the file',
                'Check plan_id spelling',
            ],
        }

    content = file_path.read_text(encoding='utf-8')

    if not content.strip():
        return 1, {
            'status': 'error',
            'error': 'empty_content',
            'plan_id': plan_id,
            'message': 'Content cannot be empty',
        }

    errors, warnings, info = validate_solution_structure(content)

    if errors:
        return 1, {
            'status': 'error',
            'error': 'validation_failed',
            'plan_id': plan_id,
            'issues': errors,
            'warnings': warnings,
            'deliverable_count': info['deliverable_count'],
        }

    validation = {
        'deliverable_count': info['deliverable_count'],
        'sections_found': ','.join(info['sections_found']),
    }

    if 'compatibility' in info:
        validation['compatibility'] = info['compatibility']

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'file': SOLUTION_FILE,
        'validation': validation,
    }

    if warnings:
        result['warnings'] = warnings

    return 0, result


def cmd_resolve_path(args) -> dict:
    """Return the target file path for the solution outline.

    Used by LLM to get the path for direct file write via Write tool.
    """
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'path': str(file_path),
        'exists': file_path.exists(),
    }


def cmd_write(args) -> dict:
    """Validate solution outline already written to disk.

    File must be written externally (via Write tool) before calling this command.
    Validates against the deliverable contract. Use --force to allow overwriting
    an existing file (checked before external write via resolve-path exists field).
    """
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)

    _exit_code, result = _validate_file_on_disk(args.plan_id, file_path)
    if result.get('status') == 'success':
        result['action'] = 'created'
    return result


def cmd_update(args) -> dict:
    """Validate an updated solution outline already written to disk.

    File must already exist and be updated externally (via Write tool).
    Validates against the deliverable contract.
    """
    require_valid_plan_id(args)

    file_path = get_solution_path(args.plan_id)

    if not file_path.exists():
        return {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'message': 'Cannot update: solution outline does not exist. Use write to create it.',
        }

    _exit_code, result = _validate_file_on_disk(args.plan_id, file_path)
    if result.get('status') == 'success':
        result['action'] = 'updated'
    return result


def cmd_get_module_context(args) -> dict:
    """Get project architecture context for placement decisions.

    Reads .plan/project-architecture/ files and returns module information
    to help with file placement decisions during solution outline creation.
    """
    plan_base = base_path()
    arch_dir = plan_base / ARCHITECTURE_DIR
    derived_path = arch_dir / DERIVED_DATA_FILE
    enriched_path = arch_dir / LLM_ENRICHED_FILE

    if not derived_path.exists():
        return {
            'status': 'not_found',
            'file': str(arch_dir),
            'message': 'Project architecture not discovered. Run architecture discovery first.',
            'suggestion': 'Run: python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover',
        }

    try:
        import json

        with open(derived_path, encoding='utf-8') as f:
            derived_data = json.load(f)

        enriched_data = {}
        if enriched_path.exists():
            with open(enriched_path, encoding='utf-8') as f:
                enriched_data = json.load(f)
    except Exception as e:
        return {'status': 'error', 'error': 'parse_error', 'file': str(arch_dir), 'message': str(e)}

    # Extract modules from derived data
    derived_modules = derived_data.get('modules', {})
    enriched_modules = enriched_data.get('modules', {})

    # Build context for LLM
    modules_list: list[dict] = []
    context: dict[str, Any] = {'status': 'success', 'module_count': len(derived_modules), 'modules': modules_list}

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

    return context


# =============================================================================
# Main
# =============================================================================


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Manage solution outline documents', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True, help='Command')

    # validate
    validate_parser = subparsers.add_parser('validate', help='Validate solution structure', allow_abbrev=False)
    add_plan_id_arg(validate_parser)
    validate_parser.set_defaults(func=cmd_validate)

    # list-deliverables
    list_parser = subparsers.add_parser('list-deliverables', help='Extract deliverables', allow_abbrev=False)
    add_plan_id_arg(list_parser)
    list_parser.set_defaults(func=cmd_list_deliverables)

    # read
    read_parser = subparsers.add_parser('read', help='Read solution outline', allow_abbrev=False)
    add_plan_id_arg(read_parser)
    read_parser.add_argument('--raw', action='store_true', help='Output raw content')
    read_parser.add_argument('--deliverable-number', type=int, help='Read specific deliverable by number')
    read_parser.set_defaults(func=cmd_read)

    # exists
    exists_parser = subparsers.add_parser('exists', help='Check if solution exists', allow_abbrev=False)
    add_plan_id_arg(exists_parser)
    exists_parser.set_defaults(func=cmd_exists)

    # resolve-path
    resolve_parser = subparsers.add_parser(
        'resolve-path', help='Get target file path for direct Write', allow_abbrev=False
    )
    add_plan_id_arg(resolve_parser)
    resolve_parser.set_defaults(func=cmd_resolve_path)

    # write
    write_parser = subparsers.add_parser(
        'write', help='Validate solution outline on disk (written via Write tool)', allow_abbrev=False
    )
    add_plan_id_arg(write_parser)
    write_parser.add_argument('--force', action='store_true', help='(legacy, ignored)')
    write_parser.set_defaults(func=cmd_write)

    # update
    update_parser = subparsers.add_parser(
        'update',
        help='Validate updated solution outline on disk (written via Write tool)',
        allow_abbrev=False,
    )
    add_plan_id_arg(update_parser)
    update_parser.set_defaults(func=cmd_update)

    # get-module-context
    context_parser = subparsers.add_parser(
        'get-module-context', help='Get project structure context for placement', allow_abbrev=False
    )
    context_parser.set_defaults(func=cmd_get_module_context)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
