# inspect.getsource Use Survey — Classification

## Scope

Every `inspect.getsource` call in the test suite, surveyed for what it asserts and
whether the assertion is vacuous (pins source *text* where *behaviour* is the real
property) or structural-but-meaningful (derives or prohibits call structure that a
behaviour test cannot observe without instrumentation).

The surveyed population is the pre-change tree: **9 call sites in 8 files**
(a fresh architecture content-search re-derives the same files as 16 per-file
module-attribution rows; `test_not_triggered_detection.py` carries two of the
nine call sites).

## Classification scheme

| Class | Meaning | Verdict |
|-------|---------|---------|
| **structural derivation** | Source is read as *structure* (AST, call extraction, marker presence) to derive a population or wiring fact that feeds real assertions | keep |
| **text-shape pin** | Source text is asserted byte-for-byte (indentation-sensitive), duplicating a property the behavioural suite already owns | replace |
| **text-absence pin (prose/capability)** | A literal must not appear in the source; the consumer-visible property is a behavioural output (help text, written files) | replace or complement with a behavioural assertion |
| **prohibition pin (wiring)** | A name/call must not appear in a specific function's source, guarding a documented wiring constraint | keep |
| **utility** | Source is read only to strip or tokenise it for the *downstream* assertions | keep |

## Per-site entries

### 1. `test/plan-marshall/automatic-review/test_structural_refusal.py:1603` — `inspect.getsource(rc._parse_bot_observations)`

- **Mechanism:** `textwrap.dedent` + `ast.parse` + `ast.walk`; every `Call` node with
  a `--`-prefixed literal argument yields `flag → parse-function-name`.
- **Asserts:** the routing map *performed by the code* — each registered flag is
  actually passed to a parser inside `_parse_bot_observations`. Downstream,
  `_form_of` classifies each parser **behaviourally** (feeds a bare token and a
  pair token, observes which is rejected), and the derived pair/bare sets are
  checked against the module docstring's prose partition and count words.
- **Class:** structural derivation. The flag→parser mapping is unobservable
  without instrumentation, so reading the routing function's own AST is the honest
  way to derive it. The form classification is behavioural, not textual.
- **Verdict:** keep as-is.

### 2. `test/plan-marshall/phase-6-finalize/test_gate_derivation_diagnosability.py:235` — `inspect.getsource(_derive_module.derive_gate_bundles)`

- **Mechanism:** literal substring checks: `'\n        else:\n'` (exact
  eight-space indentation) must occur, and the tail after its last occurrence must
  contain `unresolved.append`.
- **Asserts:** the fall-through branch reports rather than drops — a terminal
  `else:` listing a consumer-shaped path appends to `unresolved` instead of
  falling off the end.
- **Why it is the replace candidate:** the file's own section header (lines
  226–231) states the property is *structural only* and that "whether the seam
  actually routes a consumer-shaped footprint into `unresolved` is the behavioural
  pair `test_derive_gate_bundles.py` owns". Pinning the exact indentation makes
  the assertion brittle to pure reformatting, and the behavioural property is
  already owned by the sibling suite — so this pin is redundant for the property it
  names and fragile for the text it pins.
- **Class:** text-shape pin.
- **Verdict:** replace — either drop in favour of the behavioural pair or convert
  to an AST terminal-`else` presence check that is indentation-independent and
  adds diagnosability without byte-matching.

### 3. `test/plan-marshall/plan-retrospective/test_footprint_resolver.py:586` — `inspect.getsource(_fr.resolve_footprint)`

- **Mechanism:** marker-membership: each tier's call marker (e.g.
  `compute_plan_branch_diff`, `read_captured_footprint`) is searched as a substring
  of the resolver function's own source; `consulted` is asserted equal to
  `RESOLVING_TIERS` and to the docstring's documented resolving count.
- **Asserts:** the resolver body actually consults every tier it declares — a
  doc-vs-body agreement guard whose population is derived from the resolver's own
  `RESOLVING_TIERS` key set, so a tier added without a marker fails.
- **Class:** structural derivation (call-marker presence). Non-vacuous in intent;
  substring matching can in principle false-pass on a comment mention, which the
  design accepts in exchange for staying derived.
- **Verdict:** keep. No behavioural replacement exists that is cheaper than the
  structural tier-coverage check it performs.

### 4. `test/plan-marshall/platform-runtime/test_permission_ops.py:351` — `inspect.getsource(permission_web)`

- **Mechanism:** whole-module source read; asserts the literals
  `~/.claude/settings.json` and `.claude/settings.local.json` are **absent**.
- **Asserts:** the script's user-facing help no longer hardcodes the settings
  path.
- **Why it is replaceable:** the consumer-visible property is the **help output**,
  not the source bytes. The script already has a behavioural CLI tier
  (`test_permission_web.py::test_help` runs `permission_web --help` and asserts on
  `stdout`), so the same pattern can assert the absence of the two path literals
  in the actual rendered help — which fails exactly when a user would see the
  hardcoded path, and does not fail on a source comment that mentions it.
  Note this is the *same script* read by site 8.
- **Class:** text-absence pin (prose) with a direct behavioural substitute.
- **Verdict:** replace with a help-output assertion.

