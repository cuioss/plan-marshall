# PLAN-TRUTH-120: Container files have no derivable build route in any project, and the completeness validator cannot see them

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-27 from an operator report against the **API-Sheriff** consumer repo: a
`/marshall-steward` cleanup stripped `Dockerfile*` and `docker-compose*.yml` routes that project needs,
and the reviewer's accepted residual states plainly that *"the entries aren't derivable, so the next
`/marshall-steward reconcile` strips them again"*. Root cause re-derived first-party in the
plan-marshall tree at `26645688b`; the chain below is read from source, not from the report.

## Objective

**No container file has a derivable `build.map` route in ANY project, because the only extensions that
contribute routes are BUILD-SYSTEM extensions, and no build system owns container files.**

The chain, each link read at HEAD:

1. `build.map` is re-derived from *"every applicable registered domain extension's `classify_globs()` +
   `classify_build_class()` predicates"* (`marshall-steward/references/build-map-setup.md`).
2. ⛔ **`classify_globs` is implemented ONLY inside the `plan-marshall` bundle, and only by `build-*`
   skills** — `build-maven`, `build-npm`, `build-pyproject`, `build-gradle`. **No domain bundle
   implements it at all.**
3. `pm-dev-oci` — the container domain — implements `applies_to_module`, `provides_triage` and
   `get_skill_domains`, and **no `classify_globs` / `classify_build_class`**. Its `applies_to_module`
   already recognises `dockerfile`, `containerfile`, `docker-compose`, `compose.yml`, `compose.yaml`,
   `.dockerignore`. ⇒ **The domain is DETECTABLE and contributes ZERO routes.**
4. The base `classify_globs` returns `[]` by design — *"build extensions that own no buildable file
   types contribute no routes."* ⇒ The absence is silent and correct at every individual link.
5. `build-map seed --force` *"bypasses the write-once guard … clears any existing `build_map` and
   re-derives a clean one"* ⇒ **the hand-added container routes are stripped, and the strip is CORRECT
   given the derivation. The derivation is what is incomplete.**

⛔⛔ **And the validator that exists for exactly this cannot see it.** `validate_tree_completeness`
returns *"uncovered git-tracked source files **within buildable-unit roots**"* and states outright that
a tracked file *"outside every build-covered root"* is excluded. A root-level `Dockerfile` in a Java
project is outside every maven build-covered root ⇒ **it is not reported as uncovered; it is not in the
population at all.** ⭐ **A completeness check whose scope excludes precisely the files that have no
owner reports "nothing uncovered" over a population defined to omit the gap** — this epic's archetype,
in the one detector built to prevent it.

⚠ **Nothing downstream catches it either**, and the operator established this half: `.plan/marshal.json`
is not a build-triggering path, so CI cannot see the strip; and `.github/workflows` is org-managed by
`cuioss-organization`, so the consumer cannot add a gate there. ⛔ **Do not propose a CI check in the
consumer repo as the remedy** — that avenue was examined and correctly left alone.

## Deliverables

1. **D0 — GATE: decide WHERE a container route may legitimately come from, and record the decision.**
   Three candidate shapes; ⛔ **do not implement before this is settled, because they have different
   architectural costs.** (a) `pm-dev-oci` gains `classify_globs` / `classify_build_class` — ⚠ but it is
   a **domain** bundle, not a build system, and step 2 above establishes that route-contribution has so
   far been a build-system-only capability; adopting (a) widens the extension contract and that widening
   is the deliverable, not a side effect. (b) A build-system-agnostic container route source. (c) A
   sanctioned **operator-declared** region of `build.map` that survives re-seed. ⭐ **(c) addresses the
   operator's actual complaint — a legitimate hand-edit is not durable — and is the only option that
   generalises beyond containers.** ⚠ A partial affordance already exists and must be read before
   choosing: `build-map drift` is documented as preserving *"a deliberate hand-edit … unless the
   operator explicitly accepts the re-seed"*, while `--force` discards unconditionally.
2. **D1 — implement the chosen source so container files route.** Minimum vocabulary from
   `pm-dev-oci`'s own `applies_to_module`, which already enumerates it: `Dockerfile*`, `Containerfile*`,
   `docker-compose*.y*ml`, `compose.y*ml`, `.dockerignore`. ⛔ **Derive the list from that existing
   enumeration rather than re-typing it** — two hand-maintained copies of one vocabulary is the
   producer-consumer drift this epic tracks.
