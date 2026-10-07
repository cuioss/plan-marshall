envelope_version=1
sender_type=plan
sender_id=sweep-preambles-shipped-accessors
epic=test-quality
kind=candidate-lesson
created=2026-09-08T01:51:13Z

# The sweep authored a new false preamble while retiring false preambles

The residual signal-2 candidate: CodeRabbit finding `79d281`, raised and fixed
inside the run. The finding record captures the defect; this captures the
*mechanism that let the sweep ship it*, which is method-level and applies to
every remaining sweep in this epic.

## What happened

D4 (`TASK-004`, commit `552f2747d`) converted
`test/sync-plugin-cache/test_staleness_guard.py::_run_python` onto an explicit
`env=` mapping and, in the same hunk, **authored a new docstring paragraph**:

> The entries are the marketplace `skills/*/scripts` directories only — never
> the repository root — so the `marketplace.targets` package route that both
> callers rely on being unreachable stays unreachable.

That sentence was false on all three of its claims when it was written:

1. **"never the repository root … stays unreachable"** — the code controls only
   `PYTHONPATH`. For a `python -c` launch `sys.path[0]` is the **cwd**, which
   was inherited from the test runner and *is* the repository root. The route
   the sentence declares closed was wide open.
2. **"the marketplace `skills/*/scripts` directories only"** — the code appends
   the inherited `PYTHONPATH` unconditionally
   (`pythonpath + os.pathsep + env['PYTHONPATH']`), re-admitting any repo-local
   entry the parent carried.
3. **"that both callers rely on being unreachable"** — the negative control
   relies on the exact opposite: it inserts `PROJECT_ROOT` deliberately so the
   package *is* reachable, so that what stops the import is the `yaml` blocker
   rather than a missing `marketplace`.

The pre-plan docstring (`b4e8a2364`) made **no isolation claim at all** — it
documented only the dedent hazard. So this is not an inherited falsehood the
sweep failed to catch. The sweep *manufactured* it, in a file it was editing,
on a plan whose entire subject matter is preambles asserting invariants the code
does not establish.

Every internal gate passed it: task verification, the deliverable sweep, the
end-of-phase verification, pre-submission self-review, and the quality gate.
It was caught by CodeRabbit **running a probe** — one `python -c` under the
helper's own launch conditions. `TASK-008` then made the code true (temp cwd +
filtered `PYTHONPATH`) and rewrote the prose.

## Why every gate missed it

**The remedy vocabulary is shape-based; the defect is claim-based.** D1's
disposition column for `subprocess-pythonpath` records remedies as
`run_script` or `explicit env=` — properties of the call's argv/kwargs shape.
D4's success criterion is therefore "does the site now carry an explicit env
mapping?", which is fully satisfied by code whose accompanying prose is false.
The `subprocess-pythonpath` rule cannot check a claim; it checks a shape. A
sweep validated by that rule is structurally blind to its own defect class the
moment it starts writing prose of its own.

**The obligation was attached to inherited prose, not authored prose.** D1
listed exactly two care-needed rows, and gave one of them an explicit
claim-verification obligation:

| D1 row | Obligation D1 attached | Outcome |
|--------|------------------------|---------|
| `test_runner_falsifiability.py:42` | "D4 must confirm propagation does not defeat the declared *isolated from this suite's config* intent" | Discharged. The resulting docstring separates pytest's CONFIG discovery (rootdir/ini/conftest, resolved from target path and cwd, both outside the repo) from module importability, and is **true**. |
| `test_staleness_guard.py:706` | *none* | Author wrote an isolation claim anyway, reasoned only about the variable just written, missed the cwd route, inverted the caller intent. **False.** |

Same task, same author, same commit. Where D1 wrote the obligation the prose
came out correct; where D1 omitted it the prose came out false. The obligation —
not author diligence — is what produced the correct result. And the row that got
it was the one whose isolation claim *already existed*; the row about to have one
*written into it* got nothing. That is backwards: authored prose is precisely the
prose no prior reviewer has ever checked.

## Proposed action

1. **Treat a claim the sweep AUTHORS as a deliverable of the sweep**, verified to
   at least the standard applied to inherited claims. For this epic a sweep that
   writes a false preamble is the highest-severity instance of the thing it exists
   to remove.
2. **Attach the claim-verification obligation per site, from the classification
   artifact**, to every row whose remedy will touch or add prose — not only to
   rows with pre-existing claims. D1 already demonstrates the mechanism works;
   it was simply not applied uniformly.
3. **Verify an environment/isolation claim by running it, not by reading the
   diff.** The falsifying probe here was one line under the helper's own launch
   conditions. Make that the required evidence for any "X is unreachable" claim.
4. **Reusable technical fact:** a `python -c` child has *two* path routes —
   `PYTHONPATH` **and** `sys.path[0]`, which for `-c` is the cwd. Any
   unreachability claim about a `-c` launch must address both. Controlling one
   and asserting the conjunction is the specific error made here.
5. **Never assert what "both callers rely on" without reading both callers.**
   The third falsehood needed no probe at all — only reading the two call sites.

## Scope note — what this is NOT

Finding `a073b5` (pending, deferred) covers the *forward* gap: now that the code
is correct, no test discriminates the isolation, so a regression would silently
restore the un-isolated child and keep both tests green. That is missing
regression protection. This candidate is the *backward* question — how the false
claim was authored and shipped green in the first place. The two are
complementary; neither subsumes the other.

The sibling site `test_runner_falsifiability.py::_run_pytest` carries the same
unconditional inherited-`PYTHONPATH` append, but there it is both harmless and
argued to be harmless in the prose. No live defect; it serves here as the
control.

## Evidence

- `552f2747d` — D4 commit that authored the false paragraph
- `b4e8a2364` — pre-plan `_run_python`, no isolation claim present
- `b64db6671` — squashed landing carrying the `TASK-008` correction
- finding `79d281` — the CodeRabbit inline comment and the triage reply
- finding `a073b5` — the complementary forward regression gap
- `work/d1-finding-classification.md` lines 272-273 — the two care-needed rows
  and the obligation attached to only one of them
