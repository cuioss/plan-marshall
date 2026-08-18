#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Manage solution outline documents.

Solution outlines support ASCII diagrams with box-drawing characters.
Content is written externally via Write tool, then validated by this script.

Usage:
    # Get target path for direct file write
    python3 manage-solution-outline.py resolve-path --plan-id EXAMPLE-PLAN

    # Validate existing file on disk
    python3 manage-solution-outline.py write --plan-id EXAMPLE-PLAN [--force]
    python3 manage-solution-outline.py update --plan-id EXAMPLE-PLAN

    python3 manage-solution-outline.py validate --plan-id EXAMPLE-PLAN
    python3 manage-solution-outline.py list-deliverables --plan-id EXAMPLE-PLAN
    python3 manage-solution-outline.py read --plan-id EXAMPLE-PLAN [--raw | --section summary | --deliverable-number N]
    python3 manage-solution-outline.py get-deliverable --plan-id EXAMPLE-PLAN --deliverable-number N
    python3 manage-solution-outline.py exists --plan-id EXAMPLE-PLAN
    python3 manage-solution-outline.py get-module-context
"""

import argparse
from pathlib import Path
from typing import Any, cast

import resolve_project_dir as _routing
from _architecture_core import (
    DataNotFoundError,
    get_project_meta_path,
    iter_modules,
    load_module_derived,
    load_module_enriched_or_empty,
    load_project_meta,
)
from _plan_parsing import (
    _slugify_section_name,
    deliverable_write_set,
    extract_deliverables,
    is_foreign_path,
    parse_document_sections,
)
from constants import VALID_STEP_INTENTS
from file_ops import base_path, cwd_checkout_root, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)

SOLUTION_FILE = 'solution_outline.md'

# Solution-level metadata: scope_estimate enum (see standards/solution-outline-standard.md)
SCOPE_ESTIMATE_VALUES = ('none', 'surgical', 'single_module', 'multi_module', 'broad')

# Allowlist of solution-level fields readable via `get-field`.
SUPPORTED_FIELDS = ('scope_estimate',)


def extract_scope_estimate(solution_metadata: str) -> str | None:
    """Extract scope_estimate value from the Solution Metadata section body.

    Looks for a line matching ``- scope_estimate: VALUE`` (with optional leading
    whitespace and tolerant of `*` bullets). Returns the trimmed value, or
    ``None`` when the field is absent.
    """
    if not solution_metadata:
        return None
    for raw_line in solution_metadata.split('\n'):
        line = raw_line.strip()
        # Accept "- scope_estimate: X", "* scope_estimate: X", or "scope_estimate: X"
        if line.startswith('- '):
            line = line[2:].strip()
        elif line.startswith('* '):
            line = line[2:].strip()
        if line.startswith('scope_estimate:'):
            return line.split(':', 1)[1].strip()
    return None


def get_solution_path(plan_id: str) -> Path:
    """Get the solution outline file path."""
    return cast(Path, base_path('plans', plan_id, SOLUTION_FILE))


def _read_solution_or_not_found(plan_id: str) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the solution outline path, guarding the ``document_not_found`` case.

    Shared by ``cmd_read`` and ``cmd_get_deliverable``, which both perform the
    identical guard: resolve the path, return the ``document_not_found`` error
    dict (with the standard ``suggestions``) when the file is absent, otherwise
    read and return the file content.

    Returns ``(error_dict, None)`` when the file does not exist, or
    ``(None, content)`` when it does. Exactly one element is non-``None``.
    """
    file_path = get_solution_path(plan_id)
    if not file_path.exists():
        return {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': plan_id,
            'file': SOLUTION_FILE,
            'suggestions': [
                'Use resolve-path to get the target path, then Write tool to create the file',
                'Check plan_id spelling',
            ],
        }, None
    return None, file_path.read_text(encoding='utf-8')


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

    # Required sections (Solution Metadata first to keep ordering stable)
    required_sections = ['solution_metadata', 'summary', 'overview', 'deliverables']
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

    # Validate Solution Metadata block: scope_estimate is required and must be in enum.
    solution_metadata_body = sections.get('solution_metadata', '')
    if 'solution_metadata' in sections:
        scope_value = extract_scope_estimate(solution_metadata_body)
        if scope_value is None:
            errors.append('Missing scope_estimate in Solution Metadata')
        elif scope_value not in SCOPE_ESTIMATE_VALUES:
            errors.append(
                f"Invalid scope_estimate '{scope_value}' (must be one of: {', '.join(SCOPE_ESTIMATE_VALUES)})"
            )
        else:
            info['scope_estimate'] = scope_value

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


