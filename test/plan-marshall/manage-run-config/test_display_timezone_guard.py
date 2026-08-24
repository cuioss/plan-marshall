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
  stale or empty. The scan pattern has two arms, published separately in the
  classification and asserted here to compose into ``scan_regex``: a raw-call arm
  for modules that construct or parse a time themselves, and a helper arm
  (``now_utc_iso`` / ``format_timestamp``) for modules that obtain one from the
  shared primitives. The raw-call arm alone cannot see the second group at all,
  so before the helper arm existed their store sites were absent from a census
  that nonetheless looked large and passed.
* The helper-only difference (helper arm MINUS raw-call arm) is re-derived from
  the tree and matched against the classification's explicit
  ``helper_only_sites`` verdicts in both directions, so neither an unclassified
  surface nor a stale entry can pass.
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


def _derive_helper_only_population(classification: dict) -> tuple[set[str], set[str], set[str]]:
    """Re-derive the helper-only population from the tree.

    Returns ``(raw_arm_hits, helper_arm_hits, helper_only)`` where ``helper_only``
    is the set difference — the bundle modules that reach a timestamp ONLY through
    a shared helper, and which the raw-call arm therefore cannot see. The
    population is derived here from the live tree, never read from the
    classification's own entry list: a detector that took its population from the
    thing it is checking could not fail.
    """
    raw_arm = _scan_time_files(classification['scan_regex_raw_call_arm'])
    helper_arm = _scan_time_files(classification['scan_regex_helper_arm'])
    return raw_arm, helper_arm, helper_arm - raw_arm


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


def test_scan_regex_reaches_the_shared_timestamp_helpers():
    """The census must see modules that get their time from a shared helper (D8).

    The raw-call arm of ``scan_regex`` matches only modules that construct or
    parse a time themselves. A module whose timestamp comes from
    ``now_utc_iso()`` / ``format_timestamp()`` matches none of those shapes, so
    it fell out of the scanned population entirely — and because STORE/COMPARE is
    the DERIVED remainder of that population, its store sites were absent from
    the census the guard publishes. The omission was invisible: the guard still
    reported a large, non-empty census and passed.
    """
    classification = _load_classification()
    scan_regex = classification['scan_regex']

    for helper in ('now_utc_iso', 'format_timestamp'):
        assert helper in scan_regex, (
            f'scan_regex does not reach {helper!r}. Every bundle module whose only '
            'timestamp comes through that helper is outside the scanned population, '
            'so it is missing from the derived STORE/COMPARE census — and a census '
            'that silently omits sites still looks non-empty and still passes. Add '
            'the helper to scan_regex_helper_arm (and to the composed scan_regex).'
        )


def test_scan_regex_is_the_composition_of_its_published_arms():
    """``scan_regex`` must equal the alternation of the two published arms.

    The arms are published separately so the guard can compute the helper-only
    difference. If an arm were widened without the composed pattern following,
    the difference would be derived over one population while the census was
    derived over another — and the two would disagree silently.
    """
    classification = _load_classification()
    raw = classification['scan_regex_raw_call_arm']
    helper = classification['scan_regex_helper_arm']

    assert classification['scan_regex'] == f'{raw}|{helper}', (
        'scan_regex is not the alternation of scan_regex_raw_call_arm and '
        'scan_regex_helper_arm — the arms have drifted from the composed pattern.'
    )


