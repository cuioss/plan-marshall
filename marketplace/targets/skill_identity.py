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


def skill_identity_metadata_lines(bundle: str, skill_name: str) -> list[str]:
    """Return the frontmatter ``metadata`` block recording ``bundle`` and ``skill_name``."""
    return ['metadata:', f'  bundle: {bundle}', f'  skill: {skill_name}']
