#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``file_ops.resolve_plan_context`` — the single plan-context resolver.

``resolve_plan_context`` is the ONE entry point every plan-id consumer resolves
against. It returns a :class:`file_ops.PlanContext` carrying both faces of a
plan id:

* ``plan_dir`` — the plan's directory under ``{base_dir}/plans/``, computed
  eagerly as a pure path join.
* ``worktree_path`` — the working tree the plan's Bucket B scripts operate in,
  resolved LAZILY on first access because it shells out to
  ``manage-status get-worktree-path``.

It also owns the ``NO_PLAN`` sentinel — the plan-less routing target that
auto-materializes on demand and whose worktree face is always the main
checkout.

These tests run against a REAL temporary plan root (the ``plan_context``
fixture redirects ``PLAN_BASE_DIR`` at ``tmp_path``) rather than mocking the
path layer. Only the ``manage-status`` subprocess boundary
(``file_ops._query_worktree_path``) and the cwd-relative checkout resolver
(``file_ops.cwd_checkout_root``) are stubbed — everything between the resolver's
public surface and the filesystem executes for real, so a test that passes
proves the directory and its ``status.json`` actually landed on disk.
"""

import json
from pathlib import Path

import file_ops
import pytest
from file_ops import (
    NO_PLAN_SENTINEL,
    PlanContext,
    PlanNotFoundError,
    resolve_plan_context,
)

# The stand-in checkout root every "falls back to the main checkout" assertion
# compares against. Never written to — the checkout resolver is stubbed.
STUB_CHECKOUT_ROOT = '/tmp/test-plan-context-checkout'

# The stand-in persisted worktree path for a plan with use_worktree=true.
STUB_WORKTREE = '/tmp/test-plan-context-worktree'

REAL_PLAN_ID = 'plan-context-resolver-real'


@pytest.fixture
def stub_checkout_root(monkeypatch):
    """Pin ``cwd_checkout_root`` so main-checkout assertions are deterministic.

    Patched on ``file_ops`` because ``PlanContext._resolve_worktree_face``
    reaches it through the module global.
    """
    monkeypatch.setattr(file_ops, 'cwd_checkout_root', lambda: STUB_CHECKOUT_ROOT)
    return STUB_CHECKOUT_ROOT


def _stub_worktree_query(monkeypatch, use_worktree, worktree_path=''):
    """Stub the single ``manage-status get-worktree-path`` shell-out seam."""
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda _pid: (use_worktree, worktree_path),
    )


def _create_real_plan(plan_context, plan_id=REAL_PLAN_ID):
    """Create a plan directory that ``require_plan_exists`` accepts.

    Directory existence alone is NOT enough — ``require_plan_exists`` demands a
    ``status.json`` marker, so the helper writes one.
    """
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text('{"plan": {"title": "real"}}\n')
    return plan_dir


# =============================================================================
# A real, resolving plan id returns BOTH faces
# =============================================================================


class TestRealPlanIdReturnsBothFaces:
    """A real id that resolves yields a plan dir AND a worktree path."""

    def test_returns_plan_dir_and_worktree_path(
        self, plan_context, monkeypatch, stub_checkout_root
    ):
        expected_dir = _create_real_plan(plan_context)
        _stub_worktree_query(monkeypatch, use_worktree=True, worktree_path=STUB_WORKTREE)

        ctx = resolve_plan_context(REAL_PLAN_ID)

        assert isinstance(ctx, PlanContext)
        assert ctx.plan_id == REAL_PLAN_ID
        assert ctx.plan_dir == expected_dir
        assert ctx.worktree_path == STUB_WORKTREE
        assert ctx.is_sentinel is False

    def test_worktree_face_is_resolved_lazily_not_at_construction(
        self, plan_context, monkeypatch, stub_checkout_root
    ):
        """Constructing the context must NOT shell out to manage-status.

        The laziness is load-bearing, not an optimisation: ``get_plan_dir``
        delegates to this resolver on every one of its call sites, so an eager
        worktree face would put a subprocess behind every plan-path computation
        — including inside ``manage-status`` itself, the producer of that very
        command. A test that only asserted the resolved VALUE would pass just as
        well against an eager implementation, so the call COUNT is what pins the
        contract.
        """
        _create_real_plan(plan_context)
        calls: list[str] = []

        def counting_query(plan_id):
            calls.append(plan_id)
            return True, STUB_WORKTREE

        monkeypatch.setattr(file_ops, '_query_worktree_path', counting_query)

        ctx = resolve_plan_context(REAL_PLAN_ID)
        assert calls == [], 'worktree face was resolved eagerly at construction'

        assert ctx.worktree_path == STUB_WORKTREE
        assert calls == [REAL_PLAN_ID], 'first access must resolve exactly once'

        # Second access is served from the cached value, not a second subprocess.
        assert ctx.worktree_path == STUB_WORKTREE
        assert calls == [REAL_PLAN_ID], 'repeat access must not re-shell-out'

    def test_relative_persisted_worktree_path_is_absolutized(
        self, plan_context, monkeypatch, stub_checkout_root
    ):
        """A persisted relative path is returned absolute, never verbatim."""
        _create_real_plan(plan_context)
        _stub_worktree_query(monkeypatch, use_worktree=True, worktree_path='some/wt')

        ctx = resolve_plan_context(REAL_PLAN_ID)

        assert ctx.worktree_path.endswith('some/wt')
        assert ctx.worktree_path.startswith('/')

    def test_use_worktree_true_with_empty_path_raises(
        self, plan_context, monkeypatch, stub_checkout_root
    ):
        """``use_worktree=true`` with an empty path is corrupt metadata, not a fallback."""
        _create_real_plan(plan_context)
        _stub_worktree_query(monkeypatch, use_worktree=True, worktree_path='')

        ctx = resolve_plan_context(REAL_PLAN_ID)

        with pytest.raises(file_ops.WorktreeResolutionError, match='worktree_path is empty'):
            _ = ctx.worktree_path


# =============================================================================
# A real plan id with use_worktree=false returns the main checkout
# =============================================================================


class TestRealPlanIdWithoutWorktree:
    """``use_worktree=false`` resolves the worktree face to the main checkout."""

    def test_worktree_face_is_the_main_checkout(
        self, plan_context, monkeypatch, stub_checkout_root
    ):
        expected_dir = _create_real_plan(plan_context)
        _stub_worktree_query(monkeypatch, use_worktree=False)

        ctx = resolve_plan_context(REAL_PLAN_ID)

        assert ctx.plan_dir == expected_dir
        assert ctx.worktree_path == STUB_CHECKOUT_ROOT
        assert ctx.is_sentinel is False


# =============================================================================
# The NO_PLAN sentinel — auto-creation, idempotence, and the worktree face
# =============================================================================


class TestSentinelMaterialization:
    """The sentinel auto-creates its directory AND its ``status.json``."""

    def test_first_use_creates_directory_and_status_json(self, plan_context):
        sentinel_dir = plan_context.plans_dir / NO_PLAN_SENTINEL
        assert not sentinel_dir.exists(), 'fixture precondition: sentinel must not pre-exist'

        ctx = resolve_plan_context(NO_PLAN_SENTINEL)

        assert ctx.is_sentinel is True
        assert ctx.plan_dir == sentinel_dir
        assert sentinel_dir.is_dir()
        status_path = sentinel_dir / 'status.json'
        assert status_path.is_file(), (
            'the directory alone is not enough — require_plan_exists treats a '
            'directory without status.json as not-found, so a mkdir-only '
            'sentinel would leave every consumer failing with plan_not_found'
        )

    def test_materialized_sentinel_satisfies_require_plan_exists(self, plan_context):
        """The whole point of writing status.json: the sentinel must RESOLVE.

        This is the assertion that would catch a regression to a mkdir-only
        materialization — checking only that the directory exists would not.
        """
        resolve_plan_context(NO_PLAN_SENTINEL)

        assert file_ops.require_plan_exists(NO_PLAN_SENTINEL) == (
            plan_context.plans_dir / NO_PLAN_SENTINEL
        )

    def test_status_json_marks_the_plan_as_a_sentinel(self, plan_context):
        """The written marker records what it is, and that it has no worktree."""
        resolve_plan_context(NO_PLAN_SENTINEL)

        payload = json.loads(
            (plan_context.plans_dir / NO_PLAN_SENTINEL / 'status.json').read_text()
        )
        metadata = payload['plan']['metadata']
        assert metadata['sentinel'] is True
        assert metadata['use_worktree'] is False

    def test_second_use_is_idempotent_and_does_not_overwrite(self, plan_context):
        """Re-resolving must not clobber an existing sentinel ``status.json``.

        A caller may have written state into the shared sentinel plan; a second
        resolve is a lookup, not a re-initialization.
        """
        resolve_plan_context(NO_PLAN_SENTINEL)
        status_path = plan_context.plans_dir / NO_PLAN_SENTINEL / 'status.json'
        status_path.write_text('{"plan": {"title": "mutated by a caller"}}\n')

        ctx = resolve_plan_context(NO_PLAN_SENTINEL)

        assert ctx.is_sentinel is True
        assert json.loads(status_path.read_text())['plan']['title'] == 'mutated by a caller'

    def test_ensure_false_does_not_materialize_the_sentinel(self, plan_context):
        """``ensure=False`` is a pure path computation — no side effects.

        This is the mode ``get_plan_dir`` delegates in, and it runs on every one
        of its call sites; materializing there would create the sentinel
        directory as a side effect of merely naming a path.
        """
        sentinel_dir = plan_context.plans_dir / NO_PLAN_SENTINEL

        ctx = resolve_plan_context(NO_PLAN_SENTINEL, ensure=False)

        assert ctx.plan_dir == sentinel_dir
        assert ctx.is_sentinel is True
        assert not sentinel_dir.exists(), 'ensure=False must not touch the filesystem'


class TestSentinelWorktreeFace:
    """The sentinel's worktree face is ALWAYS the main checkout."""

    def test_worktree_face_is_the_main_checkout(self, plan_context, stub_checkout_root):
        ctx = resolve_plan_context(NO_PLAN_SENTINEL)

        assert ctx.worktree_path == STUB_CHECKOUT_ROOT

    def test_sentinel_never_shells_out_to_manage_status(self, plan_context, stub_checkout_root, monkeypatch):
        """A plan-less caller has no worktree, so the query must never run.

        Asserting only that the face EQUALS the checkout root would still pass
        if the sentinel went through ``manage-status`` and happened to fall back
        to the same value. Pinning "the query was never called" is what proves
        the sentinel short-circuits ahead of the subprocess.
        """
        def _explode(_plan_id):
            raise AssertionError(
                'the NO_PLAN sentinel must not query manage-status get-worktree-path'
            )

        monkeypatch.setattr(file_ops, '_query_worktree_path', _explode)

        ctx = resolve_plan_context(NO_PLAN_SENTINEL)

        assert ctx.worktree_path == STUB_CHECKOUT_ROOT

    def test_sentinel_face_is_never_a_worktree_path(self, plan_context, stub_checkout_root, monkeypatch):
        """Even with a worktree persisted under the sentinel id, main wins."""
        _stub_worktree_query(monkeypatch, use_worktree=True, worktree_path=STUB_WORKTREE)

        ctx = resolve_plan_context(NO_PLAN_SENTINEL)

        assert ctx.worktree_path == STUB_CHECKOUT_ROOT
        assert ctx.worktree_path != STUB_WORKTREE


