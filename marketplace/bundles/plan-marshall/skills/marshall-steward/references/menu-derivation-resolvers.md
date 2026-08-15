# Menu Option: Derivation Resolvers

Inspect and change which **derivation resolvers** run in this checkout. A resolver contributes
`(from, to)` module edges to the graph query family — `graph`, `path`, `neighbors`, `impact`, and the
adjacency surfaces of `overview` and `module` / `info` — so this menu decides what those queries can
see.

The binding is **machine-local**. A resolver's availability and cost depend on locally-installed
tooling (the `lsp` resolver's harvest needs a language server on `PATH`), so the same project can
legitimately have a different active set on two machines. It persists to the top-level
`derivation_resolvers` map in the git-ignored, main-anchored `run-configuration.json`, beside the
`language_servers` binding rather than in a parallel store.

⛔ **An unconfigured project runs every discovered resolver.** This menu exists to switch a resolver
*off*, not to switch derivation *on*: a project that never opens it still derives its edges. Never
present the unconfigured state as "nothing configured, so nothing runs" — that is the opposite of what
the substrate does.

See
[`../../manage-run-config/standards/run-config-standard.md`](../../manage-run-config/standards/run-config-standard.md)
§ "Derivation-Resolvers Section" for the schema, and
[`../../extension-api/standards/ext-point-derivation-resolver.md`](../../extension-api/standards/ext-point-derivation-resolver.md)
for the seam itself.

## Reachability

Reachable from the marshall-steward **Configuration** menu (Main Menu → "3. Configuration" → "More..."
→ "More..." → "More..." → "Derivation Resolvers"). Like every other Configuration entry it is not
gated behind first-run setup.

---

## Step 1: Read the roster

Read the discovered resolvers joined against the stored binding. This is the **only** source for what
the menu displays — never enumerate resolvers from memory or from a list written into a document,
because a resolver added or removed by a bundle would silently outdate it:

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension_api derivation-resolvers list
```

The response carries `resolvers[]` — one `{id, origin, enabled, configured, file_patterns}` record per
**discovered** resolver, sorted by id — plus `count` and `enabled_count`.

| Field | Meaning |
|-------|---------|
| `id` | The resolver's stable provenance id, the value that appears in an edge's `producers[]` |
| `origin` | The contributing bundle (Axis-A) or build skill (Axis-B) |
| `enabled` | The **effective** state — `true` when unconfigured, since absent means active |
| `configured` | Whether an explicit entry exists, distinguishing "left at the default" from "deliberately set" |
| `file_patterns` | The files this resolver derives from, as the resolver itself declares them. **Descriptive only** — see below |

A `count` of `0` means no resolver was discovered in this envelope, which is a truthful answer, not an
error: report it as "none discovered" rather than as a failure.

## Step 2: Present the roster

Render one line per resolver, showing the id, its origin, whether it is active, and its file domain.
Mark an entry the operator has explicitly set (`configured: true`) distinctly from one sitting at the
default, so "enabled because nobody changed it" and "enabled on purpose" stay distinguishable.

Report `file_patterns` as **what the resolver reads**, never as what selects it. An empty
`file_patterns` means the resolver declares no domain — report it as *not declared*, not as "derives
from no files".

Then offer the actions:

```text
AskUserQuestion:
  question: "What would you like to do with the derivation resolvers?"
  header: "Resolvers"
  options:
    - label: "Disable a resolver"
      description: "Stop dispatching a resolver in this checkout"
      value: "disable"
    - label: "Enable a resolver"
      description: "Dispatch a resolver that is currently switched off"
      value: "enable"
    - label: "Reset to default"
      description: "Drop a resolver's entry, returning it to default-active"
      value: "reset"
    - label: "Back"
      description: "Return to the Configuration menu"
      value: "back"
```

## Step 3: Apply the change

| Selection | Command |
|-----------|---------|
| disable | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config derivation-resolver set --resolver {id} --disabled` |
| enable | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config derivation-resolver set --resolver {id} --enabled` |
| reset | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config derivation-resolver remove --resolver {id}` |
| back | Do nothing → Return to the Configuration menu |

Offer only ids the Step 1 roster reported. An id that is not discovered can still be stored — the
store does not validate against discovery — but writing one binds nothing and misleads the next
reader.

## Step 4: Confirm the round-trip

After a change, re-read the roster (Step 1) and confirm the resolver's `enabled` value is what was
just set. **Report the re-read value, not the value that was written** — the write reporting success
is a claim, and the re-read is the outcome.

Then return to Step 2 so further changes can be made without leaving the menu.

---

## What this menu does NOT configure

- **Precedence between resolvers.** There is none, and none is expressible: the graph is the **union**
  of every active resolver's edges, edges are unweighted `(from, to)` booleans, so the union is
  idempotent and commutative. Two resolvers deriving the same pair have **corroborated**, not
  disagreed — the merge collapses them into one edge carrying both producer ids. The one precedence
  that does exist is **declared-over-derived**, which core owns and configuration cannot override.
- **Binding a resolver to a file pattern.** The key is the resolver **id**. A resolver is handed module
  maps and returns `(module, module)` pairs carrying no file provenance, so there is no dispatch point
  at which a per-file binding could be applied.
- **Whether a language server runs.** The `lsp` resolver's harvest is additionally gated by the
  `language_servers` binding — configured through the same store, and enabling a language there also
  switches on a whole-workspace harvest per crawl. Disabling the `lsp` resolver here stops the edge
  derivation; it does not unbind the language server.

## A disabled resolver is still reported

Switching a resolver off does not remove it from the graph query's per-resolver report. It comes back
with `edge_count: 0`, `status: not_dispatched`, and a `configuration:` note saying it was discovered
but not dispatched. That is deliberate: pruning it would make "switched off by the operator"
indistinguishable from "never registered", and a zero-edge answer that cannot explain itself is
exactly what the seam's provenance contract exists to prevent.

⚠ **It is not counted as having run.** `resolver_count` counts only resolvers whose status is not
`not_dispatched`, so switching off *every* resolver makes the graph report `resolver_count: 0` and
`capabilities` report `module_edges: not_derivable`. That is the truthful answer — the envelope
genuinely cannot derive edges — and the non-empty `resolvers[]` alongside it is what distinguishes
this from "no resolver is registered". Tell an operator who disables everything to expect exactly
that, rather than leaving them to read it as a fault.
