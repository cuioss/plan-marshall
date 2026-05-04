#!/usr/bin/env python3
"""Tests for the ``tools-file-ops`` ``copy_tree`` helper and its
``copy-tree`` CLI subcommand consumed by ``phase-1-init`` Step 5b.

The ``copy_tree`` helper is the workhorse behind the architecture snapshot
written into ``.plan/local/plans/{plan_id}/architecture-pre/`` so
``phase-6-finalize`` can compute the architectural delta via
``manage-architecture diff-modules --pre``. These tests pin the contract the
phase-1-init SKILL relies on:

- Recursive copy semantics (nested files, multiple levels).
- Symlinks are skipped (not followed) — the snapshot is a static descriptor.
- ``FileExistsError`` is raised when destination already exists. The skill
  documents this as the abort signal that prevents silent overwrites of a
  previous snapshot. Idempotency is therefore "fail loudly", not "merge".
- Parent directories of the destination are created on demand.
- Source-not-found and source-not-directory raise the documented exceptions.
- The ``copy-tree`` CLI subcommand surfaces success and the three error
  conditions through the standard manage-* TOON contract.
- A simulated ``phase-1-init`` snapshot of a representative
  ``project-architecture/`` tree (with ``_project.json`` and per-module
  ``derived.json`` / ``enriched.json``) materialises the expected
  ``architecture-pre/`` layout byte-for-byte.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from file_ops import copy_tree
from toon_parser import parse_toon

from conftest import MARKETPLACE_ROOT, run_script

FILE_OPS_SCRIPT = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-file-ops' / 'scripts' / 'file_ops.py'


# =============================================================================
# Library helper: copy_tree
# =============================================================================


class TestCopyTreeRecursiveSemantics:
    """Pin recursive copy semantics across nested files and directories."""

    def test_copies_single_file_at_root(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'file.txt').write_text('hello')
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        assert (dst / 'file.txt').read_text() == 'hello'

    def test_copies_nested_directory_tree(self, tmp_path):
        src = tmp_path / 'src'
        (src / 'a' / 'b' / 'c').mkdir(parents=True)
        (src / 'a' / 'b' / 'c' / 'deep.txt').write_text('deep-content')
        (src / 'a' / 'shallow.txt').write_text('shallow-content')
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        assert (dst / 'a' / 'shallow.txt').read_text() == 'shallow-content'
        assert (dst / 'a' / 'b' / 'c' / 'deep.txt').read_text() == 'deep-content'

    def test_preserves_multiple_files_per_directory(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        for name in ('alpha.json', 'beta.json', 'gamma.json'):
            (src / name).write_text(f'{{"name":"{name}"}}')
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        for name in ('alpha.json', 'beta.json', 'gamma.json'):
            assert json.loads((dst / name).read_text()) == {'name': name}

    def test_preserves_byte_content_for_non_ascii(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        # Embed non-ASCII bytes to verify shutil.copy2 byte-faithfulness.
        payload = 'café — π ✓'
        (src / 'utf8.txt').write_text(payload, encoding='utf-8')
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        assert (dst / 'utf8.txt').read_text(encoding='utf-8') == payload


class TestCopyTreeSymlinkHandling:
    """Symlinks are skipped — not followed, not copied as links."""

    @pytest.mark.skipif(sys.platform == 'win32', reason='symlink semantics differ on Windows')
    def test_symlink_to_file_is_skipped(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'real.txt').write_text('real-content')
        (src / 'link.txt').symlink_to(src / 'real.txt')
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        assert (dst / 'real.txt').read_text() == 'real-content'
        # The symlink must NOT be materialised — neither as a link nor as a copy.
        assert not (dst / 'link.txt').exists()
        assert not (dst / 'link.txt').is_symlink()

    @pytest.mark.skipif(sys.platform == 'win32', reason='symlink semantics differ on Windows')
    def test_dangling_symlink_is_skipped(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'real.txt').write_text('real-content')
        (src / 'dangling').symlink_to(tmp_path / 'does-not-exist')
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        assert (dst / 'real.txt').read_text() == 'real-content'
        assert not (dst / 'dangling').exists()
        assert not (dst / 'dangling').is_symlink()

    @pytest.mark.skipif(sys.platform == 'win32', reason='symlink semantics differ on Windows')
    def test_directory_symlink_is_skipped_not_traversed(self, tmp_path):
        """A symlink pointing at a directory MUST NOT be followed.

        Regression for PR #317 review (gemini-code-assist, high priority): the
        previous ``copy_function``-based filter only blocked file symlinks.
        ``shutil.copytree`` decides whether to recurse into a directory entry
        before invoking ``copy_function`` on its children, so a directory
        symlink would be silently traversed and its target's contents copied
        into ``dst`` — contradicting the documented "symlinks are skipped"
        contract. The fix uses an ``ignore`` callable that filters both file
        AND directory symlinks at the directory-listing level, which is the
        only stage where copytree consults the filter for directory entries.
        """
        # External directory whose contents must NEVER appear under dst.
        external = tmp_path / 'external'
        external.mkdir()
        (external / 'secret.txt').write_text('must-not-be-copied')
        (external / 'nested').mkdir()
        (external / 'nested' / 'deep.txt').write_text('also-must-not-be-copied')

        src = tmp_path / 'src'
        src.mkdir()
        (src / 'real.txt').write_text('real-content')
        # Directory symlink pointing at the external tree.
        (src / 'linked-dir').symlink_to(external, target_is_directory=True)
        dst = tmp_path / 'dst'

        copy_tree(src, dst)

        # Real file copied as expected.
        assert (dst / 'real.txt').read_text() == 'real-content'
        # Directory symlink itself must NOT be materialised — neither as a
        # link nor as a directory copy.
        assert not (dst / 'linked-dir').exists()
        assert not (dst / 'linked-dir').is_symlink()
        # Crucially: the symlink target's contents must NOT have been copied
        # into dst under the symlink name. This is the regression assertion
        # — without the ignore-callable fix this path would exist with the
        # external file inside.
        assert not (dst / 'linked-dir' / 'secret.txt').exists()
        assert not (dst / 'linked-dir' / 'nested' / 'deep.txt').exists()


class TestCopyTreeIdempotency:
    """``copy_tree`` is fail-loud, not silent-merge."""

    def test_fails_when_destination_already_exists(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'file.txt').write_text('content')
        dst = tmp_path / 'dst'
        dst.mkdir()  # pre-existing

        with pytest.raises(FileExistsError, match='destination already exists'):
            copy_tree(src, dst)

    def test_fails_when_destination_is_existing_file(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'file.txt').write_text('content')
        dst = tmp_path / 'dst'
        dst.write_text('I am a file')  # pre-existing as a file

        with pytest.raises(FileExistsError):
            copy_tree(src, dst)

    def test_destination_unchanged_after_failed_call(self, tmp_path):
        """When dst exists, copy_tree must abort BEFORE touching it."""
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'new.txt').write_text('new-content')
        dst = tmp_path / 'dst'
        dst.mkdir()
        (dst / 'existing.txt').write_text('original')

        with pytest.raises(FileExistsError):
            copy_tree(src, dst)

        # Original sentinel survives, source files were NOT merged in.
        assert (dst / 'existing.txt').read_text() == 'original'
        assert not (dst / 'new.txt').exists()


class TestCopyTreeParentCreation:
    """Parent directories of the destination are created on demand."""

    def test_creates_missing_parent_directories(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'leaf.txt').write_text('leaf')
        # Two missing parent levels — mirrors the
        # ``.plan/local/plans/{plan_id}/architecture-pre`` shape phase-1-init
        # writes into a fresh plan dir.
        dst = tmp_path / 'a' / 'b' / 'architecture-pre'

        copy_tree(src, dst)

        assert (dst / 'leaf.txt').read_text() == 'leaf'

    def test_existing_parent_is_reused(self, tmp_path):
        parent = tmp_path / 'plans' / 'my-plan'
        parent.mkdir(parents=True)
        # Pre-existing sibling content that must survive the snapshot.
        (parent / 'request.md').write_text('request')

        src = tmp_path / 'src'
        src.mkdir()
        (src / 'leaf.txt').write_text('leaf')
        dst = parent / 'architecture-pre'

        copy_tree(src, dst)

        assert (dst / 'leaf.txt').read_text() == 'leaf'
        # Sibling stays put.
        assert (parent / 'request.md').read_text() == 'request'


class TestCopyTreeSourceValidation:
    """Source must exist and be a directory."""

    def test_source_not_found_raises(self, tmp_path):
        src = tmp_path / 'missing'
        dst = tmp_path / 'dst'

        with pytest.raises(FileNotFoundError, match='source does not exist'):
            copy_tree(src, dst)

    def test_source_not_a_directory_raises(self, tmp_path):
        src = tmp_path / 'not-a-dir'
        src.write_text('I am a file')
        dst = tmp_path / 'dst'

        with pytest.raises(NotADirectoryError, match='source is not a directory'):
            copy_tree(src, dst)


# =============================================================================
# CLI subcommand: file_ops copy-tree
# =============================================================================


class TestCopyTreeCLI:
    """The ``copy-tree`` CLI is the surface phase-1-init invokes."""

    def test_cli_success_emits_toon_with_paths(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'file.txt').write_text('content')
        dst = tmp_path / 'dst'

        result = run_script(FILE_OPS_SCRIPT, 'copy-tree', '--src', str(src), '--dst', str(dst))

        assert result.success, f'stdout={result.stdout!r} stderr={result.stderr!r}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['operation'] == 'copy-tree'
        assert (dst / 'file.txt').read_text() == 'content'

    def test_cli_dst_already_exists_emits_error_toon(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'file.txt').write_text('content')
        dst = tmp_path / 'dst'
        dst.mkdir()

        result = run_script(FILE_OPS_SCRIPT, 'copy-tree', '--src', str(src), '--dst', str(dst))

        assert not result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'dst_already_exists'

    def test_cli_src_not_found_emits_error_toon(self, tmp_path):
        src = tmp_path / 'missing'
        dst = tmp_path / 'dst'

        result = run_script(FILE_OPS_SCRIPT, 'copy-tree', '--src', str(src), '--dst', str(dst))

        assert not result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'src_not_found'

    def test_cli_src_not_directory_emits_error_toon(self, tmp_path):
        src = tmp_path / 'not-a-dir'
        src.write_text('regular file')
        dst = tmp_path / 'dst'

        result = run_script(FILE_OPS_SCRIPT, 'copy-tree', '--src', str(src), '--dst', str(dst))

        assert not result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'src_not_directory'


# =============================================================================
# phase-1-init integration: architecture-pre snapshot
# =============================================================================


def _build_project_architecture_fixture(root: Path) -> None:
    """Build a representative ``project-architecture/`` tree.

    Mirrors the per-module layout phase-1-init snapshots: a top-level
    ``_project.json`` plus one directory per module containing
    ``derived.json`` and ``enriched.json``.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / '_project.json').write_text(json.dumps({'modules': ['plan-marshall', 'pm-dev-java']}, indent=2))
    for module in ('plan-marshall', 'pm-dev-java'):
        mod_dir = root / module
        mod_dir.mkdir()
        (mod_dir / 'derived.json').write_text(json.dumps({'module': module, 'paths': []}, indent=2))
        (mod_dir / 'enriched.json').write_text(
            json.dumps({'module': module, 'responsibility': f'{module} responsibility'}, indent=2)
        )


