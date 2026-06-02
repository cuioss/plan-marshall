#!/usr/bin/env python3
"""
Tests for the file_ops.py module.

Tests functions:
- atomic_write_file: Atomic file writing with temp file + rename
- ensure_directory: Directory creation (mkdir -p equivalent)
- output_success/output_error: TOON output helpers
- parse_markdown_metadata: Key=value metadata parsing
- generate_markdown_metadata: Metadata block generation
- update_markdown_metadata: Metadata field updates
- get_metadata_content_split: Split metadata from body
- get_base_dir/set_base_dir/base_path: Base directory configuration
"""

import sys
from io import StringIO
from pathlib import Path

import file_ops
import pytest
from file_ops import (
    PlanNotFoundError,
    atomic_write_file,
    base_path,
    ensure_directory,
    generate_markdown_metadata,
    get_base_dir,
    get_executor_path,
    get_metadata_content_split,
    get_plan_dir,
    get_temp_dir,
    get_worktree_root,
    output_error,
    output_success,
    parse_markdown_metadata,
    require_plan_exists,
    safe_main,
    set_base_dir,
    update_markdown_metadata,
)
from toon_parser import parse_toon


@pytest.fixture(autouse=True)
def _reset_base_dir_override():
    """Ensure no test leaks file_ops._BASE_DIR_OVERRIDE across tests.

    Several tests in this file call set_base_dir() without restoring the
    previous value. After get_base_dir() grew a per-project global default
    (resolved via git), a stale override from one test would shadow the
    default for every subsequent test in the suite.
    """
    original = file_ops._BASE_DIR_OVERRIDE
    yield
    file_ops._BASE_DIR_OVERRIDE = original


# =============================================================================
# get_temp_dir tests
# =============================================================================


def test_get_temp_dir_default(tmp_path, monkeypatch):
    """Test get_temp_dir returns .plan/temp by default."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_temp_dir()
    assert result == tmp_path / 'temp'


def test_get_temp_dir_with_subdir(tmp_path, monkeypatch):
    """Test get_temp_dir with subdirectory appends correctly."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_temp_dir('tools-marketplace-inventory')
    assert result == tmp_path / 'temp' / 'tools-marketplace-inventory'


def test_get_temp_dir_without_subdir_is_none(tmp_path, monkeypatch):
    """Test get_temp_dir with None subdir returns temp root."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_temp_dir(None)
    assert result == tmp_path / 'temp'


# =============================================================================
# atomic_write_file tests
# =============================================================================


def test_atomic_write_file_creates_file(tmp_path):
    """Test atomic_write_file creates file with content."""
    path = tmp_path / 'test.txt'
    content = 'Hello, World!'

    atomic_write_file(path, content)

    assert path.exists()
    assert path.read_text() == content + '\n'


def test_atomic_write_file_creates_parent_dirs(tmp_path):
    """Test atomic_write_file creates parent directories."""
    path = tmp_path / 'nested' / 'dir' / 'test.txt'
    content = 'Nested content'

    atomic_write_file(path, content)

    assert path.exists()
    assert path.read_text() == content + '\n'


def test_atomic_write_file_preserves_trailing_newline(tmp_path):
    """Test atomic_write_file doesn't double newlines."""
    path = tmp_path / 'test.txt'
    content = 'Content with newline\n'

    atomic_write_file(path, content)

    assert path.read_text() == content


# =============================================================================
# ensure_directory tests
# =============================================================================


def test_ensure_directory_creates_directory(tmp_path):
    """Test ensure_directory creates directory."""
    path = tmp_path / 'new' / 'nested' / 'dir'

    result = ensure_directory(path)

    assert path.exists()
    assert path.is_dir()
    assert result == path


def test_ensure_directory_with_file_path(tmp_path):
    """Test ensure_directory creates parent when given file path."""
    path = tmp_path / 'parent' / 'file.txt'

    result = ensure_directory(path)

    expected_dir = tmp_path / 'parent'
    assert expected_dir.exists()
    assert expected_dir.is_dir()
    assert result == expected_dir


