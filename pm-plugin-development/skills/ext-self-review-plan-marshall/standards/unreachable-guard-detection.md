# Unreachable-Guard Detection — Gate Verdict

Design rationale for the reachability candidate list this skill surfaces. Records the gate decision
that selected the framing, the framings that were rejected and why, the discriminator that explains
when this skill's surfacing pass sees a structural defect and when it cannot, and the explicit
in-or-out rulings on two adjacent surfaces.

The defect class: a newly-added guard whose refusal path can never fire a true positive. The guard is
present, its tests are green, and it reports nothing — because the predicate feeding it collapses
every input to the same value. The refusal is unreachable, so the guard's greenness carries no
information.

## 1. Decision

**Framing (b), predicate-over-parsed-structure (scan-versus-anchor), is selected.**

The candidate list surfaces an added Python function that derives an identity key by **scanning an
unbounded decomposed sequence for a first pattern match**, rather than by **indexing that sequence at
a position anchored on a known root**. Concretely, three conjuncts — two of which fire the candidate,
the third of which rides on it as a flag:

1. **(fires)** the function decomposes a value into segments (`Path(...).parts`, `.split(sep)`);
2. **(fires)** it selects a segment by first-match of a compiled pattern iterated over that
   decomposition, exiting the loop on that first match, and returns that segment (or a neighbour of
   it) as a key;
3. **(flag, not a firing condition)** a caller consumes that key as an **identity** — grouping by it,
   comparing it for equality, or testing the cardinality of the resulting key set.

**Why the third conjunct is a flag rather than a firing condition.** The consuming caller is
frequently outside the diff — in #1013 it happened to be in the same commit, but a scanning key
derivation added to serve a caller that already exists on `main` is the ordinary case. Gating the
candidate on finding that caller would make the check depend on a fact outside the change surface,
which is exactly the blindness § 3 identifies as the reason the missed instances were missed. So
conjuncts 1 and 2 fire the candidate and the third is recorded as a `key_consumed` boolean on the
entry — the same Tier-2-flag-riding-on-a-candidate shape `symmetric_pairs.test_present` established.
`key_consumed: true` is corroboration that raises the candidate's priority for the adjudicating check;
`false` narrows what the adjudication must go looking for, and never suppresses the candidate.

The list **is summed into `counts.total`**: it flags a specific added line (the scan loop), which is
the criterion that separates the line-level heuristics from the review-anchor/index lists.

Framings (a) and (c) are rejected. Their rejection is not a ranking preference; each fails a specific,
stated bar, recorded in § 2.

The list is **surfacing-only**, exactly like the eighteen sibling candidate lists: it records
candidates and never blocks, never self-adjudicates, and never asserts cleanliness on its own. The
adjudication is the consumer's cognitive check.

**How the selected check is verified to reach a true positive.** A gate that selects a check for the
unreachable-predicate class and then ships a check that cannot itself fire would be this plan
committing its own subject-matter defect. The verification is executable, not asserted in prose: the
dedicated regression pins the #1013 pre-fix scanning form as an input the new check surfaces, AND
asserts — as a real assertion, not a docstring claim — that **no pre-existing candidate list surfaces
it**. The first half proves the true-positive path is reachable; the second proves the reachability is
attributable to this check rather than to an incidental hit from a sibling detector. The post-fix
anchored form is pinned as the negative, proving the check discriminates rather than fires on the
shape's whole family.

## 2. Framings evaluated, cheapest first

Each framing carries its own false-positive assessment. They are not covered by a single blanket
judgment, because they fail at different points and two of the three are cheap enough that a blanket
"too noisy" verdict would be the wrong reason to drop them.

### (a) New-guard-without-a-failing-test

*Shape:* a diff adds a refusal or guard path, and no test asserts that the refusal fires.

*Cost:* cheapest of the three. The machinery already exists — `_load_test_tree_blob` reads the test
tree once, `_name_in_test_blob` answers word-boundary membership against that blob, and the
`symmetric_pairs.test_present` flag is the established precedent for a Tier-2 missing-test signal
riding on a candidate entry. A guard-name membership query would reuse both helpers with no second
test-tree walk.

*False-positive assessment:* moderate, and bounded — a private helper referenced only indirectly by
its caller's tests would surface as untested when it is in fact exercised. That noise level would be
tolerable on its own for a surfacing-only list.

