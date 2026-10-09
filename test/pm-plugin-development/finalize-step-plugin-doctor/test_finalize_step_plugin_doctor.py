# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for finalize-step-plugin-doctor skill directory extraction logic.

The finalize-step-plugin-doctor wrapper derives its gate scope from two reads —
the plan's realized footprint (``manage-references compute-footprint``) united
with the declared ``affected_files`` list — extracts skill directory paths from
that union, and passes them to ``plugin-doctor quality-gate --paths``.

Since the wrapper is a SKILL.md (not a Python script), this module validates the
documented derivation as pure Python functions: the regex extraction patterns
identify and deduplicate skill directories from file paths, the union keeps a
declared-but-untouched directory in scope, and the whole-tree triggers are
evaluated against the union rather than against either list alone — ahead of
both the skip-clean exit and scoped mode. The trigger set itself is parsed out
of the wrapper document and compared with the test-side definition, so the two
cannot drift apart silently.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT, get_skill_dir

_MARKETPLACE_PATTERN = re.compile(r'marketplace/bundles/[^/]+/skills/[^/]+')
_PROJECT_LOCAL_PATTERN = re.compile(r'\.claude/skills/[^/]+')

_WRAPPER_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-plugin-doctor' / 'SKILL.md'

# The planning-workflow docs whose documentation_only Verification citations
# use the scopeable `quality-gate --paths ... --marketplace-root` gate.
#
# phase-5-execute/SKILL.md is intentionally excluded: per ADR-004 documentation
# has no build owner, so the phase-5 derived ladder classifies a marketplace
# skill `.md` change to `none` (zero rungs) rather than a `docs-validate` rung
# that ran the plugin-doctor gate. phase-5-execute therefore no longer cites the
# `quality-gate --paths ... --marketplace-root` doc gate.
_PHASE_3_OUTLINE_DIR = get_skill_dir('plan-marshall', 'phase-3-outline')
_PLANNING_DOCS = (
    _PHASE_3_OUTLINE_DIR / 'standards' / 'outline-workflow-detail.md',
    _PHASE_3_OUTLINE_DIR / 'SKILL.md',
)

# default:push resolves to order 11 in the phase-6-finalize seed; the
# wrapper MUST gate before it.
_PUSH_ORDER = 11


def _read_frontmatter_order(skill_md: Path) -> int:
    """Parse the integer `order:` field from a SKILL.md YAML frontmatter block."""
    content = skill_md.read_text(encoding='utf-8')
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    assert fm_match, f'No YAML frontmatter found in {skill_md}'
    order_match = re.search(r'^order:\s*(\d+)\s*$', fm_match.group(1), re.MULTILINE)
    assert order_match, f'No `order:` field in {skill_md} frontmatter'
    return int(order_match.group(1))


def _step5_gate_block(content: str) -> str:
    """Return the Step 5 gate block of the wrapper SKILL.md.

    Anchored from the `### Step 5` heading to the next `## ` (or `### Step`)
    heading so an enumeration mention elsewhere in the doc cannot false-trip
    the gate-operation assertions.
    """
    start = content.find('### Step 5')
    assert start != -1, 'Wrapper SKILL.md should declare a Step 5 gate section'
    rest = content[start + len('### Step 5') :]
    end_candidates = [pos for pos in (rest.find('\n## '), rest.find('\n### Step 6')) if pos != -1]
    end = min(end_candidates) if end_candidates else len(rest)
    return rest[:end]


def extract_skill_dirs(modified_files: list[str]) -> list[str]:
    """Extract unique skill directory paths from a list of modified files.

    Applies two regex patterns:
    - ``marketplace/bundles/{bundle}/skills/{skill}`` for marketplace skills
    - ``.claude/skills/{skill}`` for project-local skills

    Returns a sorted, deduplicated list of skill directory paths.
    """
    dirs: set[str] = set()
    for path in modified_files:
        m = _MARKETPLACE_PATTERN.search(path)
        if m:
            dirs.add(m.group(0))
            continue
        m = _PROJECT_LOCAL_PATTERN.search(path)
        if m:
            dirs.add(m.group(0))
    return sorted(dirs)


