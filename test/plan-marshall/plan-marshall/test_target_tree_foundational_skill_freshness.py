#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every generated target tree names only skills the marketplace still ships.

The source-scoped completeness guard (``test_foundational_skill_completeness.py``)
cannot see this failure, and the blindness is structural rather than an oversight.
A body in the SOURCE can only name a skill the source contains, so a source-scoped
check is green by construction. The name that actually reaches a running agent
lives one layer out: in the generated per-target tree, which is a DERIVED artifact
that survives edits to its source until something regenerates it.

That is how a deployment ends up carrying a notation the marketplace retired. The
body was renamed or the skill was withdrawn; the source was corrected; nobody
regenerated; and the deployed tree kept instructing agents to load a skill that
exists in neither source nor deployment. Every dispatch through that deployed body
then names a skill it cannot load — the exact condition the load-or-fail-closed
rule exists for, reached by a path that rule alone cannot close.

This module reads the direction the existing ``skills_by_profile`` staleness guard
does not: that guard asks whether a CONFIG names a retired skill, and this one asks
whether a DEPLOYED TREE does.

**An absent tree is reported as unevaluated, never as a pass.** The two must not
render identically: a green run over the registered targets and a green run over
none of them are different findings, and collapsing them is how a deployment goes
unexamined for months. The absent case is stated in the failure message of the
aggregate test below, so a reader is told which trees were looked at.

**The population is the registry, not whatever happens to exist.** The expected
tree set is derived from the generator's ``TARGET_REGISTRY`` — the same set
``./pw generate --target all --output target`` writes, one ``target/{name}``
directory per registered target. A sweep over whatever trees exist would read a
PARTIAL generation (only ``target/claude``, say) as a clean sweep over every
target: the empty-population hole and the incomplete-population hole are the same
failure, and each registered tree that is absent is named as unevaluated.

**The boundary this module can and cannot draw.** A directory under the target
root that carries no markdown is not a tree: the discovery filter excludes it, so
a HALF-WRITTEN tree is indistinguishable from an absent one here — and is
reported as unevaluated for exactly that reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _foundational_skills import (
    TARGET_ROOT,
    extract_foundational_notations,
    resolve_notation,
)


def discover_target_trees() -> dict[str, Path]:
    """Map each generated target tree to its root.

    Discovered from the generator's own output directory rather than named, so a
    target added to the registry later is swept without an edit here. A directory
    with no markdown under it is not a tree and is not returned.
    """
    if not TARGET_ROOT.is_dir():
        return {}
    return {path.name: path for path in sorted(TARGET_ROOT.iterdir()) if path.is_dir() and any(path.rglob('*.md'))}


def registered_target_names() -> list[str]:
    """Return every target the generator registers — the trees a sweep must examine.

    Read from ``TARGET_REGISTRY`` rather than listed here, so a target added to
    the registry is expected by this guard without an edit. ``generate --target
    all --output target`` writes each one to ``target/{name}``.
    """
    from marketplace.targets import TARGET_REGISTRY

    return sorted(TARGET_REGISTRY)


def unevaluated_targets(trees: dict[str, Path]) -> list[str]:
    """Return the registered targets whose generated tree is absent from *trees*."""
    return sorted(set(registered_target_names()) - set(trees))


def stale_named_skills(tree: Path) -> dict[str, list[str]]:
    """Map every file in *tree* to the notations it names that no longer resolve."""
    stale: dict[str, list[str]] = {}
    for path in sorted(tree.rglob('*.md')):
        text = path.read_text(encoding='utf-8', errors='replace')
        missing = sorted(n for n in extract_foundational_notations(text) if resolve_notation(n) is None)
        if missing:
            stale[path.relative_to(tree).as_posix()] = missing
    return stale


@pytest.fixture(scope='module')
def trees() -> dict[str, Path]:
    return discover_target_trees()


_REGENERATE_HINT = '`./pw generate --target all --output target`'


