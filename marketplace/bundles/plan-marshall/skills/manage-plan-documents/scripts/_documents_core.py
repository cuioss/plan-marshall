#!/usr/bin/env python3
"""
Core utilities for plan document management.

Contains shared imports, constants, document type definitions,
validation, template rendering, and path resolution used by
all _cmd_* modules.
"""

import re
from pathlib import Path
from typing import Any, cast

from file_ops import atomic_write_file, get_plan_dir, now_utc_iso, output_toon, output_toon_error  # type: ignore[import-not-found]  # noqa: F401 - atomic_write_file re-exported
from input_validation import is_valid_plan_id  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Skill directory paths for document definitions and templates
SKILL_DIR = Path(__file__).parent.parent
DOCUMENTS_DIR = SKILL_DIR / 'documents'
TEMPLATES_DIR = SKILL_DIR / 'templates'


def load_document_type(doc_type: str) -> dict[Any, Any] | None:
    """Load document definition from documents/{type}.toon"""
    doc_file = DOCUMENTS_DIR / f'{doc_type}.toon'
    if not doc_file.exists():
        return None
    return cast(dict[Any, Any], parse_toon(doc_file.read_text(encoding='utf-8')))


def get_available_types() -> list[str]:
    """Get list of available document types."""
    if not DOCUMENTS_DIR.exists():
        return []
    return [f.stem for f in DOCUMENTS_DIR.glob('*.toon')]


# get_plan_dir imported from file_ops


def get_file_name(doc_def: dict, doc_type: str) -> str:
    """Get the file name for a document type."""
    return str(doc_def.get('file', f'{doc_type}.md'))


def validate_fields(doc_def: dict, provided: dict) -> list[str]:
    """Validate provided fields against document definition."""
    errors = []
    fields = doc_def.get('fields', [])

    for field in fields:
        name = field['name']
        required = field.get('required') == 'true' or field.get('required') is True
        field_type = field.get('type', 'string')

        value = provided.get(name)

        if required and not value:
            errors.append(f'Missing required field: {name}')
        elif value:
            # Type-specific validation
            if field_type.startswith('enum('):
                allowed = field_type[5:-1].split('|')
                if value not in allowed:
                    errors.append(f'Invalid {name}: must be one of {allowed}')

    return errors


def render_template(doc_def: dict, fields: dict, plan_id: str) -> str:
    """Render template with field substitution."""
    template_rel = doc_def.get('template', '')
    template_name = template_rel.replace('templates/', '') if template_rel else f'{doc_def["name"]}.md'
    template_path = TEMPLATES_DIR / template_name

    if not template_path.exists():
        # Generate basic template if not found
        lines = [f'# {doc_def["name"].title()}: {fields.get("title", plan_id)}']
        lines.append(f'\nplan_id: {plan_id}')
        lines.append(f'created: {now_utc_iso()}')
        for name, value in fields.items():
            if value and name != 'title':
                lines.append(f'\n## {name.replace("_", " ").title()}\n\n{value}')
        return '\n'.join(lines)

    template = template_path.read_text(encoding='utf-8')

    # Built-in placeholders
    template = template.replace('{plan_id}', plan_id)
    template = template.replace('{timestamp}', now_utc_iso())

    # Field placeholders
    for key, value in fields.items():
        placeholder = f'{{{key}}}'
        template = template.replace(placeholder, value if value else '')

    # Clean up unreplaced placeholders (optional fields not provided)
    template = _cleanup_unreplaced_placeholders(template)

    return template


def _cleanup_unreplaced_placeholders(content: str) -> str:
    """Remove lines with unreplaced placeholders and empty sections.

    Handles:
    - Metadata lines like "source_id: {source_id}" - remove entire line
    - Section content lines with only placeholder - remove line
    - Empty sections (heading followed by blank or another heading) - remove section
    """
    lines = content.split('\n')
    cleaned_lines = []
    placeholder_pattern = re.compile(r'\{[a-z_]+\}')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line contains unreplaced placeholder
        if placeholder_pattern.search(line):
            # Metadata line pattern: "key: {placeholder}" - skip entire line
            if re.match(r'^[a-z_]+:\s*\{[a-z_]+\}\s*$', line):
                i += 1
                continue
            # Line is ONLY a placeholder - skip it
            if re.match(r'^\s*\{[a-z_]+\}\s*$', line):
                i += 1
                continue
            # Otherwise replace placeholder with empty string
            line = placeholder_pattern.sub('', line)

        cleaned_lines.append(line)
        i += 1

    # Remove empty sections (## heading followed by blank lines then another ## or EOF)
    final_lines = []
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]

        if line.startswith('## '):
            # Look ahead to see if section is empty
            section_has_content = False
            j = i + 1
            while j < len(cleaned_lines):
                next_line = cleaned_lines[j]
                if next_line.startswith('## ') or next_line.startswith('# '):
                    # Hit another heading - section was empty
                    break
                if next_line.strip():
                    # Found non-empty content
                    section_has_content = True
                    break
                j += 1

            if not section_has_content:
                # Skip this empty section heading and any blank lines after it
                i = j
                continue

        final_lines.append(line)
        i += 1

    # Clean up trailing blank lines
    while final_lines and not final_lines[-1].strip():
        final_lines.pop()

    return '\n'.join(final_lines) + '\n'


def output_error(error_key: str, **kwargs) -> None:
    """Print TOON-serialized error output. Delegates to file_ops.output_toon_error."""
    output_toon_error(error_key, kwargs.pop('message', ''), **kwargs)


def validate_doc_type_and_plan(doc_type: str, plan_id: str) -> dict | None:
    """Validate document type and plan ID, returning doc_def or None on error.

    Prints error output and returns None if validation fails.
    """
    doc_def = load_document_type(doc_type)
    if not doc_def:
        output_error('unknown_document_type', document=doc_type)
        return None

    if not is_valid_plan_id(plan_id):
        output_error('invalid_plan_id', plan_id=plan_id)
        return None

    return doc_def


def resolve_document_path(doc_def: dict, doc_type: str, plan_id: str) -> tuple[Path, str]:
    """Resolve plan directory and file path for a document.

    Returns (file_path, file_name) tuple.
    """
    plan_dir = get_plan_dir(plan_id)
    file_name = get_file_name(doc_def, doc_type)
    return plan_dir / file_name, file_name
