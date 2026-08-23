#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Positive control for ``ARGUMENT_NAMING_SUBSTRATE_ABSENT`` — the could_not_look outcome.

The argument-naming cluster derives its whole accept-set from the generated
executor at ``{marketplace_root.parent}/.plan/execute-script.py``. That file is
git-ignored, so a fresh clone carries none — and the cluster used to answer an
unusable registry with ``[]``, the same answer it gives a corpus it read in full
and found clean. This module pins the replacement: an unusable registry is
reported as its own outcome, and the report says WHICH kind of unusable.

Why the assertions key on ``details.reason`` and not on the rule id alone: the
implementation deliberately keeps three substrate states apart —
``executor_absent`` (nothing to read), ``executor_unreadable`` (something is
there but it does not decode), and ``registry_empty`` (it decoded and registers
nothing). They call for different operator action, and a test that pinned only
the rule id would keep passing if the three were later collapsed into one — the
distinction would retire silently, which is the class of loss this whole rule
exists to prevent. Each state is therefore driven to a distinct literal.

This is the POSITIVE half of a matched control pair. The NEGATIVE half is the
substrate-seeded fixture set the quality-gate suites build via
``seed_notation_registry`` — reproduced here as the last test so the pair is
readable in one place: with a registry present, the guard is silent.
"""

from __future__ import annotations

from pathlib import Path

from _plugin_doctor_dispatching_executor import seed_notation_registry
from conftest import load_script_module

_aan = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_argument_naming.py',
    '_analyze_argument_naming_absent_substrate',
)

#: The one markdown file every fixture tree below carries. One is enough to make
#: ``markdown_targets`` non-zero, which is the figure that makes the outcome
#: legible: it is the corpus the cluster WOULD have judged, and none of it was.
_SKILL_MD_RELPATH = 'bundles/b/skills/s/SKILL.md'


def _marketplace_with_corpus(temp_root: Path) -> Path:
    """Build a marketplace whose bundles corpus is non-empty; return its root.

    ``temp_root`` is the directory CONTAINING ``marketplace/`` — the anchor the
    cluster resolves its executor from — so a tree built here and left alone is
    an ``executor_absent`` tree by construction.
    """
    marketplace_root = temp_root / 'marketplace'
    skill_md = marketplace_root / _SKILL_MD_RELPATH
    skill_md.parent.mkdir(parents=True)
    skill_md.write_text(
        '# F\n\nA skill body carrying no executor invocation to judge.\n',
        encoding='utf-8',
    )
    return marketplace_root


def _write_executor(temp_root: Path, payload: bytes) -> Path:
    """Write raw bytes as the executor, bypassing the dispatching-stub writer.

    Raw bytes rather than text because one of the states under test is an
    executor that does not DECODE, which no text writer can produce.
    """
    plan_dir = temp_root / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    executor.write_bytes(payload)
    return executor


def _sole_substrate_finding(marketplace_root: Path) -> dict:
    """Run the cluster and return its single substrate finding.

    Asserts singularity first: an unusable registry short-circuits the whole
    cluster, so exactly one finding is the contract. A test that picked the
    matching finding out of a list would pass while the cluster also reported
    findings it could not have derived.
    """
    findings = _aan.analyze_argument_naming(marketplace_root)
    assert len(findings) == 1, (
        f'An unusable registry must short-circuit the cluster into exactly one '
        f'finding, got {len(findings)}: {findings!r}'
    )
    finding = findings[0]
    assert finding['rule_id'] == _aan.RULE_SUBSTRATE_ABSENT, (
        f'Expected {_aan.RULE_SUBSTRATE_ABSENT}, got {finding!r}'
    )
    return finding


def test_absent_executor_is_reported_as_could_not_look_at_the_bundles_root(tmp_path):
    """No executor at all: ``executor_absent``, anchored tree-wide with line 0.

    The anchor is load-bearing, not cosmetic. ``cmd_quality_gate`` keeps a
    finding under a ``--paths``-scoped run only when it is anchored at the
    BUNDLES root (``_finding_is_tree_wide``), and an anti-vacuity guard that a
    scoped run could filter out is one that reports clean exactly when it has
    seen least.
    """
    marketplace_root = _marketplace_with_corpus(tmp_path)

    finding = _sole_substrate_finding(marketplace_root)

    assert finding['details']['reason'] == 'executor_absent'
    assert finding['details']['outcome'] == 'could_not_look'
    assert finding['file'] == str(marketplace_root / 'bundles')
    assert finding['line'] == 0
    assert finding['severity'] == 'error'
    assert finding['fixable'] is False
    # The corpus that went unjudged is published; a bare zero-findings result
    # says nothing about it.
    assert finding['details']['markdown_targets'] == 1
    assert finding['details']['population_size'] == 0


def test_undecodable_executor_is_reported_as_unreadable_not_absent(tmp_path):
    """An executor that does not decode is ``executor_unreadable``.

    Distinct from absence because the operator action differs: bootstrap the
    checkout vs. repair a corrupt file. Driven with bytes that are invalid UTF-8
    rather than by revoking read permission, so the state is reachable on a root
    host too — where a permission-based fixture would silently not fire.
    """
    marketplace_root = _marketplace_with_corpus(tmp_path)
    _write_executor(tmp_path, b'SCRIPTS = {\n    "b:s:x": "\xff\xfe",\n}\n')

    finding = _sole_substrate_finding(marketplace_root)

    assert finding['details']['reason'] == 'executor_unreadable'
    assert finding['details']['outcome'] == 'could_not_look'


def test_executor_registering_no_notation_is_reported_as_empty_registry(tmp_path):
    """A readable executor whose ``SCRIPTS`` literal registers nothing is ``registry_empty``.

    The state that makes an empty stub useless as a fixture substrate: the file
    exists and decodes, and the cluster still has no accept-set, so it still
    reports could_not_look. Kept apart from the two executor states because an
    executor that IS present and registers nothing is a demonstrated defect,
    while an absent one is a missing file.
    """
    marketplace_root = _marketplace_with_corpus(tmp_path)
    _write_executor(tmp_path, b'SCRIPTS = {\n}\n')

    finding = _sole_substrate_finding(marketplace_root)

    assert finding['details']['reason'] == 'registry_empty'
    assert finding['details']['outcome'] == 'could_not_look'


def test_seeded_registry_yields_no_substrate_finding(tmp_path):
    """Matched negative control: with a usable registry the guard is silent.

    Without this, the three positives above are compatible with a rule that
    fires on every tree. It also pins the premise the quality-gate suites' clean
    fixtures rest on — ``seed_notation_registry`` really does make a fixture tree
    examinable.
    """
    marketplace_root = _marketplace_with_corpus(tmp_path)
    seed_notation_registry(tmp_path)

    findings = _aan.analyze_argument_naming(marketplace_root)

    assert findings == [], (
        f'A seeded registry makes the tree examinable, so a corpus with no '
        f'invocations must yield no findings at all, got: {findings!r}'
    )
