#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Workflow-lint guard: the structural invariants over ``.github/workflows/*.yml``.

This module is the only automated control over this repository's workflow
template-injection surface and its token scopes, so each guard has to cover the
shapes its own docstring claims — a scanner that recognises one spelling of a
construct reports a clean tree it never actually read.

- **No context interpolation in a shell.** No GitHub Actions context expression
  (``${{ ... }}``) may appear inside a ``run:`` body, in ANY of its spellings:
  inline, block scalar, or multi-line plain scalar, behind a step dash of any
  width. A context value spliced into a shell is a template-injection surface (a
  ref name can carry shell metacharacters); the safe form passes the value
  through ``env:`` and references it as a quoted shell variable.
- **No implicit token scope, and no unreviewed write.** Every workflow declares a
  top-level ``permissions:`` block, and every scope in it is read-only unless it
  is on an explicit allowlist that carries the justification. Presence alone was
  never the property worth asserting: a declared ``contents: write`` satisfies
  "declares a block" while granting exactly what the guard exists to prevent.
  Job-level grants are checked separately and NOT folded into the top-level
  verdict — see :func:`test_a_top_level_read_only_block_is_not_a_whole_workflow_claim`.
- **Concurrency keys the verify gate can be cancelled by.** ``python-verify.yml``
  separates push runs from pull_request runs by event name, and cancels only
  within the pull_request class.

