#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Negative-control test for the refine feasibility underivable guard (D3).

The refine phase's feasibility check reasons over ``architecture graph`` output to
validate dependency direction. That reasoning CANNOT fire at zero edges — an
edgeless graph carries no dependency-direction signal. The guard the deliverable
adds is: before treating an empty graph as a clean dependency-direction pass, read
``resolver_count`` to tell the two empties apart.

``resolver_count: 0`` (no resolver ran) means UNDERIVABLE — the empty edge set is
an absence of capability, and a consumer must NOT record a clean pass.
``resolver_count: N`` with empty edges means N resolvers ran and found nothing — a
real answer, and a clean pass is correct.

This is the negative control from the plan's Verification section: a zero-edge
graph produced by "no resolver" must be DISTINGUISHABLE from a zero-edge graph
produced by "a resolver found nothing", asserted by a consumer that applies the
documented guard and classifies the two oppositely — so it CANNOT silently pass on
emptiness.

The document is READ, not paraphrased
-------------------------------------
The guard's only shipped form is prose: ``phase-2-refine/standards/
refine-workflow-detail.md`` § "Step 9 → Feasibility Check" carries the
``**Underivable guard**`` block, and the consumer that applies it is an LLM reading
that block. This module used to model the guard as a local one-line helper and open
no document at all — so deleting the entire guard block from the standard left every
test here green, and the deliverable reverted silently.

The block is now read and BOTH ARMS are asserted against it, and the local helper is
checked to agree with the arms the document declares rather than merely with itself.
Anchored on stable tokens — the ``**Underivable guard`` marker, the two
``resolver_count`` bullet keys, the ``UNDERIVABLE`` classifier, and the exact
``FEASIBILITY: UNDERIVABLE`` finding literal — never on whole sentences, which move
under ordinary rewording. The same shape as the sibling contract-text guards in this
skill's suite, which parse a standards document and assert set-equality against the
code constant.
"""

import re
import tempfile

import extension_discovery

from conftest import MARKETPLACE_ROOT, load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
get_module_graph = _cmd_client.get_module_graph

#: The standards document that carries the guard in its only shipped form.
_GUARD_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-2-refine' / 'standards' / 'refine-workflow-detail.md'
)

#: The guard block's opening token. A bold marker rather than a heading: the guard
#: sits INSIDE § "Feasibility Check" and has no heading of its own, and a heading
#: anchor would drift with any re-sectioning of the step.
_GUARD_MARKER = '**Underivable guard'

#: Line prefixes that terminate the guard block.
_BLOCK_STOP_PREFIXES = ('## ', '### ')

#: An arm of the guard: a bullet keyed on the ``resolver_count`` value it governs.
#: ``0`` and ``N`` are the two keys the discriminator is defined over.
_ARM_BULLET = re.compile(r'^-\s+`resolver_count:\s*([0N])`')

#: The classifier that makes an arm a refusal. Upper-case and load-bearing: the
#: guard's whole content is that ONE of the two empties is not a pass.
_UNDERIVABLE_TOKEN = 'UNDERIVABLE'

#: The exact finding literal the refusing arm instructs the consumer to emit. A
#: HARD copy-target — a consumer emitting an approximation files a finding no
#: downstream reader keys on.
_UNDERIVABLE_FINDING = 'FEASIBILITY: UNDERIVABLE'

#: The permitting arm's positive verdict token.
_CLEAN_PASS_TOKEN = 'clean feasibility pass'


def _guard_block(text: str) -> list[str]:
    """Return the guard block's lines, from its marker to the next heading.

    Pure over ``text`` so the mutation guards can drive it with a synthetic
    document — including one with the block deleted.
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if _GUARD_MARKER in line), None)
    if start is None:
        return []
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith(_BLOCK_STOP_PREFIXES):
            break
        block.append(line)
    return block


def _guard_arms(text: str) -> dict[str, bool]:
    """Return ``{resolver_count_key: dependency_direction_is_derivable}``.

    Derived from the document's own bullets: an arm is a refusal (not derivable)
    exactly when its bullet carries the ``UNDERIVABLE`` classifier. The mapping is
    what the local consumer helper is checked against, so the helper can no longer
    agree only with itself.
    """
    return {
        match.group(1): _UNDERIVABLE_TOKEN not in line
        for line in _guard_block(text)
        if (match := _ARM_BULLET.match(line.strip()))
    }


