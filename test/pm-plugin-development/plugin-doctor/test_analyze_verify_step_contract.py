# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``verify-step-canonicals-required`` rule analyzer.

The analyzer walks every ``.md`` file under the marketplace bundles root, keeps
those whose ``implements:`` frontmatter names
``plan-marshall:extension-api/standards/ext-point-build-verify-step``, and flags
each implementor whose ``canonicals:`` frontmatter list is missing or empty
(lesson ``2026-06-25-08-001``).

Test layers:
  * Implementor with a non-empty ``canonicals:`` block sequence → no finding.
  * Implementor declaring the ext-point in block-sequence ``implements:`` form → recognized.
  * Implementor with a non-empty inline ``canonicals: [...]`` list → no finding.
  * Implementor with a missing ``canonicals:`` key → finding ("missing").
  * Implementor with ``canonicals: []`` → finding ("empty").
  * Non-implementor doc (other ext-point / no ``implements:``) with no canonicals → no finding.
  * Finding shape (rule_id / type / severity / line).
  * Absent tree → empty list.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_avsc = _load_module('_analyze_verify_step_contract', '_analyze_verify_step_contract.py')

analyze_verify_step_contract = _avsc.analyze_verify_step_contract
RULE_ID = _avsc.RULE_ID
FINDING_TYPE = _avsc.FINDING_TYPE

_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-build-verify-step'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, frontmatter: str) -> Path:
    path = tmp_path / 'plan-marshall' / 'skills' / 'phase-5-execute' / 'standards' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\n{frontmatter}---\n\n# Step\n', encoding='utf-8')
    return path


# ===========================================================================
# Compliant implementors → no finding
# ===========================================================================


def test_scalar_implements_with_block_canonicals_ok(tmp_path: Path) -> None:
    _write(
        tmp_path,
        'canonical_verify.md',
        f'implements: {_EXT_POINT}\nname: default:verify\ncanonicals:\n  - quality-gate\n  - module-tests\n',
    )
    assert analyze_verify_step_contract(tmp_path) == []


def test_block_sequence_implements_recognized(tmp_path: Path) -> None:
    fm = (
        'implements:\n'
        '  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow\n'
        f'  - {_EXT_POINT}\n'
        'canonicals:\n  - quality-gate\n'
    )
    _write(tmp_path, 'multi.md', fm)
    assert analyze_verify_step_contract(tmp_path) == []


def test_inline_canonicals_list_ok(tmp_path: Path) -> None:
    _write(
        tmp_path,
        'inline.md',
        f'implements: {_EXT_POINT}\ncanonicals: [quality-gate, module-tests]\n',
    )
    assert analyze_verify_step_contract(tmp_path) == []


# ===========================================================================
# Violating implementors → finding
# ===========================================================================


def test_missing_canonicals_flagged(tmp_path: Path) -> None:
    _write(tmp_path, 'nocanon.md', f'implements: {_EXT_POINT}\nname: default:verify\n')
    findings = analyze_verify_step_contract(tmp_path)
    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID
    assert 'missing required' in findings[0]['description']


def test_empty_inline_canonicals_flagged(tmp_path: Path) -> None:
    _write(tmp_path, 'emptycanon.md', f'implements: {_EXT_POINT}\ncanonicals: []\n')
    findings = analyze_verify_step_contract(tmp_path)
    assert len(findings) == 1
    assert 'empty' in findings[0]['description']


def test_empty_block_canonicals_flagged(tmp_path: Path) -> None:
    # canonicals: key present, immediately followed by another top-level key
    # (no list items) → empty.
    _write(tmp_path, 'emptyblock.md', f'implements: {_EXT_POINT}\ncanonicals:\nname: default:verify\n')
    findings = analyze_verify_step_contract(tmp_path)
    assert len(findings) == 1
    assert 'empty' in findings[0]['description']


# ===========================================================================
# Non-implementors → no finding
# ===========================================================================


def test_other_ext_point_not_flagged(tmp_path: Path) -> None:
    _write(
        tmp_path,
        'other.md',
        'implements: plan-marshall:extension-api/standards/ext-point-finalize-step\nname: x\n',
    )
    assert analyze_verify_step_contract(tmp_path) == []


def test_no_implements_not_flagged(tmp_path: Path) -> None:
    _write(tmp_path, 'plain.md', 'name: supporting-doc\norder: 20\n')
    assert analyze_verify_step_contract(tmp_path) == []


def test_no_frontmatter_not_flagged(tmp_path: Path) -> None:
    path = tmp_path / 'plan-marshall' / 'skills' / 'phase-5-execute' / 'standards' / 'body.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# No frontmatter\n\nBody only.\n', encoding='utf-8')
    assert analyze_verify_step_contract(tmp_path) == []


# ===========================================================================
# Finding shape + edge cases
# ===========================================================================


def test_finding_shape(tmp_path: Path) -> None:
    _write(tmp_path, 'nocanon.md', f'implements: {_EXT_POINT}\n')
    finding = analyze_verify_step_contract(tmp_path)[0]
    assert finding['type'] == FINDING_TYPE
    assert finding['rule_id'] == RULE_ID
    assert finding['severity'] == 'error'
    assert finding['line'] == 1


def test_absent_tree_returns_empty(tmp_path: Path) -> None:
    assert analyze_verify_step_contract(tmp_path / 'does-not-exist') == []