The linter is text-based on purpose: PyYAML is not in the project's locked dev
environment (``uv.lock`` carries no PyYAML), so the sibling structural guards in
``test/plan-marshall/manage-config/`` already parse these files without it. This
guard does the same, so it runs identically on a developer machine and in CI.
"""

import re
from pathlib import Path

import pytest

# repo_root/test/default/test_workflow_lint.py -> parents[2] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO_ROOT / '.github' / 'workflows'

# A GitHub Actions context expression opener. Its presence inside a run: body is
# the violation; the safe env-passing form keeps it on an env: line instead.
_CONTEXT_EXPR = re.compile(r'\$\{\{')
# A ``run:`` mapping key. The step dash is matched at ANY width: YAML accepts
# ``- run:``, ``-  run:`` and ``-   run:`` alike, and a scanner that only knows
# the two-character spelling silently skips the others — it would report a clean
# workflow it never read. The dash width is captured so the key column is
# computed from what was matched rather than from a hard-coded 2.
_RUN_LINE = re.compile(r'^(?P<lead>\s*)(?P<dash>-\s+)?run:(?P<after>.*)$')
_EXPR_LABEL = '${{ ... }}'


def _scalar_body(lines: list[str], start: int, key_col: int) -> tuple[list[str], int]:
    """The continuation lines of a scalar whose key begins at ``key_col``.

    Every following line that is blank or indented more deeply than ``key_col``
    belongs to the scalar, up to the first line that dedents to or past it.
    Returns the body and the index of that first non-body line.
    """
    body: list[str] = []
    j = start
    while j < len(lines):
        candidate = lines[j]
        if candidate.strip() == '':
            body.append(candidate)
            j += 1
            continue
        if len(candidate) - len(candidate.lstrip()) > key_col:
            body.append(candidate)
            j += 1
            continue
        break
    return body, j


def _run_block_context_violations(text: str) -> list[str]:
    """Return one message per ``run:`` body that carries a context expression.

    All three ``run:`` spellings are covered: the inline ``run: cmd`` form, the
    block-scalar ``run: |`` / ``run: >`` form, and the multi-line plain scalar
    whose command continues on deeper-indented following lines. The plain scalar
    needs the same body walk as the block scalar, because YAML folds those
    continuation lines into the command the shell ultimately runs — reading only
    the text after ``run:`` sees the first line of a command and calls the rest
    of it absent.
    """
    lines = text.splitlines()
    violations: list[str] = []
    i = 0
    while i < len(lines):
        match = _RUN_LINE.match(lines[i])
        if match is None:
            i += 1
            continue
        dash = match.group('dash') or ''
        key_col = len(match.group('lead')) + len(dash)
        after = match.group('after').strip()
        line_no = i + 1
        body, next_index = _scalar_body(lines, i + 1, key_col)
        body_has_expr = any(_CONTEXT_EXPR.search(line) for line in body)
        if after == '' or after.startswith('|') or after.startswith('>'):
            if body_has_expr:
                violations.append(
                    f'run: block starting at line {line_no} contains a {_EXPR_LABEL} '
                    'context expression; pass the value via env: and reference it as a '
                    'quoted shell variable instead.'
                )
            # Only the block scalar consumes its body: a plain scalar's
            # continuation lines are re-examined so a nested run: is not skipped.
            i = next_index
            continue
        if _CONTEXT_EXPR.search(after) or body_has_expr:
            violations.append(
                f'run: at line {line_no} contains a {_EXPR_LABEL} context expression; '
                'pass the value via env: and reference it as a quoted shell variable instead.'
            )
        i += 1
    return violations


# --- permissions ----------------------------------------------------------------

#: A ``scope: value`` line inside a permissions block.
_SCOPE_LINE = re.compile(r'^\s+(?P<scope>[A-Za-z][A-Za-z-]*):\s*(?P<value>\S+)\s*$')
#: The permission values that grant nothing. Anything else is a write grant.
_READ_ONLY_VALUES = frozenset({'read', 'none'})
#: The key an inline shorthand is recorded under — it stands for EVERY scope, so
#: no single scope name would be honest.
_ALL_SCOPES_KEY = '*'
#: GitHub's two inline shorthands, mapped to the ordinary per-scope value they
#: are equivalent to. Both spellings end in ``-all`` and neither is in
#: :data:`_READ_ONLY_VALUES`, so an un-normalised reader gets them BOTH wrong and
#: in opposite directions: ``read-all`` reads as a write grant it is not, and
#: ``write-all`` — which has no indented body for the block reader to find —
#: reads as no grant at all, though it is the broadest one the syntax allows.
_INLINE_SHORTHANDS = {'read-all': 'read', 'write-all': 'write'}


def _inline_permissions(value: str) -> dict[str, str] | None:
    """The scope mapping an inline ``permissions: <value>`` header stands for.

    ``None`` means the header carried no inline value, i.e. it opens a block
    whose scopes are on the following indented lines and the block reader owns
    it. A recognised shorthand is normalised to the per-scope value it means; an
    unrecognised one is passed through verbatim rather than guessed at, so a
    spelling this table does not know stays visible to the write-scope reader
    instead of vanishing.

    Shared by BOTH readers so the top-level and job-level verdicts cannot
    disagree about what an inline header means.
    """
    if not value:
        return None
    return {_ALL_SCOPES_KEY: _INLINE_SHORTHANDS.get(value, value)}


def _permission_scopes(lines: list[str], header: int, header_indent: int) -> dict[str, str]:
    """The ``scope: value`` mapping under the permissions header at ``lines[header]``."""
    scopes: dict[str, str] = {}
    for line in lines[header + 1:]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if len(line) - len(line.lstrip()) <= header_indent:
            break
        found = _SCOPE_LINE.match(line)
        if found:
            scopes[found.group('scope')] = found.group('value')
    return scopes


def _top_level_permissions(text: str) -> dict[str, str] | None:
    """The top-level (column-0) permissions mapping, or None when the block is absent.

    An inline form (``permissions: read-all``) is normalised by
    :func:`_inline_permissions` and returned under the ``*`` key so it is neither
    silently dropped nor mistaken for an empty block.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('permissions:'):
            inline = _inline_permissions(line[len('permissions:'):].strip())
            return inline if inline is not None else _permission_scopes(lines, i, 0)
    return None


