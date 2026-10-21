# SPDX-License-Identifier: FSL-1.1-ALv2
"""Execute the OpenCode guard plugin under node, as a behavioural contract.

The guard plugin (``.opencode/plugin/guard.js``) is a real ES module loaded by the
OpenCode host, so a test that greps its source pins text, not behaviour. This
helper runs the plugin's registered ``execute.before`` hook under ``node`` against
a scratch project root, so a decision-table change is exercised rather than
read.

The scratch root is a self-contained ESM project:

* ``package.json`` marks the tree as ``"type": "module"`` so the copied ``.js``
  plugin loads as an ES module.
* ``node_modules/@opencode/plugin/index.js`` stubs the host package the plugin
  imports, exporting ``Plugin.define`` as the identity so the plugin's exported
  spec (``{ id, setup }``) is returned whole.
* a copy of the REAL ``.opencode/plugin/guard.js`` (read at test time, so an edit
  to the plugin under test is picked up) and of the REAL shared allow-list data
  file, so the guard resolves the same allow-list content a live install would.
* ``driver.mjs`` registers the hook through ``setup`` and invokes it once per
  supplied event, reporting ``blocked`` + the thrown message.

The scratch root is deliberately NOT under ``.plan/local/worktrees/``, so a test
that wants to exercise a worktree-shaped path passes it as the shell ``workdir``.
R5 binds when the plan-context gate fires OR the project root carries the
repository marker (this scratch root does), so the guard refuses an interpreter
bypass in a root session here; R6 resolves the plan MAIN-ANCHORED, and the
harness pins ``PLAN_BASE_DIR`` to ``<scratch>/.plan/local`` so a test can place
the plan's ``status.json`` where that resolution looks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: This file lives at ``test/plan-marshall/platform-runtime/``; the test tree
#: root is two levels up and the repository root one above that.
TEST_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = TEST_ROOT.parent

#: Bundle-qualified sub-agent identity carrying the ``execution-context`` marker
#: (Signal 1), as the OpenCode host passes it on a dispatched sub-agent call.
SUB_AGENT_AGENT = 'plan-marshall:execution-context-level-4'

#: A working directory resolving under the plan-worktree path segment (Signal 2).
WORKTREE_WORKDIR = '/home/dev/project/.plan/local/worktrees/plan-a'

#: The shared allow-list data file both harnesses read.
_ALLOWLIST_REL = Path('marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json')

#: The shared wrapper table data file both harnesses read (the allow-list's
#: sibling). The scratch root must carry BOTH, or the guard fails closed.
_WRAPPER_TABLE_REL = Path('marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-wrappers.json')


def guard_plugin_path() -> Path:
    """Return the path to the real ``.opencode/plugin/guard.js`` under test."""
    for parent in (REPO_ROOT, *REPO_ROOT.parents):
        candidate = parent / '.opencode' / 'plugin' / 'guard.js'
        if candidate.is_file():
            return candidate
    raise AssertionError('could not locate .opencode/plugin/guard.js above the test tree')


def guard_allowlist_path() -> Path:
    """Return the path to the shared R5 allow-list data file."""
    return REPO_ROOT / _ALLOWLIST_REL


def wrapper_table_path() -> Path:
    """Return the path to the shared R5 wrapper table data file."""
    return REPO_ROOT / _WRAPPER_TABLE_REL


def wrapper_table() -> dict[str, Any]:
    """Return the parsed shared wrapper table (empty dict when the file is absent)."""
    path = wrapper_table_path()
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    return data if isinstance(data, dict) else {}


def allowlist_entries() -> list[str]:
    """Return the entry keys of the real shared allow-list (empty when absent)."""
    path = guard_allowlist_path()
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    entries = data.get('entries')
    if isinstance(entries, dict):
        return [str(key) for key in entries]
    if isinstance(entries, list):
        return [str(entry) for entry in entries]
    return []


def allowlist_bundle_entries() -> dict[str, str]:
    """Return the BUNDLE-RELATIVE entries of the real shared allow-list."""
    path = guard_allowlist_path()
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    entries = data.get('bundle_entries')
    if isinstance(entries, dict):
        return {str(key): str(value) for key, value in entries.items()}
    return {}


def require_node() -> str:
    """Return the ``node`` executable, or fail loudly when it is unavailable.

    The enforcement tests EXECUTE the plugin, so a missing interpreter is a
    broken environment, not an inapplicable one: skipping would quietly shrink
    coverage of the decision table this suite exists to pin. The CI runner image
    preinstalls Node.js (GitHub ``ubuntu-24.04`` "Language and Runtime"), so the
    failure names that and asks for a local install rather than degrading.
    """
    node = shutil.which('node')
    if node is None:
        raise AssertionError(
            'node is required to execute .opencode/plugin/guard.js in the enforcement '
            'suite; the CI runner image preinstalls Node.js (GitHub ubuntu-24.04 '
            "'Language and Runtime'). Install node locally to run these tests."
        )
    return node


@dataclass(frozen=True)
class GuardOutcome:
    """One hook invocation's verdict: whether it threw, and the thrown message."""

    blocked: bool
    message: str


