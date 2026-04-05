#!/usr/bin/env python3
"""Tests for analyze.py - consolidated plugin analysis tools.

Consolidates tests from:
- test_analyze_skill_structure.py (structure subcommand)
- test_analyze_cross_file_content.py (cross-file subcommand)

Tests plugin component analysis capabilities.
"""

from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
from conftest import create_temp_file, get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_analyze.py')
SKILL_STRUCTURE_FIXTURES = Path(__file__).parent / 'fixtures' / 'skill-structure'
CROSS_FILE_FIXTURES = Path(__file__).parent / 'fixtures' / 'cross-file-analysis'

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_analyze_crossfile_mod = _load_module('_analyze_crossfile', '_analyze_crossfile.py')
_analyze_markdown_mod = _load_module('_analyze_markdown', '_analyze_markdown.py')
_analyze_structure_mod = _load_module('_analyze_structure', '_analyze_structure.py')

cmd_crossfile_analyze = _analyze_crossfile_mod.cmd_cross_file
cmd_markdown = _analyze_markdown_mod.cmd_markdown
cmd_structure = _analyze_structure_mod.cmd_structure

# =============================================================================
# CLI plumbing tests (Tier 3 - subprocess)
# =============================================================================


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'markdown' in combined, 'markdown subcommand in help'
    assert 'structure' in combined, 'structure subcommand in help'
    assert 'coverage' in combined, 'coverage subcommand in help'
    assert 'cross-file' in combined, 'cross-file subcommand in help'


def test_crossfile_missing_argument():
    """Test returns error for missing argument."""
    result = run_script(SCRIPT_PATH, 'cross-file')
    assert result.returncode != 0, 'Should return error for missing argument'


# =============================================================================
# Structure Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_structure_table_refs_no_unreferenced():
    """Test that table-referenced files are detected (no unreferenced files)."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    args = Namespace(directory=str(test_dir))
    data = cmd_structure(args)
    unreferenced = data.get('standards_files', {}).get('unreferenced_files', [])
    assert len(unreferenced) == 0, f'Should have no unreferenced files, found {len(unreferenced)}'


def test_structure_table_refs_no_missing():
    """Test that all referenced files exist (no missing files)."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    args = Namespace(directory=str(test_dir))
    data = cmd_structure(args)
    missing = data.get('standards_files', {}).get('missing_files', [])
    assert len(missing) == 0, f'Should have no missing files, found {len(missing)}'


def test_structure_table_refs_perfect_score():
    """Test perfect score for table-referenced files."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    args = Namespace(directory=str(test_dir))
    data = cmd_structure(args)
    score = data.get('structure_score', 0)
    assert score >= 100, f'Score should be 100, got {score}'


def test_structure_code_block_no_false_positive():
    """Test that example paths in code blocks are NOT detected as missing."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'code-block-examples'
    if not test_dir.exists():
        return  # Skip if fixture not available

    args = Namespace(directory=str(test_dir))
    data = cmd_structure(args)
    missing = data.get('standards_files', {}).get('missing_files', [])
    assert len(missing) == 0, f'Should not flag code block examples as missing, found {len(missing)}'


def test_structure_cross_skill_no_false_positive():
    """Test that cross-skill references are NOT flagged as missing."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'cross-skill-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    args = Namespace(directory=str(test_dir))
    data = cmd_structure(args)
    missing = data.get('standards_files', {}).get('missing_files', [])
    assert len(missing) == 0, f'Cross-skill refs should not be flagged as missing, found {len(missing)}'


def test_structure_real_plugin_doctor():
    """Test plugin-doctor skill (has table-format refs and cross-skill refs)."""
    skill_dir = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor'
    if not skill_dir.exists():
        return  # Skip if not found

    args = Namespace(directory=str(skill_dir))
    data = cmd_structure(args)
    score = data.get('structure_score', 0)
    assert score >= 90, f'plugin-doctor should score >= 90, got {score}'


# =============================================================================
# Cross-File Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_crossfile_invalid_path():
    """Test returns error for invalid path."""
    args = Namespace(skill_path='/nonexistent/path', similarity_threshold=0.6)
    data = cmd_crossfile_analyze(args)
    assert data.get('status') == 'error', 'Should return error for invalid path'
    output = str(data).lower()
    assert 'not found' in output or 'error' in output, 'Should indicate path not found'


def test_crossfile_duplicates_valid_json():
    """Test returns valid dict for skill with duplicates."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    args = Namespace(skill_path=str(skill_path), similarity_threshold=0.6)
    data = cmd_crossfile_analyze(args)
    assert data is not None, 'Should return valid dict'


