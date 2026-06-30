# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``step-configurable-contract`` rule analyzer.

The analyzer (``scan_step_configurable_contract``) is a pure static scanner
that fires on a finalize-step body doc whose ``configurable:`` frontmatter
block is *present but malformed* and stays silent on every clean or ownerless
doc. It delegates the malformed-vs-valid decision to the central contract
parser (``extension-api/scripts/configurable_contract.py``) — the single source
of truth for the declaration schema — turning the parser's ``ValueError`` into
a plugin-doctor finding.

It walks two roots:

1. **Built-in finalize-step body docs** —
   ``marketplace_root/plan-marshall/skills/phase-6-finalize/{workflow,standards}/*.md``.

2. **Project-local finalize-step skills** —
   ``<repo>/.claude/skills/finalize-step-*/SKILL.md`` discovered by glob,
   resolved as ``marketplace_root.parent.parent / '.claude' / 'skills'``.

A finding is emitted only when a ``configurable:`` block IS present and fails
the contract parser. A doc with no ``configurable:`` block (ownerless) and a
doc whose block parses cleanly produce no finding.

Test layers:
  * (a) Malformed cases — each malformed-declaration class (missing key,
        missing default, missing description, empty description, wrong-typed
        key, wrong-typed description, duplicate key, empty block) fires the
        rule.
  * (b) Clean / ownerless — a well-formed block and a doc with no
        ``configurable:`` block both stay silent.
  * (c) Project-local — the ``.claude/skills/finalize-step-*`` tree is scanned
        (malformed fires, ownerless stays silent), and bundle + project-local
        findings combine.
  * (d) Finding shape — the finding carries the documented contract fields.
  * (e) Parser-unavailable — a synthetic tree with no contract parser is a
        no-op (empty result, no crash).
  * (f) doctor-marketplace integration — the analyzer is imported and invoked
        by ``doctor-marketplace.py`` and surfaces a ``rule_summaries`` entry.
  * (g) Real-marketplace-zero — the real bundles tree produces zero findings.