def test_helper_only_population_has_an_explicit_classification_entry(capsys):
    """Every helper-only module carries an explicit, recorded verdict (D8).

    The population is re-derived HERE from the live tree as the set difference
    between the helper arm and the raw-call arm — it is never taken from the
    classification's own ``helper_only_sites`` list, which is the thing under
    test. The assertion runs in both directions: an undeclared member is a
    surface that was never classified, and a declared entry that is no longer in
    the difference is a stale claim about a tree that has moved.
    """
    classification = _load_classification()
    raw_arm, helper_arm, helper_only = _derive_helper_only_population(classification)
    declared = {entry['file'] for entry in classification['helper_only_sites']}

    census = {
        'raw_call_arm_files': len(raw_arm),
        'helper_arm_files': len(helper_arm),
        'helper_only_files': len(helper_only),
        'declared_entries': len(declared),
    }
    with capsys.disabled():
        print('\n[display-timezone guard] helper-only census:', json.dumps(census, indent=2))
        print('[display-timezone guard] helper-only files:', json.dumps(sorted(helper_only), indent=2))

    # A difference of zero would make the two directional assertions below
    # vacuously true, so the population size is asserted, not merely printed.
    assert helper_only, (
        'The helper-only population is empty. Either every helper caller also '
        'makes a raw datetime call (in which case the helper arm is buying '
        'nothing), or the arms are no longer matching what they claim to match.'
    )

    undeclared = helper_only - declared
    assert not undeclared, (
        'Bundle module(s) reach a timestamp ONLY through a shared helper but carry '
        'no entry in helper_only_sites, so no verdict was ever recorded for them:\n'
        + json.dumps(sorted(undeclared), indent=2)
    )

    stale = declared - helper_only
    assert not stale, (
        'helper_only_sites declares module(s) that are no longer in the live '
        'helper-only difference — the classification has drifted from the tree:\n'
        + json.dumps(sorted(stale), indent=2)
    )


def test_published_census_covers_every_helper_reaching_module(capsys):
    """The published census leaves no helper-reaching module outside it (D8).

    The census the guard prints is the ``scanned`` population, and STORE/COMPARE
    is its derived remainder — so a module absent from ``scanned`` is absent from
    the census, silently. This asserts the difference the widening was made to
    close is now EMPTY: every bundle module reaching ``now_utc_iso`` /
    ``format_timestamp`` is inside the scanned population.

    Pre-widening this failed with the whole helper-only set listed, which is the
    defect stated as a set: the guard's census and the set of modules that
    actually obtain a timestamp were not the same population.
    """
    classification = _load_classification()
    scanned = _scan_time_files(classification['scan_regex'])
    _raw_arm, helper_arm, _helper_only = _derive_helper_only_population(classification)

    uncovered = helper_arm - scanned
    with capsys.disabled():
        print(
            '\n[display-timezone guard] helper-arm coverage:',
            json.dumps(
                {'helper_arm_files': len(helper_arm), 'scanned_files': len(scanned),
                 'uncovered': sorted(uncovered)},
                indent=2,
            ),
        )

    assert helper_arm, 'The helper arm matched nothing — the coverage claim below would be vacuous.'
    assert not uncovered, (
        'Module(s) reach a timestamp helper but are absent from the scanned population, '
        'so they are absent from the census this guard publishes and from the derived '
        'STORE/COMPARE remainder:\n' + json.dumps(sorted(uncovered), indent=2)
    )


def test_helper_only_entries_are_well_formed(capsys):
    """Each helper-only verdict carries the shape its classification requires (D8).

    A STORE entry must NOT carry a ``render_call_budget`` — a budget on a store
    site would assert that the display knob legitimately reaches it. A RENDER
    entry must carry a re-derived budget AND appear in ``render_files``, so the
    two arms of the write-path guard see it.
    """
    classification = _load_classification()
    entries = classification['helper_only_sites']
    render_files = set(classification['render_files'])
    budgeted = {site['file'] for site in classification['render_sites']}

    verdicts = {'STORE': 0, 'RENDER': 0}
    for entry in entries:
        rel = entry['file']
        verdict = entry['classification']
        assert verdict in verdicts, (
            f'helper_only_sites entry {rel!r} carries an unknown classification '
            f'{verdict!r} — expected STORE or RENDER.'
        )
        verdicts[verdict] += 1

        assert entry.get('reason'), (
            f'helper_only_sites entry {rel!r} records no reason. An entry without a '
            'reason is a bare assertion that the site is safe, which is exactly what '
            'this classification exists to replace.'
        )

        if verdict == 'STORE':
            assert 'render_call_budget' not in entry, (
                f'STORE entry {rel!r} carries a render_call_budget. A budget grants a '
                'file render calls; a STORE site is one the display-timezone knob must '
                'never reach, so it has no budget to spend.'
            )
            assert rel not in render_files, (
                f'{rel!r} is classified STORE but is also listed in render_files — the '
                'file would be exempted from the cross-file leak arm it is meant to be '
                'held to.'
            )
        else:
            assert rel in render_files, (
                f'RENDER entry {rel!r} is not listed in render_files, so the write-path '
                'guard treats it as STORE/COMPARE and its render call reads as a leak.'
            )
            assert rel in budgeted, (
                f'RENDER entry {rel!r} carries no render_call_budget in render_sites — '
                'an unbudgeted RENDER file can absorb further store sites unnoticed.'
            )

    # Publish the verdict split so a run in which one branch above examined
    # nothing is visible rather than silently vacuous.
    with capsys.disabled():
        print('\n[display-timezone guard] helper-only verdicts:', json.dumps(verdicts, indent=2))

    assert sum(verdicts.values()) == len(entries)


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