def _job_level_permissions(text: str) -> dict[str, str]:
    """The union of every indented (job-level) permissions mapping in the workflow.

    The inline form is normalised through the same :func:`_inline_permissions`
    helper the top-level reader uses. Handing an inline header to
    :func:`_permission_scopes` instead would contribute NOTHING — that reader
    only collects indented continuation lines, and an inline header has none —
    so a job declaring ``permissions: write-all`` would be invisible here.
    """
    scopes: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()
        if indent > 0 and stripped.startswith('permissions:'):
            inline = _inline_permissions(stripped[len('permissions:'):].strip())
            scopes.update(inline if inline is not None else _permission_scopes(lines, i, indent))
    return scopes


def _has_top_level_permissions(text: str) -> bool:
    """True when the workflow declares a top-level (column-0) ``permissions:`` key."""
    return _top_level_permissions(text) is not None


def _write_scopes(scopes: dict[str, str]) -> set[str]:
    return {scope for scope, value in scopes.items() if value not in _READ_ONLY_VALUES}


#: TOP-LEVEL write scopes that are deliberate, keyed ``(filename, scope)`` so the
#: population is countable and each entry carries its own justification. Derived
#: at execute time from a walk of .github/workflows/: seven workflows, of which
#: six declare a top-level block that is entirely read (python-verify.yml carries
#: `pull-requests: read` beside `contents: read`, still a read scope).
#: pr-agent.yml is the sole top-level write-bearing workflow, with these three.
_TOP_LEVEL_WRITE_ALLOWLIST = {
    ('pr-agent.yml', 'pull-requests'):
        'The reviewer publishes its review as a PR review body and inline comments.',
    ('pr-agent.yml', 'issues'):
        'On-demand commands (/review, /ask, /improve) arrive as issue_comment events '
        'and are answered on the issue/PR thread.',
    ('pr-agent.yml', 'id-token'):
        'Mints the OIDC token Workload Identity Federation exchanges for the '
        'short-lived GCP credentials the reviewer uses to reach Gemini on Vertex AI.',
}

#: JOB-LEVEL write scopes. Kept in a SEPARATE allowlist from the top-level one on
#: purpose: a job-level grant narrows a read-only top-level default to the one job
#: that needs it, which is the least-privilege form, whereas a top-level write
#: grant hands the scope to every job in the file. Merging the two lists would
#: also make the top-level count meaningless — see the strict-subset test below.
_JOB_LEVEL_WRITE_ALLOWLIST = {
    ('dependabot-auto-merge.yml', 'contents'):
        'The auto-merge job merges the dependabot PR.',
    ('dependabot-auto-merge.yml', 'pull-requests'):
        'The auto-merge job approves the dependabot PR and enables auto-merge on it.',
    ('dependency-review.yml', 'pull-requests'):
        'The review job posts its dependency-diff summary as a PR comment.',
    ('scorecards.yml', 'security-events'):
        'The analysis job uploads its SARIF result to the code-scanning API.',
    ('scorecards.yml', 'id-token'):
        'The analysis job mints the OIDC token the Scorecard publish step exchanges.',
}


def _workflow_files() -> list[Path]:
    return sorted(_WORKFLOWS_DIR.glob('*.yml')) + sorted(_WORKFLOWS_DIR.glob('*.yaml'))


def _observed_write_scopes(reader) -> set[tuple[str, str]]:
    """``(filename, scope)`` for every write grant ``reader`` finds in the real tree."""
    return {
        (workflow.name, scope)
        for workflow in _workflow_files()
        for scope in _write_scopes(reader(workflow.read_text(encoding='utf-8')) or {})
    }


# --- guards over the real .github/workflows/ tree -------------------------------


def test_workflows_have_no_context_expression_in_run_blocks() -> None:
    """No workflow interpolates a context expression inside a run: body."""
    offenders: dict[str, list[str]] = {}
    for workflow in _workflow_files():
        found = _run_block_context_violations(workflow.read_text(encoding='utf-8'))
        if found:
            offenders[workflow.name] = found

    assert not offenders, (
        'A GitHub Actions context expression (${{ ... }}) appears inside a run: '
        'block — a template-injection surface, since a context value (e.g. a ref '
        'name) can carry shell metacharacters. Pass the value via env: and '
        f'reference it as a quoted shell variable.\n{offenders}'
    )


