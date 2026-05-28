#!/usr/bin/env python3
"""Tests for the ``_classify_affected_files`` helper in manage-execution-manifest.py.

The helper implements the four-bucket file-type classifier at composer scope.
The bucket vocabulary, predicates, and per-bucket assignments are the
normative source of truth in
``marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md``
§ File-type classifier — these tests verify the script-side implementation
returns the same string literals (``"python-prod"``, ``"python-test"``,
``"doc-only"``, ``"mixed"``) so the per-deliverable outline classifier and
the plan-wide composer classifier converge on a shared vocabulary.

See sibling lessons ``2026-05-28-10-001`` and ``2026-05-27-19-002``.
"""

import importlib.util
from pathlib import Path

import pytest

# =============================================================================
# Module loading (script has hyphens in filename → load via importlib)
# =============================================================================

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script_classify_affected_files', 'manage-execution-manifest.py')
_classify_affected_files = _mem._classify_affected_files


# =============================================================================
# Parametrized bucket tests — one case per canonical bucket
# =============================================================================


@pytest.mark.parametrize(
    'paths,expected_bucket',
    [
        # python-prod: every path under marketplace/bundles/**/scripts/**/*.py
        (
            [
                'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py',
                'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py',
            ],
            'python-prod',
        ),
        # python-test: every path under test/**/*.py
        (
            [
                'test/plan-marshall/manage-execution-manifest/test_classify_affected_files.py',
                'test/plan-marshall/phase-5-execute/test_phase_5_execute.py',
            ],
            'python-test',
        ),
        # doc-only: every path is non-.py (markdown skill bodies)
        (
            [
                'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
                'marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md',
                'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md',
            ],
            'doc-only',
        ),
        # mixed: .py + .md
        (
            [
                'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py',
                'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md',
            ],
            'mixed',
        ),
    ],
    ids=['python-prod', 'python-test', 'doc-only', 'mixed'],
)
def test_classify_affected_files_returns_canonical_bucket(paths, expected_bucket):
    """AAA: arrange paths matching each bucket's predicate; act via classifier; assert bucket label."""
    # Arrange
    # (paths and expected_bucket supplied by parametrize)

    # Act
    result = _classify_affected_files(paths)

    # Assert
    assert result == expected_bucket, (
        f'Expected bucket {expected_bucket!r} for paths {paths!r}; got {result!r}'
    )


# =============================================================================
# Edge case tests
# =============================================================================


def test_classify_affected_files_empty_list_defaults_to_doc_only():
    """An empty path list resolves to doc-only (conservative default — no Python to verify)."""
    # Arrange
    paths: list[str] = []

    # Act
    result = _classify_affected_files(paths)

    # Assert
    assert result == 'doc-only'


def test_classify_affected_files_single_doc_only_path():
    """A single non-.py file resolves to doc-only."""
    # Arrange
    paths = ['marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md']

    # Act
    result = _classify_affected_files(paths)

    # Assert
    assert result == 'doc-only'


def test_classify_affected_files_single_python_prod_path():
    """A single .py file under scripts/ resolves to python-prod."""
    # Arrange
    paths = [
        'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py'
    ]

    # Act
    result = _classify_affected_files(paths)

    # Assert
    assert result == 'python-prod'


def test_classify_affected_files_mixed_python_and_json():
    """A .py + .json file list resolves to mixed (Python + non-Python)."""
    # Arrange
    paths = [
        'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py',
        'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.json',
    ]

    # Act
    result = _classify_affected_files(paths)

    # Assert
    assert result == 'mixed'


def test_classify_affected_files_python_outside_scripts_or_test_resolves_to_mixed():
    """Python files outside both scripts/ and test/ fall through to mixed (defensive)."""
    # Arrange
    paths = ['some/random/dir/file.py']

    # Act
    result = _classify_affected_files(paths)

    # Assert
    # Python is present but not in conventional scripts/ or test/ location;
    # treat as mixed-equivalent so holistic verification is retained.
    assert result == 'mixed'


def test_classify_affected_files_three_doc_only_deliverables_from_this_plan():
    """Self-referential meta example: the three deliverables of this very plan.

    D1 and D2 are doc-only; D3 is mixed. The union of D1 + D2 alone resolves
    to doc-only — verifies the worked classification documented in
    outline-workflow-detail.md § File-type classifier.
    """
    # Arrange — D1 + D2's affected files (both doc-only deliverables)
    paths = [
        'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
        'marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md',
        'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md',
    ]

    # Act
    result = _classify_affected_files(paths)

    # Assert
    assert result == 'doc-only'


def test_classify_affected_files_raises_on_non_string_entries():
    """Verify that non-string entries cause a loud failure (TypeError) as per general rules."""
    # Arrange
    paths = [
        'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
        None,  # type: ignore[list-item]
    ]

    # Act & Assert
    with pytest.raises(TypeError):
        _classify_affected_files(paths)
