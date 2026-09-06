# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for POC agent fixtures: agent-name resolution and per-agent model/effort.

The fixtures at ``test/fixtures/poc-agent.md`` and
``test/fixtures/poc-agent-high.md`` lock down the runtime contract:

1. ``Task: <plugin>:poc-agent`` dispatches the canonical fixture; the
   agent runs on ``model: sonnet`` (no effort). The canonical's
   frontmatter is the source of truth.
2. ``Task: <plugin>:poc-agent-high`` dispatches the variant fixture; the
   agent runs on ``model: opus`` with ``effort: high``. Effort
   propagation is observable in the agent's returned ``<usage>`` block.

The agents themselves are dispatched and inspected by a live Claude
Code runtime — this test cannot do that at unit-test time. What it
DOES verify is the static contract the runtime depends on:

- Fixtures exist at the expected paths.
- The canonical frontmatter pins the expected ``(model, effort)``
  primitives — any drift breaks the runtime regression.
- Fixture files are NOT collected as production tests (no name clash
  with marketplace/bundles agents).
- Fixture files are NOT processed by the variant emitter (they live
  outside ``marketplace/bundles/``).

When Claude Code's name-resolution semantics change, or when a model
release flips capability flags, this test fires before downstream
regressions surface in PR review.
"""

from __future__ import annotations

from pathlib import Path

from conftest import PROJECT_ROOT

FIXTURE_DIR = PROJECT_ROOT / 'test' / 'fixtures'
CANONICAL = FIXTURE_DIR / 'poc-agent.md'
VARIANT_HIGH = FIXTURE_DIR / 'poc-agent-high.md'


def _read_frontmatter(path: Path) -> str:
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise AssertionError(f'{path} missing YAML frontmatter')
    end = text.find('\n---\n', 4)
    assert end != -1, f'{path} frontmatter not closed'
    return text[4:end]


# =============================================================================
# Existence
# =============================================================================


def test_canonical_fixture_exists():
    assert CANONICAL.exists(), f'POC canonical fixture missing: {CANONICAL}'


def test_variant_fixture_exists():
    assert VARIANT_HIGH.exists(), f'POC variant fixture missing: {VARIANT_HIGH}'


# =============================================================================
# Canonical contract
# =============================================================================


def test_canonical_pins_sonnet_no_effort():
    fm = _read_frontmatter(CANONICAL)
    assert 'name: poc-agent' in fm
    assert 'model: sonnet' in fm
    # Canonical fixture deliberately has NO effort line — exercises the
    # haiku/medium-effort-omitted branch of the runtime.
    assert 'effort:' not in fm


def test_canonical_does_not_declare_implements():
    """The fixture canonical is NOT a build-target source — it must NOT declare
    `implements: ext-point-dynamic-level-executor` or the variant emitter
    would try to regenerate it (which would fail because the fixture
    pins `model:` directly).
    """
    fm = _read_frontmatter(CANONICAL)
    assert 'implements:' not in fm


# =============================================================================
# Variant contract
# =============================================================================


def test_variant_pins_opus_high():
    fm = _read_frontmatter(VARIANT_HIGH)
    assert 'name: poc-agent-high' in fm
    assert 'model: opus' in fm
    assert 'effort: high' in fm


def test_variant_name_matches_filename_convention():
    """`{base}-{level}.md` filename matches the `name:` field — Claude Code
    resolves Task: <plugin>:<name>; mismatched name would silently
    dispatch the wrong agent.
    """
    fm = _read_frontmatter(VARIANT_HIGH)
    assert VARIANT_HIGH.stem == 'poc-agent-high'
    assert 'name: poc-agent-high' in fm


# =============================================================================
# Build-target isolation
# =============================================================================


def test_fixtures_outside_marketplace_bundles():
    """Fixtures live under test/fixtures/, NOT under marketplace/bundles/.

    The Claude target's emitter scans marketplace/bundles/ — fixtures
    must stay outside that root or the build target would regenerate
    them (and refuse, because they pin model: directly without
    declaring implements:).
    """
    bundles_root = PROJECT_ROOT / 'marketplace' / 'bundles'
    assert FIXTURE_DIR.is_relative_to(PROJECT_ROOT)
    assert not FIXTURE_DIR.is_relative_to(bundles_root)


# =============================================================================
# Test-collection isolation
# =============================================================================


def test_fixture_files_have_no_test_collisions():
    """Fixture filenames don't collide with any marketplace agent.

    pytest does not collect agents/*.md as tests, but a filename clash
    between fixture and production agent is still a smell — the fixture
    test relies on `poc-agent` and `poc-agent-high` being unique names
    no production agent shares.

    ⛔ The POPULATION is asserted as well as the tree, and the distinction is
    the whole point: `is_dir()` proves the tree exists, never that the sweep
    iterated anything. If the bundles directory survived but its agent files did
    not, `rglob` would yield nothing, `collisions == []` would hold trivially,
    and this guard would report green having checked no agent at all. Publishing
    the population as its own assertion is what stops a sweep from passing over
    an empty set — the same convention `test/conftest.py` follows for its
    routing-guard populations.

    The fixture names are read from the module's own constants rather than
    restated: a hardcoded pair would go on matching the OLD name after a rename,
    so the sweep would silently stop protecting the name it exists to protect
    while the rest of the module followed the rename.
    """
    bundles_root = PROJECT_ROOT / 'marketplace' / 'bundles'
    # This repository IS the marketplace, so the bundles tree is present in every
    # valid checkout. An absent tree is a broken checkout, not one this test does
    # not apply to — a skip would delete the collision sweep and still report the
    # run green.
    assert bundles_root.is_dir(), f'Marketplace bundles tree not found at {bundles_root}'
    fixture_names = {CANONICAL.name, VARIANT_HIGH.name}
    agent_files = list(bundles_root.rglob('agents/*.md'))
    assert agent_files, f'No production agent files found under {bundles_root}'
    collisions: list[Path] = []
    for agent_md in agent_files:
        if agent_md.name in fixture_names:
            collisions.append(agent_md)
    assert collisions == [], (
        f'POC fixture filenames collide with production agents: {collisions}'
    )
