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
_doctor_analysis_mod = _load_module('_doctor_analysis', '_doctor_analysis.py')

cmd_crossfile_analyze = _analyze_crossfile_mod.cmd_cross_file
cmd_markdown = _analyze_markdown_mod.cmd_markdown
cmd_structure = _analyze_structure_mod.cmd_structure
analyze_subdocuments = _doctor_analysis_mod.analyze_subdocuments
extract_issues_from_subdoc_analysis = _doctor_analysis_mod.extract_issues_from_subdoc_analysis

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
# Structure Subcommand Tests - skill-naming-noun-suffix Rule
# =============================================================================


def test_structure_noun_suffix_flags_executor(tmp_path):
    """Skill directory names ending in reserved -executor are flagged."""
    fixture_src = SKILL_STRUCTURE_FIXTURES / 'skill-with-noun-suffix'
    if not fixture_src.exists():
        return  # Skip if fixture not available

    # Rename the fixture into a reserved-suffix directory name for this test.
    target = tmp_path / 'sample-executor'
    target.mkdir()
    (target / 'SKILL.md').write_text((fixture_src / 'SKILL.md').read_text(encoding='utf-8'), encoding='utf-8')

    args = Namespace(directory=str(target))
    data = cmd_structure(args)

    noun_suffix = data.get('noun_suffix', {})
    assert noun_suffix.get('violation') is True, f'Expected violation=True, got {noun_suffix!r}'
    assert noun_suffix.get('suffix') == '-executor', f'Expected suffix=-executor, got {noun_suffix.get("suffix")!r}'
    assert noun_suffix.get('directory_name') == 'sample-executor'
    # Score is penalised when a violation is present.
    assert data.get('structure_score', 100) < 100, 'Noun-suffix violation should reduce structure_score'


def test_structure_noun_suffix_flags_plurals(tmp_path):
    """Plural reserved suffixes (-managers) are also flagged."""
    fixture_src = SKILL_STRUCTURE_FIXTURES / 'skill-with-noun-suffix'
    if not fixture_src.exists():
        return  # Skip if fixture not available

    target = tmp_path / 'resource-managers'
    target.mkdir()
    (target / 'SKILL.md').write_text((fixture_src / 'SKILL.md').read_text(encoding='utf-8'), encoding='utf-8')

    args = Namespace(directory=str(target))
    data = cmd_structure(args)

    noun_suffix = data.get('noun_suffix', {})
    assert noun_suffix.get('violation') is True, f'Expected violation=True, got {noun_suffix!r}'
    assert noun_suffix.get('suffix') == '-managers', f'Expected suffix=-managers, got {noun_suffix.get("suffix")!r}'


def test_structure_noun_suffix_passes_verb_first_name():
    """Verb-first skill directory names are not flagged."""
    skill_dir = (
        PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'execute-task'
    )
    if not skill_dir.exists():
        return  # Skip if not found (depends on rename tasks completing earlier)

    args = Namespace(directory=str(skill_dir))
    data = cmd_structure(args)

    noun_suffix = data.get('noun_suffix', {})
    assert noun_suffix.get('violation') is False, f'Verb-first name should not be flagged, got {noun_suffix!r}'
    assert noun_suffix.get('suffix') is None


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
# Markdown Subcommand Tests - mark-step-done Argument Validation
# =============================================================================


def _canonical_mark_step_done_block(extra_args: str = '') -> str:
    """Build a canonical (correct) mark-step-done bash fence.

    Uses the underscored notation ``manage-status:manage_status`` and always
    supplies ``--phase`` and ``--outcome``. Callers can inject additional args
    via ``extra_args`` (appended after the required ones) for variants that
    should still be considered canonical.
    """

    return (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --phase 6-finalize --outcome done '
        '--step my-step --display-detail "ok"' + (f' {extra_args}' if extra_args else '') + '\n'
        '```\n'
    )


def _mark_step_done_codes(violations: list) -> list:
    """Extract the ``code`` field from each violation entry for easy assertion."""

    return [v.get('code') for v in violations]


def test_mark_step_done_bad_notation_detected():
    """Hyphenated `manage-status:manage-status` notation triggers BAD_NOTATION."""
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
        'mark-step-done --plan-id foo --phase 6-finalize --outcome done '
        '--step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        codes = _mark_step_done_codes(violations)
        assert codes.count('MARK_STEP_DONE_BAD_NOTATION') == 1, (
            f'Expected exactly one BAD_NOTATION finding, got codes={codes}'
        )
    finally:
        temp_file.unlink()


