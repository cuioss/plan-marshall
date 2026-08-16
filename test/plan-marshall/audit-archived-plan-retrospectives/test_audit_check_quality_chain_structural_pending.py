#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``quality-chain`` pending partition — backlog versus mislabelled population.

``manage-findings.add_finding`` seeds EVERY record with ``resolution: 'pending'``,
and nothing ever resolves a knowledge finding: a ``tip`` is a suggestion, an
``insight`` an observation, a ``best-practice`` a note. Counting them as
unresolved chain debt made the pending population one no action could empty.

The property under test is the one that makes the count meaningful: a detector
reporting a count must be able to say what would make that count zero. For the
actionable half that answer is "resolve the findings"; for the structural half
there is no answer, so it is reported in its own bucket instead of inflating the
genuine signal.

The membership mirrors the fixed actionable-vs-knowledge partition already
shipped at ``plan-marshall/scripts/_invariants.py``.
"""

import json
from pathlib import Path
from typing import Any

from _audit_fixtures import audit


def _plan_with_findings(
    repo_root: Path, plan_id: str, findings_by_file: dict[str, list[dict[str, Any]]]
) -> Any:
    plan_dir = repo_root / ".plan" / "temp" / "qc-pending" / plan_id
    findings_dir = plan_dir / "artifacts" / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    for fname, records in findings_by_file.items():
        (findings_dir / fname).write_text(
            "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
        )
    return audit.collect_inputs(plan_dir)


def _seeded(**overrides: Any) -> dict[str, Any]:
    """A record shaped as `add_finding` writes it — `resolution` seeded pending."""
    record = {
        "hash_id": "abc123",
        "title": "a finding",
        "detail": "some detail",
        "resolution": "pending",
        "resolution_detail": None,
        "promoted": False,
    }
    record.update(overrides)
    return record


class TestStructuralPendingPredicate:
    def test_knowledge_types_are_structurally_pending(self):
        for finding_type in ("tip", "insight", "best-practice", "improvement"):
            obj = _seeded(type=finding_type)
            assert audit._qc_structural_pending(obj, f"{finding_type}.jsonl") is True

    def test_actionable_types_are_not_structurally_pending(self):
        for finding_type in ("build-error", "test-failure", "lint-issue", "pr-comment"):
            obj = _seeded(type=finding_type)
            assert audit._qc_structural_pending(obj, f"{finding_type}.jsonl") is False

    def test_filename_carries_the_type_when_the_record_omits_it(self):
        """The per-type JSONL layout is the normal route; a record need not repeat it."""
        assert audit._qc_structural_pending(_seeded(), "tip.jsonl") is True
        assert audit._qc_structural_pending(_seeded(), "build-error.jsonl") is False

    def test_a_declared_type_overrules_the_filename(self):
        obj = _seeded(type="build-error")
        assert audit._qc_structural_pending(obj, "tip.jsonl") is False

    def test_a_resolved_knowledge_finding_is_not_structural(self):
        """An operator who dispositioned a tip has made it a resolved finding.

        The predicate reports what the record says; it never overrules a real
        disposition on the strength of the type alone.
        """
        obj = _seeded(type="tip", resolution="accepted")
        assert audit._qc_structural_pending(obj, "tip.jsonl") is False


class TestGenuineSignalExcludesStructuralPending:
    def test_pending_tip_is_not_genuine_chain_debt(self):
        row = {
            "mechanism": "other",
            "resolution": "pending",
            "structural_pending": True,
        }
        assert audit._qc_finding_genuine(row) is False

    def test_pending_actionable_finding_is_still_genuine(self):
        """The negative control — the partition must not silence real debt."""
        row = {
            "mechanism": "build",
            "resolution": "pending",
            "structural_pending": False,
        }
        assert audit._qc_finding_genuine(row) is True

    def test_auto_review_knowledge_finding_stays_genuine(self):
        """The shift-left leg is about what it COST to catch, not about closure."""
        row = {
            "mechanism": "auto-review",
            "resolution": "pending",
            "structural_pending": True,
        }
        assert audit._qc_finding_genuine(row) is True


class TestPendingSplitIsReported:
    def test_corpus_splits_pending_into_actionable_and_structural(self, tmp_path: Path):
        inputs = _plan_with_findings(
            tmp_path,
            "plan-mixed",
            {
                "tip.jsonl": [_seeded(type="tip"), _seeded(type="tip")],
                "build-error.jsonl": [_seeded(type="build-error")],
            },
        )
        result = audit.cross_quality_chain([inputs])

        assert result["corpus_pending"] == 3
        assert result["corpus_structural_pending"] == 2
        assert result["corpus_actionable_pending"] == 1
        # The split is exhaustive over the pending column — no row is lost.
        assert (
            result["corpus_actionable_pending"] + result["corpus_structural_pending"]
            == result["corpus_pending"]
        )

    def test_matrix_still_counts_every_finding(self, tmp_path: Path):
        """The census stays faithful: structural rows are labelled, not deleted.

        Subtracting them from the matrix would trade one untrue number for
        another — the matrix answers "what was filed", the split answers "what
        could be cleared".
        """
        inputs = _plan_with_findings(
            tmp_path, "plan-census", {"tip.jsonl": [_seeded(type="tip")]}
        )
        result = audit.cross_quality_chain([inputs])

        matrix_total = sum(
            result["corpus_matrix"][m][r]
            for m in result["mechanisms"]
            for r in result["resolutions"]
        )
        assert matrix_total == 1
        assert result["corpus_structural_pending"] == 1

    def test_block_publishes_both_halves_and_says_why(self, tmp_path: Path):
        inputs = _plan_with_findings(
            tmp_path,
            "plan-emit",
            {
                "tip.jsonl": [_seeded(type="tip")],
                "build-error.jsonl": [_seeded(type="build-error")],
            },
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)

        assert "pending_total: 2" in block
        assert "pending_actionable: 1" in block
        assert "pending_structural: 1" in block
        assert "pending_structural_note:" in block
        assert "structural_pending" in block

    def test_an_all_knowledge_plan_reports_zero_actionable_debt(self, tmp_path: Path):
        """The end-to-end consequence: a plan whose only pendings are permanent.

        Its chain debt is genuinely zero, and the count now says so instead of
        reporting a backlog no action could clear.
        """
        inputs = _plan_with_findings(
            tmp_path,
            "plan-knowledge",
            {"tip.jsonl": [_seeded(type="tip")], "insight.jsonl": [_seeded(type="insight")]},
        )
        result = audit.cross_quality_chain([inputs])

        assert result["corpus_actionable_pending"] == 0
        assert result["corpus_structural_pending"] == 2
        assert not any(audit._qc_finding_genuine(f) for f in result["findings"])