def test_each_budgeted_render_call_feeds_its_declared_subject(capsys):
    """Each budgeted render call still feeds the human-facing site it is budgeted for.

    The ``render_call_budget`` arm is a COUNT, and a count cannot see a
    SUBSTITUTION. Moving the one budgeted ``render_timestamp(...)`` call off the
    human-facing line and onto a store site inside the same file leaves
    ``actual == budget``, so the budget arm passes while the display-timezone
    knob has been re-pointed at a stored value and the operator-facing line no
    longer renders through it. Both halves of that swap are silent to every arm
    that only counts.

    This binds the call to its SITE instead: the classification names the
    subject each budgeted call renders (``renders_anchor``) and the identifier
    that carries the rendered value into it (``render_binding``, or ``None``
    when the call is written inline in the anchor line). A substitution has to
    restate a subject that no longer matches — either the anchor line stops
    consuming the render, or the assignment feeding it stops being a render —
    and both are red here.

    Deliberately NOT line numbers: nothing below records where a site lives, so
    ordinary edits above it cost nothing. The anchor is required to be unique in
    the file, because two candidate subject lines make "the" subject line
    ambiguous and the binding unverifiable.
    """
    classification = _load_classification()
    sites = classification['render_sites']

    checked = {'inline': 0, 'bound': 0}
    for site in sites:
        rel = site['file']
        anchor = site['renders_anchor']
        binding = site['render_binding']
        lines = (REPO_ROOT / rel).read_text(encoding='utf-8').splitlines()

        anchor_lines = [ln for ln in lines if anchor in ln]
        assert len(anchor_lines) == 1, (
            f'RENDER file {rel!r} carries {len(anchor_lines)} line(s) containing the '
            f'declared renders_anchor {anchor!r}; exactly one is required. Zero means '
            'the human-facing subject this render is budgeted for no longer exists (or '
            'the anchor has drifted from the source); more than one makes "the subject '
            'line" ambiguous, so no binding could be verified.'
        )
        subject_line = anchor_lines[0]

        if binding is None:
            assert 'render_timestamp(' in subject_line, (
                f'RENDER file {rel!r} declares render_binding: null, meaning its budgeted '
                f'call is written inline in the {anchor!r} line — but that line makes no '
                'render_timestamp(...) call. The budgeted render has been moved off the '
                'subject it is budgeted for, which the render_call_budget count cannot '
                f'see.\n  subject line: {subject_line.strip()!r}'
            )
            checked['inline'] += 1
            continue

        assert '{' + binding + '}' in subject_line, (
            f'RENDER file {rel!r} declares render_binding {binding!r}, but its {anchor!r} '
            f'line does not interpolate {{{binding}}} — so whatever that line now renders, '
            'it is not the value the budgeted render_timestamp(...) call produced.\n'
            f'  subject line: {subject_line.strip()!r}'
        )
        assignment = re.compile(rf'^\s*{re.escape(binding)}\s*=\s*render_timestamp\(')
        assignments = [ln for ln in lines if assignment.match(ln)]
        assert len(assignments) == 1, (
            f'RENDER file {rel!r} has {len(assignments)} assignment(s) of the form '
            f'"{binding} = render_timestamp(...)"; exactly one is required. The '
            f'{anchor!r} line still interpolates {{{binding}}}, so a missing assignment '
            'means that subject is now fed from something OTHER than the display-timezone '
            'render — the knob has quietly stopped reaching the one line it exists to '
            'render, while the budget count stayed exactly as it was.'
        )
        checked['bound'] += 1

    with capsys.disabled():
        print('\n[display-timezone guard] render-site binding:', json.dumps(checked, indent=2))

    # A zero-length render_sites list would make the loop vacuous; the sum also
    # proves every site took one of the two branches rather than being skipped.
    assert sites, 'render_sites is empty — this guard bound nothing.'
    assert checked['inline'] + checked['bound'] == len(sites)


