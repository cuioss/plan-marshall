#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract-text agreement across the ``derive_gate_bundles`` unresolved-path sites.

The rule that a footprint path which matched a ``build_map`` glob but resolves
to no bundle is REPORTED in ``unresolved[]`` — never silently dropped — is
declared at three independent sites, and a reader may arrive at any one of
them:

1. the ``derive_gate_bundles.py`` module docstring's derivation rules,
2. the ``derive_gate_bundles()`` function docstring's ``Returns`` description,
3. ``standards/pre-push-quality-gate.md`` section "Derive unique bundle set".

Each is read LIVE from its own source here, so a site that drifts out of
agreement fails rather than being reconciled by a reader who happens to have
read a different one. The population is the site list itself, published in
every failure message and in the session report header, because a sweep that
silently lost a site would otherwise pass over the two that remain.

**Scope — the CONTRACT-TEXT dimension only.** The runtime behavioural pair (the
consumer-shaped negative AND its matched positive control, exercised against the
real ``marketplace/bundles/`` tree) is owned solely by
``test_derive_gate_bundles.py``, which declares that ownership in its own module
docstring. Nothing here re-asserts it: this module reads prose and the shape of
the fall-through branch, never the seam's verdict over a footprint.

Every property assertion below is paired with a mutation guard that runs its
detector against the known pre-fix prose, so a typo in a detector fails loudly
instead of making the property vacuously green.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable

import pytest

from _dispatch_roster import section_lines
from conftest import MARKETPLACE_ROOT, get_script_path, load_script_module

# ---------------------------------------------------------------------------
# The three declaring sites, each read live from its own source
# ---------------------------------------------------------------------------

#: Loaded with an explicitly named binding rather than a star-unpack, and with
#: ``register=False`` so this module's load cannot displace the ``sys.modules``
#: entry ``test_derive_gate_bundles.py`` publishes for the same script.
_derive_module = load_script_module(
    'plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py', register=False
)

_SCRIPT_PATH = get_script_path(
    'plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py'
)

_GATE_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'pre-push-quality-gate.md'
)

_DERIVE_HEADING = '### Derive unique bundle set'
_STOP_PREFIXES = ('### ', '## ', '# ', '---')


def _module_docstring() -> str:
    """Site 1 — the script's module docstring, carrying the derivation rules."""
    return str(_derive_module.__doc__ or '')


def _function_docstring() -> str:
    """Site 2 — the ``derive_gate_bundles()`` docstring's ``Returns`` description."""
    return str(_derive_module.derive_gate_bundles.__doc__ or '')


def _standard_section() -> str:
    """Site 3 — the gate standard's "Derive unique bundle set" section."""
    text = _GATE_DOC.read_text(encoding='utf-8')
    return '\n'.join(section_lines(text, _DERIVE_HEADING, _STOP_PREFIXES))


#: ``(site_name, reader)`` for every site declaring the unresolved-path rule.
#: The population every cardinality below is derived from — no assertion writes
#: a literal count, so removing a site fails here rather than shrinking the
#: sweep silently.
_SITES: tuple[tuple[str, Callable[[], str]], ...] = (
    ('derive_gate_bundles.py module docstring', _module_docstring),
    ('derive_gate_bundles() Returns docstring', _function_docstring),
    (f'pre-push-quality-gate.md {_DERIVE_HEADING!r}', _standard_section),
)