# The whole-tree trigger patterns the mode-selection predicate below matches
# against. Two families: F1 (any changed file of the plugin-doctor / plan-doctor
# skills, whose rules re-classify skills the diff never touched) and verdict-input (a
# file outside every skill directory whose content the gate's verdict reads).
#
# This tuple is the test-side definition. TestTriggerSetMatchesWrapperDocument
# pins it to the trigger table in Step 2.5 of the wrapper document in both
# directions, so a pattern added to either side alone turns that test red.
_WHOLE_TREE_TRIGGER_PATTERNS = (
    'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**',
    'marketplace/bundles/plan-marshall/skills/plan-doctor/**',
    'marketplace/targets/*/__init__.py',
    'marketplace/bundles/*/.claude-plugin/plugin.json',
    'marketplace/bundles/*/agents/*.md',
    'marketplace/bundles/*/commands/*.md',
    '**/CLAUDE.md',
    '**/AGENTS.md',
)

_GATE_MODE_WHOLE_TREE = 'whole-tree'
_GATE_MODE_SCOPED = 'scoped'
_GATE_MODE_SKIP_CLEAN = 'skip-clean'


def _trigger_pattern_regex(pattern: str) -> re.Pattern[str]:
    """Compile a trigger pattern under the matching rule Step 2.5 states.

    ``*`` matches within one path segment; ``**`` matches any run of segments,
    including none.
    """
    segments = pattern.split('/')
    parts: list[str] = []
    for index, segment in enumerate(segments):
        is_last = index == len(segments) - 1
        if segment == '**':
            parts.append('.*' if is_last else '(?:[^/]+/)*')
            continue
        parts.append(re.escape(segment).replace(r'\*', '[^/]*'))
        if not is_last:
            parts.append('/')
    return re.compile(''.join(parts))


def gate_scope(realized_footprint: list[str], declared_files: list[str]) -> list[str]:
    """Return the wrapper's gate scope: realized footprint ∪ declared files.

    Mirrors Step 1 of the wrapper document. Both operands are required — the
    documented indeterminate branch covers a failed read, which is not modelled
    here because a missing operand yields no union at all.
    """
    return sorted(set(realized_footprint) | set(declared_files))


def whole_tree_trigger_fires(scope: list[str], patterns: tuple[str, ...] = _WHOLE_TREE_TRIGGER_PATTERNS) -> bool:
    """Return whether any scope entry matches a whole-tree trigger pattern."""
    compiled = [_trigger_pattern_regex(pattern) for pattern in patterns]
    return any(regex.fullmatch(path) for path in scope for regex in compiled)


def select_gate_mode(scope: list[str]) -> str:
    """Return the mode Step 2.5 selects for a scope formed from two successful reads.

    The trigger is evaluated first, ahead of both the skip-clean exit and scoped
    mode. The indeterminate-read mode is not modelled: it needs a failed read,
    and a failed read yields no scope to pass in.
    """
    if whole_tree_trigger_fires(scope):
        return _GATE_MODE_WHOLE_TREE
    if extract_skill_dirs(scope):
        return _GATE_MODE_SCOPED
    return _GATE_MODE_SKIP_CLEAN


def _step2_5_block(content: str) -> str:
    """Return the Step 2.5 section of the wrapper SKILL.md, up to the Step 3 heading."""
    start = content.find('### Step 2.5')
    assert start != -1, 'Wrapper SKILL.md should declare a Step 2.5 mode-selection section'
    end = content.find('\n### Step 3', start)
    assert end != -1, 'Wrapper SKILL.md should declare a Step 3 section after Step 2.5'
    return content[start:end]


def documented_trigger_patterns(content: str) -> list[str]:
    """Parse the whole-tree trigger patterns out of the Step 2.5 trigger table.

    The table is located by its ``| Trigger pattern |`` header row; every body
    row contributes the backticked pattern in its first cell. A body row whose
    first cell is not exactly one backticked span fails the parse rather than
    being skipped, so a malformed row cannot silently shrink the parsed set.
    """
    lines = _step2_5_block(content).splitlines()
    header_indexes = [index for index, line in enumerate(lines) if line.startswith('| Trigger pattern |')]
    assert len(header_indexes) == 1, (
        f'Step 2.5 must hold exactly one `| Trigger pattern |` table, found {len(header_indexes)}'
    )
    patterns: list[str] = []
    # +2 skips the header row and the `|---|` separator row beneath it.
    for line in lines[header_indexes[0] + 2 :]:
        if not line.startswith('|'):
            break
        first_cell = line.split('|')[1].strip()
        cell_match = re.fullmatch(r'`([^`]+)`', first_cell)
        assert cell_match, f'Trigger table row has no single backticked pattern in its first cell: {line!r}'
        patterns.append(cell_match.group(1))
    return patterns


