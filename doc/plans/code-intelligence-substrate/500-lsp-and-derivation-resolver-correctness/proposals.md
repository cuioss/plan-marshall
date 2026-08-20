# Recorded proposals and decision records — plan 500

Everything here is **recorded rather than acted on**. Nothing in this document was implemented by the
run that produced it, and nothing here may be implemented by reading it.

Two kinds of entry appear below, and they differ in who has to act next:

- **Proposals** (`P1`–`P6`) — a change the run identified but is **not authorised to make**. Each names
  what would change, the blast radius, and the observation that would settle it. **Each needs an
  operator's approval before anyone acts on it.**
- **Decision records** (`D1`) — a state the run measured and **left exactly as it found it**. Nothing
  was changed and nothing needs approving, because doing nothing is what already happens; what the
  entry records is the *reasoning* for the status quo and the **trigger that should reopen it**.
  ⚠ Read it as "here is why this is the way it is, and what would change that" — not as the run
  having settled the question.

---

## P1 — Publish marketplace-bundle prefixes as Axis-D path-attribution claims

**Handed up by:** D3 (`200-lsp-derivation-resolver/gaps.md#G3`, `#G6`).

**What would change.** The `lsp` harvest lifts file references to module granularity through a
caller-supplied longest-prefix table (`make_prefix_attributor`), not through the Axis-D
path-attribution seam. That substitution is currently *necessary*: no attributor on that seam claims
a `marketplace/bundles/**` path. Re-derived on this clone —
`merge_path_claims(discover_path_attributors(), ['plan-marshall', 'pm-plugin-development',
'documentation'])` returns a `(claims, roster)` pair whose **claims** list holds **five** entries
from **three** attributors: `.claude` → `pm-plugin-development`, `.plan` → `plan-marshall`, and
`doc` / `README.md` / `CONTRIBUTING.md` → `documentation`. None covers `marketplace/bundles/**`, so
`lookup_claim('marketplace/bundles/…/scripts/y.py', …)` returns `None` and routing through it would
derive zero edges. The proposal is to make the seam claim what the table claims — publishing
`(marketplace/bundles/{bundle}, {bundle})` through `claim_paths()`.

**Blast radius — wider than the resolver.** Axis-D claims are not scoped to this harvest. They decide
what `which-module` answers, and what the change-footprint classifiers attribute, **for every
`marketplace/bundles/**` path in the repository**. A change here is felt by every surface that asks
"which module owns this file", not by the `lsp` resolver alone.

**What would settle it.** Run the `which-module` test suite against a tree carrying the new claims and
show it unchanged; then re-derive the change-footprint classification for a sample of recent commits
and show the same. Both must come back identical before the claim set is a safe substitution, because
the point of the change is to make one consumer agree with the others — not to move the others.

**What the run did instead.** Corrected both docstrings (`lsp_harvest.py`'s lift, and the resolver's
`derive_edges`) to describe the mechanism the code actually invokes, and to name the two obligations
the substitute does not carry: the seam's ambiguous-ownership rule (the prefix table's equal-length
tie-break is iteration order, which `ext-point-path-attribution.md` forbids; unreachable today because
bundle directory names are unique) and vendored-tree exclusion, which the harvest now performs before
the lift is asked.

---

## P2 — Extend npm discovery to `peerDependencies` and `optionalDependencies`

**Handed up by:** D4 (`210-native-coordinate-resolvers/gaps.md#G4`).

**What would change.** `_npm_cmd_discover.py::_extract_dependencies` iterates `dependencies` and
`devDependencies` only. `peerDependencies` — the idiomatic way a plugin package declares its
dependency on a workspace's core package, and therefore squarely the intra-workspace relationship the
resolver exists to find — and `optionalDependencies` produce no edge. The proposal is to read all
four.

**Blast radius — a scope-vocabulary change, not a parser change.** The extraction emits `name:scope`
strings, and widening what it emits widens what **every** npm module publishes. The scope vocabulary
is consumed at four sites that must move in lock-step, or a module will publish a scope its readers
drop silently:

