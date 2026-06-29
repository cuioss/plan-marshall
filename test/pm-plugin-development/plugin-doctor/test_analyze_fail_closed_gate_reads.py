# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``fail-closed-gate-read`` and
``redundant-contract-typed-isinstance`` rule analyzer.

The analyzer detects two forward-enforcement anti-patterns via AST analysis:

- **Form A** (``fail-closed-gate-read``): a file read inside a read-only
  gate/boundary verb that is NOT enclosed in a ``try`` catching ``OSError``.
- **Form B** (``redundant-contract-typed-isinstance``): an ``isinstance(param,
  Cls)`` guard on a parameter already annotated with that concrete contract
  type.

Test layers:
  * Form A positive: unguarded read inside a gate-verb function, including a
    keyword-passed wrapped read (``json.loads(s=<read>)``).
  * Form A scope-locality: a nested non-gate helper's read is not attributed to
    the enclosing gate verb, and a nested gate verb's read is flagged exactly
    once (no over-traversal duplicate).
  * Form A negatives: OSError-wrapped read, non-gate-verb function, canonical
    ``file_ops.py`` (whitelist), the analyzer's own file (whitelist), and a
    bare ``json.loads`` over an in-memory string (not a file read).
  * Form B positive: redundant isinstance on a contract-typed param.
  * Form B negatives: isinstance on an ``Any``/union/``Optional`` param, and a
    type-mismatched guard.
  * Empty marketplace tree returns ``[]``.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_afcgr = _load_module('_analyze_fail_closed_gate_reads', '_analyze_fail_closed_gate_reads.py')

analyze_fail_closed_gate_reads = _afcgr.analyze_fail_closed_gate_reads
is_whitelisted = _afcgr.is_whitelisted
RULE_FAIL_CLOSED_GATE_READ = _afcgr.RULE_FAIL_CLOSED_GATE_READ
RULE_REDUNDANT_ISINSTANCE = _afcgr.RULE_REDUNDANT_ISINSTANCE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_marketplace(tmp_path: Path) -> Path:
    mp = tmp_path / 'marketplace'
    (mp / 'bundles').mkdir(parents=True)
    return mp


