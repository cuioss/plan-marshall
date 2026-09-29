# SPDX-License-Identifier: FSL-1.1-ALv2
"""What the flat emitters write is what the runtime identity reader reads.

The OpenCode and Antigravity targets deploy ``{bundle}-{skill}`` directories,
whose names cannot be split back into the pair. Each emitter records the pair
in the skill's ``SKILL.md`` frontmatter (``marketplace.targets.skill_identity``);
``deployed_layout.read_flat_skill_identity`` is the one runtime reader. The two
live on opposite sides of the build, so this test is the lock-step between them:
every flat target's REAL skill transform is written into a directory of the
emitted name and read back.
"""

from __future__ import annotations

from pathlib import Path

import deployed_layout
import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity import frontmatter as antigravity_frontmatter
from marketplace.targets.opencode import frontmatter as opencode_frontmatter

#: The flat targets and their frontmatter modules + rules directories.
_FLAT_TARGETS = {
    'opencode': (opencode_frontmatter, Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'opencode'),
    'antigravity': (antigravity_frontmatter, Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity'),
}

#: Pairs whose components are both kebab-case — the shape no split can recover.
_PAIRS = [
    ('plan-marshall', 'manage-status'),
    ('pm-plugin-development', 'plugin-script-architecture'),
]


@pytest.mark.parametrize('target', sorted(_FLAT_TARGETS))
@pytest.mark.parametrize(('bundle', 'skill'), _PAIRS)
def test_emitted_identity_reads_back(target: str, bundle: str, skill: str, tmp_path: Path) -> None:
    module, config_dir = _FLAT_TARGETS[target]
    rules = module.load_rules(config_dir)
    frontmatter = module.transform_skill_frontmatter({'description': 'a skill'}, bundle, skill, rules)
    skill_dir = tmp_path / deployed_layout.flat_skill_dir_name(bundle, skill)
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text(frontmatter + '\n\n# body\n', encoding='utf-8')

    assert deployed_layout.read_flat_skill_identity(skill_dir) == (bundle, skill)


@pytest.mark.parametrize('target', sorted(_FLAT_TARGETS))
def test_identity_lives_inside_the_frontmatter_block(target: str) -> None:
    """The block must sit between the fences, or the runtime reads it as body text."""
    module, config_dir = _FLAT_TARGETS[target]
    rules = module.load_rules(config_dir)
    frontmatter = module.transform_skill_frontmatter({'description': 'a skill'}, 'b', 's', rules)

    block = frontmatter.split('---')[1]
    assert 'metadata:\n  bundle: b\n  skill: s' in block
    assert frontmatter.count('---') == 2