*Why it is rejected — a false NEGATIVE on the worked example, which is disqualifying here.* The
#1013 guard `_check_emitted_path_provenance` **had tests**. The same commit shipped unit coverage in
`test_generate_executor.py` and an end-to-end fixture-driven regression in
`test_executor_version_split_regression.py`. `test_present` would have resolved `true` and the framing
would have surfaced nothing on the one instance it exists to catch. The deeper reason generalises past
this instance: **a test's presence is not evidence of a predicate's reachability.** #1013's tests
exercised the guard through synthetic fixtures whose paths happened to split correctly, so they proved
the guard fires on inputs where the predicate works — and said nothing about the input family where it
collapses. A framing whose signal is "is there a test" cannot distinguish "the refusal was asserted to
fire" from "the refusal was exercised on inputs that never reach it". Rejected: it does not clear the
worked example, and its blindness is structural rather than incidental.

### (b) Predicate-over-parsed-structure (scan versus anchor)

*Shape:* a new predicate derives a key by first-match over an unbounded sequence instead of by
anchoring on a known root. It is the literal shape of the worked example.

*Cost:* moderate. It is a pure structural read of the added lines — a decomposition call, an iteration
with a first-match return, and a caller that treats the result as an identity. No test-tree index, no
semantic model, no cross-file resolution beyond the diff the surfacer already holds.

*False-positive assessment:* the raw shape "return the first element of a sequence matching a pattern"
is a common and usually correct idiom, and firing on it unconditionally would be noisy enough to
degrade the surface. The three-conjunct narrowing in § 1 is what brings it under the bar: requiring
the sequence to be a *decomposition of a single value* and the result to be consumed as an *identity*
excludes the ordinary search-a-list uses, which neither decompose nor key on the result. Residual
false positives remain — a scan over a decomposition can be correct when the domain genuinely admits
only one matching segment — and they are accepted for two reasons. First, the list is surfacing-only,
so a residual candidate costs one LLM adjudication, never a blocked build; the entire eighteen-list
surface is calibrated to that cost. Second, and more importantly, **a scan over a decomposition that
is correct today is correct only for as long as the domain admits exactly one match** — which is
precisely the assumption whose silent violation produced this defect. Surfacing it for adjudication is
the right disposition even in the cases that turn out to be fine.

*Selected.* It clears the worked example, it needs no fact from outside the diff (see § 3 for why that
property is load-bearing), and its noise is bounded by the surfacing-only contract.

### (c) Fixture-contradiction

*Shape:* a newly-added regex is tested against string literals already present in the test tree; a
literal that matches the new pattern in a context contradicting the pattern's intended domain is the
contradiction.

*Cost:* cheap — the same read-once test-tree blob, plus applying each newly-compiled pattern to the
literals in it.

*Concrete instance:* #1013 added `_VERSION_DIR_NAME_RE = re.compile(r'^\d+\.\d+')` to identify
plugin-cache **version directories**. The repo's own test tree already pinned
`test_non_versioned_bundle_starting_with_digits`, which constructs the bundles `1.0-bundle-a` and
`2.0-bundle-b` to pin the supported convention — documented in `find_bundles` as `1.0-my-bundle` —
that a top-level **bundle name** may itself begin with `N.N`. Both fixture literals match the new
pattern. The contradiction the vacuous guard depended on was sitting in the repo's own fixtures, which
is exactly the kind of fact a deterministic in-house check is well-placed to hold and a human reviewer
is not.

*False-positive assessment — this is where it fails.* "A newly-added regex matches a literal in the
test tree" is the **normal** case, not the anomalous one: most added regexes exist precisely because
their patterns match values the tests already construct. The detector fires on nearly every added
pattern, so the signal-to-noise ratio is inverted and the list would drown the surface it is meant to
sharpen. Narrowing does not rescue it, because what makes `1.0-bundle-a` a contradiction rather than a
match is the pattern's **intended domain** — "this names a version directory, not a bundle" — and the
intent lives in the author's head and the surrounding prose, not in any structure the surfacer reads.
A detector that needs an intent model to separate its true positives from its ordinary matches does
not clear the false-positive bar as a standalone list.

*Rejected as a standalone candidate list.* The observation it encodes is retained in a different
place: it is the **evidence a human or the cognitive check reaches for when adjudicating a framing (b)
candidate** — once the scan-versus-anchor shape is surfaced, "is there a literal in this repo that
lands in the scanned sequence and matches?" is the question that resolves the candidate. Demoting it
from a producer to an adjudication input is the disposition, not discarding it.

## 3. The discriminator — when this surface sees a defect and when it cannot

