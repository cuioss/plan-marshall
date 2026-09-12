# Machine-global config-scope audit

An enumeration of the sites where a configuration key and the state it governs sit
in different anchoring tiers, each carrying a disposition against two failure
shapes. The population, and the criteria that bound it, are derived in
§ "Population, and how it was derived" rather than asserted here.

- **Shape A — a config key read by a process that has moved its cwd away from the
  key's resolution root.** The cwd-relative resolver (`file_ops.get_base_dir()` /
  `get_marshal_path()`, ADR-002) walks up from the process cwd to find a
  repository. A process that has deliberately moved its cwd — a daemon that
  `chdir('/')` on detach — walks up from a directory with no repository above it,
  finds nothing, and receives the resolver's *absent* answer. Where the consumer
  turns that absence into a default, the result is indistinguishable from a
  configured value: the process reports the default as its setting and no signal
  says the file was never reached.
- **Shape B — a key applied per caller against machine-global shared state.** The
  home-root tier (`marketplace_paths.home_root()`, ADR-008) anchors state to the
  HOST, not to a repository. A key read from the *caller's own* repository and
  then applied to that host-wide state means each caller governs every other
  caller's entries by its own value. Two callers with different values do not
  produce an error; they produce a queue admitted under two different rules, and
  nothing in either caller's view reports the other's.

Both shapes end the same way — a value is applied whose provenance the consumer
cannot state. The governing decisions are ADR-008 (the machine-global home-root
anchor tier), ADR-009 (status reporting fails closed with an explicit unknown
state) and ADR-019 (an unmeasured occurrence is reported as unmeasured, never as
absence). Shape A is the provenance case of ADR-009: a resolution that never
reached its source must not report the value it fell back to as though it had.

## Population, and how it was derived

The universe this audit dispositions is the **machine-global config-scope
surface**: configuration keys whose resolution root and whose governed state are
anchored in different tiers. That criterion — not the word "every" — is what a
later reader re-derives against.

**Method.** Each shape's population is derived in two stages, because no text
sweep can apply either criterion. `architecture search --content` is a regex over
bytes: it returns no line numbers and no line bodies, so it cannot distinguish a
call from a comment, a docstring or a `def` line. A text sweep therefore bounds
the CANDIDATES and an `ast` pass CLASSIFIES them. Narrowing the pattern to a
parenthesised form is **not** a substitute for that second stage — `os.chdir(`
matches a docstring exactly as it matches a call.

**⛔ Sum `match_count` over ONE attribution — never read the top-level `count`.**
The inventory indexes each file twice, once under the `default` module with a
generic category and once under its owning module with a specific one, so an
unscoped sweep returns two rows per file. Every sweep below is scoped
`--category script`, which keeps the owning-module row so each script file
contributes exactly one row. `count` answers "how many attributed rows matched",
`file_count` answers "how many files contain this", and only the `match_count`
sum answers "how many occurrences".

**An agreement between the text figure and the AST figure is a coincidence, not a
validation.** For shape A the parenthesised sweep and the AST pass happen to
return the same three files (below), and that agreement establishes nothing: the
two answer different questions, and they coincide here only because no comment in
this candidate set writes the parenthesis. Verify the method, never the
coincidence.

### Shape A — stage 1, candidate set (text, superset by construction)

`architecture search --content --literal --category script`:

| `--pattern` | `file_count` | `match_count` sum |
|-------------|--------------|-------------------|
| `chdir` | 4 | 7 |
| `os.chdir(` | 3 | 3 |

The bare name is the operative sweep: a call always contains it, so the 4-file set
provably contains every call site. The parenthesised figure is recorded only to
show that it is 3 — one file short of the superset — and that the missing file is
the one the next stage decides.

### Shape A — stage 2, classification (AST, call-aware)

Parse each candidate with `ast` and classify every occurrence of `chdir`,
resolving `import … as` aliases to their target before counting, then keep only
occurrences that are a call's own `func` (`Name(id=target)` or
`Attribute(attr=target)`). A `FunctionDef`, an import alias, a bare non-call
reference and textual residue in comments, docstrings and string literals are all
exclusions.