1. `_npm_cmd_discover.py::_extract_dependencies` — the producer.
2. The npm derivation resolver's join (`build-npm/scripts/extension.py`, via the shared
   `derive_name_edges`), which reads the **name** — `dependency.split(':', 1)[0]` — and, in its own
   words, *deliberately ignores* the scope segment. ⚠ That makes the coupling **tighter**, not looser,
   than "must not start treating a new scope as an edge": the join already treats every scope as an
   edge, so widening the producer **alone** would immediately create edges for both new kinds, with
   no separate decision made anywhere. There is no second gate to fall back on.
3. `build-npm/SKILL.md` § Axis-C, which states which kinds contribute.
4. `doc/user/dependency-intelligence.adoc` § npm specifics, which states the same limit to an
   operator.

Choosing *which* of the four kinds count as edges is the decision — a `peerDependency` is arguably a
stronger signal than a `devDependency`, and an `optionalDependency` arguably weaker than either. That
is a scope call, not a bug fix.

**What would settle it.** A workspace fixture declaring a sibling under each of the four kinds, with
the expected edge set stated per kind by whoever takes the decision. Until that expectation exists
there is nothing to implement against.

**What the run did instead.** Took the disclosure route the plan directs: both the user page and
`build-npm/SKILL.md` now state that the two unread kinds produce no edge and what that costs, matching
the shape of the Python disclosure, so an empty edge set is not read as "these packages do not depend
on each other".

---

## P3 — A typed discriminator on the LSP transport's error

**Handed up by:** D3 (`200-lsp-derivation-resolver/gaps.md#G2`).

**What would change.** The shared transport raises one exception type, `LspError`, for a wait expiry
and for a JSON-RPC error reply alike. D3 needed to tell them apart — a server that *refuses* the
workspace is not a server that *failed to respond* — and the only discriminator available was the
message text. The proposal is a typed field on `LspError` (a `kind`, or distinct subclasses) so the
two are separable structurally.

**Blast radius — another bundle.** `LspError` lives in `plan-marshall:lsp-client`; the consumer that
needs the discriminator is in `pm-plugin-development`. Reaching across to change one bundle's error
type for another bundle's classification is the coupling the plan directs this run not to introduce.

**What would settle it.** Whether any *second* consumer needs the distinction. One consumer is served
adequately by the text split; two would make the text split a duplicated fragility and the typed field
clearly correct.

**What the run did instead.** Implemented the text-based split in `lsp_harvest.py`, with the fragility
stated at the constant that carries the marker string, and chose the fallback direction so that an
unrecognised message from a *completed* handshake stays a timeout — the pre-existing behaviour — rather
than silently reclassifying every handshake failure as a rejection.

---

## P4 — Index invalidation with a debounce on `didChange` / `didSave`

**Handed up by:** D5 (`240-skill-lsp-server/gaps.md#G3`).

**What would change.** The corpus server's index is built once and never cleared; the line and
candidate caches only grow; `didOpen` / `didChange` / `didClose` touch only the document map. In a
long-lived session every answer after the first edit is computed against a stale snapshot, and a
newly created sub-document is invisible for the process's lifetime. The proposal is to invalidate and
rebuild on document change, behind a debounce.

