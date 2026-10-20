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
  settings. A file in the OpenCode 2 shape is read and written through its
  ordered ``permissions`` list of ``{action, resource, effect}`` rules;
  a file still in the OpenCode 1 shape is read and written through its
  ``permission`` pattern maps, so the operator's file keeps the shape it has.
  configure writes grants, fix ensure/add/remove add and delete them (carrying
  ``allow``/``ask``/``deny`` actions via ``to_opencode_grant``), and fix
  protect-path renders deny entries guarding a named directory in BOTH the
  tilde and the absolute spelling — counts only ever cross back, exactly as on
  the Claude target. The maintenance operations consolidate and normalize
  report a ``success`` no-op, mirroring the Claude target's contract split.
- web-analyze and web-apply are real too: they read and write the ``webfetch``
  permission in whichever shape the settings file carries.
- metrics capture declines on every input, manual count included, returning
  ``no-op`` (no token-persistence boundary is reachable from this target, so a
  success carrying the count would be a silently lost measurement).
- metrics normalized-tokens and chat extract-signal return ``no-op`` with
  ``transcript_not_found`` (no session transcript exists to walk or reduce).
- subagent dispatch succeeds, mapping the ``Task`` tool to OpenCode 2's
  ``subagent``.
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
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
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

#: OpenCode MAJOR whose configuration schema the emitter targets. The health
#: ``version`` check compares the installed binary's major against this, so a
#: future OpenCode major surfaces as a reported mismatch instead of an emit
#: that silently lands in a schema the client no longer reads the same way.
OPENCODE_CONFIG_SCHEMA_MAJOR = 2

DEFAULT_OPENCODE_COMMANDS = OPENCODE_DEFAULT_PERMISSIONS

#: Version of the standing-rules bridge format written by project setup.
STANDING_RULES_BRIDGE_VERSION = 1

#: Baseline source the bridge copies from. CLAUDE.md stays authoritative.
STANDING_RULES_BASELINE = 'CLAUDE.md'

#: Marker embedded in every bridge file so drift detection reads the marker,
#: never rule prose.
STANDING_RULES_BRIDGE_MARKER = f'bridge-version: {STANDING_RULES_BRIDGE_VERSION}'

#: Filename of the bridge-owned standing-rules file. It is deliberately
#: distinct from the installed target rules shipped by
#: ``install.sh --emit-rules``, so a setup write can never land in the
#: installed file.
BRIDGE_RULES_FILENAME = 'plan-marshall-standing-rules.md'

#: Filename of the installed target rules shipped by ``install.sh --emit-rules``.
INSTALLED_RULES_FILENAME = 'plan-marshall-target-rules.md'

#: Pattern matching a bridge stub a previous setup left in the installed
#: target rules. Only the bridge marker spells ``bridge-version`` followed by
#: a colon and a digit; the rule prose carries the bare words, so prose can
#: never false-positive a clobber report.
_BRIDGE_MARKER_PATTERN = re.compile(r'bridge-version\s*:\s*\d')

#: The content hash the bridge records for the baseline it was generated from.
#: Drift is decided by comparing this hash to the CURRENT baseline, never by
#: mtime: a checkout, a rebase or a ``touch`` moves mtime without changing a
#: rule, and a mtime-only verdict would flag drift on every one of them.
_SOURCE_HASH_PATTERN = re.compile(r'^source-sha256:\s*([0-9a-f]{64})$', re.MULTILINE)


def _baseline_text(project_dir: Path) -> str | None:
    """Return the standing-rules baseline's text, or ``None`` when unreadable."""
    try:
        return (project_dir / STANDING_RULES_BASELINE).read_text(encoding='utf-8')
    except OSError:
        return None


