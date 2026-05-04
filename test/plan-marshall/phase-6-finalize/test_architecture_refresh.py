#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""End-to-end regression tests for the phase-6-finalize architecture-refresh standard.

The standard at ``standards/architecture-refresh.md`` is a markdown executor
playbook, not a Python module. These tests pin its decision flow contract by:

1. **Parsing the standard's pseudo-code summary** and re-implementing it as a
   pure decision function in this test module. The re-implementation is
   exercised across the full matrix:

      * Tier-0 ``enabled`` vs ``disabled``
      * Architecture-pre snapshot present vs absent (greenfield)
      * Diff detected vs empty (drift vs none)
      * Tier-1 dispatch knob (``prompt`` / ``auto`` / ``disabled``)
      * ``change_type`` shortcut for ``bug_fix`` / ``verification``

2. **Asserting the standard's narrative** documents every observable branch
   (greenfield, tier-0 disabled, empty diff, non-empty diff with each tier-1
   value, change_type shortcut) and emits the matching ``--display-detail``
   template per branch.

3. **Asserting registration** of ``architecture-refresh`` in
   ``standards/required-steps.md`` so the ``phase_steps_complete`` handshake
   enforces it whenever it is in ``manifest.phase_6.steps``.

4. **Asserting cross-references** are correct: the SKILL.md dispatch table
   resolves ``default:architecture-refresh`` to this standard, the standard
   declares its inline-dispatch contract, the phase-1-init Step 5d snapshot
   surface is named, and the manage-run-config tier-0/tier-1 knobs are
   referenced.

The functional behaviour of the underlying scripts (``architecture discover
--force``, ``diff-modules --pre``, ``manage-run-config architecture-refresh
get-tier-0/1``, etc.) is covered by their own bundle-scoped test suites; this
file pins ONLY the orchestration contract documented in the standard.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
from conftest import MARKETPLACE_ROOT  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Standards-doc paths (authoritative narrative surface).
# ---------------------------------------------------------------------------

_PHASE_6_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_PHASE_6_SKILL_MD = _PHASE_6_DIR / 'SKILL.md'
_ARCHITECTURE_REFRESH_MD = _PHASE_6_DIR / 'standards' / 'architecture-refresh.md'
_REQUIRED_STEPS_MD = _PHASE_6_DIR / 'standards' / 'required-steps.md'
_PHASE_1_INIT_SKILL_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-1-init' / 'SKILL.md'

# ---------------------------------------------------------------------------
# Bring the live ``_parse_required_steps`` helper onto the import path so the
# required-steps.md registration test exercises the same parser the
# ``phase_steps_complete`` invariant uses at runtime.
# ---------------------------------------------------------------------------

_PHASE_HANDSHAKE_SCRIPTS_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'scripts'
if str(_PHASE_HANDSHAKE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE_HANDSHAKE_SCRIPTS_DIR))

import _invariants as inv  # noqa: E402


# ===========================================================================
# Decision-flow re-implementation (mirrors the standard's pseudo-code).
#
# The architecture-refresh standard ends with a "Pseudo-Code Summary" section
# that is the authoritative procedural form of its decision tree. We mirror
# that summary here and exercise it across the full matrix below. If the
# narrative ever diverges from this re-implementation, the assertions in
# ``TestNarrativeContract`` will catch the drift on the markdown side and the
# parametric tests will catch it on the behavioural side.
# ===========================================================================


# Sentinel for "Tier 0 disabled — affected modules never computed".
_AFFECTED_UNKNOWN = object()


