# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``refine-contract-violation`` rule analyzer.

The analyzer scans ``phase-2-refine/`` workflow files for ``Edit`` / ``Write``
tool references whose path argument is not prefixed with ``.plan/local/``,
``{WORKTREE}/.plan/local/``, or ``{worktree_path}/.plan/local/``. The
contract documented in ``phase-2-refine/SKILL.md`` § Enforcement → Allowed
write paths restricts refine to writing only inside the plan's own scope.

Test layers:
  * Clean workflow file (no Edit/Write calls)                → no finding.
  * Edit targeting ``marketplace/.../foo.md``                → one finding.
  * Write targeting ``src/main/foo.py``                      → one finding.
  * Edit targeting ``.plan/local/plans/{plan_id}/foo.md``    → no finding.
  * Edit targeting ``{WORKTREE}/.plan/local/...``           → no finding.
  * Write targeting ``{worktree_path}/.plan/local/...``     → no finding.
  * ``Read`` of any path                                     → no finding.
  * ``rules_filter`` excluding the rule                      → no findings.
  * ``rules_filter`` including the rule                      → findings emitted.
  * File outside ``phase-2-refine/``                         → out of scope, no findings.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_a = _load_module(
    '_analyze_phase2_refine_contract',
    '_analyze_phase2_refine_contract.py',
)

analyze_phase2_refine_contract = _a.analyze_phase2_refine_contract
RULE_ID = _a.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_refine_file(tmp_path: Path, content: str, filename: str = 'SKILL.md') -> Path:
    """Create ``<tmp>/phase-2-refine/<filename>`` with the given content.

    Returns the path to the created file.
    """
    refine_dir = tmp_path / 'phase-2-refine'
    refine_dir.mkdir(parents=True, exist_ok=True)
    file_path = refine_dir / filename
    file_path.write_text(content, encoding='utf-8')
    return file_path


