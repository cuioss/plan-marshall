#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
OpenCode implementation of every platform-runtime operation.

OpenCode-specific behaviour:
- Operations requiring a platform session id (session capture, session
  render-title) return ``no-op`` because OpenCode does not expose a session id
  to the shell environment (upstream issue #9292). Absent identity is the
  ``NO_SESSION_IDENTITY`` sentinel from runtime_base, never null; callers log
  the returned reason at INFO and apply the verbatim alternative per the
  no-op policy.
- project initial-setup succeeds but reports ``hook_installed: false`` for the
  same reason.
- permission operations are REAL writing operations against OpenCode's
  ``permission`` settings block: configure writes grants into the per-tool
  pattern maps, fix ensure/add/remove add and delete them (carrying
  ``allow``/``ask``/``deny`` actions via ``to_opencode_grant``), and fix
  protect-path renders deny entries guarding a named directory in BOTH the
  tilde and the absolute spelling — counts only ever cross back, exactly as on
  the Claude target. The maintenance operations consolidate and normalize
  report a ``success`` no-op, mirroring the Claude target's contract split.
- web-analyze and web-apply are real too: they read and write the ``webfetch``
  permission key in the same settings block.
- metrics capture declines on every input, manual count included, returning
  ``no-op`` (no token-persistence boundary is reachable from this target, so a
  success carrying the count would be a silently lost measurement).
- metrics normalized-tokens and chat extract-signal return ``no-op`` with
  ``transcript_not_found`` (no session transcript exists to walk or reduce).
- subagent dispatch succeeds, mapping the ``Task`` tool to OpenCode's ``task``.
- health-check succeeds; the ``display`` check always reports unhealthy on
  OpenCode because no hook file is present.
- wait for returns ``no-op``: OpenCode's runtime holds no wait channel, so the
  caller runs the observable's own bounded-wait verb in-turn instead.
- OpenCode never returns ``hook_not_configured``: that error names wiring that
  ought to be reachable but is not, while this target exposes no session
  identifier at all, so the honest answer is always ``no-op``.

All methods return a serialized TOON string via the helpers in runtime_base.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import runtime_info
from marketplace_paths import resolve_home
from runtime_base import (
    PERMISSION_FIX_OPERATIONS,
    Runtime,
    _unmapped_agent_tools,
    ensure_steps_without_skill_grants,
    extract_project_steps,
    toon_error,
    toon_noop,
    toon_success,
)
from toon_parser import BlockScalar

#: Default bash permission patterns to guarantee in OpenCode settings.
OPENCODE_DEFAULT_PERMISSIONS: tuple[str, ...] = (
    'python3 .plan/execute-script.py *',
    './pw *',
    'python3 marketplace/targets/sync.py *',
)

DEFAULT_OPENCODE_COMMANDS = OPENCODE_DEFAULT_PERMISSIONS

#: Version of the standing-rules bridge format written by project setup.
STANDING_RULES_BRIDGE_VERSION = 1

#: Baseline source the bridge copies from. CLAUDE.md stays authoritative.
STANDING_RULES_BASELINE = 'CLAUDE.md'

#: Marker embedded in every bridge file so drift detection reads the marker,
#: never rule prose.
STANDING_RULES_BRIDGE_MARKER = f'bridge-version: {STANDING_RULES_BRIDGE_VERSION}'


def _bridge_rules_path(project_dir: Path) -> Path:
    """Return the OpenCode workspace rules-bridge file path."""
    return project_dir / '.opencode' / 'rules' / 'plan-marshall-target-rules.md'


def _marshal_target_present(project_dir: Path, target: str) -> bool:
    """True when marshal.json already carries the target (benign no-write).

    A ``False`` seed on a file that already carries the target is the idle
    re-setup path, not a failure. Every other ``False`` — corrupt content,
    a non-dict document, an unwritable file — leaves the target unseeded.
    """
    try:
        data = json.loads((project_dir / '.plan' / 'marshal.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and isinstance(data.get('runtime'), dict) and data['runtime'].get('target') == target


def _seed_marshal_runtime_target(project_dir: Path, target: str) -> bool:
    """Seed ``runtime.target`` into ``.plan/marshal.json``, preserving other keys.

    Returns True when the file was written, False when it already carried the
    target or could not be written. Never raises.
    """
    marshal_file = project_dir / '.plan' / 'marshal.json'
    try:
        if marshal_file.is_file():
            data = json.loads(marshal_file.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return False
            runtime = data.get('runtime')
            if isinstance(runtime, dict) and runtime.get('target') == target:
                return False
            if not isinstance(runtime, dict):
                if runtime is None:
                    data['runtime'] = {'target': target}
                else:
                    # Present but malformed: refuse without writing (fail-closed).
                    # The caller reports io_error; the corrupt value is never destroyed.
                    return False
            else:
                runtime['target'] = target
            marshal_file.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
            return True
        marshal_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'runtime': {'target': target},
            'standing_rules_bridge': {
                'version': STANDING_RULES_BRIDGE_VERSION,
                'source': STANDING_RULES_BASELINE,
            },
        }
        marshal_file.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        return True
    except (OSError, ValueError):
        return False


def _write_rules_bridge(project_dir: Path) -> bool:
    """Copy the bridged standing-rules header into the OpenCode grant surface."""
    bridge = _bridge_rules_path(project_dir)
    body = (
        f'# Plan Marshall target rules (OpenCode bridge {STANDING_RULES_BRIDGE_MARKER})\n\n'
        f'Standing rules bridged from {STANDING_RULES_BASELINE} at project setup. '
        'This file is a bridge, not a fork: the baseline stays authoritative, '
        'and re-setup flags drift when this marker no longer matches the source.\n'
    )
    try:
        if bridge.is_file() and STANDING_RULES_BRIDGE_MARKER in bridge.read_text(encoding='utf-8'):
            try:
                baseline = project_dir / STANDING_RULES_BASELINE
                baseline_newer = baseline.is_file() and baseline.stat().st_mtime > bridge.stat().st_mtime
            except OSError:
                return False
            if not baseline_newer:
                # Bridge is current (baseline older, same age, or absent):
                # nothing to re-affirm.
                return False
            # Baseline newer than the bridge: fall through to the rewrite
            # below, which re-affirms the bridge and clears the
            # baseline_newer drift verdict on re-setup. The bridge carries
            # only the version marker plus a baseline pointer (no copied
            # prose), so re-affirmation is a rewrite, not a content merge.
        bridge.parent.mkdir(parents=True, exist_ok=True)
        bridge.write_text(body, encoding='utf-8')
        return True
    except OSError:
        return False


def standing_rules_drift_status(project_dir: str) -> dict[str, Any]:
    """Detect drift of the OpenCode standing-rules bridge against its baseline."""
    proj = Path(project_dir).resolve()
    baseline = proj / STANDING_RULES_BASELINE
    bridge = _bridge_rules_path(proj)
    if not baseline.is_file():
        return {'drift': False, 'needs_bridge': not bridge.is_file(), 'reason': 'baseline_missing'}
    if not bridge.is_file():
        return {'drift': False, 'needs_bridge': True, 'reason': 'bridge_missing'}
    try:
        text = bridge.read_text(encoding='utf-8')
    except OSError:
        return {'drift': True, 'needs_bridge': False, 'reason': 'bridge_unreadable'}
    if STANDING_RULES_BRIDGE_MARKER not in text:
        return {'drift': True, 'needs_bridge': False, 'reason': 'marker_mismatch'}
    try:
        if baseline.stat().st_mtime > bridge.stat().st_mtime:
            return {'drift': True, 'needs_bridge': False, 'reason': 'baseline_newer'}
    except OSError:
        return {'drift': True, 'needs_bridge': False, 'reason': 'stat_failed'}
    return {'drift': False, 'needs_bridge': False, 'reason': 'in_sync'}


#: Grant action wrappers ``to_opencode_grant`` peels before the tool grammar.
#: The wrapper action is carried into the returned triple, so a ``deny(...)``
#: intent can never degrade to ``allow`` by reaching the bare-form default.
_OPENCODE_GRANT_ACTIONS = ('allow', 'ask', 'deny')

#: Bash binaries that can exfiltrate a file's contents. Guarded in BOTH the
#: tilde and the absolute spelling of a protected directory, because either
#: can appear in a command line. Mirrors the Claude runtime's vector set.
_OPENCODE_EXFILTRATION_BASH_VECTORS = ('cat', 'head', 'tail', 'less', 'more', 'cp', 'grep', 'base64')

#: Characters a protected path may not carry. ``(`` and ``)`` delimit the
#: generic grant grammar, and ``*`` is OpenCode's pattern metacharacter, so a
#: path carrying one does not merely render badly — it renders as a DIFFERENT
#: rule. The grammar has no escape, so the only fail-closed answer is to
#: refuse. Mirrors ``claude_runtime._PATH_CHARS_THE_DSL_CANNOT_CARRY``.
_OPENCODE_PATH_CHARS_THE_MAP_CANNOT_CARRY = ('(', ')', '*')


def _opencode_config_dir() -> Path:
    """Return ~/.config/opencode directory path (overridable by OPENCODE_CONFIG_DIR)."""
    env = os.environ.get('OPENCODE_CONFIG_DIR')
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / '.config' / 'opencode').resolve()


def to_opencode_grant(perm: str) -> tuple[str, str, str]:
    """Translate Claude or generic permission strings to OpenCode format.

    Accepts an optional action wrapper around any bare form: ``allow(<form>)``,
    ``ask(<form>)`` or ``deny(<form>)``. Bare forms default to ``allow``. The
    wrapper verb is peeled FIRST and its action threads through every branch, so
    a deny intent can never degrade to ``allow`` by falling through to a
    lower-level default; an unrecognized wrapper verb is not peeled at all and
    the string is treated exactly as before.

    Returns: (tool_category, pattern_or_rule, action)
    """
    perm = perm.strip()
    action = 'allow'
    for verb in _OPENCODE_GRANT_ACTIONS:
        if perm.startswith(f'{verb}(') and perm.endswith(')'):
            action = verb
            perm = perm[len(verb) + 1 : -1].strip()
            break

    if perm.startswith('command(') and perm.endswith(')'):
        inner = perm[8:-1].strip()
        return ('bash', inner, action)

    if perm.startswith('Bash(') and perm.endswith(')'):
        inner = perm[5:-1].strip()
        return ('bash', inner, action)

    if perm.startswith('read_file(') and perm.endswith(')'):
        inner = perm[10:-1].strip()
        return ('read', inner, action)

    if perm.startswith('Read(') and perm.endswith(')'):
        inner = perm[5:-1].strip()
        return ('read', inner, action)

    if (perm.startswith('write_file(') or perm.startswith('Write(') or perm.startswith('Edit(')) and perm.endswith(')'):
        inner = perm[perm.index('(') + 1 : -1].strip()
        return ('edit', inner, action)

    if perm in ('read', 'edit', 'glob', 'grep', 'bash', 'webfetch', 'websearch', 'question', 'task', 'skill'):
        return (perm, '*', action)

    return ('bash', perm, action)


def _tilde_form(path: Path) -> str:
    """Render *path* with a leading ``~/`` when it lies under the home directory.

    Anchored on ``Path.relative_to`` rather than a string prefix test: with home
    ``/home/user``, a plain ``startswith`` also matches ``/home/user2/x`` and
    would render it as the nonsensical ``~2/x``. A path outside home is returned
    unchanged. The home directory ITSELF renders as bare ``~``, not ``~/.`` —
    the same hazard the Claude target's twin guards against.
    """
    try:
        relative = path.relative_to(resolve_home())
    except ValueError:
        return str(path)
    return '~' if str(relative) == '.' else '~/' + str(relative)


def _reject_unprotectable_path(protected_dir: str) -> str | None:
    """Return why *protected_dir* cannot be protected, or ``None`` if it can.

    A deny rule is a security control, so every input this cannot render
    faithfully is refused rather than rendered approximately. The refusal
    families mirror ``claude_runtime._reject_unprotectable_path`` exactly:
    empty or blank, carrying a delimiter or glob character, a control
    character, whitespace (moves the argument boundary in a bash pattern),
    not absolute, containing ``..``, and the filesystem root.
    """
    if not protected_dir or not protected_dir.strip():
        return 'path is empty'
    for char in _OPENCODE_PATH_CHARS_THE_MAP_CANNOT_CARRY:
        if char in protected_dir:
            return f'path contains {char!r}, which the permission grammar cannot carry'
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in protected_dir):
        return 'path contains a control character'
    if any(char.isspace() for char in protected_dir):
        return 'path contains whitespace, which moves the argument boundary in a bash pattern'
    path = Path(protected_dir)
    if not path.is_absolute():
        return 'path is not absolute'
    if '..' in path.parts:
        return "path contains '..'; name the directory to protect directly"
    if path == path.parent:
        return 'path is the filesystem root'
    return None


def _protect_path_deny_entries(protected_dir: str) -> dict[str, dict[str, str]]:
    """Render the OpenCode deny entries that guard *protected_dir* against reads.

    Every entry names the directory in BOTH the tilde and the absolute form,
    because a command line may use either. The ``python3 -c`` inline-script
    vector matches on the distinctive path tail so it catches either spelling
    inside a one-liner. A directory outside the home has no distinct tilde
    spelling, so the two forms collapse to one entry per tool; the result is
    de-duplicated, and the count a caller receives is therefore entries it will
    actually get rather than entries that were drafted.

    Defense-in-depth only: a blocklist is fundamentally incomplete, and the
    directory's own ``0700`` mode remains the primary boundary.

    Callers validate with ``_reject_unprotectable_path`` first; this renders.
    """
    normalized = Path(protected_dir)
    absolute = str(normalized)
    tilde = _tilde_form(normalized)
    distinctive = tilde[2:] if tilde.startswith('~/') else absolute

    entries: dict[str, dict[str, str]] = {'read': {}, 'bash': {}}
    for spelling in dict.fromkeys((tilde, absolute)):
        entries['read'][f'{spelling}/**'] = 'deny'
        for vector in _OPENCODE_EXFILTRATION_BASH_VECTORS:
            entries['bash'][f'{vector} {spelling}/*'] = 'deny'
    entries['bash'][f'python3 -c *{distinctive}*'] = 'deny'
    return entries


#: Operation name the persisted-approval reporter answers under.
PERSISTED_CONTRADICTION_OPERATION = 'permission report-persisted-contradictions'

#: Values in a persisted decision column that count as an allow row.
_PERSISTED_ALLOW_VALUES = frozenset({'allow', 'always_allow', 'always-allow'})

#: Candidate column names for the persisted-approval triple, lowest-case.
_TOOL_COLUMNS = ('tool', 'category', 'scope')
_PATTERN_COLUMNS = ('pattern', 'resource', 'command', 'rule')
_DECISION_COLUMNS = ('effect', 'decision', 'status', 'approval')


def _default_opencode_db_path() -> Path:
    """Return the default persisted-approval database path.

    Overridable by ``OPENCODE_DB_PATH`` for tests; otherwise the XDG data
    home value ``~/.local/share/opencode/opencode.db``.
    """
    env = os.environ.get('OPENCODE_DB_PATH')
    if env:
        return Path(env).expanduser()
    return Path.home() / '.local' / 'share' / 'opencode' / 'opencode.db'


def _normalize_persisted_tool(tool: str) -> str:
    """Normalize a tool name so ``shell`` and ``bash`` compare equal."""
    lowered = tool.strip().lower()
    if lowered == 'shell':
        return 'bash'
    return lowered


def _bare_command(pattern: str) -> str:
    """Return *pattern* stripped of a trailing ' *' glob and surrounding quotes."""
    stripped = pattern.strip().strip('"').strip("'").strip()
    if stripped.endswith(' *'):
        stripped = stripped[:-2].strip()
    elif stripped == '*':
        return ''
    return stripped


def _patterns_contradict(allow_pattern: str, deny_pattern: str) -> bool:
    """True when a persisted allow pattern contradicts a project deny pattern.

    Exact equality, either-direction glob match, or bare-command equivalence
    all count: ``ls`` contradicts ``ls *``, and ``ls *`` contradicts ``ls``.
    Bare-command equivalence strips a trailing ' *' from both sides before
    comparing, so ``allow git status *`` no longer contradicts
    ``deny git push *``.
    """
    allow = allow_pattern.strip()
    deny = deny_pattern.strip()
    if not allow or not deny:
        return False
    if allow == deny:
        return True
    if fnmatch.fnmatchcase(allow, deny) or fnmatch.fnmatchcase(deny, allow):
        return True
    bare_allow = _bare_command(allow)
    bare_deny = _bare_command(deny)
    return bare_allow != '' and bare_allow == bare_deny


def _deny_rules_from_config(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract deny ``(tool, pattern)`` pairs from one OpenCode config object.

    Parses the OpenCode 2 list shape (``permissions: [{action, resource,
    effect}]``) at the top level AND under each ``agent``/``agents`` entry, and
    the permission-map shape (``permission: {bash: {pattern: action}}``) in both
    places. An agent-scoped deny is a deny too — the spec's
    ``agents.*.permissions`` surface — so it participates in the contradiction
    check exactly as a top-level deny does.
    """
    denies: list[tuple[str, str]] = []

    def _consume(container: dict[str, Any]) -> None:
        permissions = container.get('permissions')
        if isinstance(permissions, list):
            for entry in permissions:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get('effect', '')).lower() != 'deny':
                    continue
                resource = entry.get('resource')
                if not isinstance(resource, str) or not resource.strip():
                    continue
                denies.append((str(entry.get('action', 'bash')), resource.strip()))
        perm_map = container.get('permission')
        if isinstance(perm_map, dict):
            for tool, value in perm_map.items():
                if isinstance(value, dict):
                    for pattern, action in value.items():
                        if str(action).lower() == 'deny' and isinstance(pattern, str) and pattern.strip():
                            denies.append((str(tool), pattern.strip()))
                elif isinstance(value, str) and value.lower() == 'deny':
                    denies.append((str(tool), '*'))

    if not isinstance(data, dict):
        return denies
    _consume(data)
    for key in ('agent', 'agents'):
        agents = data.get(key)
        if isinstance(agents, dict):
            for agent in agents.values():
                if isinstance(agent, dict):
                    _consume(agent)
    return denies


def _read_project_deny_rules(project_dir: str) -> list[tuple[str, str]]:
    """Read deny rules as (tool, pattern) pairs, read-only.

    Unions THREE sources, so a contradiction is found wherever the deny lives:
    the project ``opencode.json``, the project ``.opencode/opencode.json``,
    and the GLOBAL ``~/.config/opencode/opencode.json``
    (or ``$OPENCODE_CONFIG_DIR/opencode.json``). Each source contributes its
    top-level deny rules AND its ``agent``/``agents`` scoped denies. Never
    creates or writes any settings file; an absent or unreadable config yields
    nothing from that source. No config is ever written here.
    """
    proj = Path(project_dir)
    candidates = [
        proj / 'opencode.json',
        proj / '.opencode' / 'opencode.json',
        _opencode_config_dir() / 'opencode.json',
    ]
    denies: list[tuple[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen or not candidate.is_file():
            continue
        seen.add(key)
        try:
            data = json.loads(candidate.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        denies.extend(_deny_rules_from_config(data))
    return denies


def _column_lookup(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    """Return the first present column (original spelling) matching *candidates*."""
    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _list_persisted_allow_rows(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], bool]:
    """List persisted allow rows from every permission-like table, read-only.

    Returns ``(rows, recognised)``. ``recognised`` is True when at least ONE
    table carried both a pattern-like and a decision-like column — the live
    permission-table shape. When no table matches, the schema is unrecognised
    and the caller MUST report ``checkable: false`` rather than a clean result:
    an empty read of an unknown schema is an unmeasured observation, never
    evidence that nothing contradicts.

    Only ``SELECT`` statements run here; this helper never writes. Tables
    without both a pattern-like and a decision-like column are skipped. A
    decision column named ``action`` is only honored alongside an explicit
    ``tool`` column, so a list-shape ``(action, resource)`` table is not
    misread as ``(tool, decision)``. The table-list query error propagates so
    the caller maps an unreadable database to checkable False / db_unreadable.
    """
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    prioritized = sorted(tables, key=lambda name: 0 if name.lower() in ('permission', 'permissions') else 1)
    rows: list[dict[str, Any]] = []
    recognised = False
    for table in prioritized:
        try:
            info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        except sqlite3.Error:
            continue
        columns = [str(col[1]) for col in info]
        pattern_col = _column_lookup(columns, _PATTERN_COLUMNS)
        decision_col = _column_lookup(columns, ('effect', 'decision', 'status', 'approval'))
        tool_col = _column_lookup(columns, _TOOL_COLUMNS)
        if decision_col is None and tool_col is not None:
            maybe_action = _column_lookup(columns, ('action',))
            if maybe_action is not None and maybe_action.lower() != tool_col.lower():
                decision_col = maybe_action
        if pattern_col is None or decision_col is None:
            continue
        recognised = True
        select_cols = f'rowid, "{tool_col}"' if tool_col else 'rowid, NULL'
        select_cols += f', "{pattern_col}", "{decision_col}"'
        try:
            for rowid, tool, pattern, decision in conn.execute(f'SELECT {select_cols} FROM "{table}"'):
                if not isinstance(pattern, str) or not pattern.strip():
                    continue
                if str(decision).strip().lower() not in _PERSISTED_ALLOW_VALUES:
                    continue
                rows.append(
                    {
                        'table': table,
                        'rowid': rowid,
                        'tool': str(tool) if isinstance(tool, str) and tool.strip() else 'bash',
                        'pattern': pattern.strip(),
                    }
                )
        except sqlite3.Error:
            continue
    return rows, recognised


class OpenCodeRuntime(Runtime):
    """OpenCode concrete implementation of the Runtime ABC.

    Every method returns a serialized TOON string ready for ``print()``.
    """

    #: Model variables this target may resolve: OpenCode-specific sources
    #: first by construction (the shared collector reads first-match-wins),
    #: generic fallbacks last, and no Claude-specific source at all — kept
    #: here, outside the shared collector, whose contract forbids per-target
    #: logic.
    _OPENCODE_MODEL_ENV = frozenset(
        {
            'OPENCODE_MODEL',
            'OPENCODE_MODEL_NAME',
            'OPENCODE_MODEL_TYPE',
            'OPENCODE_MODEL_VERSION',
            'MODEL_NAME',
            'MODEL_TYPE',
            'MODEL_VERSION',
            'PLAN_MARSHALL_EFFORT',
            'MARSHALL_EFFORT',
            'EFFORT_LEVEL',
            'PLAN_MARSHALL_BUILD_VERSION',
            'BUILD_VERSION',
        }
    )

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup for OpenCode.

        Creates ``.plan/``, seeds ``marshal.json`` with ``runtime.target``,
        bridges the standing rules into the OpenCode settings surface, and
        reports bridge drift against the CLAUDE.md baseline on re-setup.
        No SessionStart hook is installed because OpenCode has no equivalent.
        The ``platform_runtime.py`` project initial-setup CLI renders this
        result verbatim as the steward-path operator surface.
        """
        import pathlib

        proj = pathlib.Path(project_dir)
        plan_dir = proj / '.plan'

        try:
            plan_dir.mkdir(parents=True, exist_ok=True)
            temp_dir = plan_dir / 'temp'
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return toon_error(
                'project initial-setup',
                'io_error',
                f'Failed to create .plan directory: {exc}',
            )

        # Ensure project settings exist and default executor is allowed
        settings_path = self.permission_settings_path('project', write=True, project_dir=str(proj))
        settings = self.permission_load_settings(settings_path)
        self.permission_ensure_defaults(settings, settings_path, dry_run=False)

        resolved = pathlib.Path(project_dir).resolve()
        marshal_written = _seed_marshal_runtime_target(resolved, target)
        if not marshal_written and not _marshal_target_present(resolved, target):
            return toon_error(
                'project initial-setup',
                'io_error',
                'Failed to seed runtime.target into .plan/marshal.json: file is corrupt or unwritable',
            )
        bridge_written = _write_rules_bridge(resolved)
        drift = standing_rules_drift_status(str(resolved))

        persisted_checkable = False
        persisted_warnings: list[dict[str, Any]] = []
        try:
            from toon_parser import parse_toon as _parse_report_toon

            report = _parse_report_toon(self.permission_report_persisted_contradictions(str(resolved)))
            if isinstance(report, dict):
                persisted_checkable = bool(report.get('checkable', False))
                warnings = report.get('contradictions', [])
                if isinstance(warnings, list):
                    persisted_warnings = [entry for entry in warnings if isinstance(entry, dict)]
        except Exception:
            persisted_checkable = False
            persisted_warnings = []

        return toon_success(
            'project initial-setup',
            {
                'target': target,
                'project_dir': str(proj.resolve()),
                'marshal_written': marshal_written,
                'bridge_written': bridge_written,
                'bridge_drift': drift['drift'],
                'bridge_reason': drift['reason'],
                'settings_path': settings_path,
                'hook_installed': False,
                'hook_skip_reason': ('OpenCode does not support a SessionStart hook equivalent (issue #9292)'),
                'persisted_approval_checkable': persisted_checkable,
                'persisted_approval_warnings': persisted_warnings,
            },
        )

    def project_install_hook(
        self,
        target: str,
        overwrite: Sequence[str] = (),
        enforcement: bool = False,
    ) -> str:
        """No-op: OpenCode exposes no session/display integration to wire.

        The decline is honest rather than a stub: OpenCode offers no hook channel
        at all (issue anomalyco/opencode#8619), so there is no configuration to
        write and no conflict an ``overwrite`` key could resolve. Declining every
        invocation — both install modes, any key set — is the whole behaviour.
        """
        return toon_noop(
            'project install-hook',
            'OpenCode exposes no session/display hook channel to wire (issue anomalyco/opencode#8619)',
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    # ------------------------------------------------------------------
    # Filesystem layout resolution
    # ------------------------------------------------------------------

    def layout_skill_roots(self) -> str:
        """Return the OpenCode project-local-skill roots (executor's root order).

        Mirrors ``generate_executor.py``'s OpenCode discovery-root list: the
        ``$OPENCODE_CONFIG_DIR`` override (when set), the project-local roots,
        and the ``~``-anchored user-global roots. The list is returned in
        priority order; callers probe first-match-wins.
        """
        import os
        import pathlib

        home = pathlib.Path.home()
        roots: list[str] = []

        env_config_dir = os.environ.get('OPENCODE_CONFIG_DIR', '')
        if env_config_dir:
            roots.append(str(pathlib.Path(env_config_dir) / 'skills'))

        roots.extend(
            [
                '.opencode/skills',
                '.claude/skills',
                '.agents/skills',
                str(home / '.config' / 'opencode' / 'skills'),
                str(home / '.claude' / 'skills'),
                str(home / '.agents' / 'skills'),
            ]
        )

        return toon_success(
            'layout skill-roots',
            {'target': 'opencode', 'roots': roots},
        )

    def layout_bundle_cache_root(self) -> str:
        """Return the OpenCode deployed-bundle cache root(s).

        OpenCode has no separate single plugin-cache directory; deployed
        bundles live under the project-local-skill discovery roots themselves.
        Return the ``~``-anchored user-global skill roots (the cross-checkout
        discovery homes) in priority order, mirroring the executor's discovery
        order. Callers probe first-match-wins.
        """
        import os
        import pathlib

        home = pathlib.Path.home()
        roots: list[str] = []

        env_config_dir = os.environ.get('OPENCODE_CONFIG_DIR', '')
        if env_config_dir:
            roots.append(str(pathlib.Path(env_config_dir) / 'skills'))

        roots.extend(
            [
                str(home / '.config' / 'opencode' / 'skills'),
                str(home / '.claude' / 'skills'),
                str(home / '.agents' / 'skills'),
            ]
        )

        return toon_success(
            'layout bundle-cache-root',
            {'target': 'opencode', 'roots': roots},
        )

    # ------------------------------------------------------------------
    # Harness operations
    # ------------------------------------------------------------------

    def harness_bash_timeout_ceiling(self) -> str:
        """Resolve OpenCode's Bash-tool timeout ceiling.

        Returns 120 seconds — the ceiling OpenCode's harness enforces on a
        single Bash invocation (its tool-harness default). This deliberately
        differs from the Claude ceiling: a consumer that stamps a Bash
        ``timeout`` must be bound by the target it actually runs on.
        """
        return toon_success(
            'harness bash-timeout-ceiling',
            {'target': 'opencode', 'ceiling_seconds': 120},
        )

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def session_capture(self, plan_id: str) -> str:
        """No-op: OpenCode does not expose a platform session id.

        This is the ABC's "exposes no session identifier at all" case, not its
        "ought to be reachable but is not" case: there is no wiring that could
        supply one (upstream issue #9292), so the decline is ``no-op`` rather
        than ``hook_not_configured``.
        """
        return toon_noop(
            'session capture',
            'OpenCode does not expose a platform-provided session id to the shell; tracked upstream at issue #9292',
            'pass --total-tokens manually to metrics capture',
        )

    def session_render_title(self, statusline: bool = False) -> str:
        """No-op: OpenCode has no plugin-driven terminal-title hook."""
        return toon_noop(
            'session render-title',
            'OpenCode has no plugin-driven terminal-title hook (issue anomalyco/opencode#8619)',
            "Use OpenCode's built-in TUI status surface for plan visibility",
        )

    def session_push_title_token(
        self,
        plan_id: str,
        icon: str | None = None,
        store: str = 'plans',
        slug: str | None = None,
    ) -> str:
        """No-op: OpenCode has neither a session id to bind nor a render channel."""
        return toon_noop(
            'session push-title-token',
            'OpenCode exposes no platform-provided session id to bind'
            ' (issue #9292) and has no plugin-driven terminal-title render channel'
            ' for a later event to deliver on (issue anomalyco/opencode#8619)',
            "Use OpenCode's built-in TUI status surface for plan visibility",
        )

    def session_bind(self, plan_id: str, session_id: str | None = None) -> str:
        """No-op: OpenCode does not expose a platform session id to bind."""
        return toon_noop(
            'session bind',
            'OpenCode does not expose a platform-provided session id to the shell,'
            ' so there is no per-session slot to bind (issue #9292)',
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_resolve_plan(self, session_id: str | None = None) -> str:
        """No-op: OpenCode does not expose a platform session id to resolve."""
        return toon_noop(
            'session resolve-plan',
            'OpenCode does not expose a platform-provided session id to the shell,'
            ' so there is no per-session binding to resolve (issue #9292)',
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_doctor(self, fix: bool = False) -> str:
        """No-op: OpenCode keeps no per-session active-plan cache to scan."""
        return toon_noop(
            'session doctor',
            'OpenCode does not expose a platform-provided session id, so there is'
            ' no per-session active-plan cache to scan (issue #9292)',
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_teardown(self) -> str:
        """No-op: OpenCode exposes no session binding to release."""
        return toon_noop(
            'session teardown',
            'OpenCode does not expose a platform-provided session id to the shell,'
            ' so there is no per-session binding to release (issue #9292)',
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_reload_directive(self) -> str:
        """No-op: OpenCode has no live plugin-reload command equivalent to
        Claude's ``/reload-plugins``; a full session restart is required to pick
        up the regenerated executor / agent set."""
        return toon_noop(
            'session reload-directive',
            "OpenCode exposes no live plugin-reload command equivalent to Claude's /reload-plugins",
            'Restart the OpenCode session to pick up the regenerated executor / agent set',
        )

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    def permission_configure(self, scope: str, grants: list[dict[str, Any]]) -> str:
        """Configure permission grants in OpenCode settings."""
        if scope not in ('project', 'global'):
            return toon_error(
                'permission configure',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = self.permission_settings_path(scope, write=True)
        settings = self.permission_load_settings(settings_path)
        if 'error' in settings:
            return toon_error(
                'permission configure',
                'load_error',
                f'Failed to load settings from {settings_path}: {settings["error"]}',
            )
        perm = settings.setdefault('permission', {})
        if not isinstance(perm, dict):
            perm = {}
            settings['permission'] = perm

        bash_val = perm.get('bash')
        if isinstance(bash_val, dict):
            bash_map = bash_val
        elif bash_val == 'allow':
            bash_map = None
        else:
            bash_map = {}
            perm['bash'] = bash_map

        added = 0
        for g in grants:
            rule = g.get('rule') or g.get('command') or str(g)
            cat, pat, act = to_opencode_grant(str(rule))
            if cat == 'bash':
                if bash_map is not None:
                    if bash_map.get(pat) != act:
                        bash_map[pat] = act
                        added += 1
            else:
                cat_val = perm.get(cat)
                if pat and pat != '*':
                    if not isinstance(cat_val, dict):
                        cat_map = {}
                        if isinstance(cat_val, str):
                            cat_map['*'] = cat_val
                        perm[cat] = cat_map
                    else:
                        cat_map = cat_val
                    if cat_map.get(pat) != act:
                        cat_map[pat] = act
                        added += 1
                else:
                    if cat_val != act:
                        perm[cat] = act
                        added += 1

        if added:
            if not self.permission_save_settings(settings_path, settings):
                return toon_error(
                    'permission configure',
                    'save_error',
                    f'Failed to write settings to {settings_path}',
                )

        return toon_success(
            'permission configure',
            {
                'scope': scope,
                'settings_path': settings_path,
                'grants_added': added,
            },
        )

    def permission_analyze(self, scope: str, checks: list[str], marshal_path: str | None) -> str:
        """Analyze OpenCode permissions for coverage."""
        valid_scopes = ('global', 'project', 'both')
        if scope not in valid_scopes:
            return toon_error(
                'permission analyze',
                'invalid_scope',
                f'--scope must be one of {valid_scopes}; got {scope!r}',
            )
        valid_checks = {'redundant', 'suspicious', 'missing-steps', 'all'}
        for check in checks:
            if check not in valid_checks:
                return toon_error(
                    'permission analyze',
                    'invalid_check',
                    f'Unknown check {check!r}; valid checks are: {", ".join(sorted(valid_checks))}',
                )

        scopes_to_check = ['global', 'project'] if scope == 'both' else [scope]
        results: dict[str, Any] = {}

        for sc in scopes_to_check:
            spath = self.permission_settings_path(sc, write=False)
            settings = self.permission_load_settings(spath)
            perm = settings.get('permission', {})
            bash_map = perm.get('bash', {}) if isinstance(perm, dict) else {}
            has_executor = False
            if isinstance(bash_map, dict):
                has_executor = any(
                    k in ('python3 .plan/execute-script.py *', 'python3 .plan/execute-script.py') and v == 'allow'
                    for k, v in bash_map.items()
                )
            elif bash_map == 'allow':
                has_executor = True

            missing_defaults = []
            if isinstance(bash_map, dict):
                for d in OPENCODE_DEFAULT_PERMISSIONS:
                    if bash_map.get(d) != 'allow':
                        missing_defaults.append(d)

            results[sc] = {
                'settings_path': spath,
                'has_executor': has_executor,
                'missing_defaults': missing_defaults,
            }

        return toon_success('permission analyze', {'scope': scope, 'analysis': results})

    def permission_fix(
        self,
        scope: str,
        operation: str,
        arguments: list[Any],
        dry_run: bool,
    ) -> str:
        """Apply fixes to OpenCode permissions."""
        if scope not in ('project', 'global'):
            return toon_error(
                'permission fix',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        valid_ops = set(PERMISSION_FIX_OPERATIONS)
        if operation not in valid_ops:
            return toon_error(
                'permission fix',
                'invalid_operation',
                f'--operation must be one of {sorted(valid_ops)}; got {operation!r}',
            )

        # protect-path is the one deny-writing operation. It validates its
        # arguments BEFORE loading settings, so an unprotectable path cannot
        # reach the renderer: a deny rule is a security control, and a path
        # this cannot render faithfully is refused, never rendered
        # approximately (fail-closed, mirroring the Claude runtime).
        if operation == 'protect-path':
            return self._permission_fix_protect_path(scope, arguments, dry_run)

        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        perm = settings.setdefault('permission', {})
        if not isinstance(perm, dict):
            perm = {}
            settings['permission'] = perm

        bash_map = perm.setdefault('bash', {})
        if not isinstance(bash_map, dict):
            bash_map = {}
            perm['bash'] = bash_map

        if operation in ('ensure', 'add'):
            added = 0
            for item in arguments:
                cat, pat, act = to_opencode_grant(str(item))
                if cat == 'bash':
                    if bash_map.get(pat) != act:
                        if not dry_run:
                            bash_map[pat] = act
                        added += 1
                else:
                    if perm.get(cat) != act:
                        if not dry_run:
                            perm[cat] = act
                        added += 1
            if added and not dry_run:
                self.permission_save_settings(settings_path, settings)
            return toon_success(
                'permission fix',
                {
                    'fix_operation': operation,
                    'scope': scope,
                    'added': added,
                    'dry_run': dry_run,
                },
            )

        if operation == 'remove':
            removed = 0
            for item in arguments:
                cat, pat, _ = to_opencode_grant(str(item))
                if cat == 'bash' and pat in bash_map:
                    if not dry_run:
                        del bash_map[pat]
                    removed += 1
                elif cat in perm:
                    if not dry_run:
                        del perm[cat]
                    removed += 1
            if removed and not dry_run:
                self.permission_save_settings(settings_path, settings)
            return toon_success(
                'permission fix',
                {
                    'fix_operation': operation,
                    'scope': scope,
                    'removed': removed,
                    'dry_run': dry_run,
                },
            )

        if operation in ('normalize', 'consolidate'):
            return toon_success(
                'permission fix',
                {
                    'fix_operation': operation,
                    'scope': scope,
                    'action': 'no-op',
                    'dry_run': dry_run,
                },
            )

        return toon_success(
            'permission fix',
            {
                'fix_operation': operation,
                'scope': scope,
                'action': 'no-op',
                'dry_run': dry_run,
            },
        )

    def _permission_fix_protect_path(self, scope: str, arguments: list[Any], dry_run: bool) -> str:
        """Write deny entries guarding each named directory (goal-based).

        The caller names DIRECTORIES; the deny patterns are rendered here as
        native OpenCode permission-map entries and never cross back — counts
        only. Mirrors the Claude runtime's protect-path contract: validation
        happens before ANY settings are loaded, a failed write is an
        ``io_error`` never a reported success, and a re-run that changes
        nothing leaves the settings file untouched (idempotence).
        """
        if not arguments:
            return toon_error(
                'permission fix',
                'invalid_operation',
                "--permissions must name at least one directory path for 'protect-path'",
            )
        for candidate in arguments:
            if not isinstance(candidate, str):
                return toon_error(
                    'permission fix',
                    'invalid_operation',
                    f'protect-path arguments must be directory paths; got {candidate!r}',
                )
            refusal = _reject_unprotectable_path(candidate)
            if refusal is not None:
                return toon_error(
                    'permission fix',
                    'invalid_operation',
                    f'cannot protect {candidate!r}: {refusal}',
                )

        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        if 'error' in settings:
            return toon_error(
                'permission fix',
                'invalid_settings',
                settings['error'],
            )
        perm = settings.setdefault('permission', {})
        if not isinstance(perm, dict):
            perm = {}
            settings['permission'] = perm

        # De-duplicate ACROSS the named paths, not only within each: two paths
        # can render the same entry (the same directory twice, or two spellings
        # of one directory), and a rules_total that counted them separately
        # would report entries the caller will not get.
        rendered: dict[str, dict[str, str]] = {}
        for protected_dir in arguments:
            for tool, tool_entries in _protect_path_deny_entries(protected_dir).items():
                for pattern, action in tool_entries.items():
                    rendered.setdefault(tool, {})[pattern] = action
        rules_total = sum(len(tool_entries) for tool_entries in rendered.values())

        changes_applied = 0
        proposed_count = 0
        for tool, tool_entries in rendered.items():
            # A blanket string action (``'allow'``) is OpenCode's catch-all; a
            # pattern map with last-match-wins must keep it as the map's ``*``
            # row BEFORE the deny rows so the specific denies win.
            current = perm.get(tool)
            if isinstance(current, dict):
                target = current
            elif isinstance(current, str):
                target = {'*': current}
                perm[tool] = target
            else:
                target = {}
                perm[tool] = target
            for pattern, action in tool_entries.items():
                if target.get(pattern) == action:
                    continue
                if dry_run:
                    proposed_count += 1
                else:
                    target[pattern] = action
                    changes_applied += 1

        # Write only when a row was actually added: this operation is meant to
        # be re-run for its idempotence, and re-serializing an operator's
        # settings file on a call that changed nothing is a modification they
        # can see for no effect.
        if not dry_run and changes_applied:
            if not self.permission_save_settings(settings_path, settings):
                # A security control that reports success when the write failed
                # tells an operator their files are guarded by rules that
                # reached nothing. Fail loudly instead.
                return toon_error(
                    'permission fix',
                    'io_error',
                    f'Failed to write settings to {settings_path}',
                )

        result: dict[str, Any] = {
            'scope': scope,
            'fix_operation': 'protect-path',
            'dry_run': dry_run,
            'target_file': settings_path,
            'changes_applied': 0 if dry_run else changes_applied,
            # Counts only — a rendered deny entry must not reach the caller.
            # Named, not protected: three spellings of one directory are three
            # names and one protection; rules_total is the honest measure.
            'paths_named': len(arguments),
            'rules_total': rules_total,
        }
        if dry_run:
            result['proposed_count'] = proposed_count
        return toon_success('permission fix', result)

    def permission_ensure_wildcards(self, scope: str, marketplace_dir: str, dry_run: bool) -> str:
        """Ensure baseline executor and build tool permissions in OpenCode."""
        if scope not in ('project', 'global'):
            return toon_error(
                'permission ensure-wildcards',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        res = self.permission_ensure_defaults(settings, settings_path, dry_run=dry_run)
        return toon_success('permission ensure-wildcards', res)

    def permission_ensure_steps(self, marshal_path: str, scope: str, dry_run: bool) -> str:
        """Ensure step permissions for OpenCode."""
        import pathlib

        if not pathlib.Path(marshal_path).exists():
            return toon_error(
                'permission ensure-steps',
                'marshal_not_found',
                f"{marshal_path} not found; run 'project initial-setup' first",
            )
        if scope not in ('project', 'global'):
            return toon_error(
                'permission ensure-steps',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        config = self.permission_load_marshal_config(marshal_path)
        steps = [] if 'error' in config else self.permission_extract_project_steps(config)
        return ensure_steps_without_skill_grants('OpenCode', config, steps, scope, dry_run)

    def permission_web_analyze(self, scope: str) -> str:
        """Analyze allowed URL domains in OpenCode."""
        valid_scopes = ('global', 'project', 'both')
        if scope not in valid_scopes:
            return toon_error(
                'permission web-analyze',
                'invalid_scope',
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )
        spath = self.permission_settings_path('project' if scope == 'project' else 'global', write=False)
        settings = self.permission_load_settings(spath)
        perm = settings.get('permission', {})
        webfetch = perm.get('webfetch') if isinstance(perm, dict) else None
        return toon_success(
            'permission web-analyze',
            {
                'scope': scope,
                'webfetch_permission': webfetch,
            },
        )

    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Apply URL allow/deny rules in OpenCode."""
        if scope not in ('project', 'global'):
            return toon_error(
                'permission web-apply',
                'invalid_scope',
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        settings_path = self.permission_settings_path(scope, write=not dry_run)
        settings = self.permission_load_settings(settings_path)
        if 'error' in settings:
            return toon_error(
                'permission web-apply',
                'load_error',
                f'Failed to load settings from {settings_path}: {settings["error"]}',
            )
        perm = settings.setdefault('permission', {})
        if not isinstance(perm, dict):
            perm = {}
            settings['permission'] = perm

        changed = False
        if add and perm.get('webfetch') != 'allow':
            if not dry_run:
                perm['webfetch'] = 'allow'
            changed = True
        elif remove and perm.get('webfetch') == 'allow':
            if not dry_run:
                del perm['webfetch']
            changed = True

        if changed and not dry_run:
            if not self.permission_save_settings(settings_path, settings):
                return toon_error(
                    'permission web-apply',
                    'save_error',
                    f'Failed to write settings to {settings_path}',
                )

        return toon_success(
            'permission web-apply',
            {
                'scope': scope,
                'changed': changed,
                'dry_run': dry_run,
            },
        )

    def permission_report_persisted_contradictions(
        self,
        project_dir: str,
        db_path: str | None = None,
    ) -> str:
        """Report persisted allow rows contradicting project deny rules.

        Read-only: opens ``opencode.db`` with sqlite3 read-only intent
        (``mode=ro``), inspects the LIVE permission-table schema, selects
        persisted allow rows, and diffs them against the deny rules read from
        ``project_dir``'s ``opencode.json``, its ``.opencode/opencode.json``,
        and the global ``~/.config/opencode/opencode.json`` — top-level AND
        ``agent``/``agents`` scoped. When no table carries the permission shape
        the schema is unrecognised and the result is ``checkable: false``
        (``schema_unrecognised``), never a clean zero. Each contradiction is
        returned as a warning entry carrying the operator removal command; the
        verb performs no writes, removes none of the persisted approvals, and
        never touches any config file. The plan-start flow surfaces the returned
        warnings verbatim.
        """
        resolved_db = Path(db_path).expanduser() if db_path else _default_opencode_db_path()
        if not resolved_db.is_file():
            return toon_success(
                PERSISTED_CONTRADICTION_OPERATION,
                {
                    'checkable': False,
                    'reason': 'db_missing',
                    'db_path': str(resolved_db),
                    'persisted_allow_count': 0,
                    'contradictions': [],
                },
            )
        try:
            conn = sqlite3.connect(f'file:{resolved_db}?mode=ro', uri=True)
        except (sqlite3.Error, OSError, ValueError):
            return toon_success(
                PERSISTED_CONTRADICTION_OPERATION,
                {
                    'checkable': False,
                    'reason': 'db_unreadable',
                    'db_path': str(resolved_db),
                    'persisted_allow_count': 0,
                    'contradictions': [],
                },
            )
        try:
            allow_rows, recognised = _list_persisted_allow_rows(conn)
        except sqlite3.Error:
            return toon_success(
                PERSISTED_CONTRADICTION_OPERATION,
                {
                    'checkable': False,
                    'reason': 'db_unreadable',
                    'db_path': str(resolved_db),
                    'persisted_allow_count': 0,
                    'contradictions': [],
                },
            )
        finally:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        if not recognised:
            return toon_success(
                PERSISTED_CONTRADICTION_OPERATION,
                {
                    'checkable': False,
                    'reason': 'schema_unrecognised',
                    'db_path': str(resolved_db),
                    'persisted_allow_count': 0,
                    'contradictions': [],
                },
            )
        deny_rules = _read_project_deny_rules(project_dir)
        contradictions: list[dict[str, Any]] = []
        for row in allow_rows:
            allow_tool = _normalize_persisted_tool(str(row.get('tool', 'bash')))
            allow_pattern = str(row.get('pattern', ''))
            for deny_tool_raw, deny_pattern in deny_rules:
                if _normalize_persisted_tool(deny_tool_raw) != allow_tool:
                    continue
                if not _patterns_contradict(allow_pattern, deny_pattern):
                    continue
                table = str(row.get('table', 'permission'))
                rowid = row.get('rowid')
                contradictions.append(
                    {
                        'tool': allow_tool,
                        'pattern': allow_pattern,
                        'deny_pattern': deny_pattern,
                        'warning': (
                            f"Persisted approval '{allow_pattern}' ({allow_tool}) "
                            f'contradicts project deny rule {deny_pattern!r}'
                        ),
                        'removal_hint': (
                            f'sqlite3 "{resolved_db}" '
                            f'\'DELETE FROM "{table}" WHERE rowid={rowid};\''
                            '  -- operator action: this tool never writes the database'
                        ),
                    }
                )
                break
        return toon_success(
            PERSISTED_CONTRADICTION_OPERATION,
            {
                'checkable': True,
                'db_path': str(resolved_db),
                'persisted_allow_count': len(allow_rows),
                'contradictions': contradictions,
            },
        )

    # ------------------------------------------------------------------
    # Permission settings I/O for OpenCode
    # ------------------------------------------------------------------

    def permission_settings_path(self, scope: str, write: bool = False, project_dir: str | None = None) -> str:
        """Resolve path to OpenCode settings file.

        - 'global': ~/.config/opencode/opencode.json (or $OPENCODE_CONFIG_DIR/opencode.json)
        - 'project': <project_dir>/opencode.json (prefers existing opencode.json or .opencode/opencode.json)
        """
        if scope == 'global':
            g_path = _opencode_config_dir() / 'opencode.json'
            if write and not g_path.is_file():
                g_path.parent.mkdir(parents=True, exist_ok=True)
                skeleton = {
                    '$schema': 'https://opencode.ai/config.json',
                    'permission': {
                        'bash': dict.fromkeys(OPENCODE_DEFAULT_PERMISSIONS, 'allow'),
                    },
                }
                try:
                    g_path.write_text(json.dumps(skeleton, indent=2) + '\n', encoding='utf-8')
                except OSError:
                    pass
            return str(g_path)

        if scope == 'project':
            pd = Path(project_dir).resolve() if project_dir else Path.cwd().resolve()
            root_cfg = pd / 'opencode.json'
            if root_cfg.is_file():
                return str(root_cfg)
            dot_cfg = pd / '.opencode' / 'opencode.json'
            if dot_cfg.is_file():
                return str(dot_cfg)

            target_cfg = root_cfg
            if (pd / '.opencode').is_dir():
                target_cfg = dot_cfg

            if write and not target_cfg.is_file():
                target_cfg.parent.mkdir(parents=True, exist_ok=True)
                skeleton = {
                    '$schema': 'https://opencode.ai/config.json',
                    'permission': {
                        'bash': dict.fromkeys(OPENCODE_DEFAULT_PERMISSIONS, 'allow'),
                    },
                }
                try:
                    target_cfg.write_text(json.dumps(skeleton, indent=2) + '\n', encoding='utf-8')
                except OSError:
                    pass
            return str(target_cfg)

        raise ValueError(f"Unsupported scope: {scope!r}; must be 'global' or 'project'")

    def permission_load_settings(self, path: str) -> dict[str, Any]:
        """Load settings from an OpenCode JSON file."""
        p = Path(path)
        if not p.is_file():
            return {}
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            return {'error': str(exc)}

    def permission_save_settings(self, path: str, settings: dict[str, Any]) -> bool:
        """Persist settings to an OpenCode JSON file."""
        p = Path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
            return True
        except OSError:
            return False

    def permission_ensure_defaults(
        self,
        settings: dict[str, Any],
        settings_path: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Ensure default Plan Marshall executor permissions exist in OpenCode settings."""
        if 'error' in settings:
            return {
                'defaults_added': [],
                'defaults_added_count': 0,
                'defaults_removed': [],
                'defaults_removed_count': 0,
                'applied': False,
                'error': settings['error'],
            }
        perm = settings.setdefault('permission', {})
        if not isinstance(perm, dict):
            perm = {}
            settings['permission'] = perm

        bash_map = perm.get('bash')
        if not isinstance(bash_map, dict):
            if bash_map == 'allow':
                return {
                    'defaults_added': [],
                    'defaults_added_count': 0,
                    'defaults_removed': [],
                    'defaults_removed_count': 0,
                    'applied': False,
                }
            bash_map = {}
            perm['bash'] = bash_map

        added: list[str] = []
        for cmd in OPENCODE_DEFAULT_PERMISSIONS:
            if bash_map.get(cmd) != 'allow':
                added.append(cmd)
                if not dry_run:
                    bash_map[cmd] = 'allow'

        saved = False
        if added and not dry_run:
            saved = self.permission_save_settings(settings_path, settings)

        return {
            'defaults_added': added,
            'defaults_added_count': len(added),
            'defaults_removed': [],
            'defaults_removed_count': 0,
            'applied': bool(added and not dry_run and saved),
        }

    def permission_check_skill_coverage(self, skill: str, allow_list: list[str]) -> str | None:
        """Decline — OpenCode permission checking does not use Skill(...) coverage."""
        return None

    def permission_load_marshal_config(self, marshal_path: str) -> dict[str, Any]:
        """Load marshal.json — target-neutral, same schema on every target."""
        marshal = Path(marshal_path)
        if not marshal.exists():
            return {'error': f'marshal.json not found: {marshal_path}'}
        try:
            data = json.loads(marshal.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {'error': f'Invalid JSON in {marshal_path}: {exc}'}
        except OSError as exc:
            return {'error': f'Could not read {marshal_path}: {exc}'}
        if not isinstance(data, dict):
            return {'error': f'Invalid marshal.json (expected object) in {marshal_path}'}
        return data

    def permission_extract_project_steps(self, marshal_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Enumerate project:{skill} step references — target-neutral.

        Delegates to :func:`runtime_base.extract_project_steps`, the same reader
        the Claude runtime uses. marshal.json is a shared, target-neutral file,
        so the schema is identical across targets and the reader must be too.

        This method previously inlined the phase tuple and guarded with
        ``isinstance(entries, list)``. Against a real marshal.json — where
        ``steps`` is a keyed map — that guard made the scan return an empty
        list, which read exactly like a marshal.json with no ``project:`` steps
        in it.
        """
        return extract_project_steps(marshal_config)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_capture(self, plan_id: str, phase: str, total_tokens: int | None) -> str:
        """Record token consumption for OpenCode.

        This operation is an honest ``no-op`` on OpenCode — on EVERY input,
        manual count included.

        OpenCode exposes no session transcript, so auto-capture has nothing to
        sum. And this target reaches no persistence boundary: the token-cursor
        write and the ``manage-metrics end-phase`` call live in the Claude
        runtime, so even an explicit ``--total-tokens`` cannot be stored here.
        The Runtime contract therefore forbids returning ``success`` for a
        manual count — a success the caller cannot distinguish from a stored one
        turns a declined measurement into a silently lost one. The target
        declines instead, naming the reason and the alternative.

        Do NOT "helpfully" return a success carrying the count: that was the
        fabricate-success defect this no-op exists to close. The recommended
        remediation is to relocate the (target-neutral) metrics persistence
        boundary to a shared home so both runtimes can reach it; until then,
        OpenCode declines rather than lying about a write it cannot perform.
        """
        if total_tokens is None:
            reason = (
                'automatic token capture requires a platform-provided session id,'
                ' which OpenCode does not expose (issue #9292)'
            )
            alternative = (
                'run metrics capture on the Claude target, or wire a shared'
                ' metrics-persistence boundary OpenCode can reach'
            )
        else:
            reason = (
                'OpenCode reaches no token-persistence boundary, so an explicit count cannot be stored (issue #9292)'
            )
            alternative = (
                'run metrics capture on the Claude target, or wire a shared'
                ' metrics-persistence boundary OpenCode can reach'
            )
        return toon_noop(
            'metrics capture',
            reason,
            alternative,
        )

    def metrics_normalized_tokens(
        self,
        session_id: str,
        windows: list[tuple[str, str, str]],
        output_file: str,
    ) -> str:
        """Honest no-op: OpenCode exposes no session transcript to normalize.

        OpenCode does not provide a session transcript, so there is nothing to
        walk or normalize. Returns ``transcript_not_found`` so the
        finalize/retrospective enrich steps degrade gracefully (skip enrichment).

        **Counters are ABSENT here, never zero.** This method constructs no
        per-phase bucket, writes no *output_file*, and returns no counters, which
        is exactly the required shape: OpenCode declines the primitive rather than
        reporting a measurement it never took. Do NOT "helpfully" add a
        zero-initialized bucket carrying the exploration-share counters — a zero
        asserts "measured, and it was none", which would make an unmeasured target
        indistinguishable from a target that genuinely explored nothing and would
        silently pollute the corpus the ``exploration-share`` audit check reads.
        This is the declinable-primitive posture of ADR-011 and the
        explicit-unknown rule of ADR-009.
        """
        return toon_noop(
            'metrics normalized-tokens',
            'transcript_not_found',
            'pass --total-tokens manually to metrics capture',
        )

    def chat_extract_signal(self, session_id: str) -> str:
        """Honest no-op: OpenCode exposes no session transcript to reduce.

        OpenCode does not provide a session transcript, so there is nothing to
        locate or reduce. Returns ``transcript_not_found`` so the
        chat-history aspect degrades gracefully (skip enrichment).

        **Signal fields are ABSENT here, never zero.** This method performs no
        reduction and returns no ``operator_turn_count`` / ``gate_decision_count``
        / ``no_signal`` fields, which is exactly the required shape: OpenCode
        declines the primitive rather than reporting a measurement it never
        took. Do NOT "helpfully" add a zero-initialized ``no_signal: true`` and
        empty ``reduced_transcript`` — a zero asserts "measured, and there was
        none", which would make an unmeasured target indistinguishable from a
        target whose transcript genuinely carried no operator signal and would
        silently pollute the corpus that reads those fields. This is the
        declinable-primitive posture of ADR-011 and the explicit-unknown rule
        of ADR-009.
        """
        return toon_noop(
            'chat extract-signal',
            'transcript_not_found',
            'run on a target that exposes a session transcript, or record the session with session capture first',
        )

    # ------------------------------------------------------------------
    # Subagent dispatch
    # ------------------------------------------------------------------

    def subagent_dispatch(
        self,
        agent: str,
        prompt_file: str | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Return OpenCode subagent invocation parameters.

        Uses ``task`` (lowercase) as the OpenCode native tool name, and echoes
        the REQUESTED *agent* back as ``subagent_type`` so the caller's
        selection reaches the invocation instead of being discarded.

        Verify-first clause 1: the ``task``-tool dispatch fires only when the
        tool is available in this envelope. A caller that knows the tool is
        absent passes ``task_tool_available: False`` (legacy) or the
        target-neutral ``spawning_tool_available: False`` inside *context*;
        either explicit ``False`` declines — the decline takes the explicit
        logged inline branch — a ``no-op`` naming the inline fallback (the
        caller propagates ``usage`` as ``unknown``) — instead of a faux
        success the harness cannot honour. The flags default explicitly to
        available: an absent flag (or an absent *context*) reads as ``True``
        and the dispatch fires; only an explicit ``False`` declines. Both
        flags are consumed here and never merged into the prompt.

        Verify-first clause 2: the requested agent's frontmatter tools must
        map onto the OpenCode tool set (``targets/opencode/mapping.json``).
        An agent requiring a tool OpenCode has no equivalent for declines
        with the same inline-branch ``no-op``. When the agent file or the
        mapping is unreadable the check is vacuous and the dispatch proceeds
        — an unmeasured source is never read as a refusal.
        """
        import pathlib

        task_tool_available = True if not isinstance(context, dict) else context.get('task_tool_available', True)
        spawning_tool_available = (
            True if not isinstance(context, dict) else context.get('spawning_tool_available', True)
        )
        if task_tool_available is False or spawning_tool_available is False:
            return toon_noop(
                'subagent dispatch',
                "OpenCode 'task' tool is not available in this envelope — "
                'take the explicit logged inline branch instead of dispatching',
                'Inline the agent logic in-turn and propagate usage as unknown',
            )

        if prompt_file is not None and not pathlib.Path(prompt_file).exists():
            return toon_error(
                'subagent dispatch',
                'prompt_not_found',
                f'prompt file not found: {prompt_file}',
            )

        unmapped = _unmapped_agent_tools(agent, 'opencode')
        if unmapped:
            return toon_noop(
                'subagent dispatch',
                f'Agent {agent!r} requires unmapped tools: {", ".join(unmapped)}',
                'Remove unsupported tools from agent frontmatter or inline the agent logic',
            )

        prompt_body = f'Run {agent}'
        if prompt_file is not None:
            try:
                prompt_body = pathlib.Path(prompt_file).read_text(encoding='utf-8')
            except OSError as exc:
                return toon_error(
                    'subagent dispatch',
                    'prompt_not_found',
                    f'Failed to read prompt file {prompt_file}: {exc}',
                )

        if context:
            context = {k: v for k, v in context.items() if k not in ('task_tool_available', 'spawning_tool_available')}
            for key, value in context.items():
                prompt_body = prompt_body.replace(f'{{{key}}}', str(value))

        return toon_success(
            'subagent dispatch',
            {
                'platform': 'opencode',
                'usage': 'unknown',
                'invocation': {
                    'tool': 'task',
                    'description': f'Run {agent}',
                    'prompt': BlockScalar(prompt_body),
                    'subagent_type': agent,
                },
            },
        )

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_for(self, observable: str, reference: str, bound_seconds: int) -> str:
        """No-op: OpenCode's runtime holds no wait channel.

        The decline is not hollow. Every liveness surface a runtime-held wait
        would need is already absent on this target — no platform-provided
        session id (issue #9292), no hook channel (issue anomalyco/opencode#8619)
        — and the OpenCode runtime bootstraps none of the shared build layer the
        observables are inspected through. A wait held here would be an
        unobservable block with no re-attach path.

        The alternative is real, shipped behaviour on this target, not a
        weaker stand-in for a capability OpenCode lacks entirely: the
        observable's own bounded-wait verb runs in-turn, and
        checkpoint-and-re-dispatch remains available when the bound is large.
        """
        return toon_noop(
            'wait for',
            "OpenCode's runtime holds no wait channel — it has no platform-provided"
            ' session id (issue #9292), no hook channel'
            ' (issue anomalyco/opencode#8619), and no shared build layer to inspect'
            ' an observable through, so a wait held here would be unobservable and'
            ' could not be re-attached',
            "Invoke the observable's own bounded-wait verb synchronously in-turn"
            ' (build-server-client wait, ci checks wait), or checkpoint and'
            ' re-dispatch to re-establish the wait from persisted state',
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self, checks: str) -> str:
        """Verify OpenCode platform integration.

        The ``display`` check always reports unhealthy because no hook file is
        installed.  All other checks report healthy.
        """
        check_list = [c.strip() for c in checks.split(',')]
        if 'all' in check_list:
            check_list = ['permissions', 'display', 'mcp-diagnostics', 'hook']

        results: list[dict[str, Any]] = []
        all_healthy = True

        for check in check_list:
            if check == 'permissions':
                # OpenCode settings file presence and executor permission
                global_path = self.permission_settings_path('global', write=False)
                project_path = self.permission_settings_path('project', write=False)
                g_settings = self.permission_load_settings(global_path)
                p_settings = self.permission_load_settings(project_path)

                def _has_exec(s: dict[str, Any]) -> bool:
                    perm = s.get('permission', {})
                    if not isinstance(perm, dict):
                        return False
                    b = perm.get('bash')
                    if b == 'allow':
                        return True
                    if isinstance(b, dict):
                        return any(
                            k in ('python3 .plan/execute-script.py *', 'python3 .plan/execute-script.py')
                            and v == 'allow'
                            for k, v in b.items()
                        )
                    return False

                has_executor = _has_exec(g_settings) or _has_exec(p_settings)
                has_file = Path(global_path).is_file() or Path(project_path).is_file()
                healthy = has_file and has_executor
                detail = (
                    'OpenCode settings present'
                    + (' with executor permission' if has_executor else ' (missing executor permission)')
                    if has_file
                    else 'OpenCode config not found (checked opencode.json and ~/.config/opencode/opencode.json)'
                )
                results.append(
                    {
                        'check': check,
                        'healthy': healthy,
                        'detail': detail,
                    }
                )
                if not healthy:
                    all_healthy = False

            elif check == 'display':
                # OpenCode has no plugin-driven display hook — always unhealthy
                results.append(
                    {
                        'check': check,
                        'healthy': False,
                        'detail': ('OpenCode has no plugin-driven terminal-title hook (issue anomalyco/opencode#8619)'),
                    }
                )
                all_healthy = False

            elif check == 'mcp-diagnostics':
                # Check for OpenCode MCP server (port 63342 by convention)
                import socket

                try:
                    with socket.create_connection(('127.0.0.1', 63342), timeout=1):
                        healthy = True
                        detail = 'MCP server reachable at 127.0.0.1:63342'
                except OSError:
                    healthy = False
                    detail = 'MCP server not reachable at 127.0.0.1:63342'
                results.append({'check': check, 'healthy': healthy, 'detail': detail})
                if not healthy:
                    all_healthy = False

            elif check == 'hook':
                # No SessionStart hook on OpenCode
                results.append(
                    {
                        'check': check,
                        'healthy': False,
                        'detail': ('SessionStart hook not applicable on OpenCode (issue #9292)'),
                    }
                )
                all_healthy = False

        return toon_success(
            'health-check',
            {
                'checks_run': check_list,
                'all_healthy': all_healthy,
                'results': results,
            },
        )

    def runtime_info(self) -> str:
        """Collect runtime information for the opencode target.

        Reads harness, model, effort, and build-version from
        script-accessible sources via the shared collector; unreadable
        attributes are dropped rather than estimated. Model resolution is
        target-scoped here (never in the shared collector): only
        OpenCode-specific and generic variables are visible, so Claude
        metadata leaking into a shared environment can never be attributed
        to an OpenCode entry.
        """
        import os

        env = {key: value for key, value in os.environ.items() if key in self._OPENCODE_MODEL_ENV}
        info = runtime_info.collect_runtime_info('opencode', env=env)
        return toon_success(runtime_info.RUNTIME_INFO_OPERATION, info)