def test_mark_step_done_missing_phase_detected():
    """Canonical-notation invocation without --phase triggers MISSING_PHASE."""
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --outcome done '
        '--step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        codes = _mark_step_done_codes(violations)
        assert codes.count('MARK_STEP_DONE_MISSING_PHASE') == 1, (
            f'Expected exactly one MISSING_PHASE finding, got codes={codes}'
        )
        # Canonical notation + outcome present → no other defect codes expected.
        assert 'MARK_STEP_DONE_BAD_NOTATION' not in codes
        assert 'MARK_STEP_DONE_MISSING_OUTCOME' not in codes
    finally:
        temp_file.unlink()


def test_mark_step_done_missing_outcome_detected():
    """Canonical-notation invocation without --outcome triggers MISSING_OUTCOME."""
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --phase 6-finalize '
        '--step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        codes = _mark_step_done_codes(violations)
        assert codes.count('MARK_STEP_DONE_MISSING_OUTCOME') == 1, (
            f'Expected exactly one MISSING_OUTCOME finding, got codes={codes}'
        )
        assert 'MARK_STEP_DONE_BAD_NOTATION' not in codes
        assert 'MARK_STEP_DONE_MISSING_PHASE' not in codes
    finally:
        temp_file.unlink()


def test_mark_step_done_canonical_form_no_findings():
    """Fully canonical mark-step-done invocation produces zero findings."""
    content = _canonical_mark_step_done_block()
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        assert violations == [], f'Canonical form should yield no findings, got {violations!r}'
    finally:
        temp_file.unlink()


def test_mark_step_done_non_bash_fence_no_false_positive():
    """`mark-step-done` inside a non-bash fence or plain prose is ignored."""
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Background\n\n'
        'The old habit was to call mark-step-done with hyphen notation like '
        '`plan-marshall:manage-status:manage-status mark-step-done` in prose — '
        'we now warn about it only inside bash fences.\n\n'
        '```text\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
        'mark-step-done --plan-id foo\n'
        '```\n\n'
        '```python\n'
        '# Commentary-only python block also mentions mark-step-done but must not trigger.\n'
        'cmd = "mark-step-done"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        assert violations == [], (
            f'Non-bash fences and prose should not trigger mark-step-done rule, got {violations!r}'
        )
    finally:
        temp_file.unlink()


def test_mark_step_done_multiline_continuation_assembled():
    """Backslash-continued invocation is assembled so --phase/--outcome on later lines are seen."""
    # Canonical notation split across three lines via trailing backslash
    # continuation. --phase and --outcome live on continuation lines, so the
    # single-line check would miss them; the rule must assemble the full
    # invocation before evaluating MISSING_PHASE / MISSING_OUTCOME.
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \\\n'
        '  mark-step-done --plan-id foo \\\n'
        '  --phase 6-finalize \\\n'
        '  --outcome done --step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        assert violations == [], (
            f'Multi-line canonical invocation should produce no findings once assembled, got {violations!r}'
        )
    finally:
        temp_file.unlink()


def test_mark_step_done_multiline_continuation_detects_bad_notation():
    """Bad notation on a continuation line after `mark-step-done` is still caught after assembly.

    The rule anchors on the line that contains ``mark-step-done`` and walks
    forward over trailing-backslash continuations to assemble the full
    invocation. This test pins that forward-assembly behaviour: the offending
    hyphenated notation appears on a continuation line below the anchor line,
    yet the rule must still flag BAD_NOTATION on the anchor line.
    """
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py mark-step-done \\\n'
        '  --notation plan-marshall:manage-status:manage-status \\\n'
        '  --plan-id foo --phase 6-finalize --outcome done \\\n'
        '  --step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        codes = _mark_step_done_codes(violations)
        assert codes.count('MARK_STEP_DONE_BAD_NOTATION') == 1, (
            f'Expected exactly one BAD_NOTATION finding across continuation lines, got codes={codes}'
        )
        # --phase and --outcome are present on the continuation → no MISSING_* codes.
        assert 'MARK_STEP_DONE_MISSING_PHASE' not in codes
        assert 'MARK_STEP_DONE_MISSING_OUTCOME' not in codes
    finally:
        temp_file.unlink()


