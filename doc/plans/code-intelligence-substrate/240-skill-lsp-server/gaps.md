# Gaps — 240-skill-lsp-server

The surface ships and works: all six deliverables are present, D4's no-op is reproducible on this
real unconfigured repository, and the versioned-cache bootstrap that round 4 fixed holds up when
driven from a real two-version cache. Driven the way a client drives it, a running `serve` subprocess
answers `definition`, `hover` and `references` correctly from the real corpus.

What remains is **five code defects** (G1, G2, G28, G3, G4 — grouped together below rather than in
numeric order, since the file groups by kind): one a demonstrated crash-plus-stream-corruption of the
resident server, one a documented provenance contract that holds on the `query` verb but is silently
dropped on the LSP surface. Then a mutation-proven vacuous test pair, four
uncovered paths, and a family of stale D3 justifications created by `230-validate-precision` landing
on `main` 74 minutes **before** this plan merged: every artifact that explains why diagnostics are
withheld still names an unexecuted gate and a 380/97 % measurement that is now 61 of 5 081.

## G1 — Put an exception boundary around JSON-RPC dispatch and stop `serve` writing TOON to stdout

- **Kind:** bug
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/_corpus_lsp_protocol.py:143`
  (`LspServer.handle`) and `:148-158` (`LspServer.serve`); entry point
  `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/corpus_lsp.py:481-485`
  (`cmd_serve`) via `@safe_main` at `:530`
- **Evidence:** `handle()` calls `result = handler(params)` with no `try`, and `serve()` wraps
  nothing. Driving the real script as a client does (no `PYTHONPATH`) with
  `initialize`, then `textDocument/definition` on `uri: file:///tmp/a%00b.md`, then a second
  `initialize`: process exits **1**, the second `initialize` is never answered, and stdout ends
  `…"hoverProvider": true, "textDocumentSync": 1}}}status: error\nerror: internal_error\nmessage: embedded null byte\n`.
  The trigger is `Path.read_text` raising `ValueError` at `corpus_lsp.py:298`, whose `except` clause
  (`:299`) catches only `OSError` and `UnicodeDecodeError`. `safe_main`'s contract is TOON-on-stdout
  (`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py:1664-1676`) — correct
  for a verb, fatal for a stdio protocol channel.
- **Why it matters:** the surface's entire justification is residency; a resident server that dies on
  one malformed request delivers none of it. Worse, the death emits non-LSP bytes on the frame
  stream, so a client that is still parsing sees garbage rather than a clean EOF. Any handler
  exception has this shape — a corpus directory removed mid-session, an index build failure, an
  unexpected `ValueError` — not just this URI.
- **Action:** wrap the handler call in `LspServer.handle` in `try/except Exception` and return a
  JSON-RPC error response (`code -32603`, InternalError) for a request, or swallow-and-log for a
  notification; wrap the `serve` loop body so one bad frame cannot end the session. Give `serve` its
  own entry path that does **not** go through `@safe_main`, or make the wrapper write to stderr when
  the command is `serve`.
- **Done when:** the probe above returns a JSON-RPC error object for id 2, answers id 3 normally, and
  exits 0; a test drives that exact sequence as a subprocess and asserts stdout contains only
  `Content-Length`-framed messages.
- **Effort:** S
- **Risk if fixed:** a swallowed exception could hide a real defect — pair the boundary with a stderr
  log line so failures stay visible.

## G2 — Disambiguate the reference site instead of taking the first candidate that matches

- **Kind:** bug
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/_corpus_index.py:233-236`
  (`CorpusIndex.resolve_reference_site`)
- **Evidence:** the loop returns the first candidate file whose line at the cited number contains any
  `expected_tokens` entry, owner-file first, then `sorted(rglob)` order — no tie-break, no ambiguity
  signal. Reproduced on a synthetic corpus: with a decoy line `prose about target_script, unrelated`
  at line 5 of `beta/skills/caller/SKILL.md` and the true citation at line 5 of
  `workflow/step.md`, the answer is `SKILL.md`, `verified=True`. Scanned the real corpus using the
  resolver's own candidate order and token test, all figures from one process: the corpus returns
  **5 020 reference sites**, of which **4 858 are `verified: true`**; **296 of those 4 858 (6.1 %)**
  have more than one candidate matching at that line, so at most one of each is correct; **1 331
  (27 %)** win on the tail segment alone rather than the full notation.
- **Why it matters:** `SKILL.md:118-121` and `doc/user/corpus-language-server.adoc:182` present
  `verified: true` as *"an exact location"*. A confidently wrong jump target is precisely the failure
  class D3 is gated to avoid, shipped through a different door.
- **Action:** rank candidates rather than taking the first — prefer a line carrying the **full
  notation** over one carrying only the tail; when two or more candidates tie, either report the
  owner file with `verified: false` or add an `ambiguous: true` field to the reference payload and
  document it.
- **Done when:** the synthetic decoy corpus above resolves to `workflow/step.md` (or reports the
  site unverified/ambiguous), a test pins it, and a re-run of the corpus scan reports zero
  `verified: true` sites with more than one full-notation match.
- **Effort:** M
- **Risk if fixed:** some currently-`verified` sites become unverified, lowering the headline
  verified count; that is the honest direction.

## G28 — Stop presenting unverified reference sites to an editor as exact locations

- **Kind:** bug
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/corpus_lsp.py:321-328`
  (`CorpusLanguageServer.on_references`) and `:343-351` (`_lsp_location`)
- **Evidence:** `on_references` maps every `Reference` through
  `_lsp_location(ref.location.path, ref.location.line)`, which emits only `uri` and `range`. The
  `verified` flag that `resolve_reference_site` computed is discarded, so a site the index itself
  could not confirm is delivered to the client as an ordinary LSP `Location` — and LSP has no weaker
  form than `Location`. Measured on the real corpus: of **5 020 reference sites, 162 (3.2 %) are
  `verified: false`**, and each is reported against the owner's own file at the cited line, which is
  the wrong-file/wrong-line pairing `resolve_reference_site` exists to avoid. Demonstrated live
  through a running `serve` subprocess: `plan-marshall:manage-architecture` has one unverified inbound
  edge, and the server emits `manage-architecture/SKILL.md` `{"line": 515, "character": 0}`, whose
  text is *"Searches inventoried file **bodies** and reports the module-attributed files containing
  `--pattern`…"* — a line that never mentions the target. The `query` verb does carry `verified` in
  its payload; only the protocol projection loses it.
- **Why it matters:** two shipped pages promise exactly the opposite, in near-identical words.
  `SKILL.md:121` — *"Reported against the owner's file, and **never presented as exact**"*; and
  `doc/user/corpus-language-server.adoc:182` — *"one that cannot be confirmed is still shown, but
  never presented as an exact location"*. On the surface this plan actually shipped, every such site
  **is** presented as an exact location. This is a documented contract that is unimplemented on the
  primary surface, which is why it is rated high rather than medium: the flag's whole purpose is to
  keep an unconfirmed site from being trusted, and the editor never learns of it. It is also a
  distinct defect from G2 — G2 is the resolver choosing the wrong candidate among several, this is the
  protocol layer discarding a signal the resolver got right.
- **Action:** pick one and make the documentation match. Either (a) omit `verified: false` sites from
  the `textDocument/references` response — 3.2 % recall for a contract the docs already state — or
  (b) keep emitting them and correct both `SKILL.md:121` and the user page's line 182 to scope the
  "never presented as exact" promise to the `query` payload, stating plainly that the editor surface
  cannot carry the distinction.
- **Done when:** driving a running `serve` over a corpus containing a known-unverified edge either
  returns no `Location` for that edge, or the two documents no longer claim unconfirmed sites are
  never presented as exact; and a test pins whichever behaviour was chosen.
- **Effort:** S
- **Risk if fixed:** option (a) lowers the reference count an editor shows and can hide a site that
  was in fact correct but unconfirmable (a non-positional frontmatter edge, for instance); option (b)
  costs nothing in code but leaves the wrong-line jump in place, so it should be taken only alongside
  G2.

## G3 — Invalidate the index and its caches on document change, or document that answers are snapshot-aged

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/corpus_lsp.py:244-251`
  (`CorpusLanguageServer.index`), `:255-274` (`did_open` / `did_change` / `did_close`);
  `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/_corpus_index.py:150-151`
  (`_line_cache`, `_candidate_cache`)
- **Evidence:** `self._index` is built once and never cleared; the two caches only grow; the three
  sync handlers touch only `self.documents`. Nothing in either module resets any of them. The
  proposal lists "incremental re-index on change" under Option A's costs
  (`proposal-protocol-surface.md:175`) — it was not built and no shipped page says so.
- **Why it matters:** in a long-lived editor session every `definition` / `references` / `hover`
  answer after the first file edit is computed against a stale snapshot, and
  `SKILL.md:108` ("every reference site is re-read before it is reported") is true only for the first
  read of each file per process. A newly created sub-document is invisible for the server's lifetime.
- **Action:** either (a) drop `_line_cache[path]` and `_candidate_cache[owner]` on
  `textDocument/didChange` / `didSave` for the affected path and rebuild the index on a debounce, or
  (b) if that is deferred, state the bound explicitly in `SKILL.md`, the user page and the module
  docstring, next to the residency claim they sit beside.
- **Done when:** a test opens a corpus, queries a reference, edits the cited file through
  `didChange`, re-queries and gets the post-edit answer — or, for option (b), each of the three named
  documents carries the staleness bound and a test asserts the phrase is present.
- **Effort:** M
- **Risk if fixed:** rebuilding the index costs ~2.5 s; a naive invalidation on every keystroke would
  destroy the interactivity residency bought. Debounce and scope invalidation to the edited path.

## G4 — Honour `initialize.rootUri` when `--project-path` was not given

- **Kind:** omission
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/corpus_lsp.py:380`
  (the `initialize` handler) and `:493-495` (`--project-path`, default `.`)
- **Evidence:** the `initialize` lambda ignores its `params` entirely; the project root comes only
  from `--project-path`, defaulting to the client's cwd. `SKILL.md:209-211` and the user page
  acknowledge the consequence: *"a cwd outside the project yields empty capabilities that are
  indistinguishable from a deliberate opt-out"*, and mitigate it with documentation only.
- **Why it matters:** the Form 2 (Neovim / VS Code / Emacs) config an operator is told to write is
  the one most likely to omit the flag, and the failure is silent and looks exactly like opt-out.
  LSP already carries the answer in the handshake.
- **Action:** in the `initialize` handler, when the CLI project path resolved to nothing, resolve the
  project from `params['rootUri']` (falling back to `rootPath`, then `workspaceFolders[0].uri`) and
  rebuild the config/corpus resolution before returning capabilities.
- **Done when:** a subprocess test spawns `serve` with cwd outside the project and **no**
  `--project-path`, sends `initialize` with `rootUri` pointing at an enabled project, and receives
  the three providers.
- **Effort:** M
- **Risk if fixed:** capabilities must then be computed after params are read — keep the explicit
  `--project-path` winning over `rootUri` so the documented block's behaviour is unchanged.

## G5 — Make the candidate-walk cache tests non-vacuous

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/pm-plugin-development/tools-corpus-language-server/test_corpus_index.py:219-253`
  (`TestCandidateFilesAreCached`)
- **Evidence:** deleting the cache **read** in `_corpus_index.py:252-254` (so the directory walk runs
  once per reverse edge again — exactly report finding #4's regression) leaves **all 78 tests
  green**. Both tests only observe that `_candidate_cache` gets *written*: `test_repeat_calls_reuse_the_walk`
  compares the dict to itself, and `test_walk_runs_once_per_owner_not_once_per_edge` derives `walked`
  from `index._candidate_cache.get(owner) is not None` — i.e. from what the cache *contains*, not from
  whether it was *read* — so `len(walked) < len(calls)` holds for any input with a repeated owner.
  (Deleting the cache write as well would leave `walked` empty and `0 < len(calls)` passing too, so
  neither half of the cache is guarded.)
- **Why it matters:** finding #4 was a high-severity performance defect (~125 ms per `references`
  call, unchanged on repeat, defeating residency). Its fix has no guard, so it can silently regress.
- **Action:** count actual filesystem walks — monkeypatch `Path.rglob` or wrap `_candidate_files`'s
  body — and assert the walk executes **once** across two `references()` calls on the same owner.
- **Done when:** deleting the `cached is not None` early return in `_candidate_files` turns
  `test_corpus_index.py` red.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Make `test_negative_content_length_does_not_consume_the_stream` test what it claims

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/pm-plugin-development/tools-corpus-language-server/test_corpus_lsp_protocol.py:53-57`
- **Evidence:** the docstring says *"The next frame must still be readable after a rejected negative
  one"*, but the body builds `good` and never reads it — the only assertion is that the first read is
  `None`. Confirmed by mutation: with the `parsed < 0` guard deleted, this test still passes while the
  stream *is* consumed to EOF (only its sibling `test_negative_content_length_yields_none` goes red).
- **Why it matters:** the sibling test happens to cover the guard, so the defect is currently
  masked — but the test that names the stream-position property does not check it, and would not
  catch a future variant that rejects the frame after consuming it.
- **Action:** after the first `read_message(stream)` returns `None`, call `read_message(stream)` again
  and assert it returns the `shutdown` message.
- **Done when:** the added assertion fails if `read_message` consumes the stream before rejecting.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Cover the enabled `query` and `preflight` verbs

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/pm-plugin-development/tools-corpus-language-server/test_corpus_lsp_optin.py:126-141`
  (the only `cmd_preflight` / `cmd_query` tests, both on the disabled path); production
  `corpus_lsp.py:401-478`
- **Evidence:** a repo-wide grep for `cmd_query` finds one call in this suite, inside
  `test_query_degrades_without_touching_the_corpus`. Nothing exercises `state: ok`, the
  `definition` / `references` / `hover` payload shapes, `reference_count`, `verified_count`,
  `completeness_note`, or `preflight`'s `state: ready` + `stats()` branch.
- **Why it matters:** the run report designates `query` as the surface's **only reachable consumer**
  ("`query` is reachable without a client"). The payload contract three shipped documents describe is
  unpinned; any refactor can rename a key silently.
- **Action:** add tests over the existing synthetic corpus fixture (`build_corpus`) that call
  `cmd_preflight` and `cmd_query` with an enabled config and assert the documented keys, including
  `verified_count` and `completeness_note`.
- **Done when:** renaming any key in `cmd_query`'s payload turns the suite red.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Cover the `corpus_path` field and the missing-corpus branch

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** production `corpus_lsp.py:198-207` (`resolve_corpus_path`), `:413-422` and `:446-454`
  (the `configured corpus path does not exist` branches); no test sets `corpus_path`
- **Evidence:** grep for `corpus_path` across `test/` returns no hit. The field is documented in
  `SKILL.md:70`, `doc/user/corpus-language-server.adoc:65-67` and `data-model.md` § code_intelligence.
- **Why it matters:** a documented configuration field with a documented degradation state has no
  executable guard, and the degradation state (`configured: true` + `state: not_configured` +
  `reason`) is a contract consumers are told to branch on.
- **Action:** add two tests — a custom relative `corpus_path` that resolves and answers, and a
  configured path that does not exist yielding `degraded` / `not_configured` / the `reason` string.
- **Done when:** both branches are executed by the suite.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Cover `didChange` / `didClose` and the synced-buffer resolution path

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** production `corpus_lsp.py:261-274` (`did_change`, `did_close`) and `:292` (the
  `self.documents` branch of `notation_at_position`)
- **Evidence:** no test calls `did_open`, `did_change` or `did_close`; every existing test relies on
  the file-read fallback, so `self.documents` is never populated and the synced-text branch never
  runs.
- **Why it matters:** `textDocumentSync: 1` is advertised in the capability set, so a client will
  send these notifications; an unsynced or mis-synced buffer means the cursor token is resolved
  against on-disk text an editor has already changed.
- **Action:** add tests that `didOpen` a buffer whose text differs from disk, assert the notation is
  resolved from the buffer, then `didChange` and `didClose` and assert the fallback resumes.
- **Done when:** the three handlers and the `self.documents` branch are executed by the suite.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Re-evaluate D3 now that its hard gate has landed

- **Kind:** omission
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/_corpus_lsp_protocol.py:92-105`
  (`active_capabilities`, no diagnostic provider); gate plan
  `doc/plans/code-intelligence-substrate/230-validate-precision/`
- **Evidence:** `230-validate-precision` executed — its `report-01.md` exists and its landing commit
  `3d96e40` is dated **2026-08-16T08:54:13Z**, 74 minutes before this plan's `5edca5a` (10:08:21Z).
  Re-derived on this tree with pristine `HEAD` copies of the validator: **61 unresolved of 5 081
  dependencies over 308 components**, against the 380–381 the gate reasoning was built on.
- **Why it matters:** D3 is the one deliverable this plan left unbuilt, and its residue entry names a
  blocker that no longer exists. ⭐ **The premise has not merely drifted — it has inverted.** Tallying
  the current 61 rows by target:
  - **25 (41 %) are not notations at all** — `lint:js:fix` ×9, `lint:style:fix` ×6,
    `project:core:compile` ×3, `YYYY-MM-DDTHH:MM:SSZ` ×2, `css:lint:fix`, `css:format:check`,
    `HH:mm:ss`, `trivy:ignore:CVE-2024-XXXX`, and the truncated fragment `plan-marshall:recipe-`.
  - **36 (59 %) are well-formed notations whose target does not exist** — `plan-marshall:extension-api:extension_base`
    ×11 (the file is `extension_api.py`; there is no `extension_base.py`),
    `pm-plugin-development:plugin-doctor:{validate,fix,analyze}` ×13 (no such scripts; these look like
    verb names), `plan-marshall:tools-integration-ci:{github,gitlab}`, `pm-dev-java:build-maven:maven`,
    `pm-plugin-development:README.md`, and ten others.

  So the false-positive share the whole deferral rests on has fallen from the claimed ~97 % to at
  most ~41 %, and the majority of what remains now looks like genuinely broken or stale references —
  exactly the class diagnostics exist to surface. **The decision should be presumed to need
  reversing, not upholding**, which is the opposite of what every shipped artifact currently implies.
- **Action:** confirm the classification above against the live validator, decide whether the
  residual false-positive share clears the bar for editor diagnostics, and either implement D3
  (advertise `diagnosticProvider`, stream the validator's set) or record the re-taken decision with
  the new measurement and the reason a 41 % non-reference share is still too high.
- **Done when:** a document in this plan directory or its successor states the current unresolved
  count, its classification, and the diagnostics decision derived from it.
- **Effort:** M
- **Risk if fixed:** advertising diagnostics binds the surface to the validator's precision; a later
  regression there becomes visible squiggles.

## G11 — Correct the D3 figures on the user page

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/user/corpus-language-server.adoc:190`
- **Evidence:** *"The underlying validator reports roughly 380 unresolved references across a corpus
  of about 5,300, and close to 97% of them are not broken references at all"*. Measured now:
  **61 unresolved of 5 081** (validator run twice, second time with pristine `HEAD` scripts).
- **Why it matters:** this is the operator-facing justification for a missing capability, and it is
  wrong by roughly 6× in the numerator. The run deliberately restated these as ranges to survive
  drift; the range no longer contains the value.
- **Action:** re-derive and restate, or replace the figures with a pointer to the validator command so
  the reader measures it themselves.
- **Done when:** the sentence's numbers match a fresh `resolve-dependencies validate --scope marketplace`
  run, or name no number.
- **Effort:** S
- **Risk if fixed:** the figure drifts again; prefer the "run this command" form.

## G12 — Correct the "about 97% false positives" claim on the developer page

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/developer/corpus-language-server-protocol.adoc:92` (§ "Two constraints the decision
  carries forward" → *Diagnostics stay withheld*)
- **Evidence:** *"The validator's unresolved set is presently about 97% false positives"*. The set is
  now 61 rows, not ~380, and the precision work that changed it landed before this page did.
- **Why it matters:** this page is the decision record future work is told not to re-litigate from
  scratch; a superseded measurement in it propagates the wrong premise.
- **Action:** restate against the current set, and note that `230-validate-precision` has since
  landed so the constraint is a live question rather than a settled one (see G10).
- **Done when:** the paragraph names the current count or names none, and references the executed
  gate plan.
- **Effort:** S
- **Risk if fixed:** none.

## G13 — Correct the diagnostics paragraph on the concepts page

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/concepts/code-intelligence.adoc:286` (§ "The bound it inherits, and the one thing it
  withholds", which opens at `:282`) — *"The corpus validator's unresolved set is presently dominated
  by references that are not broken at all"*
- **Evidence:** qualitative rather than numeric, so less wrong than G11/G12 — but "presently" now
  describes a 61-row set produced by a validator whose precision work has landed, and the sentence's
  examples ("build-command and Maven coordinates borrowed into prose") describe the pre-precision
  partition.
- **Why it matters:** it is the third shipped statement of the same superseded premise; leaving it
  keeps the tier-model page out of step with the code.
- **Action:** replace "dominated by references that are not broken at all" with the measured split
  (G10: 25 of 61 non-notations, 36 well-formed notations with an absent target), and drop the
  "build-command and Maven coordinates borrowed into prose" example list, which describes the
  pre-precision partition.
- **Done when:** the paragraph no longer asserts that non-broken references dominate the set, and
  either names the current counts or names none.
- **Effort:** S
- **Risk if fixed:** none.

## G14 — Correct the D3 gate wording in `SKILL.md`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/SKILL.md:123-131`
  (§ "Diagnostics are deliberately absent")
- **Evidence:** *"hard-gated on the validator-precision work: the validator's current unresolved set
  is overwhelmingly false positives"*. That work has landed (`3d96e40`), and the set is 61 rows.
- **Why it matters:** the skill contract is what an agent loads; it states an open gate that is
  closed.
- **Action:** restate the reason for withholding diagnostics against the current set, per G10's
  outcome.
- **Done when:** the section names no unexecuted gate.
- **Effort:** S
- **Risk if fixed:** none.

## G15 — Correct the stale gate justification in `corpus_lsp.py`'s module docstring

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/corpus_lsp.py:25-29`
- **Evidence:** *"hard-gated on the validator-precision work: the validator's current unresolved set
  is overwhelmingly false positives"*.
- **Why it matters:** same superseded premise, in the source a maintainer reads first.
- **Action:** restate with the current measurement or drop the numeric characterisation and
  cross-reference the decision record.
- **Done when:** the docstring names no unexecuted gate.
- **Effort:** S
- **Risk if fixed:** none.

## G16 — Correct the stale gate justification in `active_capabilities()`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/_corpus_lsp_protocol.py:95-99`
- **Evidence:** *"plan 240's D3, hard-gated on the validator-precision work: the validator's current
  unresolved set is overwhelmingly false positives"*.
- **Why it matters:** this docstring sits on the function that decides what is advertised; it is the
  first thing a later implementer of D3 will read.
- **Action:** restate per G10.
- **Done when:** the docstring names no unexecuted gate.
- **Effort:** S
- **Risk if fixed:** none.

## G17 — Add `lspServers` to `plugin_json_gen.py`'s docstring field list

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/targets/claude/plugin_json_gen.py:6-9` (the multi-target generator, not a
  bundle — hence `documentation-surface` rather than `bundle-docs`)
- **Evidence:** the module docstring enumerates the passthrough fields — *"(`name`, `version`,
  `description`, `author`, `license`, `homepage`, `repository`, `keywords`)"* — while
  `PASSTHROUGH_FIELDS` at `:59-69` now also contains `lspServers`, added by this plan.
- **Why it matters:** the docstring is the human-readable statement of the allowlist whose
  silent-drop behaviour this plan spent a blocking finding on; an incomplete list is the same class
  of defect one level up.
- **Action:** add `lspServers` to the enumeration, or replace the inline list with a reference to
  `PASSTHROUGH_FIELDS` so it cannot drift again.
- **Done when:** the docstring and the tuple agree.
- **Effort:** S
- **Risk if fixed:** none.

## G18 — Fix the dangling `../220-resolver-configuration.md` link in the proposal

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/proposal-protocol-surface.md:239`
- **Evidence:** the target does not exist — the plan was executed and is now the directory
  `doc/plans/code-intelligence-substrate/220-resolver-configuration/` holding `plan.md` and
  `report-01.md`.
- **Why it matters:** the sentence is about a coupling constraint; a reader following the link to
  check it lands on nothing.
- **Action:** repoint to `../220-resolver-configuration/plan.md` (or `report-01.md`).
- **Done when:** the link resolves.
- **Effort:** S
- **Risk if fixed:** none.

## G19 — Fix the dangling `../230-validate-precision.md` link in the proposal (line 293)

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/proposal-protocol-surface.md:293`
- **Evidence:** the target does not exist; the plan executed and is now
  `doc/plans/code-intelligence-substrate/230-validate-precision/`.
- **Why it matters:** the link is attached to the claim *"has not been executed"*, which is itself
  false now — fixing the link without fixing the sentence would preserve the wrong statement.
- **Action:** repoint to `../230-validate-precision/plan.md` and correct the surrounding sentence to
  say the gate has since landed (see G10).
- **Done when:** the link resolves and the sentence matches the epic's state.
- **Effort:** S
- **Risk if fixed:** none.

## G20 — Fix the dangling `../230-validate-precision.md` link in the proposal (line 339)

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/proposal-protocol-surface.md:339`
  (§ "Decision (operator, this run)")
- **Evidence:** same dangling target, in the sentence *"its hard gate … has not executed"*.
- **Why it matters:** this is the decision section, the part most likely to be quoted forward.
- **Action:** repoint and correct the claim, as in G19.
- **Done when:** the link resolves and the sentence matches the epic's state.
- **Effort:** S
- **Risk if fixed:** none.

## G21 — Correct the report's "230 is still an unexecuted plan file" claim

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/report-01.md:175` (§ D3 —
  the sentence itself; `:178` opens the measurement table beneath it) and the Residue bullet at
  `:465-467`
- **Evidence:** *"`230-validate-precision.md` is still an unexecuted plan file"*. It executed as
  `3d96e40` on 2026-08-16T08:54:13Z; this plan merged as `5edca5a` at 10:08:21Z.
- **Why it matters:** the report is the record a retrospective reads; it asserts a blocked state that
  was already unblocked on `main` when it merged, which understates what a fifth verification round
  would have caught.
- **Action:** append a correction noting the gate landed before merge and that D3's deferral needs
  re-taking (G10). Do not rewrite history — record the correction.
- **Done when:** the report no longer asserts the gate is unexecuted.
- **Effort:** S
- **Risk if fixed:** none.

## G22 — Correct the report's 381/5 312/97.4 % D3 table

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/report-01.md:178-188`
- **Evidence:** *"381 unresolved edges of 5 312"* with a 371/97.4 % classification. Measured on this
  tree: **61 of 5 081**.
- **Why it matters:** the residue bullet designates 97.4 % as *"the baseline it must improve on"* for
  a future D3 implementation; that baseline was already superseded at merge.
- **Action:** annotate the table with its measurement point and the post-`230` figure.
- **Done when:** the table states the branch it was measured on and the current value alongside.
- **Effort:** S
- **Risk if fixed:** none.

## G23 — Fix the mixed 0-/1-based line numbering in the report's D2 narrative

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/report-01.md:164-166`
- **Evidence:** *"the index cites `beta:caller` `line:5`, where `SKILL.md` line 5 is blank and the
  real citation is `step.md` line 4"* — the first two numbers are 1-based, the third is the 0-based
  index. Reproduced on the fixture: the index cites `line:5`, `SKILL.md` line 5 is blank, and the
  citation is `step.md` line 5 (1-based) = `location.line == 4`.
- **Why it matters:** the whole design finding is about an off-by-file/off-by-line confusion; stating
  it in two unit systems in one sentence invites the reader to repeat it.
- **Action:** state both in 1-based file terms, or mark the 0-based value as `location.line`.
- **Done when:** the sentence uses one convention.
- **Effort:** S
- **Risk if fixed:** none.

## G24 — Fix `_lsp_location`'s docstring, which describes a range it does not emit

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/corpus_lsp.py:343-351`
- **Evidence:** the docstring reads *"An LSP Location covering the whole line"*, but the range is
  `start: {line, character: 0}`, `end: {line, character: 0}` — zero width at column 0.
- **Why it matters:** a reader (or a later change) will assume the range spans the line and may
  compute against it; editors highlight nothing today.
- **Action:** either emit `end.character` at the line's length, or restate the docstring as "a
  zero-width location at the start of the line" with the reason.
- **Done when:** docstring and emitted range agree, pinned by a test.
- **Effort:** S
- **Risk if fixed:** widening the range changes what an editor highlights on jump.

## G25 — Give the surface a consumer, or record the decision not to

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** whole surface; `marketplace/bundles/pm-plugin-development/.claude-plugin/plugin.json`
  (no `lspServers`), `SKILL.md:195-207`, `doc/user/corpus-language-server.adoc:83-128`
- **Evidence:** a tree-wide grep for `lspServers` finds it in no bundle manifest; the only 14 files
  naming this skill are its own source, its tests, its three docs and two config-standard docs. No
  workflow, persona, phase skill or command invokes `preflight` or `query`. The run report states
  this plainly: *"the surface has no automatic consumer"*, and flags that the D-half of the operator's
  A+D decision ("must not ship without a consumer") is unmet.
- **Why it matters:** this epic has already built and removed one zero-adoption surface
  (`130` → `135`). The condition that failure mode exists to prevent is not met here, only reduced.
- **Action:** either wire one real consumer that is safe without the `.md` binding — e.g. have a
  plugin-doctor or outline step call `query --kind references` instead of a Grep sweep — or record a
  dated decision that the surface stays operator-wired, with the criterion for revisiting.
- **Done when:** either a component in `marketplace/bundles/` invokes a `corpus_lsp` verb, or a
  decision record names the deliberate zero-consumer state and its review trigger.
- **Effort:** M
- **Risk if fixed:** a consumer that pays the ~2.5 s one-shot index build per call would reintroduce
  exactly the cost D1 ruled out — any consumer must batch or run resident.

## G26 — Add a `manage-config` path for the `code_intelligence` section

- **Kind:** omission
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/` — `code_intelligence` appears
  only in `standards/data-model.md` and in `scripts/_config_core.py`'s
  `CANONICAL_TOP_LEVEL_KEY_ORDER`
- **Evidence:** grep for `code_intelligence` under `manage-config/` returns exactly those two files;
  no verb reads or writes the section. `doc/user/corpus-language-server.adoc:44-55` instructs
  hand-editing `.plan/marshal.json`, unlike every other documented section. Declared as report
  finding 20 and accepted as-is.
- **Why it matters:** hand-editing a version-controlled config is the one workflow this repository
  otherwise scripts; the asymmetry invites malformed blocks, which fail closed (silently off) and are
  hard to diagnose.
- **Action:** add a `manage-config code-intelligence set --enabled true|false [--corpus-path P]` verb
  (or fold it into the existing section handling) and repoint the user page at it.
- **Done when:** the switch can be set through the executor and the user page documents that path.
- **Effort:** M
- **Risk if fixed:** a new verb widens `manage-config`'s surface; keep it read-modify-write over the
  canonical key order so ordering tests stay green.

## G27 — Reconcile `CLAUDE.md`'s component counts

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `CLAUDE.md`, § Repository Overview — *"157 registered components (153 skills, 2 agents,
  2 commands)"*
- **Evidence:** re-derived now from the tree: `marketplace/bundles/*/skills/*/SKILL.md` → **156**;
  `*/agents/*.md` → **2**; `*/commands/*.md` → **2**; total **160**. Declared as report finding 19,
  deferred as pre-existing and unowned.
- **Why it matters:** the number is the first factual claim in the repository's own agent-facing
  instructions, and it has been wrong across at least three plans.
- **Action:** settle what "components" counts (skills + agents + commands, or something else), state
  the definition next to the number, and correct it — ideally with a test or doctor rule that
  re-derives it.
- **Done when:** the stated total matches a re-derivation from the tree, with the counting rule named.
- **Effort:** S
- **Risk if fixed:** the number drifts again unless a check enforces it.
