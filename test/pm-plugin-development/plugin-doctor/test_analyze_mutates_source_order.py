# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``mutates-source-step-post-merge-order`` rule analyzer.

The analyzer enforces the pre-merge source-edit pushability contract: a
finalize step declaring ``mutates_source: true`` must be ordered before the
merge gate (``default:branch-cleanup``), because a source edit written after
the feature branch is merged cannot be pushed onto that branch.

Test layers:
  * (a) Settle-band case — a source-mutating step ordered BEFORE the merge
        gate produces zero findings.
  * (b) Post-merge case — the same step ordered at or after the merge gate
        produces exactly one finding with the expected rule_id, severity, and
        line anchor.
  * (c) No-claim case — a step declaring no ``mutates_source`` key at a
        post-merge order produces zero findings (the discriminator requires an
        explicit source-mutation claim).
  * (d) Undiscoverable-merge-gate case — an absent ``default:branch-cleanup``
        record yields zero findings rather than raising.
  * (e) Live-tree assertion — the shipped marketplace corpus is clean.
"""

from pathlib import Path

from conftest import get_script_path, load_script_module

_amso = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_mutates_source_order.py',
    '_analyze_mutates_source_order',
)

analyze_mutates_source_order = _amso.analyze_mutates_source_order
RULE_ID = _amso.RULE_ID
FINDING_TYPE = _amso.FINDING_TYPE
RULE_NAME = _amso.RULE_NAME

_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

# The merge gate's order in every synthetic fixture below. The analyzer never
# hardcodes this value — it reads it back off the branch-cleanup record — so
# the fixture is free to choose any integer.
_MERGE_GATE_ORDER = 70


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step_doc_text(
    name: str, order: int, *, mutates_source: bool | None = None
) -> str:
    """Render a finalize-step doc's frontmatter + body.

    ``mutates_source=None`` omits the key entirely — the "makes no
    source-mutation claim" shape the rule treats as out of scope.
    """
    lines = ['---', f'name: {name}', f'order: {order}']
    if mutates_source is not None:
        lines.append(f'mutates_source: {str(mutates_source).lower()}')
    lines.extend(
        [
            f'description: Synthetic step {name}',
            'default_on: false',
            'presets: []',
            f'implements: {_EXT_POINT}',
            '---',
            '',
            f'# Step {name}',
            '',
        ]
    )
    return '\n'.join(lines)


def _order_line_number(text: str) -> int:
    """Return the 1-based line number of the ``order:`` key in a step doc."""
    for index, line in enumerate(text.splitlines(), start=1):
        if line.startswith('order:'):
            return index
    raise AssertionError('fixture step doc carries no order: line')


def _write_merge_gate(bundles_root: Path, order: int = _MERGE_GATE_ORDER) -> Path:
    """Write the ``default:branch-cleanup`` record the rule reads its threshold from."""
    standards = (
        bundles_root / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards'
    )
    standards.mkdir(parents=True, exist_ok=True)
    target = standards / 'branch-cleanup.md'
    target.write_text(_step_doc_text('default:branch-cleanup', order), encoding='utf-8')
    return target


def _write_bundle_step(
    bundles_root: Path,
    name: str,
    order: int,
    *,
    mutates_source: bool | None = None,
    bundle: str = 'test-bundle',
    skill: str = 'test-step',
) -> tuple[Path, str]:
    """Write a bundle finalize-step ``SKILL.md``; return ``(path, content)``."""
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = _step_doc_text(name, order, mutates_source=mutates_source)
    target = skill_dir / 'SKILL.md'
    target.write_text(content, encoding='utf-8')
    return target, content


# ===========================================================================
# (a) Settle-band case — pre-merge order is the correct shape
# ===========================================================================


class TestSettleBandOrdering:
    """A source-mutating step ordered before the merge gate is not flagged."""

    def test_mutating_step_before_merge_gate_produces_no_finding(
        self, tmp_path: Path
    ) -> None:
        """Arrange a mutating step at order 4; act; assert zero findings."""
        _write_merge_gate(tmp_path)
        _write_bundle_step(
            tmp_path, 'test-bundle:test-step', 4, mutates_source=True
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert findings == []

    def test_mutating_step_just_below_merge_gate_produces_no_finding(
        self, tmp_path: Path
    ) -> None:
        """The boundary is exclusive below: ``order == merge_gate - 1`` is clean."""
        _write_merge_gate(tmp_path)
        _write_bundle_step(
            tmp_path,
            'test-bundle:test-step',
            _MERGE_GATE_ORDER - 1,
            mutates_source=True,
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert findings == []


# ===========================================================================
# (b) Post-merge case — the flagged shape
# ===========================================================================


class TestPostMergeOrdering:
    """A source-mutating step ordered at/after the merge gate is flagged."""

    def test_mutating_step_after_merge_gate_produces_one_finding(
        self, tmp_path: Path
    ) -> None:
        """A post-merge mutating step yields exactly one correctly-shaped finding."""
        _write_merge_gate(tmp_path)
        step_path, content = _write_bundle_step(
            tmp_path, 'test-bundle:test-step', 996, mutates_source=True
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == FINDING_TYPE
        assert finding['rule'] == RULE_NAME
        assert finding['severity'] == 'error'
        assert finding['fixable'] is False
        assert finding['file'] == str(step_path)
        assert finding['line'] == _order_line_number(content)
        assert finding['details']['step_name'] == 'test-bundle:test-step'
        assert finding['details']['step_order'] == 996
        assert finding['details']['merge_gate_order'] == _MERGE_GATE_ORDER

    def test_mutating_step_at_merge_gate_order_produces_finding(
        self, tmp_path: Path
    ) -> None:
        """The boundary is inclusive at the gate: ``order == merge_gate`` is flagged.

        A step sharing the merge gate's order has no guaranteed ordering
        against it, so it cannot be relied on to run pre-merge.
        """
        _write_merge_gate(tmp_path)
        _write_bundle_step(
            tmp_path,
            'test-bundle:test-step',
            _MERGE_GATE_ORDER,
            mutates_source=True,
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['merge_gate_order'] == _MERGE_GATE_ORDER

    def test_merge_gate_order_is_read_not_hardcoded(self, tmp_path: Path) -> None:
        """Moving the merge gate moves the threshold with it.

        With the gate relocated to order 20, a step at order 30 — well below the
        conventional 70 — is post-merge and must be flagged. A hardcoded
        threshold would miss it.
        """
        _write_merge_gate(tmp_path, order=20)
        _write_bundle_step(
            tmp_path, 'test-bundle:test-step', 30, mutates_source=True
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['merge_gate_order'] == 20

    def test_project_local_step_is_in_scope(self, tmp_path: Path) -> None:
        """A project-local ``.claude/skills/finalize-step-*`` doc is scanned.

        The analyzer resolves the project-local tree as
        ``marketplace_root.parent.parent / '.claude' / 'skills'``, so the
        bundles root must sit at ``tmp_path/marketplace/bundles``.
        """
        bundles_root = tmp_path / 'marketplace' / 'bundles'
        bundles_root.mkdir(parents=True)
        _write_merge_gate(bundles_root)
        step_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-demo'
        step_dir.mkdir(parents=True)
        content = _step_doc_text(
            'project:finalize-step-demo', 996, mutates_source=True
        )
        (step_dir / 'SKILL.md').write_text(content, encoding='utf-8')

        findings = analyze_mutates_source_order(bundles_root)

        assert len(findings) == 1
        assert findings[0]['details']['step_name'] == 'project:finalize-step-demo'


# ===========================================================================
# (c) No-claim case — the out-of-scope shape
# ===========================================================================


class TestNoMutatesSourceClaim:
    """A step that makes no source-mutation claim is never flagged."""

    def test_step_without_mutates_source_key_produces_no_finding(
        self, tmp_path: Path
    ) -> None:
        """A post-merge step with no ``mutates_source`` key is out of scope."""
        _write_merge_gate(tmp_path)
        _write_bundle_step(tmp_path, 'test-bundle:test-step', 996)

        findings = analyze_mutates_source_order(tmp_path)

        assert findings == []

    def test_explicitly_false_mutates_source_produces_no_finding(
        self, tmp_path: Path
    ) -> None:
        """``mutates_source: false`` is a negative claim and is not flagged."""
        _write_merge_gate(tmp_path)
        _write_bundle_step(
            tmp_path, 'test-bundle:test-step', 996, mutates_source=False
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert findings == []

    def test_doc_without_ext_point_declaration_is_not_scanned(
        self, tmp_path: Path
    ) -> None:
        """Membership is declared: a doc omitting the ext-point is out of scope."""
        _write_merge_gate(tmp_path)
        skill_dir = tmp_path / 'test-bundle' / 'skills' / 'not-a-step'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            '---\nname: not-a-step\norder: 996\nmutates_source: true\n---\n',
            encoding='utf-8',
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert findings == []

    def test_commented_out_ext_point_declaration_is_not_scanned(
        self, tmp_path: Path
    ) -> None:
        """A commented-out ``implements:`` line does not pull the doc into scope.

        The membership test joins the frontmatter block before searching for the
        ext-point token; comment lines must be excluded from that join, matching
        the key-parsing loop that already skips them. The paired assertion on the
        uncommented form keeps this non-vacuous — the same doc with a live
        ``implements:`` line IS flagged.
        """
        _write_merge_gate(tmp_path)
        skill_dir = tmp_path / 'test-bundle' / 'skills' / 'commented-step'
        skill_dir.mkdir(parents=True)
        target = skill_dir / 'SKILL.md'
        live = _step_doc_text('test-bundle:commented-step', 996, mutates_source=True)
        commented = live.replace(
            f'implements: {_EXT_POINT}', f'# implements: {_EXT_POINT}'
        )
        target.write_text(commented, encoding='utf-8')

        assert analyze_mutates_source_order(tmp_path) == []

        target.write_text(live, encoding='utf-8')

        assert len(analyze_mutates_source_order(tmp_path)) == 1


# ===========================================================================
# (d) Undiscoverable merge gate — skip cleanly
# ===========================================================================


class TestUndiscoverableMergeGate:
    """Without a discoverable merge gate the rule skips rather than guessing."""

    def test_absent_branch_cleanup_record_yields_no_findings(
        self, tmp_path: Path
    ) -> None:
        """A synthetic marketplace with no merge gate returns [] and does not raise."""
        _write_bundle_step(
            tmp_path, 'test-bundle:test-step', 996, mutates_source=True
        )

        findings = analyze_mutates_source_order(tmp_path)

        assert findings == []

    def test_empty_marketplace_yields_no_findings(self, tmp_path: Path) -> None:
        """An empty tree is tolerated without raising."""
        assert analyze_mutates_source_order(tmp_path) == []


# ===========================================================================
# (e) Live-tree assertion — the shipped corpus is clean
# ===========================================================================


def test_real_marketplace_has_zero_findings() -> None:
    """The shipped marketplace declares no post-merge source-mutating step."""
    bundles_root = get_script_path(
        'pm-plugin-development',
        'plugin-doctor',
        '_analyze_mutates_source_order.py',
    ).parents[4]

    findings = analyze_mutates_source_order(bundles_root)

    assert findings == [], f'live tree produced findings: {findings}'


def test_real_marketplace_merge_gate_is_discoverable() -> None:
    """The live-tree assertion above is non-vacuous.

    ``analyze_mutates_source_order`` returns ``[]`` both for a clean tree and
    for a tree whose merge gate cannot be found. This guard pins the second
    case away: injecting a post-merge source-mutating step into the live tree's
    step set must produce a finding, which is only possible when the real
    ``default:branch-cleanup`` record was discovered and its order read.
    """
    bundles_root = get_script_path(
        'pm-plugin-development',
        'plugin-doctor',
        '_analyze_mutates_source_order.py',
    ).parents[4]

    steps = [
        _amso._parse_step_doc(path)
        for path in _amso._candidate_paths(bundles_root)
    ]
    merge_order = _amso._merge_gate_order([s for s in steps if s is not None])

    assert merge_order is not None, 'live tree merge gate must be discoverable'
    assert merge_order > 0