def test_mark_step_done_bad_notation_on_line_before_anchor():
    """Bad notation on a continuation line ABOVE `mark-step-done` is still caught.

    A real-world pattern is:

        python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \\
          mark-step-done --plan-id foo --phase 6-finalize --outcome done

    Here the offending hyphenated notation lives on the line that ends with a
    trailing backslash, and ``mark-step-done`` is on the continuation line
    below. The rule must assemble the full logical command (regardless of
    which line anchors ``mark-step-done``) and still flag BAD_NOTATION.
    """
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \\\n'
        '  mark-step-done --plan-id foo --phase 6-finalize --outcome done \\\n'
        '  --step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        codes = _mark_step_done_codes(violations)
        assert codes.count('MARK_STEP_DONE_BAD_NOTATION') == 1, (
            f'Expected BAD_NOTATION across a backward-referenced continuation, got codes={codes}'
        )
        assert 'MARK_STEP_DONE_MISSING_PHASE' not in codes
        assert 'MARK_STEP_DONE_MISSING_OUTCOME' not in codes
    finally:
        temp_file.unlink()


def test_mark_step_done_phase_prefix_does_not_spoof_missing_phase():
    """A flag like ``--phase-override`` must NOT satisfy the ``--phase`` presence check.

    Substring matching (``'--phase' in text``) would let a partial-match flag
    such as ``--phase-override`` spoof the presence of the real ``--phase``
    argument. The rule uses anchored matching with word boundaries so that
    MARK_STEP_DONE_MISSING_PHASE still fires in this case.
    """
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --phase-override "hack" --outcome done '
        '--step s --display-detail "x"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('mark_step_done_violations', [])
        codes = _mark_step_done_codes(violations)
        assert codes.count('MARK_STEP_DONE_MISSING_PHASE') == 1, (
            f'Expected MISSING_PHASE even though --phase-override is present, got codes={codes}'
        )
        assert 'MARK_STEP_DONE_BAD_NOTATION' not in codes
        assert 'MARK_STEP_DONE_MISSING_OUTCOME' not in codes
    finally:
        temp_file.unlink()


# =============================================================================
# Markdown Subcommand Tests - --display-detail ASCII contract
# =============================================================================


def _display_detail_block(detail_value: str) -> str:
    """Build a canonical mark-step-done bash fence with a caller-supplied detail value.

    The value is inlined verbatim between double quotes, mirroring the
    canonical phase-6-finalize step termination shape. Callers pass the body
    of the ``--display-detail`` argument (without the surrounding quotes).
    """

    return (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --phase 6-finalize --outcome done '
        f'--step my-step --display-detail "{detail_value}"\n'
        '```\n'
    )


def _display_detail_codes(violations: list) -> list:
    """Extract the ``code`` field from each display_detail violation entry."""

    return [v.get('code') for v in violations]


def test_display_detail_em_dash_triggers_non_ascii():
    """Em-dash (U+2014) in --display-detail triggers DISPLAY_DETAIL_NON_ASCII."""
    content = _display_detail_block('no PR — nothing to clean up')
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        codes = _display_detail_codes(violations)
        assert codes.count('DISPLAY_DETAIL_NON_ASCII') == 1, (
            f'Expected exactly one NON_ASCII finding for em-dash value, got codes={codes}'
        )
        non_ascii = next(v for v in violations if v['code'] == 'DISPLAY_DETAIL_NON_ASCII')
        assert '—' in non_ascii['value'], 'Reported value should preserve the offending unicode glyph'
    finally:
        temp_file.unlink()


def test_display_detail_too_long_triggers_too_long():
    """An 81-character --display-detail value triggers DISPLAY_DETAIL_TOO_LONG."""
    content = _display_detail_block('a' * 81)
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        codes = _display_detail_codes(violations)
        assert codes.count('DISPLAY_DETAIL_TOO_LONG') == 1, (
            f'Expected exactly one TOO_LONG finding for 81-char value, got codes={codes}'
        )
        assert 'DISPLAY_DETAIL_NON_ASCII' not in codes
        assert 'DISPLAY_DETAIL_MULTILINE' not in codes
        assert 'DISPLAY_DETAIL_TRAILING_PERIOD' not in codes
    finally:
        temp_file.unlink()


def test_display_detail_multiline_quoted_value_triggers_multiline():
    """Multi-line quoted --display-detail value triggers DISPLAY_DETAIL_MULTILINE.

    A bash double-quoted string can span multiple lines without backslash
    continuation. The rule must assemble the full quoted value across line
    boundaries and flag the embedded newline.
    """
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Step: Mark Done\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --phase 6-finalize --outcome done '
        '--step my-step --display-detail "first line\n'
        'second line"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        codes = _display_detail_codes(violations)
        assert codes.count('DISPLAY_DETAIL_MULTILINE') == 1, (
            f'Expected exactly one MULTILINE finding for multi-line value, got codes={codes}'
        )
    finally:
        temp_file.unlink()


