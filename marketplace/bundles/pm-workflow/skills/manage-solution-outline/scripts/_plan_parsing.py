#!/usr/bin/env python3
"""
Shared plan document parsing utilities.

Provides common parsing functions for plan documents (solution outlines,
deliverables) used across pm-workflow and verify-workflow scripts.

Usage:
    from _plan_parsing import (
        parse_document_sections,
        extract_deliverable_headings,
        extract_deliverables,
        parse_toon_simple,
    )
"""

import re
from typing import Any


def parse_document_sections(content: str) -> dict[str, str]:
    """Parse markdown document into sections by ## heading.

    Section keys are lowercase with underscores (e.g., 'summary', 'deliverables').
    The content before any ## heading is stored under '_header'.

    Args:
        content: Markdown document content

    Returns:
        Dictionary mapping section names to their content
    """
    sections: dict[str, str] = {}
    current_section = '_header'
    current_content: list[str] = []

    for line in content.split('\n'):
        if line.startswith('## '):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section (lowercase with underscores)
            current_section = line[3:].strip().lower().replace(' ', '_')
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections


def extract_deliverable_headings(content: str) -> list[dict[str, str]]:
    """Extract deliverable headings from Deliverables section.

    Simple extraction that only returns id and title - use for
    basic structural verification.

    Args:
        content: The Deliverables section content

    Returns:
        List of dicts with 'id' and 'title' keys
    """
    deliverables: list[dict[str, str]] = []
    pattern = re.compile(r'^###\s+(\d+)\.\s+(.+)$', re.MULTILINE)

    for match in pattern.finditer(content):
        deliverables.append({'id': match.group(1), 'title': match.group(2).strip()})

    return deliverables


def extract_deliverables(deliverables_section: str) -> list[dict[str, Any]]:
    """Extract full deliverable information from Deliverables section.

    Parses `### N. Title` headings and extracts structured information
    including metadata, profiles, affected files, and verification.

    Args:
        deliverables_section: The Deliverables section content

    Returns:
        List of deliverable dicts with full metadata
    """
    deliverables: list[dict[str, Any]] = []
    pattern = re.compile(r'^###\s+(\d+)\.\s+(.+)$', re.MULTILINE)

    # Find all deliverable start positions
    matches = list(pattern.finditer(deliverables_section))

    for i, match in enumerate(matches):
        number = int(match.group(1))
        title = match.group(2).strip()

        # Get content until next deliverable or end
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(deliverables_section)
        content = deliverables_section[start_pos:end_pos].strip()

        # Extract structured blocks
        metadata = _extract_metadata_block(content)
        profiles = _extract_profiles(content)
        affected_files = _extract_affected_files(content)
        verification = _extract_verification(content)
        has_success_criteria = bool(re.search(r'\*\*Success Criteria:\*\*', content, re.IGNORECASE))

        deliverables.append(
            {
                'number': number,
                'title': title,
                'reference': f'{number}. {title}',
                'metadata': metadata,
                'profiles': profiles,
                'affected_files': affected_files,
                'verification': verification,
                'has_success_criteria': has_success_criteria,
            }
        )

    return sorted(deliverables, key=lambda d: d['number'])


def _extract_metadata_block(content: str) -> dict[str, str]:
    """Extract **Metadata:** block fields from deliverable content."""
    metadata: dict[str, str] = {}

    metadata_match = re.search(r'\*\*Metadata:\*\*\s*((?:- [^\n]+\n?)+)', content, re.IGNORECASE)
    if not metadata_match:
        return metadata

    metadata_text = metadata_match.group(1)
    field_pattern = re.compile(r'-\s*(\w+):\s*(.+)')
    for match in field_pattern.finditer(metadata_text):
        field_name = match.group(1).strip()
        field_value = match.group(2).strip()
        metadata[field_name] = field_value

    return metadata


def _extract_profiles(content: str) -> list[str]:
    """Extract **Profiles:** list from deliverable content."""
    profiles: list[str] = []

    profiles_match = re.search(r'\*\*Profiles:\*\*\s*((?:- [^\n]+\n?)+)', content, re.IGNORECASE)
    if not profiles_match:
        return profiles

    profiles_text = profiles_match.group(1)
    profile_pattern = re.compile(r'-\s*(\w+)')
    for match in profile_pattern.finditer(profiles_text):
        profile = match.group(1).strip()
        if profile:
            profiles.append(profile)

    return profiles


def _extract_affected_files(content: str) -> list[str]:
    """Extract **Affected files:** list from deliverable content."""
    files: list[str] = []

    files_match = re.search(r'\*\*Affected files:\*\*\s*((?:- [^\n]+\n?)+)', content, re.IGNORECASE)
    if not files_match:
        return files

    files_text = files_match.group(1)
    file_pattern = re.compile(r'-\s*`?([^`\n]+)`?')
    for match in file_pattern.finditer(files_text):
        file_path = match.group(1).strip()
        if file_path:
            files.append(file_path)

    return files


def _extract_verification(content: str) -> dict[str, str]:
    """Extract **Verification:** section from deliverable content."""
    verification: dict[str, str] = {}

    verif_match = re.search(r'\*\*Verification:\*\*\s*\n?((?:- [^\n]+\n?)+)', content, re.IGNORECASE)
    if not verif_match:
        return verification

    verif_text = verif_match.group(1)

    cmd_match = re.search(r'-\s*Command:\s*(.+)', verif_text)
    if cmd_match:
        verification['command'] = cmd_match.group(1).strip()

    criteria_match = re.search(r'-\s*Criteria:\s*(.+)', verif_text)
    if criteria_match:
        verification['criteria'] = criteria_match.group(1).strip()

    return verification


def parse_toon_simple(content: str) -> dict[str, Any]:
    """Parse simple TOON format (key: value pairs and lists).

    Handles basic TOON structures:
    - Key: value pairs
    - Lists with [N]: header
    - Comments (# lines)

    Args:
        content: TOON format content

    Returns:
        Dictionary with parsed values
    """
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Check for list header
        if '[' in line and line.endswith(':'):
            if current_list_key and current_list:
                result[current_list_key] = current_list
            key_part = line.split('[')[0]
            current_list_key = key_part
            current_list = []
            continue

        # Check if we're in a list
        if current_list_key:
            if ':' in line and not line.startswith(' '):
                result[current_list_key] = current_list
                current_list_key = None
                current_list = []
            else:
                current_list.append(line.strip())
                continue

        # Key-value pair
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()

    if current_list_key and current_list:
        result[current_list_key] = current_list

    return result
