# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Behavioral tests for ``_cmd_verify.py`` — the fix-verification predicates.

Each ``verify_*`` function reads a file and reports whether a previously-applied
fix resolved its issue (``issue_resolved``) along with a ``verified`` flag for
read success. The functions are pure (path in, dict out), so they are driven
here with ``tmp_path`` files staged in both the resolved and unresolved states,
plus the OSError path (a directory passed where a file is expected) and the
``cmd_verify`` dispatcher's error envelopes.
"""

import types
from pathlib import Path

from conftest import load_script_module

_verify = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_cmd_verify.py', '_cmd_verify_under_test'
)


def _file(tmp_path: Path, content: str, name: str = 'comp.md') -> Path:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return p


# =============================================================================
# verify_frontmatter_fix
# =============================================================================


def test_verify_frontmatter_resolved_when_name_and_description_present(tmp_path):
    f = _file(tmp_path, '---\nname: a\ndescription: d\n---\n\n# A\n')

    result = _verify.verify_frontmatter_fix(f)

    assert result['verified'] is True
    assert result['issue_resolved'] is True


def test_verify_frontmatter_unresolved_when_no_frontmatter(tmp_path):
    f = _file(tmp_path, '# A\n\nNo frontmatter here.\n')

    result = _verify.verify_frontmatter_fix(f)

    assert result['issue_resolved'] is False
    assert 'missing frontmatter' in result['details'].lower()


def test_verify_frontmatter_unresolved_when_description_missing(tmp_path):
    f = _file(tmp_path, '---\nname: a\n---\n\n# A\n')

    result = _verify.verify_frontmatter_fix(f)

    assert result['issue_resolved'] is False


def test_verify_frontmatter_read_failure_on_directory(tmp_path):
    a_dir = tmp_path / 'a-directory'
    a_dir.mkdir()

    result = _verify.verify_frontmatter_fix(a_dir)

    assert result['verified'] is False
    assert 'error' in result


# =============================================================================
# verify_array_syntax_fix
# =============================================================================


def test_verify_array_syntax_unresolved_when_brackets_remain(tmp_path):
    f = _file(tmp_path, '---\nname: a\ntools: [Read, Write]\n---\n\n# A\n')

    result = _verify.verify_array_syntax_fix(f)

    assert result['issue_resolved'] is False


def test_verify_array_syntax_resolved_when_comma_separated(tmp_path):
    f = _file(tmp_path, '---\nname: a\ntools: Read, Write\n---\n\n# A\n')

    result = _verify.verify_array_syntax_fix(f)

    assert result['issue_resolved'] is True


def test_verify_array_syntax_resolved_when_no_frontmatter(tmp_path):
    f = _file(tmp_path, '# A\n\nNo frontmatter.\n')

    result = _verify.verify_array_syntax_fix(f)

    assert result['issue_resolved'] is True


# =============================================================================
# verify_task_tool_fix
# =============================================================================


def test_verify_task_tool_unresolved_when_task_present(tmp_path):
    f = _file(tmp_path, '---\nname: a\ntools: Read, Task, Skill\n---\n\n# A\n')

    result = _verify.verify_task_tool_fix(f)

    assert result['issue_resolved'] is False


def test_verify_task_tool_resolved_when_task_removed(tmp_path):
    f = _file(tmp_path, '---\nname: a\ntools: Read, Skill\n---\n\n# A\n')

    result = _verify.verify_task_tool_fix(f)

    assert result['issue_resolved'] is True


# =============================================================================
# verify_trailing_whitespace_fix
# =============================================================================


def test_verify_trailing_whitespace_unresolved_when_present(tmp_path):
    f = _file(tmp_path, '# A   \n\nline with trailing\t\n')

    result = _verify.verify_trailing_whitespace_fix(f)

    assert result['issue_resolved'] is False


def test_verify_trailing_whitespace_resolved_when_clean(tmp_path):
    f = _file(tmp_path, '# A\n\nclean line\n')

    result = _verify.verify_trailing_whitespace_fix(f)

    assert result['issue_resolved'] is True


# =============================================================================
# verify_lessons_via_skill_fix
# =============================================================================


def test_verify_lessons_via_skill_unresolved_when_self_update_present(tmp_path):
    f = _file(tmp_path, '# A\n\nRun /plugin-update-agent to refresh.\n')

    result = _verify.verify_lessons_via_skill_fix(f)

    assert result['issue_resolved'] is False


def test_verify_lessons_via_skill_resolved_when_removed(tmp_path):
    f = _file(tmp_path, '# A\n\nNo self-update commands here.\n')

    result = _verify.verify_lessons_via_skill_fix(f)

    assert result['issue_resolved'] is True


# =============================================================================
# verify_skill_tool_visibility_fix
# =============================================================================


def test_verify_skill_tool_visibility_resolved_when_no_tools_field(tmp_path):
    f = _file(tmp_path, '---\nname: a\ndescription: d\n---\n\n# A\n')

    result = _verify.verify_skill_tool_visibility_fix(f)

    assert result['issue_resolved'] is True


def test_verify_skill_tool_visibility_resolved_when_skill_declared(tmp_path):
    f = _file(tmp_path, '---\nname: a\ntools: Read, Skill\n---\n\n# A\n')

    result = _verify.verify_skill_tool_visibility_fix(f)

    assert result['issue_resolved'] is True


def test_verify_skill_tool_visibility_unresolved_when_skill_absent(tmp_path):
    f = _file(tmp_path, '---\nname: a\ntools: Read, Write\n---\n\n# A\n')

    result = _verify.verify_skill_tool_visibility_fix(f)

    assert result['issue_resolved'] is False


# =============================================================================
# verify_misspelled_user_invocable_fix
# =============================================================================


def test_verify_misspelled_user_invocable_unresolved_when_misspelled(tmp_path):
    f = _file(tmp_path, '---\nname: a\nuser-invokable: false\n---\n\n# A\n')

    result = _verify.verify_misspelled_user_invocable_fix(f)

    assert result['issue_resolved'] is False


def test_verify_misspelled_user_invocable_resolved_when_correct(tmp_path):
    f = _file(tmp_path, '---\nname: a\nuser-invocable: false\n---\n\n# A\n')

    result = _verify.verify_misspelled_user_invocable_fix(f)

    assert result['issue_resolved'] is True


# =============================================================================
# verify_invokable_mismatch_fix
# =============================================================================


def test_verify_invokable_mismatch_unresolved_reference_mode_still_invocable(tmp_path):
    f = _file(
        tmp_path,
        '---\nname: a\nuser-invocable: true\n---\n\n# A\n\n**REFERENCE MODE**: reference content.\n',
    )

    result = _verify.verify_invokable_mismatch_fix(f)

    assert result['issue_resolved'] is False


def test_verify_invokable_mismatch_resolved_when_reference_mode_not_invocable(tmp_path):
    f = _file(
        tmp_path,
        '---\nname: a\nuser-invocable: false\n---\n\n# A\n\n**REFERENCE MODE**: reference content.\n',
    )

    result = _verify.verify_invokable_mismatch_fix(f)

    assert result['issue_resolved'] is True


# =============================================================================
# verify_generic
# =============================================================================


def test_verify_generic_defers_to_manual(tmp_path):
    f = _file(tmp_path, '# A\n')

    result = _verify.verify_generic(f, 'some-unknown-fix')

    assert result['issue_resolved'] is None
    assert 'manual' in result['details'].lower()


# =============================================================================
# cmd_verify dispatcher
# =============================================================================


def test_cmd_verify_file_not_found(tmp_path):
    args = types.SimpleNamespace(file=str(tmp_path / 'absent.md'), fix_type='trailing-whitespace')

    result = _verify.cmd_verify(args)

    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


def test_cmd_verify_not_a_file(tmp_path):
    a_dir = tmp_path / 'd'
    a_dir.mkdir()
    args = types.SimpleNamespace(file=str(a_dir), fix_type='trailing-whitespace')

    result = _verify.cmd_verify(args)

    assert result['status'] == 'error'
    assert result['error'] == 'not_a_file'


def test_cmd_verify_dispatches_to_trailing_whitespace(tmp_path):
    f = _file(tmp_path, '# clean\n')
    args = types.SimpleNamespace(file=str(f), fix_type='trailing-whitespace')

    result = _verify.cmd_verify(args)

    assert result['status'] == 'success'
    assert result['issue_resolved'] is True


def test_cmd_verify_dispatches_to_generic_for_unknown_type(tmp_path):
    f = _file(tmp_path, '# anything\n')
    args = types.SimpleNamespace(file=str(f), fix_type='totally-unknown')

    result = _verify.cmd_verify(args)

    assert result['status'] == 'success'
    assert result['issue_resolved'] is None