def test_crossfile_detect_exact_duplicates():
    """Test detection of exact duplicates."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    args = Namespace(skill_path=str(skill_path), similarity_threshold=0.6)
    data = cmd_crossfile_analyze(args)
    exact_duplicates = data.get('exact_duplicates', [])
    assert len(exact_duplicates) >= 1, f'Should detect exact duplicates, found {len(exact_duplicates)}'


def test_crossfile_extraction_candidates():
    """Test extraction_candidates field exists."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    args = Namespace(skill_path=str(skill_path), similarity_threshold=0.6)
    data = cmd_crossfile_analyze(args)
    assert 'extraction_candidates' in data, 'Should have extraction_candidates field'


def test_crossfile_llm_review_flag():
    """Test contains llm_review_required flag in summary."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    args = Namespace(skill_path=str(skill_path), similarity_threshold=0.6)
    data = cmd_crossfile_analyze(args)
    summary = data.get('summary', {})
    assert 'llm_review_required' in summary, 'Should contain llm_review_required flag in summary'


def test_crossfile_clean_skill():
    """Test returns valid dict for clean skill."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-clean'
    if not skill_path.exists():
        return  # Skip if fixture not available

    args = Namespace(skill_path=str(skill_path), similarity_threshold=0.6)
    data = cmd_crossfile_analyze(args)
    assert data is not None, 'Should return valid dict for clean skill'


def test_crossfile_custom_threshold():
    """Test accepts custom similarity threshold."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-clean'
    if not skill_path.exists():
        return  # Skip if fixture not available

    args = Namespace(skill_path=str(skill_path), similarity_threshold=0.3)
    data = cmd_crossfile_analyze(args)
    assert data is not None, 'Should accept custom similarity threshold'


# =============================================================================
# Markdown Subcommand Tests - Subdoc Bloat Thresholds (Tier 2 - direct import)
# =============================================================================


def test_markdown_subdoc_bloat_normal():
    """Test subdoc bloat classification: NORMAL for small files."""
    content = '---\nname: test\ndescription: test\n---\n\n# Test\n\n' + 'Line\n' * 100
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='subdoc')
        data = cmd_markdown(args)
        assert data['bloat']['classification'] == 'NORMAL', f'Expected NORMAL, got {data["bloat"]["classification"]}'
    finally:
        temp_file.unlink()


def test_markdown_subdoc_bloat_large():
    """Test subdoc bloat classification: LARGE for >400 lines."""
    content = '# Test\n\n' + 'Line of content here.\n' * 450
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='subdoc')
        data = cmd_markdown(args)
        assert data['bloat']['classification'] == 'LARGE', f'Expected LARGE, got {data["bloat"]["classification"]}'
    finally:
        temp_file.unlink()


def test_markdown_subdoc_bloat_bloated():
    """Test subdoc bloat classification: BLOATED for >600 lines."""
    content = '# Test\n\n' + 'Line of content here.\n' * 650
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='subdoc')
        data = cmd_markdown(args)
        assert data['bloat']['classification'] == 'BLOATED', f'Expected BLOATED, got {data["bloat"]["classification"]}'
    finally:
        temp_file.unlink()


def test_markdown_subdoc_bloat_critical():
    """Test subdoc bloat classification: CRITICAL for >800 lines."""
    content = '# Test\n\n' + 'Line of content here.\n' * 850
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='subdoc')
        data = cmd_markdown(args)
        assert data['bloat']['classification'] == 'CRITICAL', (
            f'Expected CRITICAL, got {data["bloat"]["classification"]}'
        )
    finally:
        temp_file.unlink()


# =============================================================================
# Markdown Subcommand Tests - Rule 12 (Prose-Parameter Consistency)
# =============================================================================


def test_markdown_rule_12_detects_body_fallback():
    """Test Rule 12: detect 'body' section reference near manage-plan-documents call."""
    content = """---