# =============================================================================
# An unresolvable real id errors, and the error carries BOTH hint and caveat
# =============================================================================


class TestUnresolvablePlanId:
    """A real id that does not resolve raises, with a hint AND its caveat."""

    def test_raises_plan_not_found(self, plan_context):
        with pytest.raises(PlanNotFoundError) as exc_info:
            resolve_plan_context('plan-context-resolver-missing')

        assert exc_info.value.plan_id == 'plan-context-resolver-missing'

    def test_ensure_false_does_not_raise_for_a_missing_plan(self, plan_context):
        """``ensure=False`` is a path computation — no existence check."""
        ctx = resolve_plan_context('plan-context-resolver-missing', ensure=False)

        assert ctx.plan_dir == plan_context.plans_dir / 'plan-context-resolver-missing'
        assert ctx.is_sentinel is False

    def test_envelope_is_a_structured_error(self, plan_context):
        with pytest.raises(PlanNotFoundError) as exc_info:
            resolve_plan_context('plan-context-resolver-missing')

        envelope = exc_info.value.envelope
        assert envelope['status'] == 'error'
        assert envelope['error'] == 'plan_not_found'
        assert envelope['plan_id'] == 'plan-context-resolver-missing'
        assert 'plan-context-resolver-missing' in envelope['plan_dir']

    def test_envelope_carries_the_sentinel_hint(self, plan_context):
        with pytest.raises(PlanNotFoundError) as exc_info:
            resolve_plan_context('plan-context-resolver-missing')

        assert NO_PLAN_SENTINEL in exc_info.value.envelope['hint']

    def test_envelope_carries_the_hint_caveat(self, plan_context):
        """The caveat is NOT optional decoration on the hint.

        A hint without its caveat turns every mistyped plan id into a silent
        write against the shared sentinel directory: the caller reads "pass
        NO_PLAN", does so, and the typo is never surfaced. Asserting the hint
        alone would pass against exactly that broken payload, so both halves are
        pinned — and pinned separately, so removing either one fails a test.
        """
        with pytest.raises(PlanNotFoundError) as exc_info:
            resolve_plan_context('plan-context-resolver-missing')

        caveat = exc_info.value.envelope['hint_caveat']
        assert NO_PLAN_SENTINEL in caveat
        assert 'ONLY' in caveat
        assert 'do NOT substitute the sentinel' in caveat