| File | Call sites | Disposition |
|------|-----------|-------------|
| `manage-build-server/scripts/marshalld.py` | 1 (`double_fork`) | **IN POPULATION — RESOLVED.** `double_fork` moves cwd to `/` so the detached daemon holds no working-directory reference; that move is correct and stays. What made it shape A was the cap read that followed it. The daemon now resolves its cap through `_machine_config.resolve_max_slots()`, which consults only the machine-global file, so nothing in the daemon reads a cwd-relative path after the move. The resolution carries its source, and the daemon re-resolves per submit and reports `max_slots` / `max_slots_source` / `max_slots_detail` on `ping`. |
| `workflow-integration-git/scripts/integrate_into_main.py` | 1 (`_assert_cwd_unchanged`) | **EXCLUDE — a cwd RESTORE, not a cwd move.** The call fires only when the script's own never-change-the-caller-cwd invariant has already been violated: it restores the entry cwd and returns an error payload. Nothing is resolved after it, so no key can be read against a moved root. |
| `workflow-integration-git/scripts/prepare_execute.py` | 1 (`_assert_cwd_unchanged`) | **EXCLUDE — same restore-and-fail guard**, with the same reasoning. |
| `script-shared/scripts/build/_machine_config.py` | 0 | **EXCLUDE — text-only residue, and the counter-example that decides the method.** Both occurrences are module-docstring prose describing the daemon's `chdir('/')` as the hazard this module exists to remove. A criterion that counted text would place the module that CLOSES shape A inside shape A. |

**Shape A figures.** 4 candidate files; 3 call sites over 3 files; **1 file in the
population**. The population is published beside the count so a shrunken
derivation cannot pass as a clean one: three of the four candidates are
dispositioned out on stated evidence, not dropped.

In current state, the number of sites where a cwd-moved process reads a
cwd-anchored config key is **0 out of 1 population member**. That zero is
reportable only because the population it is drawn from is published with it.

### Shape B — stage 1, candidate set (text, superset by construction)

`architecture search --content --literal --category script --pattern home_root`:
`file_count` **12**, `match_count` sum **58**.

The bare name is used deliberately, and one sweep suffices because
`ensure_home_root` contains `home_root` as a substring, so a single pattern bounds
both entry points.

### Shape B — stage 2, classification (AST, call-aware)

The same classifier, over the target names `home_root` and `ensure_home_root`.

| File | Call sites | State reached | Disposition |
|------|-----------|---------------|-------------|
| `script-shared/scripts/marketplace_paths.py` | 1 | the home root itself | **IN POPULATION — JUSTIFY (the resolver).** Holds the sole `def` of both entry points. A definition is not a call, so neither `def` puts the file in the population; it is a member on independent evidence, because `ensure_home_root` itself invokes `home_root()`. `home_root()` is a pure resolver and `ensure_home_root()` is the sole creating variant, so a caller cannot widen the root's permissions by accident. It reads no config key and decides nothing. |
| `script-shared/scripts/build/_machine_config.py` | 2 | `marshalld/machine-config.json` | **IN POPULATION — RESOLVED, and the shape's remedy.** The single reader and writer of the one machine-global config file, in the same tier as the state its key governs. `resolve_max_slots()` consults neither the cwd nor any repository, never raises, and names its source on every resolution (`machine_config`, `default`, `invalid`, `unreadable`), so a fallback is never reported as a configured value. Both writers serialize on one guard file, and the migration writer re-resolves inside that guard. |
| `manage-locks/scripts/build_queue.py` | 1 | `build-queue.json` | **IN POPULATION — RESOLVED for both keys.** The queue is machine-global; both keys that govern it now are too. See § "Member dispositions". |
| `manage-build-server/scripts/marshalld.py` | 2 | `marshalld/` (socket, pidfile, log, job-logs) | **IN POPULATION — JUSTIFY (state, no key).** Resolves the daemon's own state directory in the tier where that state belongs. It applies no per-caller key against it; its cap comes from the machine-global resolver. This file is the single member of BOTH shapes. |
| `manage-build-server/scripts/_marshalld_audit.py` | 2 | `marshalld/` audit record | **JUSTIFY (state, no key).** Resolves its path once at construction and appends the daemon's own audit record. No config key is applied against it. |
| `manage-build-server/scripts/_marshalld_journal.py` | 2 | `marshalld/` journal dir | **JUSTIFY (state, no key).** Same shape as the audit record. |
| `script-shared/scripts/build/_build_server_registry.py` | 2 | `marshalld/registry.json` | **JUSTIFY (state, no key).** The daemon registry. Registration is an enable signal, not a configured value, so there is no per-caller key to disagree over. |
| `script-shared/scripts/build/_build_execute_factory.py` | 1 | `marshalld/` fallback-routing state | **JUSTIFY (state, no key).** Records which route a build took. No config key is applied against it. |
| `manage-providers/scripts/_providers_core.py` | 3 | `credentials/` | **JUSTIFY (state, no key).** Host-wide credentials, correctly host-anchored, with an explicit directory override. Credentials are not a config key applied to another caller's entries. |