def _decide_architecture_refresh(
    *,
    snapshot_present: bool,
    tier_0: str,
    tier_1: str,
    change_type: str,
    diff_added: tuple[str, ...] = (),
    diff_removed: tuple[str, ...] = (),
    diff_changed: tuple[str, ...] = (),
    user_response: str | None = None,
) -> dict[str, Any]:
    """Pure re-implementation of the standard's pseudo-code summary.

    Returns a dict with keys:

      * ``branch``: the ``A``-``F`` branch identifier from "Step 5: Mark Step
        Complete" (greenfield / tier-0+tier-1 skipped / no diff / refresh only /
        refresh + enrich / refresh + PR note).
      * ``tier_0_committed``: True if the Tier-0 ``chore(architecture):
        refresh`` commit fires.
      * ``tier_1_action``: ``enrich`` / ``pr_note`` / ``skipped``.
      * ``affected_modules``: sorted union of diff buckets, or
        ``_AFFECTED_UNKNOWN`` when Tier 0 is disabled.
      * ``display_detail``: the ``--display-detail`` payload that the
        ``mark-step-done`` call MUST carry on this branch.
    """
    # -- Step 2: Greenfield handling ----------------------------------------
    if not snapshot_present:
        return {
            'branch': 'A',
            'tier_0_committed': False,
            'tier_1_action': 'skipped',
            'affected_modules': (),
            'display_detail': 'skipped (greenfield — no pre-snapshot)',
        }

    # -- Step 3: Tier 0 -----------------------------------------------------
    if tier_0 == 'enabled':
        affected_set = set(diff_added) | set(diff_removed) | set(diff_changed)
        affected: tuple[Any, ...] = tuple(sorted(affected_set))
        tier_0_committed = len(affected) > 0
    elif tier_0 == 'disabled':
        affected = _AFFECTED_UNKNOWN  # type: ignore[assignment]
        tier_0_committed = False
    else:
        raise ValueError(f'tier_0 must be enabled|disabled, got {tier_0!r}')

    # -- Step 4: Tier 1 -----------------------------------------------------
    # 4a. change_type shortcut
    if change_type in {'bug_fix', 'verification'}:
        if tier_0_committed:
            return {
                'branch': 'D',
                'tier_0_committed': True,
                'tier_1_action': 'skipped',
                'affected_modules': affected,
                'display_detail': (f'refreshed derived data ({len(affected)} modules)'),
            }
        # No tier-0 commit: empty diff or tier-0 disabled.
        if affected is _AFFECTED_UNKNOWN:
            return {
                'branch': 'B',
                'tier_0_committed': False,
                'tier_1_action': 'skipped',
                'affected_modules': _AFFECTED_UNKNOWN,
                'display_detail': 'tier-0 disabled; tier-1 skipped',
            }
        return {
            'branch': 'C',
            'tier_0_committed': False,
            'tier_1_action': 'skipped',
            'affected_modules': affected,
            'display_detail': 'no module structure changed',
        }

    # 4b. affected empty (Tier-0 enabled, empty diff)
    if affected is not _AFFECTED_UNKNOWN and len(affected) == 0:
        return {
            'branch': 'C',
            'tier_0_committed': False,
            'tier_1_action': 'skipped',
            'affected_modules': (),
            'display_detail': 'no module structure changed',
        }

    # 4c. affected unknown (Tier-0 disabled)
    if affected is _AFFECTED_UNKNOWN:
        return {
            'branch': 'B',
            'tier_0_committed': False,
            'tier_1_action': 'skipped',
            'affected_modules': _AFFECTED_UNKNOWN,
            'display_detail': 'tier-0 disabled; tier-1 skipped',
        }

    # 4d. tier_1 dispatch — affected is non-empty, tier-0 enabled, change_type
    # is not in the shortcut list.
    n = len(affected)
    if tier_1 == 'disabled':
        return {
            'branch': 'F',
            'tier_0_committed': True,
            'tier_1_action': 'pr_note',
            'affected_modules': affected,
            'display_detail': ('refreshed; re-enrichment deferred to PR note'),
        }
    if tier_1 == 'auto':
        return {
            'branch': 'E',
            'tier_0_committed': True,
            'tier_1_action': 'enrich',
            'affected_modules': affected,
            'display_detail': f'refreshed + re-enriched ({n} modules)',
        }
    if tier_1 == 'prompt':
        if user_response is None:
            raise ValueError('tier_1=prompt requires a user_response (Re-enrich now / Skip — note in PR).')
        if user_response == 'Re-enrich now':
            return {
                'branch': 'E',
                'tier_0_committed': True,
                'tier_1_action': 'enrich',
                'affected_modules': affected,
                'display_detail': f'refreshed + re-enriched ({n} modules)',
            }
        if user_response in ('Skip — note in PR', 'aborted'):
            return {
                'branch': 'F',
                'tier_0_committed': True,
                'tier_1_action': 'pr_note',
                'affected_modules': affected,
                'display_detail': ('refreshed; re-enrichment deferred to PR note'),
            }
        raise ValueError(f'unknown user_response: {user_response!r}')

    raise ValueError(f'tier_1 must be prompt|auto|disabled, got {tier_1!r}')


