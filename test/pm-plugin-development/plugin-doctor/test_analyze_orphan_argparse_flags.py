# ruff: noqa: I001, E402
"""Tests for the ``orphan-argparse-flag`` rule analyzer.

The analyzer detects argparse flags declared in a manage-* script but
never read in the corresponding subcommand handler body.

Test layers:
  a. Flag declared and read via ``args.{dest}`` — no finding.
  b. Flag declared but never read — finding emitted.
  c. Flag read indirectly via ``vars(args)`` — no finding (conservative).
  d. Flag read indirectly via ``**vars(args)`` unpacking — no finding.
  e. Multiple flags: one read, one orphan — only orphan flagged.
  f. Unreadable/unparseable file — no crash.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_aoaf = _load_module('_analyze_orphan_argparse_flags', '_analyze_orphan_argparse_flags.py')

analyze_orphan_argparse_flags = _aoaf.analyze_orphan_argparse_flags
RULE_ID = _aoaf.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_script(tmp_path: Path, content: str) -> Path:
    path = tmp_path / 'manage_test.py'
    path.write_text(content, encoding='utf-8')
    return path


# ===========================================================================
# Fixture a: flag declared and read — no finding
# ===========================================================================


class TestFlagDeclaredAndRead:
    def test_flag_read_directly(self, tmp_path: Path) -> None:
        """Flag declared and accessed via args.{dest} → no finding."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_run = subparsers.add_parser('run', allow_abbrev=False)\n"
            "p_run.add_argument('--output', default='out.txt')\n"
            'p_run.set_defaults(func=cmd_run)\n'
            '\n'
            'def cmd_run(args):\n'
            '    path = args.output\n'
            '    print(path)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert findings == []

    def test_flag_with_hyphen_dest(self, tmp_path: Path) -> None:
        """Flag --dry-run normalises to dest dry_run and is correctly tracked."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_deploy = subparsers.add_parser('deploy', allow_abbrev=False)\n"
            "p_deploy.add_argument('--dry-run', action='store_true')\n"
            'p_deploy.set_defaults(func=cmd_deploy)\n'
            '\n'
            'def cmd_deploy(args):\n'
            '    if args.dry_run:\n'
            '        return\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert findings == []


# ===========================================================================
# Fixture b: flag declared but never read — finding emitted
# ===========================================================================


class TestFlagNeverRead:
    def test_orphan_flag_emits_finding(self, tmp_path: Path) -> None:
        """Flag declared but not read in the handler body → one finding."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_run = subparsers.add_parser('run', allow_abbrev=False)\n"
            "p_run.add_argument('--verbose', action='store_true')\n"
            'p_run.set_defaults(func=cmd_run)\n'
            '\n'
            'def cmd_run(args):\n'
            '    print("running")\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['flag_name'] == '--verbose'
        assert f['subcommand'] == 'run'
        assert isinstance(f['line'], int)
        assert f['line'] >= 1
        assert 'file' in f

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Each finding carries required keys."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_x = subparsers.add_parser('x', allow_abbrev=False)\n"
            "p_x.add_argument('--orphan-flag')\n"
            'p_x.set_defaults(func=cmd_x)\n'
            '\n'
            'def cmd_x(args):\n'
            '    pass\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert findings
        f = findings[0]
        for key in ('rule_id', 'file', 'line', 'flag_name', 'subcommand'):
            assert key in f, f'Missing key: {key}'


# ===========================================================================
# Fixture c: vars(args) — no finding (conservative)
# ===========================================================================


class TestVarsArgsConservative:
    def test_vars_args_suppresses_finding(self, tmp_path: Path) -> None:
        """Handler using ``vars(args)`` → analyzer cannot prove orphaning → no finding."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_go = subparsers.add_parser('go', allow_abbrev=False)\n"
            "p_go.add_argument('--mode')\n"
            'p_go.set_defaults(func=cmd_go)\n'
            '\n'
            'def cmd_go(args):\n'
            '    kwargs = vars(args)\n'
            '    _run(**kwargs)\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert findings == []


# ===========================================================================
# Fixture d: **vars(args) unpacking — no finding
# ===========================================================================


class TestDoubleStarVarsArgs:
    def test_double_star_suppresses_finding(self, tmp_path: Path) -> None:
        """Handler using ``**vars(args)`` → conservative, no finding."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_build = subparsers.add_parser('build', allow_abbrev=False)\n"
            "p_build.add_argument('--target')\n"
            'p_build.set_defaults(func=cmd_build)\n'
            '\n'
            'def cmd_build(args):\n'
            '    do_build(**vars(args))\n'
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert findings == []


# ===========================================================================
# Fixture e: mixed — one read, one orphan
# ===========================================================================


class TestMixedFlags:
    def test_only_orphan_flagged(self, tmp_path: Path) -> None:
        """When one flag is read and one is not, only the orphan is reported."""
        src = (
            'import argparse\n'
            'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
            'subparsers = parser.add_subparsers()\n'
            "p_run = subparsers.add_parser('run', allow_abbrev=False)\n"
            "p_run.add_argument('--output')\n"
            "p_run.add_argument('--verbose', action='store_true')\n"
            'p_run.set_defaults(func=cmd_run)\n'
            '\n'
            'def cmd_run(args):\n'
            '    print(args.output)\n'  # reads output, ignores verbose
        )
        script = _write_script(tmp_path, src)
        findings = analyze_orphan_argparse_flags(script)
        assert len(findings) == 1
        assert findings[0]['flag_name'] == '--verbose'


# ===========================================================================
# Fixture f: unreadable / unparseable — no crash
# ===========================================================================


class TestRobustness:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'nonexistent.py'
        findings = analyze_orphan_argparse_flags(path)
        assert findings == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'broken.py'
        path.write_text('def x(\n', encoding='utf-8')
        findings = analyze_orphan_argparse_flags(path)
        assert findings == []

    def test_no_argparse_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'simple.py'
        path.write_text('print("hello")\n', encoding='utf-8')
        findings = analyze_orphan_argparse_flags(path)
        assert findings == []
