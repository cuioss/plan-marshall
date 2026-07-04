# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for _analyze_sys_path_bootstrap.py.

Covers:
- ``sys.path.insert`` in a non-allowlisted skill script IS flagged
- ``sys.path.append`` is flagged the same way
- An allowlisted script path is exempt (any number of mutations)
- ``sys.path.insert`` appearing only inside a string/regex is NOT flagged (AST,
  not text matching)
- A clean script produces no findings
- Finding shape: all required fields present and correctly typed
- Real-tree guard: the shipped marketplace tree is clean, so the allowlist is in
  sync with reality
"""
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_aspb = _load_module('_analyze_sys_path_bootstrap', '_analyze_sys_path_bootstrap.py')
analyze_sys_path_bootstrap = _aspb.analyze_sys_path_bootstrap
RULE_ID = _aspb.RULE_ID
FINDING_TYPE = _aspb.FINDING_TYPE
_ALLOWLIST = _aspb._ALLOWLIST


def _make_script(tmp_path: Path, rel: str, content: str) -> Path:
    """Create a script at ``tmp_path/<rel>`` (rel is a bundles-relative path)."""
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


_NON_ALLOWLISTED = 'plan-marshall/skills/manage-widgets/scripts/manage-widgets.py'
# A real allowlist entry, recreated under the synthetic tree.
_ALLOWLISTED = 'plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'


class TestFlagsNonAllowlisted:
    def test_insert_is_flagged(self, tmp_path):
        _make_script(
            tmp_path,
            _NON_ALLOWLISTED,
            'import sys\nsys.path.insert(0, "x")\n',
        )
        findings = analyze_sys_path_bootstrap(tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert f['rule'] == 'analyze_sys_path_bootstrap'
        assert f['call'] == 'sys.path.insert'
        assert f['line'] == 2
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert f['file'].endswith('manage-widgets.py')

    def test_append_is_flagged(self, tmp_path):
        _make_script(
            tmp_path,
            _NON_ALLOWLISTED,
            'import sys\nsys.path.append("x")\n',
        )
        findings = analyze_sys_path_bootstrap(tmp_path)
        assert len(findings) == 1
        assert findings[0]['call'] == 'sys.path.append'

    def test_multiple_mutations_each_flagged(self, tmp_path):
        _make_script(
            tmp_path,
            _NON_ALLOWLISTED,
            'import sys\nsys.path.insert(0, "a")\nsys.path.append("b")\n',
        )
        findings = analyze_sys_path_bootstrap(tmp_path)
        assert len(findings) == 2


class TestExemptAllowlisted:
    def test_allowlisted_script_is_exempt(self, tmp_path):
        _make_script(
            tmp_path,
            _ALLOWLISTED,
            'import sys\nsys.path.insert(0, "x")\nsys.path.append("y")\n',
        )
        assert analyze_sys_path_bootstrap(tmp_path) == []

    def test_allowlist_entry_matches_expected_shape(self):
        # Every allowlist entry is a bundles-relative POSIX path to a .py file.
        for rel in _ALLOWLIST:
            assert rel.endswith('.py')
            assert '/skills/' in rel
            assert '\\' not in rel


class TestAstNotText:
    def test_sys_path_inside_string_is_not_flagged(self, tmp_path):
        # The analyzer modules that DETECT this pattern carry the tokens in
        # regexes/strings; AST matching must not mistake those for real calls.
        _make_script(
            tmp_path,
            _NON_ALLOWLISTED,
            'import re\n'
            'PATTERN = re.compile(r"sys\\\\.path\\\\.insert")\n'
            'HELP = "call sys.path.append to bootstrap"\n',
        )
        assert analyze_sys_path_bootstrap(tmp_path) == []

    def test_clean_script_is_not_flagged(self, tmp_path):
        _make_script(
            tmp_path,
            _NON_ALLOWLISTED,
            'from file_ops import safe_main\n\n\ndef main():\n    return 0\n',
        )
        assert analyze_sys_path_bootstrap(tmp_path) == []

    def test_unrelated_insert_append_not_flagged(self, tmp_path):
        # ``foo.path.insert`` / ``mylist.append`` are not sys.path mutations.
        _make_script(
            tmp_path,
            _NON_ALLOWLISTED,
            'import sys\nitems = []\nitems.append(sys.argv)\nfoo = object()\n',
        )
        assert analyze_sys_path_bootstrap(tmp_path) == []


class TestRealTreeInSync:
    def test_shipped_marketplace_tree_is_clean(self):
        """The allowlist stays in sync: the real tree has zero violations."""
        findings = analyze_sys_path_bootstrap(MARKETPLACE_ROOT)
        assert findings == [], (
            'Non-allowlisted sys.path mutations found in the shipped tree:\n'
            + '\n'.join(f"{f['file']}:{f['line']} ({f['call']})" for f in findings)
        )
