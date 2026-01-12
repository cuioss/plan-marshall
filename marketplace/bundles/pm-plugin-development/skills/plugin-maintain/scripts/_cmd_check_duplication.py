#!/usr/bin/env python3
"""Check-duplication subcommand for detecting duplicate knowledge in skills."""

import re
from difflib import SequenceMatcher
from pathlib import Path

from _maintain_shared import EXIT_SUCCESS, EXIT_ERROR, output_json


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove markdown formatting
    text = re.sub(r'[#*`_\[\]]', '', text)
    # Normalize whitespace
    text = ' '.join(text.lower().split())
    return text


def extract_sections(content: str) -> dict[str, str]:
    """Extract sections from markdown content."""
    sections = {}
    current_section = 'intro'
    current_content = []

    for line in content.split('\n'):
        if line.startswith('#'):
            if current_content:
                sections[current_section] = '\n'.join(current_content)
            # Extract section name
            current_section = re.sub(r'^#+\s*', '', line).strip().lower()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = '\n'.join(current_content)

    return sections


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    normalized1 = normalize_text(text1)
    normalized2 = normalize_text(text2)

    if not normalized1 or not normalized2:
        return 0.0

    return SequenceMatcher(None, normalized1, normalized2).ratio()


def find_duplicate_sections(new_sections: dict, existing_sections: dict) -> list:
    """Find sections that have high overlap."""
    duplicates = []

    for new_name, new_content in new_sections.items():
        for existing_name, existing_content in existing_sections.items():
            similarity = calculate_similarity(new_content, existing_content)
            if similarity > 0.6:  # 60% similarity threshold
                duplicates.append({
                    'new_section': new_name,
                    'existing_section': existing_name,
                    'similarity': round(similarity * 100, 1)
                })

    return duplicates


def check_duplication(skill_path: str, content_file: str) -> dict:
    """Main duplication checking function."""
    skill_dir = Path(skill_path)
    content_path = Path(content_file)

    # Validate inputs
    if not skill_dir.exists():
        return {
            'error': f'Skill directory not found: {skill_path}',
            'skill_path': skill_path
        }

    if not content_path.exists():
        return {
            'error': f'Content file not found: {content_file}',
            'new_content_file': content_file
        }

    # Read new content
    new_content = content_path.read_text()
    new_sections = extract_sections(new_content)
    new_normalized = normalize_text(new_content)

    # Check for empty content
    if not new_normalized.strip():
        return {
            'skill_path': skill_path,
            'new_content_file': content_file,
            'duplication_detected': False,
            'duplication_percentage': 0,
            'duplicate_files': [],
            'recommendation': 'proceed',
            'note': 'Content file is empty or minimal'
        }

    # Find references directory
    refs_dir = skill_dir / 'references'
    if not refs_dir.exists():
        refs_dir = skill_dir / 'standards'  # Try standards directory

    if not refs_dir.exists():
        return {
            'skill_path': skill_path,
            'new_content_file': content_file,
            'duplication_detected': False,
            'duplication_percentage': 0,
            'duplicate_files': [],
            'recommendation': 'proceed',
            'note': 'No existing references directory found'
        }

    # Scan existing references
    duplicate_files = []
    max_overlap = 0

    for ref_file in refs_dir.glob('*.md'):
        existing_content = ref_file.read_text()

        # Overall similarity
        overall_similarity = calculate_similarity(new_content, existing_content)

        if overall_similarity > 0.3:  # 30% overall threshold
            existing_sections = extract_sections(existing_content)
            duplicate_sections = find_duplicate_sections(new_sections, existing_sections)

            if duplicate_sections:
                overlap_pct = round(overall_similarity * 100, 1)
                duplicate_files.append({
                    'existing_file': str(ref_file.relative_to(skill_dir)),
                    'overlap_percentage': overlap_pct,
                    'duplicate_sections': [d['existing_section'] for d in duplicate_sections[:5]]
                })
                max_overlap = max(max_overlap, overlap_pct)

    # Determine recommendation
    duplication_detected = max_overlap > 30
    if max_overlap >= 70:
        recommendation = 'skip'
    elif max_overlap >= 40:
        recommendation = 'consolidate'
    else:
        recommendation = 'proceed'

    return {
        'skill_path': skill_path,
        'new_content_file': content_file,
        'duplication_detected': duplication_detected,
        'duplication_percentage': max_overlap,
        'duplicate_files': sorted(duplicate_files, key=lambda x: x['overlap_percentage'], reverse=True),
        'recommendation': recommendation
    }


def cmd_check_duplication(args) -> int:
    """Handle check-duplication subcommand."""
    result = check_duplication(args.skill_path, args.content_file)
    output_json(result)
    return EXIT_SUCCESS if 'error' not in result else EXIT_ERROR
