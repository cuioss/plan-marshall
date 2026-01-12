#!/usr/bin/env python3
"""Skill structure analysis subcommand."""

import json
import re
import sys
from pathlib import Path

from _analyze_shared import extract_frontmatter, check_yaml_validity, remove_code_blocks


def extract_skill_references(content: str, skill_dir: Path) -> set[str]:
    """Extract file references from SKILL.md content."""
    references = set()

    local_pattern = r'(scripts|references|assets)(/[a-zA-Z0-9_.-]+)+\.[a-z]+'
    for match in re.finditer(local_pattern, content):
        ref = match.group(0)
        start = match.start()
        if start > 0 and content[start-1] == ':':
            continue
        references.add(ref)

    content_no_codeblocks = remove_code_blocks(content)
    table_pattern = r'`(scripts|references|assets)(/[a-zA-Z0-9_.-]+)+\.[a-z]+`'
    for match in re.finditer(table_pattern, content_no_codeblocks):
        ref = match.group(0).strip('`')
        references.add(ref)

    for subdir in ['scripts', 'references', 'assets']:
        subdir_path = skill_dir / subdir
        if subdir_path.is_dir():
            for file_path in subdir_path.iterdir():
                if file_path.is_file():
                    filename = file_path.name
                    if f'`{filename}`' in content_no_codeblocks:
                        references.add(f"{subdir}/{filename}")

    return references


def find_existing_files(skill_dir: Path) -> set[str]:
    """Find all files in scripts/, references/, and assets/ directories."""
    existing = set()

    for subdir in ['scripts', 'references', 'assets']:
        subdir_path = skill_dir / subdir
        if subdir_path.is_dir():
            for file_path in subdir_path.rglob('*'):
                if file_path.is_file():
                    if '__pycache__' in file_path.parts:
                        continue
                    if file_path.suffix in {'.pyc', '.pyo', '.class', '.o'}:
                        continue
                    existing.add(str(file_path.relative_to(skill_dir)))

    return existing


def calculate_structure_score(skill_exists: bool, yaml_valid: bool,
                              missing_count: int, unreferenced_count: int) -> int:
    """Calculate structure score based on issues."""
    if not skill_exists:
        return 0
    if not yaml_valid:
        return 30

    if missing_count == 0 and unreferenced_count == 0:
        return 100

    score = 100
    score -= missing_count * 20
    score -= unreferenced_count * 10

    return max(0, score)


def analyze_skill_structure(skill_dir: Path) -> dict:
    """Analyze skill directory structure."""
    skill_md = skill_dir / 'SKILL.md'

    skill_exists = skill_md.is_file()
    yaml_valid = False
    missing_files = []
    unreferenced_files = []

    if skill_exists:
        try:
            content = skill_md.read_text(encoding='utf-8', errors='replace')
        except (OSError, IOError):
            content = ''

        frontmatter_present, frontmatter = extract_frontmatter(content)
        if frontmatter_present:
            yaml_valid = check_yaml_validity(frontmatter)

        references = extract_skill_references(content, skill_dir)
        existing = find_existing_files(skill_dir)

        content_no_codeblocks = remove_code_blocks(content)
        refs_outside_codeblocks = set()
        local_pattern = r'(scripts|references|assets)(/[a-zA-Z0-9_.-]+)+\.[a-z]+'
        for match in re.finditer(local_pattern, content_no_codeblocks):
            ref = match.group(0)
            start = match.start()
            if start > 0 and content_no_codeblocks[start-1] == ':':
                continue
            refs_outside_codeblocks.add(ref)

        for ref in references:
            file_path = skill_dir / ref
            if not file_path.is_file():
                if ref in refs_outside_codeblocks:
                    missing_files.append(ref)

        for existing_file in existing:
            if existing_file not in references:
                # Skip internal/private Python modules - these are imported by main scripts, not referenced in docs
                # Convention: underscore-prefixed files (_*.py) are private modules per Python convention
                # Legacy patterns also supported: cmd_*.py, doctor_*.py, analyze_*.py, *_shared.py
                if existing_file.endswith('.py'):
                    basename = existing_file.split('/')[-1]
                    # Underscore prefix indicates private/internal module (Python convention)
                    if basename.startswith('_'):
                        continue
                    # Legacy patterns (for backward compatibility)
                    if (basename.startswith('cmd_') or
                        basename.startswith('doctor_') or
                        basename.startswith('analyze_') or
                        basename.endswith('_shared.py')):
                        continue
                unreferenced_files.append(existing_file)

    structure_score = calculate_structure_score(
        skill_exists, yaml_valid,
        len(missing_files), len(unreferenced_files)
    )

    return {
        'skill_dir': str(skill_dir),
        'skill_md': {'exists': skill_exists, 'yaml_valid': yaml_valid},
        'standards_files': {
            'missing_files': sorted(missing_files),
            'unreferenced_files': sorted(unreferenced_files)
        },
        'structure_score': structure_score
    }


def cmd_structure(args) -> int:
    """Analyze skill directory structure."""
    skill_dir = Path(args.directory)

    if not skill_dir.exists():
        print(json.dumps({'error': f'Directory not found: {args.directory}'}), file=sys.stderr)
        return 1

    if not skill_dir.is_dir():
        print(json.dumps({'error': f'Not a directory: {args.directory}'}), file=sys.stderr)
        return 1

    result = analyze_skill_structure(skill_dir)
    print(json.dumps(result, indent=2))
    return 0
