# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``lane-frontmatter-invalid`` rule analyzer.

The analyzer walks every ``.md`` file under the marketplace bundles root and, for
each file that declares a ``lane:`` frontmatter block, validates the block against
the closed enums owned by
``plan-marshall:extension-api/standards/ext-point-lane-element.md``: a valid
``class``, a valid ``cost_size``, a ``prunable_when`` predicate when
``class: prunable``, and a valid ``tier`` (when present). It validates every block
that exists — it does NOT require an element to declare one.

Test layers:
  * Valid blocks (all four classes, both tier deviations) → no finding.
  * Missing / invalid ``class`` → finding.
  * Missing / invalid ``cost_size`` → finding.
  * ``class: prunable`` without ``prunable_when`` → finding.
  * Invalid ``tier`` → finding.
  * Files with no frontmatter, no ``lane:`` block, or a ``lane:`` only in the body
    (a code fence) → no finding.
  * Finding shape (rule_id / type / severity / line) and the suppression-key
    contract.
  * Absent tree → empty list.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_alf = _load_module('_analyze_lane_frontmatter', '_analyze_lane_frontmatter.py')

analyze_lane_frontmatter = _alf.analyze_lane_frontmatter
RULE_ID = _alf.RULE_ID
FINDING_TYPE = _alf.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundle_dir(tmp_path: Path) -> Path:
    """Create a synthetic skill directory under a marketplace-bundles root."""
    scoped = tmp_path / 'plan-marshall' / 'skills' / 'demo'
    scoped.mkdir(parents=True)
    return scoped


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding='utf-8')
    return path


def _frontmatter(lane_lines: str, *, extra: str = '') -> str:
    return f'---\n{lane_lines}name: default:demo\norder: 5\n{extra}---\n\n# Demo\n'


# ===========================================================================
# Valid blocks → no finding
# ===========================================================================


class TestValidLaneBlocks:
    """A well-formed lane: block produces no finding."""

    def test_core_minimal_block_is_valid(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: core\n  cost_size: XS\n'))
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_adversarial_with_explicit_tier_is_valid(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'b.md', _frontmatter('lane:\n  class: adversarial\n  tier: full\n  cost_size: L\n'))
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_prunable_with_predicate_is_valid(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(
            scoped / 'c.md',
            _frontmatter('lane:\n  class: prunable\n  tier: auto\n  prunable_when: no_code_delta\n  cost_size: L\n'),
        )
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_derived_state_block_is_valid(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'd.md', _frontmatter('lane:\n  class: derived-state\n  cost_size: XS\n'))
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_quoted_scalar_values_accepted(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'e.md', _frontmatter('lane:\n  class: "core"\n  cost_size: \'XXL\'\n'))
        assert analyze_lane_frontmatter(tmp_path) == []


# ===========================================================================
# Invalid blocks → finding
# ===========================================================================


class TestInvalidLaneBlocks:
    """A malformed lane: block produces exactly one finding per defect."""

    def test_missing_class_is_flagged(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  cost_size: M\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        assert 'class' in findings[0]['description']

    def test_invalid_class_is_flagged(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: bogus\n  cost_size: M\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        assert 'bogus' in findings[0]['description']

    def test_missing_cost_size_is_flagged(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: core\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        assert 'cost_size' in findings[0]['description']

    def test_invalid_cost_size_is_flagged(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: core\n  cost_size: HUGE\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        assert 'HUGE' in findings[0]['description']

    def test_invalid_tier_is_flagged(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: core\n  tier: maximal\n  cost_size: XS\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        assert 'tier' in findings[0]['description']

    def test_prunable_without_prunable_when_is_flagged(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: prunable\n  tier: auto\n  cost_size: L\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        assert 'prunable_when' in findings[0]['description']

    def test_multiple_defects_emit_multiple_findings(self, tmp_path: Path) -> None:
        """Missing class AND missing cost_size emit two findings for the one file."""
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  tier: full\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 2


# ===========================================================================
# Non-participating files → no finding
# ===========================================================================


class TestNonParticipatingFiles:
    """Files that declare no frontmatter lane: block are never flagged."""

    def test_file_without_frontmatter_is_ignored(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', '# Plain doc\n\nNo frontmatter here.\n')
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_frontmatter_without_lane_block_is_ignored(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', '---\nname: default:demo\norder: 5\n---\n\n# Demo\n')
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_lane_in_body_code_fence_is_not_frontmatter(self, tmp_path: Path) -> None:
        """A ``lane:`` example inside the body (not the leading frontmatter) is ignored."""
        scoped = _bundle_dir(tmp_path)
        _write(
            scoped / 'a.md',
            '# Doc\n\nExample block:\n\n```yaml\nlane:\n  class: bogus\n  cost_size: HUGE\n```\n',
        )
        assert analyze_lane_frontmatter(tmp_path) == []

    def test_recipe_lane_seed_block_is_skipped(self, tmp_path: Path) -> None:
        """A recipe lane SEED block (``profile:`` posture) is a different contract — not flagged.

        Recipe seeds share the ``lane:`` key but carry a ``profile`` posture (and
        optional ``steps:`` overrides) instead of the element ``class`` /
        ``cost_size`` schema. They are validated by the recipe-scoring reader, so
        the element-lane rule skips them rather than flagging a missing ``class``.
        """
        scoped = _bundle_dir(tmp_path)
        _write(
            scoped / 'recipe.md',
            '---\nname: recipe-demo\nlane:\n  profile: auto\n  steps:\n    sonar-roundtrip: off\n---\n',
        )
        assert analyze_lane_frontmatter(tmp_path) == []


# ===========================================================================
# Finding shape + scope guards
# ===========================================================================


class TestFindingShapeAndScope:
    """Finding contract, line attribution, suppression key, and absent-tree guard."""

    def test_finding_shape_and_suppression_key(self, tmp_path: Path) -> None:
        scoped = _bundle_dir(tmp_path)
        _write(scoped / 'a.md', _frontmatter('lane:\n  class: bogus\n  cost_size: XS\n'))
        findings = analyze_lane_frontmatter(tmp_path)
        assert len(findings) == 1
        finding = findings[0]
        # The rule_id is the suppression substrate's match key.
        assert finding['rule_id'] == RULE_ID == 'lane-frontmatter-invalid'
        assert finding['type'] == FINDING_TYPE
        assert finding['severity'] == 'error'
        assert finding['fixable'] is False
        assert finding['file'].endswith('a.md')

    def test_finding_line_points_at_lane_key(self, tmp_path: Path) -> None:
        """The finding line number points at the ``lane:`` frontmatter line."""
        scoped = _bundle_dir(tmp_path)
        # `lane:` is the second line of the file (after the opening `---`).
        _write(scoped / 'a.md', '---\nlane:\n  class: bogus\n  cost_size: XS\n---\n')
        findings = analyze_lane_frontmatter(tmp_path)
        assert findings[0]['line'] == 2

    def test_absent_tree_returns_empty_list(self, tmp_path: Path) -> None:
        missing = tmp_path / 'does-not-exist'
        assert analyze_lane_frontmatter(missing) == []
