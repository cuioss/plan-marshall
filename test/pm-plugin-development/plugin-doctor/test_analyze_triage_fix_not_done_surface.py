# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``triage-fix-not-done-contract`` rule analyzer.

The analyzer walks every ``triage.md`` file under the marketplace bundles root,
locates the Step 3c FIX action body (a ``- **FIX**`` bullet region whose
defining fix-task allocation signature — ``prepare-add`` / ``commit-add`` — is
present), and flags the body when EITHER:

  * (a) it marks its fix task done inline — a ``mark-step-done`` / ``--outcome
    done`` / ``--status done`` call shape appears in the region; OR
  * (b) it omits any member of the required ``not-done`` / ``loop_back`` /
    ``STOP`` directive triad.

Detection is deliberately narrow: the inline-done condition matches only
unambiguous done-marking *call shapes*, never the descriptive prose ("... marking
its task done inline strands the change ...") the contract itself requires — so
the very doc that correctly states the contract is not a false positive.

Test layers:
  * A FIX body carrying the full triad + allocation, no inline-done → no finding.
  * A FIX body that marks the task done inline → one finding.
  * A FIX body missing the triad → one finding.
  * A FIX body describing the failure mode in prose (no call shape) → no finding
    (false-positive guard mirroring the real post-D1 triage.md).
  * A triage.md that merely describes the invariant with no FIX action body → no
    finding (region-skipped).
  * A non-triage.md file with a FIX body → no finding (not a triage surface).
  * Finding shape (rule_id / type / severity / line) + RULE_DESCRIPTOR fields.
  * Absent tree → empty list.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_afnds = _load_module('_analyze_triage_fix_not_done_surface', '_analyze_triage_fix_not_done_surface.py')

analyze_triage_fix_not_done_surface = _afnds.analyze_triage_fix_not_done_surface
RULE_ID = _afnds.RULE_ID
FINDING_TYPE = _afnds.FINDING_TYPE
RULE_DESCRIPTOR = _afnds.RULE_DESCRIPTOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _triage_doc(tmp_path: Path, name: str = 'triage.md') -> Path:
    return tmp_path / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / name


# Compliant FIX body: full triad + allocation signature, no inline done-marking.
_COMPLIANT_FIX = (
    '# Triage\n\n'
    '### 3c. Act on each decision\n\n'
    '- **FIX** — allocate the fix task, then resolve the finding fixed.\n\n'
    '  > **Not-done / STOP contract.** FIX allocates the fix task **not-done** via\n'
    '  > the `prepare-add` then `commit-add` flow, resolves the finding fixed, then\n'
    '  > **STOP**. Execution and commit are owned by phase-5-execute, re-entered by\n'
    '  > the `loop_back` this FIX raises.\n\n'
    '- **SUPPRESS** — annotate the sink.\n'
)


# ===========================================================================
# Compliant surface → no finding
# ===========================================================================


def test_compliant_fix_body_not_flagged(tmp_path: Path) -> None:
    _write(_triage_doc(tmp_path), _COMPLIANT_FIX)
    assert analyze_triage_fix_not_done_surface(tmp_path) == []


def test_prose_failure_mode_description_not_flagged(tmp_path: Path) -> None:
    # The contract REQUIRES the FIX body to describe the failure mode in prose.
    # An affirmative "marking its task done" sentence with no call shape must NOT
    # be flagged — this is the guard that keeps the real post-D1 triage.md clean.
    body = (
        '# Triage\n\n'
        '- **FIX** — allocate the fix task, then resolve the finding fixed.\n\n'
        '  > **Not-done / STOP contract.** FIX allocates the fix task **not-done** via\n'
        '  > `prepare-add` then `commit-add`, then **STOP**; the `loop_back` re-enters\n'
        '  > phase-5-execute. Implementing the fix and marking its task done inline\n'
        '  > strands the change behind a done task and makes the loop_back a no-op.\n\n'
        '- **SUPPRESS** — annotate the sink.\n'
    )
    _write(_triage_doc(tmp_path), body)
    assert analyze_triage_fix_not_done_surface(tmp_path) == []


def test_describe_only_doc_without_fix_action_not_flagged(tmp_path: Path) -> None:
    # A triage.md that merely discusses the invariant but has no FIX action body
    # (no allocation signature) is region-skipped and never flagged.
    body = (
        '# Triage overview\n\n'
        'The FIX action must allocate the fix task not-done and then STOP; the\n'
        'loop_back re-enters phase-5-execute which owns execution and commit.\n'
    )
    _write(_triage_doc(tmp_path), body)
    assert analyze_triage_fix_not_done_surface(tmp_path) == []


def test_non_triage_file_with_fix_body_not_flagged(tmp_path: Path) -> None:
    # Only basename triage.md is a triage-FIX surface; an identically-shaped FIX
    # body in another doc is never scanned.
    other = tmp_path / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'verification-feedback.md'
    _write(other, _COMPLIANT_FIX.replace('not-done', 'nope').replace('STOP', 'go'))
    assert analyze_triage_fix_not_done_surface(tmp_path) == []


# ===========================================================================
# Violating surfaces → finding
# ===========================================================================


def test_inline_done_marking_flagged(tmp_path: Path) -> None:
    # Triad present, but the body marks the fix task done inline via a call shape.
    body = (
        '# Triage\n\n'
        '- **FIX** — allocate the fix task.\n\n'
        '  > **Not-done / STOP contract.** FIX allocates **not-done** via `prepare-add`\n'
        '  > then `commit-add`, then **STOP**; the `loop_back` re-enters phase-5-execute.\n\n'
        '  Then run `manage-tasks finalize-step --outcome done` to close the task.\n\n'
        '- **SUPPRESS** — annotate the sink.\n'
    )
    _write(_triage_doc(tmp_path), body)
    findings = analyze_triage_fix_not_done_surface(tmp_path)
    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID
    assert 'done inline' in findings[0]['description']


def test_status_done_call_shape_flagged(tmp_path: Path) -> None:
    body = (
        '# Triage\n\n'
        '- **FIX** — allocate the fix task via `prepare-add` then `commit-add`.\n\n'
        '  > **Not-done / STOP contract.** FIX allocates **not-done**, then **STOP**;\n'
        '  > the `loop_back` re-enters phase-5-execute.\n\n'
        '  Finally, `manage-tasks update --status done` marks it complete.\n\n'
        '- **SUPPRESS** — annotate the sink.\n'
    )
    _write(_triage_doc(tmp_path), body)
    findings = analyze_triage_fix_not_done_surface(tmp_path)
    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID


def test_missing_triad_flagged(tmp_path: Path) -> None:
    # Allocation present, no inline-done call, but the directive triad is absent.
    body = (
        '# Triage\n\n'
        '- **FIX** — allocate the fix task via `prepare-add` then `commit-add`, then\n'
        '  resolve the finding fixed with a reviewer-ready resolution_detail.\n\n'
        '- **SUPPRESS** — annotate the sink.\n'
    )
    _write(_triage_doc(tmp_path), body)
    findings = analyze_triage_fix_not_done_surface(tmp_path)
    assert len(findings) == 1
    assert findings[0]['rule_id'] == RULE_ID
    assert 'triad' in findings[0]['description']


# ===========================================================================
# Finding shape + descriptor + edge cases
# ===========================================================================


def test_finding_shape(tmp_path: Path) -> None:
    body = (
        '# Triage\n\n'
        '- **FIX** — allocate the fix task via `prepare-add` then `commit-add`.\n\n'
        '- **SUPPRESS** — annotate the sink.\n'
    )
    _write(_triage_doc(tmp_path), body)
    finding = analyze_triage_fix_not_done_surface(tmp_path)[0]
    assert finding['type'] == FINDING_TYPE
    assert finding['rule_id'] == RULE_ID
    assert finding['severity'] == 'error'
    # The missing-triad finding anchors at the FIX bullet line (1-indexed).
    assert finding['line'] == 3


def test_rule_descriptor_fields() -> None:
    assert RULE_DESCRIPTOR.rule_id == RULE_ID
    assert RULE_DESCRIPTOR.rule_id == 'triage-fix-not-done-contract'
    assert RULE_DESCRIPTOR.severity == 'error'
    assert RULE_DESCRIPTOR.category == 'safety'
    assert RULE_DESCRIPTOR.scope == 'file-local'


def test_absent_tree_returns_empty(tmp_path: Path) -> None:
    assert analyze_triage_fix_not_done_surface(tmp_path / 'does-not-exist') == []