# ===========================================================================
# Greenfield handling — snapshot absent.
# ===========================================================================


class TestGreenfieldHandling:
    """Step 2 — greenfield short-circuit."""

    def test_no_snapshot_yields_branch_a_regardless_of_tier_settings(self):
        """A missing architecture-pre snapshot exits before reading tiers."""
        for tier_0 in ('enabled', 'disabled'):
            for tier_1 in ('prompt', 'auto', 'disabled'):
                result = _decide_architecture_refresh(
                    snapshot_present=False,
                    tier_0=tier_0,
                    tier_1=tier_1,
                    change_type='feature',
                )
                assert result['branch'] == 'A', (
                    f'Greenfield must yield Branch A even with tier_0={tier_0} tier_1={tier_1}, got {result}'
                )
                assert result['tier_0_committed'] is False
                assert result['tier_1_action'] == 'skipped'
                assert 'greenfield' in result['display_detail']

    def test_no_snapshot_short_circuits_for_change_type_shortcut(self):
        """Greenfield wins over the change_type shortcut — Step 2 runs first."""
        result = _decide_architecture_refresh(
            snapshot_present=False,
            tier_0='enabled',
            tier_1='auto',
            change_type='bug_fix',
        )
        assert result['branch'] == 'A'
        assert 'greenfield' in result['display_detail']


# ===========================================================================
# Tier 0 enabled — full diff matrix.
# ===========================================================================


class TestTier0EnabledMatrix:
    """Step 3 — deterministic discover + diff."""

    def test_empty_diff_yields_branch_c_no_commit(self):
        """No drift detected -> no commit, Tier 1 skipped, Branch C."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
        )
        assert result['branch'] == 'C'
        assert result['tier_0_committed'] is False
        assert result['tier_1_action'] == 'skipped'
        assert result['display_detail'] == 'no module structure changed'

    def test_drift_detected_in_added_bucket_triggers_commit(self):
        """Modules in `added` move to the union -> commit fires."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('mod-x',),
        )
        assert result['tier_0_committed'] is True
        assert result['affected_modules'] == ('mod-x',)

    def test_drift_detected_in_removed_bucket_triggers_commit(self):
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_removed=('mod-r',),
        )
        assert result['tier_0_committed'] is True
        assert 'mod-r' in result['affected_modules']

    def test_drift_detected_in_changed_bucket_triggers_commit(self):
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_changed=('mod-c',),
        )
        assert result['tier_0_committed'] is True
        assert 'mod-c' in result['affected_modules']

    def test_affected_modules_is_sorted_union_of_three_buckets(self):
        """Pseudo-code §3c: affected = added ∪ removed ∪ changed (sorted)."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('zeta',),
            diff_removed=('alpha',),
            diff_changed=('mu',),
        )
        # Sorted alphabetically across all three buckets.
        assert result['affected_modules'] == ('alpha', 'mu', 'zeta')

    def test_overlap_between_buckets_dedupes_in_union(self):
        """A module appearing in two buckets should count once in the union."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('shared',),
            diff_changed=('shared',),
        )
        assert result['affected_modules'] == ('shared',)


# ===========================================================================
# Tier 0 disabled — short-circuit semantics.
# ===========================================================================


