# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``plan-path-in-scripts`` rule analyzer.

The analyzer detects drift from the canonical ``tools-file-ops:file_ops``
path helpers via AST analysis.  Three forms are detected:

- **Form A** (literal bypass): an ``ast.Constant`` string node whose value
  contains ``.plan/plans/`` (without ``/local/``).
- **Form B** (parent-walking re-derivation): a ``Path(__file__).parent…``
  or ``os.path.dirname(__file__)`` chain joined against a ``.plan``-domain
  subdirectory name (``plans``, ``lessons-learned``, ``logs``,
  ``archived-plans``, ``workspace``).
- **Form C** (resolver bypass): a working-tree-binding consumer that
  re-derives a worktree path by hand instead of routing through
  ``file_ops.resolve_plan_context``.

Exemptions asserted not-flagged:
  * ``sys.path.insert`` / ``sys.path.append`` bootstrap chains (form B).
  * ``file_ops.py`` (the canonical source — whitelist entry).
  * ``manage-status.py`` (the canonical ``get-worktree-path`` producer —
    whitelist entry, form C).
  * The named baseline straggler set (form C only).

Test layers:
  * End-to-end scan distinguishing a production hit from a whitelisted hit.
  * ``_classify`` returns ``production_script`` for code-literal hits and
    ``test_assertion`` for hits in test directories.
  * Whitelist excludes the analyzer's self-referential occurrence AND
    ``file_ops.py``.
  * Empty marketplace tree returns ``[]``.
  * ``_scan_file`` emits one finding per code-literal occurrence (multi-hit).
  * ``.plan/plans/`` inside a triple-quoted docstring produces zero findings.
  * Form A no-regression: ``.plan/plans/`` (without ``/local/``) still flagged;
    ``.plan/local/plans/`` is NOT flagged.
  * Form B literal bypass detected.
  * Form B parent-walking re-derivation detected.
  * ``sys.path.insert`` bootstrap exemption NOT flagged.
  * ``file_ops.py`` canonical-source exemption NOT flagged.
  * Form C: a bypassing consumer flagged, a compliant one not, a baseline
    member suppressed, and the docstring/prose exemption honoured.
  * Form C anti-vacuity, anchored to the REAL marketplace tree rather than a
    fixture, so the guard cannot pass vacuously against live data.
