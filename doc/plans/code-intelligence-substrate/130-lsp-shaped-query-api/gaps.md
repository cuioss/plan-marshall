# Gaps — 130-lsp-shaped-query-api

Four of the plan's five deliverables survive in the tree (D1, the `lsp` facade, was deliberately
retired by the later landed plan `135-remove-lsp-query-facade`, PR #1214 / `064b387` on `main` —
that absence is intended and is **not** a gap). Nine gaps remain open, concentrated in D2 and D3:
the `capabilities` verb does not draw its own cannot-derive-versus-derived-nothing distinction on
the `content_search` row, three shipped documents assert an "uncached" property the code does not
have, the documented three-state entry shape is unexpressible on the `path_attribution` row, the
refine `UNDERIVABLE` guard has no test that touches the shipped artifact, and two sibling counters
in the `search` response are row populations documented as file populations. Each entry below is
grounded in a measurement re-run at audit time (mutation runs, in-process probes, GitHub API reads),
every one of which was re-taken independently by an adversarial pass at `a90adeb` — see
`verification.md` for the full evidence.

## G1 — Make `capabilities.content_search` distinguish "never crawled" from "crawled, nothing inventoried"

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:211-218`
  and `:243-248` (`cmd_capabilities`, the `content_search` entry)
- **Evidence:** the entry carries only `status` (`available`/`unavailable`) and
  `modules_inventoried`, and the module loop swallows a missing descriptor
  (`except DataNotFoundError: continue`). Probed in this clone: an empty envelope and an envelope
  carrying two crawled but file-less modules both return
  `{"capability": "content_search", "verbs": ["files", "find", "search"], "status": "unavailable", "modules_inventoried": 0}`
  — payload comparison `True`. The shipped tests encode the same conflation:
  `test_capabilities.py:121-135` asserts the never-crawled envelope reports `unavailable`, and
  `:225-233` asserts the crawled-but-file-less envelope reports `unavailable` with
  `modules_inventoried == 0`; nothing anywhere asserts the two entries differ, and as shipped they
  cannot.
- **Why it matters:** this row is the one a dispatched leaf consults before deciding whether a
  `count: 0` from `search --content` is a trustworthy negative. As shipped it cannot tell "the crawl
  never ran here, refresh it" from "the crawl ran and inventoried nothing" — the exact ambiguity
  D2 was created to close, left open in one of its three rows, and the same archetype the plan's own
  D2 constraints name.
- **Action:** give the entry producer evidence in the same shape the other two rows use — e.g.
  `modules_total` (or `modules_without_descriptor`) alongside `modules_inventoried`, and a
  `not_derivable` status when no module descriptor could be read at all, reserving
  `available`/`unavailable` (or, better, the `derivable`/`not_derivable` vocabulary noted as a
  follow-up in `135-remove-lsp-query-facade/plan.md:226-229`) for the crawled case. Update
  `client-api.md:1392-1415`, `SKILL.md:544`, `doc/user/code-search.adoc:198` and
  `doc/concepts/code-intelligence.adoc:252-262` to match — **and `client-api.md:572`**, whose
  verb-summary row already claims `capabilities` reports "Per-capability
  `derivable`/`not_derivable` (module edges, path attribution, content search)" while the code gives
  `content_search` only `available`/`unavailable` (`_cmd_client_handlers.py:246`). That row is wrong
  today whichever way this gap is closed; harmonising the vocabulary makes it right, keeping the
  split means rewording it.
- **Done when:** a test seeds (a) an envelope with no descriptors and (b) an envelope with N crawled
  file-less modules, and asserts the two `content_search` entries differ; no envelope can produce an
  entry that is silent about how many modules were inspected; and `client-api.md:572` states the
  vocabulary the code actually emits.
- **Effort:** S
- **Risk if fixed:** the entry's field set changes, so the TOON examples in `client-api.md` and any
  consumer reading `status` as a two-valued enum must be updated in lock-step.

## G2 — Reconcile the "nothing is memoised across calls" claim with `_PATH_CLAIM_CACHE`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** claim at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:162-163`,
  `.../standards/client-api.md:1375-1376`, `doc/concepts/code-intelligence.adoc:259`; contradicting
  code at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:1122`
  (`_PATH_CLAIM_CACHE`) used by `resolve_path_attribution` at `:1176-1181`
- **Evidence:** the docs say "Nothing is memoised across calls" / "memoised across none". Probed:
  two `cmd_capabilities` calls in one process, with `discover_path_attributors` returning an
  attributor between them, both report `path_attribution: not_derivable, producer_count 0` — the
  second call is served from the memo. (`SKILL.md:544` and `doc/user/code-search.adoc:198` use the
  weaker, accurate "never cached across dispatches".)
- **Why it matters:** the uncached property is one of D2's three *binding* constraints, written into
  the plan because "probe then branch" is unsound. A reader of the strongest phrasing will believe a
  repeated in-process call re-probes; it does not. Any future in-process consumer (the test corpus
  already is one) inherits a stale capability answer while the documentation promises freshness.
- **Action:** either (preferred) invalidate the attribution memo at the top of `cmd_capabilities` so
  the strong claim becomes true, or downgrade all three statements to the accurate per-dispatch
  phrasing already used in `SKILL.md` and `code-search.adoc`, and say explicitly that a
  process-lifetime memo backs the path-attribution row.
- **Done when:** a test calls `cmd_capabilities` twice in one process with the attributor population
  changed in between and asserts the outcome the docs promise; all four doc sites state the same
  property.
- **Effort:** S
- **Risk if fixed:** dropping the memo per call re-runs full extension discovery, which
  `_architecture_core.py:1111-1121` documents as the reason the memo exists — scope the
  invalidation to `capabilities` only, never to `resolve_module_for_path`'s per-path loop.

## G3 — Key `_PATH_CLAIM_CACHE` by project directory as well as module names

- **Kind:** bug
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:1122, 1176-1181`
- **Evidence:** `cache_key = tuple(sorted(module_names))` — `project_dir` is not part of the key, so
  two envelopes with identical module-name sets share one memo entry within a process.