def _bridge_body(baseline_text: str | None) -> str:
    """Render the bridge file for *baseline_text*.

    The bridge CARRIES the baseline's rules — it is generated from ``CLAUDE.md``,
    so an OpenCode agent reads them without a second source of truth — and
    records the baseline's SHA-256 so drift is a content comparison. With no
    readable baseline there is nothing to carry and the bridge stays a marker
    plus a pointer, which is still an honest statement of what was bridged.
    """
    if baseline_text is None:
        return (
            f'# Plan Marshall standing rules (OpenCode bridge {STANDING_RULES_BRIDGE_MARKER})\n\n'
            f'Standing rules bridged from {STANDING_RULES_BASELINE} at project setup. '
            'No readable baseline was present, so this file carries no rules yet; '
            're-run setup once the baseline exists.\n'
        )
    digest = hashlib.sha256(baseline_text.encode('utf-8')).hexdigest()
    return (
        f'# Plan Marshall standing rules (OpenCode bridge {STANDING_RULES_BRIDGE_MARKER})\n\n'
        f'source: {STANDING_RULES_BASELINE}\n'
        f'source-sha256: {digest}\n\n'
        f'<!-- Generated from {STANDING_RULES_BASELINE}; edit the baseline, not this file. -->\n\n'
        f'{baseline_text}'
    )


def _write_rules_bridge(project_dir: Path) -> bool:
    """Write the bridge file that carries the baseline's standing rules.

    Returns whether the file was (re)written. The bridge owns its own file; the
    installed target rules shipped by ``install.sh --emit-rules`` are never
    written here, so a setup can no longer replace the full rules with a stub.
    """
    bridge = _bridge_rules_path(project_dir)
    desired = _bridge_body(_baseline_text(project_dir))
    try:
        if bridge.is_file() and bridge.read_text(encoding='utf-8') == desired:
            return False
        bridge.parent.mkdir(parents=True, exist_ok=True)
        bridge.write_text(desired, encoding='utf-8')
        return True
    except OSError:
        return False


def standing_rules_drift_status(project_dir: str) -> dict[str, Any]:
    """Detect drift of the OpenCode standing-rules bridge against its baseline.

    Drift is decided by CONTENT: the ``source-sha256`` the bridge recorded is
    compared with the current baseline's hash. ``baseline_changed`` means the
    rules moved; a mtime change alone is ``in_sync``. A bridge with the marker
    but no recorded hash predates content tracking and is reported as
    ``source_hash_missing`` rather than assumed current.
    """
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
    baseline_text = _baseline_text(proj)
    if baseline_text is None:
        return {'drift': True, 'needs_bridge': False, 'reason': 'baseline_unreadable'}
    recorded = _SOURCE_HASH_PATTERN.search(text)
    if recorded is None:
        return {'drift': True, 'needs_bridge': False, 'reason': 'source_hash_missing'}
    if recorded.group(1) != hashlib.sha256(baseline_text.encode('utf-8')).hexdigest():
        return {'drift': True, 'needs_bridge': False, 'reason': 'baseline_changed'}
    return {'drift': False, 'needs_bridge': False, 'reason': 'in_sync'}


def _rules_dir(project_dir: Path) -> Path:
    """Return the OpenCode workspace rules directory."""
    return project_dir / '.opencode' / 'rules'


def _bridge_rules_path(project_dir: Path) -> Path:
    """Return the OpenCode workspace rules-bridge file path."""
    return _rules_dir(project_dir) / BRIDGE_RULES_FILENAME


def _installed_rules_path(project_dir: Path) -> Path:
    """Return the installed target-rules file path shipped by ``install.sh``."""
    return _rules_dir(project_dir) / INSTALLED_RULES_FILENAME


def installed_rules_clobbered(project_dir: Path) -> bool:
    """Report whether a previous setup left its bridge stub in the installed rules.

    Read-only: the installed target rules belong to the ``install.sh`` emit
    path (``--workspace`` / ``--emit-rules``), so this never writes. A file
    carrying the bridge marker is a clobbered install and is restored with that
    emit command. Non-UTF-8 bytes are decoded with replacement, so a malformed
    file is judged rather than raised on.
    """
    try:
        text = _installed_rules_path(project_dir).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False
    return _BRIDGE_MARKER_PATTERN.search(text) is not None


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

    if perm in (
        'read',
        'edit',
        'glob',
        'grep',
        'bash',
        'webfetch',
        'websearch',
        'question',
        'task',
        'subagent',
        'skill',
    ):
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