**Mention-only candidates, excluded** — in the text set, absent from the call set:

| File | Occurrences | Reason for exclusion |
|------|-------------|----------------------|
| `manage-locks/scripts/merge_lock.py` | 2 | Both are prose that DISCLAIM the tier: the module docstring states that the build-slot queue is machine-global under `home_root()` and therefore NOT in the per-repo main-anchored exception set this script resolves through, and a helper docstring repeats the boundary. A disclaimer is the opposite of a consumer. |
| `tools-file-ops/scripts/file_ops.py` | 1 | One docstring sentence, on a main-anchored resolver, pointing non-entry-shaped machine-wide state at the home-root tier instead. Also a boundary statement, not a call. |
| `build-server-client/scripts/build_server.py` | 2 | Two comments explaining that the socket lives under `<home_root>/marshalld` and that `registry_dir()` resolves that same directory. The client reaches the tier **indirectly**, through `_build_server_registry`, which is itself in the population — so the tier is dispositioned where it is resolved, and this file adds no independent site. |

**Alias resolution is part of the method, not a refinement.** An
`import … as` binding hides the target substring from any name-matching
classifier, textual or AST, and under-counts callers by exactly the aliased sites.
The pass therefore builds the `asname → target` map before counting. In this
candidate set the map is **empty** — every import is a plain
`from marketplace_paths import ensure_home_root, home_root`. That is a derived
result, not a reason to drop the stage: the stage is what establishes that the
figures are not short.

**Shape B figures.** 12 candidate files; 16 call sites over **9 files**; 3
mention-only files excluded.

### Counts

| Set | Files |
|-----|-------|
| Shape A population | **1** |
| Shape B population | **9** |
| In both (intersection) | **1** |
| **Union — the machine-global config-scope population** | **9** |

The intersection is `manage-build-server/scripts/marshalld.py`, so the union is
1 + 9 − 1 = **9 distinct script files**.

At the KEY level, where the shapes are defined:

| Set | Keys |
|-----|------|
| Shape A | **1** — `build.queue.max_slots` |
| Shape B | **2** — `build.queue.max_slots`, `build.queue.upper_limit_seconds` |
| Overlap | **1** — `build.queue.max_slots` |
| **Union** | **2** |

**This is not a population of one**, which is the finding the key-level count
exists to make. A survey that stopped at the first member would have reported the
cap alone and left the reap threshold in a per-repo file, governing every
repository's entries in the host-wide queue.

**Excluded key.** `build.queue.max_retries` is a `build.queue` sibling of both
members and is **not** in either shape: it bounds only the caller's own wait loop
in `_build_queue_slot.py` and is never evaluated against another caller's entries.
It stays per-repo, and it is the reason the `build.queue` block still exists in
`marshal.json`.

### Coverage

Every sweep quoted here returned `unreadable: []`, `truncated: false` and
`elided: []`, so each text enumeration is complete to the inventory's edge, and
each sweep scanned **441** `--category script` rows.

The AST pass walked **431** `*.py` files matching
`marketplace/bundles/*/skills/*/scripts/**/*.py` with **no** parse error and **no**
unreadable file. That glob is narrower than the 441-row text scope by 10 files,
and the difference carries no candidate: every row either text sweep attributed a
hit to lies inside the glob, so no candidate sits outside the classified set.

**Inventory-scope caveat.** The crawl does not walk `.plan/`, `.claude/**`,
`.github/**`, or anything a `.gitignore` rule excludes. A negative from the sweeps
above is *"not in any inventoried file"* — never *"not in the tree"*. The
supplementary sweep below is what closes that gap; without it the counts above
would be a clean-looking zero over an unstated hole.

## The supplementary out-of-inventory sweep

`.claude/**` and `.github/**` are not crawled, so they are swept by two
independent methods: a git pickaxe over tracked history, and a direct scan of the
trees at HEAD. The two answer different questions — "was this token ever
introduced" and "is it here now" — and a member missed by one is caught by the
other.