"""

import shutil
from pathlib import Path

import pytest
from conftest import MARKETPLACE_ROOT, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ascc = _load_module(
    '_analyze_step_configurable_contract',
    '_analyze_step_configurable_contract.py',
)

scan_step_configurable_contract = _ascc.scan_step_configurable_contract
RULE_ID = _ascc.RULE_ID
RULE_NAME = _ascc.RULE_NAME
FINDING_TYPE = _ascc.FINDING_TYPE


# The real contract parser the synthetic tree must carry so the analyzer's
# dynamic import (``_load_contract_parser``) succeeds. The parser imports
# ``marketplace_bundles`` / ``toon_parser`` from the test PYTHONPATH at module
# top, but neither is *called* during a ``parse_configurable(path)`` scan, so a
# verbatim copy into the synthetic tree resolves and validates identically.
_REAL_PARSER = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'extension-api'
    / 'scripts'
    / 'configurable_contract.py'
)


# ---------------------------------------------------------------------------
# Synthetic marketplace builders
# ---------------------------------------------------------------------------


def _bundles_root(tmp_path: Path, with_parser: bool = True) -> Path:
    """Build a synthetic marketplace bundles root.

    Creates ``{tmp_path}/marketplace/bundles`` and, when ``with_parser`` is
    True, copies the real contract parser into
    ``plan-marshall/skills/extension-api/scripts/configurable_contract.py`` so
    ``_load_contract_parser`` can import it. The two-levels-up resolution of
    ``.claude/skills`` lands on ``tmp_path``.

    Returns the bundles root to pass to the scanner.
    """
    bundles_root = tmp_path / 'marketplace' / 'bundles'
    bundles_root.mkdir(parents=True, exist_ok=True)
    if with_parser:
        ext_scripts = (
            bundles_root
            / 'plan-marshall'
            / 'skills'
            / 'extension-api'
            / 'scripts'
        )
        ext_scripts.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_REAL_PARSER, ext_scripts / 'configurable_contract.py')
    return bundles_root


def _write_builtin_doc(
    bundles_root: Path, content: str, subdir: str = 'workflow', name: str = 'sonar-roundtrip'
) -> Path:
    """Create a built-in phase-6-finalize body doc the scanner walks.

    Scope: ``plan-marshall/skills/phase-6-finalize/{workflow,standards}/*.md``.
    """
    doc_dir = (
        bundles_root
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
        / subdir
    )
    doc_dir.mkdir(parents=True, exist_ok=True)
    doc = doc_dir / f'{name}.md'
    doc.write_text(content, encoding='utf-8')
    return doc


def _write_project_doc(
    tmp_path: Path, content: str, name: str = 'finalize-step-deploy-target'
) -> Path:
    """Create a project-local ``.claude/skills/{name}/SKILL.md``.

    Two levels up from ``{tmp_path}/marketplace/bundles`` is ``tmp_path``, where
    ``.claude/skills`` is rooted.
    """
    skill_dir = tmp_path / '.claude' / 'skills' / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


def _frontmatter(configurable_block: str | None, *, with_fm: bool = True) -> str:
    """Compose a body doc with optional ``---``-fenced frontmatter.

    ``configurable_block`` is the YAML text placed inside the frontmatter (omit
    by passing ``None``). ``with_fm=False`` emits a doc with no frontmatter
    fence at all.
    """
    if not with_fm:
        return '# Step\n\nBody with no frontmatter.\n'
    fm_body = 'name: step\norder: 50\n'
    if configurable_block is not None:
        fm_body += configurable_block
    return f'---\n{fm_body}---\n\n# Step\n\nBody.\n'


# A well-formed configurable block (one valid entry).
_VALID_BLOCK = (
    'configurable:\n'
    '  - key: touched_file_cleanup\n'
    '    default: new_code_only\n'
    '    description: Which surface the success criterion covers.\n'
)


# ===========================================================================
# (a) Malformed cases — every malformed-declaration class fires the rule
# ===========================================================================


class TestMalformedFires:
    """Each malformed ``configurable:`` declaration class produces a finding."""

    @pytest.mark.parametrize(
        'block',
        [
            pytest.param(
                'configurable:\n'
                '  - default: foo\n'
                '    description: missing the key sub-field.\n',
                id='missing-key',
            ),
            pytest.param(
                'configurable:\n'
                '  - key: foo\n'
                '    description: missing the default sub-field.\n',
                id='missing-default',
            ),
            pytest.param(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n',
                id='missing-description',
            ),
            pytest.param(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: ""\n',
                id='empty-description',
            ),
            pytest.param(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: first.\n'
                '  - key: foo\n'
                '    default: baz\n'
                '    description: duplicate key.\n',
                id='duplicate-key',
            ),
            pytest.param(
                'configurable:\n',
                id='empty-block',
            ),
        ],
    )
    def test_malformed_block_triggers_finding(self, tmp_path: Path, block: str) -> None:
        bundles_root = _bundles_root(tmp_path)
        doc = _write_builtin_doc(bundles_root, _frontmatter(block))

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 1
        assert findings[0]['file'] == str(doc)
        assert findings[0]['rule_id'] == RULE_ID

    def test_wrong_typed_description_triggers_finding(self, tmp_path: Path) -> None:
        """A boolean ``description`` is wrong-typed and fires the rule."""
        bundles_root = _bundles_root(tmp_path)
        block = (
            'configurable:\n'
            '  - key: foo\n'
            '    default: bar\n'
            '    description: false\n'
        )
        _write_builtin_doc(bundles_root, _frontmatter(block))

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 1

    def test_no_frontmatter_with_configurable_is_ownerless(self, tmp_path: Path) -> None:
        """A doc with no frontmatter fence is ownerless (no block to validate)."""
        bundles_root = _bundles_root(tmp_path)
        _write_builtin_doc(bundles_root, _frontmatter(None, with_fm=False))

        findings = scan_step_configurable_contract(bundles_root)

        assert findings == []


# ===========================================================================
# (b) Clean / ownerless — well-formed block and no-block both stay silent
# ===========================================================================


class TestCleanAndOwnerless:
    """A valid block and an ownerless doc produce no finding."""

    def test_valid_block_is_clean(self, tmp_path: Path) -> None:
        bundles_root = _bundles_root(tmp_path)
        _write_builtin_doc(bundles_root, _frontmatter(_VALID_BLOCK))

        findings = scan_step_configurable_contract(bundles_root)

        assert findings == []

    def test_frontmatter_without_configurable_is_ownerless(self, tmp_path: Path) -> None:
        """Frontmatter present but no ``configurable:`` key → ownerless, skipped."""
        bundles_root = _bundles_root(tmp_path)
        _write_builtin_doc(bundles_root, _frontmatter(None))

        findings = scan_step_configurable_contract(bundles_root)

        assert findings == []

    def test_standards_subdir_is_scanned(self, tmp_path: Path) -> None:
        """A malformed block in ``standards/`` is scanned, not just ``workflow/``."""
        bundles_root = _bundles_root(tmp_path)
        block = (
            'configurable:\n'
            '  - key: foo\n'
            '    default: bar\n'  # missing description
        )
        _write_builtin_doc(
            bundles_root, _frontmatter(block), subdir='standards', name='branch-cleanup'
        )

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 1


# ===========================================================================
# (c) Project-local case — .claude/skills/finalize-step-*/SKILL.md
# ===========================================================================