# ----------------------------------------------------------------------
# OpenCode 2 permission-rule accessors
# ----------------------------------------------------------------------
#
# OpenCode 2 stores permissions as an ordered ``permissions`` list of
# ``{action, resource, effect}`` rules evaluated last-match-wins, with no match
# meaning ``ask``. The OpenCode 1 ``permission`` map is still READ so an
# operator's existing file is not rewritten behind their back, but nothing is
# ever written into a map beside a list: the normalizer concatenates the map
# BEFORE the list, so a rule added there is overridden by the list's catch-all.
#
# ``to_opencode_grant`` keeps its internal ``bash`` category; the OpenCode 2
# action for that category is ``shell``. Keeping the rename in ONE place means
# the legacy map path and the list path cannot disagree about which tool a
# grant names.

#: Internal grant category -> OpenCode 2 rule action. ``bash`` is the shell
#: rename; ``task`` is the OpenCode 1 name a caller may still hand us, and it is
#: normalized to the OpenCode 2 tool on WRITE so the list never carries an
#: action no OpenCode 2 tool matches. Every other category is already the tool.
_CATEGORY_TO_ACTION = {'bash': 'shell', 'task': 'subagent'}


def _permission_action(category: str) -> str:
    """Return the OpenCode 2 rule action for an internal grant category."""
    return _CATEGORY_TO_ACTION.get(category, category)


def _permission_rules(settings: dict[str, Any], *, create: bool = False) -> list[Any] | None:
    """Return the ``permissions`` list when the settings carry one, else ``None``.

    ``None`` means the file carries the OpenCode 1 ``permission`` map, which
    callers keep writing in place rather than converting behind the operator's
    back. A file carrying NEITHER shape has nothing to preserve, so a writer
    passes ``create=True`` and gets a fresh list: a config that only names its
    schema must not gain the OpenCode 1 map from a producer. Readers leave
    ``create`` off, so an empty config reports no shape instead of being
    silently given one.
    """
    rules = settings.get('permissions')
    if isinstance(rules, list):
        return rules
    if 'permission' in settings:
        return None
    if create:
        created: list[Any] = []
        settings['permissions'] = created
        return created
    return None


def _resource_matches(pattern: Any, resource: str) -> bool:
    """Match a rule's ``resource`` glob against a concrete resource."""
    text = pattern if isinstance(pattern, str) else ''
    regex = '^' + re.escape(text).replace(r'\*', '.*') + '$'
    return re.match(regex, resource, re.S) is not None


def _rule_effect(rule: dict[str, Any]) -> str:
    return str(rule.get('effect', '')).strip().lower()


def _matching_rules(rules: list[Any], action: str, resource: str) -> list[dict[str, Any]]:
    return [
        rule
        for rule in rules
        if isinstance(rule, dict) and rule.get('action') == action and _resource_matches(rule.get('resource'), resource)
    ]


def _effective_rule_effect(rules: list[Any], action: str, resource: str) -> str | None:
    """Evaluate *action*/*resource* the way OpenCode 2 does: last match wins."""
    hits = _matching_rules(rules, action, resource)
    return _rule_effect(hits[-1]) if hits else None


def _rule_exists(rules: list[Any], action: str, resource: str, effect: str) -> bool:
    """True when an exact (action, resource, effect) rule is already present."""
    return any(
        isinstance(rule, dict)
        and rule.get('action') == action
        and rule.get('resource') == resource
        and _rule_effect(rule) == effect
        for rule in rules
    )


