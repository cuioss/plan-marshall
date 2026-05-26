# ruff: noqa: I001, E402
"""Tests for the ``phase-5-step-missing-role-field`` rule analyzer.

The analyzer scans
``marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/*.md``
and emits a ``missing_role_field`` finding for any file whose YAML
frontmatter lacks a non-empty ``role:`` declaration. The ``role:`` field is
consumed by the ``manage-execution-manifest`` composer's structural role-
based intersection in Rows 2/3/4/5 of the decision matrix — see
``manage-execution-manifest/standards/decision-rules.md`` § Role-Field
Intersection.

Test layers:
  * Fixture with ``role:`` present → no finding (positive case)
  * Fixture missing ``role:`` → one finding (negative case)
  * Fixture with empty ``role:`` value → one finding (boundary case)
  * Files outside the scoped directory are NOT scanned (path-scope guard)
  * Real marketplace tree post-deliverable-1 produces zero findings
    (invariant test that doubles as a drift sentinel)
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


_arf = _load_module('_analyze_role_field', '_analyze_role_field.py')

analyze_role_field = _arf.analyze_role_field
RULE_ID = _arf.RULE_ID
FINDING_TYPE = _arf.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scoped_dir(tmp_path: Path) -> Path:
    """Create the scoped directory structure under a synthetic marketplace root.

    Returns the scoped standards directory; the marketplace root is its parent
    chain ancestor (used as the ``marketplace_root`` arg to the analyzer).
    """
    scoped = (
        tmp_path
        / 'plan-marshall'
        / 'skills'
        / 'phase-5-execute'
        / 'standards'
    )
    scoped.mkdir(parents=True)
    return scoped


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding='utf-8')
    return path


# ===========================================================================
# Positive case: role: field present → no finding
# ===========================================================================


class TestRoleFieldPresent:
    """Files declaring a non-empty ``role:`` field produce no findings."""

    def test_role_field_present_produces_no_finding(self, tmp_path: Path) -> None:
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'quality_check.md',
            '---\n'
            'name: default:quality_check\n'
            'description: Run quality-gate build command\n'
            'order: 10\n'
            'role: quality-gate\n'
            '---\n'
            '\n'
            '# Quality Check\n',
        )
        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_role_field_with_double_quoted_value_accepted(self, tmp_path: Path) -> None:
        """Quoted YAML scalars are accepted (``role: "quality-gate"``)."""
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'quality_check.md',
            '---\n'
            'name: default:quality_check\n'
            'role: "quality-gate"\n'
            '---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_role_field_with_single_quoted_value_accepted(self, tmp_path: Path) -> None:
        """Single-quoted YAML scalars are accepted (``role: 'module-tests'``)."""
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'build_verify.md',
            '---\n'
            'name: default:build_verify\n'
            'description: Run the full test suite\n'
            'order: 20\n'
            "role: 'module-tests'\n"
            '---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_helper_doc_without_default_name_prefix_is_not_required_to_declare_role(
        self, tmp_path: Path
    ) -> None:
        """Helper / narrative docs in the standards/ directory are not step files.

        The phase-5-execute standards/ directory hosts both step files
        (``quality_check.md`` etc) AND helper / narrative documents
        (``operations.md``, ``recovery.md``, ``workflow.md``,
        ``sync-with-main.md``). The role-field requirement applies only to
        step files — files whose frontmatter declares ``name: default:…``
        together with ``description:`` and ``order:``. A helper doc without
        those keys is treated as compliant.
        """
        scoped = _make_scoped_dir(tmp_path)
        # Helper doc — no `name: default:…`, no `order:`. Must NOT be flagged.
        _write(
            scoped / 'operations.md',
            '---\n'
            'description: Operational patterns for phase-5-execute\n'
            '---\n'
            '\n'
            '# Operations\n',
        )
        findings = analyze_role_field(tmp_path)
        assert findings == []


# ===========================================================================
# Negative case: role: field missing → one finding
# ===========================================================================


class TestRoleFieldMissing:
    """Files lacking the ``role:`` key produce exactly one finding each."""

    def test_missing_role_field_produces_one_finding(self, tmp_path: Path) -> None:
        scoped = _make_scoped_dir(tmp_path)
        path = _write(
            scoped / 'quality_check.md',
            '---\n'
            'name: default:quality_check\n'
            'description: Run quality-gate build command\n'
            'order: 10\n'
            '---\n'
            '\n'
            '# Quality Check\n',
        )
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == FINDING_TYPE
        assert finding['severity'] == 'error'
        assert finding['file'] == str(path)
        assert finding['snippet'] == 'quality_check'

    def test_file_without_frontmatter_produces_finding(self, tmp_path: Path) -> None:
        """A markdown file with no leading ``---`` block is treated as missing role.

        Note: only files identifiable as step files (via the ``name:
        default:…`` + ``description`` + ``order:`` triple) are subject to
        the requirement; a bare markdown file with no frontmatter cannot
        be classified as a step file but is still flagged here because the
        absence of any frontmatter at all is itself a structural defect for
        the step-files directory.
        """
        scoped = _make_scoped_dir(tmp_path)
        path = _write(scoped / 'orphan.md', '# Just a heading, no frontmatter\n')
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 1
        assert findings[0]['file'] == str(path)

    def test_multiple_missing_files_produce_one_finding_each(self, tmp_path: Path) -> None:
        scoped = _make_scoped_dir(tmp_path)
        # All three are step files (name: default:…, description, order).
        _write(
            scoped / 'a.md',
            '---\nname: default:a\ndescription: a step\norder: 10\n---\n',
        )
        _write(
            scoped / 'b.md',
            '---\nname: default:b\ndescription: b step\norder: 20\n---\n',
        )
        _write(
            scoped / 'c.md',
            '---\nname: default:c\ndescription: c step\norder: 30\nrole: quality-gate\n---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 2
        snippets = {f['snippet'] for f in findings}
        assert snippets == {'a', 'b'}


# ===========================================================================
# Boundary case: empty role: value → one finding
# ===========================================================================


class TestRoleFieldEmpty:
    """A ``role:`` key with an empty value is treated as missing."""

    def test_empty_role_value_produces_finding(self, tmp_path: Path) -> None:
        scoped = _make_scoped_dir(tmp_path)
        path = _write(
            scoped / 'broken.md',
            '---\n'
            'name: default:broken\n'
            'description: A broken step\n'
            'order: 99\n'
            'role:\n'  # bare key with empty value
            '---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 1
        assert findings[0]['file'] == str(path)

    def test_whitespace_only_role_value_produces_finding(self, tmp_path: Path) -> None:
        scoped = _make_scoped_dir(tmp_path)
        path = _write(
            scoped / 'broken.md',
            '---\n'
            'name: default:broken\n'
            'description: A broken step\n'
            'order: 99\n'
            'role:    \n'  # whitespace-only after the colon
            '---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 1
        assert findings[0]['file'] == str(path)

    def test_empty_quoted_role_value_produces_finding(self, tmp_path: Path) -> None:
        """``role: ""`` and ``role: ''`` are both empty after quote-stripping."""
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'a.md',
            '---\nname: default:a\ndescription: a\norder: 10\nrole: ""\n---\n',
        )
        _write(
            scoped / 'b.md',
            '---\nname: default:b\ndescription: b\norder: 20\nrole: \'\'\n---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 2


# ===========================================================================
# Path-scope guard: files outside the scoped directory are not scanned
# ===========================================================================


class TestPathScope:
    """Files outside phase-5-execute/standards/ are ignored even when role: is absent."""

    def test_file_under_different_skill_is_not_scanned(self, tmp_path: Path) -> None:
        """A markdown file in a sibling skill's standards directory is silently skipped."""
        # Scoped (in-scope) file with role present so it doesn't false-positive.
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'quality_check.md',
            '---\nname: default:quality_check\nrole: quality-gate\n---\n',
        )

        # Out-of-scope file in a sibling skill without role: — must NOT be flagged.
        sibling = (
            tmp_path
            / 'plan-marshall'
            / 'skills'
            / 'phase-6-finalize'
            / 'standards'
        )
        sibling.mkdir(parents=True)
        _write(sibling / 'commit-push.md', '---\nname: commit-push\n---\n')

        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_file_in_other_bundle_is_not_scanned(self, tmp_path: Path) -> None:
        """A markdown file in a different bundle is silently skipped."""
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'quality_check.md',
            '---\nname: default:quality_check\nrole: quality-gate\n---\n',
        )

        other = (
            tmp_path
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'standards'
        )
        other.mkdir(parents=True)
        _write(other / 'rule-catalog.md', '---\nname: rule-catalog\n---\n')

        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_missing_scoped_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """When phase-5-execute/standards/ does not exist, return empty findings."""
        # No directory created at all.
        findings = analyze_role_field(tmp_path)
        assert findings == []


# ===========================================================================
# Real marketplace invariant: after deliverable 1, zero MISSING_ROLE_FIELD
# ===========================================================================


class TestRealMarketplaceInvariant:
    """The real marketplace tree must produce zero findings after deliverable 1."""

    def test_real_marketplace_has_zero_findings(self) -> None:
        """Post-deliverable-1, every phase-5-execute step file declares role:.

        This test doubles as a drift sentinel: any future contributor who
        adds a new ``*.md`` to ``phase-5-execute/standards/`` without
        declaring a ``role:`` frontmatter field will trip this assertion.
        Removing ``role:`` from any existing step file triggers the same
        failure.
        """
        marketplace_root = PROJECT_ROOT / 'marketplace' / 'bundles'
        findings = analyze_role_field(marketplace_root)
        assert findings == [], (
            f'Expected zero MISSING_ROLE_FIELD findings on the real marketplace; '
            f'got {len(findings)}: {[f["file"] for f in findings]!r}'
        )
