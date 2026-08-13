# Verdict Currency — what re-stales a finalize verdict, and what it costs

The dispatcher's re-entry check re-fires a head-dependent step whose recorded
`head_at_completion` differs from the live worktree HEAD (see
[`../SKILL.md`](../SKILL.md) § "Special case — HEAD-dependent steps"). That rule is
safe. Left as a bare SHA inequality it is also **maximally expensive**: one finalize
advances HEAD many times, and each advance re-stales every verdict recorded before
it — mostly re-confirming the identical answer.

This document owns the model that bounds it. It states **which events advance HEAD**
inside finalize (the trigger set), **what a re-stale costs** per step, **how an
advance is classified** as invalidating or not, and **how the re-fire count is
obtained**. It does not restate head-dependence membership, which is declared per
step and read from frontmatter — see [`../SKILL.md`](../SKILL.md) § "Special case —
HEAD-dependent steps" for the single authoritative statement.

## Two levers, and only one of them was ever pulled

Bounding this cost has exactly two levers, and they are independent:

| Lever | Bounds | Owner |
|---|---|---|
| **Delta-scoping** — a re-run examines only what changed since its own last record | the cost of EACH re-run | the individual gate (e.g. `pre-submission-self-review`'s `--since-ref` anchor) |
| **Re-stale classification** — an advance that cannot change a verdict does not re-run the gate | the NUMBER of re-runs | this document |

Delta-scoping does not reduce the number of re-runs, and pulling it harder never
will. A gate that re-fires seven times with a perfectly-scoped delta still pays
seven envelopes, seven skill loads, and — where the gate carries an unconditional
whole-tree arm — seven whole-tree sweeps. **Read a landed delta-scoping improvement
as bounding the first column only.**

## The trigger set — what advances HEAD inside finalize

A verdict re-stales when, and only when, the worktree HEAD moves. Every mechanism
that moves it during finalize is one of the following. The set is **derived from
declared frontmatter facts**, not hand-maintained: each row names the fact that puts
the step in it, so a step added later is covered by its own declaration.

| Trigger | Declared by | Mechanism |
|---|---|---|
| A settle-band step's edits being committed | `mutates_source: true` on a step ordered `< 11` | the dispatcher's commit instrumentation (Step 3 item 5f) commits the step's output before advancing, which moves HEAD |
| A post-push step's edits being committed | `mutates_source: true` on a step ordered `> 11` and before the merge gate | same instrumentation, plus the item-5f post-PR re-push |
| A baseline rebase replaying commits | `advances_main_via_rebase: true` | the branch's history is rewritten onto a freshly-fetched base tip, so every SHA on it changes at once |
| A loop-back fix commit | the unified wait-region triage opening a fix task | the fix lands as a new commit on the feature branch |

Two properties of this set are load-bearing and easy to get wrong:

- **A rebase re-stales EVERYTHING at once, not incrementally.** Replaying the branch
  changes every commit's SHA, so every head-dependent verdict recorded before it
  fails the equality test in the same instant. It is the single largest re-stale
  event in the pipeline.
- **A rebase that replays nothing advances nothing.** `worktree-rebase-to` reads HEAD
  immediately before and after the rebase and returns `action: noop` with HEAD
  unchanged when the branch already contained the base — and returns `noop` without
  running a rebase at all when the branch is already `clean` relative to it. So a
  rebase step is a re-stale trigger **only on its `action: rebased` return**. A claim
  that an unconditional rebase re-stales every verdict is therefore true of the
  replaying case and false of the noop case; the discriminator is the step's own
  returned `action`, and it is reported on the payload with both SHAs.

## What a re-stale costs

The cost of one re-fire is the step's whole body, not a delta of it — the re-entry
check re-dispatches the step as a fresh run. Two properties make that expensive
beyond the obvious:

- **A dispatched step pays a full envelope per re-fire** — target resolution, the
  agent spawn, the skill loads its prompt body names, and its own tool calls. Delta
  scoping shrinks what the body examines; it does not shrink the envelope.
- **An unconditional whole-tree arm is paid in full every time.** `pre-push-quality-gate`
  scopes its per-bundle sweep to the live footprint but runs its whole-tree
  `quality-gate`, whole-tree `test-compile`, and module-tests gate unconditionally by
  design (see [`pre-push-quality-gate.md`](pre-push-quality-gate.md) § "Whole-tree
  quality-gate arm"). Those arms exist to catch what a scoped run structurally cannot,
  so they are not delta-scopable — which makes not re-running them the only lever
  available on this gate.

The earliest head-dependent steps absorb the most re-fires, because every later
trigger in the pipeline is behind them: a step at `order: 4` is re-staled by every
mutating step, every rebase, and every loop-back commit that follows it, while a step
at `order: 40` is re-staled only by what comes after IT.

## The classification — an advance that cannot change a verdict does not re-run it

A head-dependent step MAY declare `verdict_inputs` — the fnmatch globs naming the
tracked paths whose content its verdict reads (see
[`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md)
§ "Implementor Frontmatter"). Given that declaration, the classifier
`plan-marshall:phase-6-finalize:verdict_currency` answers one question per step:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:verdict_currency classify \
  --step {step_id} --worktree-path {worktree_path} --head-at-completion {recorded_sha}
```

It returns `verdict: preserved` when the **tree difference** between the recorded SHA
and the live HEAD touches none of the declared paths — and on one further path, equal
SHAs, which needs no declaration; it returns `verdict: invalidated` on everything else,
including every uncertainty. The exact reachability is stated once under § "Fail-closed,
structurally" below and not restated here. The dispatcher consumes it at the one branch
where the SHAs already differ.

**Why the rule is a purity argument, not a heuristic.** A step's verdict is a function
of the content of its declared inputs. When that content is byte-identical between the
two trees, re-running the step recomputes the same verdict by construction. Nothing is
being predicted or estimated — the skip is licensed by the declaration itself, which is
why the declaration must be substantiated arm-by-arm from the step's own doc rather
than guessed.

**Why a tree diff rather than a commit walk.** `git diff --name-only {recorded} {live}`
compares two trees. That is correct under all three supersession mechanisms the
dispatcher must handle — a loop-back commit, a force-push, and a rebase — because none
of them changes what the two trees contain, and it needs no separate detector per
mechanism. It is also strictly narrower than a commit walk: a change and its revert
cancel out, and a rebase folding in upstream commits that touch nothing in the surface
reports no difference on that surface.

**Fail-closed, structurally.** `preserved` is reachable only past a resolution gate — the
step doc resolved AND the step declares `head_dependent: true` — and past that gate on
exactly two paths, each of which *proves* the recorded tree is still in force: the two SHAs
are equal (byte-identical trees, decided without consulting any declaration), or a non-empty
declaration's globs match no path in the tree difference. Every other path returns
`invalidated` with a `reason` naming the uncertainty: an absent declaration on a genuinely
advanced HEAD, an unresolvable step doc, unavailable discovery machinery, an absent recorded
SHA, or a tree diff git could not compute (a SHA that no longer resolves after a force-push
and a prune is exactly this case). An unnecessary re-run costs tokens; a skipped necessary
one costs correctness, so the asymmetry is built into the control flow rather than stated as
guidance.

**A declaration is admissible only when it is a SUPERSET of what the step reads — and some
steps have no such subset.** The bar is not "name the paths the step obviously cares about";
it is "name a set the step's verdict provably cannot depend on the complement of". The
distinction that decides it is what the step's body *does*:

- **A verdict that is a property of NAMED FILES is trivially declarable**, and its surface is a
  superset by construction rather than by survey. `project:finalize-step-era-stamp-fill` is the
  worked positive case: it asserts that two files — named by full path in its own doc, and the
  same pair it stages — carry no unresolved sentinel. Its declaration names a third path, the
  executor whose matcher DEFINES "unresolved", because that is the one other tracked file whose
  change could make the recorded claim false. Which is the general rule for a declaration:
  **name what determines the TRUTH of the recorded claim, not what determines the step's future
  behaviour.** A step's own procedural doc — its staging list, its detail wording — governs what
  it does next time and cannot falsify a verdict already recorded about the tree, so it stays
  out; a file that redefines what the verdict *means* stays in.
- **A verdict produced by a body that executes something OPEN-ENDED over the repository has no
  sound subset at all.** Three shapes recur, and each is independently disqualifying:
  1. **A test suite that asserts against the real tree** — this repository's own pytest reads
     `doc/**`, `.github/**`, and the root agentfile.
  2. **A scan whose inputs are DISCOVERED rather than fixed** — a relative-link checker stats
     every link target it finds, within a repository-root containment boundary, so renaming
     *any* file can turn it red. Its input set is perfectly derivable at run time and
     underivable ahead of time, which is exactly what a static glob cannot express.
  3. **A whole-repo walk** — an analyzer that enumerates files by walking from the repository
     root has the whole tree as its input set by construction.

  A whole-tree declaration in any of these cases would be an inert lever wearing the shape of a
  real one.

The two worked negative cases each exhibit more than one shape, and each refusal is recorded in
that step's own doc rather than left as an unexplained absence:

| Step | Shapes | Refusal recorded at |
|---|---|---|
| `default:pre-push-quality-gate` | 1 (its module-tests arm runs the pytest suite), and 2 + 3 transitively (its whole-tree arm invokes the marketplace-wide doctor pass) | [`pre-push-quality-gate.md`](pre-push-quality-gate.md) § "Verdict-input surface — deliberately undeclared" |
| `project:finalize-step-plugin-doctor` | 2 (`broken-relative-link`) and 3 (the agentfile analyzers) | that step's own § "Verdict-input surface — deliberately undeclared" |

The vocabulary is deliberately static globs; admitting a *derived* surface — a command whose
output is the path set — would make shape 2 declarable, and is not attempted here.

**A preserved verdict keeps its original anchor.** The dispatcher does NOT re-stamp
`head_at_completion` to the live HEAD on a preserved skip. Re-stamping would make the
record claim the verdict was computed against a tree it was never computed against —
the exact false-currency signal this mechanism exists to remove. Keeping the original
anchor also makes the classification monotone: the diff range only grows, so the first
advance that touches the surface invalidates the verdict no matter how many preserved
advances preceded it.

**A remote-state verdict declares no surface.** `ci-verify`, `automatic-review`, and
`sonar-roundtrip` record verdicts about the *pushed* HEAD, not about the local tree.
Any advance that reaches the remote re-stales them regardless of which paths moved, so
they carry no `verdict_inputs` and keep the unconditional re-fire.

## Ruling — the pre-merge rebase is conditional on the merge queue

`branch-cleanup` rebases the feature branch onto the freshly-fetched base tip before
merging. The rebase has two stated purposes: the merged history is a linear append, and
CI runs against the exact commits that will land. **Both purposes are already discharged
by the merge queue when one is in use**, and this document records the resulting ruling
so the deviation stops being unwritten:

- **`use_merge_queue == true` — the pre-merge rebase is redundant, and is skipped.** The
  queue re-tests the branch against the latest base and refuses a still-red one; the
  same document already downgrades the pre-merge CI wait to a non-authoritative snapshot
  for exactly this reason. A rebase performed here duplicates the queue's own work while
  paying its full price: on a replaying rebase every recorded verdict re-stales at once,
  which is the pipeline's largest single re-stale event.
- **`use_merge_queue == false` — the rebase stays unconditional.** The immediate
  `pr safe-merge` path has no queue re-test, so the rebase plus the authoritative CI wait
  after it ARE what make the merged history linear and verified. Nothing else discharges
  those purposes on this path, so removing it here would trade a real safety property for
  a cost saving.

The ruling is therefore not "the rebase was always unnecessary" and not "skipping it was
unsafe" — it is that its necessity is a function of `use_merge_queue`, and the operator
deviation that prompted this ruling was correct **on the path it was taken on**. The
mechanics live at [`branch-cleanup.md`](branch-cleanup.md) § "Rebase Branch onto Base"; this
section is the ruling, not a second implementation of it.

## Obtaining the re-fire count

The count is **derived from instrumentation that already exists**, not from a new
emitter. `record-step` appends one `execution_log[]` row per firing — for every finalize
step, dispatched and inline alike — so a step that fired seven times carries seven rows:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  refire-report --plan-id {plan_id} --phase 6-finalize
```

Per step it reports `firings`, `refires` (`max(0, firings - 1)`), `skipped`, `errors`,
and the summed token-attribution triple, sorted worst-offender first.

**`refires` counts extra firings, NOT re-stales — the causes are several and the column
does not separate them.** `max(0, firings - 1)` is agnostic about *why* a step fired
again, and at least four mechanisms produce a second `executed` row: the HEAD-advance
re-entry check re-firing a re-staled verdict (the mechanism this document is about), a
`loop_back` record re-firing the step on the next entry, a retry after a `failed` record,
and the `push` barrier's parity-driven re-fire plus its explicit post-PR re-invocation.
Attributing the whole column to the re-stale treadmill would be the confident-but-untrue
framing this epic files against. A before/after comparison over the SAME plan shape is
still sound — the other causes are common to both arms — but a single run's `refires` is
not a re-stale count, and must not be reported as one.

**A preserved skip lands a `skipped` row, so the saving has a positive trace.** The
dispatcher's item-5e `record-step` call fires for every step on every entry, including the
re-entry-check SKIP branches, with `--outcome skipped`. Without that row the saving would
show up only as an *absence* — one fewer `executed` row — which is indistinguishable from a
step that was never in the manifest. `skipped` is therefore counted in its own column and
never folded into `firings`: folding it in would restore the very count the classification
removes and blind the instrument to its own effect.

**`total_tokens` is a floor.** `record-step` receives the `<usage>` triple only for steps
dispatched as Task agents, while every inline step records zeros by contract, so the payload
carries a `token_population` field naming exactly which rows the figure was summed over.
`default:pre-push-quality-gate` is inline AND head-dependent, so the single most expensive
re-firing gate contributes zero to this column. A saving computed from it is stated with
that floor attached, never as a measured total.

## Related

- [`../SKILL.md`](../SKILL.md) § "Special case — HEAD-dependent steps" — the re-entry
  check this model narrows, and the single authoritative statement of head-dependence.
- [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md)
  § "Implementor Frontmatter" — the `head_dependent` / `verdict_inputs` declarations.
- [`pre-push-quality-gate.md`](pre-push-quality-gate.md) § "Verdict-input surface —
  deliberately undeclared" — the worked NEGATIVE case: why this gate's arms admit no sound
  surface, recorded as a refusal on evidence rather than left as an absence.
- [`branch-cleanup.md`](branch-cleanup.md) § "Rebase Branch onto Base" — the rebase site the
  ruling above governs.