class TestTier0DisabledMatrix:
    """Step 3a — Tier-0 disabled paths."""

    def test_tier_0_disabled_skips_commit_and_enters_tier_1_with_unknown(self):
        """Tier-0 disabled never commits; affected is sentinel UNKNOWN."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='disabled',
            tier_1='prompt',
            change_type='feature',
        )
        assert result['tier_0_committed'] is False
        assert result['affected_modules'] is _AFFECTED_UNKNOWN

    def test_tier_0_disabled_yields_branch_b_for_normal_change_types(self):
        """Tier 1 cannot proceed without a diff -> Branch B short-circuits."""
        for tier_1 in ('prompt', 'auto', 'disabled'):
            result = _decide_architecture_refresh(
                snapshot_present=True,
                tier_0='disabled',
                tier_1=tier_1,
                change_type='feature',
            )
            assert result['branch'] == 'B', f'Tier-0 disabled with tier_1={tier_1} must yield Branch B'
            assert result['display_detail'] == 'tier-0 disabled; tier-1 skipped'


# ===========================================================================
# Tier 1 dispatch knob — prompt / auto / disabled.
# ===========================================================================


class TestTier1KnobDispatch:
    """Step 4d — tier-1 knob dispatch with non-empty diff."""

    def test_tier_1_disabled_yields_branch_f_pr_note(self):
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='disabled',
            change_type='feature',
            diff_added=('mod-a',),
        )
        assert result['branch'] == 'F'
        assert result['tier_1_action'] == 'pr_note'
        assert result['display_detail'] == 'refreshed; re-enrichment deferred to PR note'

    def test_tier_1_auto_yields_branch_e_enrich(self):
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type='feature',
            diff_added=('m1',),
            diff_changed=('m2',),
        )
        assert result['branch'] == 'E'
        assert result['tier_1_action'] == 'enrich'
        assert result['display_detail'] == 'refreshed + re-enriched (2 modules)'

    def test_tier_1_prompt_accepted_routes_through_auto_branch(self):
        """`Re-enrich now` follows the auto branch verbatim."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
            diff_added=('mod-only',),
            user_response='Re-enrich now',
        )
        assert result['branch'] == 'E'
        assert result['tier_1_action'] == 'enrich'
        assert result['display_detail'] == 'refreshed + re-enriched (1 modules)'

    def test_tier_1_prompt_declined_routes_through_disabled_branch(self):
        """`Skip — note in PR` follows the disabled branch verbatim."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
            diff_added=('mod-x',),
            user_response='Skip — note in PR',
        )
        assert result['branch'] == 'F'
        assert result['tier_1_action'] == 'pr_note'

    def test_tier_1_prompt_aborted_treated_as_decline(self):
        """`AskUserQuestion aborted` is informationally equivalent to Skip."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='prompt',
            change_type='feature',
            diff_added=('mod-y',),
            user_response='aborted',
        )
        assert result['branch'] == 'F'
        assert result['tier_1_action'] == 'pr_note'

    def test_tier_1_prompt_requires_user_response_with_drift(self):
        """The standard documents `prompt` as default — caller must supply UX answer."""
        with pytest.raises(ValueError, match='user_response'):
            _decide_architecture_refresh(
                snapshot_present=True,
                tier_0='enabled',
                tier_1='prompt',
                change_type='feature',
                diff_added=('mod-z',),
            )


# ===========================================================================
# change_type shortcut — Step 4a.
# ===========================================================================