class TestProjectLocal:
    """The project-local finalize-step tree is scanned identically."""

    def test_project_local_malformed_fires(self, tmp_path: Path) -> None:
        bundles_root = _bundles_root(tmp_path)
        block = (
            'configurable:\n'
            '  - key: foo\n'
            '    description: missing the default sub-field.\n'
        )
        md = _write_project_doc(tmp_path, _frontmatter(block))

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 1
        assert findings[0]['file'] == str(md)

    def test_project_local_ownerless_is_skipped(self, tmp_path: Path) -> None:
        bundles_root = _bundles_root(tmp_path)
        _write_project_doc(tmp_path, _frontmatter(None))

        findings = scan_step_configurable_contract(bundles_root)

        assert findings == []

    def test_project_local_valid_is_clean(self, tmp_path: Path) -> None:
        bundles_root = _bundles_root(tmp_path)
        _write_project_doc(tmp_path, _frontmatter(_VALID_BLOCK))

        findings = scan_step_configurable_contract(bundles_root)

        assert findings == []

    def test_builtin_and_project_findings_combine(self, tmp_path: Path) -> None:
        """Findings from the built-in tree and ``.claude/skills`` combine."""
        bundles_root = _bundles_root(tmp_path)
        builtin_block = 'configurable:\n  - key: a\n    default: 1\n'  # missing desc
        builtin = _write_builtin_doc(bundles_root, _frontmatter(builtin_block))
        project_block = 'configurable:\n  - default: 2\n    description: no key.\n'
        project = _write_project_doc(
            tmp_path, _frontmatter(project_block), name='finalize-step-plugin-doctor'
        )

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 2
        files = {f['file'] for f in findings}
        assert str(builtin) in files
        assert str(project) in files


# ===========================================================================
# (d) Finding shape
# ===========================================================================


class TestFindingShape:
    """The finding dict carries the documented contract fields."""

    def test_finding_shape(self, tmp_path: Path) -> None:
        bundles_root = _bundles_root(tmp_path)
        block = 'configurable:\n  - key: foo\n    default: bar\n'  # missing desc
        doc = _write_builtin_doc(bundles_root, _frontmatter(block))

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert f['rule'] == RULE_NAME
        assert f['file'] == str(doc)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert isinstance(f['message'], str) and f['message']
        assert 'parser_error' in f['details']
        assert isinstance(f['details']['parser_error'], str)

    def test_line_points_at_configurable_key(self, tmp_path: Path) -> None:
        """The reported line is the 1-based line of the ``configurable:`` key."""
        bundles_root = _bundles_root(tmp_path)
        # Frontmatter: line 1 '---', 2 'name', 3 'order', 4 'configurable:'.
        block = 'configurable:\n  - key: foo\n    default: bar\n'  # missing desc
        _write_builtin_doc(bundles_root, _frontmatter(block))

        findings = scan_step_configurable_contract(bundles_root)

        assert len(findings) == 1
        assert findings[0]['line'] == 4


