#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Write-path guard for the display_timezone knob (D4).

The display_timezone knob is a DISPLAY-ONLY setting. Storage and comparison stay
UTC unconditionally — the knob must never reach a write or compare path. This
guard keeps that refusal true against a future author who has forgotten why a
configured write-zone re-opens a silent-mixed-clock defect.

The guard is DERIVED OVER the D1 classification
(``timestamp_render_classification.json``), not a hand-written site list:

* It re-scans the live ``marketplace/bundles/**/*.py`` tree for every
  timestamp call site (the population), so the classification cannot silently go
  stale or empty.
* It treats STORE/COMPARE as the derived remainder (every scanned file that is
  neither a declared RENDER file nor a knob-owner file), so a newly-added
  timestamp site is STORE/COMPARE by default and trips this guard the instant it
  references a knob-consumer symbol.
* It PUBLISHES the population it examined — the scanned/render/owner/store-compare
  census — via an assertion-visible print, so a guard that examined an empty
  population is impossible to mistake for a passing one.

The core assertion (write-path isolation) has two arms, because a knob leak has
two shapes:

* **Across files** — every knob-consumer symbol (``render_timestamp``,
  ``resolve_display_timezone``, ``read_display_timezone``, ``display_timezone``)
  appears ONLY in a knob-owner file or a declared RENDER file, never in a
  STORE/COMPARE file.