**Method 1 — pickaxe over tracked history.** `git log -S <token> HEAD -- .claude
.github`. A token present at HEAD was introduced by some commit, so an empty
result means no tracked file under those trees has ever carried it.

**Positive control.** The method is only trustworthy if it can return a hit at
all: `cloud-plan-lane` returns **4** commits. A sweep reporting zero without a
passing control reports its own silence.

| Token | Commits |
|-------|---------|
| `cloud-plan-lane` (control) | 4 |
| `max_slots` | 0 |
| `resolve_max_slots` | 0 |
| `machine-config` | 0 |
| `build-queue-limit` | 0 |
| `build_queue_upper_limit` | 0 |
| `upper_limit_seconds` | 2 |
| `home_root` | 2 |
| `build-queue.json` | 1 |

`build_queue_upper_limit` subsumes the leading-underscore spelling of the retired
helpers, so one sweep covers both names.

**Method 2 — direct scan at HEAD.** Walk both trees and count occurrences per
file. **61** files scanned; **3** unreadable, and each of the three is a compiled
`.pyc` artifact under `__pycache__` whose `.py` source sibling WAS scanned — so the
unreadable count is a build artifact, not a coverage gap. **3** files carry a hit:

| File | Tokens |
|------|--------|
| `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` | `upper_limit_seconds` (2), `build-queue.json` (3), `home_root` (2) |
| `.claude/skills/audit-archived-plan-retrospectives/checks/global-log-analysis.md` | `upper_limit_seconds` (2), `build-queue.json` (2) |
| `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py` | `home_root` (2) |

**The out-of-inventory members, dispositioned by name.**

- `audit.py` — `_ratcheted_ci_wait_ceiling` reads the top-level
  `upper_limit_seconds` of the machine-global `build-queue.json` under the home
  root (`PLAN_MARSHALL_HOME` when set, else `~/.plan-marshall`), inline, per the
  skill's inline-reader rule. It is a genuine consumer of a population member and
  it is invisible to the pinned population on **two** independent grounds: the
  inventory does not walk its tree, and it never calls
  `marketplace_paths.home_root` — it binds a LOCAL name `home_root` to the
  resolved path, which the call-aware classifier correctly reads as a non-call
  reference. Either ground alone would hide it, which is why it is dispositioned
  here by name rather than left to a derivation. The same function reads
  `commands.{key}.timeout_seconds` from the main-anchored
  `.plan/local/run-configuration.json` — the one path that file ever sits at — and
  each of the two reads degrades to the flat floor independently, so an absent or
  unreadable source never suppresses the other.
- `global-log-analysis.md` — the interpretation guide for that reader. It states
  the same two sources, so the guide and the code cannot drift into describing
  different files.
- `reconcile_daemon.py` — `_daemon_state_dir()` re-implements the home-root
  resolution inline (`PLAN_MARSHALL_HOME`, else `~/.plan-marshall`, then
  `marshalld`) because it is a standalone project-local script that must not
  import the marketplace tree. It reaches the tier for the reconcile-owed marker
  and applies **no config key** against it, so it is the same
  state-without-a-key class as the daemon journal — but it is a real tier consumer
  that no inventory sweep can see, and a future key added there would be outside
  every derivation above.

Git-ignored files under `.claude/` are machine-local and outside both methods.

## Member dispositions

### `build.queue.max_slots` — the build-slot admission cap

Resolved through `_machine_config.resolve_max_slots()` from
`home_root()/marshalld/machine-config.json`, so the cap and the queue it governs
sit in one tier and the resolution does not depend on the process cwd. Every
resolution names its source, and an `invalid` or `unreadable` source is never
reported as `machine_config` or `default`.

- A surviving per-repo `build.queue.max_slots` never changes the admitted cap. It
  is reported as `per_repo_max_slots: {value, in_effect: false}` with one
  `per_repo_max_slots_not_in_effect` warning on every queued build, and it is
  moved machine-wide in one step by `manage_build_server config migrate` — which
  copies it only when no machine-wide value is set, and refuses without touching
  either file when the two values differ.
- The key is no longer seeded into a new project's `marshal.json`, so no project
  acquires a key that would never take effect.
- Every new queue entry is stamped with `admitted_under_max_slots`, the cap it was
  actually admitted under. An admitting caller compares its own cap against those
  stamps and reports `cap_agreement` with `cap_compared_count`,
  `cap_unstamped_count` and `cap_disagreement[]`. A disagreement is reported on the
  result, in the build output and in the `[LOCK]` log, and is **never** reconciled
  — neither value is picked as authoritative. An entry with no stamp yields
  `unknown`, never counted as agreement; an empty queue yields `agree` with
  `cap_compared_count: 0`, so the compared population is published rather than an
  unqualified verdict.

