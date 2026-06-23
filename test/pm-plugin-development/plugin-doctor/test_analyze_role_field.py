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
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


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

    def test_file_without_frontmatter_is_exempt(self, tmp_path: Path) -> None:
        """A markdown file with no leading ``---`` block is treated as a helper doc.

        The phase-5-execute standards/ directory hosts both step files
        (``quality_check.md``, ``build_verify.md``, ``coverage_check.md``)
        AND reference / narrative documents (``operations.md``, ``recovery.md``,
        ``sync-with-main.md``, ``test-scaffolding.md``, ``workflow.md``).
        Reference docs carry no YAML frontmatter at all and cannot structurally
        be step files (step-file identification requires
        ``name: default:…`` + ``description`` + ``order``). They are exempt
        from the role requirement.
        """
        scoped = _make_scoped_dir(tmp_path)
        _write(scoped / 'orphan.md', '# Just a heading, no frontmatter\n')
        findings = analyze_role_field(tmp_path)
        assert findings == []

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
# Canonical-verify exemption: the parameterized canonical-verify step derives
# its role dynamically at compose time and is exempt from the static role:
# requirement. Every other (legacy-style) role-less step file still fires.
# ===========================================================================


class TestCanonicalVerifyExemption:
    """The ``default:verify`` / ``default:verify:`` step is exempt from role:."""

    def test_canonical_verify_step_without_role_produces_no_finding(
        self, tmp_path: Path
    ) -> None:
        """The bare ``name: default:verify`` step carries no static role: and is exempt.

        This mirrors the on-disk
        ``phase-5-execute/standards/canonical_verify.md`` frontmatter:
        ``name: default:verify`` + ``description`` + ``order`` and NO
        ``role:`` field. The role is derived dynamically from the trailing
        canonical segment at compose time, so the static requirement does not
        apply.
        """
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'canonical_verify.md',
            '---\n'
            'name: default:verify\n'
            'description: Parameterized canonical-verify step\n'
            'order: 10\n'
            '---\n'
            '\n'
            '# Canonical Verify\n',
        )
        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_non_string_name_does_not_crash(self, tmp_path: Path) -> None:
        """A malformed frontmatter with a non-string ``name`` (YAML int/null) must NOT
        raise AttributeError — both the step-file and canonical-verify predicates
        type-guard the value before calling string methods (Gemini review finding e4c9ce).
        """
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'malformed.md',
            '---\n'
            'name: 123\n'
            'description: Malformed name field\n'
            'order: 10\n'
            '---\n'
            '\n'
            '# Malformed\n',
        )
        # A non-string name is simply not a default: step — must not raise.
        findings = analyze_role_field(tmp_path)
        assert isinstance(findings, list)

    def test_canonical_verify_prefixed_step_id_without_role_produces_no_finding(
        self, tmp_path: Path
    ) -> None:
        """A ``default:verify:{canonical}`` step ID is also exempt from role:."""
        scoped = _make_scoped_dir(tmp_path)
        _write(
            scoped / 'verify_quality_gate.md',
            '---\n'
            'name: default:verify:quality-gate\n'
            'description: Canonical-verify step for quality-gate\n'
            'order: 11\n'
            '---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert findings == []

    def test_legacy_role_less_step_still_fires_alongside_exempt_canonical_verify(
        self, tmp_path: Path
    ) -> None:
        """The exemption is scoped: a legacy role-less step file still fires.

        With both an exempt canonical-verify step and a legacy-style role-less
        step in the same directory, exactly one finding is emitted — for the
        legacy step, not the canonical-verify step.
        """
        scoped = _make_scoped_dir(tmp_path)
        # Exempt — canonical-verify step, no role:.
        _write(
            scoped / 'canonical_verify.md',
            '---\n'
            'name: default:verify\n'
            'description: Parameterized canonical-verify step\n'
            'order: 10\n'
            '---\n',
        )
        # Legacy-style role-less step — must still fire.
        legacy = _write(
            scoped / 'quality_check.md',
            '---\n'
            'name: default:quality_check\n'
            'description: Run quality-gate build command\n'
            'order: 20\n'
            '---\n',
        )
        findings = analyze_role_field(tmp_path)
        assert len(findings) == 1
        assert findings[0]['file'] == str(legacy)
        assert findings[0]['snippet'] == 'quality_check'


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
        _write(sibling / 'push.md', '---\nname: push\n---\n')

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