- **Why it matters:** `capabilities` advertises an envelope-scoped answer
  (`client-api.md:1380-1381`). Today the property survives only because attributor discovery is
  process-global (bundle-registered, `extension_discovery.py:581`); the moment any project-local or
  project-parameterised attributor exists, envelope A's answer will be served to envelope B in the
  same process, silently.
- **Action:** include the resolved project directory in the memo key (or pass it through and key on
  `(project_dir, module_names)`), keeping the existing `invalidate_crawl_cache` drop behaviour.
- **Done when:** a test computes path attribution for two project dirs with identical module names
  and different expected outcomes in one process and gets two different answers.
- **Effort:** S
- **Risk if fixed:** a wider key lowers the memo hit-rate for callers that alternate project dirs;
  `resolve_module_for_path`'s per-path loop must still hit the memo for a single project dir.

## G4 — Pin the refine `UNDERIVABLE` guard with a test that reads the shipped document

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-architecture/test_feasibility_underivable_guard.py:85-93`
  (`_dependency_direction_derivable`); the artifact it is supposed to protect is
  `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md:493-498`
- **Evidence:** the test defines the guard locally and asserts it against `get_module_graph`'s
  `resolver_count`; it never opens `refine-workflow-detail.md`. Proven by mutation: deleting the
  entire `**Underivable guard …**` block from the standards file leaves the test file green
  (`3 passed in 0.39s`). Precedent for the missing check exists in the same skill —
  `test/plan-marshall/phase-2-refine/test_phase_2_refine_scope_estimate.py:361-384` reads that same
  document and asserts its content.
- **Why it matters:** D3's *Done when* requires "a test asserts it cannot silently pass on
  emptiness". The shipped consumer is prose; with no doc-anchored assertion, an editor can delete or
  weaken the guard and every gate stays green — restoring exactly the vacuous-consumer failure the
  deliverable closed.
- **Action:** add a test (in `test/plan-marshall/phase-2-refine/`) that reads
  `refine-workflow-detail.md` and asserts the Feasibility Check section still contains both arms —
  the `resolver_count: 0` ⇒ `FEASIBILITY: UNDERIVABLE` instruction and the `resolver_count: N`
  clean-pass instruction — and, ideally, that the `capabilities` cross-reference resolves.
- **Done when:** removing or weakening either arm of the guard turns that test red.
- **Effort:** S
- **Risk if fixed:** a text-anchored assertion is brittle to rewording; anchor on the stable tokens
  (`FEASIBILITY: UNDERIVABLE`, `resolver_count`) rather than whole sentences.

## G5 — Name `files_scanned`'s real population (scans, not distinct files)

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1238`
  (`files_scanned += 1`, inside the per-`(module, category, path)` loop); documented as a file count
  at `.../standards/client-api.md:988` and `doc/user/code-search.adoc:147-148`