def test_ensure_directory_idempotent(tmp_path):
    """Test ensure_directory is idempotent."""
    path = tmp_path / 'existing'
    path.mkdir()

    result = ensure_directory(path)

    assert path.exists()
    assert result == path


# =============================================================================
# output_success/output_error tests (TOON format)
# =============================================================================


def test_output_success_format():
    """Test output_success produces correct TOON."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    output_success('test-op', file='test.txt', count=5)

    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    result = parse_toon(output)
    assert result['success'] is True
    assert result['operation'] == 'test-op'
    assert result['file'] == 'test.txt'
    assert result['count'] == 5


def test_output_error_format():
    """Test output_error produces correct TOON to stderr."""
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    output_error('test-op', 'Something went wrong')

    output = sys.stderr.getvalue()
    sys.stderr = old_stderr

    result = parse_toon(output)
    assert result['success'] is False
    assert result['operation'] == 'test-op'
    assert result['error'] == 'Something went wrong'


# =============================================================================
# safe_main exception-rendering tests
#
# An uncaught exception inside a @safe_main-wrapped entry point MUST be
# rendered as a status:error TOON on STDOUT (per the manage-* TOON-on-stdout
# contract), NOT on stderr, while still exiting with code 1 (a genuine crash
# is distinguished from an operation failure, which exits 0). These tests pin
# the stdout sink, the populated message, the status:error code, and the
# retained exit code 1.
# =============================================================================


def test_safe_main_renders_uncaught_exception_as_stdout_toon(capsys):
    """A raised exception → status:error TOON on stdout, exit code 1."""

    @safe_main
    def boom() -> int:
        raise RuntimeError('kaboom detail')

    with pytest.raises(SystemExit) as excinfo:
        boom()

    # Genuine crash keeps exit code 1 (distinct from operation failures = 0).
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    # The diagnostic lives on STDOUT, not stderr (TOON-on-stdout contract).
    assert captured.out.strip(), 'safe_main must emit the error TOON on stdout'
    assert captured.err == '', 'safe_main must not write the crash to stderr'

    result = parse_toon(captured.out)
    assert result['status'] == 'error'
    assert result['error'] == 'internal_error'
    # The exception message is preserved in the populated TOON message field.
    assert 'kaboom detail' in result['message']


def test_safe_main_success_path_exits_zero(capsys):
    """A clean return value is propagated as the process exit code (0)."""

    @safe_main
    def ok() -> int:
        return 0

    with pytest.raises(SystemExit) as excinfo:
        ok()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    # No error TOON is emitted on the success path.
    assert 'status: error' not in captured.out
    assert captured.err == ''


# =============================================================================
# parse_markdown_metadata tests
# =============================================================================


def test_parse_markdown_metadata_basic():
    """Test parse_markdown_metadata with basic content."""
    content = """id=2025-11-28-001
component.type=command
applied=false

# Title

Content here..."""

    result = parse_markdown_metadata(content)

    assert result['id'] == '2025-11-28-001'
    assert result['component.type'] == 'command'
    assert result['applied'] == 'false'
    assert len(result) == 3


def test_parse_markdown_metadata_empty_content():
    """Test parse_markdown_metadata with empty content."""
    result = parse_markdown_metadata('')
    assert result == {}


def test_parse_markdown_metadata_no_metadata():
    """Test parse_markdown_metadata with only content."""
    content = """# Title

Just content, no metadata."""

    result = parse_markdown_metadata(content)
    assert result == {}


def test_parse_markdown_metadata_with_equals_in_value():
    """Test parse_markdown_metadata handles = in values."""
    content = """key=value=with=equals
other=normal

# Title"""

    result = parse_markdown_metadata(content)

    assert result['key'] == 'value=with=equals'
    assert result['other'] == 'normal'


# =============================================================================
# generate_markdown_metadata tests
# =============================================================================


