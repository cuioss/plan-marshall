# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``triage-reads-top-level-only`` rule analyzer.

The analyzer walks every ``.md`` file under the marketplace bundles root, keeps
the triage surfaces (files named ``triage.md`` / ``verification-feedback.md`` and
any file under an ``ext-triage-*`` directory), and flags any line that READS a
concrete ``raw_input`` field — the containment invariant that triage reads the
clean top-level fields only, never the ``raw_input.*`` quarantine namespace.

Test layers:
  * A triage doc that reads a concrete ``raw_input`` field (dotted, subscript,
    key-access) → finding.
  * An ``ext-triage-{domain}`` skill doc that reads ``raw_input`` → finding.
  * A triage doc that only DOCUMENTS the invariant with placeholder/wildcard
    forms (``raw_input.*`` / ``raw_input.{field}`` / bare backtick) → no finding.
  * A non-triage file that reads ``raw_input`` (e.g. the store scripts) → no
    finding (not a triage surface).
  * Finding shape (rule_id / type / severity / line).
  * Absent tree → empty list.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_atrs = _load_module('_analyze_triage_read_surface', '_analyze_triage_read_surface.py')

analyze_triage_read_surface = _atrs.analyze_triage_read_surface
RULE_ID = _atrs.RULE_ID
FINDING_TYPE = _atrs.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _triage_doc(tmp_path: Path, name: str = 'triage.md') -> Path:
    return tmp_path / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / name


def _ext_triage_doc(tmp_path: Path, bundle: str = 'pm-dev-java') -> Path:
    return tmp_path / bundle / 'skills' / 'ext-triage-java' / 'SKILL.md'


# ===========================================================================
# Violating surfaces → finding
# ===========================================================================


def test_dotted_raw_input_read_in_triage_doc_flagged(tmp_path: Path) -> None:
    _write(_triage_doc(tmp_path), '# Triage\n\nRead the finding `raw_input.detail` and decide.\n')
    findings = analyze_triage_read_surface(tmp_path)
    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID


def test_subscript_raw_input_read_in_verification_feedback_flagged(tmp_path: Path) -> None:
    _write(
        _triage_doc(tmp_path, 'verification-feedback.md'),
        "# VF\n\nQuote raw_input['body'] into the reply.\n",
    )
    findings = analyze_triage_read_surface(tmp_path)
    assert len(findings) == 1
    assert findings[0]['file'].endswith('verification-feedback.md')


def test_key_access_raw_input_in_ext_triage_skill_flagged(tmp_path: Path) -> None:
    _write(
        _ext_triage_doc(tmp_path),
        "# ext-triage-java\n\nInspect finding['raw_input'] before triage.\n",
    )
    findings = analyze_triage_read_surface(tmp_path)
    assert len(findings) == 1
    assert 'ext-triage-java' in findings[0]['file']


def test_get_raw_input_read_flagged(tmp_path: Path) -> None:
    _write(_triage_doc(tmp_path), "# Triage\n\nfinding.get('raw_input') is off-limits.\n")
    findings = analyze_triage_read_surface(tmp_path)
    assert len(findings) == 1


def test_multiple_reads_emit_one_finding_per_line(tmp_path: Path) -> None:
    _write(
        _triage_doc(tmp_path),
        '# Triage\n\nRead `raw_input.detail`.\nAlso `raw_input.message`.\n',
    )
    findings = analyze_triage_read_surface(tmp_path)
    assert len(findings) == 2
    assert {f['line'] for f in findings} == {3, 4}


# ===========================================================================
# Compliant surfaces → no finding
# ===========================================================================


def test_placeholder_wildcard_forms_not_flagged(tmp_path: Path) -> None:
    _write(
        _triage_doc(tmp_path),
        (
            '# Triage\n\n'
            'Triage MUST read TOP-LEVEL fields only, never `raw_input.*`.\n'
            'The `raw_input.{field}` quarantine namespace is audit-only.\n'
            'Every value is quarantined under `raw_input`.\n'
        ),
    )
    assert analyze_triage_read_surface(tmp_path) == []


def test_non_triage_file_reading_raw_input_not_flagged(tmp_path: Path) -> None:
    # A manage-findings store doc legitimately documents raw_input.detail access
    # but is NOT a triage surface, so it is never scanned.
    store_doc = tmp_path / 'plan-marshall' / 'skills' / 'manage-findings' / 'standards' / 'jsonl-format.md'
    _write(store_doc, '# Ledger\n\nThe store writes raw_input.detail on file.\n')
    assert analyze_triage_read_surface(tmp_path) == []


def test_clean_triage_doc_with_top_level_reads_not_flagged(tmp_path: Path) -> None:
    _write(
        _triage_doc(tmp_path),
        '# Triage\n\nDecide on the promoted top-level `detail` and `message` fields.\n',
    )
    assert analyze_triage_read_surface(tmp_path) == []


# ===========================================================================
# Finding shape + edge cases
# ===========================================================================


def test_finding_shape(tmp_path: Path) -> None:
    _write(_triage_doc(tmp_path), '# Triage\n\nRead `raw_input.detail`.\n')
    finding = analyze_triage_read_surface(tmp_path)[0]
    assert finding['type'] == FINDING_TYPE
    assert finding['rule_id'] == RULE_ID
    assert finding['severity'] == 'error'
    assert finding['line'] == 3


def test_absent_tree_returns_empty(tmp_path: Path) -> None:
    assert analyze_triage_read_surface(tmp_path / 'does-not-exist') == []