3. **D2 — close the completeness validator's blind spot, or state it.** Either widen
   `validate_tree_completeness` to report tracked files outside every build-covered root, or **publish
   the excluded population** so *"no uncovered paths"* is legible as *"none within build-covered roots,
   which excludes N tracked files"*. ⛔ **A bare zero from a scope-limited check is the defect; either
   remedy is acceptable, silence is not.**
4. **D3 — matched controls.** A project WITH container files gets container routes and a re-seed
   preserves them; a project WITHOUT container files gets none (the negative control that proves the
   routes are applicability-scoped and not unconditional). ⛔ **And a re-seed/`--force` cycle must be
   shown to preserve whatever D0 chose** — that is the regression the operator actually hit, and a test
   that only checks the first seed would pass while the defect stands.

## Claim Labels

- OBSERVED: `build.map` is re-derived from applicable extensions' `classify_globs()` + `classify_build_class()` — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/references/build-map-setup.md`:5
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: build-map-setup.md:5 still states build.map is re-derived from classify_globs() plus classify_build_class()
- OBSERVED: `classify_globs` is implemented only within the `plan-marshall` bundle's `build-*` skills; a repo-wide sweep for `def classify_globs` returns no domain bundle — measured 2026-08-27 at `26645688b`
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: classify_globs is defined only in extension_base.py default plus build-maven/gradle/npm/pyproject extension.py; confirmed via inventory sweep
- OBSERVED: `pm-dev-oci`'s extension defines exactly `applies_to_module`, `provides_triage`, `get_skill_domains` — no `classify_globs`, no `classify_build_class` — read at `marketplace/bundles/pm-dev-oci/skills/plan-marshall-plugin/extension.py`:17, :61, :65
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: STALE: pm-dev-oci extension.py now ALSO defines provides_file_globs (Axis-A), so the exactly-three-methods count is wrong; the substantive half survives (still neither classify_globs nor classify_build_class). Re-scoped -- and the decisive finding is that doc/adr/004 is Accepted, names this gap INTENTIONAL, warns a reader may misread it as a defect, and explicitly rejects D0 option (a). Operator d
- OBSERVED: that extension's `applies_to_module` already enumerates the container filename vocabulary (`dockerfile`, `containerfile`, `docker-compose`, `compose.yml`, `compose.yaml`, `.dockerignore`) — read at the same file :25-31
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: extension.py container_filenames vocabulary present and now expanded to 10 entries including .hadolint and .trivyignore
- OBSERVED: the base `classify_globs` returns an empty list by design — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py`:1395 § docstring "The default implementation returns an empty list"
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: extension_base.py classify_globs default returns an empty list: build extensions that own no buildable file types contribute no routes
- OBSERVED: `build-map seed --force` clears any existing `build_map` and re-derives — read at `build-map-setup.md`:38
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: build-map-setup.md:38 confirms --force clears the existing build_map and re-derives
- OBSERVED: `validate_tree_completeness` is scoped to buildable-unit roots and explicitly excludes a tracked file outside every build-covered root — read at `extension_base.py`:339-355
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: validate_tree_completeness is still buildable-root-scoped; but doc/adr/004 rules this exclusion INTENTIONAL, not a defect, and rejects D0 option (a) outright
- OBSERVED: the affected consumer config currently carries the container routes under `build.map.java` — read at `/Users/oliver/git/API-Sheriff/.plan/local/worktrees/distroless-health-check/.plan/marshal.json`
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The cited API-Sheriff worktree .plan/marshal.json no longer exists on this machine
- ⭐ **HYPOTHESIS, and it sharpens the operator's report:** because those entries sit under the **`java`** domain key, they would be stripped **even if `pm-dev-oci` gained routes**, since an oci route would seed under a different key. ⇒ The consumer's current hand-fix is in a bucket the java derivation can never produce. Confirm/refute at the seed aggregator's domain-keying (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Domain-keying stripping oci under a different key was not directly tested; moot since ADR-004 rejects oci gaining routes regardless
- HYPOTHESIS: `build-map drift` would report these as `removed_globs` before a re-seed, so the strip is *detectable* by an operator who runs it — the report's claim that CI cannot catch it is about CI, not about the verb. Confirm/refute by running `build-map drift` against that config (verify-at-outline). ⚠ **This does not soften the defect** — a strip that requires an operator to run a detection verb at the right moment is not a guard.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: build-map-setup.md drift gate confirms removed_globs detection plus hand-edit preservation; runs automatically at menu-mode entry
- Verify-first clause: before scoping D1, settle whether `build.map` is keyed by BUILD SYSTEM or by DOMAIN. Every observed key so far (`java`, `javascript`) is ambiguous between the two readings, and D0's option (a) is only coherent under the domain reading. Refutation re-scopes D0 toward (b) or (c).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_build_map.py docstring says a per-domain inventory, confirming domain-keying; doc/adr/004 already settles D0 regardless by rejecting option (a) structurally

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-dev-oci/skills/plan-marshall-plugin/extension.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py`:339 `validate_tree_completeness`, :1395 `classify_globs`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/build-map-setup.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — the build-map seed/drift implementation (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/**` — the authoritative `build.map` schema and the closed `build_class` set (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/extension-contract.md` § `classify_globs()` — the contract D0 option (a) would widen (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/script-shared/**` and `test/plan-marshall/marshall-steward/**` — the D3 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-104` — D2 is another empty-population verdict, but at a different call site; cross-reference rather than merge.
- Adjacent to: `PLAN-TRUTH-117` — D2's *"publish the excluded population"* is the same discipline as its D3.
- ⚠ **Consumer-repo coordination:** API-Sheriff currently carries the routes as a hand-edit that a re-seed will strip. ⛔ **Do not edit that repo from this plan** — it is outside the write boundary. The landing should state what the consumer must re-run once the derivation lands.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-120-container-files-have-no-derivable-build-route-in-any-project.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⛔⛔⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d`. AN ACCEPTED ADR ALREADY SETTLES THIS SPEC, AND REJECTS ITS D0 OPTION (a).

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 2 | `pm-dev-oci`'s `extension.py` defines **exactly** three methods | **STALE** — it now ALSO defines `provides_file_globs` (Axis-A). The substantive half survives: it still defines **neither** `classify_globs` nor `classify_build_class`. |

⛔⛔⛔ **THE DECISIVE FINDING IS NOT A CLAIM VERDICT — IT IS THAT `doc/adr/004` ALREADY DECIDED THIS.**
That ADR is **Accepted**, it names the `pm-dev-oci` / container-manifest routing gap as an
**INTENTIONAL consequence**, it **explicitly warns that a future reader may "misread the absence as a
defect and re-add domain-based routes,"** and it **explicitly REJECTS this spec's D0 option (a)**
(reparenting `pm-dev-oci` onto `BuildExtensionBase`) on two independent grounds.

⇒ ⛔ **This spec, executed as written, would do the thing the ADR forbids — and the ADR predicted the
reader who would try.** Ten of its eleven claims are individually accurate; **the spec is
well-evidenced and aimed at a settled decision.**

⭐ **Recommended disposition: SUPERSEDE, do not execute.** ⛔ **The spec file is NOT deleted** — it is
the audit record of why this was retired, and the ADR's own warning makes that record load-bearing for
the next reader who rediscovers the gap. ⚠ **Residue worth keeping IF anything survives**: whether
container files should get a build route at all is an ADR-amendment question for the ADR's owner, **not
a plan in this epic.** ⇒ **Operator decision owed before this spec is emitted or retired.**

## ⛔⛔⛔ SUPERSEDED 2026-09-05 — operator decision at cleanup. DO NOT EXECUTE. DO NOT DELETE THIS FILE.

**Superseded by `doc/adr/004`**, which is **Accepted** and already decides this spec's whole subject.

⭐ **The positive account, which is what licenses the retirement** (an absent symbol never would):
ADR-004 names the `pm-dev-oci` / container-manifest routing gap as an **INTENTIONAL consequence** of
the file-to-build contract being owned by build-system extensions rather than language/content domains;
it **explicitly warns that a future reader may "misread the absence as a defect and re-add domain-based
routes"**; and it **explicitly REJECTS this spec's D0 option (a)** (reparenting `pm-dev-oci` onto
`BuildExtensionBase`) on two independent grounds.

⛔ **Ten of eleven claims here are individually ACCURATE.** This spec is not wrong; it is **aimed at a
settled decision**. That distinction matters for anyone reading it later: the observations stand, the
conclusion does not follow, and the ADR is the reason.

⭐⭐ **THIS FILE IS THE AUDIT RECORD AND IS LOAD-BEARING.** ADR-004 predicted the reader who would
rediscover the gap and try to fix it. **This spec is that reader, caught.** The next one will find this
file, and it is cheaper than re-deriving the whole investigation to reach the same stop.

⚠ **The one residue that is NOT retired**: *should container files have a build route at all?* is an
**ADR-amendment question for ADR-004's owner** — not a plan in this epic. It is recorded here and
staged nowhere.
