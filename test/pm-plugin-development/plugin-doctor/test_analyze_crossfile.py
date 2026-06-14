# ruff: noqa: I001, E402
"""Verifier-echo tests for the cross-file rules (``duplication`` /
``extraction`` / ``terminology``).

These three ``type`` values are NOT static-detection findings: the static
``analyze_cross_file`` analyzer emits only raw analysis structures
(``exact_duplicates`` / ``similarity_candidates`` / ``extraction_candidates`` /
``terminology_variants``). The ``type: duplication/extraction/terminology``
FINDINGS are emitted SOLELY by ``verify_findings(analysis, llm_findings)`` in
``_cmd_cross_file.py``, and only when a crafted LLM claim verifies.

This is therefore a verifier-echo test — it calls ``verify_findings()`` with a
crafted ``analysis`` + ``llm_findings`` pair (authored once in
``_fixtures.crossfile_verified_findings``) and asserts each rule type lands in
``verified``. It is NOT a duplication-detector test against a scratch tree. Each
emitted finding is fed through the shared ``record_fired(...)`` tap so the
suite-coverage meta-test (``test_zero_match_suite_coverage.py``) counts these
three rules as fired even when run in isolation.
"""

from _fixtures import crossfile_verified_findings, record_fired


def test_duplication_rule_fires_from_verified_claim():
    """A verified true_duplicate claim yields a ``duplication`` finding."""
    # Arrange / Act
    findings = crossfile_verified_findings()
    record_fired(findings)

    # Assert
    assert any(f['type'] == 'duplication' for f in findings), (
        'verify_findings did not emit a duplication finding for the crafted '
        'true_duplicate claim'
    )


def test_extraction_rule_fires_from_verified_claim():
    """A verified extraction claim yields an ``extraction`` finding."""
    # Arrange / Act
    findings = crossfile_verified_findings()
    record_fired(findings)

    # Assert
    assert any(f['type'] == 'extraction' for f in findings), (
        'verify_findings did not emit an extraction finding for the crafted '
        'extraction claim'
    )


def test_terminology_rule_fires_from_verified_claim():
    """A verified standardize claim yields a ``terminology`` finding."""
    # Arrange / Act
    findings = crossfile_verified_findings()
    record_fired(findings)

    # Assert
    assert any(f['type'] == 'terminology' for f in findings), (
        'verify_findings did not emit a terminology finding for the crafted '
        'terminology standardize claim'
    )


def test_all_three_crossfile_rule_types_verified():
    """All three cross-file rule types land in the verified set together."""
    # Arrange / Act
    findings = crossfile_verified_findings()
    types = {f['type'] for f in findings}
    record_fired(findings)

    # Assert
    assert {'duplication', 'extraction', 'terminology'} <= types, (
        f'crafted claims did not verify all three cross-file rule types; got {sorted(types)}'
    )