**Blast radius — a design decision, not a fix.** A rebuild costs a full index build, which is the cost
residency exists to amortise; rebuilding eagerly would give back the entire justification for the
surface being a server. So the change is inseparable from a **debounce policy** — how long after the
last edit, and whether a partial invalidation (one component's caches rather than the whole index) is
worth its complexity. Both are choices with no obviously correct answer and no operator in a cloud run
to approve one.

⛔ **Every timing figure in this area is a lead, not a fact.** The ~2.5 s build figure this question was
originally framed around was later shown to be measurement contention and re-measured materially
lower. Re-measure before designing around any number, and state the measurement conditions.

**What would settle it.** A measured rebuild cost under quiet conditions, and an observed edit cadence
for a real session — the two together decide whether a debounce is even needed, or whether a plain
invalidate-on-change is affordable.

**What the run did instead.** Took the disclosure half. `SKILL.md`, `doc/user/corpus-language-server.adoc`
and the module docstring each now state the staleness bound explicitly — answers may be stale after an
edit, and the remedy is to restart the server or use the `query` verb, which builds fresh each call —
beside the residency claim they sit next to. A test asserts the phrase is present on all three
surfaces.

---

## P5 — Keep unverified sites in the references response, and reword the two pages

**Handed up by:** D5 (`240-skill-lsp-server/gaps.md#G28`), as the option **not** taken.

**What would change.** D5 implemented option (a): omit `verified: false` sites from
`textDocument/references`, which makes the shipped code satisfy the two documents already on `main`.
The alternative, option (b), is the opposite: keep emitting those sites and reword both pages to scope
the "never presented as an exact location" promise to the `query` payload alone.

**Why it was not taken — and why that is not the same as it being rejected.** Option (b) weakens a
shipped guarantee, which is an operator's call rather than an executing run's; option (a) is the
contract-conforming direction and therefore not a contract change the run would be self-approving.
That reasoning is about **which one an unattended run may take**, not about which is better. ⚠ Do not
read the fact that (a) has landed as (b) having been ruled out: the trade below is genuinely open, and
if the measurement goes the other way, (a) is a revert plus two reworded pages — no harder to undo
than (b) would have been to adopt.

**Blast radius — a recall/precision trade, measurable.** Option (a) costs **recall**: a real reference
site that the index cannot confirm no longer appears in an editor's find-references at all. Option (b)
costs **precision**: an unconfirmed site is presented as an exact position, which is what the audit
demonstrated live — an unverified inbound edge emitted `manage-architecture/SKILL.md` line 515, whose
text never mentions the target.

**What would settle it.** The share of sites that are unverified, and how many of those are genuinely
*correct* sites the verifier merely cannot confirm. Note that D5's own G2 fix moves this number: ranking
candidates and refusing to break a tie converts some previously-`verified` sites to unverified, so the
share must be re-derived after that change rather than taken from the audit.

**Mitigation already in place, either way.** The omission is not silent: the withheld count travels
with the answer on each returned `Location` as `omittedUnverifiedCount`, and as a `window/logMessage`
notification — which is the only channel left when every site was withheld and the list is empty. The
`query` verb remains unfiltered and emits every site with its `verified` flag.

---

## P6 — Editor diagnostics on the corpus server: the deferral's premise, re-derived

**Handed up by:** D6 (`240-skill-lsp-server/gaps.md#G10`).

⛔ **This is a proposal and a re-derivation. The run did NOT implement diagnostics, and does NOT
declare the deferral upheld.** Advertising a diagnostic provider binds the surface to the validator's
precision, which is a scope and risk decision.

**The deferral, and what it rested on.** The corpus server advertises no `diagnosticProvider`. The
stated reason — in `SKILL.md`, in the module docstring, and in the user page — is that the validator's
unresolved set is *"overwhelmingly false positives"*, quantified in the user page as roughly 380
unresolved of about 5,300 with close to **97 %** of them not broken references at all.

**Re-derived on this clone.** Command:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  validate --scope marketplace --format json --direct-result
```

⚠ Through the generated executor, not by direct path: the script imports sibling-skill modules
(`marketplace_bundles`, `_dep_index`) that only the executor's injected `PYTHONPATH` supplies, so
running the file directly fails with `ModuleNotFoundError: No module named 'marketplace_bundles'`.
The figures below were taken with that import path supplied by hand, which is equivalent; the
executor form above is the one to reproduce them with.

| Figure | Value |
|---|---|
| Components | 308 |
| Dependencies | 5083 |
| Resolved | 5022 |
| **Unresolved** | **61** |

Classifying those 61 by whether the target is a well-formed component notation whose component
actually exists:

| Class | Count | Share |
|---|---|---|
| Well-formed notation, absent target — no such **script** in an existing skill | 31 | 50.8 % |
| Non-notation — first segment is not a marketplace bundle (build commands like `project:core:compile`, a timestamp placeholder, foreign namespaces) | 26 | 42.6 % |
| Well-formed notation, absent target — no such **skill** | 4 | 6.6 % |
| **Roll-up: non-notations** | **26** | **43 %** |
| **Roll-up: well-formed notations with an absent target** | **35** | **57 %** |

**What the figures say, stated as a measurement rather than a verdict.** The gate reasoning was built
on ~97 % false positives. On the structural classification above, 57 % of what remains is the class
diagnostics exist to surface — a well-formed reference to a component that does not exist — and the
absolute count has fallen by roughly a factor of six. That reverses the ratio the deferral was argued
on. It does **not** by itself settle whether the deferral should end: the "against" case below is
load-bearing rather than a formality, and the criterion at the foot of this item is not yet met.

**The argument on both sides.**

*For advertising diagnostics:* the majority of the remaining unresolved set is real, the total is now
small enough that even the false-positive tail is a handful of squiggles rather than hundreds, and the
class it surfaces — a citation whose target does not exist — is precisely the failure a corpus
language server should catch at edit time rather than at validate time.

*Against:* advertising `diagnosticProvider` binds this surface's credibility to the validator's
precision permanently, and 43 % non-notations is still a substantial false-positive rate on the most
visible surface the corpus has. The classification above is also **structural, not semantic**: it asks
whether the target resolves, not whether the citing author meant it as a reference. Several of the 26
non-notations are deliberate documentation placeholders, and some fraction of the 35 well-formed ones
may be too.

**The criterion that would settle it.** Hand-classify the 61 by *intent* rather than by shape — for
each, is it a citation the author meant to resolve? A false-positive rate low enough to advertise is a
rate an editor user would not learn to ignore, which in practice means single digits. The structural
classification above is the input to that judgement, not a substitute for it.

⛔ **Re-derive these figures before acting on them.** They move with every commit, and this table was
measured once.

---

## D1 — The corpus language server has no consumer, deliberately

**Recorded by:** D6 (`240-skill-lsp-server/gaps.md#G25`). This is a **decision record**, not a
proposal: the state is being left as it is.

**The absence, re-derived.** The claim is an asserted absence, which makes it the highest-risk claim in
this document, so the searches and their results are recorded rather than summarised:

| Searched for | Where | Found |
|---|---|---|
| `lspServers` | every `marketplace/bundles/*/.claude-plugin/plugin.json` | **nothing** — no bundle manifest declares an LSP server |
| `lspServers` | `marketplace/bundles/**` | 2 files, neither a declaration: the skill's own `SKILL.md` (documenting the block an **operator** adds) and a plugin-doctor comment |
| `corpus_lsp` | `marketplace/bundles/**` | the skill's own scripts and `SKILL.md`, plus one plugin-doctor allowlist comment |
| `tools-corpus-language-server` | `marketplace/bundles/**` | the bundle's `plugin.json` skills list (registration), the bundle `README.md` catalogue row, and two cross-references from configuration standards describing the *config surface* |
| `tools-corpus-language-server:corpus_lsp` | `marketplace/bundles/**`, `.claude/**` | **nothing outside the skill's own directory** — no workflow, persona, phase skill or command invokes `preflight` or `query` |

Every hit is registration, catalogue, or documentation. **No component calls this surface.**

**Why the state is left as it is.** Wiring a consumer is a design decision with a real cost, and the
cost has a specific shape: **any consumer paying a one-shot index build per call reintroduces exactly
the ~2 s-per-call cost the resident design was built to avoid.** A consumer must therefore either batch
its queries into one server session or run resident itself. That constraint rules out the obvious
naive integrations, which is why this is a decision rather than an oversight.

**Candidate consumers, if it is reopened.** A plugin-doctor or outline step calling
`query --kind references` in place of a `Grep` sweep is the natural first one — it asks the corpus a
question the index already answers, and it asks it many times, which is the shape that can amortise a
build. Any such integration must batch or run resident.

**⚠ The failure mode this record is guarding against is real and has already happened once in this
epic.** A zero-adoption surface was built and then removed (the LSP query facade, plan 135). That
history *reduces* the risk of leaving this surface unwired — it does not eliminate it, and it is not a
reason to wire one hastily.

**Review trigger — what should reopen this.** Any of:

1. A workflow or phase skill acquires a repeated notation-reference sweep currently done with `Grep`.
2. P6 above is accepted and diagnostics are advertised, which gives the surface an editor-facing
   consumer by construction.
3. A second surface needs the corpus index resident, making the server's residency shared rather than
   unused.

Absent one of those, the surface stays available and unwired, and that is the recorded intent rather
than an omission.