def _upsert_permission_rule(rules: list[Any], action: str, resource: str, effect: str) -> bool:
    """Add or update one rule in an OpenCode 2 ``permissions`` list.

    An exact ``(action, resource)`` rule is updated in place. A new specific
    rule is inserted AFTER that action's catch-all (``resource == "*"``), so
    last-match-wins lets the specific rule override it. A new catch-all is
    inserted at the FRONT, where it cannot override anything. Returns whether
    anything changed.
    """
    for rule in rules:
        if isinstance(rule, dict) and rule.get('action') == action and rule.get('resource') == resource:
            if _rule_effect(rule) == effect:
                return False
            rule['effect'] = effect
            return True

    new_rule = {'action': action, 'resource': resource, 'effect': effect}
    if resource == '*':
        rules.insert(0, new_rule)
        return True

    insert_at = 0
    for index, rule in enumerate(rules):
        if isinstance(rule, dict) and rule.get('action') == action and rule.get('resource') == '*':
            insert_at = index + 1
    rules.insert(insert_at, new_rule)
    return True


def _remove_permission_rule(rules: list[Any], action: str, resource: str) -> bool:
    """Remove the exact ``(action, resource)`` rule; returns whether one was removed."""
    for index, rule in enumerate(list(rules)):
        if isinstance(rule, dict) and rule.get('action') == action and rule.get('resource') == resource:
            del rules[index]
            return True
    return False


def installed_opencode_version() -> tuple[int | None, str]:
    """Read the installed OpenCode version and return ``(major, raw)``.

    ``major`` is ``None`` when the version cannot be checked — an absent
    binary, a failed invocation, or unparseable output — and the second
    element then explains why. A caller must never read ``None`` as "ok":
    not-checkable is its own state, and reporting it as healthy would tell an
    operator the emitted schema was verified when nothing was read.
    """
    executable = shutil.which('opencode')
    if not executable:
        return None, 'opencode executable not found on PATH'
    try:
        completed = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f'opencode --version failed: {exc}'
    output = (completed.stdout or completed.stderr or '').strip()
    match = re.search(r'(\d+)\.\d+', output)
    if match is None:
        return None, f'unparseable opencode version output: {output!r}'
    return int(match.group(1)), output


def _opencode2_skeleton() -> dict[str, Any]:
    """Return a fresh OpenCode 2 ``opencode.json`` skeleton.

    The shell catch-all comes FIRST because OpenCode 2 evaluates the list
    last-match-wins: the executor and build-wrapper allows follow it, so they
    override it while everything else keeps the ``ask`` default the client
    would apply anyway. No ``permission`` map is written — the normalizer
    concatenates that map ahead of the list, which is what turned written
    deny rules into dead letters in the OpenCode 1 shape.
    """
    rules: list[dict[str, str]] = [{'action': 'shell', 'resource': '*', 'effect': 'ask'}]
    rules.extend({'action': 'shell', 'resource': cmd, 'effect': 'allow'} for cmd in OPENCODE_DEFAULT_PERMISSIONS)
    return {'$schema': 'https://opencode.ai/config.json', 'permissions': rules}


def _deny_rules(settings: dict[str, Any]) -> list[dict[str, str]]:
    """Return the settings' deny rules as ``{action, resource, effect}`` objects.

    Reads the OpenCode 2 list when present and the OpenCode 1 map otherwise, so
    the analysis surface reports the same rule set whichever shape the file has.
    """
    rules = _permission_rules(settings)
    if rules is not None:
        return [
            {'action': str(rule.get('action', '')), 'resource': str(rule.get('resource', '')), 'effect': 'deny'}
            for rule in rules
            if isinstance(rule, dict) and _rule_effect(rule) == 'deny'
        ]

    denies: list[dict[str, str]] = []
    perm = settings.get('permission')
    if not isinstance(perm, dict):
        return denies
    for tool, value in perm.items():
        if isinstance(value, dict):
            for pattern, action in value.items():
                if str(action).lower() == 'deny':
                    denies.append({'action': str(tool), 'resource': str(pattern), 'effect': 'deny'})
        elif isinstance(value, str) and value.lower() == 'deny':
            denies.append({'action': str(tool), 'resource': '*', 'effect': 'deny'})
    return denies


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


