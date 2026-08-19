#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``classification validation gate`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_gate = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_classification_validate.py', '_cmd_classification_validate_under_test'
)


run_classification_validation = _gate.run_classification_validation


cmd_classification_validate = _gate.cmd_classification_validate


_lane = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_for_classification_test'
)


cmd_planning_lane_route = _lane.cmd_planning_lane_route


classify_scope_pure = _lane.classify_scope_pure


# The sensor's own whole-body reader. Feeding the gate's fixture through THIS, rather
# than through the raw ``body`` string, makes the equivalence assertions below compare
# the two verdicts over byte-identical input — the request.md template chrome included.
read_request_body = _lane._read_request_body


# =============================================================================
# Fixture authoring helpers
# =============================================================================

# A request body that clearly reads as a feature ("add / create / implement a
# new X"), so the change-type heuristic resolves a non-ambiguous feature winner.
_FEATURE_BODY = 'Add a new export command that creates and implements a fresh report generator.'


# A request body that clearly reads as a bug fix, so the heuristic does NOT
# resolve feature (no feature-as-bug_fix false positive).
_BUGFIX_BODY = 'The parser crashes on empty input — this is a regression; fix the broken exception path.'


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request\n\n'
        '## Original Input\n\n'
        '(unused)\n\n'
        '## Clarified Request\n\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': metadata or {}}),
        encoding='utf-8',
    )


def _write_references(
    plan_dir: Path,
    *,
    scope_estimate: str | None,
    affected_files: list[str] | None = None,
) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs: dict = {'base_branch': 'main'}
    if scope_estimate is not None:
        refs['scope_estimate'] = scope_estimate
    if affected_files is not None:
        refs['affected_files'] = affected_files
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')


def _write_marshal(fixture_dir: Path) -> None:
    config = {
        'plan': {
            'phase-1-init': {'deep_lane': 'auto'},
            'phase-2-refine': {'compatibility': 'deprecation'},
        },
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


# The multi_module floor, read from the SENSOR rather than restated here. The
# production detector imports the same constant, so these boundary cases move with
# it automatically — a threshold hard-coded in the test would let the gate and the
# sensor drift apart while every test still passed.
_MULTI_MODULE_MIN_PATHS = _lane._MULTI_MODULE_MIN_PATHS


# The ReDoS-defense per-line cap, likewise read from the SENSOR. A line longer
# than this is SKIPPED by ``_safe_path_scan`` and sets ``scan_incomplete`` — the
# cheapest way to construct a body whose path total is a lower bound rather than
# a count, without needing a 50KB fixture to exhaust the budget instead.
_MAX_SCAN_LINE_CHARS = _lane._MAX_SCAN_LINE_CHARS


# The surgical ceiling, likewise read from the SENSOR — used to build a body that
# lands in the ``single_module`` middle band, which is neither a narrow claim nor a
# multi_module reading and therefore must leave class 3 silent.
_SURGICAL_MAX_PATHS = _lane._SURGICAL_MAX_PATHS


def _body_with_paths(count: int, *, lead: str = '') -> str:
    """Return a request body naming exactly ``count`` distinct repo-relative paths."""
    paths = ', '.join(f'pkg/mod{i}/file{i}.py' for i in range(count))
    return f'{lead}Touch {paths}.'


def _body_with_unscannable_line(path_count: int) -> str:
    """Return a body the bounded scan cannot cover in full, naming few paths.

    One over-long, path-free line forces ``_safe_path_scan`` to skip it and report
    ``scan_incomplete=True``, while the remaining scannable text names only
    ``path_count`` paths — deliberately BELOW ``_MULTI_MODULE_MIN_PATHS``. That is
    exactly the shape a count-only detector reads as "narrow, nothing to flag".
    """
    unscannable = 'x' * (_MAX_SCAN_LINE_CHARS + 1)
    return f'{_body_with_paths(path_count)}\n\n{unscannable}\n'


def _body_with_fan_out_marker(path_count: int) -> str:
    """Return a body carrying a glob fan-out marker while naming few literal paths.

    The sensor bands this ``multi_module`` on its ``fan_out_marker`` row, which it
    evaluates BEFORE the path-count rows — a pattern declares an unbounded file set,
    and an unbounded set cannot be a bounded one. ``path_count`` is deliberately
    below ``_MULTI_MODULE_MIN_PATHS``, so a detector that only re-derived the count
    (and the ``scan_incomplete`` flag) reads this as "narrow, nothing to flag".
    """
    return f'{_body_with_paths(path_count)} Then sweep the same rename across **/*.py.'


def _ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


def _ns_route(plan_id: str):
    return Namespace(plan_id=plan_id, lane_override=None, persist=False)


# One fixture per row of ``classify_scope_pure``'s band table, narrow rows included.
# The equivalence test below asserts the gate's verdict AGAINST the sensor's band for
# each — no row's expected outcome is hard-coded, so the assertion stays honest even
# if a row's own predicate changes.
_SCALE_BAND_ROW_BODIES = [
    ('cv-equiv-surgical', _body_with_paths(1)),
    ('cv-equiv-middle-band', _body_with_paths(_SURGICAL_MAX_PATHS + 1)),
    ('cv-equiv-pathless', _BUGFIX_BODY),
    ('cv-equiv-path-floor', _body_with_paths(_MULTI_MODULE_MIN_PATHS)),
    ('cv-equiv-scan-incomplete', _body_with_unscannable_line(2)),
    ('cv-equiv-fan-out', _body_with_fan_out_marker(2)),
]