def _step1_scope_block(content: str) -> str:
    """Return the Step 1 section of the wrapper SKILL.md, up to the Step 2 heading."""
    start = content.find('### Step 1')
    assert start != -1, 'Wrapper SKILL.md should declare a Step 1 scope section'
    end = content.find('\n### Step 2', start)
    assert end != -1, 'Wrapper SKILL.md should declare a Step 2 section after Step 1'
    return content[start:end]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMarketplaceSkillChanges:
    """Scenario 1: modified_files containing only marketplace skill paths."""

    def test_extracts_skill_dirs_from_marketplace_paths(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/SKILL.md',
            'marketplace/bundles/pm-dev-java/skills/bar/standards/x.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            'marketplace/bundles/plan-marshall/skills/foo',
            'marketplace/bundles/pm-dev-java/skills/bar',
        ]


class TestProjectLocalSkillChanges:
    """Scenario 2: modified_files containing only project-local skill paths."""

    def test_extracts_skill_dirs_from_project_local_paths(self):
        modified_files = [
            '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            '.claude/skills/finalize-step-plugin-doctor',
        ]


class TestMixedSkillChanges:
    """Scenario 3: both marketplace and project-local skill paths."""

    def test_extracts_both_marketplace_and_project_local(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md',
            '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
            'marketplace/bundles/pm-dev-java/skills/junit-core/standards/patterns.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            '.claude/skills/finalize-step-plugin-doctor',
            'marketplace/bundles/plan-marshall/skills/phase-5-execute',
            'marketplace/bundles/pm-dev-java/skills/junit-core',
        ]