name: test-agent
description: Test agent
tools: Read, Bash
---

# Test Agent

## Step 1: Read Request

If clarified_request is empty, fall back to body section.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \\
  --plan-id {plan_id} \\
  --section clarified_request
```
"""
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='agent')
        data = cmd_markdown(args)
        rule_12 = data.get('rules', {}).get('workflow_prose_param_violations', [])
        assert len(rule_12) >= 1, f'Should detect body section reference, found {len(rule_12)}'
        assert rule_12[0]['pattern'] == 'invalid_section_reference'
    finally:
        temp_file.unlink()


def test_markdown_rule_12_detects_otherwise_body():
    """Test Rule 12: detect 'otherwise body' prose pattern."""
    content = """---
name: test-skill
description: Test skill
---

# Test Skill

### 1.2 Read Request

Read request (clarified_request otherwise body):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \\
  --plan-id {plan_id} \\
  --section clarified_request
```
"""
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        rule_12 = data.get('rules', {}).get('workflow_prose_param_violations', [])
        assert len(rule_12) >= 1, f'Should detect "otherwise body" pattern, found {len(rule_12)}'
    finally:
        temp_file.unlink()


def test_markdown_rule_12_no_false_positive_original_input():
    """Test Rule 12: no false positive when prose correctly says original_input."""
    content = """---
name: test-agent
description: Test agent
tools: Read, Bash
---

# Test Agent

## Step 1: Read Request

Read request (clarified_request falls back to original_input automatically):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \\
  --plan-id {plan_id} \\
  --section clarified_request