# ===========================================================================
# (e) Parser-unavailable — no contract parser → no-op
# ===========================================================================


class TestParserUnavailable:
    """A synthetic tree with no contract parser is a silent no-op."""

    def test_missing_parser_returns_empty(self, tmp_path: Path) -> None:
        # with_parser=False: no extension-api parser is copied in.
        bundles_root = _bundles_root(tmp_path, with_parser=False)
        block = 'configurable:\n  - key: foo\n    default: bar\n'  # malformed
        _write_builtin_doc(bundles_root, _frontmatter(block))

        findings = scan_step_configurable_contract(bundles_root)

        assert findings == []


# ===========================================================================
# (f) doctor-marketplace integration wiring
# ===========================================================================


class _Args:
    """Minimal argparse-Namespace stand-in for ``cmd_quality_gate``.

    ``cmd_quality_gate`` reads ``marketplace_root`` (the marketplace root, parent
    of ``bundles/``) and ``paths`` (the optional --paths scope) off its ``args``.
    Both default to ``None`` here so the gate resolves the real marketplace tree
    script-relatively and runs whole-tree.
    """

    def __init__(self, marketplace_root: str | None = None, paths=None):
        self.marketplace_root = marketplace_root
        self.paths = paths


class TestDoctorMarketplaceWiring:
    """``doctor-marketplace.py`` imports and runs the analyzer in quality-gate."""

    def test_runner_imports_scanner(self) -> None:
        """The single-pass runner binds ``scan_step_configurable_contract``.

        The quality-gate dispatch is driven by
        ``_runner.RuleRunner.run_quality_gate``, so the scanner import lives on
        the runner module rather than the doctor-marketplace CLI orchestrator.
        """
        runner = _load_module('_runner', '_runner.py')
        assert hasattr(runner, 'scan_step_configurable_contract')
        assert (
            runner.scan_step_configurable_contract
            is scan_step_configurable_contract
        )

    def test_quality_gate_runs_the_rule(self) -> None:
        """``cmd_quality_gate`` includes the analyzer in its ``rules_run`` and
        the real tree is clean for it.

        Exercises the actual wiring path (the gate calls the analyzer and
        records its rule summary) against the real marketplace, which doubles as
        the gate-level zero-findings anchor for this rule.
        """
        if not _marketplace_available():
            pytest.skip('Real marketplace not available')

        doctor = _load_module('doctor_marketplace', 'doctor-marketplace.py')

        result = doctor.cmd_quality_gate(_Args())

        rules_run = {s['rule'] for s in result['rules_run']}
        assert 'scan_step_configurable_contract' in rules_run
        summary = next(
            s for s in result['rules_run'] if s['rule'] == 'scan_step_configurable_contract'
        )
        assert summary['findings'] == 0
        # No issue of this rule's finding type leaked into the gate result.
        types = {i.get('type') for i in result['issues']}
        assert FINDING_TYPE not in types


# ===========================================================================
# (g) Real-marketplace-zero anchor
# ===========================================================================


def _marketplace_available() -> bool:
    return MARKETPLACE_ROOT.is_dir() and any(MARKETPLACE_ROOT.iterdir())


def test_real_marketplace_tree_produces_zero_findings() -> None:
    """The real bundles tree has zero malformed ``configurable:`` declarations.

    Every param-owning finalize-step body doc — built-in and project-local —
    must declare a contract-valid ``configurable:`` block. A non-empty result
    means a real step's declaration drifted out of the D1 contract schema.
    """
    if not _marketplace_available():
        pytest.skip('Real marketplace not available')

    findings = scan_step_configurable_contract(MARKETPLACE_ROOT)

    assert findings == [], (
        f'Found {len(findings)} malformed step configurable declaration(s) in '
        f'the real marketplace tree: '
        f'{[(f["file"], f["details"].get("parser_error")) for f in findings]}. '
        f'Each finalize-step configurable block must satisfy the D1 contract '
        f'(every entry needs key, default, description).'
    )
