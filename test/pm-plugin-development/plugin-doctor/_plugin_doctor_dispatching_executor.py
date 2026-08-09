#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The one synthetic dispatching ``execute-script.py`` the plugin-doctor tests probe.

Every plugin-doctor cluster that consumes a help-derived accept-set
(``_analyze_argument_naming``, ``_analyze_manage_invocation``) reads the
executor TWO ways, and a fixture that serves only the first turns every
finding-expecting test into a vacuous pass:

- ``load_registered_notations`` regex-parses the ``SCRIPTS = { ... }`` literal,
  so the dict keeps its one-quoted-notation-per-line shape;
- the shared ``argparse_surface`` derivation runs each script's own ``--help``
  THROUGH this executor, so it must actually DISPATCH rather than stand in as a
  lookup stub. A lookup-only stub satisfies the first read and silently empties
  the second, leaving the cluster with no accept-set and no findings to assert.

Resolution mirrors the real executor: ``bundle:skill:script`` maps to
``{root}/marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py``,
computed at DISPATCH time rather than baked in at write time. That ordering
matters — several callers write the executor BEFORE the script it will dispatch
to, so a path resolved eagerly would point at a file that does not exist yet.

Dispatch is in-process via ``runpy.run_path`` under redirected streams: the
derivation already spawns this executor as a subprocess, and an inner spawn
would double the interpreter cold-start of every probe.

This module is the single definition on purpose. Two near-identical copies
previously lived in ``test_analyze.py`` and
``test_analyze_argument_naming_workflow_scope.py``, differing only in one local
binding; a later fix to dispatch semantics in one copy would have left the other
cluster probing a materially different executor while both suites still passed.
"""

from __future__ import annotations

from pathlib import Path

_PREAMBLE: tuple[str, ...] = (
    '#!/usr/bin/env python3',
    'import contextlib',
    'import io',
    'import runpy',
    'import sys',
    'from pathlib import Path',
    '',
    'SCRIPTS = {',
)

_BODY: tuple[str, ...] = (
    '}',
    '',
    '',
    'def _resolve(notation):',
    '    parts = notation.split(":", 2)',
    '    if len(parts) != 3:',
    '        return None',
    '    bundle, skill, script = parts',
    '    root = Path(__file__).parent.parent',
    '    candidate = (',
    '        root / "marketplace" / "bundles" / bundle / "skills" / skill',
    '        / "scripts" / (script + ".py")',
    '    )',
    '    return candidate if candidate.is_file() else None',
    '',
    '',
    'def main():',
    '    if len(sys.argv) < 2:',
    '        sys.exit(2)',
    '    notation = sys.argv[1]',
    '    target = _resolve(notation)',
    '    if target is None:',
    '        sys.stderr.write("Unknown notation: " + notation + "\\n")',
    '        sys.exit(2)',
    '    out_buf = io.StringIO()',
    '    err_buf = io.StringIO()',
    '    rc = 0',
    '    saved_argv = sys.argv',
    '    sys.argv = [str(target), *sys.argv[2:]]',
    '    try:',
    '        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):',
    '            runpy.run_path(str(target), run_name="__main__")',
    '    except SystemExit as exc:',
    '        code = exc.code',
    '        rc = 0 if code is None else (code if isinstance(code, int) else 1)',
    '    finally:',
    '        sys.argv = saved_argv',
    '    sys.stdout.write(out_buf.getvalue())',
    '    sys.stderr.write(err_buf.getvalue())',
    '    sys.stdout.flush()',
    '    sys.stderr.flush()',
    '    sys.exit(rc)',
    '',
    '',
    'if __name__ == "__main__":',
    '    main()',
)


def write_dispatching_executor(plan_dir: Path, notations: list[str]) -> Path:
    """Write the dispatching ``execute-script.py`` into ``plan_dir``.

    ``plan_dir`` is the scratch tree's ``.plan/`` directory (created when
    absent); ``notations`` are the ``bundle:skill:script`` keys to register in
    the ``SCRIPTS`` literal. Returns the executor path.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    lines = [
        *_PREAMBLE,
        *(f'    "{notation}": "resolved-at-dispatch",' for notation in notations),
        *_BODY,
    ]
    executor.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return executor