def test_display_detail_trailing_period_triggers_trailing_period():
    """A --display-detail value ending in `.` triggers DISPLAY_DETAIL_TRAILING_PERIOD."""
    content = _display_detail_block('archived plan.')
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        codes = _display_detail_codes(violations)
        assert codes.count('DISPLAY_DETAIL_TRAILING_PERIOD') == 1, (
            f'Expected exactly one TRAILING_PERIOD finding for "archived plan.", got codes={codes}'
        )
        assert 'DISPLAY_DETAIL_NON_ASCII' not in codes
        assert 'DISPLAY_DETAIL_TOO_LONG' not in codes
        assert 'DISPLAY_DETAIL_MULTILINE' not in codes
    finally:
        temp_file.unlink()


def test_display_detail_canonical_value_no_findings():
    """Plain ASCII, single-line, ≤80 chars, no trailing period yields zero findings."""
    content = _display_detail_block('no PR, nothing to clean up')
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        assert violations == [], f'Canonical value should yield no findings, got {violations!r}'
    finally:
        temp_file.unlink()


def test_display_detail_multiple_defects_all_reported():
    """A value that violates multiple constraints emits one finding per defect kind."""
    # >80 chars, ends with `.`, contains em-dash → expect NON_ASCII + TOO_LONG + TRAILING_PERIOD.
    long_bad_value = 'no PR — ' + ('x' * 80) + '.'
    assert len(long_bad_value) > 80, 'fixture must exceed 80 chars to trigger TOO_LONG'
    content = _display_detail_block(long_bad_value)
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        codes = _display_detail_codes(violations)
        assert 'DISPLAY_DETAIL_NON_ASCII' in codes
        assert 'DISPLAY_DETAIL_TOO_LONG' in codes
        assert 'DISPLAY_DETAIL_TRAILING_PERIOD' in codes
        assert 'DISPLAY_DETAIL_MULTILINE' not in codes
    finally:
        temp_file.unlink()


def test_display_detail_non_bash_fence_no_false_positive():
    """`mark-step-done` with em-dash inside a non-bash fence is ignored."""
    content = (
        '---\nname: test-skill\ndescription: Test\n---\n\n'
        '# Test Skill\n\n'
        '## Background\n\n'
        '```text\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
        'mark-step-done --plan-id foo --phase 6-finalize --outcome done '
        '--step s --display-detail "no PR — nothing to clean up"\n'
        '```\n'
    )
    temp_file = create_temp_file(content)
    try:
        args = Namespace(file=str(temp_file), type='skill')
        data = cmd_markdown(args)
        violations = data.get('rules', {}).get('display_detail_violations', [])
        assert violations == [], f'Non-bash fence should not trigger display_detail rule, got {violations!r}'
    finally:
        temp_file.unlink()


def test_display_detail_subdoc_em_dash_surfaces_in_subdoc_analysis():
    """Em-dash in a standards/*.md mark-step-done invocation surfaces as a subdoc issue.

    Pins the wiring through ``analyze_subdocuments`` →
    ``extract_issues_from_subdoc_analysis`` so violations in
    ``phase-6-finalize/standards/*.md`` (the original failure surface that
    motivated this rule) fail ``verify`` locally rather than only at PR review.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_root:
        skill_dir = Path(tmp_root) / 'plugin-doctor-fixture'
        standards_dir = skill_dir / 'standards'
        standards_dir.mkdir(parents=True)
        bad_doc = standards_dir / 'branch-cleanup.md'
        bad_doc.write_text(
            '# Branch Cleanup\n\n'
            '```bash\n'
            'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status '
            'mark-step-done --plan-id foo --phase 6-finalize --outcome done '
            '--step s --display-detail "no PR — nothing to clean up"\n'
            '```\n',
            encoding='utf-8',
        )

        subdoc_results = analyze_subdocuments(skill_dir)
        issues = extract_issues_from_subdoc_analysis(subdoc_results, str(skill_dir))

        non_ascii_issues = [i for i in issues if i.get('type') == 'DISPLAY_DETAIL_NON_ASCII']
        assert len(non_ascii_issues) == 1, (
            f'Expected exactly one DISPLAY_DETAIL_NON_ASCII subdoc issue, got {issues!r}'
        )
        issue = non_ascii_issues[0]
        assert issue['file'] == str(bad_doc)
        assert issue['severity'] == 'error'
        assert issue['fixable'] is False
        assert issue['line'] is not None


# =============================================================================
# Main
# =============================================================================