class TestNoSkillChanges:
    """Scenario 4: modified_files with no skill-related paths."""

    def test_returns_empty_for_non_skill_paths(self):
        modified_files = [
            'test/foo.py',
            '.plan/marshal.json',
            'README.md',
            'marketplace/bundles/plan-marshall/README.md',
            'marketplace/bundles/plan-marshall/agents/some-agent.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == []


class TestDeduplication:
    """Scenario 5: multiple files in the same skill directory."""

    def test_deduplicates_same_skill_dir(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/foo/standards/bar.md',
            'marketplace/bundles/plan-marshall/skills/foo/scripts/baz.py',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            'marketplace/bundles/plan-marshall/skills/foo',
        ]

    def test_deduplicates_project_local_same_dir(self):
        modified_files = [
            '.claude/skills/my-skill/SKILL.md',
            '.claude/skills/my-skill/standards/rules.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            '.claude/skills/my-skill',
        ]


# ---------------------------------------------------------------------------
# Gate scope: realized footprint united with the declared list
# ---------------------------------------------------------------------------


class TestGateScopeUnion:
    """The gate covers what the plan changed AND what it declared."""

    def test_union_gates_declared_and_realized_skill_dirs(self):
        # Arrange
        declared_files = [
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md',
        ]
        realized_footprint = [
            '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
        ]

        # Act
        result = extract_skill_dirs(gate_scope(realized_footprint, declared_files))

        # Assert
        assert result == [
            '.claude/skills/finalize-step-plugin-doctor',
            'marketplace/bundles/plan-marshall/skills/extension-api',
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize',
        ]

    def test_declared_list_alone_misses_the_realized_only_skill_dir(self):
        """Negative control: the pre-union scope does not contain the third directory."""
        # Arrange
        declared_files = [
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md',
        ]

        # Act
        result = extract_skill_dirs(declared_files)

        # Assert
        assert '.claude/skills/finalize-step-plugin-doctor' not in result
        assert len(result) == 2

    def test_union_deduplicates_a_path_present_in_both_reads(self):
        # Arrange
        shared = 'marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md'

        # Act
        result = gate_scope([shared], [shared])

        # Assert
        assert result == [shared]


class TestF1TriggerOverUnion:
    """The F1 whole-tree trigger is evaluated against the union."""

    def test_trigger_fires_when_rule_script_is_in_realized_set_only(self):
        # Arrange
        declared_files = ['marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md']
        realized_footprint = [
            'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py',
        ]

        # Act
        fires_on_union = whole_tree_trigger_fires(gate_scope(realized_footprint, declared_files))
        fires_on_declared_alone = whole_tree_trigger_fires(declared_files)

        # Assert
        assert fires_on_union
        assert not fires_on_declared_alone

    def test_trigger_fires_for_plan_doctor_path(self):
        # Arrange
        scope = gate_scope(['marketplace/bundles/plan-marshall/skills/plan-doctor/scripts/plan_doctor.py'], [])

        # Act / Assert
        assert whole_tree_trigger_fires(scope)

    def test_trigger_does_not_fire_without_a_rule_script(self):
        # Arrange
        scope = gate_scope(
            ['.claude/skills/finalize-step-plugin-doctor/SKILL.md'],
            ['marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md'],
        )

        # Act / Assert
        assert not whole_tree_trigger_fires(scope)


_VERDICT_INPUT_ONLY_UNIONS = (
    pytest.param(['marketplace/targets/claude/__init__.py'], id='targets-init-only'),
    pytest.param(['marketplace/bundles/plan-marshall/.claude-plugin/plugin.json'], id='bundle-plugin-json-only'),
    pytest.param(['CLAUDE.md'], id='root-claude-md-only'),
    pytest.param(['AGENTS.md'], id='root-agents-md-only'),
    pytest.param(['doc/developer/CLAUDE.md'], id='nested-claude-md-only'),
)

_UNRELATED_NON_SKILL_UNIONS = (
    pytest.param(['README.md', 'doc/developer/build.adoc', 'test/conftest.py'], id='docs-and-tests'),
    pytest.param(['marketplace/targets/sync.py'], id='targets-root-module'),
    pytest.param(['marketplace/targets/claude/adapter.py'], id='target-package-non-init'),
    pytest.param(['marketplace/targets/claude/sub/__init__.py'], id='nested-init-below-a-target-package'),
    pytest.param(['marketplace/bundles/plan-marshall/README.md'], id='bundle-readme'),
    pytest.param(['marketplace/bundles/plan-marshall/.claude-plugin/other.json'], id='other-manifest-dir-file'),
    pytest.param(['marketplace/bundles/plan-marshall/agents/plugin.json'], id='plugin-json-outside-manifest-dir'),
    pytest.param(['doc/NOT-CLAUDE.md', 'doc/CLAUDE.md.bak'], id='agent-file-near-miss-names'),
)


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        ('marketplace/bundles/plan-marshall/agents/execution-context.md', _GATE_MODE_WHOLE_TREE),
        ('marketplace/bundles/pm-dev-java/commands/java-create.md', _GATE_MODE_WHOLE_TREE),
        ('marketplace/bundles/plan-marshall/agents/nested/deeper.md', _GATE_MODE_SKIP_CLEAN),
        ('marketplace/bundles/plan-marshall/agents/notes.txt', _GATE_MODE_SKIP_CLEAN),
        ('doc/agents/overview.md', _GATE_MODE_SKIP_CLEAN),
    ],
    ids=['bundle-agent', 'bundle-command', 'nested-below-agents', 'non-markdown', 'agents-dir-outside-bundles'],
)
def test_bundle_component_file_alone_in_the_union_selects_its_mode(path: str, expected: str) -> None:
    """A bundle agent or command is a verdict input; a look-alike path is not."""
    assert select_gate_mode([path]) == expected