#: The bucket value asserting a deliverable changes no code.
_DOCUMENTATION_ONLY_BUCKET = 'documentation_only'


def _write_set_is_all_documentation(write_set: list[str]) -> bool | None:
    """Whether EVERY declared write is documentation by the owner-less rule.

    Delegates to ``_manifest_core._is_documentation_path`` — the aggregator's own
    extension-agnostic documentation predicate — rather than restating a suffix
    list here. A second copy of "what counts as documentation" is exactly the
    drift that lets the declared bucket and the derived one disagree while both
    look right.

    Returns ``None`` when the predicate cannot be imported, so the caller skips
    the check rather than guessing. The import is deferred and fail-open for the
    same reason ``_findings_core`` is elsewhere in this tree: outline validation
    must not hard-fail because a sibling skill's module is unavailable on the
    current path.
    """
    try:
        from _manifest_core import _is_documentation_path
    except ImportError:
        return None
    return all(_is_documentation_path(path) for path in write_set)


def _check_declared_bucket(
    num: int, deliverable: dict[str, Any], write_set: list[str]
) -> list[str]:
    """Check the recorded ``<!-- bucket: X -->`` against the declared write-set.

    The bucket is the audit trail for the deliverable's profile assignment, and
    it was authored by hand and read back by nobody — so a bucket that
    contradicted the very files it describes reached phase-4-plan unchallenged,
    and the profiles it licensed rode along with it.

    **Exactly one contradiction is adjudicated, and it is the only one this
    layer can PROVE.** When every declared write is documentation by suffix, the
    aggregator's bucket is necessarily ``documentation_only``: stage 1 of
    ``_classify_paths_via_extensions`` splits doc paths out *before* the build
    extensions run, so no extension sees them, no other role can be claimed, and
    the collapse has only ``documentation`` to work with. Any other declared
    bucket over that write-set is therefore false, and it is the shape a
    read-only reference produces — a consulted ``.py`` or test file in
    ``affected_files`` pulling a docs-only deliverable onto the code path.

    **The converse is NOT adjudicated, deliberately.** A write-set containing a
    non-doc path may still resolve to ``documentation_only``: infrastructure
    config collapses to it (the ``config`` role is excluded from the plan-wide
    collapse), a template whose render target is a doc or config takes that
    role, and a build extension may itself claim a path as ``config``. Deciding
    which of those applies needs ``BuildExtensionBase.classify_paths``, which
    this layer does not have. Erroring on the un-decidable case would reject an
    outline whose bucket is exactly what the classifier mandates — an
    infra-only deliverable resolves ``documentation_only``, and phase-3-outline's
    own standard says so — so the case is left to the aggregator rather than
    approximated. Approximating it is the second-weaker-classifier defect this
    check exists to catch, and building one here would be committing it.

    A deliverable with an empty write-set is skipped — a verification-only
    deliverable declares no writes, so there is nothing for a bucket to
    contradict.
    """
    declared = deliverable.get('declared_bucket')
    if not declared or not write_set:
        return []
    if declared.strip().lower() == _DOCUMENTATION_ONLY_BUCKET:
        return []
    if not _write_set_is_all_documentation(write_set):
        return []
    return [
        f'D{num}: declared bucket {declared!r} contradicts the write-set, in which '
        f'every changed file is documentation: {write_set}. A file declared '
        f'(read) is consulted, not changed, and must not decide the bucket.'
    ]


