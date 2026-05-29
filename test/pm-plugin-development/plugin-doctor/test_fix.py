#!/usr/bin/env python3
"""Tests for fix.py - consolidated plugin fix tools.

Tests plugin component fix capabilities including:
- extract: Extract fixable issues from diagnosis
- categorize: Categorize fixes as safe/risky
- apply: Apply a single fix
- verify: Verify a fix was applied
"""

import json
import tempfile
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, load_script_module, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_fix.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'fix'


def _load_module(name, filename):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_cmd_apply_mod = _load_module('_cmd_apply', '_cmd_apply.py')
_cmd_categorize_mod = _load_module('_cmd_categorize', '_cmd_categorize.py')
_cmd_extract_mod = _load_module('_cmd_extract', '_cmd_extract.py')
_cmd_verify_mod = _load_module('_cmd_verify', '_cmd_verify.py')

cmd_apply = _cmd_apply_mod.cmd_apply
cmd_categorize = _cmd_categorize_mod.cmd_categorize
cmd_extract = _cmd_extract_mod.cmd_extract
cmd_verify = _cmd_verify_mod.cmd_verify

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
    assert 'extract' in combined, 'extract subcommand in help'
    assert 'categorize' in combined, 'categorize subcommand in help'
    assert 'apply' in combined, 'apply subcommand in help'
    assert 'verify' in combined, 'verify subcommand in help'


def test_apply_missing_arguments():
    """Test apply requires fix and bundle-dir."""
    result = run_script(SCRIPT_PATH, 'apply')
    assert result.returncode != 0, 'Should error without arguments'


# =============================================================================
# Extract Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_extract_from_stdin():
    """Test extract accepts JSON diagnosis data."""
    diagnosis = {
        'issues': [
            {'type': 'missing-frontmatter', 'severity': 'high', 'fixable': True},
            {'type': 'bloat', 'severity': 'medium', 'fixable': False},
        ]
    }
    # Write to temp file for input
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(diagnosis, f)
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_extract(args)
        assert data is not None, 'Should return valid dict'
        assert 'fixable_issues' in data or 'issues' in data, 'Should have issues field'
        Path(f.name).unlink()


