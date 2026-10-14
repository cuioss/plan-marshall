#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc contract: the five wait documents agree on the one runnable rule.

D6 states the single bounded hand-back rule for orchestrator-tier long-build
waits across five wait documents: a daemon-routed build's wrapper call returns
within a bound below the per-call ceiling with a terminal result or a live
running status plus job id, and the orchestrator re-attaches with a bounded
wait on that id; backgrounding (``run_in_background``) is named only for the
non-daemon fallback, never for a daemon-routed build.

This module pins that agreement from the document side (the factory side is
pinned by ``test_build_execute_factory.py``): every one of the five documents
states the canonical rule sentence verbatim, and no passage in any of them
prescribes ``run_in_background`` for a daemon-routed build. A rewording that
drops the rule, or a new passage that backgrounds a daemon-routed build, fails
here instead of letting the five documents drift apart unnoticed.

The document population is FIXED at five — the agreement is defined over
exactly these documents — so there is no tree-derived shrink/growth guard;
promoting a sixth document into the agreement is a scope change that updates
``_WAIT_DOCS`` explicitly.
"""

from __future__ import annotations

from pathlib import Path

from conftest import PROJECT_ROOT

#: The five wait documents the one-runnable-rule agreement spans, as
#: repo-relative paths. Fixed, not tree-derived: the agreement names them.
_WAIT_DOCS = (
    'marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md',
    'marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md',
    'marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md',
    'marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md',
)

#: The canonical rule sentence every agreement document states verbatim.
_ONE_RUNNABLE_RULE = (
    'One runnable rule: the wrapper call for a daemon-routed build returns '
    'within a bound below the per-call ceiling with a terminal result or a '
    'live running status plus job id, and the orchestrator re-attaches with '
    'a bounded wait on that id; backgrounding (`run_in_background`) is named '
    'only for the non-daemon fallback, never for a daemon-routed build.'
)

#: Phrases that couple a passage to daemon-routed waiting. Strict on purpose:
#: ``non-daemon fallback`` carries ``daemon`` as a substring but is the
#: legitimate scope, so the bare word alone must never qualify a paragraph.
_DAEMON_ROUTING_PHRASES = (
    'daemon-routed build',
    'daemon-routed',
    'daemon `wait`',
    'daemon wait',
)

#: Tokens that exonerate a daemon-coupled ``run_in_background`` passage: a
#: prohibition, a non-daemon scoping, or the rule sentence itself. A passage
#: that backgrounds a daemon-routed build carries none of these.
_EXONERATING_TOKENS = (
    'never for a daemon-routed build',
    'non-daemon fallback',
    'Never `run_in_background`',
    'Do NOT `run_in_background`',
    'MUST NOT',
    'cannot',
    'superseded',
    'not daemon-served',
    'In neither tier',
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The agreement is defined over exactly five
#: documents, so a miscount here means ``_WAIT_DOCS`` drifted.
GUARD_POPULATION_LABEL = 'wait documents swept for the one-runnable-rule agreement'
GUARD_POPULATION_SIZE = len(_WAIT_DOCS)


def _paragraphs(text: str) -> list[str]:
    """Split document text into blank-line-separated passages."""
    return [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]


def _prescribes_background_for_daemon_routed_build(paragraph: str) -> bool:
    """Decide whether one passage backgrounds a daemon-routed build.

    A passage prescribes exactly when it names ``run_in_background`` against
    a daemon-routing phrase with no exonerating token — no prohibition, no
    non-daemon scoping, no rule sentence. Anything else (wait-class detach,
    leaf prohibitions, the synchronous fallback) answers False.
    """
    if 'run_in_background' not in paragraph:
        return False
    if not any(phrase in paragraph for phrase in _DAEMON_ROUTING_PHRASES):
        return False
    return not any(token in paragraph for token in _EXONERATING_TOKENS)


def _read_doc(rel: str) -> str:
    text: str = (PROJECT_ROOT / rel).read_text(encoding='utf-8')
    return text


def test_all_five_wait_documents_exist() -> None:
    missing = [rel for rel in _WAIT_DOCS if not (PROJECT_ROOT / rel).is_file()]

    assert not missing, (
        f'These agreement documents name no file in the tree, so the rule agreement cannot be verified: {missing}'
    )


def test_published_population_matches_the_agreement() -> None:
    assert GUARD_POPULATION_SIZE == len(_WAIT_DOCS) == 5, (
        f'Published population size {GUARD_POPULATION_SIZE} disagrees with the '
        f'agreement population ({len(_WAIT_DOCS)}), so the number reported on '
        f'a green run is not the number swept'
    )
    assert GUARD_POPULATION_LABEL.strip(), (
        'The published label is empty, so the report header would carry a bare '
        'number with nothing naming what was counted'
    )


def test_each_wait_document_states_the_one_runnable_rule() -> None:
    silent = [rel for rel in _WAIT_DOCS if _ONE_RUNNABLE_RULE not in _read_doc(rel)]

    assert not silent, (
        f'These agreement documents no longer state the canonical one-runnable-rule '
        f'sentence verbatim, so the five-document agreement is broken: {silent}. '
        f'Either restore the sentence or promote the rewording across all five.'
    )


def test_no_passage_prescribes_background_for_a_daemon_routed_build() -> None:
    offenders: list[str] = []
    for rel in _WAIT_DOCS:
        for paragraph in _paragraphs(_read_doc(rel)):
            if _prescribes_background_for_daemon_routed_build(paragraph):
                offenders.append(f'{rel}: {paragraph[:200]}')

    assert not offenders, (
        f'These passages prescribe run_in_background for a daemon-routed build, '
        f'against the one runnable rule (backgrounding is named only for the '
        f'non-daemon fallback): {offenders}'
    )


def test_detector_flags_a_prescription_for_a_daemon_routed_build(tmp_path: Path) -> None:
    prescribing = tmp_path / 'prescribing.md'
    prescribing.write_text(
        'To wait for a daemon-routed build, dispatch it with '
        'run_in_background: true and wake on its completion notification.\n',
        encoding='utf-8',
    )

    assert _prescribes_background_for_daemon_routed_build(prescribing.read_text(encoding='utf-8')) is True, (
        'The detector did not fire on a synthetic prescription, so the sweep '
        'above would report a clean agreement no matter what the docs say'
    )


def test_detector_stays_silent_on_the_rule_sentence() -> None:
    assert _prescribes_background_for_daemon_routed_build(_ONE_RUNNABLE_RULE) is False, (
        'The detector fires on the canonical rule sentence itself, so every '
        'correctly-written agreement document would be reported as an offender'
    )


def test_detector_stays_silent_on_a_prohibition_and_a_wait_class_detach() -> None:
    prohibition = (
        'Do NOT `run_in_background` or `sleep` the daemon `wait` — a reaped '
        'wait is recovered by re-issuing `wait`, not by backgrounding it.'
    )
    wait_class_detach = (
        'Run the CI-wait handler with the Claude background primitive — the '
        'Bash `run_in_background: true` parameter — so the orchestrator does '
        'NOT block on it.'
    )

    assert _prescribes_background_for_daemon_routed_build(prohibition) is False, (
        'The detector fires on an explicit prohibition, so a document that '
        'forbids backgrounding the daemon wait would be reported as an offender'
    )
    assert _prescribes_background_for_daemon_routed_build(wait_class_detach) is False, (
        'The detector fires on the wait-class detach, so the legitimate '
        'remote-CI consumer would be reported as an offender'
    )