class TestVerdictInputTriggerOverUnion:
    """A non-skill file the gate's verdict reads selects whole-tree, never a skip."""

    @pytest.mark.parametrize('realized_footprint', _VERDICT_INPUT_ONLY_UNIONS)
    def test_verdict_input_alone_selects_whole_tree_and_not_skip_clean(self, realized_footprint):
        # Arrange
        scope = gate_scope(realized_footprint, [])

        # Act
        mode = select_gate_mode(scope)

        # Assert
        assert extract_skill_dirs(scope) == [], 'the union must name no skill, or the case proves nothing'
        assert mode == _GATE_MODE_WHOLE_TREE
        assert mode != _GATE_MODE_SKIP_CLEAN

    @pytest.mark.parametrize('realized_footprint', _VERDICT_INPUT_ONLY_UNIONS)
    def test_verdict_input_beside_an_unrelated_skill_preempts_scoped_mode(self, realized_footprint):
        # Arrange
        declared_files = ['marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md']

        # Act
        with_trigger = select_gate_mode(gate_scope(realized_footprint, declared_files))
        without_trigger = select_gate_mode(gate_scope([], declared_files))

        # Assert
        assert with_trigger == _GATE_MODE_WHOLE_TREE
        assert without_trigger == _GATE_MODE_SCOPED

    @pytest.mark.parametrize('realized_footprint', _UNRELATED_NON_SKILL_UNIONS)
    def test_unrelated_non_skill_files_still_take_skip_clean(self, realized_footprint):
        # Arrange
        scope = gate_scope(realized_footprint, [])

        # Act
        mode = select_gate_mode(scope)

        # Assert
        assert not whole_tree_trigger_fires(scope)
        assert mode == _GATE_MODE_SKIP_CLEAN

    def test_trigger_fires_when_verdict_input_is_in_declared_list_only(self):
        # Arrange
        realized_footprint = ['README.md']
        declared_files = ['marketplace/bundles/pm-dev-java/.claude-plugin/plugin.json']

        # Act
        fires_on_union = whole_tree_trigger_fires(gate_scope(realized_footprint, declared_files))
        fires_on_realized_alone = whole_tree_trigger_fires(realized_footprint)

        # Assert
        assert fires_on_union
        assert not fires_on_realized_alone