- **Evidence:** probed on the same doubly-attributed fixture the D4 test uses — one physical file
  inventoried by two modules returns `count 2 / file_count 1 / files_scanned 2`. The docs say
  `files_scanned` "Counts the files actually OPENED AND SCANNED" and "How many files were actually
  opened and searched".
- **Why it matters:** `files_scanned` is the field the documented complete-coverage conjunction
  (`client-api.md:992-1006`) rests on, and it is quoted to callers as the population size behind a
  negative result. On a tree with cross-module duplicate inventory it over-states that population —
  the same row-versus-file recurrence D4 closed one field over, left open in the field that carries
  the trust. **Severity note (why medium, not high):** the calibration reserves *high* for a
  measurement that misreports in a way that changes an outcome. The documented complete-coverage
  conjunction tests `files_scanned > 0`, and duplicate attribution can only inflate the counter —
  it is zero exactly when the distinct-file count is zero — so no gate flips. What is wrong is the
  population size quoted to a reader, not the trust decision computed from it.
- **Action:** either count distinct paths (`len(scanned_paths)`) or keep the counter and rename/
  redocument it explicitly as scans (adding a distinct `files_scanned_distinct`). Then state the
  chosen semantics **once**, in `client-api.md` § search → "Complete-coverage rule" (`:988`,
  `:992-1006`) — that section is the canonical coverage contract, and `CLAUDE.md` already points
  readers at it as the field list of record. `doc/user/code-search.adoc:147-148` and
  `doc/concepts/code-intelligence.adoc:254` must **cross-reference** it rather than restate the
  definition, per the repository's no-duplication documentation standard; where they need a sentence
  of their own, it names the field and defers, it does not redefine.
- **Done when:** a test using the doubly-attributed fixture asserts the documented meaning of
  `files_scanned` holds (distinct-file semantics, or the explicitly-scans semantics); `client-api.md`
  carries exactly one definition of that meaning; and neither `code-search.adoc` nor
  `code-intelligence.adoc` carries a second definition that could drift from it.
- **Effort:** S
- **Risk if fixed:** any consumer comparing `files_scanned` against a previously recorded number
  sees a step change on duplicate-inventory trees; the double `read_text` per duplicate row is also
  a small performance cost that a de-duplicating fix would remove.

## G6 — Stop emitting duplicate `unreadable[]` entries for one physical file