#: The two sites that state rule 4 EXPLICITLY. The standard deliberately does
#: not — it says "The derivation rule lives in exactly one place ... Do NOT
#: restate it here" — so this is a real subset of ``_SITES`` rather than an
#: oversight, and it is derived by naming the sites that carry the statement
#: rather than by assuming every site does.
_RULE_FOUR_SITES: tuple[str, ...] = (
    'derive_gate_bundles.py module docstring',
    'derive_gate_bundles() Returns docstring',
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The non-emptiness assertions below fail an EMPTY
#: population, but a population that merely SHRANK still passes them; publishing
#: the size on the green run is what makes that shrink visible.
GUARD_POPULATION_LABEL = 'derive_gate_bundles unresolved-rule declaration sites'
GUARD_POPULATION_SIZE = len(_SITES)


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

#: The shared claim every site must carry: a path that resolves to no bundle is
#: never dropped in silence. Matched as a NEGATED-drop phrase, because the
#: affirmative token ("silent drop") appears inside every correct site as the
#: thing being denied — a bare substring test for it would fire on the fix.
_NEVER_SILENTLY_DROPPED = re.compile(
    r'never\s+(?:a\s+)?silent(?:ly)?\s+drop(?:ped)?', re.IGNORECASE
)

#: Rule 4's own statement: a path of ANY OTHER SHAPE reaches ``unresolved``.
_ANY_OTHER_SHAPE = re.compile(r'any\s+other\s+shape', re.IGNORECASE)

#: The pre-fix inline comment the fix replaced. A literal, because the literal
#: IS what regressing would restore — a looser pattern would pass on prose that
#: merely discusses the old behaviour.
_PRE_FIX_COMMENT = '# Any other shape contributes no bundle (silent drop by rule 4).'


def _reads(site_name: str) -> str:
    """Return the live text of one declaring site by name."""
    for name, reader in _SITES:
        if name == site_name:
            return reader()
    raise AssertionError(f'Unknown site: {site_name!r}')


def _sites_missing(pattern: re.Pattern[str]) -> list[str]:
    """Site names whose live text does not match ``pattern``."""
    return [name for name, reader in _SITES if not pattern.search(reader())]


# ---------------------------------------------------------------------------
# Vacuity floor — every site must actually yield text
# ---------------------------------------------------------------------------


def test_declaring_site_population_is_non_empty():
    assert _SITES, (
        'No declaring site is registered, so every agreement assertion below '
        'would sweep an empty population and pass vacuously'
    )


@pytest.mark.parametrize('site_name', [name for name, _reader in _SITES])
def test_every_declaring_site_yields_text(site_name):
    """A site that reads back empty makes every claim about it vacuous."""
    text = _reads(site_name)

    assert text.strip(), (
        f'Declaring site {site_name!r} read back empty across a population of '
        f'{len(_SITES)} site(s) — every agreement assertion over it would be '
        f'vacuously green'
    )


# ---------------------------------------------------------------------------
# The three sites agree with each other
# ---------------------------------------------------------------------------


def test_every_site_names_the_unresolved_list():
    missing = [name for name, reader in _SITES if 'unresolved' not in reader()]

    assert not missing, (
        f'These declaring sites do not name the `unresolved` list at all, so a '
        f'reader arriving at one of them never learns the path is reported: '
        f'{missing} (population: {len(_SITES)} site(s))'
    )


def test_every_site_states_the_path_is_never_silently_dropped():
    missing = _sites_missing(_NEVER_SILENTLY_DROPPED)

    assert not missing, (
        f'These declaring sites state no "never a silent drop" claim, so they '
        f'no longer agree with their siblings on the rule that makes the gate '
        f'diagnosable: {missing} (population: {len(_SITES)} site(s))'
    )


def test_rule_four_is_stated_explicitly_where_it_is_declared():
    """Both docstring sites state rule 4; the standard defers to them by design.

    The subset is derived from ``_RULE_FOUR_SITES`` rather than assumed over
    ``_SITES``: asserting it of all three would fail the standard for obeying
    its own "the derivation rule lives in exactly one place" instruction.
    """
    assert _RULE_FOUR_SITES, 'No rule-4 site registered — the sweep would be vacuous'

    missing = [
        name for name in _RULE_FOUR_SITES if not _ANY_OTHER_SHAPE.search(_reads(name))
    ]

    assert not missing, (
        f'These sites declare rule 4 but no longer state that a path of any '
        f'OTHER shape reaches `unresolved`: {missing} '
        f'({len(_RULE_FOUR_SITES)} of {len(_SITES)} sites declare it)'
    )


def test_rule_four_sites_are_a_real_subset_of_the_declaring_sites():
    """The rule-4 subset is drawn from the site population, not invented.

    Without this, a typo in ``_RULE_FOUR_SITES`` would name a site that does not
    exist, and the sweep above would iterate a set unrelated to the documents
    actually shipped.
    """
    known = {name for name, _reader in _SITES}
    unknown = [name for name in _RULE_FOUR_SITES if name not in known]

    assert not unknown, (
        f'These rule-4 site names are not declaring sites at all: {unknown}. '
        f'Known sites: {sorted(known)}'
    )
    assert len(_RULE_FOUR_SITES) < len(_SITES), (
        'Every site is registered as stating rule 4 explicitly, which would '
        'make the deferring-standard case unrepresented and the subset '
        'distinction meaningless'
    )


# ---------------------------------------------------------------------------
# The sites agree with the shipped fall-through SHAPE
#
# Structural only. Whether the seam actually routes a consumer-shaped footprint
# into ``unresolved`` is the behavioural pair test_derive_gate_bundles.py owns.
# ---------------------------------------------------------------------------


def test_the_fall_through_branch_reports_rather_than_drops():
    source = inspect.getsource(_derive_module.derive_gate_bundles)

    assert '\n        else:\n' in source, (
        'derive_gate_bundles() no longer carries a terminal `else:` branch, so '
        'a path matching none of the earlier shapes falls off the end of the '
        'chain contributing nothing — the silent drop the three sites deny'
    )
    tail = source.rsplit('\n        else:\n', 1)[1]
    assert 'unresolved.append' in tail, (
        'The terminal `else:` branch of derive_gate_bundles() does not append '
        'to `unresolved`, so the documented rule-4 disposition and the shipped '
        'fall-through disagree'
    )


def test_the_pre_fix_silent_drop_comment_is_absent_from_the_script():
    source = _SCRIPT_PATH.read_text(encoding='utf-8')

    assert _PRE_FIX_COMMENT not in source, (
        f'The pre-fix comment {_PRE_FIX_COMMENT!r} is back in '
        f'{_SCRIPT_PATH.name} — the fall-through is documented at the code site '
        f'as a silent drop again'
    )


# ---------------------------------------------------------------------------
# Mutation guards — each detector must fire on the known pre-fix prose
# ---------------------------------------------------------------------------


def test_never_silently_dropped_detector_separates_the_two_wordings():
    pre_fix = (
        '4. Any other shape contributes no bundle (silent drop by rule 4).\n'
    )
    post_fix = (
        '3. ``test/<b>/...`` -> the path is appended to ``unresolved[]`` — '
        'never silently dropped, never a hard failure.\n'
    )

    assert not _NEVER_SILENTLY_DROPPED.search(pre_fix), (
        'The negated-drop detector fires on the pre-fix prose, so the '
        'agreement assertion would stay green across the regression it exists '
        'to catch'
    )
    assert _NEVER_SILENTLY_DROPPED.search(post_fix), (
        'The negated-drop detector does not fire on the shipped wording, so '
        'the agreement assertion would fail for the wrong reason'
    )


def test_any_other_shape_detector_fires_on_both_wordings_of_rule_four():
    # Positive control: the shipped statement of rule 4.
    assert _ANY_OTHER_SHAPE.search(
        'Any other shape resolves to no bundle and is appended to unresolved[].'
    )
    # And on the pre-fix one, so the rule-4 sweep is measuring the RULE's
    # presence rather than the fix's wording.
    assert _ANY_OTHER_SHAPE.search(
        'Any other shape contributes no bundle (silent drop by rule 4).'
    )
    # Negative control: prose that declares no rule-4 disposition at all.
    assert not _ANY_OTHER_SHAPE.search(
        'Skip the path when it matches none of the build_map globs.'
    )


def test_pre_fix_comment_detector_fires_on_a_synthetic_regression():
    # The regression is written out LITERALLY, never interpolated from
    # ``_PRE_FIX_COMMENT``. Building it with an f-string would make the positive
    # control below ``x in f'...{x}...'`` — true for every possible value of the
    # constant, so it would pass even if the constant were edited to a spelling
    # the real sweep can no longer find. An independently-written literal is what
    # gives this control something to disagree with.
    regressed = (
        '        else:\n'
        '            # Any other shape contributes no bundle (silent drop by '
        'rule 4).\n'
        '            continue\n'
    )

    assert _PRE_FIX_COMMENT in regressed, (
        'The pre-fix comment detector would not fire on a synthetic '
        'regression, so the absence assertion above would be vacuous. Either '
        '_PRE_FIX_COMMENT no longer spells the comment the fix replaced, or '
        'this control has drifted from it.'
    )
    assert _PRE_FIX_COMMENT not in (
        '        else:\n'
        '            # Rule 4. The path matched a build_map glob but is '
        'neither shape, so it is REPORTED rather than dropped.\n'
        '            unresolved.append(path)\n'
    )