class TestPhase1InitSnapshotIntegration:
    """Pin the phase-1-init Step 5b architecture-snapshot contract.

    The SKILL invokes::

        file_ops copy-tree \
          --src .plan/project-architecture \
          --dst .plan/local/plans/{plan_id}/architecture-pre

    These tests simulate that invocation against a representative source
    tree and verify the materialised destination matches the source
    byte-for-byte. Failure modes that the SKILL documents (FileExistsError,
    missing source) are pinned in the CLI tests above; here we focus on the
    happy-path materialisation contract.
    """

    def test_snapshot_materialises_project_json_and_per_module_dirs(self, tmp_path):
        src = tmp_path / 'project-architecture'
        _build_project_architecture_fixture(src)
        # Mirror the phase-1-init destination shape — parent directories don't
        # pre-exist on a fresh plan.
        dst = tmp_path / 'local' / 'plans' / 'phase-d-auto-refresh' / 'architecture-pre'

        copy_tree(src, dst)

        # Top-level _project.json.
        assert json.loads((dst / '_project.json').read_text()) == {'modules': ['plan-marshall', 'pm-dev-java']}
        # Per-module derived.json + enriched.json.
        for module in ('plan-marshall', 'pm-dev-java'):
            derived = json.loads((dst / module / 'derived.json').read_text())
            enriched = json.loads((dst / module / 'enriched.json').read_text())
            assert derived == {'module': module, 'paths': []}
            assert enriched == {'module': module, 'responsibility': f'{module} responsibility'}

    def test_snapshot_via_cli_matches_source_byte_for_byte(self, tmp_path):
        src = tmp_path / 'project-architecture'
        _build_project_architecture_fixture(src)
        dst = tmp_path / 'local' / 'plans' / 'phase-d-auto-refresh' / 'architecture-pre'

        result = run_script(FILE_OPS_SCRIPT, 'copy-tree', '--src', str(src), '--dst', str(dst))

        assert result.success, f'stdout={result.stdout!r} stderr={result.stderr!r}'

        # Compare the entire tree byte-for-byte using a relative-path walk.
        src_files = sorted(p.relative_to(src) for p in src.rglob('*') if p.is_file())
        dst_files = sorted(p.relative_to(dst) for p in dst.rglob('*') if p.is_file())
        assert src_files == dst_files
        for rel in src_files:
            assert (src / rel).read_bytes() == (dst / rel).read_bytes(), f'mismatch at {rel}'

    def test_snapshot_aborts_on_pre_existing_destination(self, tmp_path):
        """Re-running phase-1-init against an already-snapshotted plan
        directory MUST fail loudly so the SKILL can surface the error
        rather than silently merge over the previous snapshot.
        """
        src = tmp_path / 'project-architecture'
        _build_project_architecture_fixture(src)
        dst = tmp_path / 'local' / 'plans' / 'phase-d-auto-refresh' / 'architecture-pre'
        dst.mkdir(parents=True)
        (dst / 'stale.json').write_text('previous-snapshot')

        with pytest.raises(FileExistsError):
            copy_tree(src, dst)

        # Stale sentinel preserved, no merge happened.
        assert (dst / 'stale.json').read_text() == 'previous-snapshot'
        assert not (dst / '_project.json').exists()
