#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Zero-orphaned-references sweep over the live marketplace + test tree.

This plan retired several advisory surfaces that the legacy compose-driven
docs-only suppression path relied on. After every prior deliverable has landed,
the live tree must contain **zero** residual references to those retired tokens,
except inside the small set of files whose explicit job is to assert the removal
(removal-assertion tests use ``not hasattr`` / ``not in choices`` and therefore
legitimately name the symbols they pin as gone).

Retired surfaces asserted here (truly gone from production AND from non-allow-list
tests):

- **(b) Compose symbols** — the advisory docs-only post-matrix branch's return
  fields and helper: ``docs_only_classifier_fired``, ``plan_wide_bucket``, and the
  ``_log_docs_only_classifier_fired`` helper.
- **(c) Phase-4 LLM-authored verification-template prose** — the instructions that
  told the planner to hand-author per-task verification commands:
  ``"single source of truth for verification commands"`` and
  ``"Copy the deliverable's Verification block verbatim"``. Verification authoring
  is now derived deterministically by ``architecture derive-verification``.
- **(e) Phase-4 Step-7 holistic-task heading** — the ``"Create Holistic
  Verification Tasks"`` section heading; holistic verification is now derived, not
  hand-planned.
- **(f) ``classify-affected-files`` subcommand family** — the removed
  ``classify-affected-files`` subcommand and its ``cmd_classify_affected_files`` /
  ``classify_affected_files`` symbols.

Surfaces deliberately NOT swept here:

- The phase-3-outline ``Profiles: <!-- bucket: X -->`` advisory-comment requirement
  is RETAINED — it drives profile classification and is orthogonal to build_map.
- The ``_classify_paths_via_extensions`` seed-source aggregator is RETAINED and
  exercised by ``test_classify_paths_via_extensions.py`` /
  ``test_classify_affected_files.py``.

The allow-list (``_ALLOWED_RETIRED_TOKEN_FILES``) names the removal-assertion test
files that legitimately reference the retired tokens. Every other file in
``marketplace/`` and ``test/`` — plus this sweep file itself — must be clean.
"""

from pathlib import Path

# =============================================================================
# Tree roots and scan configuration
# =============================================================================

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_MARKETPLACE_ROOT = _REPO_ROOT / 'marketplace'
_TEST_ROOT = _REPO_ROOT / 'test'

# File suffixes worth scanning. Retired tokens only ever lived in Python sources,
# markdown skill/standards bodies, and JSON manifests.
_SCANNED_SUFFIXES = {'.py', '.md', '.json', '.toon'}

# Removal-assertion tests legitimately name the retired tokens (via ``not
# hasattr`` / ``not in choices`` assertions and the docstrings that explain the
# removal). They are excluded from the sweep by repo-relative path. This sweep
# file itself is excluded because it embeds every retired token as a search
# needle.
_ALLOWED_RETIRED_TOKEN_FILES = frozenset(
    {
        'test/plan-marshall/manage-execution-manifest/test_compose_docs_only_branch.py',
        'test/plan-marshall/manage-execution-manifest/test_classify_affected_files.py',
        'test/plan-marshall/manage-execution-manifest/test_no_orphaned_advisory_refs.py',
    }
)

# =============================================================================
# Retired-token catalogue (surface → list of literal needles)
# =============================================================================

# (b) Compose advisory docs-only symbols.
_SURFACE_B_COMPOSE_SYMBOLS = (
    'docs_only_classifier_fired',
    'plan_wide_bucket',
    '_log_docs_only_classifier_fired',
)

# (c) Phase-4 LLM-authored verification-template prose.
_SURFACE_C_TEMPLATE_PROSE = (
    'single source of truth for verification commands',
    "Copy the deliverable's Verification block verbatim",
)

# (e) Phase-4 Step-7 holistic-verification-task heading.
_SURFACE_E_HOLISTIC_HEADING = ('Create Holistic Verification Tasks',)

# (f) ``classify-affected-files`` subcommand family.
_SURFACE_F_CLASSIFY_SUBCOMMAND = (
    'classify-affected-files',
    'cmd_classify_affected_files',
    'classify_affected_files',
)

# Flat catalogue of every retired needle paired with its surface label, for
# precise failure reporting.
_RETIRED_TOKENS: tuple[tuple[str, str], ...] = tuple(
    [(needle, 'b: compose advisory symbols') for needle in _SURFACE_B_COMPOSE_SYMBOLS]
    + [(needle, 'c: phase-4 verification-template prose') for needle in _SURFACE_C_TEMPLATE_PROSE]
    + [(needle, 'e: phase-4 holistic-task heading') for needle in _SURFACE_E_HOLISTIC_HEADING]
    + [(needle, 'f: classify-affected-files subcommand') for needle in _SURFACE_F_CLASSIFY_SUBCOMMAND]
)


# =============================================================================
# Scan helpers
# =============================================================================


def _iter_scanned_files() -> list[Path]:
    """Yield every scannable file under marketplace/ and test/ minus the allow-list."""
    files: list[Path] = []
    for root in (_MARKETPLACE_ROOT, _TEST_ROOT):
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix not in _SCANNED_SUFFIXES:
                continue
            rel = path.relative_to(_REPO_ROOT).as_posix()
            if rel in _ALLOWED_RETIRED_TOKEN_FILES:
                continue
            files.append(path)
    return files


def _find_orphaned_references() -> list[tuple[str, str, str]]:
    """Return ``(rel_path, needle, surface)`` triples for every orphaned reference."""
    hits: list[tuple[str, str, str]] = []
    for path in _iter_scanned_files():
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for needle, surface in _RETIRED_TOKENS:
            if needle in text:
                hits.append((rel, needle, surface))
    return hits


# =============================================================================
# Tests
# =============================================================================


def test_no_orphaned_retired_references_in_live_tree():
    """Zero retired tokens survive anywhere in the live tree (allow-list excepted)."""
    hits = _find_orphaned_references()
    assert hits == [], (
        'Orphaned references to retired advisory surfaces found in the live tree '
        '(not on the removal-assertion allow-list):\n'
        + '\n'.join(f'  {rel}: {needle!r} (surface {surface})' for rel, needle, surface in hits)
    )


def test_scan_actually_covers_files():
    """Guard against a vacuous pass: the sweep must scan a non-trivial file set."""
    scanned = _iter_scanned_files()
    assert len(scanned) > 100, (
        f'Expected the marketplace+test sweep to cover many files; only {len(scanned)} '
        'were scanned — the tree roots or suffix filter are likely misconfigured.'
    )


def test_production_manifest_script_clean_of_classify_family():
    """The manage-execution-manifest production script carries no surface-(f) token.

    The clean-slate prose leak (``the legacy _classify_affected_files() helper``)
    was the last surviving surface-(f) reference in production; this pins it gone.
    """
    script = (
        _MARKETPLACE_ROOT
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'manage-execution-manifest'
        / 'scripts'
        / 'manage-execution-manifest.py'
    )
    text = script.read_text(encoding='utf-8')
    for needle in _SURFACE_F_CLASSIFY_SUBCOMMAND:
        assert needle not in text, (
            f'Surface-(f) token {needle!r} still present in {script.name}'
        )
    for needle in _SURFACE_B_COMPOSE_SYMBOLS:
        assert needle not in text, (
            f'Surface-(b) token {needle!r} still present in {script.name}'
        )


def test_allow_list_files_exist():
    """Every allow-listed path must exist — a stale allow-list silently widens the sweep gap."""
    for rel in _ALLOWED_RETIRED_TOKEN_FILES:
        assert (_REPO_ROOT / rel).is_file(), (
            f'Allow-listed file {rel!r} does not exist; prune or correct the allow-list.'
        )
