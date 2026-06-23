#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic validator for untrusted-ingestion candidate structs.

This script IS the containment boundary in the reader/orchestrator/writer
isolation model (see plan-marshall:untrusted-ingestion). The reader (a
read-only execution-context-reader variant) performs semantic extraction of
untrusted external text into a CANDIDATE struct; the orchestrator/writer runs
this script on that candidate BEFORE consuming it. Security rests on the
script, not on the reader behaving.

It enforces three things deterministically:
    1. Schema      — additionalProperties:false + per-field type + pattern.
                     Any structural violation → status: error.
    2. Length-cap  — every string clamped to maxLength, every array to
                     maxItems; clamped struct returned on status: success.
    3. Domain-gate — every URL host checked against the WebFetch allowlist by
                     reusing permission_web.categorize_domain / check_red_flags.
                     A host categorizing to 'unknown' or tripping a red flag →
                     status: error.

Usage:
    validate_struct.py validate --schema research|ci-finding|issue-body --struct '<json>'
"""

import argparse
import re
import sys
from typing import Any
from urllib.parse import urlparse

# permission_web: reuse the WebFetch domain-membership logic — do NOT restate it.
from permission_web import categorize_domain, check_red_flags  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    create_workflow_cli,
    make_error,
    parse_json_arg,
    print_toon,
    safe_main,
)

# ============================================================================
# SCHEMA DECLARATIONS
# ============================================================================
#
# Each schema is a dict mapping field name -> field spec. A field spec carries:
#   type      — the expected Python type (or tuple of types)
#   max_length — clamp cap for str fields
#   max_items  — clamp cap for list fields
#   pattern    — regex an enum/identifier field must fully match
#   url_list   — True when the field is a list of URL strings to domain-check
#   item       — for list-of-object fields, the nested field-spec dict
#
# additionalProperties is always false: any key not declared here is rejected.

_CONFIDENCE_PATTERN = r'^(high|medium|low)$'
_SEVERITY_PATTERN = r'^(blocker|critical|major|minor|info)$'

SCHEMAS: dict[str, dict[str, dict[str, Any]]] = {
    'research': {
        'findings': {
            'type': list,
            'max_items': 50,
            'item': {
                'practice': {'type': str, 'max_length': 2000},
                'justification': {'type': str, 'max_length': 2000},
                'confidence': {'type': str, 'pattern': _CONFIDENCE_PATTERN},
                'references': {'type': list, 'max_items': 20, 'url_list': True},
            },
        },
    },
    'ci-finding': {
        'summary': {'type': str, 'max_length': 4000},
        'severity': {'type': str, 'pattern': _SEVERITY_PATTERN},
        'file': {'type': str, 'max_length': 1000},
        'line': {'type': int},
        'references': {'type': list, 'max_items': 20, 'url_list': True},
    },
    'issue-body': {
        'narrative': {'type': str, 'max_length': 8000},
        'references': {'type': list, 'max_items': 20, 'url_list': True},
    },
}


# ============================================================================
# VALIDATION CORE
# ============================================================================


def _type_name(expected: type | tuple[type, ...]) -> str:
    if isinstance(expected, tuple):
        return '/'.join(t.__name__ for t in expected)
    return expected.__name__


def _url_host(url: str) -> str:
    """Extract the bare host from a URL.

    permission_web.categorize_domain / check_red_flags expect a host, not a
    full URL with a path — e.g. 'github.com', not 'https://github.com/o/r'.
    Uses urlparse().hostname which correctly handles IPv6 addresses
    (e.g. [2001:db8::1]), ports, and userinfo. Schemeless URLs are normalised
    by prepending '//' so urlparse treats them as netloc rather than path.
    """
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url) and not url.startswith('//'):
        url = '//' + url
    try:
        return urlparse(url).hostname or ''
    except Exception:
        return ''


def _domain_allowed(url: str) -> bool:
    """A URL host is allowlisted iff it categorizes to a known tier and trips
    no red flag. Reuses permission_web logic — never restated here."""
    host = _url_host(url)
    category = categorize_domain(host)
    if category not in ('major', 'high_reach', 'universal'):
        return False
    if check_red_flags(host):
        return False
    return True


def _validate_field(
    path: str,
    value: Any,
    spec: dict[str, Any],
    clamped: list[str],
    domain_errors: list[str],
) -> tuple[Any, list[str]]:
    """Validate and clamp a single field against its spec.

    Returns (possibly-clamped value, list of structural-violation messages).
    Length clamps are recorded in ``clamped``; domain rejections in
    ``domain_errors``. Structural violations (type, pattern) are returned.
    """
    errors: list[str] = []
    expected = spec['type']

    # bool is a subclass of int — reject it explicitly where int is expected.
    if expected is int and isinstance(value, bool):
        return value, [f"Field '{path}' should be int, got bool"]
    if not isinstance(value, expected):
        return value, [f"Field '{path}' should be {_type_name(expected)}, got {type(value).__name__}"]

    if isinstance(value, str):
        pattern = spec.get('pattern')
        if pattern is not None and not re.fullmatch(pattern, value):
            errors.append(f"Field '{path}' value '{value}' does not match pattern {pattern}")
            return value, errors
        max_length = spec.get('max_length')
        if max_length is not None and len(value) > max_length:
            clamped.append(f"{path} (string {len(value)}→{max_length})")
            value = value[:max_length]
        return value, errors

    if isinstance(value, list):
        max_items = spec.get('max_items')
        if max_items is not None and len(value) > max_items:
            clamped.append(f"{path} (array {len(value)}→{max_items})")
            value = value[:max_items]

        if spec.get('url_list'):
            new_list = []
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    errors.append(f"Field '{path}[{i}]' should be str, got {type(item).__name__}")
                    continue
                if not _domain_allowed(item):
                    domain_errors.append(f"{path}[{i}]: {item}")
                new_list.append(item)
            return new_list, errors

        item_spec = spec.get('item')
        if item_spec is not None:
            new_list = []
            for i, item in enumerate(value):
                clamped_item, item_errors = _validate_object(f"{path}[{i}]", item, item_spec, clamped, domain_errors)
                errors.extend(item_errors)
                new_list.append(clamped_item)
            return new_list, errors
        return value, errors

    return value, errors


def _validate_object(
    path: str,
    obj: Any,
    schema: dict[str, dict[str, Any]],
    clamped: list[str],
    domain_errors: list[str],
) -> tuple[Any, list[str]]:
    """Validate an object against a schema with additionalProperties:false."""
    if not isinstance(obj, dict):
        return obj, [f"Field '{path}' should be object, got {type(obj).__name__}"]

    errors: list[str] = []
    # additionalProperties:false — reject any undeclared key.
    for key in obj:
        if key not in schema:
            errors.append(f"Field '{path}' has undeclared key '{key}' (additionalProperties:false)")

    result: dict[str, Any] = {}
    for field, spec in schema.items():
        field_path = f"{path}.{field}" if path else field
        if field not in obj:
            # Absent fields are permitted; the reader emits what it extracted.
            continue
        clamped_value, field_errors = _validate_field(field_path, obj[field], spec, clamped, domain_errors)
        errors.extend(field_errors)
        result[field] = clamped_value

    # Preserve undeclared keys' presence only in the error list, never in output.
    return result, errors


# ============================================================================
# COMMAND HANDLER
# ============================================================================


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    schema = SCHEMAS.get(args.schema)
    if schema is None:
        return make_error(
            f"Unknown schema: {args.schema}",
            code='invalid_input',
            valid_schemas=sorted(SCHEMAS.keys()),
        )

    candidate, parse_err = parse_json_arg(args.struct, '--struct')
    if parse_err is not None:
        return parse_err

    if not isinstance(candidate, dict):
        return make_error(
            f"Candidate struct must be a JSON object, got {type(candidate).__name__}",
            code='schema_violation',
        )

    clamped: list[str] = []
    domain_errors: list[str] = []
    validated, errors = _validate_object('', candidate, schema, clamped, domain_errors)

    if errors:
        return make_error(
            'Schema validation failed',
            code='schema_violation',
            schema=args.schema,
            violations=errors,
        )

    if domain_errors:
        return make_error(
            'Domain allowlist check failed',
            code='domain_rejected',
            schema=args.schema,
            rejected_urls=domain_errors,
        )

    return {
        'status': 'success',
        'schema': args.schema,
        'struct': validated,
        'clamped': clamped,
    }


def main() -> int:
    parser = create_workflow_cli(
        description='Deterministic validator for untrusted-ingestion candidate structs',
        epilog="""
Examples:
  validate_struct.py validate --schema research --struct '{"findings": []}'
  validate_struct.py validate --schema ci-finding --struct '{"summary": "...", "severity": "major"}'
""",
        subcommands=[
            {
                'name': 'validate',
                'help': 'Validate (and clamp) a candidate struct against a schema',
                'handler': cmd_validate,
                'args': [
                    {'flags': ['--schema'], 'required': True, 'help': 'Schema selector: research|ci-finding|issue-body'},
                    {'flags': ['--struct'], 'required': True, 'help': 'Candidate struct as a JSON string'},
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