The gate is not uniformly blind, and a fix scoped on the assumption of total blindness would be scoped
wrong. This surface caught a description-versus-body drift before push during the PLAN-55 era; on
#1027 it found five real defects including two vacuous guards; and on #1038 it caught the plan
**reproducing its own target defect** — `phase-4-plan` Step 8 parsing only `total_failed` and
`ambiguous` while silently dropping a rejected persist at a call site that same plan had just created.
It has also returned CLEAN over real defects on #1013, #1022 and #1027.

**Volume is not the discriminator, and a volume-based remedy is refuted by the evidence.** #1038's
defect was caught at 38 candidates; #1013's was missed at 50 and #1022's at 75. If candidate count
governed, the small run would have been the blind one. It was the sighted one. A remedy aimed at
raising or lowering the candidate count would have changed nothing about any of these outcomes.

**The discriminator is co-presence.** This surface sees a defect exactly when **both halves of the
contradiction appear as tokens inside the change surface it reads**. It cannot see a defect when
establishing the contradiction requires something that is not two co-present tokens. Three distinct
non-co-present classes account for every missed instance:

- **A fact outside the diff.** #1013's added lines are internally consistent: a scan for a
  version-shaped segment, returning the segment before it. Nothing in the diff says a bundle name may
  begin with `N.N`. That fact lives in a test fixture and a docstring elsewhere in the repo, so no
  amount of reading the diff harder recovers it.
- **A property over execution rather than over text.** #1022's `ci_complete_precondition.py::resolve`
  rebound `timeout_seconds` at a clamp settle point and then used the rebound name as the ratchet's
  comparison base, so the learned value drifted downward on every deadline-exceeded finalize. Both
  tokens are present; the defect is that the *meaning* of one name changes across a rebinding. That is
  dataflow, not co-presence. #1027's `cmd_inbox_archive` TOCTOU is the extreme of the same class: it
  requires running an interleaving, so no static structural read can falsify it at all.
- **The case space of an already-surfaced candidate.** #1027's `_section()` was surfaced and
  *examined*; the review reasoned correctly about the `####` nesting case and never checked the `##`
  boundary. The candidate was seen; the coverage inside it was partial. This is a distinct failure
  from never-surfacing and it needs a different remedy — recording *which cases were checked*, not
  merely that the candidate was looked at.

#1038 sits on the other side of the line and confirms it: both halves were co-present tokens in the
added lines — the set of outcome keys the persist call produces, and the strictly smaller set the
parse consumed. Reading the added lines was sufficient. That is why 38 candidates were enough.

**What the discriminator implies for the selected framing.** Framing (b) is selectable *because it
does not need the outside fact*. It flags the **shape that makes an outside fact load-bearing**: an
unbounded first-match scan is defeated by the existence of *any* out-of-domain segment, so the check
never has to know which one exists. Framing (c) is rejected in part for the mirror-image reason — it
tries to find the specific outside fact, and the search for it is what makes it noisy. The
discriminator is therefore not a postscript to the decision; it is the reason the decision came out
the way it did.

## 4. Worked example — PR #1013, `_split_bundle_version`

