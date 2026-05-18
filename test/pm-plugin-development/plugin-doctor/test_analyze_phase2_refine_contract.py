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

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


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
    # Arrange
    content = (
        '# Phase 2 Refine\n'
        '\n'
        'This file describes the refine phase but does not invoke any tools.\n'
        'It mentions Read operations only, and lists script calls.\n'
        '\n'
        '`python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read --plan-id X`\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert findings == []


def test_edit_to_marketplace_emits_finding(tmp_path: Path) -> None:
    """An Edit call targeting marketplace/ must produce a finding."""
    # Arrange
    content = (
        '# Refine Step\n'
        '\n'
        'Update the standards file:\n'
        '\n'
        'Edit("marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['tool'] == 'Edit'
    assert 'marketplace' in finding['path']
    assert finding['line'] == 5


def test_write_to_src_emits_finding(tmp_path: Path) -> None:
    """A Write call targeting src/ must produce a finding."""
    # Arrange
    content = (
        '# Refine\n'
        '\n'
        'Write(file_path="src/main/foo.py", content="...")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert len(findings) == 1
    assert findings[0]['tool'] == 'Write'
    assert findings[0]['path'] == 'src/main/foo.py'


def test_plan_local_path_is_allowed(tmp_path: Path) -> None:
    """An Edit targeting .plan/local/ must produce no finding."""
    # Arrange
    content = (
        '# Refine\n'
        '\n'
        'Edit(".plan/local/plans/my-plan/request.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert findings == []


def test_worktree_prefix_uppercase_placeholder_is_allowed(tmp_path: Path) -> None:
    """{WORKTREE}/.plan/local/... is the worktree-substituted form — allowed."""
    # Arrange
    content = (
        '# Refine\n'
        '\n'
        'Edit("{WORKTREE}/.plan/local/plans/my-plan/clarifications.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert findings == []


def test_worktree_path_placeholder_is_allowed(tmp_path: Path) -> None:
    """{worktree_path}/.plan/local/... is also a valid substitution form."""
    # Arrange
    content = (
        '# Refine\n'
        '\n'
        'Write(file_path="{worktree_path}/.plan/local/plans/p/request.md", content="...")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert findings == []


def test_read_calls_are_ignored(tmp_path: Path) -> None:
    """Read is allowed against any path — must produce no finding."""
    # Arrange
    content = (
        '# Refine\n'
        '\n'
        'Read("marketplace/bundles/some/file.md")\n'
        'Read("src/main/java/Foo.java")\n'
        'Read("/etc/passwd")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert findings == []


def test_rules_filter_excludes_rule(tmp_path: Path) -> None:
    """When the rule is not in rules_filter, the analyzer returns no findings."""
    # Arrange
    content = (
        '# Refine\n'
        'Edit("marketplace/foo.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act — supply a filter that excludes this rule
    findings = analyze_phase2_refine_contract([file_path], rules_filter={'other-rule'})

    # Assert
    assert findings == []


def test_rules_filter_includes_rule(tmp_path: Path) -> None:
    """When the rule IS in rules_filter, findings are emitted normally."""
    # Arrange
    content = (
        '# Refine\n'
        'Edit("marketplace/foo.md")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract(
        [file_path],
        rules_filter={RULE_ID, 'other-rule'},
    )

    # Assert
    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID


def test_file_outside_phase2_refine_is_out_of_scope(tmp_path: Path) -> None:
    """Files outside phase-2-refine/ are not scanned even when passed directly."""
    # Arrange
    content = (
        '# Phase 5 Execute\n'
        'Edit("marketplace/foo.md")\n'
    )
    outside_file = _make_outside_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([outside_file])

    # Assert
    assert findings == []


def test_directory_input_recurses(tmp_path: Path) -> None:
    """When a directory is passed, the analyzer recurses to find phase-2-refine files."""
    # Arrange
    content = (
        '# Refine\n'
        'Edit("marketplace/foo.md")\n'
    )
    _make_refine_file(tmp_path, content, filename='SKILL.md')

    # Act — pass the parent directory instead of the file
    findings = analyze_phase2_refine_contract([tmp_path])

    # Assert
    assert len(findings) == 1
    assert findings[0]['tool'] == 'Edit'


def test_suggested_fix_present_in_finding(tmp_path: Path) -> None:
    """Every finding includes a suggested_fix remediation hint."""
    # Arrange
    content = (
        '# Refine\n'
        'Write("build.gradle")\n'
    )
    file_path = _make_refine_file(tmp_path, content)

    # Act
    findings = analyze_phase2_refine_contract([file_path])

    # Assert
    assert len(findings) == 1
    assert 'suggested_fix' in findings[0]
    assert '.plan/local/' in findings[0]['suggested_fix']
