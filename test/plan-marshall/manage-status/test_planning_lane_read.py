#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status.

The router resolves ``planning_lane ∈ {light, deep}`` from the DQ1 signal set
(S1–S7) plus a ``request.md`` regex, with zero codebase discovery. The default
is ``light``; any deep-precondition signal forces ``deep``; the
``plan.phase-1-init.deep_lane`` (``always``/``never``/``auto``) gate
short-circuits the signal evaluation. The ``escalate`` verb is a one-way
light→deep ratchet that refuses any downgrade.

Coverage:
- Each signal (S1–S6) firing deep in isolation. S7 (``risk_prose``) is covered
  in ``test_planning_lane_risk_prose.py``, not here.
- The all-light default (no deep signal fires).
- The deep_lane ``always`` / ``never`` short-circuit.
- ``--lane-override`` handling.
- ``--persist`` writes status.metadata.planning_lane.
- The one-way escalate invariant (deep + lane_escalated, no downgrade).
- Dispatch wiring (both verbs registered in manage-status.py argparse).
- ``evaluate_signals_pure`` — direct, I/O-free unit coverage of the extracted
  pure scorer: each of the six signal arguments firing deep in isolation, the
  all-light default, the S6 override, and the importability of the S5 regex
  constants and ``_request_is_concrete`` for downstream consumers.
- ``project_profile_pure`` — the execution-profile posture projection: the
  ``full`` / ``minimal`` / ``standard`` recommendation as a pure function of the same
  signals, the ``profile`` key on the route return, ``--persist`` writing
  ``status.metadata.execution_profile``, the independence invariant that
  ``deep_lane=always`` does NOT coerce the posture to ``full``, and the mirrored
  negative that a concrete but NON-narrow change never projects ``minimal`` (the
  security-gate half of the shared-predicate defect).
- ``classify_scope_pure`` / ``scope_estimate_from_request_pure`` — the pre-route
  coarse scope classifier over the whole band table: ``surgical`` for one-to-three
  distinct file paths with no fan-out marker, ``single_module`` for the 4–7 middle
  band and for an ambiguous pathless request, ``multi_module`` for a real fan-out
  marker or eight-or-more distinct paths, ``none`` as the DECLARED UNKNOWN for an
  unscoreable body (plus the invariant that the unknown biases S2 deep). Also the
  band boundaries at 3/4 and 7/8, markdown bold NOT registering as fan-out,
  distinct-path dedup, the ``scope_provenance`` explanation block, and the
  zero-architecture-call invariant.
- ``_read_request_body`` — the whole-body, heading-blind read: text below a
  nested ``## `` heading is reached, only the host ``# Request`` title line is
  stripped, and an absent / title-only / non-UTF-8 ``request.md`` degrades to the
  declared unknown instead of raising.
- The settled path-counter semantics — the intentional bare-filename exclusion
  (a directory separator is required) and the declared inapplicability of
  target-vs-citation discrimination, both asserted with their one-directional
  (band-widening) residual.
- The shared-population invariant — S5 concreteness and the scope band are shown
  to consume the identical body, not merely documented as doing so.
- ``cmd_scope_estimate_heuristic`` — ``--persist`` writing
  ``references.json.scope_estimate``, the ``scope_resolved`` classified-vs-unknown
  discriminator, the no-persist read-only path, the missing plan-dir error, its
  manage-status dispatch registration, and the D2 acceptance that
  pre-classification flips the router's S2 from deep to light for a concrete
  narrow request.
"""


from __future__ import annotations

import json
from argparse import Namespace

import pytest
from _planning_lane_fixtures import (
    _BOILERPLATE_CITATION,
    _TARGET_BELOW_NESTED_HEADING,
    _mod,
    _write_ingested_request,
    _write_references,
    _write_request,
    cmd_scope_estimate_heuristic,
    evaluate_signals_pure,
    scope_estimate_from_request_pure,
)


def test_pure_override_defaults_to_none_when_omitted():
    """The override argument is optional and defaults to None (no S6)."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert result['signals']['planning_lane_override'] is None