def test_workflows_declare_top_level_permissions() -> None:
    """Every workflow declares a top-level permissions: block."""
    missing = [
        workflow.name
        for workflow in _workflow_files()
        if not _has_top_level_permissions(workflow.read_text(encoding='utf-8'))
    ]

    assert not missing, (
        'Workflow(s) without a top-level permissions: block inherit the '
        'repository/organisation default GITHUB_TOKEN scope. Declare an explicit '
        f'least-privilege permissions: block.\n  missing: {missing}'
    )


def test_every_top_level_permission_scope_is_read_only_or_allowlisted() -> None:
    """Declared is not the property worth asserting — read-only is.

    A workflow satisfies "declares a permissions: block" with `contents: write`,
    which grants exactly what the block exists to withhold. Every top-level scope
    must therefore be read or none, unless it is allowlisted with a stated reason.
    """
    unreviewed = sorted(
        _observed_write_scopes(_top_level_permissions) - set(_TOP_LEVEL_WRITE_ALLOWLIST)
    )

    assert not unreviewed, (
        'Top-level write scope(s) with no allowlist entry. A top-level grant is '
        'held by every job in the file, so it needs a reviewed justification or a '
        f'narrowing job-level block instead:\n  {unreviewed}'
    )


def test_the_top_level_allowlist_holds_exactly_the_three_pr_agent_scopes() -> None:
    """The allowlist is a closed, countable set — a fourth entry must fail here.

    An allowlist that can absorb a new entry silently is not a control. Three
    entries, all pr-agent.yml, is the derived state of the tree; anything else is
    a change that has to be argued for rather than merged into the guard.
    """
    keys = sorted(_TOP_LEVEL_WRITE_ALLOWLIST)

    assert len(keys) == 3, f'expected exactly three allowlisted top-level scopes, got {keys}'
    assert {name for name, _ in keys} == {'pr-agent.yml'}, (
        f'pr-agent.yml is the sole top-level write-bearing workflow; got {keys}'
    )


@pytest.mark.parametrize(
    ('allowlist', 'reader', 'label'),
    [
        (_TOP_LEVEL_WRITE_ALLOWLIST, _top_level_permissions, 'top-level'),
        (_JOB_LEVEL_WRITE_ALLOWLIST, _job_level_permissions, 'job-level'),
    ],
    ids=['top-level', 'job-level'],
)
def test_every_allowlist_entry_matches_a_real_declared_write_scope(
    allowlist, reader, label
) -> None:
    """Each entry earns its place: a stale or invented one fails here.

    Without this direction the guard above passes for the wrong reason — an
    allowlist naming scopes nothing declares would let a real write scope be
    added under a name already excused, and a removed scope would leave a
    permanent hole nobody notices.
    """
    stale = sorted(set(allowlist) - _observed_write_scopes(reader))

    assert not stale, (
        f'{label} allowlist entr(ies) matching no declared write scope. Remove '
        f'them, or the allowlist excuses grants that are no longer reviewed:\n  {stale}'
    )


def test_every_job_level_write_scope_is_allowlisted() -> None:
    """Job-level grants are reviewed too — the top-level check does not see them."""
    unreviewed = sorted(
        _observed_write_scopes(_job_level_permissions) - set(_JOB_LEVEL_WRITE_ALLOWLIST)
    )

    assert not unreviewed, (
        f'Job-level write scope(s) with no allowlist entry:\n  {unreviewed}'
    )


