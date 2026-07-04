#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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

_CREATE_PR_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'create-pr.md'
)


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
            'create-pr.md must not read the dead --section summary (request.md has '
            'no Summary section).'
        )


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