class TestTriggerSetMatchesWrapperDocument:
    """The test-side trigger set and the Step 2.5 trigger table are the same set."""

    def test_documented_and_test_side_trigger_sets_are_equal_in_both_directions(self):
        # Arrange
        documented = documented_trigger_patterns(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Act
        documented_only = sorted(set(documented) - set(_WHOLE_TREE_TRIGGER_PATTERNS))
        test_side_only = sorted(set(_WHOLE_TREE_TRIGGER_PATTERNS) - set(documented))

        # Assert
        assert documented, 'Step 2.5 must name at least one whole-tree trigger pattern'
        assert documented_only == [], (
            f'Step 2.5 names trigger pattern(s) the test-side definition lacks: {documented_only}'
        )
        assert test_side_only == [], (
            f'the test-side definition holds pattern(s) Step 2.5 does not name: {test_side_only}'
        )

    def test_neither_side_repeats_a_pattern(self):
        # Arrange
        documented = documented_trigger_patterns(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert len(documented) == len(set(documented)), 'the Step 2.5 trigger table repeats a pattern'
        assert len(_WHOLE_TREE_TRIGGER_PATTERNS) == len(set(_WHOLE_TREE_TRIGGER_PATTERNS))

    def test_parser_reports_a_pattern_added_to_the_document_only(self):
        """Control: the comparison is not vacuous — a document-only row is seen."""
        # Arrange
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        existing_row = '| `**/AGENTS.md` |'
        assert content.count(existing_row) == 1, 'the control needs exactly one anchor row to extend'
        extended = content.replace(existing_row, '| `doc/**/extra.md` | verdict-input | control |\n' + existing_row)

        # Act
        documented = documented_trigger_patterns(extended)

        # Assert
        assert set(documented) - set(_WHOLE_TREE_TRIGGER_PATTERNS) == {'doc/**/extra.md'}

    def test_every_documented_pattern_selects_whole_tree_for_a_matching_path(self):
        """Each parsed pattern, compiled under the documented rule, matches a concrete path."""
        # Arrange
        documented = documented_trigger_patterns(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Act
        unmatched = [
            pattern
            for pattern in documented
            if not whole_tree_trigger_fires([pattern.replace('**', 'a/b').replace('*', 'x')], (pattern,))
        ]

        # Assert
        assert unmatched == []


class TestStep1NamesBothReads:
    """Step 1 of the wrapper document names both reads and their union."""

    def test_step1_names_compute_footprint_with_both_flags(self):
        # Arrange
        block = _step1_scope_block(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert 'manage-references compute-footprint' in block
        assert '--plan-id {plan_id} --worktree-path {worktree_path}' in block

    def test_step1_names_the_declared_affected_files_read(self):
        # Arrange
        block = _step1_scope_block(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert '--field affected_files' in block

    def test_step1_states_the_scope_is_the_union(self):
        # Arrange
        block = _step1_scope_block(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert 'union' in block, 'Step 1 must state that the gate scope is the union of the two reads'

    def test_f1_trigger_and_skip_clean_are_stated_against_the_union(self):
        # Arrange
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        step_2_5 = content[content.find('### Step 2.5') : content.find('### Step 3')]
        step_3 = content[content.find('### Step 3') : content.find('### Step 4')]

        # Assert
        assert step_2_5 and step_3, 'Steps 2.5 and 3 must both be locatable in the wrapper document'
        assert 'Step 1 union' in step_2_5, 'the F1 trigger must be evaluated against the Step 1 union'
        assert 'union' in step_3, 'the skip-clean exit must be stated against the union'


# ---------------------------------------------------------------------------
# Scopeable rule-running gate + ordering regression (D7)
# ---------------------------------------------------------------------------


class TestRuleRunningScopeableGate:
    """The wrapper's Step 5 gate uses the scopeable rule-running quality-gate."""

    def test_step5_uses_quality_gate_with_paths_and_marketplace_root(self):
        """Step 5 invokes `quality-gate` with both `--paths` and `--marketplace-root`."""
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        block = _step5_gate_block(content)
        assert 'quality-gate' in block, 'Step 5 must invoke the quality-gate verb'
        assert '--paths' in block, 'Step 5 quality-gate must scope via --paths'
        assert '--marketplace-root' in block, 'Step 5 quality-gate must pass --marketplace-root'

    def test_step5_does_not_use_noop_enumerate_verb_as_gate(self):
        """Step 5 does NOT use the rule-less `scan`/`list-components` as the gate."""
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        block = _step5_gate_block(content)
        # The gate operation must be quality-gate, never a bare enumerate verb.
        assert 'doctor-marketplace \\\n  scan' not in block and 'doctor-marketplace scan' not in block, (
            'Step 5 must not use the rule-less `scan` subcommand as the gate'
        )
        assert 'list-components --paths' not in block, 'Step 5 must not use the rule-less `list-components` as the gate'


class TestGateOrderingBeforePush:
    """The wrapper is ordered before default:push (order 11)."""

    def test_order_strictly_precedes_push(self):
        order = _read_frontmatter_order(_WRAPPER_SKILL_MD)
        assert order < _PUSH_ORDER, (
            f'finalize-step-plugin-doctor order={order} must be < default:push '
            f'order={_PUSH_ORDER} so structural lint gates before push'
        )


class TestPlanningDocCitations:
    """The planning-workflow docs cite the scopeable rule-running gate, not bare scan."""

    def test_no_bare_scan_paths_documentation_verification_citation(self):
        """No planning doc cites `doctor-marketplace scan --paths` as a verification gate."""
        for doc in _PLANNING_DOCS:
            content = doc.read_text(encoding='utf-8')
            assert 'doctor-marketplace scan --paths' not in content, (
                f'{doc} still cites the rule-less `scan --paths` as a verification gate'
            )
            assert 'doctor-marketplace list-components --paths' not in content, (
                f'{doc} cites `list-components --paths` as a verification gate (rule-less enumerate verb)'
            )

    def test_corrected_quality_gate_paths_shape_present(self):
        """Each planning doc cites the corrected `quality-gate --paths ... --marketplace-root` shape."""
        for doc in _PLANNING_DOCS:
            content = doc.read_text(encoding='utf-8')
            assert 'quality-gate --paths' in content and '--marketplace-root' in content, (
                f'{doc} should cite the scopeable `quality-gate --paths ... --marketplace-root` gate'
            )