_DRIVER = """\
import { readFileSync } from "node:fs"
import { pathToFileURL } from "node:url"

const input = JSON.parse(readFileSync(0, "utf8"))
const loaded = await import(pathToFileURL(input.guardPath).href)
const guard = loaded.default

let handler = null
const ctx = {
  location: { directory: input.root },
  tool: {
    hook: async (name, fn) => {
      if (name === "execute.before") handler = fn
    },
  },
}
await guard.setup(ctx)

const results = []
for (const event of input.events) {
  try {
    await handler(event)
    results.push({ blocked: false, message: "" })
  } catch (error) {
    results.push({ blocked: true, message: String((error && error.message) || error) })
  }
}
process.stdout.write(JSON.stringify(results))
"""


class GuardHarness:
    """Runs the guard plugin against one scratch project root."""

    def __init__(self, root: Path, plan_base: Path, extra_env: dict[str, str] | None = None) -> None:
        self.root = root
        self.guard_path = root / 'guard.js'
        #: The ``.plan/local`` base the guard's R6 main-anchored plan resolution
        #: anchors on (passed as ``PLAN_BASE_DIR``), mirroring the sanctioned
        #: resolver's override precedence.
        self.plan_base = plan_base
        #: Extra environment for the node child — used to point ``HOME`` /
        #: ``OPENCODE_CONFIG_DIR`` at a fixture deployed tree so the guard's
        #: deployed bundle-relative admission can be exercised.
        self.extra_env = extra_env or {}

    def run(self, events: list[dict[str, Any]]) -> list[GuardOutcome]:
        """Invoke the registered hook once per event; return one outcome each."""
        node = require_node()
        payload = json.dumps({'root': str(self.root), 'guardPath': str(self.guard_path), 'events': events})
        env = {**os.environ, 'PLAN_BASE_DIR': str(self.plan_base), **self.extra_env}
        proc = subprocess.run(
            [node, str(self.root / 'driver.mjs')],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f'node guard driver failed (rc={proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}'
            )
        decoded = json.loads(proc.stdout)
        return [GuardOutcome(bool(item['blocked']), str(item['message'])) for item in decoded]

    def blocks(self, event: dict[str, Any]) -> tuple[bool, str]:
        """Convenience: run one event and return ``(blocked, message)``."""
        outcome = self.run([event])[0]
        return outcome.blocked, outcome.message


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _outside_any_worktree(scratch: Path) -> Path:
    """Return ``scratch`` unless it sits inside a plan worktree.

    A guard root under ``.plan/local/worktrees/`` looks like a plan worktree, and
    pytest's basetemp lives INSIDE the runbook lane's worktree, so a
    ``tmp_path_factory`` directory would make the scratch root look worktree-ish
    and couple every case to that shape. In that case a system temp directory is
    used instead; the guard reads the allow-list from a scratch location either
    way, so the relocation changes nothing else.
    """
    normalized = scratch.resolve().as_posix() + '/'
    if '/.plan/local/worktrees/' in normalized:
        return Path(tempfile.mkdtemp(prefix='guard-node-'))
    return scratch


