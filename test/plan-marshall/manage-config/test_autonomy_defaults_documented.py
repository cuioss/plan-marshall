#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The documented autonomy-gate default set equals the declared default set.

Six knobs decide whether a plan run pauses for the operator: the five flat
``*_without_asking`` gates and the step-owned ``final_merge_without_asking``.
Each has exactly one declaring source — the ``DEFAULT_PLAN_*`` blocks in
``_config_defaults.py`` for the flat five, and ``default:branch-cleanup``'s
``configurable:`` frontmatter (reached through ``configurable_contract``) for the
merge gate. Each is then restated in prose across the documentation as a JSON
example, a table row, or a sentence.

A restatement that disagrees with its declaring source is worse than an omission:
an operator reading it configures against a default the code does not have, and a
reader obeying the project's quote-it-verbatim rule copies the wrong literal. This
module keeps the copies honest — it derives the declared value and asserts every
documented restatement of that knob states it, so drift fails a build instead of
shipping.

BOTH sides are derived, never hand-listed. The declared side is discovered from
the seeded config; the documented side is discovered by walking the documentation
roots in :data:`_DOC_ROOTS` and keeping every file an extractor matches. A
hand-maintained document tuple would leave a restatement unguarded the moment one
was added elsewhere — which is exactly what "asserts every restatement" must not
mean.

The guarantee is therefore bounded by the walk, and by nothing else: it covers
every ``.md`` under ``marketplace/bundles`` and every ``.md`` / ``.adoc`` under
``doc``. A restatement outside those two roots — a repo-root file, ``.claude/``,
``.github/`` — is not reached. No such site exists today; the bound is stated so a
future one is recognised as out of guard rather than assumed covered.

Two sites deliberately state the OPPOSITE value: they illustrate non-destructive
merge by showing a user-set value surviving the opposite default, so flipping them
would turn the illustration into a tautology. The one in ``manage-config/SKILL.md``
is cut out by the region assertion below; the one in ``test_sync_defaults.py`` is
out by construction, because no test module is under a documentation root.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

import pytest

from conftest import load_script_module

# repo_root/test/plan-marshall/manage-config/test_autonomy_defaults_documented.py
#                                          ^ parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]

_config_defaults_mod = load_script_module(
    'plan-marshall',
    'manage-config',
    '_config_defaults.py',
    module_name='_config_defaults_for_autonomy_defaults_documented',
)

#: The step that owns the one non-flat member of the family.
_MERGE_GATE = 'final_merge_without_asking'
_MERGE_GATE_STEP = 'default:branch-cleanup'

#: One knob that must survive every derivation and every scan. A regex that
#: silently stops matching yields an empty set, and an empty-set assertion passes
#: while covering nothing — the anchors are what make that failure visible.
_ANCHOR_KNOB = 'loop_back_without_asking'
_ANCHOR_DOC = 'doc/user/configuration.adoc'

#: The documentation roots walked to derive the guarded population, each paired
#: with the glob patterns that select its documents. Repo-root-relative. Both are
#: documentation trees, so no test module is reachable from either — which is what
#: makes :func:`test_the_documented_population_is_documentation_only` a guarantee
#: of construction rather than a maintained exclusion list. These two roots are
#: also the exact bound on this module's coverage claim; see the module docstring.
_DOC_ROOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('marketplace/bundles', ('**/*.md',)),
    ('doc', ('**/*.md', '**/*.adoc')),
)

#: The polarity illustration in ``manage-config/SKILL.md``: a user-set value
#: surviving the OPPOSITE default, proving the deep merge preserves what the
#: operator set. Its stated boolean is intentionally the negation of the declared
#: default, so it is cut out of the parse rather than asserted against. Anchored on
#: its own wording so a rewrite fails :func:`test_polarity_illustration_is_present`
#: instead of silently re-entering the parse.
_POLARITY_REGION_RE = re.compile(
    r'- A key already present in the live config is preserved unchanged\.'
    r'.*?survives even when the default is `(?:true|false)`\.',
    re.DOTALL,
)


def _read(document: str) -> str:
    """Return the text of a document addressed by its repo-root-relative path."""
    return (_REPO_ROOT / document).read_text(encoding='utf-8')


