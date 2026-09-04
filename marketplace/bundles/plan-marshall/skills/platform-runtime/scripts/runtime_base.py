#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Abstract base class and shared TOON helpers for platform-runtime.

Defines the Runtime ABC with all 25 platform operations. Each concrete subclass
implements every operation for one target, or declines it via the no-op policy.

TOON helpers delegate to the canonical toon_parser from ref-toon-format — no
ad-hoc parsing or serialization in this module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from toon_parser import serialize_toon

#: The `permission fix` operation set, published once so no site restates it.
#:
#: The names were maintained by hand in five places — the argparse ``choices``,
#: each runtime's ``valid_ops``, and a test sweep. Copies drift in two
#: directions, and each drift is silent in a different way: a name in the router
#: but not in a runtime returns ``invalid_operation`` at dispatch, and a name in
#: a runtime but not in the router is rejected by argparse before that runtime
#: is ever reached. Every site derives from this tuple instead.
#:
#: Order is the argparse help order, so it is meaningful and kept.
PERMISSION_FIX_OPERATIONS: tuple[str, ...] = (
    "normalize",
    "add",
    "remove",
    "ensure",
    "consolidate",
    "protect-path",
)

# =============================================================================
# TOON Response Builders
#
# Every public helper returns a ready-to-print string via serialize_toon().
# Callers pass these strings directly to print() or return them as the script
# body. No ad-hoc formatting is performed; all serialization goes through the
# canonical ref-toon-format module.
# =============================================================================


def toon_success(operation: str, result: dict[str, Any] | None = None) -> str:
    """Build a TOON success response.

    Args:
        operation: The operation name (e.g. "session capture").
        result: Optional dict of result fields to merge into the response.

    Returns:
        Serialized TOON string.
    """
    data: dict[str, Any] = {
        "status": "success",
        "operation": operation,
    }
    if result:
        data.update(result)
    return serialize_toon(data)


def toon_error(operation: str, code: str, message: str) -> str:
    """Build a TOON error response.

    Args:
        operation: The operation name.
        code: Machine-readable error code (e.g. "hook_not_configured").
        message: Human-readable explanation of the error.

    Returns:
        Serialized TOON string.
    """
    data: dict[str, Any] = {
        "status": "error",
        "operation": operation,
        "error": code,
        "message": message,
    }
    return serialize_toon(data)


def toon_noop(operation: str, reason: str, alternative: str) -> str:
    """Build a TOON no-op response.

    Args:
        operation: The operation name.
        reason: Why the operation is a no-op on this target.
        alternative: What the caller can do instead.

    Returns:
        Serialized TOON string.
    """
    data: dict[str, Any] = {
        "status": "no-op",
        "operation": operation,
        "reason": reason,
        "alternative": alternative,
    }
    return serialize_toon(data)


def marshal_shape_error(operation: str, marshal_path: Any, marshal_data: Any) -> str | None:
    """Return a TOON ``io_error`` when a PARSED marshal.json is the wrong shape.

    A successful ``json.loads`` says only that the bytes were valid JSON — not
    that they were an object. Every ``project initial-setup`` implementation
    then seeds ``runtime.target`` by item assignment, which raises an UNCAUGHT
    ``TypeError`` on two parseable documents:

    - a top-level non-object (``[]``, ``"x"``, ``3``, ``null``) — item
      assignment against it is unsupported, so the verb dies with a traceback;
    - an object whose ``runtime`` key is PRESENT but not an object
      (``{"runtime": null}``) — the ``"runtime" not in data`` guard does not
      fire, so the nested assignment lands on the wrong type. Key-absent and
      key-present-but-wrong are distinct states, and only the second reaches
      here; a ``.get()``-based check would miss it entirely.

    Both are caller-visible corruption, so they take the route the unparseable
    case already takes: a structured ``io_error``, refused BEFORE any write, so
    the config this read exists to preserve is never overwritten.

    Published here rather than copied into each runtime so the implementations
    mirror one another BY CONSTRUCTION — the property both call sites' comments
    claim. A per-runtime copy is what let the parse edge be handled in both and
    the shape edge in neither.

    Args:
        operation: The operation name, used verbatim in the error response.
        marshal_path: The marshal.json path, rendered into the message.
        marshal_data: The value ``json.loads`` returned — of unknown shape.

    Returns:
        A serialized TOON ``io_error`` string when the shape is unsafe to
        mutate, or ``None`` when it is safe.
    """
    if not isinstance(marshal_data, dict):
        return toon_error(
            operation,
            "io_error",
            f"marshal.json at {marshal_path} parsed as "
            f"{type(marshal_data).__name__}, not a JSON object; refusing to overwrite it",
        )
    if "runtime" in marshal_data and not isinstance(marshal_data["runtime"], dict):
        return toon_error(
            operation,
            "io_error",
            f"marshal.json at {marshal_path} carries a 'runtime' key that is "
            f"{type(marshal_data['runtime']).__name__}, not a JSON object; refusing to overwrite it",
        )
    return None


# =============================================================================
# Abstract Base Class
# =============================================================================


