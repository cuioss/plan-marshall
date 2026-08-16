#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Recipe/lesson provenance intake — both metadata fields reach ``recipe_key``.

``collect_inputs`` resolves the Row 2 recipe signal from EITHER
``status.metadata.plan_source`` or ``status.metadata.recipe_key``. Reading only
``plan_source`` made Row 2 structurally unreachable for every plan routed through
the ``manage-lessons auto-suggest`` path, which writes ``recipe_key`` alone.

The precedence and the field set mirror the live composer's
``_manifest_decide._read_recipe_source``, so the audit's counterfactual and the
composer's decision cannot disagree on the same status.json.
"""

from pathlib import Path

from _audit_fixtures import audit


def _plan_with_metadata(repo_root: Path, metadata: str) -> audit.PlanInputs:
    """Stage an archived plan whose status.json carries ``metadata``."""
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "provenance-plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "references.json").write_text(
        '{"scope_estimate": "surgical", "affected_files": ["src/a.py"]}',
        encoding="utf-8",
    )
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix", ' + metadata + "}}", encoding="utf-8"
    )
    return audit.collect_inputs(plan_dir)


def test_recipe_key_metadata_field_populates_recipe_key(tmp_path):
    """A plan carrying ONLY ``recipe_key`` resolves the recipe signal.

    The auto-suggest auto-route path writes this field and never writes
    ``plan_source``, so this is the case the previous one-directional read
    dropped on the floor.
    """
    inputs = _plan_with_metadata(tmp_path, '"recipe_key": "recipe-lesson-cleanup"')
    assert inputs.recipe_key == "recipe-lesson-cleanup"


def test_plan_source_metadata_field_still_populates_recipe_key(tmp_path):
    inputs = _plan_with_metadata(tmp_path, '"plan_source": "lesson-042"')
    assert inputs.recipe_key == "lesson-042"


def test_plan_source_wins_when_both_fields_are_present(tmp_path):
    """Precedence matches ``_read_recipe_source``'s ``('plan_source', 'recipe_key')``."""
    inputs = _plan_with_metadata(
        tmp_path, '"plan_source": "lesson-042", "recipe_key": "recipe-lesson-cleanup"'
    )
    assert inputs.recipe_key == "lesson-042"


def test_neither_field_leaves_recipe_key_unset(tmp_path):
    inputs = _plan_with_metadata(tmp_path, '"planning_lane": "light"')
    assert inputs.recipe_key is None


def test_blank_recipe_key_is_not_a_recipe_signal(tmp_path):
    """A whitespace-only value is absence, not provenance — same as ``plan_source``."""
    inputs = _plan_with_metadata(tmp_path, '"recipe_key": "   "')
    assert inputs.recipe_key is None


def test_row_2_recipe_fires_for_a_recipe_key_routed_plan(tmp_path):
    """The end-to-end consequence: Row 2 is reachable via ``recipe_key``.

    Without the recipe signal these same inputs (surgical + bug_fix) fall through
    to Row 5, so the assertion discriminates the two readings rather than merely
    exercising the matrix.
    """
    inputs = _plan_with_metadata(tmp_path, '"recipe_key": "recipe-lesson-cleanup"')
    assert audit.derive_expected_rule(inputs) == "recipe"


def test_row_5_still_fires_without_any_recipe_provenance(tmp_path):
    """The negative control for the row above — the discriminator is the signal."""
    inputs = _plan_with_metadata(tmp_path, '"planning_lane": "light"')
    assert audit.derive_expected_rule(inputs) == "surgical_bug_fix"
