# SPDX-License-Identifier: FSL-1.1-ALv2
"""Flat-target skill identity — the bundle a ``{bundle}-{skill}`` directory belongs to.

The OpenCode and Antigravity targets deploy every skill as one dash-joined
directory, ``{bundle}-{skill}``. Both components are kebab-case, so no separator
position splits that name back into the pair, and a deployed tree therefore
cannot yield a ``{bundle}:{skill}:{script}`` notation from its directory names.

Each flat emitter records the pair in the skill's own ``SKILL.md`` frontmatter,
under the Agent Skills ``metadata`` map — an extension the runtime ignores rather
than a field it must understand. The one runtime reader is
``deployed_layout.read_flat_skill_identity`` (plan-marshall ``script-shared``),
and ``test/marketplace/targets/test_flat_skill_identity_emission.py`` pins that
what the emitters write reads back through it.
"""

from __future__ import annotations

from typing import Final


def skill_identity_metadata_lines(bundle: str, skill_name: str) -> list[str]:
    """Return the frontmatter ``metadata`` block recording ``bundle`` and ``skill_name``."""
    return ['metadata:', f'  bundle: {bundle}', f'  skill: {skill_name}']


#: The frontmatter key a skill uses to declare the extension archetype it
#: implements (``implements: plan-marshall:extension-api/standards/ext-point-domain-bundle``).
#: The runtime reader is ``extension_discovery.read_implements_field``.
IMPLEMENTS_KEY: Final[str] = 'implements'


def implements_metadata_lines(raw: str) -> list[str]:
    """Return the ``metadata`` lines that carry a skill's ``implements:`` declaration.

    The flat targets used to DROP the declaration: the frontmatter transform wrote
    a fixed key set, so a deployed ``SKILL.md`` declared no archetype and extension
    discovery found nothing on an installed tree — module discovery came back empty
    and no build command resolved. This restores the declaration, verbatim in VALUE,
    inside the ``metadata`` map beside the identity the flat emitters already record.

    Placement is deliberate. ``read_implements_field`` accepts the key at top level
    or under ``metadata:`` (it strips each line before matching), so both work; the
    ``metadata`` map is chosen because ``implements`` is not an Agent Skills
    top-level field, and ``metadata`` is the map the Agent Skills spec designates
    for exactly this kind of declaration — the same home the ``bundle``/``skill``
    identity already uses, and one no runtime has to learn a new top-level key for.

    The parsed source value arrives flattened by ``parse_frontmatter`` (a block
    sequence becomes a comma-joined string), so a declaration with more than one
    value is re-emitted as a block sequence and a single value as an inline scalar.
    Every VALUE is byte-identical to the source; only the YAML spelling of a
    one-item block sequence collapses to the scalar form that means the same thing.

    Args:
        raw: The parsed ``implements`` value, or an empty string.

    Returns:
        The lines to append inside the ``metadata`` block, or ``[]`` when the
        source declares no ``implements`` at all.
    """
    values = [value.strip() for value in raw.split(',') if value.strip()]
    if not values:
        return []
    if len(values) == 1:
        return [f'  {IMPLEMENTS_KEY}: {values[0]}']
    return [f'  {IMPLEMENTS_KEY}:', *(f'    - {value}' for value in values)]
