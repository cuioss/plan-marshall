#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Consent-prompt distinction pins for unattended merge authorization.

Asserts the unattended-order prompt carries the distinct header and the
gap-class plus HEAD wording, separate from the blocking-question shape,
with grant and check routing unchanged.
"""

from _cmd_merge_authorization import (
    UNATTENDED_CONSENT_HEADER,
    format_unattended_consent_prompt,
)


def test_unattended_prompt_carries_distinct_header() -> None:
    """Prompt opens with the unattended-order header, not a bare question."""
    text = format_unattended_consent_prompt('pre-merge-consent', 'abc123', 'merge-action', 'operator yes')
    lines = text.splitlines()
    assert lines[0] == UNATTENDED_CONSENT_HEADER
    assert 'Unattended Order' in lines[0]


def test_unattended_prompt_prefix_names_gap_class_and_head() -> None:
    """Machine prefix names the gap class and HEAD it authorizes."""
    text = format_unattended_consent_prompt('pre-merge-consent', 'abc123', 'merge-action', 'operator yes')
    assert '[UNATTENDED-CONSENT gap-class=merge-action head=abc123 kind=pre-merge-consent]' in text
    assert 'merge-action' in text
    assert 'abc123' in text


def test_unattended_prompt_differs_from_blocking_question_shape() -> None:
    """Blocking-question prompts ask without the machine prefix or header."""
    blocking = 'Merge PR #42 now?'
    text = format_unattended_consent_prompt('pre-merge-consent', 'abc123', 'merge-action', 'operator yes')
    assert text != blocking
    assert '[UNATTENDED-CONSENT' in text
    assert '[UNATTENDED-CONSENT' not in blocking