class TestChangeTypeShortcut:
    """Step 4a — bug_fix / verification skip Tier 1 even with drift."""

    @pytest.mark.parametrize('change_type', ['bug_fix', 'verification'])
    def test_shortcut_with_drift_runs_tier_0_only(self, change_type: str):
        """Drift -> tier-0 commit, but tier-1 is skipped per shortcut."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',  # would otherwise enrich
            change_type=change_type,
            diff_added=('mod-a',),
            diff_changed=('mod-b',),
        )
        assert result['branch'] == 'D'
        assert result['tier_0_committed'] is True
        assert result['tier_1_action'] == 'skipped'
        assert result['display_detail'] == ('refreshed derived data (2 modules)')

    @pytest.mark.parametrize('change_type', ['bug_fix', 'verification'])
    def test_shortcut_without_drift_yields_branch_c(self, change_type: str):
        """No drift + shortcut -> Branch C (no commit, tier-1 skipped)."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='enabled',
            tier_1='auto',
            change_type=change_type,
        )
        assert result['branch'] == 'C'
        assert result['tier_0_committed'] is False
        assert result['tier_1_action'] == 'skipped'

    @pytest.mark.parametrize('change_type', ['bug_fix', 'verification'])
    def test_shortcut_with_tier_0_disabled_yields_branch_b(
        self,
        change_type: str,
    ):
        """Shortcut + tier-0 disabled still yields tier-0-disabled branch."""
        result = _decide_architecture_refresh(
            snapshot_present=True,
            tier_0='disabled',
            tier_1='auto',
            change_type=change_type,
        )
        assert result['branch'] == 'B'
        assert result['display_detail'] == 'tier-0 disabled; tier-1 skipped'

    def test_other_change_types_run_tier_1_normally(self):
        """`feature`, `refactor`, etc. do NOT trigger the shortcut."""
        for change_type in ('feature', 'refactor', 'tech_debt', 'unknown'):
            result = _decide_architecture_refresh(
                snapshot_present=True,
                tier_0='enabled',
                tier_1='auto',
                change_type=change_type,
                diff_added=('mod-q',),
            )
            assert result['branch'] == 'E', f'change_type={change_type!r} must run tier-1 with auto knob'


# ===========================================================================
# required-steps.md registration — phase_steps_complete handshake contract.
# ===========================================================================


class TestRequiredStepsRegistration:
    """The `phase_steps_complete` invariant enforces this step's completion."""

    def test_architecture_refresh_listed_in_required_steps_md(self):
        steps = inv._parse_required_steps(_REQUIRED_STEPS_MD)
        assert 'architecture-refresh' in steps, (
            'architecture-refresh MUST be registered in required-steps.md so '
            'the phase_steps_complete handshake enforces it.'
        )

    def test_required_steps_md_uses_bare_step_name(self):
        """Bare step name (no `default:` prefix) — matches mark-step-done arg."""
        text = _REQUIRED_STEPS_MD.read_text(encoding='utf-8')
        assert '- architecture-refresh' in text
        assert '- default:architecture-refresh' not in text, (
            'required-steps.md uses bare names; the dispatcher adds the default: prefix at lookup time.'
        )

    def test_required_steps_parser_handles_canonical_format(self):
        """Smoke test — the live parser returns a non-empty list including ours."""
        steps = inv._parse_required_steps(_REQUIRED_STEPS_MD)
        assert isinstance(steps, list)
        assert len(steps) > 0
        # Sanity — the canonical finalize steps are also present.
        for canonical in ('commit-push', 'create-pr', 'archive-plan'):
            assert canonical in steps


# ===========================================================================
# Standard narrative contract — pin the documented decision tree on disk.
# ===========================================================================


