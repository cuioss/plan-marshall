#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Every pre-push-quality-gate arm obtains its invocation from a resolver.

``standards/pre-push-quality-gate.md`` runs several build arms. Each one must
take the command it runs from what ``architecture resolve`` returned — never
from a build-tool literal written into the document — because a literal makes
the arm unrunnable in any project whose build tool is not this repository's,
and an unrunnable arm is precisely the shape that reports green having executed
nothing.

**The arm population is DERIVED from the document**, not listed here: an arm is
a ``### `` section under the gate's Execution flow whose fenced code blocks
carry an ``architecture resolve --command`` call. Deriving it is what makes the
sweep survive an arm being added or renamed — a hand-written roster would keep
passing over the arms it still names while a new one shipped unchecked. The
derived size is published in every failure message and in the session report
header, so a derivation that silently collapsed to one arm is visible on a
GREEN run rather than only on a red one.

Two properties per arm, and they are not the same property:

* **Positive** — the arm captures ``executable`` from the resolve return, so
  what it runs is what the resolver produced.
* **Negative** — no fenced invocation inside the arm names a concrete build
  tool. Scoped to FENCED blocks deliberately: the ``test-compile`` arm quotes
  one such literal in prose as the recorded EVIDENCE for why it resolves
  module-scoped and widens, and that citation is not an invocation. A
  file-wide token test would fail the document for explaining itself.

Both properties are paired with mutation guards that run each detector against
a synthetic pre-fix arm, so a detector typo fails here rather than making the
sweep vacuously green.
"""

from __future__ import annotations

import re

import pytest

from conftest import MARKETPLACE_ROOT

_GATE_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'pre-push-quality-gate.md'
)

#: An ``architecture resolve`` call — the marker that makes a section an ARM.
#: Matched on the verb plus its ``--command`` flag rather than on the notation
#: alone, so a prose mention of the script name does not promote a section.
_RESOLVE_CALL = re.compile(r'architecture\s+resolve\s+--command\s+[a-z-]+')

#: The instruction that ties the arm's invocation to the resolve RETURN. An arm
#: that resolves and then runs something else would satisfy ``_RESOLVE_CALL``
#: while pinning its command anyway, so the capture is asserted separately.
_CAPTURES_EXECUTABLE = re.compile(r'[Cc]apture\s+`executable`')

#: Concrete build-tool literals. Both are this repository's own tool: the
#: pyprojectx wrapper and the notation of the build skill that wraps it. A
#: consumer on Maven, Gradle or npm has neither, so either one appearing inside
#: an arm's runnable call is the defect.
_BUILD_TOOL_TOKENS = ('./pw', 'pyproject_build')


def _doc_text() -> str:
    text: str = _GATE_DOC.read_text(encoding='utf-8')
    return text


def _subsections(text: str) -> list[tuple[str, str]]:
    """Split the document into ``(heading, body)`` for every ``### `` section."""
    sections: list[tuple[str, str]] = []
    heading: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith('### '):
            if heading is not None:
                sections.append((heading, '\n'.join(body)))
            heading = line[len('### ') :].strip()
            body = []
            continue
        if line.startswith('## ') and heading is not None:
            sections.append((heading, '\n'.join(body)))
            heading = None
            body = []
            continue
        if heading is not None:
            body.append(line)
    if heading is not None:
        sections.append((heading, '\n'.join(body)))
    return sections


def _fenced_blocks(body: str) -> list[str]:
    """Return every fenced code block in ``body``, backslash-continuations folded."""
    blocks: list[str] = []
    in_fence = False
    current: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith('```'):
            if in_fence:
                blocks.append(re.sub(r'\\\n\s*', ' ', '\n'.join(current)))
                current = []
            in_fence = not in_fence
            continue
        if in_fence:
            current.append(line)
    return blocks


def _is_arm(body: str) -> bool:
    """True when a section's FENCED blocks carry an ``architecture resolve`` call.

    Fenced-scoped so a section that merely discusses resolution in prose is not
    counted as an arm — the population must be the sections that actually run a
    resolved command.
    """
    return any(_RESOLVE_CALL.search(block) for block in _fenced_blocks(body))


def _derive_arms() -> list[tuple[str, str]]:
    """Return ``(heading, body)`` for every resolver-backed arm, in document order."""
    return [
        (heading, body) for heading, body in _subsections(_doc_text()) if _is_arm(body)
    ]


_ARMS = _derive_arms()

