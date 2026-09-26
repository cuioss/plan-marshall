# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2


# =============================================================================
# Regression: project: steps resolve via the cwd-relative working-tree root, not
# the Path(__file__)-derived _REPO_ROOT. When the executor runs the deployed
# plugin-cache copy, Path(__file__) lives under ~/.claude/plugins/cache/..., so
# resolve_bundles_root(__file__).parent.parent (_REPO_ROOT) lands at
# ~/.claude/plugins — a directory with no .claude/skills. A base=_REPO_ROOT
# project-skill probe therefore reported EVERY project: finalize/verify step
# falsely unresolvable, blocking compose for every meta-project plan. The fix
# anchors project-local resolution on the uniform cwd-relative resolver
# (_project_local_skills_root → _find_plan_root_from_cwd). The existing gate
# tests can't catch this because they run from source, where _REPO_ROOT
# coincidentally equals the real repo root; this test forces _REPO_ROOT to a
# skill-less directory to reproduce the cache anchor.
# =============================================================================


def test_project_step_resolves_from_working_tree_not_file_anchor(monkeypatch, tmp_path):
    """`project:` step resolution ignores a cache-anchored _REPO_ROOT and uses cwd."""
    import _manifest_validation as _mv

    # Fake working tree under cwd: .plan/local anchors the cwd walk-up, and
    # .claude/skills holds the project-local step's SKILL.md.
    (tmp_path / '.plan' / 'local').mkdir(parents=True)
    skill_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-cache-probe'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('---\norder: 77\n---\n# probe\n', encoding='utf-8')

    # Simulate the deployed-cache anchor: _REPO_ROOT points at a dir with no
    # .claude/skills (as ~/.claude/plugins does in production).
    cache_like = tmp_path / 'plugins-cache-root'
    cache_like.mkdir()
    monkeypatch.setattr(_mv, '_REPO_ROOT', cache_like)
    monkeypatch.chdir(tmp_path)

    # Resolvability resolves from the cwd working tree despite the bogus _REPO_ROOT.
    resolvable = _mv._check_step_resolvable('project:finalize-step-cache-probe', 'phase_6')
    assert resolvable['resolvable'] is True

    # A genuinely-absent project step still fails loud (guards against the fix
    # degrading into an unconditional pass).
    missing = _mv._check_step_resolvable('project:finalize-step-does-not-exist', 'phase_6')
    assert missing['resolvable'] is False

    # Order resolution reads the frontmatter from the cwd working tree too.
    assert _mv._resolve_step_order('project:finalize-step-cache-probe') == 77