def validate_deliverable_contract(deliverable: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Validate a single deliverable against the deliverable contract.

    Contract requires:
    - Metadata block with required fields
    - Profiles block with valid profiles
    - A declared file-type bucket consistent with the declared write-set
    - Affected files with explicit paths
    - Verification section
    - Success criteria
    """
    errors: list[str] = []
    warnings: list[str] = []
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

    # Check 2b: Warn when module_testing profile but no test files in the WRITE-SET.
    # The write-set, not the whole affected-files list: a deliverable that merely
    # READS a test file for reference has not thereby acquired a test surface, and
    # scanning the wholesale list let one such reference satisfy the profile.
    # No non-empty guard on the write-set: a module_testing deliverable whose
    # every entry is `(read)` has an EMPTY write-set and no written test file at
    # all, which is the sharpest instance of the case this check exists to
    # report. Guarding on non-emptiness silenced the check precisely there. A
    # verification-only deliverable is unaffected — it does not carry the
    # module_testing profile, so the profile test above already excludes it.
    write_set = deliverable_write_set(deliverable)
    if 'module_testing' in profiles:
        test_indicators = ('test/', 'Test.', '_test.', 'test_', '.test.', 'spec/', '/tests/')
        has_test_files = any(
            any(indicator in path for indicator in test_indicators) for path in write_set
        )
        if not has_test_files:
            warnings.append(
                f'D{num}: module_testing profile but no test files detected in the declared '
                f'write-set (expected paths containing: test/, Test., _test., test_, .test., spec/)'
            )

    # Check 2c: the declared file-type bucket must agree with the write-set.
    errors.extend(_check_declared_bucket(num, deliverable, write_set))

    # Check 3: Affected files section
    #
    # A SURVEY-SCOPE deliverable declares `**Files to survey:**` +
    # `**Files expected to mutate:**` INSTEAD of a flat `**Affected files:**`
    # list (see phase-3-outline/standards/outline-workflow-detail.md § "Survey-
    # scope vs mutation-scope declaration"), so the section requirement is
    # satisfied by either form. Without this, an outline authored exactly as
    # that standard mandates failed validation with "Missing **Affected
    # files:** section" — the validator and the authoring standard disagreed
    # about what a declaration looks like.
    #
    # Only `affected_files` is walked by 3a/3b below, deliberately. The survey
    # pair's documented form carries no `(intent)` markers, and its candidate
    # pool MAY legitimately name a glob — both of which 3a/3b reject. The
    # closure reconciliation that DOES read the survey pair (a declared glob
    # against the enumerated file list) lives in the phase-4-plan mechanical
    # Q-Gate, where it can compare the declaration against the tree.
    affected_files = deliverable.get('affected_files', [])
    survey_scope = deliverable.get('survey_scope', []) or []
    mutation_scope = deliverable.get('mutation_scope', []) or []
    declares_survey_pair = bool(survey_scope) and bool(mutation_scope)
    is_verification_only = 'verification' in profiles
    if not affected_files and not declares_survey_pair and not is_verification_only:
        errors.append(f'D{num}: Missing **Affected files:** section')
    else:
        # Check 3a: No wildcards or vague references; Check 3b: required intent marker.
        for entry in affected_files:
            path = entry.get('path', '')
            intent = entry.get('intent')
            if '*' in path:
                errors.append(f'D{num}: Wildcard in affected files: {path}')
            if '...' in path:
                errors.append(f'D{num}: Ellipsis in affected files: {path}')
            if 'all ' in path.lower():
                errors.append(f'D{num}: Vague reference in affected files: {path}')
            # Check for reasonable path structure
            if not ('/' in path or path.endswith('.md') or path.endswith('.py')):
                warnings.append(f'D{num}: Unusual file path format: {path}')
            # Check 3b: every entry MUST carry a valid intent marker.
            if intent is None:
                errors.append(
                    f"D{num}: Affected file '{path}' missing intent marker "
                    f'(read|write-new|write-replace|delete)'
                )
            elif intent not in VALID_STEP_INTENTS:
                errors.append(
                    f"D{num}: Affected file '{path}' has invalid intent marker '{intent}' "
                    f'(must be one of: {", ".join(VALID_STEP_INTENTS)})'
                )

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


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
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
    if 'scope_estimate' in info:
        validation['scope_estimate'] = info['scope_estimate']

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': SOLUTION_FILE,
        'validation': validation,
    }

    if warnings:
        result['warnings'] = warnings

    return result


def cmd_list_deliverables(args: argparse.Namespace) -> dict[str, Any]:
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
    _annotate_foreign(deliverables)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'deliverable_count': len(deliverables),
        'deliverables': deliverables,
    }


def _annotate_foreign(deliverables: list[dict[str, Any]]) -> None:
    """Stamp a ``foreign`` flag onto every deliverable and each of its
    ``affected_files`` entries, in place.

    Each ``affected_files`` entry gains ``foreign: true/false`` derived from
    :func:`is_foreign_path` against the project root (the git toplevel), and the
    deliverable gains a roll-up ``foreign: true`` when ANY of its paths is
    foreign. This is what lets a coverage ratio separate the two populations
    (host vs foreign) instead of silently pooling them, and it is the population
    the phase-6 pre-archive landing gate iterates.

    The project root is resolved once via :func:`cwd_checkout_root`. When the
    root cannot be resolved (not in a git checkout), every path is classified
    host (``foreign: false``) — the fail-open direction here is deliberate: the
    column is an *advisory* population marker, and the blocking decision lives in
    the landing gate, which resolves the root explicitly.
    """
    try:
        project_root = cwd_checkout_root()
    except Exception:
        project_root = None

    for deliverable in deliverables:
        any_foreign = False
        for entry in deliverable.get('affected_files', []):
            is_foreign = project_root is not None and is_foreign_path(entry.get('path', ''), project_root)
            entry['foreign'] = is_foreign
            any_foreign = any_foreign or is_foreign
        deliverable['foreign'] = any_foreign


def _lookup_deliverable(plan_id: str, content: str, deliverable_number: int) -> dict[str, Any]:
    """Look up a single deliverable by number within solution outline content.

    Shared by ``cmd_read`` (``--deliverable-number`` branch) and
    ``cmd_get_deliverable``. Parses the document sections, guards the missing
    Deliverables section, iterates the extracted deliverables, and returns the
    matched deliverable dict on success. The error and success shapes mirror the
    ``read --deliverable-number`` contract exactly:

    - ``section_not_found`` when the Deliverables section is absent
    - ``deliverable_not_found`` (with ``available`` numbers) when no deliverable
      matches ``deliverable_number``
    - ``success`` (with the ``deliverable`` payload) on match
    """
    sections = parse_document_sections(content)
    if 'deliverables' not in sections:
        return {
            'status': 'error',
            'error': 'section_not_found',
            'plan_id': plan_id,
            'message': 'Deliverables section not found',
        }

    deliverables = extract_deliverables(sections['deliverables'])

    for d in deliverables:
        if d['number'] == deliverable_number:
            return {
                'status': 'success',
                'plan_id': plan_id,
                'deliverable': d,
            }

    return {
        'status': 'error',
        'error': 'deliverable_not_found',
        'plan_id': plan_id,
        'number': deliverable_number,
        'available': [d['number'] for d in deliverables],
    }


def cmd_read(args: argparse.Namespace) -> dict[str, Any]:
    """Read solution outline."""
    require_valid_plan_id(args)

    error, content = _read_solution_or_not_found(args.plan_id)
    if error is not None:
        return error
    content = cast(str, content)

    # Handle --deliverable-number: read specific deliverable
    deliverable_number = getattr(args, 'deliverable_number', None)
    if deliverable_number is not None:
        return _lookup_deliverable(args.plan_id, content, deliverable_number)

    # Handle --section: read specific top-level ## section
    requested_section = getattr(args, 'section', None)
    if requested_section is not None:
        normalized = _slugify_section_name(requested_section)
        sections = parse_document_sections(content)
        if normalized not in sections:
            return {
                'status': 'error',
                'error': 'section_not_found',
                'plan_id': args.plan_id,
                'requested_section': requested_section,
                'message': f"Section '{requested_section}' not found in {SOLUTION_FILE}",
            }
        body = sections[normalized]
        if getattr(args, 'raw', False):
            print(body)
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'file': SOLUTION_FILE,
                'section': normalized,
                'requested_section': requested_section,
                'raw': True,
            }
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'section': normalized,
            'requested_section': requested_section,
            'content': body,
        }

    if getattr(args, 'raw', False):
        print(content)
        return {'status': 'success', 'plan_id': args.plan_id, 'file': SOLUTION_FILE, 'raw': True}
    else:
        sections = parse_document_sections(content)
        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'content': sections,
        }
        scope_value = extract_scope_estimate(sections.get('solution_metadata', ''))
        if scope_value is not None:
            result['scope_estimate'] = scope_value
        return result


def cmd_get_deliverable(args: argparse.Namespace) -> dict[str, Any]:
    """Read a single deliverable by number from the solution outline.

    Mirrors ``read --deliverable-number`` exactly: performs the same
    ``document_not_found`` guard ``cmd_read`` uses (via the shared
    ``_read_solution_or_not_found`` helper — identical error dict and
    suggestions), reads the content, then funnels through the shared
    ``_lookup_deliverable`` helper for the ``section_not_found`` /
    ``deliverable_not_found`` / success shapes.
    """
    require_valid_plan_id(args)

    error, content = _read_solution_or_not_found(args.plan_id)
    if error is not None:
        return error

    return _lookup_deliverable(args.plan_id, cast(str, content), args.deliverable_number)


def cmd_get_field(args: argparse.Namespace) -> dict[str, Any]:
    """Read a single solution-level metadata field.

    Currently supports: scope_estimate. Returns ``unknown_field`` for unsupported
    field names; ``field_not_found`` when the persisted document does not carry
    the requested field; ``document_not_found`` when the file is absent.
    """
    require_valid_plan_id(args)

    field_name = getattr(args, 'field', None)
    if field_name not in SUPPORTED_FIELDS:
        return {
            'status': 'error',
            'error': 'unknown_field',
            'plan_id': args.plan_id,
            'field': field_name,
            'supported': list(SUPPORTED_FIELDS),
        }

    file_path = get_solution_path(args.plan_id)
    if not file_path.exists():
        return {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'field': field_name,
        }

    content = file_path.read_text(encoding='utf-8')
    sections = parse_document_sections(content)

    # Currently only scope_estimate is supported (lives in Solution Metadata).
    if field_name == 'scope_estimate':
        value = extract_scope_estimate(sections.get('solution_metadata', ''))
        if value is None:
            return {
                'status': 'error',
                'error': 'field_not_found',
                'plan_id': args.plan_id,
                'file': SOLUTION_FILE,
                'field': field_name,
            }
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'file': SOLUTION_FILE,
            'field': field_name,
            'value': value,
        }

    # Unreachable: SUPPORTED_FIELDS gates the field name above.
    return {
        'status': 'error',
        'error': 'unknown_field',
        'plan_id': args.plan_id,
        'field': field_name,
    }


def cmd_exists(args: argparse.Namespace) -> dict[str, Any]:
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
    if 'scope_estimate' in info:
        validation['scope_estimate'] = info['scope_estimate']

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'file': SOLUTION_FILE,
        'validation': validation,
    }

    if warnings:
        result['warnings'] = warnings

    return 0, result


def cmd_resolve_path(args: argparse.Namespace) -> dict[str, Any]:
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


def cmd_write(args: argparse.Namespace) -> dict[str, Any]:
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


def cmd_update(args: argparse.Namespace) -> dict[str, Any]:
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


def _read_module_context(project_dir: str) -> dict[str, Any]:
    """Read the per-module project-architecture layout under ``project_dir``.

    Reads the top-level ``_project.json`` plus the per-module
    ``{derived,enriched}.json`` files and returns module information to help
    with file placement decisions during solution outline creation.

    The ``not_found`` status keys off ``_project.json`` existence — that file
    is the single source of truth for "which modules exist", matching the
    contract codified in ``_architecture_core``.
    """
    meta_path = get_project_meta_path(project_dir)

    if not meta_path.exists():
        return {
            'status': 'not_found',
            'file': str(meta_path.parent),
            'message': 'Project architecture not discovered. Run architecture discovery first.',
            'suggestion': 'Run: python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover',
        }

    try:
        load_project_meta(project_dir)
        module_names = iter_modules(project_dir)
    except DataNotFoundError as e:
        # Should not happen given the existence check above, but the helper
        # raises this exception type; surface it as the not_found branch.
        return {
            'status': 'not_found',
            'file': str(meta_path.parent),
            'message': str(e),
            'suggestion': 'Run: python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover',
        }
    except Exception as e:
        return {'status': 'error', 'error': 'parse_error', 'file': str(meta_path.parent), 'message': str(e)}

    modules_list: list[dict[str, Any]] = []
    context: dict[str, Any] = {'status': 'success', 'module_count': len(module_names), 'modules': modules_list}

    for name in module_names:
        try:
            derived = load_module_derived(name, project_dir)
        except DataNotFoundError:
            # ``_project.json`` lists the module but its ``derived.json`` is
            # missing — treat as an empty derived shape so callers still see
            # a stable per-module entry.
            derived = {}
        except Exception as e:
            return {'status': 'error', 'error': 'parse_error', 'file': str(meta_path.parent), 'message': str(e)}

        try:
            enriched = load_module_enriched_or_empty(name, project_dir)
        except Exception as e:
            return {'status': 'error', 'error': 'parse_error', 'file': str(meta_path.parent), 'message': str(e)}

        paths = derived.get('paths', {})
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
        if enriched.get('best_practices'):
            module_info['best_practices'] = enriched['best_practices']
        if enriched.get('skills_by_profile'):
            module_info['skills_by_profile'] = enriched['skills_by_profile']
        modules_list.append(module_info)

    return context


def _stamp_read_provenance(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    """Name the checkout the architecture context was actually read from.

    ``get-module-context`` degrades to the cwd-relative checkout root when the
    plan declares ``use_worktree=true`` but its worktree is not materialized
    yet (see the ``WorktreeResolutionError`` branch in :func:`main`). That
    degradation must never be silent, so every payload stamped by this helper
    carries:

    * ``project_dir`` — the directory the context was actually read from.
    * ``worktree_fallback`` — ``True`` only when the read degraded to the
      checkout root because the plan's worktree could not be resolved.
    * ``worktree_fallback_reason`` — present only when ``worktree_fallback``
      is ``True``, naming the resolution failure verbatim.

    A caller can therefore tell "read from the plan's worktree" from "read
    from the checkout root because no worktree exists yet" without inferring
    it from the path.
    """
    reason = getattr(args, 'worktree_fallback_reason', None)
    stamped: dict[str, Any] = {
        'status': payload['status'],
        'project_dir': str(getattr(args, 'project_dir', '.')),
        'worktree_fallback': reason is not None,
    }
    if reason is not None:
        stamped['worktree_fallback_reason'] = reason
    for key, value in payload.items():
        if key != 'status':
            stamped[key] = value
    return stamped


def cmd_get_module_context(args: argparse.Namespace) -> dict[str, Any]:
    """Get project architecture context for placement decisions.

    Thin wrapper over :func:`_read_module_context` that stamps the read
    provenance (:func:`_stamp_read_provenance`) onto the payload, so the
    reported context always names the checkout it came from.
    """
    payload = _read_module_context(getattr(args, 'project_dir', '.'))
    return _stamp_read_provenance(args, payload)


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
    read_selector_group = read_parser.add_mutually_exclusive_group()
    read_selector_group.add_argument('--deliverable-number', type=int, help='Read specific deliverable by number')
    read_selector_group.add_argument(
        '--section',
        type=str,
        help='Read a specific top-level ## section by name (case-insensitive, e.g. summary, overview)',
    )
    read_parser.set_defaults(func=cmd_read)

    # get-deliverable
    get_deliverable_parser = subparsers.add_parser(
        'get-deliverable', help='Read a single deliverable by number', allow_abbrev=False
    )
    add_plan_id_arg(get_deliverable_parser)
    get_deliverable_parser.add_argument(
        '--deliverable-number',
        type=int,
        required=True,
        help='Deliverable number to read',
    )
    get_deliverable_parser.set_defaults(func=cmd_get_deliverable)

    # exists
    exists_parser = subparsers.add_parser('exists', help='Check if solution exists', allow_abbrev=False)
    add_plan_id_arg(exists_parser)
    exists_parser.set_defaults(func=cmd_exists)

    # get-field
    get_field_parser = subparsers.add_parser(
        'get-field',
        help='Read a single solution-level metadata field (e.g., scope_estimate)',
        allow_abbrev=False,
    )
    add_plan_id_arg(get_field_parser)
    get_field_parser.add_argument(
        '--field',
        type=str,
        required=True,
        help=f'Field name (supported: {", ".join(SUPPORTED_FIELDS)})',
    )
    get_field_parser.set_defaults(func=cmd_get_field)

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
    context_parser.add_argument(
        '--project-dir',
        default='.',
        help=(
            'Project directory containing .plan/project-architecture/ '
            '(default: current directory). Mutually exclusive with --plan-id.'
        ),
    )
    _routing.add_plan_id_arg(context_parser)
    context_parser.set_defaults(func=cmd_get_module_context)

    args = parse_args_with_toon_errors(parser)

    if not args.command:
        parser.print_help()
        return 1

    # Apply two-state routing only when the active subcommand declares
    # --project-dir (i.e., get-module-context). Other subcommands keep
    # their original argument shape unchanged.
    if hasattr(args, 'project_dir'):
        try:
            args.project_dir = _routing.resolve_project_dir(getattr(args, 'plan_id', None), args.project_dir, default='.')
        except _routing.MutuallyExclusiveArgsError:
            output_toon(_routing.emit_mutually_exclusive_error(getattr(args, 'plan_id', None), args.project_dir))
            return 2
        except _routing.WorktreeResolutionError as exc:
            # This degrade no longer covers the pre-materialization window, and
            # must not be read as though it does. A plan with
            # ``use_worktree=true`` whose worktree phase-5-execute has not
            # created yet (ADR-002) is the ``pending`` state, and the shared
            # resolver now branches on the producer's ``worktree_state``
            # discriminator and returns the main checkout for it — so this verb
            # never sees an exception for the ordinary phase-3-outline window it
            # was written to survive.
            #
            # What remains here is the genuine-failure path: the executor cannot
            # be located, ``manage-status`` fails, or the payload carries no
            # recognised state. This verb is a read-only architecture reader, so
            # it degrades to the cwd-relative checkout root and records why
            # rather than failing outright; the shared resolver keeps its fatal
            # contract for every write-side caller.
            args.project_dir = cwd_checkout_root()
            args.worktree_fallback_reason = str(exc)

    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
