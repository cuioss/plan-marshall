#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Line-budget backstop rule for always-on agentfiles.

Implements the ``agentfile-line-count-over-budget`` analyze-surfaced rule: an
always-on agentfile (``CLAUDE.md`` at any nesting level, ``AGENTS.md``) whose
total line count exceeds the always-on line budget is a strong proxy signal for
accumulated bloat and a prompt to re-classify its sections.

The budget threshold and its rationale live in the shared rubric
(``plan-marshall:ref-agentfile-hygiene`` ``standards/rubric.md`` § "Always-on
line budget"), which sets a single configurable default applied across all
agentfile types. ``DEFAULT_LINE_BUDGET`` mirrors that default; callers may pass
a different ``budget`` to tune the threshold without editing the rule.

Build-failing under ``quality-gate``: this rule runs in both
``doctor-marketplace.py quality-gate`` (via ``RuleRunner.run_quality_gate``) and
``analyze``. An always-on agentfile that drifts over budget regresses the build,
so the rubric's line budget is enforced, not merely an advisory backstop.

Public API
----------
- ``analyze_agentfile_line_budget(marketplace_root, budget=DEFAULT_LINE_BUDGET)``
"""

from __future__ import annotations

from pathlib import Path

from _analyze_agentfile_shared import (
    count_lines,
    discover_agentfiles,
    read_text_or_none,
    repo_root_from_marketplace_root,
)
from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'agentfile-line-count-over-budget'
RULE_NAME = 'analyze_agentfile_line_budget'

# Build-failing agentfile-hygiene backstop (enforced under quality-gate).
RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='content',
    scope='file-local',
)

# Single configurable default budget (lines). Source: the rubric's "Always-on
# line budget" section — an agentfile SHOULD stay at or under this many lines.
DEFAULT_LINE_BUDGET = 200


def analyze_agentfile_line_budget(
    marketplace_root: str | Path,
    budget: int = DEFAULT_LINE_BUDGET,
) -> list[dict]:
    """Flag every always-on agentfile whose line count exceeds ``budget``.

    Parameters
    ----------
    marketplace_root:
        The ``bundles/`` marketplace root (as returned by
        ``find_marketplace_root``). Agentfile discovery anchors at the repo
        root derived from it.
    budget:
        The always-on line budget. An agentfile with strictly more lines than
        ``budget`` produces one finding. Defaults to ``DEFAULT_LINE_BUDGET``.

    Returns
    -------
    list[dict]
        One finding dict per over-budget agentfile (empty for a clean corpus).
    """
    repo_root = repo_root_from_marketplace_root(marketplace_root)
    findings: list[Finding] = []
    for path in discover_agentfiles(repo_root):
        text = read_text_or_none(path)
        if text is None:
            continue
        line_count = count_lines(text)
        if line_count <= budget:
            continue
        findings.append(
            Finding(
                type=RULE_ID,
                file=str(path),
                line=1,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    'Always-on agentfile exceeds the line budget — re-classify '
                    'its sections and demote or delete until back within budget. '
                    'See rule-catalog.md and recipe-agentfile-hygiene.'
                ),
                extra={'rule': RULE_NAME, 'snippet': f'{line_count} lines (budget {budget})'},
            )
        )
    return [f.to_dict() for f in findings]