def test_generate_markdown_metadata_basic():
    """Test generate_markdown_metadata with basic data."""
    data = {'id': '2025-11-28-001', 'component.type': 'command', 'applied': 'false'}

    result = generate_markdown_metadata(data)

    assert 'id=2025-11-28-001' in result
    assert 'component.type=command' in result
    assert 'applied=false' in result


def test_generate_markdown_metadata_empty():
    """Test generate_markdown_metadata with empty data."""
    result = generate_markdown_metadata({})
    assert result == ''


# =============================================================================
# update_markdown_metadata tests
# =============================================================================


def test_update_markdown_metadata_updates_existing():
    """Test update_markdown_metadata updates existing keys."""
    content = """id=2025-11-28-001
applied=false

# Title

Content"""

    result = update_markdown_metadata(content, {'applied': 'true'})

    assert 'applied=true' in result
    assert 'applied=false' not in result
    assert 'id=2025-11-28-001' in result
    assert '# Title' in result


def test_update_markdown_metadata_adds_new():
    """Test update_markdown_metadata adds new keys."""
    content = """id=2025-11-28-001

# Title"""

    result = update_markdown_metadata(content, {'new_key': 'new_value'})

    assert 'id=2025-11-28-001' in result
    assert 'new_key=new_value' in result


# =============================================================================
# get_metadata_content_split tests
# =============================================================================


def test_get_metadata_content_split_basic():
    """Test get_metadata_content_split with basic content."""
    content = """id=2025-11-28-001
applied=false

# Title

Content here..."""

    metadata, body = get_metadata_content_split(content)

    assert 'id=2025-11-28-001' in metadata
    assert 'applied=false' in metadata
    assert '# Title' in body
    assert 'Content here' in body


def test_get_metadata_content_split_no_metadata():
    """Test get_metadata_content_split with no metadata."""
    content = """# Title

Just content"""

    metadata, body = get_metadata_content_split(content)

    assert metadata == ''
    assert '# Title' in body


# =============================================================================
# Integration tests
# =============================================================================


def test_roundtrip_metadata():
    """Test that generate and parse are inverse operations."""
    original = {'id': '2025-11-28-001', 'component.type': 'command', 'component.name': 'test-cmd', 'applied': 'false'}

    generated = generate_markdown_metadata(original)
    parsed = parse_markdown_metadata(generated)

    assert parsed == original


# =============================================================================
# get_base_dir/set_base_dir tests
# =============================================================================


def test_get_base_dir_default():
    """Test get_base_dir returns the explicit override when one is set."""
    set_base_dir('.plan')
    result = get_base_dir()
    assert result == Path('.plan')


def test_set_base_dir_changes_default():
    """Test set_base_dir changes the base directory."""
    original = get_base_dir()
    try:
        set_base_dir('/custom/path')
        result = get_base_dir()
        assert result == Path('/custom/path')
    finally:
        set_base_dir(original)


def test_set_base_dir_accepts_string():
    """Test set_base_dir accepts string argument."""
    original = get_base_dir()
    try:
        set_base_dir('/string/path')
        result = get_base_dir()
        assert isinstance(result, Path)
        assert result == Path('/string/path')
    finally:
        set_base_dir(original)


# =============================================================================
# base_path tests
# =============================================================================


def test_base_path_basic():
    """Test base_path constructs path within base directory."""
    set_base_dir('.plan')
    result = base_path('plans', 'my-task', 'plan.md')
    assert result == Path('.plan/plans/my-task/plan.md')


def test_base_path_single_part():
    """Test base_path with single path part."""
    set_base_dir('.plan')
    result = base_path('config.json')
    assert result == Path('.plan/config.json')


def test_base_path_no_parts():
    """Test base_path with no parts returns base directory."""
    set_base_dir('.plan')
    result = base_path()
    assert result == Path('.plan')


def test_base_path_respects_custom_base():
    """Test base_path uses custom base directory."""
    original = get_base_dir()
    try:
        set_base_dir('/custom/base')
        result = base_path('plans', 'task')
        assert result == Path('/custom/base/plans/task')
    finally:
        set_base_dir(original)


