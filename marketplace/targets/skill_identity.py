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
    """Return the ``metadata`` line that carries a skill's ``implements:`` declaration.

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

    The VALUE is always a single string, comma-joined when the source declares
    several, because the Agent Skills ``metadata`` map is string-to-string: a YAML
    sequence there is out of spec and a strict loader may reject the whole skill.
    ``read_implements_field`` splits the joined form back into its values, so a
    multi-value declaration survives the round trip without putting a sequence in
    the map.

    Args:
        raw: The parsed ``implements`` value, or an empty string. ``parse_frontmatter``
            has already flattened a block sequence to a comma-joined string.

    Returns:
        The line to append inside the ``metadata`` block, or ``[]`` when the source
        declares no ``implements`` at all.
    """
    values = [value.strip() for value in raw.split(',') if value.strip()]
    if not values:
        return []
    return [f'  {IMPLEMENTS_KEY}: {", ".join(values)}']