class Runtime(ABC):
    """Abstract base for platform-runtime target implementations.

    Subclasses must implement every abstract method.  The router
    (platform_runtime.py) instantiates the correct subclass based on
    ``runtime.target`` in ``.plan/marshal.json`` and dispatches the requested
    operation.

    Methods return a serialized TOON string ready for ``print()``.  Use the
    ``toon_success``, ``toon_error``, and ``toon_noop`` helpers from this module
    to build responses; never format TOON strings manually. The one documented
    exception is :meth:`session_render_title`: a target that renders the title
    itself returns ``""`` on every path — written, nothing to write, or write
    failed alike — so the caller appends nothing and cannot read the outcome off
    the return value. A target that declines that operation returns an ordinary
    no-op TOON like any other.

    **The per-operation wire schemas live in ``standards/contract.md``.** This
    module states each operation's INTENT and its decline conditions; that
    document states the exact field set each status variant carries. An
    implementer needs both — the intent here to decide what to build, the schema
    there to agree on the wire with every other target. The declinable-primitive
    rules those schemas assume are in ``standards/no-op-policy.md``.
    """

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup.

        Creates ``.plan/``, seeds ``marshal.json`` with ``runtime.target``,
        ensures ``.plan/temp/`` exists, and installs any platform-specific
        session hook.

        A target that cannot create this plan state returns ``no-op`` with a
        ``reason`` and an ``alternative`` rather than reporting a setup it did
        not perform.

        Args:
            project_dir: Project root directory path.
            target: Platform target identifier — the value seeded as
                ``runtime.target``.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    @abstractmethod
    def project_install_hook(
        self,
        target: str,
        overwrite: Sequence[str] = (),
        enforcement: bool = False,
    ) -> str:
        """Wire this target's session/display integration into its own configuration.

        The operation carries INTENT only: make this target surface plan status
        to the operator over whatever channel it has. WHERE that wiring lives and
        WHAT it consists of are the implementation's to decide — INBOUND, the
        caller names the target and nothing else, so no configuration location,
        event name, or setting key is passed in.

        The RETURN is not symmetric, and deliberately so: a caller that asked for
        a write has to be told what was written, so the success payload names the
        elements the target actually manages and reports each one's disposition.
        Those names are the target's own. A caller reads them to report or to
        prompt; it must not hardcode them, and no other operation's contract
        depends on them.

        Unlike :meth:`project_initial_setup`, this operation creates no plan state
        and seeds no configuration file of plan-marshall's own; it only wires the
        integration.

        Re-invocation CONVERGES rather than merely detecting a duplicate: an
        already-present element whose shape is stale is rewritten to the current
        shape, and that outcome is reported distinguishably from a genuine no-op.
        Nothing is ever duplicated, and an element that is already correct is left
        untouched.

        A target that has no such integration channel returns ``no-op`` with a
        reason and an alternative rather than faking an install.

        Args:
            target: Platform target identifier — the value that appears as
                ``runtime.target`` in ``marshal.json``.
            overwrite: Conflict keys this call is authorised to overwrite. A
                pre-existing configuration value that differs from the one the
                integration wants is PRESERVED by default and reported as a
                conflict, so the caller can prompt the operator; naming that
                conflict's key here authorises overwriting it instead. The key
                set is target-defined — each implementation documents its own —
                and a target that defines one rejects an unrecognised key rather
                than silently ignoring it, so a typo can never read as "do not
                overwrite". A target that declines the operation outright defines
                no keys and reaches no key check; its ``no-op`` answers every
                argument, this one included.
            enforcement: Wire the target's TOOL-INVOCATION GATE instead of its
                session/display channel — the mechanism by which the target
                consults plan-marshall before a tool call runs, so a call that
                violates the active plan's discipline can be refused. A target
                with no such interception point declines this mode exactly as it
                would decline the operation. The two modes are independent:
                neither disturbs the other's configuration.

        Returns:
            Serialized TOON string (success, error, or no-op). A success payload
            reports, per element the target manages, what became of it: installed,
            converged onto the current shape, already correct, preserved because
            an existing value conflicted and no ``overwrite`` key authorised
            replacing it, or replaced because one did. Not every element admits
            every disposition — the set each one reports is the target's to
            define, and each target documents its own alongside the code that
            assigns it. The payload also carries ``already_present`` — True only
            when the call changed nothing at all.
        """

    # ------------------------------------------------------------------
    # Filesystem layout resolution
    # ------------------------------------------------------------------

    @abstractmethod
    def layout_skill_roots(self) -> str:
        """Resolve the project-local-skill discovery root(s) for this target.

        Returns the ordered list of directory paths where ``project:`` skills —
        finalize-steps, recipes, verify-steps, domain-attachable skills — are
        discovered on this target. They are typically project-relative or
        ``~``-anchored, but a target with a configuration-directory override
        derives a root beneath it and returns that, so a caller must assume
        neither form. Callers resolve each returned root against the relevant base
        directory and probe in list order (first match wins).

        A target with one such root returns a single-element list; a target that
        discovers skills across several returns them all, in the order its own
        discovery probes them.

        The result does not change for the lifetime of a process (the target
        is fixed by ``marshal.json``), so callers memoise it per process —
        this is the documented mitigation for the subprocess hop on hot
        config/manifest paths.

        A target that cannot resolve its project-local-skill discovery roots
        returns ``no-op`` with a ``reason`` and an ``alternative`` rather than
        fabricating a root list.

        Returns:
            Serialized TOON string carrying ``roots[N]`` — the ordered list of
            project-local-skill discovery roots for the active target — or a
            ``no-op`` from a target that cannot resolve them.
        """

    @abstractmethod
    def layout_bundle_cache_root(self) -> str:
        """Resolve the deployed-bundle (plugin-cache) root for this target.

        Returns the root directory under which this target deploys installed
        marketplace bundles for discovery outside the source checkout —
        i.e. where ``extension.py`` / bundle scripts are found when running
        from an installed plugin rather than the marketplace repo.

        A target that keeps a dedicated cache directory returns it. A target
        whose deployed bundles instead live among its project-local-skill roots
        returns the ones that can actually hold them — deployed bundles are shared
        across checkouts, so a root anchored inside a single project cannot — plus
        any root derived from the target's own configuration-directory override. Either way
        the caller probes the returned list in order, first match wins.

        The result does not change for the lifetime of a process (the target
        is fixed by ``marshal.json``), so callers memoise it per process.

        A target that cannot resolve its deployed-bundle cache root returns
        ``no-op`` with a ``reason`` and an ``alternative`` rather than
        fabricating a cache location.

        Returns:
            Serialized TOON string carrying ``roots[N]`` — the ordered list of
            deployed-bundle cache roots for the active target. The list may
            carry one root or several; callers ``~``-expand each entry before
            probing it. A target that cannot resolve them returns a ``no-op``
            instead.
        """

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    @abstractmethod
    def session_capture(self, plan_id: str) -> str:
        """Read and persist the current platform session identifier.

        A target that exposes a session identifier resolves it however that
        target makes it available and APPENDS it to the plan's
        ``status.metadata.session_ids`` list via ``manage-status``, so a plan
        spanning several sessions keeps every identity rather than only the
        newest. When the identifier ought to be reachable but is not — the
        target's wiring is incomplete — that is an ``error`` with code
        ``hook_not_configured``, never a silent pass. A target that exposes no
        session identifier at all returns ``no-op``.

        Args:
            plan_id: Plan identifier used by ``manage-status``.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    @abstractmethod
    def session_render_title(self, statusline: bool = False) -> str:
        """Render the current plan title in the terminal.

        Resolves session → plan, reads the title state from ``status.json``,
        composes the title via the ``manage-terminal-title`` composer, and
        emits the platform-appropriate sequence.

        Args:
            statusline: Select the target's PERSISTENT STATUS-READOUT channel
                over its event-driven one. When True, the success branch emits
                the composed title as plain text (``f"{icon} {body}"``) rather
                than the structured envelope the event channel expects. Noop
                branches still emit nothing on stdout either way. Default
                ``False`` selects the event-driven channel. A target with only
                one channel implements both settings over it, or declines the
                one it lacks.

        Returns:
            The empty string from a target that renders the title itself — on
            EVERY path. It has already written the title to stdout, or it had
            nothing to write, or the write FAILED: all three return ``""``, so
            the caller appends nothing and, critically, cannot tell the three
            apart from the return value. A target that renders must therefore
            name its outcome on a channel of its own (the reference
            implementation writes it to stderr), because a failed paint is
            otherwise indistinguishable from a successful one. A target that
            declines the operation returns an ordinary no-op TOON instead. This
            is the class docstring's one documented exception to the return-TOON
            rule.
        """

    @abstractmethod
    def session_push_title_token(
        self,
        plan_id: str,
        icon: str | None = None,
        store: str = "plans",
        slug: str | None = None,
    ) -> str:
        """Bind the session and settle *plan_id*'s title state for the next render.

        This seam BINDS and PERSISTS — it does not repaint. Terminal titles are
        delivered on the target's hook-driven render channel, which is
        event-driven rather than callable on demand, so a writer reaches the
        terminal by settling the state the *next* render will read.

        Resolves the plan's title state from ``status.json`` and composes it via
        the ``manage-terminal-title`` composer to establish that the state is
        renderable. Nothing is written to any terminal device.

        With ``store="orchestrator"`` the state-read seam resolves the epic's
        ``status.json`` via ``get_store_dir('orchestrator', slug)`` (the
        main-anchored orchestrator store) and composes the
        ``Orchestrator-{SlugName}`` body. That branch also establishes the
        session→epic binding, which is what lets the render channel resolve the
        epic on subsequent events — the load-bearing reason this seam exists.
        Gating is inherited: when the terminal-title setting is not configured
        the seam reports ``reason: feature_inactive`` — no new config knob.

        ``icon`` is OPTIONAL. When supplied it overrides the event-resolved icon
        for non-terminal phases (push-mode glyph, e.g. the lock ⏳/🔒 or build
        🔨). When omitted (``None``) the composer applies its default active
        icon — the shape every persisted-title-state change fires.

        Best-effort on every target. It never raises and never changes the
        caller's status or exit code.

        The two "nothing to settle" outcomes are ``success`` carrying a
        ``reason``, NOT ``no-op``: state absent or unrenderable
        (``reason: no_title_state``) and feature configured off
        (``reason: feature_inactive``). A target that HAS a render channel did
        its whole job in both cases — there was simply nothing to bind — so it
        reports success and says why. ``no-op`` is reserved for a target with no
        render channel to settle state for at all, which is the operation-level
        decline the no-op policy governs.

        Args:
            plan_id: Plan identifier whose ``status.json`` supplies the title
                state (default ``plans`` store; ignored for the orchestrator
                store).
            icon: Optional push-mode icon glyph that overrides the event-resolved
                icon for non-terminal phases; ``None`` for the default active icon.
            store: State store the title state is read from — ``"plans"``
                (default, plan-scoped ``status.json``) or ``"orchestrator"``
                (epic ``status.json`` under the main-anchored orchestrator
                store).
            slug: Epic slug selecting the orchestrator-store entry; required
                when ``store="orchestrator"``.

        Returns:
            Serialized TOON string (success or no-op) carrying the store entry
            fields, plus ``reason`` when there was nothing to settle. It carries
            no ``pushed`` and no ``delivery`` field: both described a repaint
            this seam does not perform.
        """

    @abstractmethod
    def session_bind(self, plan_id: str, session_id: str | None = None) -> str:
        """Bind the running session to *plan_id* (last-driven-wins).

        Writes the caller session's ``active-plan`` cache slot so
        ``session render-title`` / ``session resolve-plan`` resolve the session
        to *plan_id*. The policy is last-driven-wins: the caller's own slot is
        written unconditionally, with NO protect-active, NO stale-slot reclaim,
        and NO plan-dir-exists check — a session that switches to drive a
        different live plan rebinds cleanly instead of staying stuck.

        A target resolves ``session_id`` from the *session_id* argument first
        and, when absent, from whatever session identifier it exposes.
        Best-effort — never raises. A target that exposes none returns
        ``no-op``.

        Args:
            plan_id: Plan identifier to bind to the session's slot.
            session_id: Optional explicit session id; falls back to whatever
                session identifier the target exposes when omitted.

        Returns:
            Serialized TOON string (success or no-op) noting whether the slot
            was bound.
        """

    @abstractmethod
    def session_resolve_plan(self, session_id: str | None = None) -> str:
        """Resolve the running session's bound plan_id (the read side).

        Reads the caller session's ``active-plan`` cache slot. This is the read
        counterpart of :meth:`session_bind`; ``session render-title`` resolves
        the session->plan binding through the same read path.

        A target resolves ``session_id`` exactly as :meth:`session_bind` does —
        the argument first, then its own session identifier — and returns
        ``no-op`` when it exposes none.

        Args:
            session_id: Optional explicit session id; falls back to whatever
                session identifier the target exposes when omitted.

        Returns:
            Serialized TOON string carrying the resolved ``plan_id`` (empty when
            unbound), or ``no-op``.
        """

    @abstractmethod
    def session_doctor(self, fix: bool = False) -> str:
        """Scan every per-session active-plan slot and report binding health.

        Builds a plan->sessions reverse index over all
        ``~/.cache/plan-marshall/sessions/*/active-plan`` slots, flags any plan
        bound by more than one live session (a conflict), and identifies slots
        whose plan is archived/deleted (stale slots). An archived plan whose
        terminal title has not been delivered yet is EXEMPT — its binding is the
        pending render's only route to the plan — and becomes collectable once
        that state is delivered. The exemption is state-driven, never an
        elapsed-time grace period. When *fix* is True, GCs each stale slot. Keeps
        NO shared mutable index — the scan-then-GC is per-file and idempotent.

        A target that maintains per-session binding slots reports over them. A
        target with no session identifier keeps no slots and returns ``no-op``.

        Args:
            fix: When True, GC (remove) each stale slot whose plan is
                archived/deleted.

        Returns:
            Serialized TOON string carrying the conflict / stale report, or
            ``no-op``.
        """

    @abstractmethod
    def session_teardown(self) -> str:
        """Release the session's plan binding at end of session.

        The end-of-session counterpart to :meth:`session_bind` /
        :meth:`session_render_title`: it drops the caller session's own binding
        slots. Releasing the binding is the WHOLE of the teardown — the op writes
        no title reset, because a reset can only be delivered on the render
        channel and nothing may be reset on a channel that cannot deliver.

        This is the SOLE binding-release point, reached only from the session's
        own end-of-session signal. A plan's archive path must NOT call it:
        releasing the binding there would destroy the delivery route for the
        terminal state the archive just persisted, which the next render event
        still has to paint.

        **Activation-gated.** The activation signal is read FIRST: when the
        terminal-title feature is not wired up on this target, the op mutates NO
        binding and returns ``active: false`` with ``reason: feature_inactive``.
        A project that never opted into terminal titles is never touched by the
        teardown.

        When active, a target resolves its own session identifier and unbinds
        that session's slot. Never raises. A target with no render channel has no
        binding to release and returns ``no-op``.

        Returns:
            Serialized TOON string (success or no-op) carrying ``active`` and
            ``unbound``, plus ``reason`` when inactive.
        """

    @abstractmethod
    def session_reload_directive(self) -> str:
        """Resolve and surface the harness-appropriate post-upgrade reload directive.

        After the executor / agent set is regenerated (a steward upgrade), the
        running session must pick up the new artifacts. This op RESOLVES and
        SURFACES the target-appropriate directive only — a script CANNOT invoke a
        harness-level user-typed slash command, so the payload carries directive
        TEXT for the operator/orchestrator to act on. Zero-touch is impossible in
        any harness.

        A target with a live reload command returns ``success`` carrying that
        command's text, together with any caveat on how completely it reloads. A
        target with no such command returns ``no-op`` naming the alternative —
        typically a full session restart.

        Returns:
            Serialized TOON string (success or no-op) carrying the resolved
            reload directive text.
        """

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    @abstractmethod
    def permission_configure(self, scope: str, grants: list[dict[str, Any]]) -> str:
        """Write a semantic permission-intent list to the platform settings.

        Args:
            scope: ``"project"`` or ``"global"``.
            grants: List of semantic permission intents, each a dict with a
                ``kind`` key (``web-domain``, ``executor``, ``bundle``,
                ``skill``, ``path``, or ``macro``) plus the payload that kind
                needs. The target renders the permission-DSL grammar from these
                intents itself; no rendered rule text crosses this boundary.

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    @abstractmethod
    def permission_analyze(
        self, scope: str, checks: list[str], marshal_path: str | None
    ) -> str:
        """Read-only audit of permission configuration.

        Args:
            scope: ``"global"``, ``"project"``, or ``"both"``.
            checks: List of check names: ``"redundant"``, ``"suspicious"``,
                ``"missing-steps"``, or ``"all"``.
            marshal_path: Path to ``marshal.json`` (required when
                ``"missing-steps"`` is in checks).

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    @abstractmethod
    def permission_fix(
        self,
        scope: str,
        operation: str,
        arguments: list[Any],
        dry_run: bool,
    ) -> str:
        """Apply hygienic fixes to permission configuration.

        Args:
            scope: ``"project"`` or ``"global"``.
            operation: One of ``PERMISSION_FIX_OPERATIONS``.
            arguments: The operation's semantic arguments. For ``add`` /
                ``remove`` / ``ensure`` these are semantic permission intents
                (the same dict shape ``permission_configure`` takes). For
                ``protect-path`` they are directory paths to protect (the
                target renders the protecting rules itself, so no rule text
                crosses this boundary in either direction). Empty for
                ``normalize`` and ``consolidate``.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    @abstractmethod
    def permission_ensure_wildcards(
        self, scope: str, marketplace_dir: str, dry_run: bool
    ) -> str:
        """Ensure marketplace bundle wildcard permissions exist.

        Args:
            scope: ``"project"`` or ``"global"``.
            marketplace_dir: Path to the marketplace directory.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    @abstractmethod
    def permission_ensure_steps(
        self, marshal_path: str, scope: str, dry_run: bool
    ) -> str:
        """Ensure permissions exist for all ``project:{skill}`` steps.

        Args:
            marshal_path: Path to ``marshal.json``.
            scope: ``"project"`` or ``"global"``.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    @abstractmethod
    def permission_web_analyze(self, scope: str) -> str:
        """Read-only analysis of WebFetch/webfetch domain permissions.

        Args:
            scope: ``"global"``, ``"project"``, or ``"both"``.

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    @abstractmethod
    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Add or remove web domain permissions.

        Args:
            scope: ``"project"`` or ``"global"``.
            add: Domain names to allow.
            remove: Domain names to remove.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success, error, or no-op). A target whose
            permission model this operation cannot be expressed against declines
            here like any other operation, rather than reporting an outcome it
            did not reach.
        """

    # ------------------------------------------------------------------
    # Permission settings I/O — used by permission_common / permission_doctor
    # ------------------------------------------------------------------

    @abstractmethod
    def permission_settings_path(
        self, scope: str, write: bool = False, project_dir: str | None = None
    ) -> str:
        """Resolve the settings file path for a permission scope.

        Args:
            scope: ``"global"`` or ``"project"``.
            write: When ``True``, return the write-preferred path (which may
                differ from the read path on targets that split them).
            project_dir: When resolving the project scope, an explicit project
                root to resolve relative settings files against (optional; the
                target resolves against its own layout when omitted).

        Returns:
            Absolute file-system path as a string.

        Raises:
            ValueError: On an unsupported scope.
            RuntimeError: When the target has no settings files (honest
                decline — callers MUST handle this).
        """

    @abstractmethod
    def permission_load_settings(self, path: str) -> dict[str, Any]:
        """Load settings from a JSON file.

        Args:
            path: Absolute path to the settings JSON file.

        Returns:
            Parsed settings dictionary.  An empty ``{}`` on a missing file is
            legitimate; a parse error surfaces as ``{"error": "<message>"}``.
        """

    @abstractmethod
    def permission_save_settings(self, path: str, settings: dict[str, Any]) -> bool:
        """Persist settings to a JSON file.

        Args:
            path: Absolute path to write.
            settings: The settings dictionary to persist.

        Returns:
            ``True`` on success, ``False`` on failure.
        """

    @abstractmethod
    def permission_ensure_defaults(
        self,
        settings: dict[str, Any],
        settings_path: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Ensure the default permission set and prune retired rules.

        The runtime renders the default rules from its own resolved layout;
        no rendered grammar crosses the boundary.  The caller receives only
        semantic status: which defaults were added, which were removed, and
        whether the write was applied.

        Args:
            settings: Current settings dictionary (mutated in-place when
                ``dry_run`` is ``False``).
            settings_path: Absolute path to the settings file.
            dry_run: When ``True``, preview without writing.

        Returns:
            Status dict with keys ``defaults_added``, ``defaults_added_count``,
            ``defaults_removed``, ``defaults_removed_count``, ``applied``.
        """

    @abstractmethod
    def permission_check_skill_coverage(
        self, skill: str, allow_list: list[str]
    ) -> str | None:
        """Check if a skill is covered by an allow rule.

        Matches exact ``Skill({skill})`` or covering wildcard
        ``Skill({skill}:*)``.

        Args:
            skill: Skill name to check.
            allow_list: The current allow rules list.

        Returns:
            The matching rule string, or ``None`` if not covered.
        """

    @abstractmethod
    def permission_load_marshal_config(self, marshal_path: str) -> dict[str, Any]:
        """Load and parse marshal.json configuration.

        Args:
            marshal_path: Path to marshal.json.

        Returns:
            Parsed configuration dictionary.  An ``error`` key signals a
            parse failure.
        """

    @abstractmethod
    def permission_extract_project_steps(
        self, marshal_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Enumerate ``project:{skill}`` step references from marshal config.

        Args:
            marshal_config: The parsed marshal.json dictionary.

        Returns:
            List of dicts with keys ``skill``, ``step``, ``phase``.
        """

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @abstractmethod
    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for a planning phase.

        A target that exposes a session transcript sums the tokens recorded
        since this phase's last capture. A target that does not returns
        ``no-op`` — unless *total_tokens* is supplied.

        **Requirement when *total_tokens* is supplied:** the count MUST be
        persisted before ``success`` is returned. A target that cannot persist
        it MUST return ``no-op`` rather than a success carrying the number,
        because a success the caller cannot distinguish from a stored one turns
        a declined measurement into a silently lost one.

        Args:
            plan_id: Plan identifier.
            phase: Phase identifier (e.g. ``"phase-1-init"``).
            total_tokens: Explicit token count (optional; bypasses transcript
                scan when provided).

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    @abstractmethod
    def metrics_normalized_tokens(
        self,
        session_id: str,
        windows: list[tuple[str, str, str]],
        output_file: str,
    ) -> str:
        """Compute per-phase normalized token categories from the session transcript.

        This is the platform-owned transcript engine. The runtime walks the
        platform's session transcript (and any subagent transcripts), normalizes
        every usage record into the five canonical categories
        ``{input, output, cache_read, cache_creation, total}`` per phase, attributes
        each record to the phase window that contains its timestamp, and writes the
        per-phase result to *output_file* as JSON. ``manage-metrics`` reads that file
        and persists the numbers — it never parses a transcript itself.

        The JSON written to *output_file* is an object mapping each phase name to a
        normalized bucket:

        ``{phase_name: {input, output, cache_read, cache_creation, total,
        billing_weighted_total, subagent_total_tokens, subagent_tool_uses,
        subagent_duration_ms, subagent_samples,
        exploration_tool_calls, work_tool_calls, execute_tool_calls,
        orchestration_tool_calls, unclassified_tool_calls,
        exploration_result_bytes, work_result_bytes, execute_result_bytes,
        orchestration_result_bytes, unclassified_result_bytes,
        cache_read_attributed_exploration, cache_read_attributed_work,
        cache_read_attributed_execute, cache_read_attributed_orchestration,
        cache_read_attributed_unclassified, cache_read_unattributed,
        exploration_index_answerable_bytes, exploration_doc_residency_bytes,
        exploration_unattributed_bytes}}``

        The ten ``*_tool_calls`` / ``*_result_bytes`` keys are the exploration-share
        counters: each tool call observed in the transcript is classified by its
        tool name into one of five buckets, and both the call count (turn share)
        and its result payload's byte length (payload-byte share) are accumulated
        into the phase the call's timestamp attributes to.

        The six ``cache_read_attributed_{bucket}`` / ``cache_read_unattributed``
        keys are the CACHE-READ ATTRIBUTION group: they split the phase's recorded
        ``cache_read`` across the byte sources that put those bytes into context.
        A payload does not cost once — it costs on entry and then again on every
        later turn it stays resident, so the split is TURN-WEIGHTED RESIDENCY: each
        bucket's weight is its payload bytes multiplied by the number of the
        phase's turns those bytes remained in context, and the recorded
        ``cache_read`` is divided in proportion to those weights. Weight that
        cannot be tied to an observed payload — context the transcript does not
        explain, and every payload the walk saw no residency for — is NOT
        redistributed across the named buckets; it is disclosed as
        ``cache_read_unattributed``.

        **Exact reconciliation.** The five attributed parts plus
        ``cache_read_unattributed`` sum EXACTLY to that phase's recorded
        ``cache_read``, so no rounding can inflate a named share or lose weight
        into the gap. The residual is ALWAYS emitted with the group — never
        omitted when it happens to be zero — because a consumer must be able to
        read the residual to know how much of the split was explained.

        The three ``exploration_{sub}_bytes`` keys are the EXPLORATION SUB-SOURCE
        split. Exploration is not one activity: reading a source or test file is
        a lookup an index could answer, while reading a workflow or standard
        document is context that has to be resident to be useful. The split
        separates them by the call's TARGET PATH:

        - ``exploration_index_answerable_bytes`` — the call targeted source or
          test code.
        - ``exploration_doc_residency_bytes`` — the call targeted a workflow or
          standard document (skill and standard markdown bodies, ``doc/**``,
          ``*.adoc``, and the target's own agent-instructions file).
        - ``exploration_unattributed_bytes`` — no target path is recoverable: the
          call carried no path input, or it is not path-addressed at all
          (``WebFetch`` / ``WebSearch``). This bucket FAILS OPEN exactly as
          ``unclassified`` does for tool names — an unrecognised shape is COUNTED
          and surfaced here, never dropped and never guessed into a named
          sub-source.

        **Partition invariant.** The three sub-sources sum EXACTLY to
        ``exploration_result_bytes``; they re-cut bytes already counted there and
        add none. They carry the ``_bytes`` suffix rather than ``_result_bytes``
        deliberately: they are a BYTE-ONLY sub-split of one bucket and are NOT
        members of the ``{bucket}_{measure}`` exploration-counter family, so a
        consumer deriving that family's key set must not pick them up. There is
        no matching ``_tool_calls`` sub-split.

        **Absent is not zero.** A target that emits a phase bucket at all MUST
        carry the full counter key set — the exploration-share counters, the
        cache-read attribution group, AND the exploration sub-sources alike — so
        a zero there is a MEASURED zero. A phase whose recorded ``cache_read`` is
        0 therefore still carries all five attributed keys and the residual, and
        a phase that ran no exploration call still carries all three sub-source
        keys, every one of them at a measured zero. A target that declines the
        primitive emits no bucket, and its counters are ABSENT — consumers must
        preserve that distinction rather than substituting zeros for a target
        that never measured.

        A target that exposes a session transcript walks it — the session's own
        records and any subagent records it keeps — normalizes every usage and
        tool-call record it recognises, and writes the per-phase JSON. When such a
        target cannot locate a transcript for *session_id* it returns ``no-op``
        carrying ``transcript_not_found`` as its ``reason``.

        A target that exposes no transcript at all returns that same
        ``transcript_not_found`` no-op: it writes no bucket, and its counters are
        ABSENT rather than zero, per the rule above.

        Args:
            session_id: Platform session identifier whose transcript is walked.
            windows: Ordered ``[(phase_name, start_iso, end_iso), ...]`` phase
                windows used to attribute each usage record to a phase.
            output_file: Path the per-phase normalized JSON result is written to.

        Returns:
            Serialized TOON string (success, error, or no-op). The success payload
            carries attribution counters (``message_count``,
            ``subagent_calls_attributed``, ``subagent_transcripts_walked``,
            ``four_field_phases_attributed``, ``unclassified_tool_calls`` — the
            run-level count of tool names outside the classifier's
            population-derived domain, non-zero when the classifier needs
            extending). The no-op carries ``transcript_not_found`` as its
            ``reason`` — a no-op never carries an ``error`` field, and
            ``toon_noop`` cannot emit one.
        """

    # ------------------------------------------------------------------
    # Chat signal extraction
    # ------------------------------------------------------------------

    @abstractmethod
    def chat_extract_signal(self, session_id: str) -> str:
        """Reduce a platform session transcript to its signal-bearing turns.

        This is the platform-owned transcript engine for conversational-signal
        extraction: the runtime locates the platform session transcript for
        *session_id*, reduces it to the turns that carry operator-authored
        signal or decision markers, renders them as a plain-text reduced
        transcript, and returns the normalized record. The target's transcript
        FORMAT knowledge lives inside this operation; a consumer that needs
        signal from a session transcript invokes it and never touches a
        session JSONL itself.

        The success payload is the normalized record (always the same seven
        fields, whether the reduction kept one turn or none):

        ``{reduced_transcript, raw_turn_count, kept_raw_count,
        operator_turn_count, gate_decision_count, reduced_bytes, no_signal}``

        - ``reduced_transcript`` — ``"role: text"`` blocks for the kept turns
          in document order, ``\n\n``-separated (rendered under the
          ``operator-decision`` role for gate decisions recovered from the
          tool-result channel).
        - ``raw_turn_count`` / ``kept_raw_count`` — parseable turns before
          reduction and the raw turns kept, so the caller can see how much was
          boilerplate. Recovered gate decisions were never raw turns, so they
          appear as extra entries in ``reduced_transcript`` and are counted by
          ``gate_decision_count`` alone.
        - ``operator_turn_count`` / ``gate_decision_count`` — the two
          operator-signal classes, counted separately so a caller can
          distinguish surviving VOLUME from operator SIGNAL.
        - ``reduced_bytes`` — the reduced transcript's UTF-8 byte length. The
          runtime reports it and does NOT decide whether it fits a budget:
          read-budget policy is consumer-side, so a caller maps
          ``reduced_bytes`` against its own threshold and derives
          ``over_budget`` itself.
        - ``no_signal`` — ``true`` when the transcript carried no operator
          signal of either kind (``operator_turn_count == 0`` AND
          ``gate_decision_count == 0``). Deliberately NOT a survivor count:
          it is keyed on operator-authored counts so retained framework
          boilerplate can never move the verdict.

        A target that exposes a session transcript walks it — resolving
        *session_id* to the session JSONL exactly the way its other transcript
        operations do — and returns the success record. When such a target
        cannot locate a transcript for *session_id* it returns ``no-op``
        carrying ``transcript_not_found`` as its ``reason``.

        A target that exposes no transcript at all returns that same
        ``transcript_not_found`` no-op: it performs no reduction and carries no
        signal fields, which are ABSENT rather than zero — an unmeasured target
        must not be indistinguishable from a target whose transcript genuinely
        carried no operator signal.

        Args:
            session_id: Platform session identifier whose transcript is reduced.

        Returns:
            Serialized TOON string (success, error, or no-op). The no-op
            carries ``transcript_not_found`` as its ``reason`` — a no-op never
            carries an ``error`` field, and ``toon_noop`` cannot emit one.
        """

    # ------------------------------------------------------------------
    # Subagent dispatch
    # ------------------------------------------------------------------

    @abstractmethod
    def subagent_dispatch(
        self,
        agent: str,
        prompt_file: str | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Return platform-specific subagent invocation parameters.

        Does NOT spawn the subagent; returns a TOON payload with the exact
        parameters the caller must pass to the target's own subagent-spawning
        tool. The payload's ``invocation.tool`` names that tool, so the caller
        need not know it in advance.

        Two ``invocation`` fields are fixed across targets rather than
        target-defined, because the caller reads them: ``tool`` as above, and
        ``subagent_type``, which echoes the requested *agent* back. No target
        substitutes an agent of its own choosing, so a caller's selection always
        reaches the invocation.

        Returns ``no-op`` when the agent requires tools the target has no
        equivalent for.

        Args:
            agent: Agent name without ``.md`` extension.
            prompt_file: Optional path to a prompt markdown file; when omitted
                the agent's own body is used.
            context: Optional key-value pairs to inject into the prompt.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    @abstractmethod
    def wait_for(self, observable: str, reference: str, bound_seconds: int) -> str:
        """Hold a bounded wait until a concrete observable reaches a terminal state.

        The operation takes intent — WHICH kind of observable to inspect, WHICH
        instance of it (*reference*), and how long the caller is willing to hold
        the wait (*bound_seconds*) — and returns a normalized outcome.

        The observable is a **concrete, pollable thing a runtime subprocess can
        inspect**, named by a kind token drawn from a closed enumerated set. It
        is deliberately NOT an opaque caller-supplied condition descriptor: a
        subprocess has no way to evaluate an arbitrary predicate, so an opaque
        descriptor could only ever be answered with an unsubstantiated
        ``unknown``. An unrecognised kind is rejected with an explicit error
        rather than silently awaited.

        The returned ``outcome`` is normalized and observable-independent —
        ``succeeded``, ``failed``, ``timed_out``, ``killed`` (all terminal), or
        ``pending`` (not terminal). No observable-shaped or target-shaped value
        crosses the boundary in either direction.

        Two fail-closed rules are part of the contract:

        * **Silence is not success.** The terminal-state set MUST cover the
          failure signatures, so a negative outcome is reported as the negative
          outcome and is never mistaken for continued waiting.
        * **A bound is not a verdict.** Exhausting *bound_seconds* yields
          ``outcome: pending`` with ``terminal: false`` — an explicit unknown the
          caller must act on — never an implicit pass. An observable whose
          inspection channel cannot be reached is an ``error``, likewise never a
          pass.

        A target that exposes no runtime-held wait channel returns ``no-op``
        with a ``reason`` and an ``alternative``; the caller applies the
        alternative — invoke the observable's own bounded-wait verb in-turn, or
        checkpoint and re-dispatch — and continues.

        The governing policy (when to wait, who may hold a wait, the tiered
        realisation) lives in the target-neutral waiting standard; see
        ``plan-marshall`` ``standards/waiting.md`` and ADR-011.

        Args:
            observable: Observable KIND token from the closed enumerated set.
            reference: The concrete instance identifier within that kind.
            bound_seconds: Maximum wall-clock seconds to hold the wait.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    @abstractmethod
    def health_check(self, checks: str) -> str:
        """Verify platform integration.

        A target that cannot report on its platform integration returns ``no-op``
        with a ``reason`` and an ``alternative`` rather than inventing health
        results.

        Args:
            checks: Comma-separated list of checks: ``"all"``,
                ``"permissions"``, ``"display"``, ``"mcp-diagnostics"``.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """
