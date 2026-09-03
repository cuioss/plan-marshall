#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The resident server survives a bad frame, and never presents a guess as exact.

Four defects, each of which made the surface answer confidently without an
answer:

* **one bad request killed it.** ``handle`` called its handler with no guard and
  ``serve`` wrapped nothing, while ``cmd_serve`` ran under ``@safe_main``, whose
  contract is TOON-on-stdout — correct for a verb, fatal for a protocol channel.
  The process exited 1 mid-session and appended ``status: error`` to the byte
  stream a client was still parsing as frames.
* **``on_references`` discarded the ``verified`` flag**, so a site the index
  could not confirm reached an editor as an exact ``Location`` — which two
  shipped pages promise, in near-identical words, never happens.
* **``resolve_reference_site`` took the first matching candidate**, in
  ``sorted(rglob)`` order, with no ranking and no ambiguity signal, so a decoy
  line in an unrelated file could win over the true citation and be reported
  ``verified``.
* **``initialize`` ignored its params entirely**, so the documented editor block
  — the configuration most likely to omit ``--project-path`` — silently resolved
  the project to the client's cwd and looked exactly like a deliberate opt-out.

The first, second and fourth are driven through a **running server subprocess**,
because the protocol projection is thinner than the index beneath it and an
in-process call cannot see the framing, the process exit, or whether a withheld
count survived serialisation. The third is an index-level property and is
asserted there.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# PLAIN import, deliberately — matching ``test_corpus_index.py``: only a plain
# import gives mypy the real module, and the name must be bound the same way in
# both suites or the loader would register a copy beside the plainly-imported one.
import _corpus_index as corpus_index
import pytest

from conftest import get_script_path, get_scripts_dir, load_script_module

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-corpus-language-server')

corpus_lsp = load_script_module(
    'pm-plugin-development', 'tools-corpus-language-server', 'corpus_lsp.py'
)

SCRIPT = get_script_path('pm-plugin-development', 'tools-corpus-language-server', 'corpus_lsp.py')

PLUGIN_JSON = '{"name": "%s", "version": "0.1", "skills": []}'
ENABLED = {'code_intelligence': {'corpus_language_server': {'enabled': True}}}

# A URI whose path contains a NUL byte. `Path.read_text` raises ValueError on it,
# which the position resolver's `except (OSError, UnicodeDecodeError)` does not
# catch — the proved trigger. Any handler exception has the same shape.
NULL_BYTE_URI = 'file:///tmp/a%00b.md'


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _framed(payload: dict) -> bytes:
    body = json.dumps(payload).encode('utf-8')
    return b'Content-Length: %d\r\n\r\n' % len(body) + body


def _messages(stdout: bytes) -> list[dict]:
    """Split a framed byte stream into messages, refusing anything unframed.

    The point of the split is that it is STRICT: the defect under test appended
    non-frame bytes to this stream, and a lenient reader that skipped to the next
    `Content-Length` would hide exactly that.
    """
    out: list[dict] = []
    rest = stdout
    while rest:
        if not rest.startswith(b'Content-Length: '):
            raise AssertionError(f'stdout carries non-frame bytes: {rest[:120]!r}')
        header, _, remainder = rest.partition(b'\r\n\r\n')
        length = int(header.split(b':', 1)[1].strip())
        out.append(json.loads(remainder[:length]))
        rest = remainder[length:]
    return out