### `build.queue.upper_limit_seconds` — the adaptive reap threshold

A top-level field of `build-queue.json` — the same machine-global file whose
entries it governs. The reaper takes it from that state and the release path
recomputes it inside the queue's own read-modify-write critical section, so the
threshold is read and written where the entries are, with no window between
observing it and acting on it. An absent or invalid value reads as the floor with
an explicit source, and `build_queue limit get|set` is the operator surface.

- A surviving per-repo `build.queue.upper_limit_seconds` in a caller's
  `run-configuration.json` is reported by `limit get` as `per_repo_value` with
  `in_effect: false`.
- The key is no longer seeded into `marshal.json`, and the per-repo
  run-config verbs that used to own it no longer exist.

## Hypothesis verdicts

The survey tested four hypotheses. Their verdicts are published because two of
them were wrong in the direction that hides work — a hypothesis that a population
is empty or singular is exactly the kind that passes unexamined.

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| H1 — the fallback queue's state file is machine-global | **VERIFIED** | `build_queue._resolve_queue_path` returns `ensure_home_root() / 'build-queue.json'`, i.e. `~/.plan-marshall/build-queue.json`, overridable via `PLAN_MARSHALL_HOME`. |
| H2 — the home-root tier holds no config knob | **NO LONGER HOLDS** | It held of a tree whose home-root tier carried only credentials, the build queue and the daemon's own state. `machine-config.json` is now that tier's config member, in the slot ADR-008 reserves for the daemon, so no new tier class was introduced to add it. |
| H3 — the cap is the only key of this shape | **REFUTED** | `build.queue.upper_limit_seconds` is a second member: a per-repo threshold that was applied to every repository's entries in the host-wide queue. The key-level union is 2, not 1. |
| H4 — concurrent over-admission occurs in practice | **UNMEASURED** | Two over-admission paths are demonstrable by reading the code — disagreeing caps, and a low threshold in one repository freeing a slot another repository's long build still holds. Occurrence is a different claim, and no available log can carry it: the `[LOCK]` event log is per-repo and main-anchored, so no single log shows cross-repo interleaving. Per ADR-019 this is reported as unmeasured, **not** as absence. The `cap_disagreement` event now emitted on the machine-global queue is the signal that would make it measurable. |

## Out of universe

Named here so the shapes carry no silent tail:

- **`run-configuration.json` `language_servers`.** Described as machine-local yet
  stored per repository. It is never applied against shared state, so it meets
  neither shape — a mis-tiered key, not a cross-caller one.
- **The merge-lock `rate_windows` claim.** Per-repo state standing in for an
  account-scoped external resource. It is state, not a config key, so shape B's
  criterion does not reach it.

Both are adjacencies of the shapes, not deferred members.

## Re-derivation

A later reader re-runs this rather than trusting it, and resolves a disagreement
by comparing per-file classifications rather than totals.

1. **Shape A candidates.** `architecture search --content --literal
   --category script --pattern chdir`.
2. **Shape B candidates.** `architecture search --content --literal
   --category script --pattern home_root`.
3. **Classify both.** Parse each candidate with `ast.parse`, build the
   `asname → target` alias map first, then keep only occurrences that are a call's
   own `func`. Treat definitions, imports, bare references and textual residue as
   exclusions. The classifier is a few dozen lines of stdlib `ast`, fully specified
   by stage 2 above.
4. **Close the inventory gap.** Run the pickaxe with its positive control over
   `.claude` and `.github`, and scan both trees at HEAD, reporting the files
   scanned and every file that could not be read.
5. **Compare against the tables above** — the populations, not the counts. A file
   appearing in a derived set that no table dispositions is a new member, and it
   is a finding.

The companion pytest pins exactly this: it re-derives both sets with `ast` and
asserts each equals the set dispositioned here, publishing the derived population
size in every assertion message so an empty or shrunken derivation cannot pass
vacuously. A new cwd-moving process, or a new consumer of the machine-global tier,
therefore fails that test until this audit dispositions it.

These figures are scoped `--category script`, so documentation is outside them and
**this document is not in its own population**: editing this prose cannot move any
of them.