def build_harness(
    scratch: Path,
    *,
    entries: list[str] | None = None,
    include_allowlist: bool = True,
    extra_env: dict[str, str] | None = None,
) -> GuardHarness:
    """Materialise a scratch ESM project around a copy of the real plugin.

    Args:
        scratch: The scratch directory to build into (a pytest ``tmp_path``).
            Relocated to a system temp directory when it resolves inside a plan
            worktree — see :func:`_outside_any_worktree`.
        entries: Allow-list entry keys to write. Defaults to the REAL shared
            allow-list's entries, so the guard resolves live content.
        include_allowlist: When False, no allow-list file is written, so the
            guard falls back to its built-in base table (the absent-file path)
            and the scratch root carries no repository marker (R5 does not bind
            out of a plan context).
        extra_env: Extra environment for the node child (e.g. ``HOME`` or
            ``OPENCODE_CONFIG_DIR`` pointing at a fixture deployed tree).
    """
    scratch = _outside_any_worktree(scratch)
    _write(scratch / 'package.json', json.dumps({'type': 'module'}))
    plugin_dir = scratch / 'node_modules' / '@opencode' / 'plugin'
    _write(
        plugin_dir / 'package.json',
        json.dumps({'name': '@opencode/plugin', 'version': '0.0.0', 'type': 'module', 'main': 'index.js'}),
    )
    _write(plugin_dir / 'index.js', 'export const Plugin = { define: (spec) => spec }\n')
    shutil.copyfile(guard_plugin_path(), scratch / 'guard.js')
    _write(scratch / 'driver.mjs', _DRIVER)
    # The wrapper table is a SIBLING of the allow-list and is read from the same
    # candidate list, so a scratch root that carries one must carry the other —
    # otherwise the guard fails CLOSED on every interpreter call.
    _write(scratch / _WRAPPER_TABLE_REL, json.dumps(wrapper_table()))
    if include_allowlist:
        resolved = allowlist_entries() if entries is None else entries
        bundle_entries = allowlist_bundle_entries()
        target = scratch / _ALLOWLIST_REL
        _write(
            target,
            json.dumps(
                {
                    'schema': 'r5-allowlist/1',
                    'entries': dict.fromkeys(resolved, 'test'),
                    'bundle_entries': bundle_entries,
                }
            ),
        )
    plan_base = scratch / '.plan' / 'local'
    plan_base.mkdir(parents=True, exist_ok=True)
    return GuardHarness(scratch, plan_base, extra_env)


def shell_event(
    command: str,
    *,
    agent: str | None = None,
    workdir: str | None = None,
    session_id: str = 'sess-0001',
    call_id: str = 'call-0001',
    tool: str = 'shell',
) -> dict[str, Any]:
    """Build an OpenCode ``execute.before`` event for a shell invocation.

    ``agent`` and the shell ``workdir`` are the two plan-context signals the
    guard reads; omitting both leaves the gate off, exactly as a call outside a
    plan context would.
    """
    tool_input: dict[str, Any] = {'command': command}
    if workdir is not None:
        tool_input['workdir'] = workdir
    event: dict[str, Any] = {'tool': tool, 'sessionID': session_id, 'id': call_id, 'input': tool_input}
    if agent is not None:
        event['agent'] = agent
    return event


def edit_event(
    file_path: str,
    *,
    agent: str | None = None,
    workdir: str | None = None,
    session_id: str = 'sess-0001',
    call_id: str = 'call-0001',
    tool: str = 'edit',
) -> dict[str, Any]:
    """Build an OpenCode ``execute.before`` event for an edit/write invocation."""
    tool_input: dict[str, Any] = {'filePath': file_path}
    if workdir is not None:
        tool_input['workdir'] = workdir
    event: dict[str, Any] = {'tool': tool, 'sessionID': session_id, 'id': call_id, 'input': tool_input}
    if agent is not None:
        event['agent'] = agent
    return event