def _project(root: Path, marshal: dict | None = ENABLED) -> Path:
    (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    if marshal is not None:
        _write(root / '.plan' / 'marshal.json', json.dumps(marshal))
    return root


def _serve(project_path: Path | None, frames: bytes, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    """Spawn `serve` as a client does — no PYTHONPATH — and feed it ``frames``."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    argv = [sys.executable, str(SCRIPT), 'serve']
    if project_path is not None:
        argv += ['--project-path', str(project_path)]
    return subprocess.run(argv, input=frames, capture_output=True, env=env, cwd=cwd, timeout=180)


# =============================================================================
# (a) One bad request must not end the session or corrupt the stream
# =============================================================================


def test_a_handler_exception_is_answered_and_the_session_continues(tmp_path):
    """initialize -> a request that raises -> initialize again, all three answered."""
    project = _project(tmp_path)
    frames = (
        _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        + _framed({
            'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition',
            'params': {'textDocument': {'uri': NULL_BYTE_URI}, 'position': {'line': 0, 'character': 0}},
        })
        + _framed({'jsonrpc': '2.0', 'id': 3, 'method': 'initialize', 'params': {}})
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(project, frames)

    assert result.returncode == 0, f'the session died: rc={result.returncode} stderr={result.stderr.decode()}'
    messages = _messages(result.stdout)  # raises if any non-frame byte reached stdout
    by_id = {message.get('id'): message for message in messages}
    assert 1 in by_id and 'result' in by_id[1]
    assert 2 in by_id, f'the bad request was never answered: {messages}'
    assert by_id[2]['error']['code'] == -32603
    assert 3 in by_id and 'result' in by_id[3], 'the request AFTER the bad one must be answered normally'


def test_a_contained_exception_is_reported_on_stderr(tmp_path):
    """Swallowing the exception must not also swallow the evidence."""
    project = _project(tmp_path)
    frames = (
        _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        + _framed({
            'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition',
            'params': {'textDocument': {'uri': NULL_BYTE_URI}, 'position': {'line': 0, 'character': 0}},
        })
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(project, frames)

    assert b'corpus-lsp' in result.stderr
    assert b'textDocument/definition' in result.stderr


# -- the FRAMING layer, which is a separate boundary from the handler ---------

# Each entry is (label, raw bytes, whether the stream stays frame-aligned).
# A frame whose declared body was read whole leaves the reader on a boundary and
# the session can skip it; one whose LENGTH was unusable does not, and the
# session must end — but audibly.
_RECOVERABLE_FRAMES = [
    ('bad-json', b'Content-Length: 7\r\n\r\n{"a":,}', True),
    ('not-an-object', b'Content-Length: 9\r\n\r\n[1, 2, 3]', True),
    ('bad-utf8', b'Content-Length: 4\r\n\r\n\xff\xfe\xfd\xfc', True),
]
_UNRECOVERABLE_FRAMES = [
    ('negative-length', b'Content-Length: -1\r\n\r\n{}', False),
    ('non-integer-length', b'Content-Length: abc\r\n\r\n{}', False),
    ('no-length-header', b'X-Other: 1\r\n\r\n{}', False),
    ('short-body', b'Content-Length: 99\r\n\r\n{"a":1}', False),
]


@pytest.mark.parametrize(('label', 'raw'), [(label, raw) for label, raw, _ in _RECOVERABLE_FRAMES])
def test_a_recoverable_bad_frame_is_skipped_and_the_session_continues(tmp_path, label, raw):
    """The declared body was read whole, so the next read starts on a boundary.

    This is the deliverable's own title clause — *survives a bad frame* — and it
    was false for every frame shape until this guard existed: `read_message`
    returned ``None`` for a malformed frame exactly as it does at end of stream,
    and the loop reads ``None`` as "the client is gone". A single junk frame
    ended a resident session, and stderr said nothing at all.
    """
    project = _project(tmp_path)
    frames = (
        _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        + raw
        + _framed({'jsonrpc': '2.0', 'id': 9, 'method': 'initialize', 'params': {}})
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(project, frames)

    assert result.returncode == 0
    answered = {message.get('id') for message in _messages(result.stdout)}
    assert 1 in answered
    assert 9 in answered, f'{label}: the request AFTER the bad frame was never answered'
    assert b'malformed frame' in result.stderr, f'{label}: the skip was silent'


@pytest.mark.parametrize(('label', 'raw'), [(label, raw) for label, raw, _ in _UNRECOVERABLE_FRAMES])
def test_an_unrecoverable_bad_frame_ends_the_session_AUDIBLY(tmp_path, label, raw):
    """The length was unusable, so nobody knows where the next frame begins.

    Ending is correct here — resynchronising on arbitrary bytes is worse. What
    must not happen is ending the way end-of-stream ends, because an operator
    then sees a client that hung up rather than a client that sent something
    unparseable. stderr is the only channel that can carry the difference:
    stdout is the protocol.
    """
    project = _project(tmp_path)
    frames = (
        _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        + raw
        + _framed({'jsonrpc': '2.0', 'id': 9, 'method': 'initialize', 'params': {}})
    )

    result = _serve(project, frames)

    answered = {message.get('id') for message in _messages(result.stdout)}
    assert 1 in answered, f'{label}: the frame BEFORE the bad one must still be answered'
    assert b'malformed frame' in result.stderr, f'{label}: the session died silently'
    assert 9 not in answered, (
        f'{label}: the session continued past a frame whose length was unusable, '
        'so the reader resynchronised on bytes it cannot vouch for'
    )
    # ⛔ The half the test NAME advertises — that the session ENDS — pinned by
    # the one thing that distinguishes ending from carrying on here. A loop that
    # kept going would stumble through the remaining desynchronised bytes and
    # log a *further* malformed frame for each stumble; ending logs exactly one.
    # Without this the guard passes either way, because a desynchronised reader
    # fails to answer the next request whether it stopped or not.
    assert result.stderr.count(b'malformed frame') == 1, (
        f'{label}: expected exactly one malformed-frame line (the session ends there), '
        f'got {result.stderr.count(b"malformed frame")}'
    )


def test_a_clean_end_of_stream_is_not_reported_as_a_bad_frame(tmp_path):
    """The control that keeps the guard above honest.

    A client closing its end is the ordinary way a session finishes. If EOF
    started logging "malformed frame" the two would be conflated again, just in
    the opposite direction, and the stderr signal would mean nothing.
    """
    project = _project(tmp_path)
    frames = _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})

    result = _serve(project, frames)

    assert result.returncode == 0
    assert b'malformed frame' not in result.stderr


def test_a_failing_notification_is_swallowed_without_a_response(tmp_path):
    """A notification has no id, so there is nobody to answer — but the loop lives."""
    project = _project(tmp_path)
    frames = (
        _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        + _framed({'jsonrpc': '2.0', 'method': 'textDocument/didOpen', 'params': ['not', 'a', 'dict']})
        + _framed({'jsonrpc': '2.0', 'id': 2, 'method': 'initialize', 'params': {}})
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(project, frames)

    assert result.returncode == 0
    identifiers = [message.get('id') for message in _messages(result.stdout)]
    assert identifiers == [1, 2]


# =============================================================================
# (d) initialize adopts the client's declared root
# =============================================================================


def test_serve_without_project_path_adopts_the_client_root(tmp_path):
    """The documented editor block omits --project-path; its failure was silent."""
    project = _project(tmp_path / 'project')
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    frames = (
        _framed({
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'rootUri': project.resolve().as_uri()},
        })
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(None, frames, cwd=elsewhere)

    assert result.returncode == 0, result.stderr.decode()
    capabilities = _messages(result.stdout)[0]['result']['capabilities']
    assert capabilities['definitionProvider'] is True
    assert capabilities['referencesProvider'] is True
    assert capabilities['hoverProvider'] is True


def test_an_explicit_project_path_still_wins_over_root_uri(tmp_path):
    """The documented block's behaviour is unchanged for anyone who passes the flag."""
    configured = _project(tmp_path / 'configured', marshal=None)  # NOT enabled
    other = _project(tmp_path / 'other')  # enabled
    frames = (
        _framed({
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'rootUri': other.resolve().as_uri()},
        })
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(configured, frames)

    assert _messages(result.stdout)[0]['result']['capabilities'] == {}


def test_client_root_is_read_from_each_declared_form(tmp_path):
    """rootUri, then the deprecated rootPath, then workspaceFolders[0]."""
    target = tmp_path / 'ws'
    target.mkdir()
    uri = target.resolve().as_uri()
    assert corpus_lsp.client_root_from({'rootUri': uri}) == target.resolve()
    assert corpus_lsp.client_root_from({'rootPath': str(target)}) == target
    assert corpus_lsp.client_root_from({'workspaceFolders': [{'uri': uri}]}) == target.resolve()
    assert corpus_lsp.client_root_from({}) is None


# =============================================================================
# (c) A decoy line must not win over the true citation
# =============================================================================


def _decoy_corpus(root: Path) -> Path:
    """Two candidate files matching at the same line — one truly, one by accident.

    ``step.md`` cites the target at line 5 with the FULL notation. ``notes.md``
    happens to contain the target's tail segment as an ordinary word at line 5,
    and sorts before ``step.md``. Taking the first match therefore reported the
    decoy, ``verified: True``.
    """
    base = root / 'bundles'
    _write(base / 'alpha' / '.claude-plugin' / 'plugin.json', PLUGIN_JSON % 'alpha')
    _write(
        base / 'alpha' / 'skills' / 'target-skill' / 'SKILL.md',
        '---\nname: target-skill\ndescription: The skill under test\nmode: knowledge\n---\n\n# Target\n',
    )
    _write(base / 'alpha' / 'skills' / 'target-skill' / 'scripts' / 'target_script.py', '# target\n')

    _write(base / 'beta' / '.claude-plugin' / 'plugin.json', PLUGIN_JSON % 'beta')
    _write(
        base / 'beta' / 'skills' / 'caller' / 'SKILL.md',
        '---\nname: caller\ndescription: References the target\n---\n\n# Caller\n',
    )
    _write(
        base / 'beta' / 'skills' / 'caller' / 'aaa-notes.md',
        '# Notes\n\nfiller\nfiller\nThe target_script step is described elsewhere.\n',
    )
    _write(
        base / 'beta' / 'skills' / 'caller' / 'step.md',
        '# Step\n\nfiller\nfiller\nRun `alpha:target-skill:target_script` here.\n',
    )
    return base


def test_the_full_notation_outranks_a_tail_only_decoy(tmp_path):
    """A decoy sorting first must not win: the full notation is the stronger match."""
    index = corpus_index.CorpusIndex(_decoy_corpus(tmp_path))

    references = index.references('alpha:target-skill:target_script')

    assert references, 'the fixture produced no inbound edge; re-derive it before trusting this test'
    sites = {(ref.location.path.name, ref.verified) for ref in references}
    assert ('aaa-notes.md', True) not in sites, f'the decoy won: {sites}'
    assert any(name == 'step.md' and verified for name, verified in sites), sites


def test_two_equally_ranked_candidates_are_reported_unverified(tmp_path):
    """No file ordering makes one of them right, so the tie is reported, not broken."""
    base = _decoy_corpus(tmp_path)
    # A SECOND file carrying the full notation at the same line — now two
    # candidates match at the top rank.
    _write(
        base / 'beta' / 'skills' / 'caller' / 'also-step.md',
        '# Also\n\nfiller\nfiller\nRun `alpha:target-skill:target_script` here too.\n',
    )
    index = corpus_index.CorpusIndex(base)

    references = index.references('alpha:target-skill:target_script')

    assert references
    for ref in references:
        assert ref.verified is False, f'an ambiguous site was reported as exact: {ref.location.path}'
        assert ref.location.path.name == 'SKILL.md', 'an unconfirmed site is reported against the owner'


# =============================================================================
# (b) Unverified sites are omitted from textDocument/references, and counted
# =============================================================================


def _project_with_corpus(tmp_path: Path) -> Path:
    """A real enabled project whose corpus yields at least one UNVERIFIED site."""
    project = tmp_path / 'project'
    base = _unverified_corpus(project)
    _write(
        project / '.plan' / 'marshal.json',
        json.dumps({'code_intelligence': {'corpus_language_server': {
            'enabled': True, 'corpus_path': str(base.relative_to(project)),
        }}}),
    )
    return project


def _server_over(corpus_base: Path, project_root: Path):
    """A CorpusLanguageServer pointed at ``corpus_base``, with notify captured."""
    config = {'enabled': True, 'corpus_path': str(corpus_base.relative_to(project_root))}
    server = corpus_lsp.CorpusLanguageServer(project_root, config)
    sent: list[tuple[str, dict]] = []
    server.notify = lambda method, params: sent.append((method, params))
    return server, sent


_UNVERIFIED_NOTATION = 'alpha:target-skill:target_script'


def _unverified_corpus(root: Path) -> Path:
    """A corpus whose inbound edges cannot be confirmed — two candidates tie.

    The tie is the reachable unverified state after ranking landed: two files
    carry the full notation at the same line number, so no ordering makes either
    of them the right answer and the site is reported against the owner,
    unverified. The route matters to the fixture, not to what is asserted — the
    tests below check the *precondition* explicitly rather than assuming it.
    """
    base = _decoy_corpus(root)
    _write(
        base / 'beta' / 'skills' / 'caller' / 'also-step.md',
        '# Also\n\nfiller\nfiller\nRun `alpha:target-skill:target_script` here too.\n',
    )
    return base


def test_an_unverified_site_is_omitted_from_the_references_response(tmp_path):
    project = _project(tmp_path)
    base = _unverified_corpus(tmp_path)
    index = corpus_index.CorpusIndex(base)
    every_site = index.references(_UNVERIFIED_NOTATION)
    assert every_site, 'the fixture produced no inbound edge'
    unverified = [ref for ref in every_site if not ref.verified]
    assert unverified, f'the fixture produced no UNVERIFIED site: {[(r.location.path.name, r.verified) for r in every_site]}'

    server, sent = _server_over(base, project)
    document = _write(tmp_path / 'doc.md', 'Run `alpha:target-skill:target_script` here.\n')
    params = {
        'textDocument': {'uri': document.resolve().as_uri()},
        'position': {'line': 0, 'character': 8},
    }

    locations = server.on_references(params)

    assert len(locations) == len(every_site) - len(unverified)
    assert server.last_omitted_unverified == len(unverified)
    # The count travels with the answer even when the list is empty — a bare
    # empty result would be the silent signal the omission was meant to avoid.
    log_messages = [params for method, params in sent if method == 'window/logMessage']
    assert log_messages, f'sites were withheld with no report: {sent}'
    assert str(len(unverified)) in log_messages[0]['message']


def test_a_confirmed_site_is_returned_and_carries_the_omitted_count(tmp_path):
    """The control: filtering must not have made the verb answer nothing."""
    project = _project(tmp_path)
    base = _decoy_corpus(tmp_path)
    server, _sent = _server_over(base, project)
    document = _write(tmp_path / 'doc.md', 'Run `alpha:target-skill:target_script` here.\n')
    params = {
        'textDocument': {'uri': document.resolve().as_uri()},
        'position': {'line': 0, 'character': 8},
    }

    locations = server.on_references(params)

    assert locations, 'a confirmed site must still be returned'
    for location in locations:
        assert 'omittedUnverifiedCount' in location
        assert location['range']['start']['line'] >= 0


def test_the_query_verb_still_emits_every_site_with_its_flag(tmp_path):
    """The filter is the LSP projection's, not the index's — `query` stays complete.

    Driven through `cmd_query` itself, not through `CorpusIndex`: the constraint
    the plan attaches to omitting sites is about what the **verb** publishes, and
    a test that called the index directly would pass even if `cmd_query` had
    picked up the same filter.
    """
    project = _project_with_corpus(tmp_path)

    payload = corpus_lsp.cmd_query(argparse.Namespace(
        project_path=str(project), kind='references', notation=_UNVERIFIED_NOTATION,
    ))

    assert payload['status'] == 'success'
    assert payload['reference_count'] >= 1
    assert len(payload['references']) == payload['reference_count']
    # Every site is present, each carrying its flag — and at least one is the
    # unverified kind `textDocument/references` withholds.
    assert all('verified' in row for row in payload['references'])
    assert any(row['verified'] is False for row in payload['references'])
    assert payload['verified_count'] < payload['reference_count']


def test_the_running_server_withholds_the_unverified_site_and_says_how_many(tmp_path):
    """D5's clause (b), on the wire — the protocol projection is the thin layer.

    An in-process call cannot see this: the omitted count and the
    `window/logMessage` both have to survive serialisation and framing, and
    `notation_at_position` reads the document map keyed by the client's RAW URI
    while `_lsp_location` emits a resolved one — an assumption only a real
    request exercises.
    """
    project = _project_with_corpus(tmp_path)
    document = _write(project / 'doc.md', 'Run `alpha:target-skill:target_script` here.\n')
    frames = (
        _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        + _framed({
            'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/references',
            'params': {
                'textDocument': {'uri': document.resolve().as_uri()},
                'position': {'line': 0, 'character': 8},
                'context': {'includeDeclaration': True},
            },
        })
        + _framed({'jsonrpc': '2.0', 'method': 'exit'})
    )

    result = _serve(project, frames)

    assert result.returncode == 0, result.stderr.decode()
    messages = _messages(result.stdout)
    responses = {message['id']: message for message in messages if 'id' in message}
    assert responses[2]['result'] == [], f'an unverified site reached the client: {responses[2]}'

    logs = [
        message for message in messages
        if message.get('method') == 'window/logMessage'
    ]
    assert logs, f'every site was withheld with no report on the wire: {messages}'
    assert 'could not be confirmed' in logs[0]['params']['message']
    # The COUNT, not just the fact — an empty list plus a bare notice would still
    # leave the reader unable to tell how much was withheld.
    assert any(character.isdigit() for character in logs[0]['params']['message'])


# =============================================================================
# (e) The staleness bound is stated on the surfaces that claim residency
# =============================================================================

_STALENESS_SURFACES = (
    SCRIPTS_DIR.parent / 'SKILL.md',
    Path(__file__).resolve().parents[3] / 'doc' / 'user' / 'corpus-language-server.adoc',
    SCRIPTS_DIR / 'corpus_lsp.py',
)


def test_every_residency_surface_states_the_staleness_bound():
    """A reader must not take "re-read before it is reported" as "always current"."""
    for surface in _STALENESS_SURFACES:
        text = surface.read_text(encoding='utf-8').lower()
        assert 'stale' in text, f'{surface} claims residency without stating its staleness bound'
        assert 'restart' in text, f'{surface} states the bound without saying how to clear it'