- **Kind:** bug
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1230-1237`
  (the `unreadable.append(...)` arms, inside the per-`(module, category, path)` loop)
- **Evidence:** probed — one missing file listed in two modules' inventories yields
  `unreadable: [{"path": "shared/ghost.py", "reason": "os_error"}, {"path": "shared/ghost.py", "reason": "os_error"}]`.
  `client-api.md:989` describes each entry as "a file that MIGHT contain a match nobody saw".
- **Why it matters:** the coverage-gap report is meant to be read as a list of at-risk *files*; a
  caller counting entries (or listing them to an operator) over-reports the gap and sees the same
  path twice with no indication why.
- **Action:** de-duplicate by `(path, reason)` before returning, or attribute the entry to its
  modules explicitly (`{path, reason, modules[]}`) so a repeat is legible rather than accidental.
  ⚠ The second option is a **schema change**, not an output tweak: `unreadable[]` is part of the
  complete-coverage contract that `client-api.md` § search → "Complete-coverage rule" defines
  canonically (alongside `truncated` and `elided`). If `{path, reason, modules[]}` is chosen, the
  canonical entry shape in `client-api.md` and every consumer and test that reads an `unreadable`
  entry must be updated in the same change; `doc/user/code-search.adoc` and
  `doc/concepts/code-intelligence.adoc` cross-reference the canonical definition rather than carrying
  a second copy of it (see G5).
- **Done when:** the duplicate-attribution fixture with an unreadable file produces exactly one
  `unreadable` entry for that path (or one entry naming both modules), asserted by a test; and — if
  the entry shape changed — `client-api.md`'s canonical schema names the new shape and no consumer
  or test still assumes the old one.
- **Effort:** S
- **Risk if fixed:** ADR-014 requires the skip be reported, never suppressed — de-duplication must
  keep the path present, only collapsing repeats. Changing the entry shape additionally breaks any
  consumer keying on `{path, reason}` exactly, which is why the canonical schema and its consumers
  move together.

## G7 — Verify `capabilities` inside a real dispatched leaf, or record the constraint as unmeetable

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** plan requirement at `doc/plans/code-intelligence-substrate/130-lsp-shaped-query-api/plan.md:155-157`;
  substituted proxy at `test/plan-marshall/manage-architecture/test_capabilities.py:260-275`;
  disclosure at `report-01.md:112-117, 200-203`
- **Evidence:** the plan states "D2 is verified inside a dispatched leaf, not in main context"; the
  run recorded that a leaf with revoked Grep/Glob could not be synthesised and used a two-project-dir
  test instead. Nothing in the tree closes it: a bundle-wide grep for `architecture capabilities`
  outside `manage-architecture/` returns exactly one hit —
  `phase-2-refine/standards/refine-workflow-detail.md:498` — and the verb's only other mentions are
  its own documentation (`manage-architecture/SKILL.md:541`, `doc/user/code-search.adoc:195`) and the
  tests.
- **Why it matters:** D2 exists because a report correct in the orchestrator and wrong in a leaf is a
  failed deliverable. The proxy demonstrates project-dir scoping but not leaf behaviour, so the
  deliverable's own verification clause is still owed — and a later plan may re-encounter it as a
  new finding rather than as known residue.
- **Action:** either exercise `capabilities` from inside a dispatched execution-context sub-agent and
  record the returned payload alongside the orchestrator's, or write the reasoning down where a
  future reader will find it (a note in `client-api.md § capabilities` stating that the answer is a
  pure function of `project_dir` + the producers that ran, and therefore harness-grant-independent)
  and close the constraint explicitly.
- **Done when:** either a leaf-obtained `capabilities` payload is committed under the executing
  plan's directory alongside the orchestrator's for the same project dir, or
  `manage-architecture/standards/client-api.md` § `capabilities` carries a named paragraph stating
  that the answer is a pure function of `project_dir` plus the producers that ran and therefore
  cannot vary with the harness tool grant — either artifact being readable, a later reader can check
  which arm was taken without re-deriving the question.
- **Effort:** M
- **Risk if fixed:** none to shipped behaviour; a documentation-only close must not overstate — the
  harness-grant question genuinely is outside the verb's reach.

## G8 — Correct the run report's three inaccurate claims

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/130-lsp-shaped-query-api/report-01.md:170`
  (commit count), `:69` (the "uncached" claim), `:104-105` (the blanket verification claim)