# =============================================================================
# Categorize Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_categorize_safe_issues():
    """Test categorize identifies safe fixes."""
    issues = {
        'fixable_issues': [
            {'type': 'checklist-pattern', 'file': 'test.md'},
            {'type': 'subdoc-checklist-pattern', 'file': 'ref.md'},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(issues, f)
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_categorize(args)
        assert data is not None, 'Should return valid dict'
        assert 'safe' in data or 'safe_fixes' in data or 'categorized' in data, 'Should categorize fixes'
        Path(f.name).unlink()


# =============================================================================
# Verify Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_with_valid_file():
    """Test verify with a valid file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='missing-frontmatter', file=f.name)
        data = cmd_verify(args)
        assert data is not None, 'Should return valid dict'

        Path(f.name).unlink()


# =============================================================================
# Rule 11 Apply Tests (Tier 2 - direct import)
# =============================================================================


def test_apply_rule_11_fix():
    """Test applying Rule 11 fix appends Skill to tools."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent_file = Path(tmp_dir) / 'test-agent.md'
        agent_file.write_text('---\nname: test-agent\ndescription: Test\ntools: Read, Write\n---\n\n# Test Agent\n')

        fix_json = json.dumps({'type': 'agent-skill-tool-visibility', 'file': 'test-agent.md'})
        # Write fix to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        # Verify Skill was appended
        content = agent_file.read_text()
        assert 'Skill' in content, 'File should contain Skill after fix'
        assert 'tools: Read, Write, Skill' in content, f'Tools should have Skill appended: {content}'


def test_apply_rule_11_fix_already_present():
    """Test applying Rule 11 fix when Skill already present returns failure."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent_file = Path(tmp_dir) / 'test-agent.md'
        agent_file.write_text('---\nname: test-agent\ndescription: Test\ntools: Read, Skill\n---\n\n# Test Agent\n')

        fix_json = json.dumps({'type': 'agent-skill-tool-visibility', 'file': 'test-agent.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is False, 'Fix should fail when Skill already present'


# =============================================================================
# Rule 11 Verify Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_rule_11_fixed():
    """Test verify reports resolved after Skill is added."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\ntools: Read, Write, Skill\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='agent-skill-tool-visibility', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_rule_11_still_missing():
    """Test verify reports not resolved when Skill still missing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\ntools: Read, Write\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='agent-skill-tool-visibility', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


def test_verify_rule_11_no_tools_field():
    """Test verify reports resolved when no tools field (inherits all)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='agent-skill-tool-visibility', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved (no tools = inherits all): {data}'

        Path(f.name).unlink()


# =============================================================================
# Regression: unsupported-skill-tools-field rule fully removed
# =============================================================================
#
# This rule was fabricated and never had ecosystem support. It was removed in
# the harden-phase3-outline-plugin-doctor-audit plan. The tests below pin the
# removal in three independent ways:
#   - apply: no handler is registered, cmd_apply rejects the fix type
#   - verify: dispatch falls through to verify_generic (issue_resolved is None)
#   - analyze: extract_issues_from_markdown_analysis does NOT emit the rule
#     even when a skill carries a `tools:` field in its frontmatter (the exact
#     trigger condition that the removed rule used to fire on).


def test_unsupported_tools_field_not_in_fix_handlers():
    """Regression: unsupported-skill-tools-field is absent from FIX_HANDLERS."""
    handlers = _cmd_apply_mod.FIX_HANDLERS
    assert 'unsupported-skill-tools-field' not in handlers, (
        f'Removed rule must not have an apply handler: {sorted(handlers.keys())}'
    )


def test_apply_unsupported_tools_field_rejected():
    """Regression: cmd_apply returns success=False for the removed fix type."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text(
            '---\nname: test-skill\ndescription: Test\nallowed-tools: Read, Grep\nuser-invocable: true\n---\n\n# Test\n'
        )

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is False, f'Fix should be rejected with no handler: {data}'
        assert 'No handler' in data.get('error', ''), (
            f"Error should name the missing handler: {data.get('error')}"
        )
        # The original file content must be untouched — no allowed-tools removal.
        content = skill_file.read_text()
        assert 'allowed-tools: Read, Grep' in content, (
            f'File must not be modified when no handler exists: {content}'
        )


def test_verify_unsupported_tools_field_falls_through_to_generic():
    """Regression: cmd_verify routes the removed fix type to verify_generic."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nallowed-tools: Read\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='unsupported-skill-tools-field', file=f.name)
        data = cmd_verify(args)
        # verify_generic returns issue_resolved: None (manual verification recommended)
        assert data.get('issue_resolved') is None, (
            f'Removed rule must hit verify_generic fallthrough: {data}'
        )

        Path(f.name).unlink()


def test_analysis_does_not_emit_unsupported_tools_field_for_skill_with_tools(tmp_path):
    """Regression: extract_issues_from_markdown_analysis never emits the removed rule.

    Builds the exact analysis dict shape that previously triggered the rule
    (a skill with ``required_fields.tools.present == True``) and asserts that
    the issue type is absent from the output.
    """
    # Direct-import the analysis module the same way other analyze tests do.
    da = load_script_module(
        'pm-plugin-development', 'plugin-doctor', '_doctor_analysis.py', '_doctor_analysis_for_regression'
    )

    skill_path = tmp_path / 'SKILL.md'
    skill_path.write_text(
        '---\nname: test-skill\ndescription: Test\ntools: Read\nuser-invocable: true\n---\n\n# Test\n'
    )

    analysis = {
        'frontmatter': {
            'present': True,
            'yaml_valid': True,
            'required_fields': {
                'name': {'present': True},
                'description': {'present': True},
                'tools': {'present': True, 'field_type': 'tools'},
                'user_invocable': {'present': True, 'misspelled': False, 'value': 'true'},
            },
        },
        'metadata': {'line_count': 10},
    }
    issues = da.extract_issues_from_markdown_analysis(analysis, str(skill_path), 'skill')
    issue_types = [i.get('type') for i in issues]
    assert 'unsupported-skill-tools-field' not in issue_types, (
        f'Removed rule must not be emitted by analysis: {issue_types}'
    )


def test_analysis_does_not_emit_unsupported_tools_field_for_skill_with_allowed_tools(tmp_path):
    """Regression: the rule is also absent when skill uses allowed-tools variant."""
    da = load_script_module(
        'pm-plugin-development', 'plugin-doctor', '_doctor_analysis.py', '_doctor_analysis_for_regression_allowed'
    )

    skill_path = tmp_path / 'SKILL.md'
    skill_path.write_text(
        '---\nname: test-skill\ndescription: Test\nallowed-tools: Read, Grep\nuser-invocable: true\n---\n\n# Test\n'
    )

    analysis = {
        'frontmatter': {
            'present': True,
            'yaml_valid': True,
            'required_fields': {
                'name': {'present': True},
                'description': {'present': True},
                'tools': {'present': True, 'field_type': 'allowed-tools'},
                'user_invocable': {'present': True, 'misspelled': False, 'value': 'true'},
            },
        },
        'metadata': {'line_count': 10},
    }
    issues = da.extract_issues_from_markdown_analysis(analysis, str(skill_path), 'skill')
    issue_types = [i.get('type') for i in issues]
    assert 'unsupported-skill-tools-field' not in issue_types, (
        f'Removed rule must not be emitted by analysis: {issue_types}'
    )


# =============================================================================
# Apply misspelled-user-invocable Tests (Tier 2 - direct import)
# =============================================================================


def test_apply_rename_misspelled_user_invocable():
    """Test applying misspelled-user-invocable fix renames user-invokable."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'misspelled-user-invocable', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'user-invocable: true' in content, f'Should rename to user-invocable: {content}'
        assert 'user-invokable' not in content, f'Misspelled field should be gone: {content}'


def test_apply_rename_misspelled_user_invocable_not_present():
    """Test applying misspelled-user-invocable fix when not misspelled fails gracefully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'misspelled-user-invocable', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is False, 'Fix should fail when not misspelled'


# =============================================================================
# Verify misspelled-user-invocable Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_misspelled_user_invocable_resolved():
    """Test verify reports resolved after user-invokable renamed."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='misspelled-user-invocable', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_misspelled_user_invocable_still_present():
    """Test verify reports not resolved when user-invocable still misspelled."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='misspelled-user-invocable', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


# =============================================================================
# Apply checklist-pattern Tests (Tier 2 - direct import)
# =============================================================================


def test_checklist_pattern_is_safe():
    """Test checklist-pattern is categorized as safe fix."""
    issues = {
        'fixable_issues': [
            {'type': 'checklist-pattern', 'file': 'test.md'},
            {'type': 'subdoc-checklist-pattern', 'file': 'ref.md'},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(issues, f)
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_categorize(args)
        Path(f.name).unlink()

    safe = data.get('safe', [])
    safe_types = [fix.get('type') for fix in safe]
    assert 'checklist-pattern' in safe_types, f'checklist-pattern should be safe, got {safe_types}'
    assert 'subdoc-checklist-pattern' in safe_types, f'subdoc-checklist-pattern should be safe, got {safe_types}'


def test_apply_checklist_pattern_fix():
    """Test applying checklist-pattern fix removes - [ ] markers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = Path(tmp_dir) / 'SKILL.md'
        md_file.write_text('---\nname: test\n---\n\n# Test\n\n- [ ] First item\n- [ ] Second item\n- Normal item\n')

        fix_json = json.dumps({'type': 'checklist-pattern', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = md_file.read_text()
        assert '- [ ]' not in content, f'Checkboxes should be removed: {content}'
        assert '- First item' in content, 'List items should be preserved'
        assert '- Normal item' in content, 'Non-checkbox items should be unchanged'


def test_apply_checklist_pattern_fix_mixed():
    """Test applying checklist-pattern fix removes both [ ] and [x] markers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = Path(tmp_dir) / 'test.md'
        md_file.write_text('# Test\n\n- [ ] Unchecked\n- [x] Checked\n- [X] Also checked\n')

        fix_json = json.dumps({'type': 'subdoc-checklist-pattern', 'file': 'test.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = md_file.read_text()
        assert '[ ]' not in content, 'Unchecked boxes should be removed'
        assert '[x]' not in content, 'Checked boxes should be removed'
        assert '- Unchecked' in content, 'List text should be preserved'
        assert '- Checked' in content, 'List text should be preserved'
        assert '- Also checked' in content, 'List text should be preserved'


# =============================================================================
# Simplification Fix Tests (SIMPLICITY_*)
# =============================================================================
#
# Only SIMPLICITY_SIGNATURE_DOCSTRING has an auto-apply handler. The other four
# SIMPLICITY_* rules are detection-only (fixable=False) and have no FIX_HANDLER.


def test_simplicity_signature_docstring_in_fix_handlers():
    """SIMPLICITY_SIGNATURE_DOCSTRING is registered in FIX_HANDLERS."""
    handlers = _cmd_apply_mod.FIX_HANDLERS
    assert 'SIMPLICITY_SIGNATURE_DOCSTRING' in handlers, (
        'SIMPLICITY_SIGNATURE_DOCSTRING must have an auto-apply fix handler'
    )


def test_simplicity_other_four_not_in_fix_handlers():
    """The four detection-only SIMPLICITY_* rules have no auto-apply handler."""
    handlers = _cmd_apply_mod.FIX_HANDLERS
    for rule in (
        'SIMPLICITY_UNUSED_PARAMETER',
        'SIMPLICITY_BACKWARD_COMPAT_REEXPORT',
        'SIMPLICITY_DEFENSIVE_CATCHALL',
        'SIMPLICITY_THIN_WRAPPER',
    ):
        assert rule not in handlers, f'{rule} must be detection-only (no auto-apply handler)'


def test_apply_signature_docstring_fix_removes_restating_docstring():
    """Applying SIMPLICITY_SIGNATURE_DOCSTRING deletes the signature-restating docstring."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        py_file = Path(tmp_dir) / 'sample.py'
        py_file.write_text(
            'def f(a, b):\n'
            '    """Args:\n'
            '\n'
            '    Returns:\n'
            '    """\n'
            '    return a + b\n',
            encoding='utf-8',
        )

        fix_json = json.dumps({'type': 'SIMPLICITY_SIGNATURE_DOCSTRING', 'file': 'sample.py'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'
        content = py_file.read_text()
        assert 'Args:' not in content, f'Restating docstring should be removed: {content!r}'
        assert 'return a + b' in content, 'Function body must be preserved'


def test_apply_signature_docstring_fix_inserts_pass_for_sole_docstring():
    """A function whose body is ONLY a signature-restating docstring gets a ``pass``.

    Regression for PR #499 review 7877ca: deleting the sole-statement docstring
    leaves an empty function body, which is a SyntaxError. The fix replaces the
    docstring with a ``pass`` (preserving indentation) so the result still
    parses.
    """
    import ast as _ast

    with tempfile.TemporaryDirectory() as tmp_dir:
        py_file = Path(tmp_dir) / 'sample.py'
        py_file.write_text(
            'def f(a, b):\n'
            '    """Args:\n'
            '\n'
            '    Returns:\n'
            '    """\n',
            encoding='utf-8',
        )

        fix_json = json.dumps({'type': 'SIMPLICITY_SIGNATURE_DOCSTRING', 'file': 'sample.py'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'
        content = py_file.read_text()
        assert 'Args:' not in content, f'Restating docstring should be removed: {content!r}'
        assert '    pass' in content, f'Sole-docstring body should be replaced with pass: {content!r}'
        # The resulting source must still parse (no empty-block SyntaxError).
        _ast.parse(content)


def test_apply_signature_docstring_fix_preserves_intent_docstring():
    """A docstring with intent content is NOT removed by the fix."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        py_file = Path(tmp_dir) / 'sample.py'
        original = (
            'def f(a, b):\n'
            '    """Combine the two halves into the canonical key.\n'
            '\n'
            '    Args:\n'
            '    a: first\n'
            '    """\n'
            '    return a + b\n'
        )
        py_file.write_text(original, encoding='utf-8')

        fix_json = json.dumps({'type': 'SIMPLICITY_SIGNATURE_DOCSTRING', 'file': 'sample.py'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        # No restating docstring present → handler reports failure (nothing to fix)
        # and the intent docstring is left untouched.
        assert data['success'] is False, f'Intent docstring should not be removed: {data}'
        content = py_file.read_text()
        assert 'Combine the two halves' in content, 'Intent docstring must be preserved'


def test_categorize_simplicity_signature_docstring_safe():
    """SIMPLICITY_SIGNATURE_DOCSTRING categorizes as a safe fix."""
    extracted = {'fixable_issues': [{'type': 'SIMPLICITY_SIGNATURE_DOCSTRING', 'fixable': True}]}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(json.dumps(extracted))
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_categorize(args)
        Path(f.name).unlink()
    safe_types = {issue['type'] for issue in data.get('safe', [])}
    assert 'SIMPLICITY_SIGNATURE_DOCSTRING' in safe_types, f'Should be categorized safe, got {data}'


# =============================================================================
# Main
# =============================================================================