"""

import ast
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_appis = _load_module(
    '_analyze_plan_path_in_scripts', '_analyze_plan_path_in_scripts.py'
)

analyze_plan_path_in_scripts = _appis.analyze_plan_path_in_scripts
is_whitelisted = _appis.is_whitelisted
_classify = _appis._classify
_scan_file = _appis._scan_file
RULE_ID = _appis.RULE_ID
_PLAN_DOMAIN_DIRS = _appis._PLAN_DOMAIN_DIRS

# Form C surface.
derive_working_tree_binding_population = _appis.derive_working_tree_binding_population
find_resolver_bypasses = _appis.find_resolver_bypasses
routes_through_resolver = _appis.routes_through_resolver
collect_bypass_signals = _appis.collect_bypass_signals
binding_arms = _appis.binding_arms
baseline_stragglers = _appis.baseline_stragglers
skill_key = _appis.skill_key

# ``MARKETPLACE_ROOT`` is the bundles root; the analyzer joins ``bundles/``
# itself, so the real-tree assertions anchor on its parent.
REAL_MARKETPLACE = MARKETPLACE_ROOT.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_marketplace(tmp_path: Path) -> Path:
    """Create ``marketplace/bundles/`` skeleton. Returns marketplace root."""
    mp = tmp_path / 'marketplace'
    (mp / 'bundles').mkdir(parents=True)
    return mp


def _write_py(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


# ===========================================================================
# Fixture a: end-to-end — one production hit + one whitelisted hit
# ===========================================================================


class TestEndToEndScan:
    """End-to-end scan distinguishes a production hit from a whitelisted hit."""

    def test_production_hit_emitted_whitelisted_skipped(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)

        # Production hit: a real .plan/plans/ literal in a production script.
        prod_py = (
            mp
            / 'bundles'
            / 'my-bundle'
            / 'skills'
            / 'my-skill'
            / 'scripts'
            / 'do_work.py'
        )
        _write_py(
            prod_py,
            '# Production script\nplan_dir = ".plan/plans/" + plan_id\n',
        )

        # Whitelisted: the analyzer's own self-referential occurrence.
        whitelisted_py = (
            mp
            / 'bundles'
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'scripts'
            / '_analyze_plan_path_in_scripts.py'
        )
        _write_py(
            whitelisted_py,
            '# Self-referential analyzer\n_MARKER = ".plan/plans/"\n',
        )

        findings = analyze_plan_path_in_scripts(mp)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['category'] == 'production_script'
        assert str(prod_py) == f['file']
        assert '.plan/plans/' in f['snippet']


# ===========================================================================
# Fixture b: _classify behaviour — production_script vs test_assertion
# ===========================================================================


class TestClassify:
    """``_classify`` distinguishes production scripts from test files."""

    def test_production_script_classification(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'do_work.py'
        )
        assert _classify(path) == 'production_script'

    def test_test_directory_classified_as_test(self, tmp_path: Path) -> None:
        path = tmp_path / 'test' / 'plan-marshall' / 'foo' / 'test_bar.py'
        assert _classify(path) == 'test_assertion'

    def test_tests_directory_classified_as_test(self, tmp_path: Path) -> None:
        path = tmp_path / 'tests' / 'foo' / 'test_bar.py'
        assert _classify(path) == 'test_assertion'

    def test_test_prefix_filename_classified_as_test(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'test_runner.py'
        )
        assert _classify(path) == 'test_assertion'

    def test_test_suffix_filename_classified_as_test(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'runner_test.py'
        )
        assert _classify(path) == 'test_assertion'


# ===========================================================================
# Fixture c: whitelist correctness — self-referential file excluded
# ===========================================================================


class TestWhitelist:
    """The whitelist excludes the analyzer's own self-referential occurrence."""

    def test_self_file_whitelisted(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'scripts'
            / '_analyze_plan_path_in_scripts.py'
        )
        assert is_whitelisted(path)

    def test_arbitrary_other_path_not_whitelisted(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'do_work.py'
        )
        assert not is_whitelisted(path)

    def test_similar_name_but_different_filename_not_whitelisted(
        self, tmp_path: Path
    ) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / '_analyze_plan_path_in_scripts_helper.py'
        )
        assert not is_whitelisted(path)


# ===========================================================================
# Fixture d: empty marketplace tree returns []
# ===========================================================================