- **Evidence:**
  1. The Contract check at `:170` says "DONE — six commits, all carrying the `Co-Authored-By:
     Claude` trailer". PR #1207 carries eight: `31b8ede`, `0d12e4b`, `6126013`, `8159710`,
     `0df29ed`, `32d4c27`, `8469daf`, `1f2fdee` (GitHub API `get_commits`, re-read at audit time;
     the PR object also reports `commits: 8`). All eight do carry the trailer.
  2. `:69` claims D2 is "per-call (uncached)". The path-attribution half is memoised for the
     process lifetime (`_architecture_core.py:1122`) — see G2. The accurate phrasing is the one the
     shipped `SKILL.md` uses: "never cached across dispatches".
  3. `:104-105` records the verification sub-agent's "All five deliverables verified as
     implemented-as-specified with tests". Two of the five are not: the D3 test never touches the
     shipped guard (G4) and the D2 `content_search` row does not draw the distinction D2 is named
     for (G1).
- **Why it matters:** the contract check is the record a later retrospective reads as measurement;
  an under-count there is a small but real defect in the audit trail, and the same line is the one
  that certifies the trailer property. The other two claims are the ones a later plan would cite as
  evidence that this surface was already verified.
- **Action:** correct the count to eight; narrow the D2 claim at `:69` to "never cached across
  dispatches"; and qualify `:104-105` with a pointer to the two deliverables whose verification did
  not hold up. While editing, add the squash SHA `8d5055f` so a later reader can resolve the run
  locally — the eight branch SHAs no longer exist in a fresh clone (`git cat-file -t` → `Not a valid
  object name` for all of them).
- **Done when:** `report-01.md` states the true commit count, names the squash commit, and carries
  no claim contradicted by G1, G2 or G4.
- **Effort:** S
- **Risk if fixed:** none — a run record edited for factual accuracy; the dated-record carve-out in
  `CLAUDE.md` already covers this file. Do not rewrite the report's narrative beyond these three
  claims: it is a record of one execution, not documentation of current state.

## G9 — Give the `path_attribution` row a `derived_count`, or stop documenting one

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** architecture-core
- **Where:** entry built at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:236-242`;
  contradicting documentation at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:1383-1390`,
  `.../scripts/_cmd_client_handlers.py:172-176` (the handler docstring) and
  `doc/concepts/code-intelligence.adoc:262`
- **Evidence:** all three documents state the entry shape as three distinct states —
  `not_derivable`/`producer_count: 0`, `derivable`/`derived_count: 0`, `derivable`/`derived_count:
  N`. The `path_attribution` entry carries `capability`, `verbs`, `status`, `producers` and
  `producer_count`, and no `derived_count` at all, so an attributor that ran and claimed nothing and
  one that claimed fifty both report `derivable, producer_count: 1`. (`module_edges` does carry
  `derived_count`, and `content_search` is separately documented as using its own vocabulary — see
  G1.) The data needed is already computed: each attributor report carries `claim_count`
  (`marketplace/bundles/plan-marshall/skills/extension-api/scripts/_path_attribution_merge.py:342`).
- **Why it matters:** D2's own *Done when* is still met on this row — `producer_count` draws the
  cannot-derive versus derived-nothing binary — so this is not an unmet deliverable. What is wrong
  is that the shipped contract describes a field one of its three rows never emits, which is the
  doc-contract-divergence archetype D5 was written to prevent, at small scale. A consumer coding
  against the documented table gets a `KeyError`, not a wrong answer.
- **Action:** either add `'derived_count': sum(report['claim_count'] for report in
  attributor_reports)` to the `path_attribution` entry, or amend the three documents to say that
  `derived_count` is carried by `module_edges` only and that `path_attribution` reports producer
  presence without a claim volume.
- **Done when:** for every capability row, the fields named in `client-api.md`'s entry-shape table
  are the fields the handler emits, asserted by a test that reads the payload keys of all three
  entries.
- **Effort:** S
- **Risk if fixed:** adding the field changes the entry's key set, so the TOON examples at
  `client-api.md:1395-1415` must be updated in lock-step (the same coupling G1 carries). Summing
  `claim_count` across attributors double-counts a path two attributors both claim; if that matters,
  document the field as claims-reported rather than paths-attributed.