@cache
def _parseable_text(document: str) -> str:
    """Return the document text with every excluded region removed.

    Cached because the derivation scans every candidate document once per knob,
    and the parity checks then re-scan the surviving population once per case.
    """
    text = _read(document)
    return _POLARITY_REGION_RE.sub('', text)


def _declared_defaults() -> dict[str, bool]:
    """Return every autonomy-gate knob mapped to its declared default.

    The flat members are DISCOVERED by walking the seeded ``plan`` block for keys
    ending in ``_without_asking``, rather than restated as a tuple here — a tuple
    would be one more copy of the very set this module exists to keep from
    drifting, and a newly-added gate would go unguarded until someone remembered
    to register it. The merge gate is added explicitly because it is not flat: it
    lives in its owning step's ``configurable:`` frontmatter, and is resolved
    through the parser that owns that contract rather than re-parsed here.
    """
    from configurable_contract import resolve_step_defaults_optional

    declared: dict[str, bool] = {}
    for phase_block in _config_defaults_mod.get_default_config()['plan'].values():
        if not isinstance(phase_block, dict):
            continue
        for knob, value in phase_block.items():
            if knob.endswith('_without_asking'):
                declared[knob] = value

    step_defaults = resolve_step_defaults_optional(_MERGE_GATE_STEP) or {}
    declared[_MERGE_GATE] = step_defaults[_MERGE_GATE]
    return declared


def _json_example_re(knob: str) -> re.Pattern[str]:
    """A knob rendered as a key in a ``marshal.json`` example block."""
    return re.compile(rf'"{re.escape(knob)}"\s*:\s*(true|false)')


def _table_row_re(knob: str) -> re.Pattern[str]:
    """A knob rendered as the first cell of a table row whose next cell is its default.

    The optional ``bool`` segment absorbs the four-column ``| knob | type | default |``
    shape used by the schema tables, so the same pattern reads both column layouts.
    """
    return re.compile(
        rf'\|[^|\n]*`[^`\n]*(?<![a-z_]){re.escape(knob)}`[^|\n]*\|'
        r'(?:\s*bool\s*\|)?'
        r'\s*`?(true|false)`?\s*\|'
    )


def _prose_default_re(knob: str) -> re.Pattern[str]:
    """A knob followed on the same line by a sentence naming its default."""
    return re.compile(
        rf'(?<![a-z_]){re.escape(knob)}[^\n]{{0,80}}?default[^\n]{{0,20}}?`(true|false)`'
    )


_EXTRACTORS = (
    ('json-example', _json_example_re),
    ('table-row', _table_row_re),
    ('prose-default', _prose_default_re),
)


def _documented_values(document: str, knob: str) -> list[tuple[str, str]]:
    """Return every ``(shape, value)`` this document states for ``knob``."""
    text = _parseable_text(document)
    found: list[tuple[str, str]] = []
    for shape, build in _EXTRACTORS:
        found.extend((shape, value) for value in build(knob).findall(text))
    return found


def _family() -> list[str]:
    """Return the knob names of the autonomy-gate family, sorted for stable ids."""
    return sorted(_declared_defaults())


def _candidate_documents() -> tuple[str, ...]:
    """Return every document under :data:`_DOC_ROOTS`, repo-root-relative and sorted."""
    paths = {
        path
        for root, patterns in _DOC_ROOTS
        for pattern in patterns
        for path in (_REPO_ROOT / root).glob(pattern)
        if path.is_file()
    }
    return tuple(sorted(path.relative_to(_REPO_ROOT).as_posix() for path in paths))


def _derive_documents() -> tuple[str, ...]:
    """Return every candidate document that restates at least one family default.

    This is the documented half of the parity, DISCOVERED rather than listed. A
    hand-maintained tuple would guard only the sites someone remembered to
    register, so a restatement added to a document nobody registered would ship
    unguarded while the module still claimed to cover every one.
    """
    knobs = _family()
    return tuple(
        document
        for document in _candidate_documents()
        if any(_documented_values(document, knob) for knob in knobs)
    )


_DOCUMENTS = _derive_documents()


