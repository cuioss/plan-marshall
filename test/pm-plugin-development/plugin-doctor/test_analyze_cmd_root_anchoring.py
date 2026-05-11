# ruff: noqa: I001, E402
"""Tests for the ``cmd-root-anchoring-missing`` rule analyzer.

The analyzer checks that every ``cmd_*`` function in a dispatcher script:
  1. Calls ``find_marketplace_root(...)`` (the prelude), and
  2. Has a corresponding argparse subparser with a ``--marketplace-root`` flag.

Test layers:
  a. Compliant ``cmd_*`` (both prelude + flag present) — no finding.
  b. Missing prelude — finding with ``missing: prelude``.
  c. Missing ``--marketplace-root`` flag — finding with ``missing: flag``.
  d. Missing both — finding with ``missing: both``.
  e. Non-dispatcher script (no ``set_defaults(func=...)`` → out of scope) — no finding.
  f. Robustness: unreadable/unparseable file — no crash.
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


_acra = _load_module('_analyze_cmd_root_anchoring', '_analyze_cmd_root_anchoring.py')

analyze_cmd_root_anchoring = _acra.analyze_cmd_root_anchoring
RULE_ID = _acra.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_script(tmp_path: Path, content: str) -> Path:
    path = tmp_path / 'dispatcher.py'
    path.write_text(content, encoding='utf-8')
    return path


def _compliant_dispatcher() -> str:
    """Minimal compliant dispatcher source."""
    return (
        'import argparse\n'
        'from _doctor_shared import find_marketplace_root\n'
        '\n'
        'def cmd_scan(args):\n'
        '    marketplace_root = find_marketplace_root(args.marketplace_root)\n'
        '    project_root = marketplace_root.parent\n'
        '    return {}\n'
        '\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        '    subs = parser.add_subparsers()\n'
        "    p_scan = subs.add_parser('scan', allow_abbrev=False)\n"
        "    p_scan.add_argument('--marketplace-root', dest='marketplace_root')\n"
        '    p_scan.set_defaults(func=cmd_scan)\n'
    )


# ===========================================================================
# Fixture a: compliant cmd_* — no finding
# ===========================================================================


class TestCompliantCmdFunction:
    def test_compliant_dispatcher_no_finding(self, tmp_path: Path) -> None:
        """A cmd_* with both prelude and flag produces no finding."""
        script = _write_script(tmp_path, _compliant_dispatcher())
        findings = analyze_cmd_root_anchoring(script)
        assert findings == []

    def test_prelude_tolerance_for_intermediate_stmts(self, tmp_path: Path) -> None:
        """Intermediate assignments between function start and prelude are tolerated."""
        src = (
            'import argparse\n'
            'from _doctor_shared import find_marketplace_root\n'
            '\n'
            'def cmd_run(args):\n'
            '    # This is a comment\n'
            '    local_var = 42\n'
            '    marketplace_root = find_marketplace_root(args.marketplace_root)\n'
            '    return {}\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            '    subs = parser.add_subparsers()\n'
            "    p_run = subs.add_parser('run', allow_abbrev=False)\n"
            "    p_run.add_argument('--marketplace-root', dest='marketplace_root')\n"
            '    p_run.set_defaults(func=cmd_run)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert findings == []


# ===========================================================================
# Fixture b: missing prelude
# ===========================================================================


class TestMissingPrelude:
    def test_missing_prelude_finding(self, tmp_path: Path) -> None:
        """cmd_* without find_marketplace_root call emits finding with missing: prelude."""
        src = (
            'import argparse\n'
            '\n'
            'def cmd_analyze(args):\n'
            '    # No find_marketplace_root call\n'
            '    return {}\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            '    subs = parser.add_subparsers()\n'
            "    p_an = subs.add_parser('analyze', allow_abbrev=False)\n"
            "    p_an.add_argument('--marketplace-root', dest='marketplace_root')\n"
            '    p_an.set_defaults(func=cmd_analyze)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['missing'] == 'prelude'
        assert f['function_name'] == 'cmd_analyze'


# ===========================================================================
# Fixture c: missing --marketplace-root flag
# ===========================================================================


class TestMissingFlag:
    def test_missing_flag_finding(self, tmp_path: Path) -> None:
        """cmd_* with prelude but no --marketplace-root flag emits finding with missing: flag."""
        src = (
            'import argparse\n'
            'from _doctor_shared import find_marketplace_root\n'
            '\n'
            'def cmd_fix(args):\n'
            '    marketplace_root = find_marketplace_root(None)\n'
            '    return {}\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            '    subs = parser.add_subparsers()\n'
            "    p_fix = subs.add_parser('fix', allow_abbrev=False)\n"
            "    p_fix.add_argument('--dry-run', action='store_true')\n"
            '    p_fix.set_defaults(func=cmd_fix)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert len(findings) == 1
        f = findings[0]
        assert f['missing'] == 'flag'
        assert f['function_name'] == 'cmd_fix'


# ===========================================================================
# Fixture d: missing both
# ===========================================================================


class TestMissingBoth:
    def test_missing_both_finding(self, tmp_path: Path) -> None:
        """cmd_* missing both prelude and flag emits finding with missing: both."""
        src = (
            'import argparse\n'
            '\n'
            'def cmd_report(args):\n'
            '    return {}\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            '    subs = parser.add_subparsers()\n'
            "    p_rep = subs.add_parser('report', allow_abbrev=False)\n"
            "    p_rep.add_argument('--output')\n"
            '    p_rep.set_defaults(func=cmd_report)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert len(findings) == 1
        f = findings[0]
        assert f['missing'] == 'both'
        assert f['function_name'] == 'cmd_report'

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Each finding carries required keys."""
        src = (
            'import argparse\n'
            '\n'
            'def cmd_x(args):\n'
            '    pass\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            '    subs = parser.add_subparsers()\n'
            "    p_x = subs.add_parser('x', allow_abbrev=False)\n"
            '    p_x.set_defaults(func=cmd_x)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert findings
        f = findings[0]
        for key in ('rule_id', 'file', 'line', 'function_name', 'missing'):
            assert key in f


# ===========================================================================
# Fixture e: non-dispatcher script — out of scope, no finding
# ===========================================================================


class TestNonDispatcherScript:
    def test_script_without_set_defaults_not_flagged(self, tmp_path: Path) -> None:
        """A script with cmd_* but no set_defaults is out of scope."""
        src = (
            'import argparse\n'
            '\n'
            'def cmd_helper(args):\n'
            '    return {}\n'
            '\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert findings == []

    def test_utility_script_no_finding(self, tmp_path: Path) -> None:
        """A plain utility script with no cmd_* or set_defaults produces no finding."""
        src = 'def helper():\n    return 42\n'
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert findings == []


# ===========================================================================
# Fixture f: robustness
# ===========================================================================


class TestRobustness:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'nonexistent.py'
        findings = analyze_cmd_root_anchoring(path)
        assert findings == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'broken.py'
        path.write_text('def x(\n', encoding='utf-8')
        findings = analyze_cmd_root_anchoring(path)
        assert findings == []

    def test_multiple_compliant_functions(self, tmp_path: Path) -> None:
        """Multiple compliant cmd_* functions in the same file → no findings."""
        src = (
            'import argparse\n'
            'from _doctor_shared import find_marketplace_root\n'
            '\n'
            'def cmd_a(args):\n'
            '    marketplace_root = find_marketplace_root(args.marketplace_root)\n'
            '    return {}\n'
            '\n'
            'def cmd_b(args):\n'
            '    marketplace_root = find_marketplace_root(args.marketplace_root)\n'
            '    return {}\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            '    subs = parser.add_subparsers()\n'
            "    p_a = subs.add_parser('a', allow_abbrev=False)\n"
            "    p_a.add_argument('--marketplace-root')\n"
            '    p_a.set_defaults(func=cmd_a)\n'
            "    p_b = subs.add_parser('b', allow_abbrev=False)\n"
            "    p_b.add_argument('--marketplace-root')\n"
            '    p_b.set_defaults(func=cmd_b)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_cmd_root_anchoring(script)
        assert findings == []