class TestNarrativeContract:
    """The standard's prose surfaces every observable branch and template."""

    @pytest.fixture(scope='class')
    def standard_text(self) -> str:
        return _ARCHITECTURE_REFRESH_MD.read_text(encoding='utf-8')

    # ----- Inputs and tiers -------------------------------------------------

    def test_documents_run_config_inputs(self, standard_text: str):
        assert 'architecture_refresh.tier_0' in standard_text
        assert 'architecture_refresh.tier_1' in standard_text
        assert 'manage-run-config' in standard_text

    def test_documents_change_type_input(self, standard_text: str):
        assert 'change_type' in standard_text

    def test_documents_architecture_pre_snapshot_dependency(
        self,
        standard_text: str,
    ):
        assert 'architecture-pre' in standard_text
        assert 'phase-1-init' in standard_text, 'Standard must cite the phase-1-init Step 5d snapshot producer'

    # ----- Step 2: greenfield ----------------------------------------------

    def test_documents_greenfield_branch(self, standard_text: str):
        assert 'Greenfield' in standard_text
        assert 'skipped (greenfield' in standard_text

    # ----- Step 3: Tier 0 ---------------------------------------------------

    def test_documents_tier_0_disabled_branch(self, standard_text: str):
        assert 'Tier 0 skipped' in standard_text or 'tier_0 = disabled' in standard_text

    def test_documents_discover_force_call(self, standard_text: str):
        assert 'discover --force' in standard_text

    def test_documents_diff_modules_pre_call(self, standard_text: str):
        assert 'diff-modules' in standard_text
        assert '--pre' in standard_text

    def test_documents_empty_diff_no_commit_branch(self, standard_text: str):
        assert 'no module structure changed' in standard_text

    def test_documents_non_empty_diff_commit_message_template(
        self,
        standard_text: str,
    ):
        assert 'chore(architecture): refresh derived data after' in standard_text

    def test_documents_post_commit_push(self, standard_text: str):
        # Tier-0 commit + push, Tier-1 enrich + push — `git push` is documented
        # in both sections.
        assert standard_text.count('git -C {worktree_path} push') >= 2

    # ----- Step 4: Tier 1 ---------------------------------------------------

    def test_documents_change_type_shortcut(self, standard_text: str):
        assert 'bug_fix' in standard_text
        assert 'verification' in standard_text
        assert 'Tier 1 skipped' in standard_text

    def test_documents_tier_1_dispatch_modes(self, standard_text: str):
        assert '`disabled`' in standard_text
        assert '`auto`' in standard_text
        assert '`prompt`' in standard_text

    def test_documents_pr_note_branch(self, standard_text: str):
        assert 'Architecture re-enrichment recommended for' in standard_text
        assert 'append-body' in standard_text

    def test_documents_enrich_call_in_auto_branch(self, standard_text: str):
        """The `auto` branch enriches per-module, not via a batch invocation.

        After Phase F the standard explicitly forbids the (never-registered)
        `architecture enrich --modules {csv}` batch shape and instead
        documents a per-module loop that calls the three registered enrich
        subcommands. Pin every observable token of that contract so the
        narrative cannot silently drift back to the batch form.
        """
        assert 'architecture' in standard_text
        # The rewritten auto branch carries an explicit per-module loop.
        assert 'for each module' in standard_text, (
            'Standard must spell out the per-module iteration in the auto '
            'branch — the batch `enrich --modules {csv}` shape is gone.'
        )
        # All three registered enrich subcommands must be cited.
        assert 'architecture enrich module' in standard_text
        assert 'architecture enrich package' in standard_text
        assert 'architecture enrich skills-by-profile' in standard_text
        # The legacy batch literal MUST NOT reappear in the standard — it
        # named a verb that was never registered and prompted at least one
        # historical mis-execution. Guard against re-introduction.
        assert 'enrich --modules' not in standard_text, (
            'Standard must NOT cite `architecture enrich --modules {csv}` — '
            'this batch verb is not registered; the auto branch iterates '
            'modules and calls the per-module enrich subcommands instead.'
        )

    def test_documents_ask_user_question_prompt_options(
        self,
        standard_text: str,
    ):
        assert 'AskUserQuestion' in standard_text
        assert 'Re-enrich now' in standard_text
        assert 'Skip — note in PR' in standard_text

    # ----- Step 5: mark-step-done templates --------------------------------

    @pytest.mark.parametrize(
        'template',
        [
            'skipped (greenfield — no pre-snapshot)',
            'tier-0 disabled; tier-1 skipped',
            'no module structure changed',
            'refreshed derived data ({affected_module_count} modules)',
            'refreshed + re-enriched ({affected_module_count} modules)',
            'refreshed; re-enrichment deferred to PR note',
        ],
    )
    def test_documents_display_detail_template(
        self,
        standard_text: str,
        template: str,
    ):
        assert template in standard_text, f'Standard must document the display-detail template: {template!r}'

    def test_documents_six_branches_a_through_f(self, standard_text: str):
        for label in ('Branch A', 'Branch B', 'Branch C', 'Branch D', 'Branch E', 'Branch F'):
            assert label in standard_text, f'Standard must label {label} for renderer audit'

    def test_mark_step_done_uses_correct_phase_and_step(
        self,
        standard_text: str,
    ):
        """Every mark-step-done call MUST pass --phase 6-finalize --step architecture-refresh."""
        assert '--phase 6-finalize' in standard_text
        assert '--step architecture-refresh' in standard_text

    # ----- Error handling --------------------------------------------------

    def test_documents_error_handling_table(self, standard_text: str):
        # Documented failure modes (see Error Handling table).
        for marker in (
            'discover --force',
            'snapshot_not_found',
            'git push',
            'enrich',
        ):
            assert marker in standard_text, f'Error handling table must cover {marker!r}'

    # ----- Inline-execution contract ---------------------------------------

    def test_declares_inline_execution_contract(self, standard_text: str):
        """Tier-1 prompt mode requires AskUserQuestion -> step is inline."""
        text_lower = standard_text.lower()
        assert 'inline' in text_lower
        assert 'askuserquestion' in text_lower

    # ----- Pseudo-code summary ---------------------------------------------

    def test_includes_pseudo_code_summary(self, standard_text: str):
        """The authoritative procedural form must be present at the tail."""
        assert 'Pseudo-Code Summary' in standard_text
        # Spot-check the summary names every branch we unit-tested.
        assert 'tier_0' in standard_text
        assert 'tier_1' in standard_text
        assert 'affected' in standard_text


