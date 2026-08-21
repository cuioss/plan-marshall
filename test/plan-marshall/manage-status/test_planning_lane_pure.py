#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status.

Its one section: _read_request_body — the whole-body, heading-blind read.
"""


from __future__ import annotations

import pytest
from _planning_lane_fixtures import (
    _BOILERPLATE_CITATION,
    _TARGET_BELOW_NESTED_HEADING,
    _mod,
    _pure,
    _write_ingested_request,
    evaluate_signals_pure,
    scope_estimate_from_request_pure,
)


def test_pure_all_light_signals_resolve_light():
    """No signal fires → the pure scorer resolves the light default."""
    result = _pure()

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []


@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad', 'none'])
def test_pure_s2_deep_scope_estimate_fires_deep(scope_estimate):
    """S2 — each deep scope band fires S2 in isolation."""
    result = _pure(scope_estimate=scope_estimate)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate']


def test_pure_s2_absent_scope_estimate_fires_deep():
    """S2 — an absent (None) scope_estimate biases deep."""
    result = _pure(scope_estimate=None)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate']


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_pure_s3_generative_change_type_suppressed_when_narrow_and_concrete(change_type):
    """S3 — a generative change_type is carved out under the narrow+concrete baseline.

    The all-light baseline is surgical scope + concrete request, so S3 does not
    fire on its own. S3 firing deep alongside a broad/unknown scope is covered by
    ``test_planning_lane_calibration.py`` and ``test_pure_multiple_deep_signals``.
    """
    result = _pure(change_type=change_type)

    assert result['lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']


def test_pure_s4_breaking_compatibility_suppressed_when_narrow_and_concrete():
    """S4 — breaking compatibility is carved out under the narrow+concrete baseline.

    S4 firing deep for a broad/unknown scope is covered by
    ``test_planning_lane_calibration.py`` and ``test_pure_multiple_deep_signals``.
    """
    result = _pure(compatibility='breaking')

    assert result['lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']


def test_pure_s5_non_concrete_request_fires_deep():
    """S5 — a non-concrete request fires S5 in isolation."""
    result = _pure(request_concrete=False)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S5:concreteness']


@pytest.mark.parametrize('plan_source', [None, '', 'free_form', 'cli'])
def test_pure_s1_free_form_source_with_non_concrete_request_fires_deep(plan_source):
    """S1 — free-form source AND failed concreteness conjunction fires S1 (and S5)."""
    result = _pure(plan_source=plan_source, request_concrete=False)

    assert result['lane'] == 'deep'
    # The S1 conjunction keys off the failed S5 concreteness, so both fire.
    assert 'S1:plan_source' in result['fired_signals']
    assert 'S5:concreteness' in result['fired_signals']


@pytest.mark.parametrize('plan_source', [None, '', 'free_form', 'cli'])
def test_pure_s1_free_form_source_with_concrete_request_stays_light(plan_source):
    """S1 — free-form source ALONE does not fire when the request is concrete."""
    result = _pure(plan_source=plan_source, request_concrete=True)

    assert result['lane'] == 'light'
    assert 'S1:plan_source' not in result['fired_signals']


def test_pure_s6_override_deep_fires_deep():
    """S6 — an explicit deep override fires S6 in isolation."""
    result = _pure(override='deep')

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S6:override']


def test_pure_s6_override_light_does_not_force_deep():
    """S6 — a light override does not fire (the override is one-way to deep)."""
    result = _pure(override='light')

    assert result['lane'] == 'light'
    assert 'S6:override' not in result['fired_signals']


def test_pure_signals_echoes_all_realized_values():
    """The returned ``signals`` dict echoes every realized signal value verbatim.

    Compared with ``==`` on purpose: the point is that the echo is COMPLETE, so a
    signal added to the scorer without being echoed fails here. That is why the S7
    ``risk_prose`` key appears below — it is the pin working as designed, not an
    incidental update. (S7's own behaviour is covered by
    ``test_planning_lane_risk_prose.py``.)
    """
    result = _pure(
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=False,
        risk_prose=True,
        override='deep',
    )

    assert result['signals'] == {
        'plan_source': 'lesson',
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
        'risk_prose': True,
        'planning_lane_override': 'deep',
    }


def test_pure_multiple_deep_signals_accumulate_in_fired_order():
    """Multiple deep signals all appear in fired_signals in canonical S1..S7 order."""
    result = _pure(
        scope_estimate='multi_module',  # S2
        change_type='feature',           # S3
        compatibility='breaking',        # S4
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == [
        'S2:scope_estimate',
        'S3:change_type',
        'S4:compatibility',
    ]


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