class _StubResolver:
    """A derivation resolver returning canned ``(edges, notes)``."""

    def __init__(self, resolver_id: str, edges=None):
        self.resolver_id = resolver_id
        self._edges = edges or []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return self._edges, []


def _register(monkeypatch, *resolvers: _StubResolver) -> None:
    records = [{'origin': f'stub-{r.resolver_id}', 'id': r.resolver_id, 'module': r} for r in resolvers]
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


def _seed(tmpdir: str, names: list[str]) -> None:
    save_project_meta(
        {
            'name': 'feasibility-fixture',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in names},
        },
        tmpdir,
    )
    for name in names:
        save_module_derived(
            name,
            {
                'name': name,
                'paths': {'module': name},
                'dependencies': ['org.example:external:compile'],
                'commands': {},
            },
            tmpdir,
        )


def _dependency_direction_derivable(graph_result: dict) -> bool:
    """The documented refine guard, modelled as the consumer applies it.

    Dependency-direction reasoning is derivable iff a resolver ran — otherwise the
    empty edge set is UNDERIVABLE, not a clean pass. This mirrors the instruction
    in phase-2-refine's Feasibility Check: the check a consumer performs BEFORE
    reading the edges.

    ⚠ This helper is a MODEL, not the guard. The guard ships as prose, and
    ``test_local_consumer_model_matches_the_documented_arms`` below is what ties
    the two together — without it this function agrees only with itself and the
    document could be deleted underneath it.
    """
    return bool(graph_result['resolver_count'] > 0)


def test_zero_resolver_graph_is_underivable_not_a_clean_pass(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, ['api', 'core', 'app'])
        # No resolver registered → the underivable case.
        monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])

        graph = get_module_graph(tmpdir)

        assert graph['edges'] == []
        assert graph['resolver_count'] == 0
        # The guard refuses to treat this empty graph as a clean pass.
        assert _dependency_direction_derivable(graph) is False


def test_resolver_present_empty_graph_is_a_genuine_pass(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, ['api', 'core', 'app'])
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        graph = get_module_graph(tmpdir)

        # Same empty edge set — but a resolver ran, so the guard permits a pass.
        assert graph['edges'] == []
        assert graph['resolver_count'] == 1
        assert _dependency_direction_derivable(graph) is True


def test_the_two_empty_graphs_are_classified_oppositely(monkeypatch):
    """The core negative control: identical empty edges, opposite guard verdicts.

    A consumer that ignored ``resolver_count`` would silently pass BOTH as clean —
    exactly the vacuous-consumer failure this deliverable closes.
    """
    with tempfile.TemporaryDirectory() as underivable, tempfile.TemporaryDirectory() as derived_nothing:
        _seed(underivable, ['api', 'core'])
        _seed(derived_nothing, ['api', 'core'])

        monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])
        empty_no_resolver = get_module_graph(underivable)

        _register(monkeypatch, _StubResolver('maven', edges=[]))
        empty_with_resolver = get_module_graph(derived_nothing)

        # Byte-identical empty edge sets ...
        assert empty_no_resolver['edges'] == empty_with_resolver['edges'] == []
        # ... classified oppositely, so the consumer cannot silently pass emptiness.
        assert _dependency_direction_derivable(empty_no_resolver) is False
        assert _dependency_direction_derivable(empty_with_resolver) is True


# =============================================================================
# The guard's shipped form: the standards document itself.
#
# Every assertion above runs against a locally-defined helper, so deleting the
# whole guard block from refine-workflow-detail.md left them green. The consumer
# that actually applies the guard is an LLM reading that block, which makes the
# block the artifact under test.
# =============================================================================


