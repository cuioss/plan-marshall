#!/usr/bin/env python3
"""Tests for TOON syntax validation.

Migrated from test/validate-toon-syntax.sh - validates TOON file syntax
including array row counts, no tabs, and basic structure.
"""

import re
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)

# Test root directory
TEST_ROOT = Path(__file__).parent.parent.parent


def find_toon_files():
    """Find all .toon files in test directory."""
    return list(TEST_ROOT.rglob('*.toon'))


def validate_toon_file(file_path):
    """
    Validate a TOON file and return list of errors.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check 1: File exists and not empty
    if not file_path.exists():
        return [f'File not found: {file_path}']

    content = file_path.read_text()
    if not content.strip():
        return ['File is empty']

    lines = content.split('\n')

    # Check 2: No tabs (TOON should use spaces)
    for i, line in enumerate(lines, 1):
        if '\t' in line:
            errors.append(f'Tab character on line {i}')

    # Check 3: Array declarations have matching row counts
    # Look for patterns like: issues[5]{col1,col2}:
    array_pattern = re.compile(r'^([a-z_]+)\[(\d+)\]\{([^}]+)\}:')

    i = 0
    while i < len(lines):
        line = lines[i]
        match = array_pattern.match(line)
        if match:
            array_name = match.group(1)
            declared_count = int(match.group(2))

            # Count actual data rows (non-empty lines until next section or end)
            actual_count = 0
            j = i + 1
            while j < len(lines):
                row = lines[j].strip()
                # Stop at empty line, new section (name:), or new array
                if not row or row.endswith(':') or array_pattern.match(row):
                    break
                actual_count += 1
                j += 1

            if declared_count != actual_count:
                errors.append(f"Array '{array_name}': declared {declared_count} rows, found {actual_count}")
            i = j
        else:
            i += 1

    return errors


# =============================================================================
# Tests
# =============================================================================


def test_toon_files_exist():
    """Test that at least one .toon file exists."""
    toon_files = find_toon_files()
    assert len(toon_files) > 0, 'No .toon files found in test directory'


def test_all_toon_files_valid_syntax():
    """Test all .toon files have valid syntax."""
    toon_files = find_toon_files()
    all_errors = []

    for file_path in toon_files:
        errors = validate_toon_file(file_path)
        if errors:
            rel_path = file_path.relative_to(TEST_ROOT)
            all_errors.append(f'{rel_path}: {"; ".join(errors)}')

    assert len(all_errors) == 0, 'TOON syntax errors:\n  ' + '\n  '.join(all_errors)


def test_no_tabs_in_toon_files():
    """Test no .toon files contain tabs."""
    toon_files = find_toon_files()
    files_with_tabs = []

    for file_path in toon_files:
        content = file_path.read_text()
        if '\t' in content:
            files_with_tabs.append(file_path.relative_to(TEST_ROOT))

    assert len(files_with_tabs) == 0, f'TOON files with tabs (should use spaces): {files_with_tabs}'


def test_toon_files_not_empty():
    """Test no .toon files are empty."""
    toon_files = find_toon_files()
    empty_files = []

    for file_path in toon_files:
        content = file_path.read_text()
        if not content.strip():
            empty_files.append(file_path.relative_to(TEST_ROOT))

    assert len(empty_files) == 0, f'Empty TOON files: {empty_files}'


def test_array_declarations_match_rows():
    """Test array declarations match actual row counts."""
    toon_files = find_toon_files()
    array_pattern = re.compile(r'^([a-z_]+)\[(\d+)\]\{([^}]+)\}:')
    mismatches = []

    for file_path in toon_files:
        content = file_path.read_text()
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i]
            match = array_pattern.match(line)
            if match:
                array_name = match.group(1)
                declared_count = int(match.group(2))

                actual_count = 0
                j = i + 1
                while j < len(lines):
                    row = lines[j].strip()
                    if not row or row.endswith(':') or array_pattern.match(row):
                        break
                    actual_count += 1
                    j += 1

                if declared_count != actual_count:
                    rel_path = file_path.relative_to(TEST_ROOT)
                    mismatches.append(f'{rel_path}: {array_name}[{declared_count}] has {actual_count} rows')
                i = j
            else:
                i += 1

    assert len(mismatches) == 0, 'Array declaration mismatches:\n  ' + '\n  '.join(mismatches)


# =============================================================================
# Main
# =============================================================================
