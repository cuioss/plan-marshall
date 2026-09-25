# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_canonical_verify_inactive_fixtures import (
    Path,
    _guard_script,
    clean_repo,
    dirty_repo,
    run_script,
)


class TestUncommittedBlocksGreen:
    """``post_run_source_guard check --fail-on-dirty`` gates the green report.

    A dirty tree trips the gate (non-zero exit) while the default stays
    advisory (exit 0 on the same tree) — the two modes share the payload and
    differ only in whether uncommitted state blocks the caller.
    """

    def test_fail_on_dirty_blocks_dirty_tree(self, dirty_repo: Path):
        result = run_script(
            _guard_script,
            'check',
            '--step-id',
            'phase-5-execute:final-quality-sweep',
            '--project-dir',
            str(dirty_repo),
            '--fail-on-dirty',
        )
        assert result.returncode == 1
        payload = result.toon()
        assert payload['clean'] is False
        assert 'src/tracked.py' in str(payload['offending_paths'])

    def test_default_stays_advisory_on_dirty_tree(self, dirty_repo: Path):
        result = run_script(
            _guard_script,
            'check',
            '--step-id',
            'phase-5-execute:final-quality-sweep',
            '--project-dir',
            str(dirty_repo),
        )
        assert result.returncode == 0
        payload = result.toon()
        assert payload['clean'] is False
        assert 'src/tracked.py' in str(payload['offending_paths'])

    def test_fail_on_dirty_passes_clean_tree(self, clean_repo: Path):
        result = run_script(
            _guard_script,
            'check',
            '--step-id',
            'phase-5-execute:final-quality-sweep',
            '--project-dir',
            str(clean_repo),
            '--fail-on-dirty',
        )
        assert result.returncode == 0
        payload = result.toon()
        assert payload['clean'] is True
        assert payload['offending_paths'] == []