def test_the_declared_family_is_derived_and_not_silently_empty():
    """The declaring sources yield the whole family, so the parity checks are not vacuous.

    The two wrong answers both look like success: an empty family parametrizes
    zero cases and reports green while checking nothing, and a family missing the
    merge gate would silently drop the one member whose declaring source is a
    step's frontmatter rather than ``_config_defaults.py``.
    """
    declared = _declared_defaults()

    assert _ANCHOR_KNOB in declared
    assert _MERGE_GATE in declared
    assert len(declared) >= 6, f'family shrank unexpectedly: {sorted(declared)}'
    for knob, value in declared.items():
        assert isinstance(value, bool), f'{knob} must declare a bool, got {value!r}'


@pytest.mark.parametrize('document', _DOCUMENTS)
@pytest.mark.parametrize('knob', _family())
def test_documented_default_equals_declared_default(document, knob):
    """Every restatement of a knob's default states the value its source declares."""
    expected = 'true' if _declared_defaults()[knob] else 'false'

    for shape, value in _documented_values(document, knob):
        assert value == expected, (
            f'{document} states {knob} default as `{value}` via its {shape}, '
            f'but the declaring source says `{expected}`'
        )


@pytest.mark.parametrize('knob', _family())
def test_every_declared_knob_has_a_documented_row(knob):
    """A declared gate with no documented restatement anywhere is undiscoverable.

    An operator cannot configure a knob they cannot find, so an unmentioned gate
    is a documentation defect even though nothing contradicts it.
    """
    sites = [
        (document, shape, value)
        for document in _DOCUMENTS
        for shape, value in _documented_values(document, knob)
    ]

    assert sites, f'{knob} is declared but restated in no document under {[r for r, _ in _DOC_ROOTS]}'


def test_the_derived_population_is_not_silently_empty():
    """The walk reaches both roots and yields a population to run the parity over.

    Every parity assertion is parametrized over the derived population, so a
    mistyped root or a glob that stops matching reports green while covering
    nothing. Each assertion below is one of the ways that can happen: a root that
    yields no candidate files at all, and a root that contributes no restating
    document to the population.
    """
    candidates = _candidate_documents()

    for root, _ in _DOC_ROOTS:
        assert any(d.startswith(f'{root}/') for d in candidates), f'{root} yielded no candidates'
        assert any(d.startswith(f'{root}/') for d in _DOCUMENTS), f'{root} contributed no restatement'
    assert _ANCHOR_DOC in _DOCUMENTS


def test_the_scan_finds_the_anchor_so_the_extractors_still_match():
    """The anchor knob is extracted from the anchor document by a real extractor.

    Every parity assertion above is a for-loop over extracted values, so all three
    pass trivially the moment the extractors stop matching. This is the assertion
    that fails instead.
    """
    found = _documented_values(_ANCHOR_DOC, _ANCHOR_KNOB)

    assert found, f'no extractor matched {_ANCHOR_KNOB} in {_ANCHOR_DOC}'
    assert {value for _, value in found} == {'true'}


def test_polarity_illustration_is_present_and_excluded_from_the_parse():
    """The polarity illustration exists, names the merge gate, and is cut from the parse.

    It states the negation of the declared default on purpose — a user-set value
    surviving the opposite default is what proves the merge is non-destructive.
    Asserting the region is FOUND keeps the exclusion from decaying into a no-op:
    if the passage is reworded, this fails and forces the anchor to be re-cut
    rather than letting the passage silently re-enter the parse and fail as drift.
    """
    document = 'marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md'
    raw = _read(document)

    region = _POLARITY_REGION_RE.search(raw)
    assert region is not None, (
        f'{document} no longer carries the polarity illustration this module '
        'excludes; re-anchor _POLARITY_REGION_RE on its current wording'
    )
    assert _MERGE_GATE in region.group(0)
    assert region.group(0) not in _parseable_text(document)


def test_the_documented_population_is_documentation_only():
    """The parse covers documents under the declared roots, never test modules.

    ``test_sync_defaults.py`` carries the second polarity illustration. It is out
    of scope by construction rather than by exclusion — no test module lives under
    a documentation root — and this pins that, so widening :data:`_DOC_ROOTS`
    cannot quietly pull a test file into the documented side.
    """
    roots = tuple(f'{root}/' for root, _ in _DOC_ROOTS)

    for document in _DOCUMENTS:
        assert not document.startswith('test/'), f'{document} is a test path'
        assert document.endswith(('.md', '.adoc')), f'{document} is not a document'
        assert document.startswith(roots), f'{document} is outside {list(roots)}'