def _write_py(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _script(mp: Path, name: str) -> Path:
    return mp / 'bundles' / 'my-bundle' / 'skills' / 'my-skill' / 'scripts' / name


def _rules(findings: list[dict]) -> set[str]:
    return {f['rule_id'] for f in findings}


# ===========================================================================
# Form A — fail-closed-gate-read
# ===========================================================================


class TestFormAPositives:
    def test_unguarded_read_text_in_cmd_verb_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'gate.py'),
            'from pathlib import Path\n'
            '\n'
            'def cmd_run(args):\n'
            '    p = Path(args.path)\n'
            '    if p.exists():\n'
            '        content = p.read_text(encoding="utf-8")\n'
            '    return content\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ in _rules(findings)
        hit = next(f for f in findings if f['rule_id'] == RULE_FAIL_CLOSED_GATE_READ)
        assert hit['category'] == 'production_script'
        assert 'read_text' in hit['snippet']

    def test_unguarded_read_in_check_helper_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'consistency.py'),
            'from pathlib import Path\n'
            '\n'
            'def check_outline(plan_dir):\n'
            '    return Path(plan_dir, "outline.md").read_text()\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ in _rules(findings)

    def test_unguarded_parse_toon_over_read_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'manifest.py'),
            'from pathlib import Path\n'
            '\n'
            'def load_manifest(plan_dir):\n'
            '    return parse_toon(Path(plan_dir, "execution.toon").read_text())\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ in _rules(findings)

    def test_kwarg_form_wrapped_read_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # The read is passed as a KEYWORD argument to json.loads; the pre-fix
        # analyzer only inspected node.args[0] and missed the keyword form.
        _write_py(
            _script(mp, 'gate.py'),
            'import json\n'
            'from pathlib import Path\n'
            '\n'
            'def cmd_run(args):\n'
            '    return json.loads(s=Path(args.path).read_text())\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ in _rules(findings)


class TestFormANegatives:
    def test_oserror_wrapped_read_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'gate.py'),
            'from pathlib import Path\n'
            '\n'
            'def cmd_run(args):\n'
            '    p = Path(args.path)\n'
            '    try:\n'
            '        return p.read_text(encoding="utf-8")\n'
            '    except OSError:\n'
            '        return ""\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ not in _rules(findings)

    def test_exception_wrapped_read_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'gate.py'),
            'from pathlib import Path\n'
            '\n'
            'def load_status(plan_dir):\n'
            '    try:\n'
            '        return Path(plan_dir, "status.json").read_text()\n'
            '    except Exception:\n'
            '        return None\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ not in _rules(findings)

    def test_non_gate_verb_function_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # ``render_report`` is not a gate-verb name — an unguarded read here is
        # not in scope for the fail-closed rule.
        _write_py(
            _script(mp, 'render.py'),
            'from pathlib import Path\n'
            '\n'
            'def render_report(path):\n'
            '    return Path(path).read_text()\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ not in _rules(findings)

    def test_json_loads_over_inmemory_string_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # json.loads over an in-memory string cannot raise OSError, so it is not
        # a file read and must not be flagged.
        _write_py(
            _script(mp, 'gate.py'),
            'import json\n'
            '\n'
            'def cmd_run(raw):\n'
            '    return json.loads(raw)\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ not in _rules(findings)

    def test_canonical_file_ops_whitelisted(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        file_ops = mp / 'bundles' / 'plan-marshall' / 'skills' / 'tools-file-ops' / 'scripts' / 'file_ops.py'
        _write_py(
            file_ops,
            'from pathlib import Path\n'
            '\n'
            'def cmd_run(args):\n'
            '    return Path(args.path).read_text()\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert findings == []

    def test_analyzer_self_reference_whitelisted(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        analyzer = (
            mp / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor'
            / 'scripts' / '_analyze_fail_closed_gate_reads.py'
        )
        _write_py(
            analyzer,
            'from pathlib import Path\n'
            '\n'
            'def cmd_run(args):\n'
            '    return Path(args.path).read_text()\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert findings == []


class TestFormAScopeLocality:
    def test_nested_non_gate_helper_read_not_attributed_to_outer(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # cmd_outer reads nothing itself; its nested NON-gate helper does an
        # unguarded read. That read belongs to the inner scope (a non-gate verb,
        # never flagged), so the outer gate verb must NOT be flagged for it.
        _write_py(
            _script(mp, 'gate.py'),
            'from pathlib import Path\n'
            '\n'
            'def cmd_outer(args):\n'
            '    def render(path):\n'
            '        return Path(path).read_text()\n'
            '    return render(args.path)\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_FAIL_CLOSED_GATE_READ not in _rules(findings)

    def test_nested_gate_verb_read_flagged_once_not_duplicated(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # The outer gate verb reads fail-closed; a NESTED gate verb has its own
        # unguarded read. Pre-fix the outer scan over-traversed into the nested
        # verb and double-counted the read — it must be flagged exactly once, by
        # its own scope.
        _write_py(
            _script(mp, 'gate.py'),
            'from pathlib import Path\n'
            '\n'
            'def cmd_outer(args):\n'
            '    def check_inner(path):\n'
            '        return Path(path).read_text()\n'
            '    try:\n'
            '        own = Path(args.path).read_text()\n'
            '    except OSError:\n'
            '        own = ""\n'
            '    return own, check_inner(args.path)\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        fail_closed = [f for f in findings if f['rule_id'] == RULE_FAIL_CLOSED_GATE_READ]
        assert len(fail_closed) == 1
        assert 'read_text' in fail_closed[0]['snippet']


# ===========================================================================
# Form B — redundant-contract-typed-isinstance
# ===========================================================================


class TestFormBPositives:
    def test_redundant_isinstance_on_dict_param_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'guard.py'),
            'def merge(metadata: dict) -> dict:\n'
            '    if isinstance(metadata, dict):\n'
            '        return metadata\n'
            '    return {}\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_REDUNDANT_ISINSTANCE in _rules(findings)
        hit = next(f for f in findings if f['rule_id'] == RULE_REDUNDANT_ISINSTANCE)
        assert 'isinstance' in hit['snippet']

    def test_redundant_isinstance_on_subscripted_annotation_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'guard.py'),
            'from typing import Any\n'
            '\n'
            'def merge(metadata: dict[str, Any]) -> dict:\n'
            '    if not isinstance(metadata, dict):\n'
            '        return {}\n'
            '    return metadata\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_REDUNDANT_ISINSTANCE in _rules(findings)


class TestFormBNegatives:
    def test_isinstance_on_any_param_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'guard.py'),
            'from typing import Any\n'
            '\n'
            'def coerce(value: Any) -> dict:\n'
            '    if isinstance(value, dict):\n'
            '        return value\n'
            '    return {}\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_REDUNDANT_ISINSTANCE not in _rules(findings)

    def test_isinstance_on_union_param_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'guard.py'),
            'def coerce(value: dict | list) -> dict:\n'
            '    if isinstance(value, dict):\n'
            '        return value\n'
            '    return {}\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_REDUNDANT_ISINSTANCE not in _rules(findings)

    def test_isinstance_on_optional_param_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        _write_py(
            _script(mp, 'guard.py'),
            'from typing import Optional\n'
            '\n'
            'def coerce(value: Optional[dict]) -> dict:\n'
            '    if isinstance(value, dict):\n'
            '        return value\n'
            '    return {}\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_REDUNDANT_ISINSTANCE not in _rules(findings)

    def test_type_mismatched_guard_not_flagged(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # Param annotated dict but guard checks list — a genuine guard, not the
        # redundant-on-same-type anti-pattern.
        _write_py(
            _script(mp, 'guard.py'),
            'def pick(metadata: dict):\n'
            '    inner = metadata.get("items")\n'
            '    if isinstance(inner, list):\n'
            '        return inner\n'
            '    return []\n',
        )
        findings = analyze_fail_closed_gate_reads(mp)
        assert RULE_REDUNDANT_ISINSTANCE not in _rules(findings)


# ===========================================================================
# Whitelist + empty-tree
# ===========================================================================


class TestWhitelistAndEmpty:
    def test_is_whitelisted_self_and_file_ops(self) -> None:
        assert is_whitelisted(
            Path(
                '/x/marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_fail_closed_gate_reads.py'
            )
        )
        assert is_whitelisted(Path('/x/tools-file-ops/scripts/file_ops.py'))
        assert not is_whitelisted(Path('/x/scripts/other.py'))
        # Suffix-anchored, not unordered component containment: a bare filename
        # outside the canonical plugin-doctor location is NOT whitelisted.
        assert not is_whitelisted(Path('/x/scripts/_analyze_fail_closed_gate_reads.py'))

    def test_empty_tree_returns_empty(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        assert analyze_fail_closed_gate_reads(mp) == []