* **Within a RENDER file** — each declared RENDER file spends exactly its
  ``render_call_budget`` of ``render_timestamp(`` calls. A declared RENDER file
  is not wholly a render surface, so a file-granular exemption hid every store
  site inside one; the budget makes routing an additional site through the knob
  a red build.
"""

import json
import re
from pathlib import Path

# repo_root/test/plan-marshall/manage-run-config/<this file>
REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLES_ROOT = REPO_ROOT / 'marketplace' / 'bundles'
CLASSIFICATION_PATH = Path(__file__).parent / 'timestamp_render_classification.json'


def _load_classification() -> dict:
    data: dict = json.loads(CLASSIFICATION_PATH.read_text(encoding='utf-8'))
    return data


def _bundle_py_files() -> list[Path]:
    return sorted(BUNDLES_ROOT.rglob('*.py'))


def _repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _scan_time_files(scan_regex: str) -> set[str]:
    """Return the repo-relative paths of every bundle .py with a timestamp site."""
    pattern = re.compile(scan_regex)
    hits: set[str] = set()
    for path in _bundle_py_files():
        if pattern.search(path.read_text(encoding='utf-8')):
            hits.add(_repo_rel(path))
    return hits


def _files_referencing_symbols(symbols: list[str]) -> dict[str, list[str]]:
    """Map each bundle .py that references any knob symbol to the symbols it hits."""
    found: dict[str, list[str]] = {}
    for path in _bundle_py_files():
        text = path.read_text(encoding='utf-8')
        matched = [sym for sym in symbols if sym in text]
        if matched:
            found[_repo_rel(path)] = matched
    return found


def test_classification_covers_the_live_population_and_is_non_empty(capsys):
    """The classification covers every live timestamp site, and the population is non-empty.

    Publishes the derived census. A guard over an empty classification (this
    epic's namesake defect) would fail here rather than pass trivially.
    """
    classification = _load_classification()
    scan_regex = classification['scan_regex']
    render_files = set(classification['render_files'])
    owner_files = set(classification['knob_owner_files'])

    scanned = _scan_time_files(scan_regex)
    store_compare = scanned - render_files - owner_files

    # Publish the population this guard examined.
    census = {
        'scanned_time_files': len(scanned),
        'render_files': sorted(render_files),
        'knob_owner_files': sorted(owner_files),
        'store_compare_files': len(store_compare),
    }
    with capsys.disabled():
        print('\n[display-timezone guard] population census:', json.dumps(census, indent=2))
        print('[display-timezone guard] store/compare files:', json.dumps(sorted(store_compare), indent=2))

    # Non-empty population — the classification is neither empty nor stale.
    assert scanned, 'No timestamp sites scanned — the population is empty (scan is broken).'
    assert render_files, 'RENDER population is empty (D1 classification lists no render site).'
    assert store_compare, 'STORE/COMPARE population is empty — the boundary guards nothing.'

    # Every declared RENDER / owner file must actually be a live timestamp site,
    # or the classification references a path that no longer exists / no longer
    # renders.
    for declared in render_files | owner_files:
        assert declared in scanned, (
            f'Classified file {declared!r} is not a live timestamp site — '
            'the classification has drifted from the tree.'
        )


def test_render_routing_is_live(capsys):
    """Every declared RENDER file actually routes through render_timestamp (D3/D5d).

    If the routing is removed, the knob reaches no rendering surface — the render
    population would be a paper entry. This asserts the routing is present.
    """
    classification = _load_classification()
    del capsys
    for rel in classification['render_files']:
        text = (REPO_ROOT / rel).read_text(encoding='utf-8')
        assert 'render_timestamp(' in text, (
            f'Declared RENDER file {rel!r} does not call render_timestamp(...) — '
            'its render site is not routed through the labelling helper.'
        )


def test_knob_symbols_never_reach_a_store_or_compare_site():
    """Write-path isolation (D4), enforced per SITE rather than per FILE.

    Two assertions, because a knob leak has two shapes and the file-granular
    form of this guard could only ever see the first:

    1. **Across files** — a knob-consumer symbol in a file that is neither a
       knob owner nor a declared RENDER file is a STORE/COMPARE site consulting
       the display timezone.

    2. **Within a RENDER file** — a declared RENDER file is not wholly a render
       surface. ``manage-metrics.py`` renders ONCE and calls ``now_utc_iso()``
       nine times, so exempting the file wholesale made every one of those store
       sites invisible: routing one of them through ``render_timestamp(...)``
       changed nothing this guard could observe. Each RENDER file is therefore
       held to the ``render_call_budget`` re-derived in the classification, so
       spending a render call on a store site is a red build.
    """
    classification = _load_classification()
    symbols = classification['knob_consumer_symbols']
    render_files = set(classification['render_files'])
    allowed = render_files | set(classification['knob_owner_files'])

    referencing = _files_referencing_symbols(symbols)
    leaks = {rel: syms for rel, syms in referencing.items() if rel not in allowed}

    assert not leaks, (
        'Knob-consumer symbol(s) reached a non-RENDER, non-owner file — a '
        'STORE/COMPARE site is consulting display_timezone:\n'
        + json.dumps(leaks, indent=2)
    )

    # The guard must have something to examine — the owner + render files DO
    # reference the knob, so an empty result means the scan silently found nothing.
    assert referencing, 'No file references any knob symbol — the isolation scan found nothing.'

    # Site-granular arm: every RENDER file carries a budget, and spends it exactly.
    budgets = {site['file']: site['render_call_budget'] for site in classification['render_sites']}
    assert set(budgets) == render_files, (
        'Every declared RENDER file must carry a render_call_budget and vice versa — '
        f'render_files={sorted(render_files)} budgeted={sorted(budgets)}'
    )

    for rel, budget in sorted(budgets.items()):
        actual = (REPO_ROOT / rel).read_text(encoding='utf-8').count('render_timestamp(')
        assert actual == budget, (
            f'RENDER file {rel!r} makes {actual} render_timestamp(...) call(s) but is '
            f'budgeted for {budget}. A RENDER file is not wholly a render surface: an '
            'extra call is a STORE/COMPARE site that has been routed through the '
            'display-timezone knob. Route the site back through the UTC store '
            'primitive, or — only if this really is a new human-facing render site — '
            'raise render_call_budget in timestamp_render_classification.json and say '
            'what it renders.'
        )
