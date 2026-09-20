#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Presence and shape tests for PLAN-04 persona behavior rules.

Pins the nudge-batching obligation, the structured deviation-audit
checklist, and the cross-turn correction-memory rule in
``agent-behavior-rules.md``, plus the Rules Card index row.
"""

from pathlib import Path

RULES = (
    Path(__file__).resolve().parents[3]
    / "marketplace"
    / "bundles"
    / "plan-marshall"
    / "skills"
    / "persona-plan-marshall-agent"
    / "standards"
    / "agent-behavior-rules.md"
)


def _body() -> str:
    return RULES.read_text(encoding="utf-8")


def test_rules_file_exists():
    assert RULES.is_file()


def test_nudge_section_heading_present():
    assert "### Nudge handling and correction memory" in _body()


def test_nudge_batching_obligation_verbs():
    body = _body()
    assert "enumerate the invariant family" in body
    assert "close every sibling" in body
    assert "report the closed set" in body


def test_minimal_literal_compliance_is_finding():
    assert "minimal-literal compliance is itself a recorded finding" in _body()


def test_deviation_audit_checklist_fields():
    body = _body()
    for field in (
        "Nudge received",
        "Invariant family named",
        "Siblings enumerated",
        "Correction memory consulted",
        "Per-sibling closure outcome",
        "Closed set reported",
    ):
        assert field in body


def test_correction_memory_consult_obligation():
    body = _body()
    assert "consult the active corrections" in body
    assert "three nudges" in body


def test_rules_card_indexes_new_section():
    body = _body()
    assert "Nudge handling and correction memory" in body
    assert "#nudge-handling-and-correction-memory" in body