#: Candidate columns carrying a ``permission`` row's owning project id.
_PERMISSION_PROJECT_COLUMNS = ('project_id', 'project')

#: Candidate id columns on the ``project`` table.
_PROJECT_ID_COLUMNS = ('id', 'project_id')

#: Candidate worktree-path columns on the ``project`` table.
_PROJECT_PATH_COLUMNS = ('worktree', 'worktree_path', 'directory', 'path', 'worktree_dir', 'project_path', 'root')


def _normalize_fs_path(value: str) -> str:
    """Normalize a filesystem path for equality comparison (absolute, no trailing slash)."""
    expanded = Path(value).expanduser()
    try:
        return expanded.resolve().as_posix().rstrip('/')
    except OSError:
        return expanded.as_posix().rstrip('/')


def _resolve_project_id(conn: sqlite3.Connection, project_dir: str | None) -> tuple[bool, str | None]:
    """Resolve the project id whose worktree path matches *project_dir*.

    Returns ``(project_table_present, project_id)``. The first element is True
    whenever a ``project`` table EXISTS — even one lacking a usable id or path
    column — so the caller fails CLOSED rather than reading permission rows it
    cannot scope to the requested worktree. ``(False, None)`` only when there is
    no ``project`` table at all: the fixture shape, which is read unscoped.
    """
    try:
        info = conn.execute('PRAGMA table_info("project")').fetchall()
    except sqlite3.Error:
        return False, None
    if not info:
        return False, None
    columns = [str(col[1]) for col in info]
    id_col = _column_lookup(columns, _PROJECT_ID_COLUMNS)
    path_col = _column_lookup(columns, _PROJECT_PATH_COLUMNS)
    if id_col is None or path_col is None:
        return True, None
    if not project_dir:
        return True, None
    target = _normalize_fs_path(project_dir)
    try:
        for row_id, row_path in conn.execute(f'SELECT "{id_col}", "{path_col}" FROM "project"'):
            if isinstance(row_path, str) and _normalize_fs_path(row_path) == target:
                return True, str(row_id)
    except sqlite3.Error:
        return True, None
    return True, None