def test_knob_symbols_never_reach_a_store_or_compare_site():
    """Write-path isolation (D4), enforced per SITE rather than per FILE.

    Three assertions, because a knob leak has three shapes and each earlier arm
    is blind to the next:

    1. **Across files** — a knob-consumer symbol in a file that is neither a
       knob owner nor a declared RENDER file is a STORE/COMPARE site consulting
       the display timezone.

    2. **Within a RENDER file, by COUNT** — a declared RENDER file is not wholly
       a render surface. ``manage-metrics.py`` renders ONCE and calls
       ``now_utc_iso()`` nine times, so exempting the file wholesale made every
       one of those store sites invisible: routing one of them through
       ``render_timestamp(...)`` changed nothing this guard could observe. Each
       RENDER file is therefore held to the ``render_call_budget`` re-derived in
       the classification, so spending a render call on a store site is a red
       build.

    3. **Within a RENDER file, by SYMBOL** — the budget is an allowance measured
       in ``render_timestamp(`` calls, so it can only see leaks that spend one.
       A STORE path inside a RENDER file that calls ``read_display_timezone()``
       or ``resolve_display_timezone()`` DIRECTLY spends no budget at all, and
       arm 1 already waved the file through because it is file-granular. The
       leak was therefore invisible to both arms — the same defect class as arm
       2's, one level down. This arm forbids every knob-consumer symbol other
       than ``render_timestamp`` inside a declared RENDER file that is not also
       a knob owner.

    The residual arm 2 cannot close — a same-COUNT substitution that moves the
    budgeted call from the human-facing site to a store site — is closed by
    :func:`test_each_budgeted_render_call_feeds_its_declared_subject`, which
    binds each budgeted call to the SITE it is budgeted for rather than to a
    number.
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

    # Arm 3 (within a RENDER file, per SYMBOL): render_timestamp(...) is the ONLY
    # knob touch a declared RENDER file may make. Arms 1 and 2 together still let a
    # STORE path inside a RENDER file consult the knob DIRECTLY: arm 1 is
    # file-granular, so `allowed` waves through any knob symbol anywhere in the
    # file, and arm 2 counts only `render_timestamp(`, which a direct
    # `read_display_timezone()` / `resolve_display_timezone()` call does not
    # increment. The leak is therefore invisible to both. Reaching the knob through
    # the labelling helper is what makes a render site auditable — a raw read is a
    # store site helping itself to the display zone with no label and no budget.
    knob_owner_files = set(classification['knob_owner_files'])
    render_only = sorted(render_files - knob_owner_files)
    direct_symbols = [sym for sym in symbols if sym != 'render_timestamp']

    # Both populations are asserted, not merely iterated: an empty render_only or
    # an empty direct_symbols would make the loop below examine nothing and pass.
    assert render_only, (
        'Every declared RENDER file is also a knob-owner file, so this arm examined '
        'nothing. A knob owner is exempt by construction, which makes the arm '
        'vacuous rather than clean.'
    )
    assert direct_symbols, (
        'knob_consumer_symbols carries no symbol other than render_timestamp, so '
        'this arm has nothing to forbid and would pass on an empty check.'
    )

    direct_touches = {}
    for rel in render_only:
        text = (REPO_ROOT / rel).read_text(encoding='utf-8')
        hits = [sym for sym in direct_symbols if sym in text]
        if hits:
            direct_touches[rel] = hits

    assert not direct_touches, (
        'Declared RENDER file(s) touch the display-timezone knob DIRECTLY rather '
        'than through render_timestamp(...). A RENDER file is exempt from the '
        'cross-file arm and its budget counts only render_timestamp( calls, so a '
        'raw knob read inside one is a STORE/COMPARE site consulting the display '
        'zone that neither of the other arms can see. Route the site through '
        'render_timestamp(...) — which labels the converted instant and spends '
        'budget — or move it back to the UTC store primitive:\n'
        + json.dumps(direct_touches, indent=2)
    )