# ===========================================================================
# Cross-references — SKILL.md, phase-1-init, frontmatter wiring.
# ===========================================================================


class TestCrossReferences:
    @pytest.fixture(scope='class')
    def skill_md_text(self) -> str:
        return _PHASE_6_SKILL_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def standard_text(self) -> str:
        return _ARCHITECTURE_REFRESH_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def phase_1_text(self) -> str:
        return _PHASE_1_INIT_SKILL_MD.read_text(encoding='utf-8')

    def test_skill_md_dispatch_table_routes_default_architecture_refresh(
        self,
        skill_md_text: str,
    ):
        """The SKILL.md dispatch table must resolve default:architecture-refresh."""
        assert 'default:architecture-refresh' in skill_md_text
        assert 'standards/architecture-refresh.md' in skill_md_text

    def test_skill_md_lists_architecture_refresh_in_inline_only_steps(
        self,
        skill_md_text: str,
    ):
        """Tier-1 prompt mode means architecture-refresh runs inline (no Task agent)."""
        # The SKILL.md declares "Inline-only built-in steps" and lists names.
        assert 'architecture-refresh' in skill_md_text
        # No agent dispatch entry — it should NOT appear in the agent-suitable table.
        # Locate the agent-suitable section heading and verify our step is absent.
        section = skill_md_text.split('Agent-suitable built-in steps')[1]
        section_top = section.split('Inline-only built-in steps')[0]
        # The agent dispatch table should NOT mention architecture-refresh.
        assert 'architecture-refresh' not in section_top, (
            'architecture-refresh must NOT appear in the agent-suitable table; '
            'it requires AskUserQuestion and runs inline.'
        )

    def test_skill_md_standards_table_lists_architecture_refresh_row(
        self,
        skill_md_text: str,
    ):
        """The standards-table at the bottom of SKILL.md must mention the doc."""
        assert 'standards/architecture-refresh.md' in skill_md_text

    def test_standard_frontmatter_declares_default_name(
        self,
        standard_text: str,
    ):
        """Frontmatter `name:` must match the dispatch token after the prefix."""
        assert 'name: default:architecture-refresh' in standard_text

    def test_standard_frontmatter_declares_order(self, standard_text: str):
        """Frontmatter `order:` makes the manifest composer sort deterministically."""
        # The doc carries `order: 25` — pin it to detect accidental edits.
        assert 'order: 25' in standard_text

    def test_phase_1_init_produces_architecture_pre_snapshot(
        self,
        phase_1_text: str,
    ):
        """phase-1-init Step 5d must populate the input we consume."""
        assert 'architecture-pre' in phase_1_text

    def test_standard_cross_references_run_config_knobs(
        self,
        standard_text: str,
    ):
        """Cross-references section must cite manage-run-config as the knob source."""
        assert 'manage-run-config' in standard_text

    def test_standard_cross_references_required_steps(
        self,
        standard_text: str,
    ):
        """Cross-references must cite required-steps.md so the contract is discoverable."""
        assert 'required-steps.md' in standard_text