# Non-emptiness asserted at IMPORT, before any parametrize sweeps it — an empty
# parametrize is a pytest SKIP, not a failure, so a derivation that matched
# nothing would report a clean sweep over nothing. The size travels in the
# message so a silently shrunken derivation is visible as a number.
assert _ARMS, (
    f'No resolver-backed arm was derived from {_GATE_DOC.name} — the provenance '
    f'sweep would pass over an empty set. Sections seen: '
    f'{[heading for heading, _body in _subsections(_doc_text())]}'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The import-time assertion above fails an EMPTY
#: population; publishing the size is what makes a SHRUNKEN one visible on the
#: green run, where no failure message is ever rendered.
GUARD_POPULATION_LABEL = 'pre-push-quality-gate resolver-backed arms'
GUARD_POPULATION_SIZE = len(_ARMS)

_ARM_IDS = [
    re.sub(r'[^A-Za-z0-9]+', '-', heading).strip('-').lower() for heading, _body in _ARMS
]


# ---------------------------------------------------------------------------
# The derivation itself is falsifiable
# ---------------------------------------------------------------------------


def test_arm_derivation_excludes_the_non_arm_sections():
    """The gate's non-build sections must NOT be derived as arms.

    Without this the derivation could be matching every ``### `` section, and
    the per-arm sweep below would then be measuring the document's section
    count rather than its arm count.
    """
    all_headings = [heading for heading, _body in _subsections(_doc_text())]
    arm_headings = [heading for heading, _body in _ARMS]

    non_arms = [heading for heading in all_headings if heading not in arm_headings]

    assert non_arms, (
        f'Every one of the {len(all_headings)} sections in {_GATE_DOC.name} was '
        f'derived as a resolver-backed arm, so the derivation is not '
        f'discriminating and the sweep below proves nothing about arms '
        f'specifically'
    )
    assert len(arm_headings) < len(all_headings)


def test_arm_detector_fires_on_a_resolver_backed_section_and_not_on_a_prose_one():
    resolver_backed = (
        'Resolve the canonical:\n'
        '\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \\\n'
        '  resolve --command quality-gate --module {bundle} --audit-plan-id {plan_id}\n'
        '```\n'
    )
    prose_only = (
        'The derivation is exactly live footprint intersected with the '
        'registered build_map globs; a caller that needs the command would '
        'resolve it via architecture resolve --command quality-gate.\n'
    )

    assert _is_arm(resolver_backed), (
        'The arm detector did not fire on a fenced resolve call — the derived '
        'population would be empty and every sweep vacuous'
    )
    assert not _is_arm(prose_only), (
        'The arm detector fires on a PROSE mention of resolution, so sections '
        'that run no build would be swept as arms'
    )


# ---------------------------------------------------------------------------
# Positive — each arm takes its invocation from the resolve RETURN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('heading', 'body'), _ARMS, ids=_ARM_IDS)
def test_every_arm_captures_the_resolved_executable(heading, body):
    assert _CAPTURES_EXECUTABLE.search(body), (
        f'Arm {heading!r} resolves a canonical but never captures the returned '
        f'`executable`, so what it runs is not tied to what the resolver '
        f'produced (population: {len(_ARMS)} arm(s))'
    )


# ---------------------------------------------------------------------------
# Negative — no arm's runnable call names a concrete build tool
# ---------------------------------------------------------------------------


def _pinned_tokens_in_invocations(body: str) -> list[tuple[str, str]]:
    """Return ``(token, block)`` for every build-tool literal in a fenced block."""
    pinned: list[tuple[str, str]] = []
    for block in _fenced_blocks(body):
        for token in _BUILD_TOOL_TOKENS:
            if token in block:
                pinned.append((token, block))
    return pinned


@pytest.mark.parametrize(('heading', 'body'), _ARMS, ids=_ARM_IDS)
def test_no_arm_pins_a_build_tool_in_a_runnable_call(heading, body):
    pinned = _pinned_tokens_in_invocations(body)

    assert not pinned, (
        f'Arm {heading!r} names a concrete build tool inside a fenced '
        f'invocation, so the arm is unrunnable in a project whose build tool '
        f'differs: {[token for token, _block in pinned]} '
        f'(population: {len(_ARMS)} arm(s))'
    )


def test_pinned_token_detector_fires_on_a_synthetic_pre_fix_arm():
    pre_fix = (
        'For each bundle, run the gate:\n'
        '\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build \\\n'
        '  run --command-args "quality-gate {bundle}"\n'
        '```\n'
    )
    post_fix = (
        'For each bundle, resolve the canonical and run what it returned:\n'
        '\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \\\n'
        '  resolve --command quality-gate --module {bundle} --audit-plan-id {plan_id}\n'
        '```\n'
    )

    assert _pinned_tokens_in_invocations(pre_fix), (
        'The pinned-token detector did not fire on a synthetic pre-fix arm, so '
        'the per-arm negative above would be vacuously green'
    )
    assert not _pinned_tokens_in_invocations(post_fix), (
        'The pinned-token detector fires on the resolver-backed form, so the '
        'per-arm negative would fail for the wrong reason'
    )


def test_prose_citation_of_a_build_tool_is_not_read_as_an_invocation():
    """A recorded observation that QUOTES a resolved literal is not a pin.

    The ``test-compile`` arm records the exact executable a module-scoped
    resolve returned in this repository, as the evidence for why it widens that
    form rather than resolving at default scope. Scoping the negative to fenced
    blocks is what keeps that citation legal; this pins the scoping so a later
    broadening to a file-wide token test cannot pass unnoticed.
    """
    citing = (
        'The observation was recorded against this repository: '
        '`architecture resolve --command test-compile --module plan-marshall` '
        'returned `pyproject_build run --command-args "test-compile '
        'plan-marshall"`. That literal is the evidence, not the invocation.\n'
    )

    assert any(token in citing for token in _BUILD_TOOL_TOKENS), (
        'The synthetic citation carries no build-tool token, so it does not '
        'exercise the prose-versus-fence distinction at all'
    )
    assert not _pinned_tokens_in_invocations(citing), (
        'A prose citation of a resolved literal is being read as a pinned '
        'invocation, which would fail the document for recording its own '
        'evidence'
    )
