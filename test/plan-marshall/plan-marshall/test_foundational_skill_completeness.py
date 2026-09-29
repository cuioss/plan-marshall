#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every declared foundational skill resolves in the marketplace source.

The load-or-fail-closed rule (see
``marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md``
§ "Foundational Skills: load or fail closed") says a foundational skill that
cannot be loaded ABORTS the phase. A rule no gate enforces is a preference, and
the failure it exists to prevent is silent: a body naming a skill that does not
exist runs its own steps with the rules that skill carried simply absent, and
produces plausible output while doing so. Nothing downstream can tell that
difference from a correct run.

So this module is the gate. It walks the marketplace, finds every body carrying a
``## Foundational Practices`` block, and fails when a block names a skill the
marketplace does not ship.

Three properties are load-bearing, and each closes a specific way the check
could otherwise pass while proving nothing:

- **The population is re-derived every run, AND pinned.** The bodies are
  discovered from the tree and compared against a named roster, so the two must
  agree in BOTH directions: a body beyond the named roster that carries the block
  is not a silent addition, it is a red build that names itself and demands a
  roster edit. A discovery alone would let a new body in unreviewed; a roster
  alone would go stale in the direction that hides.
- **An unresolvable notation FAILS — it does not skip, and it does not fall back
  to a default.** A guard that skips what it cannot check reports the same green
  for "everything resolves" and "the check could not run".
- **The registry is the live marketplace tree, not a restated skill list.** A
  restated list goes stale in the direction that hides: a skill deleted from the
  marketplace keeps resolving against the copy the guard still carries.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from _foundational_skills import (
    MARKETPLACE_ROOT,
    extract_foundational_notations,
    foundational_section,
    resolve_notation,
)

#: The bodies that carry a ``## Foundational Practices`` block in the marketplace
#: SOURCE today. Named so a reader can see the population at a glance and so the
#: assertion below fails LOUDLY in either direction when the population moves: an
#: empty walk satisfies "every body resolves" vacuously, which is the same
#: silent-green this module exists to prevent.
#:
#: SOURCE, not deployment: every body that carries the block in a generated
#: target tree is a mirror of one that carries it here, so reading the deployed
#: copies into this list would make the guard's population a function of whether
#: somebody last ran the generator. (The reverse is not symmetric: a target may
#: legitimately omit a body — the antigravity and opencode trees carry no
#: ``recipe-surgical-fix`` — which is why the deployed trees are swept by their
#: own module.) A body that gains the block in SOURCE lands in the
#: ``found - expected`` direction of the drift assertion below, which is the
#: direction that matters — that is a new surface nobody has assessed yet.
EXPECTED_FOUNDATIONAL_BODIES: tuple[str, ...] = (
    'plan-marshall/skills/automatic-review/SKILL.md',
    'plan-marshall/skills/execute-task/SKILL.md',
    'plan-marshall/skills/phase-1-init/SKILL.md',
    'plan-marshall/skills/phase-2-refine/SKILL.md',
    'plan-marshall/skills/phase-3-outline/SKILL.md',
    'plan-marshall/skills/phase-4-plan/SKILL.md',
    'plan-marshall/skills/phase-5-execute/SKILL.md',
    'plan-marshall/skills/plan-orchestrator/SKILL.md',
    'plan-marshall/skills/plan-retrospective/SKILL.md',
    'plan-marshall/skills/recipe-code-review/SKILL.md',
    'plan-marshall/skills/recipe-lesson-cleanup/SKILL.md',
    'plan-marshall/skills/recipe-security-audit/SKILL.md',
    'plan-marshall/skills/recipe-surgical-fix/SKILL.md',
    'pm-plugin-development/skills/recipe-fix-argparse-rejection/SKILL.md',
)


def _relative(path: Path) -> str:
    return path.relative_to(MARKETPLACE_ROOT).as_posix()


def discover_foundational_bodies() -> dict[str, str]:
    """Map every marketplace body carrying the block to its source text.

    Discovered from the tree, never listed, so a body that gains the block after
    this module was written is PICKED UP on the next run — and then fails the
    two-directional comparison against :data:`EXPECTED_FOUNDATIONAL_BODIES`,
    naming itself and demanding the roster edit that assesses it.
    """
    bodies: dict[str, str] = {}
    for path in sorted(MARKETPLACE_ROOT.rglob('*.md')):
        if path.name not in ('SKILL.md',) and path.suffix != '.md':
            continue
        if path.parts[-3:-1] and 'skills' not in path.parts and 'agents' not in path.parts:
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        if foundational_section(text) is not None:
            bodies[_relative(path)] = text
    return bodies