# ===========================================================================
# End-to-end matrix — combines all axes documented in the task description.
# ===========================================================================


# (snapshot_present, tier_0, tier_1, change_type, drift, expected_branch,
#  expected_display_detail_substring, user_response)
_MATRIX_CASES = [
    # snapshot absent — greenfield short-circuit.
    (False, 'enabled', 'prompt', 'feature', False, 'A', 'greenfield', None),
    (False, 'disabled', 'auto', 'bug_fix', True, 'A', 'greenfield', None),
    # tier-0 disabled — Branch B for any tier-1 setting.
    (True, 'disabled', 'prompt', 'feature', True, 'B', 'tier-0 disabled', None),
    (True, 'disabled', 'auto', 'feature', False, 'B', 'tier-0 disabled', None),
    (True, 'disabled', 'disabled', 'refactor', True, 'B', 'tier-0 disabled', None),
    # tier-0 enabled, no drift — Branch C.
    (True, 'enabled', 'prompt', 'feature', False, 'C', 'no module structure changed', None),
    (True, 'enabled', 'auto', 'feature', False, 'C', 'no module structure changed', None),
    # tier-0 enabled, drift, change_type shortcut — Branch D.
    (True, 'enabled', 'auto', 'bug_fix', True, 'D', 'refreshed derived data', None),
    (True, 'enabled', 'prompt', 'verification', True, 'D', 'refreshed derived data', None),
    # tier-0 enabled, drift, tier-1 auto — Branch E.
    (True, 'enabled', 'auto', 'feature', True, 'E', 'refreshed + re-enriched', None),
    # tier-0 enabled, drift, tier-1 prompt accepted — Branch E.
    (True, 'enabled', 'prompt', 'feature', True, 'E', 'refreshed + re-enriched', 'Re-enrich now'),
    # tier-0 enabled, drift, tier-1 disabled — Branch F.
    (True, 'enabled', 'disabled', 'feature', True, 'F', 'deferred to PR note', None),
    # tier-0 enabled, drift, tier-1 prompt declined — Branch F.
    (True, 'enabled', 'prompt', 'feature', True, 'F', 'deferred to PR note', 'Skip — note in PR'),
]


@pytest.mark.parametrize(
    ('snapshot_present, tier_0, tier_1, change_type, drift, expected_branch, expected_detail_substring, user_response'),
    _MATRIX_CASES,
)
def test_full_decision_matrix(
    snapshot_present: bool,
    tier_0: str,
    tier_1: str,
    change_type: str,
    drift: bool,
    expected_branch: str,
    expected_detail_substring: str,
    user_response: str | None,
) -> None:
    """End-to-end matrix sweep across every documented branch."""
    result = _decide_architecture_refresh(
        snapshot_present=snapshot_present,
        tier_0=tier_0,
        tier_1=tier_1,
        change_type=change_type,
        diff_added=('mod-x',) if drift else (),
        user_response=user_response,
    )
    assert result['branch'] == expected_branch, (
        f'Matrix row produced {result["branch"]} but expected {expected_branch}: '
        f'snapshot={snapshot_present} tier_0={tier_0} tier_1={tier_1} '
        f'change_type={change_type} drift={drift} -> {result}'
    )
    assert expected_detail_substring in result['display_detail'], (
        f'display_detail {result["display_detail"]!r} missing expected substring {expected_detail_substring!r}'
    )