class TestTheSweepIsReal:
    def test_the_registry_names_at_least_one_target(self) -> None:
        """The expected population is non-empty, so the coverage check below can fail."""
        assert registered_target_names(), 'TARGET_REGISTRY is empty; the sweep would expect no tree at all'

    def test_every_registered_target_tree_was_examined(self, trees: dict[str, Path]) -> None:
        """A sweep over a SUBSET of the registered trees satisfies "every tree is clean".

        Asserted separately from the staleness check because the two fail for
        unrelated reasons and a reader needs to tell them apart: this one says
        which trees were not generated, the other says a tree names something the
        marketplace retired. A sweep over zero trees is the degenerate case of
        the same shortfall and is reported the same way.
        """
        missing = unevaluated_targets(trees)
        assert missing == [], (
            f'registered target trees absent under {TARGET_ROOT}, reported as UNEVALUATED: {missing} '
            f'(examined: {sorted(trees)}). Run {_REGENERATE_HINT} first.'
        )

    def test_no_tree_names_a_skill_the_marketplace_does_not_ship(self, trees: dict[str, Path]) -> None:
        """The gate: no deployed body names a skill the marketplace does not ship.

        One test over the discovered set rather than a ``parametrize`` over it.
        That is not a style preference: pytest treats an EMPTY parameter set as a
        COLLECTION ERROR, so a run against a checkout where the trees were never
        generated would abort the whole module with a message naming a line
        number instead of reporting the unevaluated sweep this module exists to
        distinguish from a clean one. The registered population is asserted
        first, so a partial or absent tree set reads as "not evaluated", with the
        fix in the message.
        """
        missing = unevaluated_targets(trees)
        assert missing == [], (
            f'registered target trees absent under {TARGET_ROOT}, reported as UNEVALUATED: {missing}. '
            f'Run {_REGENERATE_HINT} first — a partial sweep does not read as a clean one.'
        )

        stale = {name: findings for name, tree in trees.items() if (findings := stale_named_skills(tree))}
        assert stale == {}, (
            f'generated target trees name foundational skills the marketplace does not ship; '
            f'regenerate with `./pw generate`. Offending trees: {stale}'
        )

    def test_a_partial_generation_is_reported_as_unevaluated(self, tmp_path: Path) -> None:
        """Positive control: a tree set carrying ONE registered target names the rest.

        The incomplete-population twin of the empty-population case — the shape a
        local ``./pw generate --target claude`` leaves behind. Without this
        control a coverage check that silently compared against the discovered
        set would pass here as well.
        """
        registered = registered_target_names()
        present = registered[0]

        assert unevaluated_targets({present: tmp_path}) == registered[1:]
        assert unevaluated_targets({}) == registered

    def test_a_retired_FLAT_notation_is_reported_not_dropped(self, tmp_path: Path) -> None:
        """The gate sees a retired name in the spelling the flat trees emit.

        The OpenCode and Antigravity trees write ``{bundle}-{skill}``, not the
        ``{bundle}:{skill}`` source spelling, so a guard that only reached the
        source spelling would be blind in exactly the shape these trees carry.
        This is the positive control for that reachability: a body naming a flat
        pair whose BUNDLE ships and whose SKILL does not must be reported.

        It is also why the extractor cannot filter flat candidates on resolution
        alone — dropping them here would leave this assertion unreachable and the
        gate green over a retired skill.
        """
        tree = tmp_path / 'opencode'
        body = tree / 'skills' / 'plan-marshall-execute-task' / 'SKILL.md'
        body.parent.mkdir(parents=True)
        body.write_text(
            '## Foundational Practices\n\nLoad `plan-marshall-dev-agent-behavior-rules` before anything else.\n',
            encoding='utf-8',
        )

        assert stale_named_skills(tree) == {
            'skills/plan-marshall-execute-task/SKILL.md': ['plan-marshall-dev-agent-behavior-rules']
        }

    def test_a_bare_skill_name_in_prose_is_not_read_as_a_notation(self, tmp_path: Path) -> None:
        """A hyphenated skill NAME is not a ``{bundle}-{skill}`` pair.

        The mirror of the reachability control above, and the reason the extractor
        filters on a real bundle rather than collecting every hyphenated word:
        ``ref-workflow-architecture`` is one shipped skill, and reporting it as an
        unresolvable notation would make the gate permanently red for prose.
        """
        tree = tmp_path / 'opencode'
        body = tree / 'skills' / 'plan-marshall-execute-task' / 'SKILL.md'
        body.parent.mkdir(parents=True)
        body.write_text(
            '## Foundational Practices\n\nLoad `ref-workflow-architecture` before anything else.\n',
            encoding='utf-8',
        )

        assert stale_named_skills(tree) == {}
