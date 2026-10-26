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

#: The ext-point step fields a flat deployment must carry for a discovered
#: implementor to keep its meaning: ``order``/``default_on``/``presets`` decide
#: whether a finalize step is a seeded default and where it sorts,
#: ``canonicals``/``verification_profile`` carry the verify contract. The reader
#: is ``extension_discovery._read_frontmatter_fields`` (it descends one level into
#: ``metadata``), and the contracts are ext-point-finalize-step.md /
#: ext-point-build-verify-step.md / ext-point-verify.md.
STEP_METADATA_KEYS: Final[tuple[str, ...]] = (
    'order',
    'default_on',
    'presets',
    'canonicals',
    'verification_profile',
)

#: The step fields whose source shape is a LIST; the emitted metadata value joins
#: them because an Agent Skills ``metadata`` value must be a string.
LIST_STEP_METADATA_KEYS: Final[frozenset[str]] = frozenset({'presets', 'canonicals'})


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


def step_metadata_lines(fm: dict[str, str]) -> list[str]:
    """Return the ``metadata`` lines carrying an ext-point step's own fields.

    A skill that declares ``implements:`` is usually a step, and a step's meaning
    lives in its other declarations: ``default_on`` decides whether a finalize step
    is seeded into the default set, ``order`` where it sorts, ``presets`` which
    postures include it. The emitters wrote none of them, so a flat install
    discovered such a step but read every field as its default — ``automatic-review``
    (``default_on: true``) came back ``bundle-optional`` and was never seeded, while
    ``plan-retrospective`` lost its ``order``/``presets``.

    The values go under ``metadata`` for the same reason ``implements`` does (it is
    the Agent Skills map for non-standard declarations, and its values must be
    strings), so a list-valued field is comma-joined here and split back by
    ``extension_discovery._read_frontmatter_fields``. Only fields the SOURCE
    declares are emitted: a step that declares no ``verification_profile`` keeps its
    absence, which is the ext-point-verify non-participation signal.

    Args:
        fm: The parsed source frontmatter.

    Returns:
        The lines to append inside the ``metadata`` block, in
        :data:`STEP_METADATA_KEYS` order.
    """
    lines: list[str] = []
    for key in STEP_METADATA_KEYS:
        value = (fm.get(key) or '').strip()
        if not value:
            continue
        if key in LIST_STEP_METADATA_KEYS:
            values = [item.strip() for item in value.split(',') if item.strip()]
            if not values:
                continue
            value = ', '.join(values)
        lines.append(f'  {key}: {value}')
    return lines
