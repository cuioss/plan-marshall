# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``posture_cutoff_legacy_aggregate`` entry is a MARKED back-compat shim (D9/D8).

``_REMOVAL_CAUSE_PATTERNS``'s first entry matches a decision-log line shape the
composer once emitted and no longer does. That is the textbook Category-B shim —
a permanent read path accommodating a shape OUR OWN prior writer produced — and
before this deliverable it carried explanatory prose but no marker, so it had no
owner, no version floor, and no removal trigger.

Three things are pinned here, and the third is the one that matters:

1. The entry carries a conforming ``# SHIM(B)`` marker with all three required
   fields non-empty, checked through the plugin-doctor rule's OWN marker grammar
   rather than a second hand-written parser.
2. The ``shim-marker-missing`` rule, run over the real bundles tree, reports no
   finding naming ``check-routing-decisions.py``.
3. The retired shape this entry matches is a shape THE EMITTER ACTUALLY PRODUCED.

Point 3 exists because of lesson ``2026-08-08-20-001`` (Instance 1). The sibling
``posture_cutoff`` pattern that preceded this one was dead in production for a
long time while its test stayed green, because both the pattern and the test
literal were copied from ``decision-rules.md``. Doc → regex and doc → test-literal
is a closed loop that the emitter never enters, so the two agreed with each other
and neither agreed with the code. The fixture below is therefore transcribed from
the EMITTER'S OWN SOURCE at the commit before the shape changed, and its
provenance is recorded beside it so a later reader can re-verify it the same way.
"""


from __future__ import annotations

import json
from pathlib import Path

from conftest import load_script_module

_crd = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-routing-decisions.py', 'crd_legacy_shim_mod'
)
_shim = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_shim_marker.py', 'shim_marker_for_crd'
)

# test/plan-marshall/plan-retrospective/<this file>
REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLES_ROOT = REPO_ROOT / 'marketplace' / 'bundles'
CRD_PATH = (
    BUNDLES_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts'
    / 'check-routing-decisions.py'
)

#: The cause token whose entry carries the shim.
LEGACY_CAUSE = 'posture_cutoff_legacy_aggregate'

# ---------------------------------------------------------------------------
# The captured emitter line
# ---------------------------------------------------------------------------
#
# PROVENANCE — recovered from the emitter, not from a standards document:
#   commit `d04ac98ed^` (the parent of "fix(manage-execution-manifest): guard
#   compose-time step subtractions", #1066 — the change that retired this shape),
#   file `manage-execution-manifest/scripts/manage-execution-manifest.py`,
#   the `_emit_decision_log` call guarded by `if execution_profile != 'full' and
#   lane_dropped:`, which rendered:
#
#       '(plan-marshall:manage-execution-manifest:compose) lane_resolution — '
#       f'execution_profile={execution_profile}, dropped {lane_dropped} from phase_6.steps '
#       '(tier above posture cutoff)'
#
# `lane_dropped` is a Python LIST at that call site, so `{lane_dropped}` renders a
# list repr — which is why this is the one pattern that reaches
# `_parse_step_tokens`'s list branch. The line below is that f-string evaluated
# with a representative posture and drop list, prefixed with the log envelope a
# real decision.log line carries (the patterns use `.search`, so the prefix is
# incidental — it is included so the fixture is a whole line rather than a
# fragment).
_EMITTED_POSTURE = 'minimal'
_EMITTED_DROPPED = ['sonar-roundtrip', 'finalize-step-simplify']

CAPTURED_LEGACY_AGGREGATE_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] '
    '(plan-marshall:manage-execution-manifest:compose) lane_resolution — '
    f'execution_profile={_EMITTED_POSTURE}, dropped {_EMITTED_DROPPED} from phase_6.steps '
    '(tier above posture cutoff)'
)


def _entry_line_number() -> int:
    """Return the 1-based line of the ``posture_cutoff_legacy_aggregate`` key."""
    for idx, line in enumerate(CRD_PATH.read_text(encoding='utf-8').splitlines(), start=1):
        if f"'{LEGACY_CAUSE}'," in line:
            return idx
    raise AssertionError(
        f'{LEGACY_CAUSE!r} no longer appears in {CRD_PATH.name} — if the shim was deleted, '
        'delete this module with it; if it was renamed, this test must follow.'
    )


def _markers():
    text = CRD_PATH.read_text(encoding='utf-8')
    return _shim._parse_markers(_shim._comment_lines(text), _shim._function_spans(text))


def test_legacy_aggregate_entry_carries_a_conforming_shim_marker():
    """A conforming ``SHIM`` marker covers the entry, with all three fields non-empty.

    Parsed with the plugin-doctor rule's OWN grammar, so this test cannot pass
    against a marker the rule would reject.
    """
    entry_line = _entry_line_number()
    markers = _markers()
    assert markers, f'{CRD_PATH.name} carries no SHIM marker at all.'

    covering = [m for m in markers if m.cover[0] <= entry_line <= m.cover[1]]
    assert covering, (
        f'No SHIM marker covers the {LEGACY_CAUSE!r} entry (line {entry_line}). The entry '
        'matches a decision-log shape the composer no longer emits — a back-compat read '
        'path with no owner, no floor and no removal trigger.'
    )

    malformed = [(m.anchor_line, m.malformed_reason) for m in covering if m.malformed_reason]
    assert not malformed, (
        'The marker covering the entry is malformed: ' + json.dumps(malformed, indent=2)
    )


def test_shim_marker_fields_are_present_and_non_empty():
    """Each of the three required fields carries a real value, not a bare label.

    Asserted against the rule's own field regexes, which require a non-space
    character after the colon — so ``# shim-floor:`` with nothing after it fails
    here exactly as it would in the gate.
    """
    text = CRD_PATH.read_text(encoding='utf-8')
    comments = [body for _line, body in _shim._comment_lines(text)]

    fields = {
        'shim-owner': _shim._FIELD_OWNER,
        'shim-floor': _shim._FIELD_FLOOR,
        'shim-remove-when': _shim._FIELD_REMOVE,
    }
    values = {}
    for name, pattern in fields.items():
        matches = [pattern.match(body) for body in comments]
        hits = [m.group(1).strip() for m in matches if m]
        assert hits, f'{CRD_PATH.name} declares no non-empty {name} field.'
        values[name] = hits

    # The floor and the trigger must say something concrete — a bare "legacy" is
    # explicitly not a floor under the convention.
    for name in ('shim-floor', 'shim-remove-when'):
        for value in values[name]:
            assert value.lower() not in {'legacy', 'n/a', 'tbd', 'unknown'}, (
                f'{name} is a placeholder ({value!r}), not a concrete '
                'boundary/extinction condition.'
            )


def test_shim_marker_rule_reports_no_finding_for_this_script(capsys):
    """The live ``shim-marker-missing`` rule is clean for ``check-routing-decisions.py``.

    Run over the REAL bundles tree, so this is the gate's own verdict rather than
    a re-implementation of it. The population size and the total finding count are
    published: a run that scanned nothing would produce an empty finding list too,
    and 'clean' and 'never looked' must not read the same.
    """
    # The population-carrying variant is used deliberately: a CLEAN run carries no
    # findings and therefore no `population_size` on any finding, so reading the
    # figure off the findings would give nothing back in exactly the state this
    # test expects to be in.
    findings, population_size = _shim.analyze_shim_marker_with_population(BUNDLES_ROOT)
    scanned = _shim.enumerate_script_files(BUNDLES_ROOT)

    with capsys.disabled():
        print(
            '\n[shim-marker] population:',
            json.dumps(
                {
                    'population_size': population_size,
                    'scripts_enumerated': len(scanned),
                    'total_findings': len(findings),
                },
                indent=2,
            ),
        )

    assert population_size > 0, (
        'The rule enumerated NO scripts over the real bundles tree — a clean result here '
        'would be vacuous rather than meaningful.'
    )
    assert str(CRD_PATH) in {str(p) for p in scanned}, (
        f'{CRD_PATH.name} is not in the scanned population, so a clean verdict for it '
        'proves nothing.'
    )

    ours = [f for f in findings if str(f.get('file', '')).endswith(CRD_PATH.name)]
    assert not ours, (
        f'The shim-marker rule reports finding(s) against {CRD_PATH.name}:\n'
        + json.dumps(
            [
                {'type': f.get('type'), 'line': f.get('line'), 'message': f.get('message')}
                for f in ours
            ],
            indent=2,
        )
    )


def test_legacy_pattern_matches_a_line_the_emitter_actually_produced():
    """The shim tolerates a shape the composer REALLY emitted — the anti-tautology bind.

    A shim marker asserts that a past version of our own writer produced the old
    shape. If it never did, the entry is not a shim at all — it is a pattern for a
    line that never existed, and the marker would be documenting a fiction.

    The fixture is transcribed from the emitter's own source at the commit before
    the shape changed (see the provenance block above), NOT from
    ``decision-rules.md``. That distinction is the whole lesson: the predecessor
    pattern and its test literal were both copied from the document, agreed with
    each other, and matched nothing the emitter wrote.
    """
    causes = _crd.resolve_removal_causes([CAPTURED_LEGACY_AGGREGATE_LINE])

    for step in _EMITTED_DROPPED:
        assert causes.get(step) == LEGACY_CAUSE, (
            f'The captured emitter line does not resolve {step!r} to {LEGACY_CAUSE!r} '
            f'(got {causes.get(step)!r}). Either the shim pattern no longer matches the '
            'shape it claims to tolerate, or the captured line has drifted from the '
            'emitter it was transcribed from — re-derive it from the emitter source, '
            'never from the standards document.'
        )


def test_legacy_pattern_is_the_route_that_reaches_the_list_repr_branch():
    """The captured line carries a Python list repr, and the reader splits it.

    ``_parse_step_tokens``'s list branch is reachable by exactly this route (the
    current emitters all write one bare step per line), so the branch and this
    pattern are kept alive or retired together.
    """
    assert '[' in CAPTURED_LEGACY_AGGREGATE_LINE and ']' in CAPTURED_LEGACY_AGGREGATE_LINE

    tokens = _crd._parse_step_tokens(str(_EMITTED_DROPPED))
    assert tokens == _EMITTED_DROPPED, (
        f'The list-repr branch did not split the captured drop list: {tokens!r}'
    )