`fix(executor): single-source version-dir selection across resolvers` (#1013, commit `144d68483`)
added `_check_emitted_path_provenance` — Guard 4, which refuses to write a version-split executor —
fed by `_split_bundle_version`.

### Pre-fix form (scanning)

```python
def _split_bundle_version(path: str) -> tuple[str, str] | None:
    parts = Path(path).parts
    for index, part in enumerate(parts):
        if index > 0 and _VERSION_DIR_NAME_RE.match(part):
            return parts[index - 1], part
    return None
```

### Post-fix form (anchored)

```python
def _split_bundle_version(path: str, base_path: Path) -> tuple[str, str] | None:
    """Return ``(bundle, version_dir)`` for a path inside a versioned cache layout.

    A plugin-cache path is ``{base}/{bundle}/{version}/skills/...``, so the split is
    anchored on the known cache root: the path is relativized against ``base_path``
    and the first two segments ARE the bundle and its version dir. Anchoring is
    load-bearing — scanning for the first version-shaped segment anywhere in the
    path mis-splits on two real inputs: a version-shaped ANCESTOR directory above
    the cache root (``/srv/1.0-workspace/cache/{bundle}/{version}/…``) and a bundle
    whose own name starts with ``N.N`` (``1.0-my-bundle``, the supported naming
    convention ``find_bundles`` gates on ``bundle_dir.parent != base_path``). Either
    returns the wrong key and silently defeats the provenance guard.

    Returns ``None`` when the path lies outside ``base_path`` (a project-local
    ``.claude/skills`` script) or when its bundle segment carries no version dir —
    the marketplace layout, where the provenance guard has nothing to compare.
    """
    try:
        relative = Path(path).resolve().relative_to(Path(base_path).resolve())
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) < 2 or not _VERSION_DIR_NAME_RE.match(parts[1]):
        return None
    return parts[0], parts[1]
```

### The reachability argument

Guard 4 groups every path the generated executor is about to embed by owning bundle, collects the set
of version directories each bundle contributes, and refuses the write when any bundle's set has more
than one member:

```python
by_bundle.setdefault(bundle, set()).add(version)
...
if len(versions) > 1:
```

The refusal is therefore reachable only if `_split_bundle_version` can return **two different
`version` values for the same `bundle` key**. Under the pre-fix scanning form, take a bundle whose own
directory name begins with `N.N` — `1.0-my-bundle`, the convention `find_bundles` documents and
`test_non_versioned_bundle_starting_with_digits` pins. Every emitted path under that bundle begins
with the same version-shaped segment: the bundle name itself. The scan stops at the first match, which
is that segment, for every path. So every path under the bundle yields the identical `(bundle,
version)` pair, `len(versions)` is 1 for all of them, and `len(versions) > 1` is unsatisfiable.

The same collapse occurs from the other direction with a version-shaped **ancestor** directory above
the cache root (`/srv/1.0-workspace/cache/{bundle}/{version}/…`): the scan stops at `1.0-workspace`
for every path in the tree, again producing one identical key.

The guard is present, its tests are green, and its refusal branch is dead. That is the class: not a
guard that is wrong, but a guard whose greenness is uninformative — it cannot distinguish "no
version split occurred" from "I am incapable of observing a version split". Both bots that reviewed
#1013 filed it from the diff alone, so the information needed was present in the change; this
surface's disadvantage was a missing check, not missing information.

The anchored form makes the refusal reachable again: the split is taken at a fixed position relative
to a known root, so the version segment is whatever actually sits at that position, and two paths
under one bundle can genuinely disagree.

## 5. Ruling — `finalize-step-simplify` is OUT of scope

`finalize-step-simplify` also reported 0 findings on #1013, and the question of whether it shares this
reachability blindness is settled here as a **ruling**, not carried as an implementation obligation of
this plan.

**Ruled OUT.** Its mandate is the deletion of *surplus structure* against the minimum-viable-code
anti-patterns — unused parameters, thin re-export shims, defensive catch-alls around already-handled
failures, near-identical collapsible helpers, signature-restating docstrings, single-caller config
keys, and speculative abstractions with no second implementation. A vacuous guard is none of these. It
is a guard at a real boundary with a live caller, and the simplify prompt carries an explicit carve-out
instructing the pass **not** to delete a guard sitting at a real I/O or external-input boundary. Its
0-findings report on #1013 was therefore *correct under its own contract*: there was no surplus
structure to delete, and the one structure it might have noticed is the one it is told to leave alone.

Extending it to reachability would invert that carve-out — the pass would have to distinguish "a real
boundary guard, keep it" from "a real boundary guard that cannot fire, flag it", which is a
correctness judgment, not a simplification judgment. Reachability belongs on the surfacing pass this
skill owns, where a candidate is a question for adjudication rather than a deletion proposal. No
change to `finalize-step-simplify` follows from this plan.

## 6. Labelled, deliberately not solved — concurrency and TOCTOU

Concurrency and TOCTOU-class defects are **named here and explicitly out of scope for this check.**
The reference instance is #1027's `cmd_inbox_archive`, whose docstring promised *"idempotent on
repeat"* and *"safe to resume"* while carrying a genuine time-of-check-to-time-of-use race that an
external reviewer found after six in-house rounds had validated the prose.

Per § 3 that defect is not a co-presence failure and not a missing-check failure: it is
unfalsifiable by a static structural reviewer by construction, because no in-house gate runs the
interleaving. No candidate list added by this plan detects it, and none should be read as covering it.
Adding a check that pattern-matched concurrency prose would reproduce the exact defect this document
exists to characterise — a predicate that cannot reach a true positive.

The disposition is honesty rather than coverage: such a claim must be **labelled unverified rather
than silently cleared**, which is the job of the clean-verdict scope split — a clean verdict that
states *which* checks matched nothing, instead of reading as an assertion that nothing is wrong.

## Related

- [`../SKILL.md`](../SKILL.md) — the surfacing contract and the detection rule this verdict specifies
- [`../../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`](../../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md) — the extension-point schema the candidate key joins
- [`../../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md) — the consuming cognitive review and the clean-verdict scope split
- [`../../../../plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md`](../../../../plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md) — the adjacent surface ruled out of scope in § 5
