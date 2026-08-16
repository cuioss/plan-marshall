#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``end_time``-presence markers read as three states, not two, in both the
``metrics`` and ``input-integrity`` checks — a zero-token phase is incomplete
only when nothing explains it. The current marker pair explains it, and a record
written under the retired keys is recognised as old-schema so no value is read
out of it. On the input-integrity side the same three states decide whether an
execute phase reads blind, partial, or clean.
"""

from pathlib import Path

from _audit_fixtures import audit


def _plan_with_metrics(repo_root: Path, body: str) -> audit.PlanInputs:
    """Stage a one-plan corpus whose metrics.toon carries `body`; return inputs."""
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "sample-plan"
    (plan_dir / "work").mkdir(parents=True, exist_ok=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    (plan_dir / "work" / "metrics.toon").write_text(body, encoding="utf-8")
    return audit.collect_inputs(plan_dir)


_PHASE_BODY = "[4-plan]\n  total_tokens: 100\n[5-execute]\n  total_tokens: 0\n"
# A zero-token 5-execute on a PRE-#812 record: no marker pair at all.
_METRICS_UNEXPLAINED = _PHASE_BODY
# The SAME zero-token 5-execute, explained by the CURRENT markers.
_METRICS_MARKED = (
    "any_phase_missing_end_time: true\nphases_missing_end_time: 5-execute\n" + _PHASE_BODY
)
# The SAME zero-token 5-execute, named under the RETIRED keys — an archived
# record written before the rename. The reader must recognise the state and
# refuse to read the value out of it.
_METRICS_OLD_SCHEMA = "partial: true\nunrecorded_phases: 5-execute\n" + _PHASE_BODY


def test_metrics_unexplained_zero_token_is_incomplete(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_UNEXPLAINED)
    result = audit.check_metrics(inputs)
    assert "5-execute" in result["incomplete_recording"]


def test_metrics_marker_explained_zero_token_not_incomplete(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_MARKED)
    result = audit.check_metrics(inputs)
    # The marker-explained phase is excluded from incomplete_recording and
    # surfaced as an informational explained-gap anomaly instead.
    assert "5-execute" not in result["incomplete_recording"]
    assert any(
        "explained by the phases_missing_end_time marker" in a for a in result["anomalies"]
    ), result["anomalies"]


def test_metrics_old_schema_record_explains_nothing(tmp_path):
    """The retired keys name 5-execute, and the check still refuses to read them.

    This is the defect the three-state read exists to prevent: the pre-rename
    reader degraded an absent new key to `(False, set())`, so a bare rename would
    have certified every archived record clean. Here the phase falls back into
    `incomplete_recording` AND the unreadable state is named.
    """
    inputs = _plan_with_metrics(tmp_path, _METRICS_OLD_SCHEMA)
    result = audit.check_metrics(inputs)
    assert "5-execute" in result["incomplete_recording"]
    assert any("old-schema" in a for a in result["anomalies"]), result["anomalies"]


def test_parse_metrics_end_time_presence_reads_current_markers(tmp_path):
    path = tmp_path / "metrics.toon"
    path.write_text(_METRICS_MARKED, encoding="utf-8")
    presence = audit.parse_metrics_end_time_presence(path)
    assert presence.schema == audit.METRICS_SCHEMA_CURRENT
    assert presence.readable is True
    assert presence.any_phase_missing_end_time is True
    assert presence.phases_missing_end_time == frozenset({"5-execute"})
    assert presence.explained_phases == frozenset({"5-execute"})
    assert presence.forces_floor is True
    assert presence.unreadable_note == ""


def test_parse_metrics_end_time_presence_current_and_clean(tmp_path):
    """A readable record with nothing missing is the ONE non-floor state."""
    path = tmp_path / "metrics.toon"
    path.write_text(
        "any_phase_missing_end_time: false\nphases_missing_end_time: \n" + _PHASE_BODY,
        encoding="utf-8",
    )
    presence = audit.parse_metrics_end_time_presence(path)
    assert presence.schema == audit.METRICS_SCHEMA_CURRENT
    assert presence.any_phase_missing_end_time is False
    assert presence.phases_missing_end_time == frozenset()
    assert presence.forces_floor is False


def test_parse_metrics_end_time_presence_derives_bool_from_list_only_record(tmp_path):
    """A record NAMING an unclosed phase with no bool key must not read as clean.

    The writer emits the two keys as a pair, but an archived ``metrics.toon`` is
    immutable history: a truncated or hand-edited file can carry
    ``phases_missing_end_time`` alone. Defaulting the absent bool to False would
    return a ``current``, non-floor verdict for a record that explicitly names
    5-execute as never closed — the manufactured-clean-verdict defect this reader
    exists to remove. The surviving list is the authority.
    """
    # Arrange: the list names a phase; the bool key is absent entirely.
    path = tmp_path / "metrics.toon"
    path.write_text("phases_missing_end_time: 5-execute\n" + _PHASE_BODY, encoding="utf-8")

    # Act
    presence = audit.parse_metrics_end_time_presence(path)

    # Assert: the bool is derived from the list, and the record floors.
    assert presence.schema == audit.METRICS_SCHEMA_CURRENT
    assert presence.phases_missing_end_time == frozenset({"5-execute"})
    assert presence.any_phase_missing_end_time is True
    assert presence.forces_floor is True


def test_parse_metrics_end_time_presence_list_only_empty_list_stays_clean(tmp_path):
    """The negative control for the derivation above: an EMPTY list stays clean.

    Same absent-bool branch, opposite list contents. Without this pair the
    positive could pass vacuously against a blanket "bool key absent → True"
    rule, which would floor every bool-less record regardless of what its list
    actually says. The complementary control for the OTHER branch — an explicit
    ``any_phase_missing_end_time: false`` beside an empty list — is pinned by
    ``test_parse_metrics_end_time_presence_current_and_clean`` above.
    """
    # Arrange: the bool key is absent and the list is present but empty.
    path = tmp_path / "metrics.toon"
    path.write_text("phases_missing_end_time: \n" + _PHASE_BODY, encoding="utf-8")

    # Act
    presence = audit.parse_metrics_end_time_presence(path)

    # Assert: nothing is named, so the derived bool is False and nothing floors.
    assert presence.schema == audit.METRICS_SCHEMA_CURRENT
    assert presence.phases_missing_end_time == frozenset()
    assert presence.any_phase_missing_end_time is False
    assert presence.forces_floor is False


def test_parse_metrics_end_time_presence_reports_old_schema(tmp_path):
    """A record carrying only the RETIRED keys is old-schema, values withheld."""
    path = tmp_path / "metrics.toon"
    path.write_text(_METRICS_OLD_SCHEMA, encoding="utf-8")
    presence = audit.parse_metrics_end_time_presence(path)
    assert presence.schema == audit.METRICS_SCHEMA_OLD
    assert presence.readable is False
    # The values are withheld, NOT defaulted — a caller cannot accidentally read
    # a verdict out of an unreadable record.
    assert presence.any_phase_missing_end_time is None
    assert presence.phases_missing_end_time is None
    assert presence.explained_phases == frozenset()
    assert presence.forces_floor is True
    assert "old-schema" in presence.unreadable_note


def test_parse_metrics_end_time_presence_reports_pre_812(tmp_path):
    """A record carrying NEITHER pair is pre-#812 — distinct from old-schema."""
    path = tmp_path / "metrics.toon"
    path.write_text(_METRICS_UNEXPLAINED, encoding="utf-8")
    presence = audit.parse_metrics_end_time_presence(path)
    assert presence.schema == audit.METRICS_SCHEMA_PRE_812
    assert presence.schema != audit.METRICS_SCHEMA_OLD
    assert presence.any_phase_missing_end_time is None
    assert presence.phases_missing_end_time is None
    assert presence.forces_floor is True
    assert "pre-#812" in presence.unreadable_note
    assert "old-schema" not in presence.unreadable_note


def test_input_integrity_unexplained_execute_is_blind(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_UNEXPLAINED)
    result = audit.check_input_integrity(inputs)
    assert result["data_confidence"] == "blind"
    assert "5-execute" in result["metrics_blind"]


def test_input_integrity_marker_explained_execute_is_partial_not_blind(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_MARKED)
    result = audit.check_input_integrity(inputs)
    # A #812-marker-explained zero-token execute is an explained gap, never blind.
    assert result["data_confidence"] == "partial"
    assert "5-execute" not in result["metrics_blind"]
    assert result["metrics_marker_schema"] == audit.METRICS_SCHEMA_CURRENT


def test_input_integrity_old_schema_execute_stays_blind(tmp_path):
    """The retired keys do not rescue a zero-token execute out of `blind`.

    Same fixture as the marker-explained test above except for the key names, so
    the difference in verdict is traceable to the schema and nothing else.
    """
    inputs = _plan_with_metrics(tmp_path, _METRICS_OLD_SCHEMA)
    result = audit.check_input_integrity(inputs)
    assert result["metrics_marker_schema"] == audit.METRICS_SCHEMA_OLD
    assert result["data_confidence"] == "blind"
    assert "5-execute" in result["metrics_blind"]