def _list_persisted_allow_rows(
    conn: sqlite3.Connection, project_dir: str | None = None
) -> tuple[list[dict[str, Any]], str]:
    """List persisted allow rows from every permission-like table, read-only.

    Returns ``(rows, state)`` where ``state`` is one of:

    * ``'recognised'`` — a permission-shaped table was read;
    * ``'project_unresolved'`` — a ``project`` table exists but no row's worktree
      path matches *project_dir*, so rows CANNOT be scoped to this project and the
      read fails closed (the caller reports ``checkable: false``) rather than
      comparing another project's approvals against this project's denies;
    * ``'schema_unrecognised'`` — no table carried the permission shape.

    A permission table is recognised when it carries a pattern-like column plus
    EITHER a decision-like column (the declared shape) OR a ``tool``/``action``
    column (the LIVE shape, in which every row is a persisted allow because the
    table has no decision column).

    Only ``SELECT`` statements run here; this helper never writes. A database with
    no ``project`` table is read unscoped so fixture shapes keep working. A
    decision column named ``action`` is only honored alongside an explicit
    ``tool`` column, so a list-shape ``(action, resource)`` table is not misread
    as ``(tool, decision)``. The table-list query error propagates so the caller
    maps an unreadable database to checkable False / db_unreadable.
    """
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    prioritized = sorted(tables, key=lambda name: 0 if name.lower() in ('permission', 'permissions') else 1)
    project_present, project_id = _resolve_project_id(conn, project_dir)
    if project_present and project_id is None:
        return [], 'project_unresolved'
    rows: list[dict[str, Any]] = []
    recognised = False
    for table in prioritized:
        try:
            info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        except sqlite3.Error:
            continue
        columns = [str(col[1]) for col in info]
        pattern_col = _column_lookup(columns, _PATTERN_COLUMNS)
        if pattern_col is None:
            continue
        tool_col = _column_lookup(columns, (*_TOOL_COLUMNS, 'action'))
        decision_col = _column_lookup(columns, _DECISION_COLUMNS)
        if decision_col is None and tool_col is not None:
            maybe_action = _column_lookup(columns, ('action',))
            if maybe_action is not None and maybe_action.lower() != tool_col.lower():
                decision_col = maybe_action
        # The LIVE permission shape: a ``tool``/``action`` column with NO decision
        # column — every row is a persisted allow.
        live_shape = decision_col is None and tool_col is not None
        if decision_col is None and not live_shape:
            continue
        recognised = True
        table_project_col = _column_lookup(columns, _PERMISSION_PROJECT_COLUMNS)
        select_cols = f'rowid, "{tool_col}"' if tool_col else 'rowid, NULL'
        select_cols += f', "{pattern_col}"'
        select_cols += f', "{decision_col}"' if decision_col else ', NULL'
        where = ''
        params: tuple[Any, ...] = ()
        if project_id is not None and table_project_col is not None:
            where = f' WHERE "{table_project_col}" = ?'
            params = (project_id,)
        try:
            for rowid, tool, pattern, decision in conn.execute(f'SELECT {select_cols} FROM "{table}"{where}', params):
                if not isinstance(pattern, str) or not pattern.strip():
                    continue
                allowed = live_shape or str(decision).strip().lower() in _PERSISTED_ALLOW_VALUES
                if not allowed:
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
    return rows, 'recognised' if recognised else 'schema_unrecognised'


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
        }
    )

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup for OpenCode.

        Creates ``.plan/``, writes the standing-rules bridge to its own
        bridge file, and reports bridge drift against the CLAUDE.md
        baseline on re-setup. Shared ``marshal.json`` carries no
        runtime-owned keys: routing stays config-driven via the registry.
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
        # The verdict is taken BEFORE the heal: a setup that rewrites the
        # bridge has just found it drifted, and reporting the post-write
        # ``in_sync`` would tell the operator nothing needed attention.
        drift = standing_rules_drift_status(str(resolved))
        bridge_written = _write_rules_bridge(resolved)

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
                'marshal_written': False,
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
        rules = _permission_rules(settings, create=True)
        if rules is not None:
            added = 0
            for g in grants:
                rule = g.get('rule') or g.get('command') or str(g)
                cat, pat, act = to_opencode_grant(str(rule))
                if _upsert_permission_rule(rules, _permission_action(cat), pat, act):
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
                    'permission_shape': 'permissions',
                },
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
            rules = _permission_rules(settings)
            executor_patterns = ('python3 .plan/execute-script.py *', 'python3 .plan/execute-script.py')

            if rules is not None:
                has_executor = any(
                    _effective_rule_effect(rules, 'shell', pattern) == 'allow' for pattern in executor_patterns
                )
                missing_defaults = [
                    default
                    for default in OPENCODE_DEFAULT_PERMISSIONS
                    if _effective_rule_effect(rules, 'shell', default) != 'allow'
                ]
                shape = 'permissions'
            else:
                perm = settings.get('permission', {})
                bash_map = perm.get('bash', {}) if isinstance(perm, dict) else {}
                has_executor = False
                if isinstance(bash_map, dict):
                    has_executor = any(key in executor_patterns and value == 'allow' for key, value in bash_map.items())
                elif bash_map == 'allow':
                    has_executor = True

                missing_defaults = []
                if isinstance(bash_map, dict):
                    missing_defaults = [
                        default for default in OPENCODE_DEFAULT_PERMISSIONS if bash_map.get(default) != 'allow'
                    ]
                shape = 'permission' if isinstance(perm, dict) and perm else 'none'

            results[sc] = {
                'settings_path': spath,
                'permission_shape': shape,
                'has_executor': has_executor,
                'missing_defaults': missing_defaults,
                'deny_rules': _deny_rules(settings),
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
        rules = _permission_rules(settings, create=True)

        if rules is not None and operation in ('ensure', 'add'):
            added = 0
            for item in arguments:
                cat, pat, act = to_opencode_grant(str(item))
                action = _permission_action(cat)
                if dry_run:
                    if not _rule_exists(rules, action, pat, act):
                        added += 1
                elif _upsert_permission_rule(rules, action, pat, act):
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
                    'permission_shape': 'permissions',
                },
            )

        if rules is not None and operation == 'remove':
            removed = 0
            for item in arguments:
                cat, pat, _ = to_opencode_grant(str(item))
                action = _permission_action(cat)
                if dry_run:
                    if any(
                        isinstance(rule, dict) and rule.get('action') == action and rule.get('resource') == pat
                        for rule in rules
                    ):
                        removed += 1
                elif _remove_permission_rule(rules, action, pat):
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
                    'permission_shape': 'permissions',
                },
            )

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
        native OpenCode permission rules and never cross back — counts
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
        rules = _permission_rules(settings, create=True)
        if rules is not None:
            for tool, tool_entries in rendered.items():
                action = _permission_action(tool)
                for pattern, effect in tool_entries.items():
                    if _rule_exists(rules, action, pattern, effect):
                        continue
                    if dry_run:
                        proposed_count += 1
                    elif _upsert_permission_rule(rules, action, pattern, effect):
                        changes_applied += 1
        else:
            perm = settings.setdefault('permission', {})
            if not isinstance(perm, dict):
                perm = {}
                settings['permission'] = perm

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
        rules = _permission_rules(settings)
        if rules is not None:
            webfetch = _effective_rule_effect(rules, 'webfetch', '*')
        else:
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
        rules = _permission_rules(settings, create=True)
        changed = False
        if rules is not None:
            current = _effective_rule_effect(rules, 'webfetch', '*')
            if add and current != 'allow':
                if not dry_run:
                    _upsert_permission_rule(rules, 'webfetch', '*', 'allow')
                changed = True
            elif remove and current == 'allow':
                if not dry_run:
                    _remove_permission_rule(rules, 'webfetch', '*')
                changed = True
        else:
            perm = settings.setdefault('permission', {})
            if not isinstance(perm, dict):
                perm = {}
                settings['permission'] = perm

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
        ``agent``/``agents`` scoped. The LIVE ``permission(id, project_id,
        action, resource, time_created, time_updated)`` table carries NO decision
        column, so every row is a persisted allow; such rows are scoped to the
        project by ``project_id``, resolved from the ``project`` table's worktree
        path. When no table carries the permission shape the schema is
        unrecognised and the result is ``checkable: false``
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
            allow_rows, state = _list_persisted_allow_rows(conn, project_dir)
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
        if state != 'recognised':
            return toon_success(
                PERSISTED_CONTRADICTION_OPERATION,
                {
                    'checkable': False,
                    'reason': state,
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
                skeleton = _opencode2_skeleton()
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
                skeleton = _opencode2_skeleton()
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
        """Ensure default Plan Marshall executor permissions exist in OpenCode settings.

        A file in the OpenCode 2 shape gains ``allow`` rules inside its
        ``permissions`` list, after the catch-all, and never a ``permission``
        map beside it — the normalizer would concatenate that map ahead of the
        list, where the list's catch-all overrides it.
        """
        if 'error' in settings:
            return {
                'defaults_added': [],
                'defaults_added_count': 0,
                'defaults_removed': [],
                'defaults_removed_count': 0,
                'applied': False,
                'error': settings['error'],
            }

        rules = _permission_rules(settings, create=True)
        if rules is not None:
            list_added: list[str] = []
            for cmd in OPENCODE_DEFAULT_PERMISSIONS:
                if _effective_rule_effect(rules, 'shell', cmd) == 'allow':
                    continue
                list_added.append(cmd)
                if not dry_run:
                    _upsert_permission_rule(rules, 'shell', cmd, 'allow')

            saved = False
            if list_added and not dry_run:
                saved = self.permission_save_settings(settings_path, settings)

            return {
                'defaults_added': list_added,
                'defaults_added_count': len(list_added),
                'defaults_removed': [],
                'defaults_removed_count': 0,
                'applied': bool(list_added and not dry_run and saved),
                'permission_shape': 'permissions',
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
        """Return OpenCode 2 subagent invocation parameters.

        Uses ``subagent`` as the OpenCode 2 native tool name, and echoes the
        REQUESTED *agent* back under the tool's own ``agent`` parameter so the
        caller's selection reaches the invocation instead of being discarded.
        OpenCode 2's sub-agent tool takes ``{agent, description, prompt}``;
        OpenCode 1's ``task``/``subagent_type`` pair is not emitted.

        Verify-first clause 1: the ``subagent``-tool dispatch fires only when the
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
                    'tool': 'subagent',
                    'agent': agent,
                    # ``prompt`` is NOT the last field: a block scalar that ends
                    # the document loses its final newline to the document
                    # terminator, and the prompt must cross the TOON boundary
                    # byte-identical. ``description`` is single-line, so it is
                    # safe in the trailing position.
                    'prompt': BlockScalar(prompt_body),
                    'description': f'Run {agent}',
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

        The ``display`` and ``hook`` checks always report unhealthy because
        OpenCode exposes no hook channel. ``version`` compares the installed
        major with the schema major the emitter targets and reports a mismatch
        — or *not checkable* for an absent or unreadable binary — never ok.
        """
        check_list = [c.strip() for c in checks.split(',')]
        if 'all' in check_list:
            check_list = ['permissions', 'version', 'display', 'mcp-diagnostics', 'hook']

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
                    rules = _permission_rules(s)
                    if rules is not None:
                        return any(
                            _effective_rule_effect(rules, 'shell', pattern) == 'allow'
                            for pattern in ('python3 .plan/execute-script.py *', 'python3 .plan/execute-script.py')
                        )
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

            elif check == 'version':
                major, raw = installed_opencode_version()
                if major is None:
                    healthy = False
                    detail = f'not checkable: {raw}'
                elif major != OPENCODE_CONFIG_SCHEMA_MAJOR:
                    healthy = False
                    detail = (
                        f'version mismatch: installed OpenCode {raw} is major {major}; '
                        f'the emitted configuration targets major {OPENCODE_CONFIG_SCHEMA_MAJOR}'
                    )
                else:
                    healthy = True
                    detail = f'installed OpenCode {raw} matches the emitted schema major {OPENCODE_CONFIG_SCHEMA_MAJOR}'
                results.append({'check': check, 'healthy': healthy, 'detail': detail})
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

    def runtime_info(self, model: str | None = None, effort: str | None = None) -> str:
        """Collect runtime information for the opencode target.

        Reads harness, model, effort, the harness source, and the bundle/executor
        version from
        script-accessible sources via the shared collector; unreadable
        attributes are dropped rather than estimated. Model resolution is
        target-scoped here (never in the shared collector): only
        OpenCode-specific and generic variables are visible, so Claude
        metadata leaking into a shared environment can never be attributed
        to an OpenCode entry.

        The model is MEASURED, not self-reported: the collector reads the
        plan's session tree (root resolved through ``parent_id``, plus every
        descendant) from ``opencode.db`` and records it as ``measured``. The
        self-reported *model* is therefore not forwarded — the database is
        authoritative — while *effort* is.

        Args:
            model: Self-reported model identifier; superseded by the measured
                session value on this target.
            effort: Self-reported effort level, tagged ``self_reported``.
        """
        import os

        env = {key: value for key, value in os.environ.items() if key in self._OPENCODE_MODEL_ENV}
        info = runtime_info.collect_runtime_info(
            'opencode',
            env=env,
            effort=effort,
            opencode_db_path=_default_opencode_db_path(),
            opencode_session_id=os.environ.get(runtime_info.OPENCODE_SESSION_ID_ENV),
        )
        return toon_success(runtime_info.RUNTIME_INFO_OPERATION, info)