@pytest.fixture(scope='module')
def bodies() -> dict[str, str]:
    return discover_foundational_bodies()


class TestPopulationIsReal:
    def test_the_block_is_still_carried_by_the_expected_bodies(self, bodies: dict[str, str]) -> None:
        """The walk found every body the tree actually carries the block on.

        A guard whose population silently emptied passes every other assertion in
        this module while checking nothing, so the population is asserted
        positively — and asserted as a set difference rather than a count, so the
        failure names which body moved.
        """
        found = set(bodies)
        expected = set(EXPECTED_FOUNDATIONAL_BODIES)
        assert expected - found == set(), f'bodies no longer carry the block: {sorted(expected - found)}'
        assert found - expected == set(), (
            f'new bodies carry the block and are unassessed — add them to '
            f'EXPECTED_FOUNDATIONAL_BODIES: {sorted(found - expected)}'
        )

    def test_every_found_body_names_at_least_one_skill(self, bodies: dict[str, str]) -> None:
        """A block that names nothing declares no foundational skill.

        Asserted rather than allowed, because an empty block and an
        unparseable one are indistinguishable to a reader of a green run, and an
        empty block under this heading reads as a declaration that happens to
        have nothing in it.
        """
        empty = [name for name, text in bodies.items() if not extract_foundational_notations(text)]
        assert empty == [], f'foundational blocks naming no resolvable notation: {sorted(empty)}'


class TestEveryDeclaredSkillExists:
    def test_no_body_names_a_skill_the_marketplace_does_not_ship(self, bodies: dict[str, str]) -> None:
        """The gate itself: every named foundational skill resolves.

        A named skill the marketplace does not contain cannot be loaded, so the
        load-or-fail-closed rule is already violated at authoring time — the
        cheapest possible place to catch it, and the one that needs no runtime.
        """
        unresolved: dict[str, list[str]] = {}
        for name, text in bodies.items():
            missing = sorted(n for n in extract_foundational_notations(text) if resolve_notation(n) is None)
            if missing:
                unresolved[name] = missing
        assert unresolved == {}, f'bodies naming skills the marketplace does not ship: {unresolved}'

    def test_an_unresolvable_notation_fails_rather_than_skipping(self) -> None:
        """A guard that skips what it cannot resolve is not a guard.

        Pinned against the resolver directly, because the failure this module
        exists to prevent is the one where a notational body is quietly excluded
        from the population and the surviving bodies all pass.
        """
        assert resolve_notation('plan-marshall:no-such-foundational-skill') is None
        assert resolve_notation('plan-marshall:dev-agent-behavior-rules') is None, (
            'plan-marshall:dev-agent-behavior-rules is the canonical RETIRED notation — if it now '
            'resolves, a retired skill was resurrected and this assertion is no longer testing retirement'
        )


#: The rule's canonical home. It NAMES the enforced lifecycle bodies, so the
#: membership the directive checks below iterate is read from here rather than
#: restated: a body added to the rule's list is checked on the next run, and a
#: list kept only in this module would let a new lifecycle body join the rule
#: without its directive ever being asserted.
RULE_DOCUMENT = MARKETPLACE_ROOT / 'plan-marshall/skills/ref-workflow-architecture/standards/agents.md'

#: The paragraph of :data:`RULE_DOCUMENT` that enumerates the enforced bodies.
_ENFORCED_SURFACE_MARKER = '**This document owns the rule.**'

_BACKTICKED_SKILL = re.compile(r'`([a-z0-9][a-z0-9-]*)`')


def enforced_lifecycle_bodies() -> list[str]:
    """Return the lifecycle bodies the rule document names as its enforced surface.

    Parsed from the one paragraph that enumerates them, as marketplace-relative
    ``SKILL.md`` paths. An absent paragraph yields an empty list, which the
    callers assert against rather than iterate over.
    """
    text = RULE_DOCUMENT.read_text(encoding='utf-8')
    paragraph = next((line for line in text.splitlines() if line.startswith(_ENFORCED_SURFACE_MARKER)), '')
    return [f'plan-marshall/skills/{name}/SKILL.md' for name in _BACKTICKED_SKILL.findall(paragraph)]