# =============================================================================
# S5 regex constants + _request_is_concrete importability (downstream consumers)
# =============================================================================
#
# The audit retrospective check (deliverable 2) re-derives request_concrete from
# each archived request.md by importing these symbols. These tests lock that they
# remain module-level and importable, and that _request_is_concrete matches the
# documented S5 anchors.


def test_s5_regex_constants_are_module_level_importable():
    """The four S5 regexes are importable module-level compiled patterns."""
    import re  # noqa: PLC0415

    for name in ('_PATH_RE', '_FENCE_RE', '_CLI_RE', '_NOTATION_RE'):
        pattern = getattr(_mod, name)
        assert isinstance(pattern, re.Pattern), f'{name} must be a compiled regex'


def test_request_is_concrete_is_module_level_importable():
    """_request_is_concrete is importable for downstream re-derivation of S5."""
    assert callable(_mod._request_is_concrete)


@pytest.mark.parametrize(
    'body',
    [
        'Update `marketplace/bundles/plan-marshall/skills/x/scripts/x.py` to fix it.',
        'Run python3 .plan/execute-script.py plan-marshall:foo:foo bar.',
        'Use the manage-status verb to read the plan.',
        'Here is a fenced block:\n```\ncode\n```\n',
    ],
)
def test_request_is_concrete_true_for_each_anchor(body):
    """Each S5 anchor (path / CLI / notation / fence) marks the body concrete."""
    assert _mod._request_is_concrete(body) is True


@pytest.mark.parametrize('body', ['', 'The thing should do the thing, somehow.'])
def test_request_is_concrete_false_for_anchorless_body(body):
    """An empty or anchorless body is not concrete (→ S5 deep).

    Re-justified under the whole-body read: the empty case now arrives here only
    when ``request.md`` is genuinely absent, unreadable, or empty — never as a
    side effect of an H2 section boundary. S5 and the scope band agree on that
    input (S5 → not concrete, scope → declared unknown), and both bias deep, so
    the unscoreable request is widened by two independent signals rather than
    silently narrowed by either.
    """
    assert _mod._request_is_concrete(body) is False


# =============================================================================
# _read_request_body — the whole-body, heading-blind read
# =============================================================================
#
# The reader must be robust to an ingested spec carrying its own '## ' headings,
# which is the NORMAL case for every orchestrated plan. The shared markdown
# splitter starts a new section on any line beginning '## ' with no nesting
# awareness, so a section-scoped read truncated the request at the ingested
# body's first nested heading and scored boilerplate instead.


def test_read_request_body_returns_text_after_a_nested_h2_heading(plan_context):
    """The read spans the whole body, including text below a nested '## ' heading.

    The regression the whole-body read exists to prevent: with a section-scoped
    read this target is unreachable, because '## Objective' terminates the
    'Original Input' section before the surface list is ever seen.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-nested-h2')
    _write_ingested_request(plan_dir)

    body = _mod._read_request_body('pl-read-nested-h2')

    # Text below the first nested heading is present.
    assert _TARGET_BELOW_NESTED_HEADING in body
    assert '## Expected Surface' in body
    assert 'doc/concepts/orchestration.adoc' in body
    # The ingested spec's own headings survive verbatim — nothing was consumed
    # as a section boundary.
    assert '## Objective' in body


def test_read_request_body_strips_only_the_host_title_line(plan_context):
    """Only the host document's own '# Request' title line is removed."""
    plan_dir = plan_context.plan_dir_for('pl-read-title-strip')
    _write_ingested_request(plan_dir)

    body = _mod._read_request_body('pl-read-title-strip')

    assert '# Request' not in body
    # The INGESTED spec's own '# PLAN-99' title is not the host title and stays.
    assert '# PLAN-99: An ingested orchestrator plan spec' in body
    # Header metadata lines are not a section boundary and are retained.
    assert 'source: description' in body