def test_a_top_level_read_only_block_is_not_a_whole_workflow_claim() -> None:
    """The top-level verdict's scope limit is asserted, not assumed.

    Reading only the top-level block finds ONE write-bearing workflow in this
    tree; three more grant a write at job level. A guard that reported "six of
    seven are read-only" would be describing its own reach as if it were the
    repository's state — the overstatement this module exists to refuse. Pinning
    the strict subset keeps the two counts from ever being read as one.
    """
    top_level = {name for name, _ in _observed_write_scopes(_top_level_permissions)}
    anywhere = top_level | {name for name, _ in _observed_write_scopes(_job_level_permissions)}

    assert top_level < anywhere, (
        'Expected strictly more workflows to be write-bearing somewhere than at '
        'the top level; if these sets have become equal, the top-level guard is '
        f'now the whole story and this test should say so.\n  top-level: '
        f'{sorted(top_level)}\n  anywhere: {sorted(anywhere)}'
    )
    assert len(anywhere) > len(top_level) >= 1


def test_the_permission_scan_is_not_vacuous() -> None:
    """Anti-vacuity: a parser that read nothing would make every check above pass."""
    parsed = {
        workflow.name: _top_level_permissions(workflow.read_text(encoding='utf-8'))
        for workflow in _workflow_files()
    }

    assert len(parsed) >= 7, f'expected at least seven workflows, parsed {sorted(parsed)}'
    empty = sorted(name for name, scopes in parsed.items() if not scopes)
    assert not empty, (
        f'permissions parser extracted no scope from {empty}; the read-only '
        'assertions above would be vacuous for those files'
    )


def test_workflow_tree_is_non_empty() -> None:
    """Guard the guard: a mislocated workflows dir must not make the checks vacuous."""
    assert _workflow_files(), (
        f'no workflow files found under {_WORKFLOWS_DIR}; the guards would '
        'pass vacuously'
    )


# --- concurrency: the verify gate must not be cancellable across event classes ---

_VERIFY_WORKFLOW = _WORKFLOWS_DIR / 'python-verify.yml'
#: The failure this keying prevents, quoted into every assertion below so the
#: reason survives the next person's refactor.
_CANCELLED_GATE_REASON = (
    'A shared concurrency group let a pull_request run cancel the push run of the '
    'same branch mid-flight. The always-reporting `conclusion` job hard-fails on a '
    'cancelled gate (correctly — a cancelled gate must never be masked as a skip), '
    'planting a RED required `verify / conclusion` check on the PR head SHA, and '
    'the merge then fails with "405 Repository rule violations found".'
)
_EXPRESSION = re.compile(r'\$\{\{(?P<body>.*?)\}\}')


def _concurrency_field(field: str) -> str:
    """The raw value of ``concurrency.<field>`` in python-verify.yml."""
    lines = _VERIFY_WORKFLOW.read_text(encoding='utf-8').splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('concurrency:'))
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if len(line) - len(line.lstrip()) == 0:
            break
        key, _, value = line.strip().partition(':')
        if key == field:
            return value.strip()
    raise AssertionError(f'concurrency.{field} is not declared in {_VERIFY_WORKFLOW.name}')


def _lookup(context: dict, path: str):
    node = context
    for part in path.split('.'):
        if not isinstance(node, dict) or part not in node:
            return ''
        node = node[part]
    return node


def _resolve(template: str, context: dict) -> str:
    """Evaluate the ``${{ ... }}`` expressions in ``template`` against ``context``.

    Supports the two operators this workflow uses: ``||`` (first truthy operand)
    and ``==`` against a quoted literal. Enough to resolve the group a real run
    would land in, which is the property under test — the alternative, asserting
    the template's text, cannot tell two events apart.
    """
    def _one(match: re.Match) -> str:
        body = match.group('body').strip()
        if '==' in body:
            left, _, right = body.partition('==')
            return 'true' if str(_lookup(context, left.strip())) == right.strip().strip('\'"') else 'false'
        for operand in (part.strip() for part in body.split('||')):
            value = _lookup(context, operand)
            if value:
                return str(value)
        return ''

    return _EXPRESSION.sub(_one, template)