def _lifecycle_cases() -> list[str]:
    """The directive-check parametrization, over a membership proven non-empty.

    An empty parameter set is a collection error rather than a red assertion,
    so the membership is asserted here — and returned through ``list()`` so the
    returned expression carries the guarded name.
    """
    bodies = enforced_lifecycle_bodies()
    assert bodies, f'{RULE_DOCUMENT} names no enforced lifecycle body under {_ENFORCED_SURFACE_MARKER!r}'
    return list(bodies)


def _skill_id(path: str) -> str:
    return path.rsplit('/', 2)[-2]


class TestTheSixLifecycleBodiesCarryTheDirective:
    """The rule is one, stated once; the lifecycle bodies it names must point at it.

    A gate that covers four phases of six is not a gate: the phases it omits
    would proceed on a half-applied foundational set while reporting the same
    completed phase as the phases it covers.
    """

    RULE_HEADING = 'Foundational Skills: load or fail closed'

    def _body(self, relative: str) -> str:
        return (MARKETPLACE_ROOT / relative).read_text(encoding='utf-8')

    def test_every_named_lifecycle_body_carries_the_block(self, bodies: dict[str, str]) -> None:
        """The rule names only bodies that actually declare foundational skills.

        A name in the rule document that matches no block-carrying body is a
        membership the directive checks would read from a file that has nothing
        to fail closed on.
        """
        missing = sorted(set(enforced_lifecycle_bodies()) - set(bodies))
        assert missing == [], f'the rule document names bodies that carry no foundational block: {missing}'

    def test_every_phase_body_carrying_the_block_is_named_by_the_rule(self, bodies: dict[str, str]) -> None:
        """A phase body that gains the block joins the enforced surface, or the build is red.

        The phase roster is production's (``constants.PHASES``), so a phase added
        to it — or a phase body that gains a foundational block — is checked
        against the rule document's list without an edit here.
        """
        from constants import PHASES

        assert PHASES, 'constants.PHASES is empty; the phase roster cross-check would be vacuous'
        phase_bodies = {f'plan-marshall/skills/phase-{phase}/SKILL.md' for phase in PHASES}
        unnamed = sorted((phase_bodies & set(bodies)) - set(enforced_lifecycle_bodies()))
        assert unnamed == [], (
            f'phase bodies carry a foundational block but are not on the rule document enforced surface: {unnamed}'
        )

    @pytest.mark.parametrize('relative', _lifecycle_cases(), ids=_skill_id)
    def test_body_points_at_the_canonical_rule(self, relative: str) -> None:
        body = self._body(relative)
        section = foundational_section(body) or ''
        assert 'aborts' in section, f'{relative} carries no fail-closed directive in its foundational block'
        assert 'ref-workflow-architecture/standards/agents.md' in body, (
            f'{relative} does not point at agents.md, so the rule has no canonical home from this body'
        )
        assert self.RULE_HEADING in body, f'{relative} does not name the agents.md section it defers to'

    #: The normative marker, unique to the canonical statement in ``agents.md``.
    #: Chosen as a NAMED term rather than a phrase: the six bodies must repeat
    #: enough wording to be actionable, so a phrase scan would find six carriers
    #: and report the very structure the rule requires as a duplication defect.
    NORMATIVE_MARKER = 'Load-or-fail-closed'

    def test_the_rule_is_stated_once_and_referenced_elsewhere(self) -> None:
        """Exactly one document carries the normative statement; the rest defer to it.

        Six restatements of one rule are six documents free to drift, and a drift
        between two phases means the same run enforces the requirement in one
        place and not the other — which is worse than no rule, because the run
        looks covered.
        """
        carriers = [
            _relative(path)
            for path in sorted(MARKETPLACE_ROOT.rglob('*.md'))
            if self.NORMATIVE_MARKER in path.read_text(encoding='utf-8', errors='replace')
        ]
        assert carriers == ['plan-marshall/skills/ref-workflow-architecture/standards/agents.md'], (
            f'the normative fail-closed statement must live only in agents.md; found it also in {carriers}'
        )

    @pytest.mark.parametrize('relative', _lifecycle_cases(), ids=_skill_id)
    def test_lifecycle_body_defers_rather_than_restates(self, relative: str) -> None:
        """A lifecycle body references the rule; it does not reproduce it.

        The two halves of "one home" are separate claims and are checked
        separately: a body that dropped its deferral would leave the rule stated
        once and enforced nowhere, and a body that restated it would leave the
        rule stated once and drifting in six more places.
        """
        body = self._body(relative)
        assert self.NORMATIVE_MARKER not in body, f'{relative} restates the normative rule instead of deferring to it'
        assert 'ref-workflow-architecture/standards/agents.md' in body