class TestEmptyMarketplace:
    """Empty marketplace tree returns no findings."""

    def test_empty_bundles_directory(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_nonexistent_marketplace_root(self, tmp_path: Path) -> None:
        mp = tmp_path / 'does-not-exist'
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_bundles_without_marker(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / 'clean.py'
        _write_py(py, '# Nothing of interest\ndef do_work():\n    return 42\n')
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []


# ===========================================================================
# Fixture e: _scan_file emits one finding per code-literal occurrence
# ===========================================================================


class TestMultiHitInSingleFile:
    """``_scan_file`` emits a separate finding per code-literal occurrence."""

    def test_multiple_code_literal_occurrences(self, tmp_path: Path) -> None:
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'multi.py'
        )
        _write_py(
            py,
            '# Two code-literal hits\n'
            'a = ".plan/plans/" + plan_id\n'
            'b = ".plan/plans/" + other_id\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 2
        # Hits land on the two distinct lines (lines 2 and 3 of the file).
        line_numbers = sorted(f['line'] for f in findings)
        assert line_numbers == [2, 3]
        for f in findings:
            assert f['rule_id'] == RULE_ID
            assert f['category'] == 'production_script'
            assert '.plan/plans/' in f['snippet']


# ===========================================================================
# Fixture f: docstring-only occurrence produces zero findings
# ===========================================================================


class TestDocstringSkip:
    """``.plan/plans/`` inside a triple-quoted docstring produces zero findings."""

    def test_docstring_only_occurrence_skipped(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'docstring_only.py'
        )
        # Triple-quoted docstring contains the marker; no code-literal hit.
        _write_py(
            py,
            '"""Module docstring.\n\nExample: .plan/plans/{plan_id} is the legacy form.\n"""\n\n'
            'def do_work():\n    return 42\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_single_quote_triple_docstring_skipped(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'single_quote_docstring.py'
        )
        _write_py(
            py,
            "'''Module docstring.\n\n.plan/plans/ inside single-quote triple block.\n'''\n\n"
            'def do_work():\n    return 42\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_mixed_docstring_and_code_literal(self, tmp_path: Path) -> None:
        """Docstring hit is skipped but the code-literal hit is reported."""
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'mixed.py'
        )
        _write_py(
            py,
            '"""Doc: .plan/plans/{id} legacy form."""\n\n'
            'plan_dir = ".plan/plans/" + plan_id\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert len(findings) == 1
        assert findings[0]['category'] == 'production_script'
        # Line 3 holds the code-literal hit (line 1 is the docstring).
        assert findings[0]['line'] == 3


# ===========================================================================
# Fixture g: Form A no-regression — .plan/plans/ (without /local/) still
# flagged; .plan/local/plans/ (canonical form) is NOT flagged.
# ===========================================================================


class TestFormANoRegression:
    """No-regression: original .plan/plans/ literal detection still fires."""

    def test_plan_plans_without_local_flagged(self, tmp_path: Path) -> None:
        """The drifted .plan/plans/ form is still flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(py, 'plan_dir = ".plan/plans/" + plan_id\n')
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert '.plan/plans/' in findings[0]['snippet']

    def test_plan_local_plans_not_flagged(self, tmp_path: Path) -> None:
        """The canonical .plan/local/plans/ form is NOT flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(py, 'plan_dir = ".plan/local/plans/" + plan_id\n')
        findings = _scan_file(py)
        assert findings == []


# ===========================================================================
# Fixture h: Form B — parent-walking re-derivation detected
# ===========================================================================


class TestFormBParentWalking:
    """Form B: Path(__file__).parent chain joined to a .plan-domain dir."""

    def test_path_file_parent_plans_flagged(self, tmp_path: Path) -> None:
        """Path(__file__).parent / "plans" is form-B drift and must be flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'PLAN_DIR = Path(__file__).parent / "plans"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['line'] == 2

    def test_os_path_dirname_plans_flagged(self, tmp_path: Path) -> None:
        """os.path.dirname(__file__) joined to a .plan-domain dir is form-B drift."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'import os\n'
            'import os.path\n'
            'PLAN_DIR = os.path.join(os.path.dirname(__file__), "plans")\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['line'] == 3

    def test_nested_parent_lessons_flagged(self, tmp_path: Path) -> None:
        """Multi-level parent chain joined to lessons-learned is flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'LESSONS = Path(__file__).parent.parent / "lessons-learned"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['line'] == 2

    def test_parent_chain_logs_domain_flagged(self, tmp_path: Path) -> None:
        """Parent chain joined to 'logs' (a .plan-domain dir) is flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'LOG_DIR = Path(__file__).parent / "logs"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1

    def test_parent_chain_non_plan_domain_not_flagged(self, tmp_path: Path) -> None:
        """Parent chain joined to a non-.plan-domain dir is NOT flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'DATA_DIR = Path(__file__).parent / "data"\n',
        )
        findings = _scan_file(py)
        assert findings == []

    def test_plan_domain_dirs_constant_imported(self) -> None:
        """Verify the expected .plan-domain dirs are present in the constant."""
        assert 'plans' in _PLAN_DOMAIN_DIRS
        assert 'lessons-learned' in _PLAN_DOMAIN_DIRS
        assert 'logs' in _PLAN_DOMAIN_DIRS
        assert 'archived-plans' in _PLAN_DOMAIN_DIRS
        assert 'workspace' in _PLAN_DOMAIN_DIRS


# ===========================================================================
# Fixture i: sys.path.insert exemption — bootstrap chains NOT flagged
# ===========================================================================


class TestSysPathInsertExemption:
    """sys.path.insert / sys.path.append bootstrap chains are NOT flagged."""

    def test_sys_path_insert_with_plans_domain_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """sys.path.insert(0, Path(__file__).parent / "plans") is a bootstrap
        idiom and must NOT produce a form-B finding.
        """
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'import sys\n'
            'from pathlib import Path\n'
            'sys.path.insert(0, str(Path(__file__).parent / "plans"))\n',
        )
        findings = _scan_file(py)
        assert findings == [], (
            'sys.path.insert bootstrap must not be flagged as form-B drift'
        )

    def test_sys_path_append_exemption(self, tmp_path: Path) -> None:
        """sys.path.append(Path(__file__).parent / "logs") is also exempt."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'import sys\n'
            'from pathlib import Path\n'
            'sys.path.append(str(Path(__file__).parent / "logs"))\n',
        )
        findings = _scan_file(py)
        assert findings == [], (
            'sys.path.append bootstrap must not be flagged as form-B drift'
        )

    def test_non_sys_path_same_pattern_flagged(self, tmp_path: Path) -> None:
        """The same parent-chain pattern outside a sys.path call IS flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'MY_DIR = Path(__file__).parent / "plans"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1, (
            'parent chain outside sys.path call must be flagged as form-B drift'
        )


# ===========================================================================
# Fixture j: file_ops.py canonical-source exemption
# ===========================================================================


class TestFileOpsExemption:
    """file_ops.py (tools-file-ops bundle) is whitelisted — never flagged."""

    def test_file_ops_path_whitelisted(self, tmp_path: Path) -> None:
        """The path tools-file-ops/.../file_ops.py is whitelisted."""
        path = (
            tmp_path
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py'
        )
        assert is_whitelisted(path)

    def test_file_ops_with_plan_plans_literal_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """A file_ops.py containing .plan/plans/ is silently skipped."""
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py'
        )
        _write_py(py, 'canonical = ".plan/plans/" + plan_id\n')
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == [], (
            'file_ops.py must be whitelisted and produce no findings'
        )

    def test_file_ops_with_parent_chain_not_flagged(self, tmp_path: Path) -> None:
        """file_ops.py containing a parent-walking chain is silently skipped."""
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            '_BASE = Path(__file__).parent / "plans"\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == [], (
            'file_ops.py parent-chain must be whitelisted and produce no findings'
        )


# ===========================================================================
# Form C fixtures — resolver bypass
# ===========================================================================
#
# Every fixture below is a controlled pair or triple: the fixtures differ in
# exactly the property under test, so a passing assertion pins that property
# rather than an incidental difference.

# A working-tree-binding consumer that re-derives the worktree by shelling out
# to the command the resolver owns.
_BYPASSER_SHELL_OUT = '''"""Re-derives the worktree by shelling out."""

import subprocess


def _resolve_worktree_path(plan_id):
    result = subprocess.run(
        ['python3', '.plan/execute-script.py', 'b:s:x', 'get-worktree-path'],
        capture_output=True,
    )
    return result.stdout


def build(parser):
    parser.add_argument('--project-dir', help='project directory')
'''

# The same consumer, re-deriving via a status-metadata read instead.
_BYPASSER_METADATA_READ = '''"""Re-derives the worktree by reading status metadata."""


def _resolve_worktree_path(status):
    metadata = status.get('metadata', {})
    return metadata.get('worktree_path')


def build(parser):
    parser.add_argument('--project-dir', help='project directory')
'''

# Byte-for-byte the same PRIVATE HELPER NAME as the bypassers, but the body
# delegates to the resolver. This is the controlled negative that proves the
# verdict is body-based and not name-based.
_COMPLIANT_ADAPTER = '''"""A CLI argument adapter that delegates to the resolver."""

from file_ops import resolve_plan_context


def _resolve_worktree_path(plan_id, project_dir):
    if project_dir:
        return project_dir
    return resolve_plan_context(plan_id).worktree_path


def build(parser):
    parser.add_argument('--project-dir', help='project directory')
'''

# Binds no working tree at all — declares only --plan-id. Out of the
# population, which is what distinguishes the corrected Bucket-B derivation
# from the rejected --plan-id argparse walk.
_PLAN_ID_ONLY = '''"""A plan-scoped consumer that binds no working tree."""


def build(parser):
    parser.add_argument('--plan-id', help='plan id')
'''

# Names both the flag and the command in PROSE only.
_PROSE_ONLY = '''"""Documents get-worktree-path and --project-dir without using either.

The resolver shells out to get-worktree-path. Callers may pass --project-dir
to override the working tree.
"""


def noop():
    return None
'''


def _write_consumer(mp: Path, skill: str, filename: str, body: str) -> Path:
    """Materialize one bundle script under ``mp`` at a real skill-shaped path."""
    return _write_py(mp / 'bundles' / 'b1' / 'skills' / skill / 'scripts' / filename, body)


class TestFormCPopulationDerivation:
    """The population is derived from the working-tree-binding arms."""

    def test_project_dir_flag_arm(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _BYPASSER_SHELL_OUT)
        assert 'project_dir_flag' in binding_arms(ast.parse(py.read_text(encoding='utf-8')))

    def test_worktree_path_shell_out_arm(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _BYPASSER_SHELL_OUT)
        arms = binding_arms(ast.parse(py.read_text(encoding='utf-8')))
        assert 'worktree_path_shell_out' in arms

    def test_private_rederiver_arm(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _BYPASSER_METADATA_READ)
        assert 'private_rederiver' in binding_arms(ast.parse(py.read_text(encoding='utf-8')))

    def test_resolver_ref_arm_keeps_migrated_consumer_in_population(
        self, tmp_path: Path
    ) -> None:
        """The migration-stable arm: a migrated consumer stays in the population.

        Without this arm a migration that replaces a hand-rolled binding with a
        resolver call would EVICT the consumer from the population, so the guard
        would stop watching exactly the files a migration just fixed.
        """
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _COMPLIANT_ADAPTER)
        arms = binding_arms(ast.parse(py.read_text(encoding='utf-8')))
        assert 'resolver_ref' in arms
        population = derive_working_tree_binding_population(mp)
        assert py in population

    def test_plan_id_only_consumer_is_out_of_population(self, tmp_path: Path) -> None:
        """A --plan-id declaration alone does NOT put a script in the population.

        This pins the corrected Bucket-B derivation against the rejected
        --plan-id argparse-declaration walk.
        """
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _PLAN_ID_ONLY)
        assert binding_arms(ast.parse(py.read_text(encoding='utf-8'))) == []
        assert derive_working_tree_binding_population(mp) == []

    def test_prose_only_mention_is_out_of_population(self, tmp_path: Path) -> None:
        """Naming the flag / command in a docstring does not bind a working tree."""
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _PROSE_ONLY)
        assert binding_arms(ast.parse(py.read_text(encoding='utf-8'))) == []
        assert derive_working_tree_binding_population(mp) == []

    def test_whitelisted_file_excluded_from_population(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            mp
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py',
            _BYPASSER_SHELL_OUT,
        )
        assert derive_working_tree_binding_population(mp) == []

    def test_empty_tree_population_is_empty(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        assert derive_working_tree_binding_population(mp) == []


class TestFormCVerdict:
    """The verdict is body-based: a signal without a resolver reference."""

    def test_shell_out_bypasser_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _BYPASSER_SHELL_OUT)
        findings = find_resolver_bypasses(mp, apply_baseline=False)
        assert len(findings) == 1
        assert findings[0]['file'] == str(py)
        assert findings[0]['form'] == 'C'
        assert findings[0]['signal'] == 'worktree_path_shell_out'
        assert findings[0]['rule_id'] == RULE_ID

    def test_metadata_read_bypasser_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_consumer(mp, 's1', 'a.py', _BYPASSER_METADATA_READ)
        findings = find_resolver_bypasses(mp, apply_baseline=False)
        assert len(findings) == 1
        assert findings[0]['signal'] == 'worktree_path_metadata_read'

    def test_metadata_subscript_read_flagged(self, tmp_path: Path) -> None:
        """A subscript read is the same re-derivation as a ``.get`` read."""
        mp = _make_marketplace(tmp_path)
        _write_consumer(
            mp,
            's1',
            'a.py',
            'def _resolve_worktree_path(metadata):\n'
            "    return metadata['worktree_path']\n",
        )
        findings = find_resolver_bypasses(mp, apply_baseline=False)
        assert len(findings) == 1
        assert findings[0]['signal'] == 'worktree_path_metadata_read'

    def test_compliant_adapter_with_identical_helper_name_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """The load-bearing negative control: same helper NAME, delegating BODY.

        ``_BYPASSER_SHELL_OUT`` and ``_COMPLIANT_ADAPTER`` both define
        ``_resolve_worktree_path`` and both declare ``--project-dir``. They
        differ ONLY in what the body does, so a name-pattern detector would flag
        both. Form C must flag neither on name alone.
        """
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _COMPLIANT_ADAPTER)
        tree = ast.parse(py.read_text(encoding='utf-8'))
        assert 'private_rederiver' in binding_arms(tree)
        assert routes_through_resolver(tree)
        assert find_resolver_bypasses(mp, apply_baseline=False) == []

    def test_prose_mention_of_command_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_consumer(mp, 's1', 'a.py', _PROSE_ONLY)
        assert find_resolver_bypasses(mp, apply_baseline=False) == []

    def test_signals_carry_line_numbers(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _write_consumer(mp, 's1', 'a.py', _BYPASSER_METADATA_READ)
        signals = collect_bypass_signals(ast.parse(py.read_text(encoding='utf-8')))
        assert signals
        assert all(line > 0 for line, _signal in signals)

    def test_form_c_findings_reach_the_rule_entry_point(self, tmp_path: Path) -> None:
        """A form-C bypass surfaces through the rule's public entry point.

        Form C is population-derived rather than per-file, so it runs once over
        the tree AFTER the per-file scan. This pins that it is actually reached
        from ``analyze_plan_path_in_scripts`` — the function the quality-gate
        dispatch calls — and not only from ``find_resolver_bypasses`` directly.
        """
        mp = _make_marketplace(tmp_path)
        _write_consumer(mp, 's1', 'a.py', _BYPASSER_SHELL_OUT)
        findings = analyze_plan_path_in_scripts(mp)
        assert [f.get('form') for f in findings] == ['C']


class TestFormCBaselineSuppression:
    """The baseline straggler set suppresses a bypasser, and only a member."""

    def test_baseline_member_suppressed(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        member = sorted(baseline_stragglers())[0]
        skill, filename = member.split('/', 1)
        _write_consumer(mp, skill, filename, _BYPASSER_SHELL_OUT)

        assert find_resolver_bypasses(mp, apply_baseline=False), (
            'the fixture must bypass before the baseline is applied'
        )
        assert find_resolver_bypasses(mp, apply_baseline=True) == [], (
            'a baseline member must be suppressed'
        )

    def test_non_member_at_same_filename_not_suppressed(self, tmp_path: Path) -> None:
        """Suppression keys on ``{skill}/{filename}``, not the filename alone."""
        mp = _make_marketplace(tmp_path)
        member = sorted(baseline_stragglers())[0]
        _skill, filename = member.split('/', 1)
        _write_consumer(mp, 'some-other-skill', filename, _BYPASSER_SHELL_OUT)
        assert len(find_resolver_bypasses(mp, apply_baseline=True)) == 1

    def test_skill_key_derivation(self, tmp_path: Path) -> None:
        path = tmp_path / 'bundles' / 'b' / 'skills' / 'my-skill' / 'scripts' / 'x.py'
        assert skill_key(path) == 'my-skill/x.py'

    def test_skill_key_degrades_to_filename_without_skills_segment(
        self, tmp_path: Path
    ) -> None:
        assert skill_key(tmp_path / 'flat' / 'x.py') == 'x.py'


class TestFormCAntiVacuityAgainstRealTree:
    """Anti-vacuity properties asserted against the REAL marketplace tree.

    These are anchored to live data rather than a fixture on purpose: every
    fixture-based assertion above passes just as well against a detector that
    can never fire on the real corpus. A guard that is green because it watches
    nothing is the failure mode these four properties exist to rule out.
    """

    def test_property_1_derived_population_is_non_empty(self) -> None:
        population = derive_working_tree_binding_population(REAL_MARKETPLACE)
        assert population, (
            'the working-tree-binding population derived from the real tree is '
            'empty — the form-C guard would watch nothing'
        )

    def test_property_2_baseline_is_strict_subset_of_population(self) -> None:
        """Every baseline member must be a derived population member, and the
        population must be strictly larger — the guard must watch more than its
        own exemptions.
        """
        population_keys = {
            skill_key(p) for p in derive_working_tree_binding_population(REAL_MARKETPLACE)
        }
        baseline = baseline_stragglers()
        orphans = sorted(baseline - population_keys)
        assert not orphans, (
            f'baseline entries outside the derived population: {orphans} — the '
            'exemption set and the population disagree on what binds a worktree'
        )
        assert baseline < population_keys, (
            'the baseline is not a STRICT subset — the guard watches nothing '
            'beyond its own exemptions'
        )

    def test_property_3_no_phantom_baseline_entries(self) -> None:
        """Every baseline entry resolves to a file that still exists.

        A renamed or deleted file would leave a phantom exemption behind, which
        silently un-guards its successor while still reading as a deliberate,
        documented deferral.
        """
        phantoms = []
        for member in sorted(baseline_stragglers()):
            skill, filename = member.split('/', 1)
            # Resolved straight off disk — deliberately NOT via the derived
            # population, so this stays independent of property 2's orphan check.
            matches = list(MARKETPLACE_ROOT.glob(f'*/skills/{skill}/scripts/{filename}'))
            if not any(m.is_file() for m in matches):
                phantoms.append(member)
        assert not phantoms, (
            f'phantom baseline entries (no such file in the tree): {phantoms}'
        )

    def test_property_4_raw_bypassing_set_is_non_empty(self) -> None:
        """Before the baseline is subtracted, the guard flags something real.

        This is the anti-vacuity proof proper: it asserts the detector's
        predicate actually fires against the live corpus. If this ever goes
        empty, every remaining form-C assertion is vacuous and the baseline set
        should be retired rather than kept as decoration.
        """
        raw = find_resolver_bypasses(REAL_MARKETPLACE, apply_baseline=False)
        assert raw, (
            'the form-C detector flags nothing against the real tree even '
            'before exemptions — the predicate never fires'
        )
        assert all(f['form'] == 'C' for f in raw)
        assert all(
            f['signal'] in ('worktree_path_shell_out', 'worktree_path_metadata_read')
            for f in raw
        )

    def test_real_tree_is_clean_after_baseline(self) -> None:
        """With exemptions applied the real tree carries no form-C finding.

        Paired with property 4 this is the meaningful green: the guard fires on
        the corpus and every firing is a named, enumerated deferral.
        """
        remaining = find_resolver_bypasses(REAL_MARKETPLACE, apply_baseline=True)
        assert remaining == [], (
            'un-baselined resolver bypasses in the real tree: '
            f'{sorted(skill_key(Path(f["file"])) for f in remaining)}'
        )

    def test_whole_rule_is_clean_against_real_tree(self) -> None:
        """All three forms together report nothing against the real tree."""
        assert analyze_plan_path_in_scripts(REAL_MARKETPLACE) == []

    def test_canonical_producer_is_whitelisted(self) -> None:
        """manage-status.py owns ``get-worktree-path`` and must stay exempt.

        Routing the producer through the resolver would close a cycle, since the
        resolver shells out to this very command.
        """
        producer = (
            MARKETPLACE_ROOT
            / 'plan-marshall'
            / 'skills'
            / 'manage-status'
            / 'scripts'
            / 'manage-status.py'
        )
        assert producer.is_file(), 'the canonical producer moved — revisit the whitelist'
        assert is_whitelisted(producer)

    def test_private_name_helpers_survive_as_delegating_adapters(self) -> None:
        """The body-based property, asserted against the real tree.

        Real helpers keep ``_resolve_worktree*`` / ``_resolve_project_dir*``
        names as CLI argument adapters. A name-pattern detector would flag
        precisely those escape hatches, so this asserts at least one such helper
        exists in the population AND is correctly classified as delegating.
        """
        adapters = []
        for path in derive_working_tree_binding_population(REAL_MARKETPLACE):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            if 'private_rederiver' in binding_arms(tree) and routes_through_resolver(tree):
                adapters.append(skill_key(path))
        assert adapters, (
            'no delegating private-name adapter found in the population — the '
            'body-based-vs-name-based distinction is untested against live data'
        )