def _context(event_name: str, branch: str) -> dict:
    event: dict = {}
    if event_name == 'pull_request':
        event = {'pull_request': {'head': {'ref': branch}}}
    return {
        'github': {
            'workflow': 'Python Verify',
            'event_name': event_name,
            'ref_name': branch,
            'event': event,
        }
    }


def test_the_verify_concurrency_group_is_keyed_on_the_event_name() -> None:
    """python-verify.yml's concurrency group includes github.event_name."""
    group = _concurrency_field('group')

    assert 'github.event_name' in group, (
        f'concurrency.group must include github.event_name. {_CANCELLED_GATE_REASON}\n'
        f'  group: {group}'
    )


def test_a_push_and_a_pull_request_on_one_branch_resolve_to_different_groups() -> None:
    """The positive direction: the two event classes land in separate groups.

    Asserting the template contains the token is necessary but not sufficient —
    the token could be present and still resolve identically. Resolving both
    events for the SAME branch is what proves they cannot cancel one another.
    """
    group = _concurrency_field('group')
    branch = 'feature/some-work'

    push = _resolve(group, _context('push', branch))
    pull_request = _resolve(group, _context('pull_request', branch))

    assert push and pull_request, f'group resolved empty: push={push!r} pr={pull_request!r}'
    assert push != pull_request, (
        f'A push and a pull_request on branch {branch!r} resolve to the same '
        f'concurrency group ({push!r}), so either can cancel the other. '
        f'{_CANCELLED_GATE_REASON}'
    )
    assert branch in push and branch in pull_request, (
        'the group must still key on branch identity, or unrelated branches '
        f'would share a group: push={push!r} pr={pull_request!r}'
    )


def test_verify_cancel_in_progress_stays_scoped_to_pull_request() -> None:
    """Only a pull_request run is cancellable; push and merge_group never are.

    Cancelling within the pull_request class is the ~10 minute saving worth
    having. Widening it to push or merge_group re-opens the cancelled-gate
    failure from the other side, by cancelling a run whose conclusion is required.
    """
    cancel = _concurrency_field('cancel-in-progress')

    resolved = {
        event: _resolve(cancel, _context(event, 'feature/some-work'))
        for event in ('pull_request', 'push', 'merge_group')
    }

    assert resolved == {'pull_request': 'true', 'push': 'false', 'merge_group': 'false'}, (
        f'cancel-in-progress must be true only for pull_request. {_CANCELLED_GATE_REASON}\n'
        f'  expression: {cancel}\n  resolved: {resolved}'
    )


# --- linter behaviour: it must FAIL a bad workflow and PASS the fixed form -------

_BAD_INJECTION_WF = """\
name: Bad
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Create tag
        run: |
          git tag -a "${{ github.ref_name }}" -m "release"
"""

_GOOD_ENV_WF = """\
name: Good
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Create tag
        env:
          REF_NAME: ${{ github.ref_name }}
        run: |
          git tag -a "${REF_NAME}" -m "release"
"""