# =============================================================================
# Bootstrap safety — the resolver must not drag in a non-bootstrap module
# =============================================================================


class TestSentinelConstantIsBootstrapSafe:
    """``file_ops`` must import cleanly on the bootstrap path.

    ``bootstrap_plugin.py`` and its siblings run BEFORE the executor sets
    PYTHONPATH and put only ``script-shared``, ``ref-toon-format`` and
    ``tools-file-ops`` on ``sys.path`` — ``tools-input-validation`` is NOT among
    them. Importing the sentinel from ``input_validation`` at ``file_ops``
    module scope therefore breaks every bootstrap import with
    ``ModuleNotFoundError``, which is why the constant is DEFINED in
    ``marketplace_paths`` (script-shared) and re-exported by
    ``input_validation``.
    """

    def test_sentinel_is_defined_in_the_bootstrap_safe_module(self):
        import marketplace_paths

        assert marketplace_paths.NO_PLAN_SENTINEL == 'NO_PLAN'

    def test_all_three_surfaces_are_the_same_single_definition(self):
        """One definition, three import surfaces — never three literals."""
        import input_validation
        import marketplace_paths

        assert file_ops.NO_PLAN_SENTINEL is marketplace_paths.NO_PLAN_SENTINEL
        assert input_validation.NO_PLAN_SENTINEL is marketplace_paths.NO_PLAN_SENTINEL

    def test_file_ops_does_not_import_input_validation_at_module_scope(self):
        """The claimed bootstrap contract, actually pinned.

        The two assertions above pass identically whether or not ``file_ops``
        imports ``input_validation`` at module scope — ``input_validation``
        re-exports the same object, and pytest's ``sys.path`` already carries
        every bundle, so neither one can observe the ``ModuleNotFoundError``
        the class docstring describes. This check reads the SOURCE instead:
        ``input_validation`` (``tools-input-validation``) is absent from the
        bootstrap ``sys.path``, so a module-scope import of it from
        ``file_ops`` is the exact defect, and only a source-level assertion
        can see it. Function-scope (lazy) imports are fine and are not
        flagged.
        """
        import ast

        tree = ast.parse(Path(file_ops.__file__).read_text(encoding='utf-8'))
        module_scope_imports: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                module_scope_imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_scope_imports.append(node.module)

        assert 'input_validation' not in module_scope_imports, (
            'file_ops imports input_validation at module scope — that module is '
            'NOT on the bootstrap sys.path, so every bootstrap import would fail '
            'with ModuleNotFoundError. Import the sentinel from marketplace_paths '
            '(script-shared) instead, or move the import inside the function.'
        )
