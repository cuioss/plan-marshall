#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Regression tests for the create-pr title/body grounding.

These tests lock in the bug fixes shipped from the regression-defense angle —
each test asserts the *converged* behaviour the fix guarantees, so a future
revert re-breaks a named test here.
"""

from __future__ import annotations

from conftest import (
    MARKETPLACE_ROOT,
)

import pytest

_CREATE_PR_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'create-pr.md'


class TestCreatePrTitleAndBodyGrounding:
    """Regression pins for the create-pr.md deterministic-title corrections.

    Before this plan, create-pr.md passed an ungrounded ``--title "{title
    from request.md}"`` placeholder (no deterministic source) and read a dead
    ``--section summary`` (request.md has no such section). These pins fail
    against the pre-fix document and pass against the post-fix one.
    """

    def test_no_residual_ungrounded_title_placeholder(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        assert '{title from request.md}' not in text, (
            'create-pr.md must not carry the ungrounded {title from request.md} '
            'placeholder — the title is now bound from the persisted pr_title field.'
        )

    def test_title_bound_from_persisted_pr_title(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        assert 'manage-status metadata --get --field pr_title' in text or (
            'metadata' in text and '--get --field pr_title' in text
        ), (
            'create-pr.md must resolve the PR title via the canonical '
            'manage-status metadata --get --field pr_title read.'
        )
        assert '--title "{pr_title}"' in text, (
            'create-pr.md must pass the grounded --title "{pr_title}" to ci pr create.'
        )

    def test_body_reads_clarified_request_not_summary(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        assert '--section clarified_request' in text, (
            'create-pr.md body generation must read --section clarified_request.'
        )
        assert '--section summary' not in text, (
            'create-pr.md must not read the dead --section summary (request.md has no Summary section).'
        )


_STEP_3_5_HEADING = '#### Step 3.5:'
_STEP_3_6_HEADING = '#### Step 3.6:'
_STEP_4_HEADING = '#### Step 4:'


def _section(text: str, start_heading: str, end_heading: str) -> str:
    """Return the span of ``text`` from ``start_heading`` up to ``end_heading``.

    Both headings must be present and ordered, so a renamed or reordered
    heading fails the pin loudly instead of silently yielding an empty span.
    """
    start = text.find(start_heading)
    assert start != -1, f'create-pr.md is missing the {start_heading!r} heading.'
    end = text.find(end_heading, start + len(start_heading))
    assert end != -1, f'create-pr.md is missing the {end_heading!r} heading after {start_heading!r}.'
    return text[start:end]


class TestCreatePrTitleStalenessCheck:
    """Regression pins for the Step 3.5 pr_title staleness check.

    ``pr_title`` is authored once at phase-2-refine, before execute runs. Before
    this fix Step 3.5 bound it verbatim, so a PR whose scope shrank during
    execute shipped under a title naming work it no longer contained. These pins
    lock the re-read of the executed scope, the persisted re-derivation, and the
    audit line into Step 3.5 itself — the step that binds the title — so the
    check cannot drift to a later step that runs after the title was consumed.
    """

    def _step_3_5(self) -> str:
        return _section(_CREATE_PR_DOC.read_text(encoding='utf-8'), _STEP_3_5_HEADING, _STEP_3_6_HEADING)

    def test_step_3_5_reads_executed_deliverables(self):
        step = self._step_3_5()
        assert 'manage-solution-outline list-deliverables' in step, (
            'create-pr.md Step 3.5 must read the executed deliverable set via '
            'manage-solution-outline list-deliverables before trusting the refine-time pr_title.'
        )

    def test_step_3_5_behaviour_claims_need_executed_deliverables(self):
        step = self._step_3_5()
        assert '**Behaviour claims**' in step, 'create-pr.md Step 3.5 must name behaviour claims as a claim kind.'
        assert 'supported ONLY by the returned executed deliverable titles' in step, (
            'create-pr.md Step 3.5 must back a behaviour claim with the executed deliverables alone.'
        )
        assert '`{changed_files}` can NEVER vouch for a behaviour claim' in step, (
            'create-pr.md Step 3.5 must forbid {changed_files} from supporting a behaviour claim — '
            'a changed file does not prove every behaviour tied to it shipped.'
        )

    def test_step_3_5_changed_files_back_only_location_claims(self):
        step = self._step_3_5()
        assert '**File, component, or area claims**' in step, (
            'create-pr.md Step 3.5 must name file/component/area claims as a separate claim kind.'
        )
        assert 'EITHER an executed deliverable title OR the Step 1 `{changed_files}`' in step, (
            'create-pr.md Step 3.5 must let {changed_files} support file/component/area claims.'
        )

    @pytest.mark.parametrize(
        'retired_form',
        [
            'against BOTH the returned deliverable titles AND the Step 1 `{changed_files}`',
            'a component, behaviour, or area that no executed deliverable covers and no changed file touches',
        ],
        ids=['either-source-comparison', 'either-source-staleness-rule'],
    )
    def test_step_3_5_drops_the_unsplit_predicate(self, retired_form):
        assert retired_form not in self._step_3_5(), (
            'create-pr.md Step 3.5 must not keep the unsplit "deliverable titles OR changed files" '
            'predicate, which lets a changed file vouch for a dropped behaviour.'
        )

    def test_step_3_5_keeps_terse_title_is_not_stale_rule(self):
        assert 'terser or more general than the deliverable list is NOT stale' in self._step_3_5(), (
            'create-pr.md Step 3.5 must keep the rule that a terser or more general title is not stale.'
        )

    def test_step_3_5_persists_re_derived_title(self):
        step = self._step_3_5()
        assert '--set --field pr_title --value "{new_title}"' in step, (
            'create-pr.md Step 3.5 must persist a re-derived title via '
            'manage-status metadata --set --field pr_title so later readers see the shipped title.'
        )

    def test_step_3_5_logs_stale_title_decision(self):
        step = self._step_3_5()
        assert 'Stale pr_title re-derived' in step, (
            'create-pr.md Step 3.5 must record a decision-log line when the title is re-derived.'
        )
        assert 'old: {pr_title}' in step and 'new: {new_title}' in step, (
            'The stale-title decision-log line must name both the old and the new title.'
        )

    def test_step_4_still_passes_bound_pr_title(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        step_4 = _section(text, _STEP_4_HEADING, '### Log PR creation')
        assert '--title "{pr_title}"' in step_4, (
            'create-pr.md Step 4 must still pass --title "{pr_title}" — the (possibly re-derived) bound title.'
        )


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