_NO_PERMISSIONS_WF = """\
name: NoPerms
on:
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""

#: A wide step dash. YAML accepts any run of whitespace after the dash, and the
#: two-character spelling is a convention, not a rule.
_WIDE_DASH_INLINE_WF = (
    'jobs:\n  j:\n    steps:\n'
    '      -   run: echo "${{ github.event.issue.title }}"\n'
)
_WIDE_DASH_BLOCK_WF = (
    'jobs:\n  j:\n    steps:\n'
    '      -   run: |\n'
    '            echo "${{ github.event.issue.title }}"\n'
)
#: A multi-line PLAIN scalar: no `|`, no `>`, the command simply continues on the
#: following deeper-indented lines. YAML folds them into one command string.
_PLAIN_CONTINUATION_WF = (
    'jobs:\n  j:\n    steps:\n'
    '      - run: echo\n'
    '          "${{ github.event.issue.title }}"\n'
)
#: The negative control for the plain-scalar body walk: a SIBLING mapping at the
#: same indent as the run: key, legitimately carrying a context expression.
_SIBLING_MAPPING_WF = (
    'jobs:\n  j:\n    steps:\n'
    '      - run: echo "$TITLE"\n'
    '        env:\n'
    '          TITLE: ${{ github.event.issue.title }}\n'
    '        with:\n'
    '          ref: ${{ github.ref_name }}\n'
)


@pytest.mark.parametrize(
    'workflow',
    [_BAD_INJECTION_WF, _WIDE_DASH_INLINE_WF, _WIDE_DASH_BLOCK_WF, _PLAIN_CONTINUATION_WF],
    ids=['block-scalar', 'wide-dash-inline', 'wide-dash-block', 'plain-continuation'],
)
def test_linter_flags_every_run_spelling_that_interpolates(workflow: str) -> None:
    """Each spelling of a run: body reaches the shell, so each must be scanned."""
    assert _run_block_context_violations(workflow), (
        'linter did not flag a ${{ ... }} interpolation in this run: spelling; an '
        f'unrecognised spelling is scanned as if it were absent\n{workflow}'
    )


@pytest.mark.parametrize(
    'workflow',
    [_GOOD_ENV_WF, _SIBLING_MAPPING_WF],
    ids=['env-passed', 'sibling-mapping'],
)
def test_linter_passes_the_env_passed_form(workflow: str) -> None:
    """A context expression on a sibling mapping is the SAFE form, not a violation.

    The body walk stops at the first line that dedents to the run: key column, so
    an `env:`/`with:` mapping at that column is outside the scalar. Without this
    direction a widened scanner would flag the very form the fix prescribes.
    """
    assert _run_block_context_violations(workflow) == []


def test_linter_flags_missing_top_level_permissions() -> None:
    """The permissions guard must FAIL a workflow with no top-level permissions:."""
    assert not _has_top_level_permissions(_NO_PERMISSIONS_WF)


def test_linter_passes_declared_permissions() -> None:
    """The permissions guard must PASS a workflow that declares permissions:."""
    assert _has_top_level_permissions(_GOOD_ENV_WF)


def test_the_scope_reader_separates_top_level_from_job_level_grants() -> None:
    """The two readers must not see each other's blocks, or the split is fiction."""
    workflow = (
        'permissions:\n  contents: read\n'
        'jobs:\n  j:\n    permissions:\n      contents: write\n'
    )

    assert _top_level_permissions(workflow) == {'contents': 'read'}
    assert _job_level_permissions(workflow) == {'contents': 'write'}


def test_the_scope_reader_normalizes_the_inline_read_all_shorthand() -> None:
    """``permissions: read-all`` withholds every write — reporting one is a false red.

    The value is GitHub's shorthand for every scope at READ level. Left
    un-normalised it is merely "not read and not none", which is exactly how the
    write-scope reader classifies a grant, so the guard would demand an allowlist
    entry for a declaration that grants nothing.
    """
    workflow = 'permissions: read-all\njobs:\n  j:\n    permissions: read-all\n'

    assert _write_scopes(_top_level_permissions(workflow) or {}) == set()
    assert _write_scopes(_job_level_permissions(workflow)) == set()


def test_the_scope_reader_sees_the_inline_write_all_shorthand() -> None:
    """``permissions: write-all`` is the broadest grant the syntax allows.

    A header carrying it inline has no indented continuation lines, so the block
    reader finds no ``scope: value`` pair under it and contributes nothing. The
    job-level guard then returns a clean verdict over the single most permissive
    declaration it exists to catch — a false green on the worst case.
    """
    workflow = 'permissions: write-all\njobs:\n  j:\n    permissions: write-all\n'

    assert _write_scopes(_top_level_permissions(workflow) or {}) == {'*'}
    assert _write_scopes(_job_level_permissions(workflow)) == {'*'}
