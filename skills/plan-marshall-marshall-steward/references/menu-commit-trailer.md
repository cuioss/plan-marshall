# Menu Option: Commit Trailer

Inspect and change the co-author identity every assistant-authored commit ends with. The setting is a
two-field object in the run-configuration store, and it answers exactly one question: under whose
name does this checkout record work an assistant performed.

The identity names the **system** that produced the commit, not the assistant or the vendor behind
it, and it does not vary by target. One project therefore commits under one name whichever assistant
ran the work — which is the whole point of the knob, and why it is a single project-level value
rather than a per-assistant lookup.

The binding is **machine-local**. It persists to the git-ignored, main-anchored
`run-configuration.json` beside the `language_servers`, `derivation_resolvers` and `display_timezone`
bindings rather than in a version-controlled project file. Two consequences follow, and both are
worth stating to the operator:

- A fresh clone, and every cloud session, resolve to the **default** identity, because the file
  carrying the override is not in git. Repository documentation therefore states the default.
- A change here binds this checkout only. A teammate on the same repository is unaffected.

⛔ **Changing the identity does not rewrite history.** It governs the next commit onwards; commits
already recorded keep the trailer they were written with. Never present a change as "re-attributing
the project" — nothing already committed moves.

See
[`../../manage-run-config/standards/run-config-standard.md`](../../manage-run-config/standards/run-config-standard.md)
§ "Commit-Trailer Section" for the schema, the per-half fallback, and the validation rules.

## Reachability

Reachable from the marshall-steward **Configuration** menu (Main Menu → "3. Configuration" →
"More..." → "More..." → "More..." → "More..." → "Commit Trailer"). Like every other Configuration
entry it is not gated behind first-run setup.

---

## Step 1: Read the current value

Read the stored identity. This is the **only** source for what the menu displays — never report a
name from memory, from the git author configuration, or from a value written into a document:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config commit-trailer get
```

The response carries `name`, `email`, the composed `trailer`, and `name_source` / `email_source`.

⚠ **`get` never reports "unset" through the value.** An absent field, a non-string value, and a
stored value carrying an angle bracket or a line break all resolve to the default, so a `name` of
`plan-marshall` alone does not mean the operator chose it. The `name_source` / `email_source` fields
are what carry that distinction — read them, and say `configured` or `default` per half rather than
inferring one from the other. The halves fall back independently: a configured name beside a default
email is a legitimate, reportable state.

## Step 2: Present the current value and offer the actions

Report the composed trailer, and beside it the source of each half, so the operator can see which
part of the identity the project actually chose.

Then offer the actions:

```text
AskUserQuestion:
  question: "What would you like to do with the commit co-author trailer?"
  header: "Commit Trailer"
  options:
    - label: "Set the name"
      description: "Change the co-author name used from the next commit onwards"
      value: "set-name"
    - label: "Set the email"
      description: "Change the co-author address used from the next commit onwards"
      value: "set-email"
    - label: "Reset to defaults"
      description: "Return both halves to the plan-marshall default identity"
      value: "reset"
    - label: "Back"
      description: "Return to the Configuration menu"
      value: "back"
```

On `set-name` or `set-email`, ask for the value and pass whatever the operator supplies to the verb
as a **single quoted argument** — the verb validates it. Quoting is not cosmetic: the verb's
validation runs only after the shell has already parsed the command line, so an unquoted operator
answer carrying a shell metacharacter is interpreted by the shell before validation is ever reached.

Do NOT pre-screen the value here beyond passing it through: the verb rejects an empty value, one
carrying an angle bracket or a line break (either would break the trailer line's own grammar), and an
address with no `@`.

## Step 3: Apply the change

| Selection | Command |
|-----------|---------|
| set-name | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config commit-trailer set --name "{name}"` |
| set-email | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config commit-trailer set --email "{email}"` |
| reset | `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config commit-trailer set --name plan-marshall --email noreply@cuioss.de` |
| back | Do nothing → Return to the Configuration menu |

A rejected value returns the standard `invalid_value` error response and **persists nothing**.
Surface that error to the operator with the rejected value and re-ask; do not fall back to a guessed
identity and do not report the change as applied.

## Step 4: Confirm the round-trip

After a change, re-read the value (Step 1) and confirm it is what was just set. **Report the re-read
value, not the value that was written** — the write reporting success is a claim, and the re-read is
the outcome.

Then return to Step 2 so a further change can be made without leaving the menu.

---

## What this menu does NOT configure

- **The git author or committer.** Those come from `user.name` / `user.email` in the operator's own
  git configuration. This knob sets only the `Co-Authored-By` trailer appended to the message body,
  and changing one has not changed the other.
- **Commits already made.** The trailer is composed at commit time, so a change binds the next commit
  onwards. History is untouched.
- **Whether a trailer is appended at all.** It always is. The `format-commit` script deliberately
  omits it so the caller adds exactly one at `git commit` time; there is no "no trailer" setting.
- **Any additional attribution footer.** None is emitted, and none is switchable here.
- **What a cloud session or a fresh clone commits under.** Neither has this file, so both resolve to
  the default identity regardless of what is configured in this checkout.