def _make_outside_file(tmp_path: Path, content: str) -> Path:
    """Create a markdown file OUTSIDE any phase-2-refine directory."""
    outside_dir = tmp_path / 'phase-5-execute'
    outside_dir.mkdir(parents=True, exist_ok=True)
    file_path = outside_dir / 'SKILL.md'
    file_path.write_text(content, encoding='utf-8')
    return file_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_clean_workflow_emits_no_findings(tmp_path: Path) -> None:
    """A workflow file with no Edit/Write references must produce no findings."""
    content = (
        '# Phase 2 Refine\n'
        '\n'
        'This file describes the refine phase but does not invoke any tools.\n'
        'It mentions Read operations only, and lists script calls.\n'
        '\n'
        '`python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read --plan-id X`\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert findings == []


def test_edit_to_marketplace_emits_finding(tmp_path: Path) -> None:
    """An Edit call targeting marketplace/ must produce a finding."""
    content = (
        '# Refine Step\n'
        '\n'
        'Update the standards file:\n'
        '\n'
        'Edit("marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    # Rule-specific keys are carried in the nested ``details`` dict on the
    # migrated Finding record (top-level ``type``/``rule_id``/``file``/``line``).
    assert finding['details']['tool'] == 'Edit'
    assert 'marketplace' in finding['details']['path']
    assert finding['line'] == 5


def test_write_to_src_emits_finding(tmp_path: Path) -> None:
    """A Write call targeting src/ must produce a finding."""
    content = (
        '# Refine\n'
        '\n'
        'Write(file_path="src/main/foo.py", content="...")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert len(findings) == 1
    assert findings[0]['details']['tool'] == 'Write'
    assert findings[0]['details']['path'] == 'src/main/foo.py'


def test_plan_local_path_is_allowed(tmp_path: Path) -> None:
    """An Edit targeting .plan/local/ must produce no finding."""
    content = (
        '# Refine\n'
        '\n'
        'Edit(".plan/local/plans/my-plan/request.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert findings == []


def test_worktree_prefix_uppercase_placeholder_is_allowed(tmp_path: Path) -> None:
    """{WORKTREE}/.plan/local/... is the worktree-substituted form — allowed."""
    content = (
        '# Refine\n'
        '\n'
        'Edit("{WORKTREE}/.plan/local/plans/my-plan/clarifications.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert findings == []


def test_worktree_path_placeholder_is_allowed(tmp_path: Path) -> None:
    """{worktree_path}/.plan/local/... is also a valid substitution form."""
    content = (
        '# Refine\n'
        '\n'
        'Write(file_path="{worktree_path}/.plan/local/plans/p/request.md", content="...")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert findings == []


def test_read_calls_are_ignored(tmp_path: Path) -> None:
    """Read is allowed against any path — must produce no finding."""
    content = (
        '# Refine\n'
        '\n'
        'Read("marketplace/bundles/some/file.md")\n'
        'Read("src/main/java/Foo.java")\n'
        'Read("/etc/passwd")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert findings == []


def test_rules_filter_excludes_rule(tmp_path: Path) -> None:
    """When the rule is not in rules_filter, the analyzer returns no findings."""
    content = (
        '# Refine\n'
        'Edit("marketplace/foo.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # supply a filter that excludes this rule
    findings = analyze_phase2_refine_contract([file_path], rules_filter={'other-rule'})

    assert findings == []


def test_rules_filter_includes_rule(tmp_path: Path) -> None:
    """When the rule IS in rules_filter, findings are emitted normally."""
    content = (
        '# Refine\n'
        'Edit("marketplace/foo.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract(
        [file_path],
        rules_filter={RULE_ID, 'other-rule'},
    )

    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID


def test_file_outside_phase2_refine_is_out_of_scope(tmp_path: Path) -> None:
    """Files outside phase-2-refine/ are not scanned even when passed directly."""
    content = (
        '# Phase 5 Execute\n'
        'Edit("marketplace/foo.md")\n'
    )
    outside_file = _make_outside_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([outside_file])

    assert findings == []


def test_directory_input_recurses(tmp_path: Path) -> None:
    """When a directory is passed, the analyzer recurses to find phase-2-refine files."""
    content = (
        '# Refine\n'
        'Edit("marketplace/foo.md")\n'
    )
    _make_refine_file(tmp_path, content, filename='SKILL.md')

    # pass the parent directory instead of the file
    findings = analyze_phase2_refine_contract([tmp_path])

    assert len(findings) == 1
    assert findings[0]['details']['tool'] == 'Edit'


def test_suggested_fix_present_in_finding(tmp_path: Path) -> None:
    """Every finding includes a suggested_fix remediation hint."""
    content = (
        '# Refine\n'
        'Write("build.gradle")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert len(findings) == 1
    assert 'suggested_fix' in findings[0]['details']
    assert '.plan/local/' in findings[0]['details']['suggested_fix']


def test_finding_shape_contract(tmp_path: Path) -> None:
    """Every finding must expose exactly the documented top-level + details keys.

    The migrated ``Finding`` record emits the common fields
    (``type``/``file``/``line``/``severity``/``fixable``/``rule_id``/
    ``description``) at the top level and the three rule-specific keys
    (``tool``/``path``/``suggested_fix``) inside the nested ``details`` dict.
    """
    content = (
        '# Refine Step\n'
        '\n'
        'Edit("marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert len(findings) == 1
    finding = findings[0]
    expected_top_keys = {
        'type',
        'file',
        'line',
        'severity',
        'fixable',
        'rule_id',
        'description',
        'details',
    }
    assert set(finding.keys()) == expected_top_keys
    assert finding['type'] == RULE_ID
    assert finding['rule_id'] == RULE_ID
    assert finding['severity'] == 'error'
    assert finding['fixable'] is False
    assert isinstance(finding['description'], str)
    assert isinstance(finding['file'], str)
    assert isinstance(finding['line'], int)
    assert finding['line'] >= 1
    assert set(finding['details'].keys()) == {'tool', 'path', 'suggested_fix'}


def test_finding_is_byte_identical_to_pre_refactor_baseline(tmp_path: Path) -> None:
    """The emitted finding dict must be dict-equal to the pre-refactor baseline.

    Pre-refactor (git ``d428b164``) the typeless analyzer return was wrapped by
    the ``extract_issues_from_refine_contract_analysis`` normalization shim in
    ``_doctor_analysis.py``, which produced the FINAL plugin-doctor issue dict
    with ``type``/``severity``/``fixable``/``description`` added and the three
    rule-specific keys (``tool``/``path``/``suggested_fix``) nested under
    ``details``. The foundation work deleted that shim and migrated the analyzer
    onto the uniform ``Finding`` record. This test pins the FINAL emitted dict to
    the exact baseline shape (same key set AND values) so a future ``Finding``
    change cannot silently drift the refine-contract output.
    """
    content = (
        '# Refine Step\n'
        '\n'
        'Edit("marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    findings = analyze_phase2_refine_contract([file_path])

    assert len(findings) == 1
    path_ref = 'marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md'
    expected = {
        'type': 'refine-contract-violation',
        'rule_id': 'refine-contract-violation',
        'file': str(file_path),
        'line': 3,
        'severity': 'error',
        'fixable': False,
        'description': (
            'phase-2-refine workflow file invokes `Edit` against '
            f'a non-plan path `{path_ref}` — refine MUST write only '
            'inside `.plan/local/plans/{plan_id}/**` or '
            '`.plan/local/worktrees/{plan_id}/**` '
            '(refine-contract-violation)'
        ),
        'details': {
            'tool': 'Edit',
            'path': path_ref,
            'suggested_fix': (
                'route the operation through `manage-plan-documents` or restrict '
                'the path to `.plan/local/plans/{plan_id}/**` '
                f'(current: {path_ref!r})'
            ),
        },
    }
    assert findings[0] == expected