# =============================================================================
# get_worktree_root tests
# =============================================================================
#
# Worktrees migrated from ``<root>/.claude/worktrees/`` to
# ``<root>/.plan/local/worktrees/`` so they inherit the existing
# ``Write(.plan/**)`` permission and live alongside the rest of plan-local
# runtime state. These tests pin the new layout to the constant
# ``.plan/local/worktrees`` — no ``.claude/worktrees/`` fallback exists
# (compatibility: breaking).


def test_get_worktree_root_returns_plan_local_worktrees(tmp_path, monkeypatch):
    """get_worktree_root anchors at <root>/.plan/local/worktrees.

    get_worktree_root resolves through get_base_dir (the uniform cwd rule,
    ADR-002), so the production path is produced when no PLAN_BASE_DIR override
    is active and the cwd walk-up resolves a .plan/local ancestor. delenv
    PLAN_BASE_DIR + chdir into a tree with .plan/local pins the cwd-walk branch.
    """
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    (tmp_path / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = get_worktree_root()
    assert result == tmp_path.resolve() / '.plan' / 'local' / 'worktrees'


def test_get_worktree_root_path_segments_match_new_constant(tmp_path, monkeypatch):
    """The trailing segments are exactly ('.plan', 'local', 'worktrees')."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    (tmp_path / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = get_worktree_root()
    assert result.parts[-3:] == ('.plan', 'local', 'worktrees')


def test_get_worktree_root_does_not_use_claude_worktrees(tmp_path, monkeypatch):
    """The legacy .claude/worktrees/ path is no longer produced."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    (tmp_path / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = get_worktree_root()
    # No segment of the resolved path may be ``.claude`` — that prefix is
    # gone now that worktrees live under ``.plan/local/``.
    assert '.claude' not in result.parts


def test_get_worktree_root_honors_plan_base_dir(tmp_path, monkeypatch):
    """With PLAN_BASE_DIR set, get_worktree_root isolates under it.

    This is the test-isolation contract: get_worktree_root resolves through
    get_base_dir, so a PLAN_BASE_DIR override redirects the worktree root to
    ``<PLAN_BASE_DIR>/worktrees`` — no leakage into the real repo tree.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_worktree_root()
    assert result == tmp_path / 'worktrees'


def test_get_worktree_root_without_plan_root_raises(tmp_path, monkeypatch):
    """When no .plan/local ancestor of cwd resolves, get_worktree_root raises."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    bare = tmp_path / 'bare'
    bare.mkdir()
    monkeypatch.chdir(bare)
    with pytest.raises(RuntimeError, match='plan root'):
        get_worktree_root()


# =============================================================================
# get_executor_path tests
# =============================================================================
#
# get_executor_path resolves ``.plan/execute-script.py`` cwd-relatively
# (ADR-002): PLAN_BASE_DIR / set_base_dir override anchors the executor at
# ``<override>/execute-script.py``; in production it walks up from cwd to the
# nearest ``.plan/local`` ancestor and joins ``.plan/execute-script.py`` there
# — worktree-resident when cwd is pinned to the worktree (phase-5+), main when
# cwd is main (the finalize regenerate-on-main path).


def test_get_executor_path_plan_base_dir_override(tmp_path, monkeypatch):
    """With PLAN_BASE_DIR set, the executor anchors at <override>/execute-script.py."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_executor_path()
    assert result == tmp_path / 'execute-script.py'


def test_get_executor_path_cwd_walk_up(tmp_path, monkeypatch):
    """In production, the executor anchors at <plan-root>/.plan/execute-script.py."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    (tmp_path / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = get_executor_path()
    assert result == tmp_path.resolve() / '.plan' / 'execute-script.py'
    assert result.parts[-2:] == ('.plan', 'execute-script.py')


def test_get_executor_path_pinned_in_worktree_resolves_worktree_resident(tmp_path, monkeypatch):
    """With cwd pinned inside a moved-in worktree (its own .plan/local), the
    executor resolves to the worktree-resident copy — never the main checkout
    above it."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    main = tmp_path / 'main'
    (main / '.plan' / 'local').mkdir(parents=True)
    worktree = main / '.plan' / 'local' / 'worktrees' / 'plan-x'
    (worktree / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(worktree)
    result = get_executor_path()
    assert result == worktree.resolve() / '.plan' / 'execute-script.py'


def test_get_executor_path_without_plan_root_raises(tmp_path, monkeypatch):
    """When no .plan/local ancestor of cwd resolves, get_executor_path raises."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    bare = tmp_path / 'bare'
    bare.mkdir()
    monkeypatch.chdir(bare)
    with pytest.raises(RuntimeError, match='plan root'):
        get_executor_path()


# =============================================================================
# require_plan_exists tests
#
# The guard rejects (a) plan_id whose plan directory does not exist, and
# (b) plan_id whose directory exists but is missing the status.json sentinel.
# On the happy path the resolved Path is returned. Test (a) and (b) also
# pin the no-side-effect invariant: a guard rejection MUST NOT create any
# directory on the filesystem.


def test_require_plan_exists_unknown_plan_id_raises_plan_not_found(tmp_path, monkeypatch):
    """Unknown plan_id: directory does not exist → PlanNotFoundError, no mkdir."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plans_dir = tmp_path / 'plans'
    # Pre-condition: the plans/ tree does not exist yet.
    assert not plans_dir.exists()

    with pytest.raises(PlanNotFoundError) as excinfo:
        require_plan_exists('does-not-exist')

    err = excinfo.value
    assert err.plan_id == 'does-not-exist'
    assert err.plan_dir == get_plan_dir('does-not-exist')
    assert 'does not exist' in err.reason
    # Side-effect invariant: guard rejection MUST NOT have created the plan dir
    # (nor the parent plans/ tree).
    assert not plans_dir.exists()
    assert not err.plan_dir.exists()


def test_require_plan_exists_dir_without_status_json_raises_plan_not_found(
    tmp_path, monkeypatch
):
    """Plan dir exists but lacks status.json → PlanNotFoundError, no mkdir."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'half-initialized'
    plan_dir.mkdir(parents=True)
    # Sanity: directory exists but no status.json yet.
    assert plan_dir.is_dir()
    assert not (plan_dir / 'status.json').exists()

    with pytest.raises(PlanNotFoundError) as excinfo:
        require_plan_exists('half-initialized')

    err = excinfo.value
    assert err.plan_id == 'half-initialized'
    assert err.plan_dir == plan_dir
    assert 'status.json' in err.reason
    # The pre-existing (stray) directory is left untouched — the guard MUST
    # NOT remove it, but it also MUST NOT create a status.json to satisfy
    # itself.
    assert plan_dir.is_dir()
    assert not (plan_dir / 'status.json').exists()


def test_require_plan_exists_with_status_json_returns_resolved_path(tmp_path, monkeypatch):
    """Plan dir with status.json → returns resolved Path (happy path)."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'initialized-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    result = require_plan_exists('initialized-plan')

    assert result == plan_dir
    assert result.is_dir()
    assert (result / 'status.json').is_file()


def test_plan_not_found_error_carries_plan_id_plan_dir_reason(tmp_path, monkeypatch):
    """PlanNotFoundError surfaces structured attributes for TOON envelopes."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    with pytest.raises(PlanNotFoundError) as excinfo:
        require_plan_exists('absent')

    err = excinfo.value
    # Exception message includes plan_id, reason, and the expected plan_dir.
    assert 'absent' in str(err)
    assert str(err.plan_dir) in str(err)
    assert err.reason


def test_jsonl_store_source_uses_canonical_local_plans_path():
    """The sibling jsonl_store.py references .plan/local/plans, not legacy form.

    Regression guard for the path-consolidation sweep: ``get_artifact_path``'s
    docstring must spell the artifact location as ``.plan/local/plans/`` — the
    legacy bare ``.plan/plans/`` form is incorrect since runtime state moved
    under ``.plan/local``.
    """
    import re

    jsonl_store_path = Path(file_ops.__file__).parent / 'jsonl_store.py'
    source = jsonl_store_path.read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