def test_the_guard_block_is_present_and_declares_both_arms():
    """Both arms exist in the document, keyed on the discriminator field.

    A deleted or renamed block yields no arms, and the assertions below say so
    rather than passing over an empty parse — the vacuity mode this guard is
    itself about.
    """
    text = _GUARD_DOC.read_text(encoding='utf-8')

    block = _guard_block(text)
    arms = _guard_arms(text)

    assert block, (
        f'the {_GUARD_MARKER!r} block is absent from {_GUARD_DOC} — the underivable '
        'guard has been deleted or renamed, and every consumer of an empty '
        '`architecture graph` is back to reading it as a clean dependency-direction '
        'pass'
    )
    assert set(arms) == {'0', 'N'}, (
        f'the guard must declare BOTH resolver_count arms; parsed {sorted(arms)} '
        f'from {_GUARD_DOC}. One arm alone states no discriminator — it is exactly '
        'the unqualified empty graph the guard exists to reject.'
    )


def test_the_zero_resolver_arm_refuses_and_names_its_finding():
    text = _GUARD_DOC.read_text(encoding='utf-8')
    block_text = '\n'.join(_guard_block(text))

    arms = _guard_arms(text)

    assert arms['0'] is False, (
        'the `resolver_count: 0` arm no longer classifies dependency direction as '
        'UNDERIVABLE — an absent capability would be recorded as a passed '
        'feasibility gate'
    )
    assert _UNDERIVABLE_FINDING in block_text, (
        f'the refusing arm no longer instructs the consumer to emit '
        f'{_UNDERIVABLE_FINDING!r}. The literal is a hard copy-target: a consumer '
        'emitting an approximation files a finding no downstream reader keys on.'
    )


def test_the_resolver_present_arm_permits_a_clean_pass():
    text = _GUARD_DOC.read_text(encoding='utf-8')
    block_text = '\n'.join(_guard_block(text))

    arms = _guard_arms(text)

    assert arms['N'] is True, (
        'the `resolver_count: N` arm now classifies a resolver-backed empty graph '
        'as UNDERIVABLE too — that collapses the discriminator, and a guard that '
        'refuses both empties is as blind as one that passes both'
    )
    assert _CLEAN_PASS_TOKEN in block_text, (
        f'the permitting arm no longer states {_CLEAN_PASS_TOKEN!r} — without a '
        'positive verdict the arm says only what it is not'
    )


def test_local_consumer_model_matches_the_documented_arms():
    """The local helper's verdicts are the DOCUMENT's verdicts, not its own.

    This is the tie that makes every assertion above this section meaningful: the
    helper's two branches are checked against the two arms parsed out of the
    standard, so a document that inverts (or drops) an arm reddens here instead of
    leaving the model quietly disagreeing with the guard it claims to mirror.
    """
    arms = _guard_arms(_GUARD_DOC.read_text(encoding='utf-8'))

    assert _dependency_direction_derivable({'resolver_count': 0}) is arms['0']
    assert _dependency_direction_derivable({'resolver_count': 1}) is arms['N']
    assert _dependency_direction_derivable({'resolver_count': 7}) is arms['N']


def test_guard_parser_fires_on_the_deleted_and_inverted_block():
    # Mutation guard: the reads above are only meaningful if the parser actually
    # notices the two ways the guard can regress — deletion, and inversion.
    live = _GUARD_DOC.read_text(encoding='utf-8')

    deleted = '\n'.join(line for line in live.splitlines() if line not in set(_guard_block(live)))
    assert _guard_block(deleted) == [], (
        'the block parser still finds a guard after every one of its lines was removed — it would not notice a deletion'
    )
    assert _guard_arms(deleted) == {}, 'the arm parser still reports arms after the block was deleted'

    inverted = '\n'.join(
        [
            '**Underivable guard — synthetic inversion fixture.**',
            '',
            '- `resolver_count: 0` — no resolver ran, so there are no edges to '
            'contradict the request. A clean feasibility pass is correct here.',
            '- `resolver_count: N` (N ≥ 1) with empty edges — treat dependency direction as **UNDERIVABLE**.',
            '',
            '### Next Section',
        ]
    )
    inverted_arms = _guard_arms(inverted)
    assert inverted_arms == {'0': True, 'N': False}, (
        f'the arm parser did not read the inverted fixture as inverted: {inverted_arms}'
    )
    # ... and the local model DISAGREES with the inverted document, which is the
    # disagreement `test_local_consumer_model_matches_the_documented_arms` reports.
    assert _dependency_direction_derivable({'resolver_count': 0}) is not inverted_arms['0']
    assert _dependency_direction_derivable({'resolver_count': 1}) is not inverted_arms['N']