```
"""
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='agent')
        data = cmd_markdown(args)
        rule_12 = data.get('rules', {}).get('workflow_prose_param_violations', [])
        assert len(rule_12) == 0, f'Should NOT flag correct original_input reference, found {len(rule_12)}'
    finally:
        temp_file.unlink()


def test_markdown_rule_12_no_false_positive_no_plan_docs():
    """Test Rule 12: no false positive when section has no manage-plan-documents call."""
    content = """---
name: test-agent
description: Test agent
tools: Read, Bash
---

# Test Agent

## Step 1: Process Body

Process the body of the request.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \\
  --plan-id {plan_id} --field domains
```
"""
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='agent')
        data = cmd_markdown(args)
        rule_12 = data.get('rules', {}).get('workflow_prose_param_violations', [])
        assert len(rule_12) == 0, f'Should NOT flag body reference without plan-documents call, found {len(rule_12)}'
    finally:
        temp_file.unlink()


# =============================================================================
# Skill Frontmatter Field Validation Tests (Tier 2 - direct import)
# =============================================================================


def test_markdown_skill_detects_unsupported_tools_field():
    """Test that skills with allowed-tools are flagged as unsupported."""
    content = '---\nname: test-skill\ndescription: Test\nallowed-tools: Read\nuser-invocable: true\n---\n\n# Test\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        fm = data.get('frontmatter', {})
        required = fm.get('required_fields', {})
        tools_info = required.get('tools', {})
        assert tools_info.get('present') is True, 'Should detect allowed-tools field'
        assert tools_info.get('field_type') in ('allowed-tools', 'tools'), (
            f'Should identify field type, got {tools_info.get("field_type")}'
        )
    finally:
        temp_file.unlink()


def test_markdown_skill_detects_misspelled_user_invocable():
    """Test that skills with user-invokable (misspelled) are flagged."""
    content = '---\nname: test-skill\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        fm = data.get('frontmatter', {})
        required = fm.get('required_fields', {})
        user_inv = required.get('user_invocable', {})
        assert user_inv.get('misspelled') is True, 'Should detect misspelled user-invocable'
        assert user_inv.get('present') is False, 'Should not report correct user-invocable as present'
    finally:
        temp_file.unlink()


def test_markdown_skill_detects_correct_user_invocable():
    """Test that skills with correct user-invocable are detected."""
    content = '---\nname: test-skill\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        fm = data.get('frontmatter', {})
        required = fm.get('required_fields', {})
        user_inv = required.get('user_invocable', {})
        assert user_inv.get('present') is True, 'Should detect correct user-invocable'
        assert user_inv.get('misspelled') is False, 'Should not flag correct spelling as misspelled'
    finally:
        temp_file.unlink()


def test_markdown_skill_detects_missing_user_invocable():
    """Test that skills without user-invocable are detected."""
    content = '---\nname: test-skill\ndescription: Test\n---\n\n# Test\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        fm = data.get('frontmatter', {})
        required = fm.get('required_fields', {})
        user_inv = required.get('user_invocable', {})
        assert user_inv.get('present') is False, 'Should not report user-invocable as present'
        assert user_inv.get('misspelled') is False, 'Should not report as misspelled'
    finally:
        temp_file.unlink()


# =============================================================================
# Markdown Subcommand Tests - Checklist Pattern Detection (Tier 2 - direct import)
# =============================================================================


def test_checklist_detection_present():
    """Test checklist detection finds - [ ] patterns."""
    content = '---\nname: test\ndescription: test\n---\n\n# Test\n\n## Rules\n\n- [ ] First item\n- [ ] Second item\n- [ ] Third item\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        checklists = data['checklist_patterns']
        assert checklists['has_checklists'] is True
        assert checklists['count'] == 3
    finally:
        temp_file.unlink()


def test_checklist_detection_absent():
    """Test checklist detection returns False when no checkboxes."""
    content = '---\nname: test\ndescription: test\n---\n\n# Test\n\n- First item\n- Second item\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        checklists = data['checklist_patterns']
        assert checklists['has_checklists'] is False
        assert checklists['count'] == 0
    finally:
        temp_file.unlink()


def test_checklist_detection_mixed():
    """Test checklist detection counts both - [ ] and - [x] patterns."""
    content = (
        '---\nname: test\ndescription: test\n---\n\n# Test\n\n- [ ] Unchecked\n- [x] Checked\n- [X] Also checked\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        checklists = data['checklist_patterns']
        assert checklists['has_checklists'] is True
        assert checklists['count'] == 3
    finally:
        temp_file.unlink()


def test_checklist_template_exempt():
    """Test that files in /templates/ path are exempt from checklist detection."""
    template_path = (
        PROJECT_ROOT
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
        / 'templates'
        / 'pr-template.md'
    )
    if not template_path.exists():
        return  # Skip if fixture not available

    args = Namespace(file=str(template_path), type='skill')
    data = cmd_markdown(args)
    checklists = data['checklist_patterns']
    assert checklists['has_checklists'] is False, 'Templates should be exempt from checklist detection'

    # Non-template file with checkboxes should detect them
    content = '---\nname: test\ndescription: test\n---\n\n# Test\n\n- [ ] Item\n'
    temp_file = create_temp_file(content)
    try:
        args2 = Namespace(file=str(temp_file), type='skill')
        data2 = cmd_markdown(args2)
        assert data2['checklist_patterns']['has_checklists'] is True, 'Non-templates should detect checklists'
    finally:
        temp_file.unlink()


def test_checklist_sections_extracted():
    """Test that section headers containing checklists are identified."""
    content = '---\nname: test\ndescription: test\n---\n\n# Test\n\n## Quality Rules\n\n- [ ] Item A\n\n## Other Section\n\nNo checklists here.\n\n## Verification\n\n- [x] Item B\n'
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        checklists = data['checklist_patterns']
        assert 'Quality Rules' in checklists['sections']
        assert 'Verification' in checklists['sections']
        assert 'Other Section' not in checklists['sections']
    finally:
        temp_file.unlink()


# =============================================================================
# Main
# =============================================================================