def test_read_request_body_retains_a_non_first_line_request_heading(plan_context):
    """Only line 1 is eligible for the title strip — a later '# Request…' stays.

    The strip is anchored to the FIRST line rather than matched anywhere,
    because an ingested spec may legitimately carry its own ``# Request …``
    heading. Dropping that would silently remove request narrative and would
    contradict the docstring's ONLY-line-removed contract.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-nested-request-heading')
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text(
        '# Request: host title\n'
        '\n'
        'source: description\n'
        '\n'
        '# Request routing rework\n'
        '\n'
        'Body naming marketplace/bundles/plan-marshall/skills/x/y.py\n',
        encoding='utf-8',
    )

    body = _mod._read_request_body('pl-read-nested-request-heading')

    # The host title (line 1) is gone...
    assert '# Request: host title' not in body
    # ...but the ingested spec's own '# Request …' heading is preserved.
    assert '# Request routing rework' in body


def test_read_request_body_counts_targets_the_truncating_read_could_not_reach(plan_context):
    """The scored body yields the target paths, not just the boilerplate citation.

    Pins the end-to-end consequence of the read change on the same fixture: the
    truncated head region carries exactly one path — a citation — which would
    band ``surgical``; the whole body carries five, which lands in the 4–7 middle
    band, ``single_module``.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-target-count')
    _write_ingested_request(plan_dir)

    body = _mod._read_request_body('pl-read-target-count')
    paths = _mod._distinct_paths(body)

    assert _BOILERPLATE_CITATION in paths
    assert _TARGET_BELOW_NESTED_HEADING in paths
    assert len(paths) == 5, sorted(paths)
    assert scope_estimate_from_request_pure(body) == 'single_module'


def test_read_request_body_empty_when_request_absent(plan_context):
    """A plan with no request.md reads as the empty (declared-unknown) body."""
    plan_dir = plan_context.plan_dir_for('pl-read-absent')
    plan_dir.mkdir(parents=True, exist_ok=True)

    assert _mod._read_request_body('pl-read-absent') == ''


def test_read_request_body_empty_when_only_the_title_line_present(plan_context):
    """A request.md carrying nothing but the title line reads as empty, not as chrome."""
    plan_dir = plan_context.plan_dir_for('pl-read-title-only')
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text('# Request: nothing else\n', encoding='utf-8')

    assert _mod._read_request_body('pl-read-title-only') == ''


def test_read_request_body_handles_non_utf8_request(plan_context):
    """A non-UTF-8 request.md degrades to the declared unknown, never an exception.

    ``Path.read_text(encoding='utf-8')`` raises ``UnicodeDecodeError`` — a
    ``ValueError`` subtype, NOT an ``OSError`` — so an ``except OSError`` guard
    alone would let it escape and crash the phase. This asserts the widened
    guard routes an undecodable body to the same unscoreable path as a missing
    file.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-non-utf8')
    plan_dir.mkdir(parents=True, exist_ok=True)
    # 0xFF is not a valid UTF-8 start byte.
    (plan_dir / 'request.md').write_bytes(b'# Request\n\n\xff\xfe not utf-8 \xff\n')

    assert _mod._read_request_body('pl-read-non-utf8') == ''
    assert scope_estimate_from_request_pure(_mod._read_request_body('pl-read-non-utf8')) == 'none'


def test_scope_heuristic_declares_unknown_for_unreadable_request(plan_context):
    """End-to-end: an unscoreable request persists the declared unknown, not a band."""
    plan_dir = plan_context.plan_dir_for('pl-scope-unknown')
    plan_dir.mkdir(parents=True, exist_ok=True)
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(
        Namespace(plan_id='pl-scope-unknown', persist=True)
    )

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'none'
    assert result['scope_resolved'] is False
    assert result['distinct_path_count'] == 0
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'none'


def test_scope_heuristic_reports_scope_resolved_true_for_a_scored_body(plan_context):
    """``scope_resolved`` distinguishes a classified band from the declared unknown.

    Without this field a consumer reading ``scope_estimate`` alone cannot tell a
    measured band from a "cannot tell" verdict — which is exactly how a zero-byte
    read used to pass for a band.
    """
    plan_dir = plan_context.plan_dir_for('pl-scope-resolved')
    _write_request(plan_dir, 'Fix pkg/one.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(Namespace(plan_id='pl-scope-resolved', persist=False))

    assert result['scope_estimate'] == 'surgical'
    assert result['scope_resolved'] is True