### 5. `test/plan-marshall/script-shared/test_marketplace_paths.py:718` — `inspect.getsource(marketplace_paths)`

- **Mechanism:** module source is split at the first `def `; the module-head text
  is asserted not to contain `import file_ops`.
- **Asserts:** the lazy `file_ops` import stays inside `resolve_main_anchored_path`
  — no module-top import, which would reintroduce the import cycle. The same test
  then *behaviourally* proves the in-function import executes cleanly by calling
  the resolver under `PLAN_BASE_DIR`.
- **Class:** structural placement pin. The rule being guarded is genuinely about
  source placement (lazy-import architecture), so text inspection is the honest
  assertion; a behaviour run cannot distinguish "in-function import" from
  "import in an unused helper".
- **Verdict:** keep. The `split('def ', 1)` implementation is text-fragile (a
  docstring containing `def ` before the first import would mis-split); an
  AST-based module-head scan would be more robust but the property and verdict
  are unchanged.

### 6. `test/plan-marshall/workflow-integration-github/test_not_triggered_detection.py:69` — `inspect.getsource(func)` (in `_code_without_docstring`)

- **Mechanism:** reads a function's source and removes its docstring via
  `source.replace(doc, '')`.
- **Asserts:** nothing directly — it is the *precision utility* for the
  code-only prohibition scans: a name the code must not reference would otherwise
  be matched inside explanatory prose, making the assertion about words near the
  code rather than the code.
- **Class:** utility.
- **Verdict:** keep as-is.

### 7. `test/plan-marshall/workflow-integration-github/test_not_triggered_detection.py:102` — `inspect.getsource(func)` (in `_calls_in`)

- **Mechanism:** regex-extracts every called identifier from a function's source
  to build the transitive call-graph of the detection path (`_detection_path_functions`),
  then applies the privacy filter (a reachable function stays in the population
  only when every module-level caller of it is itself on the path).
- **Asserts:** the swept population is *derived from the code*, never remembered —
  the docstring documents the failure mode it exists to prevent (a literal name
  set went stale when the PR-boundary fix added two helpers while the sweep kept
  reporting full coverage over the three names it knew).
- **Class:** structural derivation (call-graph from source).
- **Verdict:** keep as-is.

### 8. `test/plan-marshall/workflow-permission-web/test_permission_web.py:181` — `inspect.getsource(mod)` (module `permission_web`)

- **Mechanism:** whole-module source read; asserts the tokens `json.loads`,
  `json.dumps`, `WebFetch(`, `read_text`, `write_text` are **absent**.
- **Asserts:** D1 routing — the script has no settings-I/O capability and no
  WebFetch-grammar rendering; driving it can never create a
  `.claude/settings*.json` file. The test's own docstring states the behavioural
  property ("Driving this script must never create a `.claude/settings*.json`
  file") that the source scan stands in for.
- **Class:** text-absence pin (capability boundary). The negative constraint *is*
  textual (the script must not import or use the I/O helpers), so the source scan
  is the precise boundary guard; the behavioural complement (run the CLI and
  assert no settings file materialises) is already half-covered by the subprocess
  tier, which runs the script but never asserts file non-creation.
- **Verdict:** keep the source-level capability pin; complement it with a
  run-level assertion that the CLI leaves no settings file behind, so the
  docstring's behavioural claim is asserted as behaviour rather than inferred from
  source bytes.

### 9. `test/pm-plugin-development/plugin-doctor/test_analyze_manage_invocation.py:1657` — `inspect.getsource(dm.cmd_analyze)`

- **Mechanism:** single-function source read; asserts `scan_manage_invocation` is
  **absent** from the body.
- **Asserts:** `cmd_analyze` must not re-wire the expensive live-`--help`
  manage-invocation rule into the per-component analyze path. The docstring
  documents the measured rationale (cold-derived whole-marketplace surface
  overrunning the per-call subprocess budget, a 30 s timeout under a cold CI
  cache), so the pin guards a real performance wiring constraint, not prose.
- **Class:** prohibition pin (wiring).
- **Verdict:** keep as-is. A behavioural expression (run `cmd_analyze` and assert
  the rule absent from `rules_run`) is possible but strictly weaker: it would
  guard this run's outcome rather than the wiring decision, and it costs a full
  analyze pass.

## Replacement candidates (feed into the replacement task)

| Site | File:line | Current pin | Replacement |
|------|-----------|-------------|-------------|
| 2 | `test_gate_derivation_diagnosability.py:235` | indentation-exact `else:` + `unresolved.append` in source tail | drop in favour of behavioural pair `test_derive_gate_bundles.py`, or AST terminal-`else` presence check |
| 4 | `test_permission_ops.py:351` | settings-path literals absent from `permission_web` source | run `permission_web --help` and assert the path literals absent from stdout |
| 8 | `test_permission_web.py:181` | I/O tokens absent from `permission_web` source | keep the capability scan; add a run-level assertion that the CLI creates no settings file |

The four structural-derivation sites (1, 3, 5, 7), the utility (6), and the
wiring prohibition (9) stay source-mediated: the facts they derive or prohibit are
call-graph/placement facts that behaviour tests cannot observe, and none of them
byte-match source text for a property the behavioural suite already owns.