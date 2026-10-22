/**
 * plan-marshall guard plugin — tool.execute.before enforcement of R1-R6.
 *
 * V2 plugin (`Plugin.define` with `ctx.tool.hook("execute.before")`). The
 * opencode host loads every module under `{plugin,plugins}/*.{ts,js}` in the
 * project config directory. This plugin registers a
 * `ctx.tool.hook("execute.before")` hook that inspects each tool invocation against the six
 * plan-marshall hard-rule bypass classes and THROWS to block the execution,
 * appending one audit line to `.plan/temp/guard.log` per blocked invocation.
 *
 * The plugin's decision table is mirrored as a behavioral contract in
 * `test/plan-marshall/platform-runtime/test_opencode_enforcement.py`, which
 * EXECUTES this module under node rather than grepping its source. Keep the
 * two in lock-step when the table changes.
 *
 * DECISION TABLE (authoritative — mirrored in the D4 runtime matrix):
 *
 *   Guarded tools: bash (R1, R2, R4, R5, R6), edit/write/patch/apply_patch (R3).
 *   Every other tool passes through untouched.
 *
 *   R1 — shell-chaining constructors (bash): the command, with single-quoted
 *   regions stripped and double-quoted regions stripped except for command
 *   substitution, contains `&&`, `||`, `;`, `|`, `$(`,
 *   a backtick, any unquoted `&` or `(`, or a newline  => block. `$(` and backticks
 *   inside double quotes still block because Bash executes them there.
 *
 *   R2 — shell file operations, mutation class (bash): the command's first token,
 *   after stripping the shell wrappers (with options), leading `NAME=value`
 *   assignments, quotes, and path qualification, is one of
 *   {rm mv cp touch mkdir rmdir truncate tee chmod chown ln dd}  => block.
 *   Read-side probes (ls cat head tail grep find) are NOT in this guard class:
 *   the two-tier permission map governs them (global deny, orchestrator
 *   small-ops carve-out under ask). Shell spawns `sh`/`bash`/`source` also block.
 *
 *   R3 — direct edits to the generated executor path (edit/write/patch/apply_patch):
 *   the target resolves under `.plan/execute-script.py` — via filePath, or via
 *   every `*** Add/Update/Delete File:` / `*** Move to:` marker (plus legacy
 *   bare add/update/move/delete targets) in apply_patch patchText  => block.
 *
 *   R4 — hard-coded build commands bypassing `python3 .plan/execute-script.py`
 *   (bash): route builds through the executor only. Block when:
 *     - first token is `./pw` unless its verb is explicitly allowed
 *       (only `./pw generate*` and `./pw --*` pass; a missing verb blocks);
 *     - first token is a bare build tool {mvn mvnw gradle gradlew make cmake ant
 *       uv}; or a JS runner {npm npx bun pnpm yarn} followed by
 *       {test run build};
 *     - first token is an interpreter and the basename of the second
 *       token is `build.py` (`python3 ./build.py` included);
 *     - `python(3) -m {pytest mypy ruff}`; a bare {pytest mypy ruff}.
 *   R4 is UNCONDITIONAL. The executor permit stays exempt under R4 and R5.
 *
 *   R5 — direct interpreter calls bypassing the executor (bash): block when the
 *   first token, after stripping the SHARED wrapper table
 *   (`standards/r5-wrappers.json`: matched by basename, with each wrapper's
 *   value options, short-option clusters, leading positionals, command-string
 *   splicing and watch/parallel positional splicing, plus `find … -exec`), is an
 *   interpreter (python/python3, pypy/pypy3, or a versioned spelling such as
 *   python3.12) and the invocation is -c, a script path (any second token not
 *   starting with -), a bare - (STDIN), a -</- redirection, or -m with any module
 *   — the allow set is executor-only, so every -m form refuses. R5 BINDS inside a
 *   plan context (Signal 1, Signal 2, or the runbook-lane marker) and in EVERY
 *   session of THIS repository; in a consumer repository outside a plan context
 *   it does not refuse a consumer's ordinary Python work (python3 x.py, python3
 *   -m venv, python3 -m pip). Three admissions apply: the executor permit, the
 *   SHARED repository-relative allow-list, and the SHARED bundle-relative
 *   allow-list (matched EXACTLY against the resolver's deployed path for the
 *   entry); neither allow-list form is ever a basename or a suffix — so a copy of
 *   an allow-listed script outside the repository, or under a non-deployed
 *   directory, never matches.
 *
 *   R6 — a raw `git commit` while the enclosing plan is in phase `6-finalize`
 *   => block. The plan is NAMED from EVERY commit form: the `--work-tree` value,
 *   the composed `git -C` TARGET (the persona-mandated `git -C {WORKTREE}
 *   commit` form), the plan a `--git-dir` / `GIT_DIR` admin directory points at
 *   (`…/worktrees/{plan}`), then the `workdir`, then the project root; its phase
 *   is read from that plan's own `status.json` field `current_phase` — the
 *   worktree-resident record first (the live one during phase 5+), then the
 *   main-anchored record. Never "the first plan found" by a directory scan. A
 *   `-c alias.NAME=…` subcommand is resolved to its body; an unresolvable target
 *   (an unexpanded variable, a shell alias) is refused fail-closed inside the
 *   enforced scope. Every plan commit must pass through the gate-bearing
 *   `git-workflow commit` verb. Outside `6-finalize`, or with no plan state
 *   present, a raw commit is untouched.
 *
 * TOKENISATION PARITY: the R5 branch tokenises with a quoting-aware splitter
 * (`shellSplit`) matching the Python hook's `shlex.split`, strips the SAME
 * wrapper set, and lowercases the program token for the interpreter check, so
 * the two decision tables agree on the interpreter surface.
 */
import { appendFileSync, existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, statSync } from "node:fs"
import { execFileSync } from "node:child_process"
import { homedir } from "node:os"
import path from "node:path"
import { Plugin } from "@opencode/plugin"

// ---- R1: shell-chaining constructors (declared set, mirrored by D4) ----
function hasChainingConstructor(command) {
  let inSingle = false
  let inDouble = false
  let escaped = false
  let unquoted = ""
  let doubleQuotedSubstitution = false
  for (let i = 0; i < command.length; i++) {
    const ch = command[i]
    if (escaped) {
      escaped = false
      continue
    }
    if (ch === "\\" && !inSingle) {
      escaped = true
      continue
    }
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle
      continue
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble
      continue
    }
    if (!inSingle && !inDouble) {
      unquoted += ch
      continue
    }
    if (inDouble && !inSingle) {
      if (ch === "`") doubleQuotedSubstitution = true
      if (ch === "$" && command[i + 1] === "(") doubleQuotedSubstitution = true
    }
  }
  if (doubleQuotedSubstitution) return true
  return /&&|\|\||[;|]|\$\(|`|[&()]|\n/.test(unquoted)
}

// ---- R2: shell file operations, mutation class (declared set, mirrored) ----
const MUTATION_FILE_OPS = new Set([
  "rm", "mv", "cp", "touch", "mkdir", "rmdir", "truncate", "tee",
  "chmod", "chown", "ln", "dd", "sh", "bash", "source",
])

// ---- R4: hard-coded build bypasses (declared sets, mirrored) ----
// `./pw` is allowlisted by decision-table prefix, not by verb set: only
// `./pw generate*` and `./pw --*` pass. Every other `./pw` invocation
// blocks, so a new build.py-routed alias cannot bypass R4 by omission.
const BARE_BUILD_TOOLS = new Set(["mvn", "mvnw", "gradle", "gradlew", "make", "cmake", "ant", "uv"])
const JS_RUNNERS = new Set(["npm", "npx", "bun", "pnpm", "yarn"])
const JS_RUNNER_BUILD_VERBS = new Set(["test", "run", "build"])
const PYTHON_DIRECT_RUNNERS = new Set(["pytest", "mypy", "ruff"])

// ---- R5: direct interpreter calls bypassing the executor (declared sets, mirrored) ----
// The allow set is executor-only: every -m form refuses, so no allowed-module
// set exists to declare. The two sets below are the whole R5 population the
// contract test parses: the interpreter names and the always-refuse flags.
// A versioned spelling (python3.12) is recognised by `isPythonInterpreter`.
const PYTHON_INTERPRETERS = new Set(["python", "python3", "pypy", "pypy3"])
const R5_ALWAYS_REFUSE_FLAGS = new Set(["-c", "-m"])

// ---- R5: the ONE shared wrapper table ----
// Shell wrappers are prefix programs whose own invocation RUNS the command that
// follows (`timeout 5 rm file` still runs `rm`, `env python3 -c x` still runs
// the interpreter). The set, each wrapper's value-consuming options, its
// leading positional arguments and its command-string splicing options live in
// ONE data file — `standards/r5-wrappers.json`, the sibling of
// `r5-allowlist.json` — read here, by the Claude hook and by the enforcement
// pin tests. Neither implementation carries a second literal list: a wrapper
// added to the data file is stripped on both harnesses and a wrapper removed
// from it is stripped on neither. A wrapper is matched by BASENAME, so
// `/usr/bin/env` strips exactly like `env`.
const R5_WRAPPER_TABLE_NAME = "r5-wrappers.json"
const EMPTY_WRAPPER_SPEC = { values: [], value_letters: [], leading_positionals: 0, splice: [] }

//: The deployed-layout data file the resolver and this guard both read.
const R5_LAYOUT_NAME = "deployed-layout.json"

//: The wrapper table in force for this process. Loaded in `setup` from the
//: project/deployed data file; an EMPTY table with `missing: true` when no data
//: file resolves, which makes the R5 check fail CLOSED (see the R5 branch).
let WRAPPER_TABLE = { wrappers: {}, findExec: new Set(), missing: true }

// The base allow-list used when no shared data file can be read. Deliberately
// narrow: the sync engine is the one non-executor invocation that must survive
// even a missing data file, because it is the harness's own deploy step. An
// entry is a REPOSITORY-RELATIVE path (see `repoRelativePath`).
const R5_ALLOWLIST_BASE = ["marketplace/targets/sync.py"]

// The ONE repository-relative marker that says "this project IS the plan-marshall
// source repository". It is the project-local copy of the shared allow-list data
// file, so the check is a statement about the same substrate R5 reads and needs
// no second convention. In this repository R5 binds in EVERY session; in a
// consumer repository it binds only inside a plan context (see `contextGate`).
const R5_REPO_MARKER = "marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json"

// The sub-agent identity carries this marker when the call originates inside a
// dispatched execution-context sub-agent (the Claude hook's Signal 1, shared
// verbatim so the two harnesses agree).
const EXECUTION_CONTEXT_MARKER = ":execution-context"

// Path segment marking a plan worktree (the Claude hook's Signal 2).
const WORKTREE_PATH_SEGMENT = "/.plan/local/worktrees/"

const ASSIGNMENT_RE = /^[A-Za-z_][A-Za-z0-9_]*=/
const VERSIONED_PYTHON_RE = /^(python|pypy)(\d+(\.\d+)*)?$/

// Phase the raw-commit rule guards, mirroring git-workflow.py's
// `_SOURCE_COMMIT_GATE_PHASE`. Outside it a raw `git commit` is untouched.
const SOURCE_COMMIT_GATE_PHASE = "6-finalize"

// `git` global options that consume a SEPARATE following token, so the
// subcommand walk steps over the option AND its value.
const GIT_VALUE_OPTIONS = new Set([
  "-C",
  "-c",
  "--git-dir",
  "--work-tree",
  "--namespace",
  "--super-prefix",
  "--config-env",
  "--exec-path",
  "--attr-source",
])

// Quoting-aware tokenizer mirroring Python's `shlex.split` (POSIX mode) on the
// shapes R5 sees. Returns null on malformed quoting (an unterminated span or a
// trailing escape), so the caller can fall back to a whitespace split exactly
// as the hook's shlex fallback does.
function shellSplit(command) {
  const tokens = []
  let current = ""
  let started = false
  let i = 0
  const n = command.length
  while (i < n) {
    const ch = command[i]
    if (ch === "\\") {
      if (i + 1 >= n) return null
      current += command[i + 1]
      started = true
      i += 2
      continue
    }
    if (ch === "'") {
      started = true
      i++
      let closed = false
      while (i < n) {
        if (command[i] === "'") {
          closed = true
          i++
          break
        }
        current += command[i]
        i++
      }
      if (!closed) return null
      continue
    }
    if (ch === '"') {
      started = true
      i++
      let closed = false
      while (i < n) {
        if (command[i] === '"') {
          closed = true
          i++
          break
        }
        current += command[i]
        i++
      }
      if (!closed) return null
      continue
    }
    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
      if (started) {
        tokens.push(current)
        current = ""
        started = false
      }
      i++
      continue
    }
    current += ch
    started = true
    i++
  }
  if (started) tokens.push(current)
  return tokens
}

function whitespaceSplit(command) {
  const trimmed = command.trim()
  return trimmed ? trimmed.split(/\s+/) : []
}

function isAssignment(token) {
  return ASSIGNMENT_RE.test(token)
}

// Step over ONE option token of a wrapper, per the shared table.
//
// `consumed` is how many tokens the option takes (1 = the option alone, 2 = the
// option plus its following value). `splice` is set when the option's value is a
// COMMAND STRING that must be re-lexed and walked (a shell's `-c`, `env -S`,
// `script -c`). A short CLUSTER (`-iu FOO`) is walked letter by letter, so the
// value-taking letter is honoured wherever it sits in the cluster.
function consumeWrapperOption(spec, token, tokens, index) {
  const values = spec.values || []
  const valueLetters = new Set(spec.value_letters || [])
  const spliceOpts = spec.splice || []
  const spliceLongs = new Set(spliceOpts.filter((option) => option.startsWith("--")))
  const spliceLetters = new Set(
    spliceOpts.filter((option) => option.length === 2 && option[0] === "-" && option[1] !== "-").map((option) => option[1]),
  )
  const nextValue = () => (index + 1 < tokens.length ? tokens[index + 1] : "")
  if (token.startsWith("--")) {
    const base = token.split("=")[0]
    const attached = token.includes("=") ? token.slice(token.indexOf("=") + 1) : null
    if (spliceLongs.has(base)) {
      const value = attached !== null ? attached : nextValue()
      return { splice: true, value, consumed: attached !== null ? 1 : 2 }
    }
    if (values.includes(base)) return { splice: false, value: null, consumed: attached !== null ? 1 : 2 }
    return { splice: false, value: null, consumed: 1 }
  }
  const letters = token.slice(1)
  for (let k = 0; k < letters.length; k++) {
    const ch = letters[k]
    if (spliceLetters.has(ch)) {
      const rest = letters.slice(k + 1)
      if (rest) return { splice: true, value: rest, consumed: 1 }
      return { splice: true, value: nextValue(), consumed: 2 }
    }
    if (valueLetters.has(ch)) {
      // A value-taking letter takes the REST of the cluster, else the next token.
      return { splice: false, value: null, consumed: letters.slice(k + 1) ? 1 : 2 }
    }
  }
  return { splice: false, value: null, consumed: values.includes(token) ? 2 : 1 }
}

// Split a spliced COMMAND STRING into its shell segments, so a wrapper's
// multi-command string (`zsh -c "cd /tmp; python3 -c x"`) is walked segment by
// segment instead of only at its first word. Quote-aware: a separator inside a
// quoted span of the string is data.
function splicedSegments(value) {
  const segments = []
  let current = ""
  let inSingle = false
  let inDouble = false
  let escaped = false
  for (const ch of String(value)) {
    if (escaped) {
      current += ch
      escaped = false
      continue
    }
    if (ch === "\\" && !inSingle) {
      current += ch
      escaped = true
      continue
    }
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle
      current += ch
      continue
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble
      current += ch
      continue
    }
    if (!inSingle && !inDouble && (ch === ";" || ch === "&" || ch === "|" || ch === "\n")) {
      segments.push(current)
      current = ""
      continue
    }
    current += ch
  }
  segments.push(current)
  return segments.map((segment) => segment.trim()).filter((segment) => segment.length > 0)
}

function isInterpreterProgramToken(token) {
  const base = basenameOf(token)
  return PYTHON_INTERPRETERS.has(base.toLowerCase()) || isPythonInterpreter(base)
}

// Strip leading wrapper/assignment prefixes, per the shared wrapper table.
// `env -S <string>`, a shell's `-c <string>` and `watch`/`parallel`'s positional
// command string SPLICE the string back through the splitter, because the
// wrapper runs that string as the command. A wrapper's `leading_positionals`
// (timeout's DURATION, flock's lock file, chrt's priority, taskset's mask) are
// consumed before the walked command.
function stripWrappers(tokens, table) {
  let i = 0
  while (i < tokens.length) {
    const token = tokens[i]
    if (isAssignment(token)) {
      i++
      continue
    }
    const base = basenameOf(token)
    const spec = table.wrappers[base] || table.wrappers[token] || EMPTY_WRAPPER_SPEC
    if (spec === EMPTY_WRAPPER_SPEC) break
    i++
    let spliced = null
    while (i < tokens.length) {
      const option = tokens[i]
      if (isAssignment(option)) {
        i++
        continue
      }
      if (!(option.startsWith("-") && option.length > 1)) break
      const step = consumeWrapperOption(spec, option, tokens, i)
      i += step.consumed
      if (step.splice) {
        spliced = step.value
        break
      }
    }
    if (spliced !== null) {
      // Walk EVERY segment of the command string: an interpreter behind a `cd` or
      // a separator in the string is still an interpreter this rule refuses.
      for (const segment of splicedSegments(spliced)) {
        const parts = shellSplit(segment)
        const segmentTokens = parts === null ? whitespaceSplit(segment) : parts
        const walked = stripWrappers(segmentTokens.concat(tokens.slice(i)), table)
        if (walked.length && isInterpreterProgramToken(walked[0])) return walked
      }
      const firstSegment = splicedSegments(spliced)[0] ?? spliced
      const parts = shellSplit(firstSegment)
      return stripWrappers((parts === null ? whitespaceSplit(firstSegment) : parts).concat(tokens.slice(i)), table)
    }
    if (spec.splice_positional && i < tokens.length) {
      // `watch '<command>'` / `parallel '<command>'` run their first positional
      // as a shell command, so it is spliced and walked like `env -S`.
      const value = stripMatchedQuotes(tokens[i])
      for (const segment of splicedSegments(value)) {
        const parts = shellSplit(segment)
        const segmentTokens = parts === null ? whitespaceSplit(segment) : parts
        const walked = stripWrappers(segmentTokens.concat(tokens.slice(i + 1)), table)
        if (walked.length && isInterpreterProgramToken(walked[0])) return walked
      }
      const firstSegment = splicedSegments(value)[0] ?? value
      const parts = shellSplit(firstSegment)
      return stripWrappers(
        (parts === null ? whitespaceSplit(firstSegment) : parts).concat(tokens.slice(i + 1)),
        table,
      )
    }
    let positionals = spec.leading_positionals || 0
    while (positionals > 0 && i < tokens.length && !tokens[i].startsWith("-")) {
      i++
      positionals--
    }
  }
  return tokens.slice(i)
}

// `find … -exec <program> … +` runs <program> exactly as a prefix wrapper does,
// so the tokens after a find-exec option are walked as the real command. Only a
// `find` program is spliced, and the option list is data
// (`find_exec_options`), never a find-specific literal.
function spliceFindExec(tokens, table) {
  if (basenameOf(tokens[0] ?? "") !== "find") return null
  for (let i = 0; i < tokens.length; i++) {
    if (table.findExec.has(tokens[i])) return tokens.slice(i + 1)
  }
  return null
}

// The command's tokens after wrapper stripping — the population every
// first-token check (R2, R4, R5, R6, the executor permit, the allow-lists) reads.
function commandTokens(command) {
  const split = shellSplit(command)
  const tokens = split === null ? whitespaceSplit(command) : split
  const stripped = stripWrappers(tokens, WRAPPER_TABLE)
  const spliced = spliceFindExec(stripped, WRAPPER_TABLE)
  return spliced === null ? stripped : stripWrappers(spliced, WRAPPER_TABLE)
}

// The command's tokens WITHOUT wrapper stripping — the raw first token, so R2's
// shell-spawn class still names `bash` even though `bash` is also a transparent
// wrapper whose `-c` string the interpreter walk descends into.
function rawCommandTokens(command) {
  const split = shellSplit(command)
  return split === null ? whitespaceSplit(command) : split
}

function stripMatchedQuotes(raw) {
  if (!raw || typeof raw !== "string") return ""
  let t = raw.trim()
  if (t.length >= 2 && ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'")))) {
    t = t.slice(1, -1)
  }
  return t
}

// Normalize an executable token for R2/R4 comparison: strip surrounding
// quotes and path qualification (`"rm"`, `'rm'`, `/bin/rm`, `./rm` all
// resolve to `rm`). Executor-permit matching stays exact and separate.
function normalizeToken(raw) {
  if (!raw || typeof raw !== "string") return ""
  const t = stripMatchedQuotes(raw)
  const slash = t.lastIndexOf("/")
  if (slash !== -1) return t.slice(slash + 1)
  return t
}

function basenameOf(raw) {
  if (!raw || typeof raw !== "string") return ""
  let t = raw.trim().replace(/\\/g, "/")
  t = stripMatchedQuotes(t)
  const slash = t.lastIndexOf("/")
  if (slash !== -1) t = t.slice(slash + 1)
  return t
}

function tokenAt(command, index) {
  const tokens = commandTokens(command)
  return tokens[index] ?? ""
}

// Whether a token names a python interpreter, case-insensitively, including a
// versioned spelling (`python3.12`). The hook lowercases the program token the
// same way, so the two guards agree on `PYTHON3` and on `python3.12`.
function isPythonInterpreter(raw) {
  const t = normalizeToken(raw).toLowerCase()
  if (PYTHON_INTERPRETERS.has(t)) return true
  return VERSIONED_PYTHON_RE.test(t)
}

// The executor permit — the ONE direct interpreter call R5 admits without an
// allow-list entry. The relative form `.plan/execute-script.py` is the canonical
// documented invocation, and it is admitted only when the command's EFFECTIVE
// working directory IS a repository root: the repository itself, or one of ITS
// plan worktrees under `.plan/local/worktrees/` (phase-5+ pins the shell cwd to
// the worktree, where `.plan` is the same executor through the worktree's
// symlink, so refusing it would break the documented execution flow). A leading
// `cd`, an `env -C` / `--chdir` / `sudo -D` directory change and the shell's
// `workdir` are resolved first (see `effectiveCwd`), so the same relative path
// run from anywhere else — `/tmp/x`, another checkout — is refused. (`git -C` is
// not a shell directory change: it moves git's own working directory for that
// one invocation and never the directory a following program runs in.) An
// ABSOLUTE form is admitted only when it equals
// `{repository root}/.plan/execute-script.py` after path normalization.
function isExecutorPermit(command, root, cwd) {
  const tokens = commandTokens(command)
  if (tokens.length < 2) return false
  if (basenameOf(tokens[0]).toLowerCase() !== "python3") return false
  const second = stripMatchedQuotes(tokens[1]).replace(/\\/g, "/")
  if (second === ".plan/execute-script.py") {
    const effective = effectiveCwd(command, cwd || root)
    if (!effective || !root) return false
    return isRepositoryRootOrPlanWorktree(effective, root)
  }
  if (!second.startsWith("/")) return false
  const repoRoot = (root || cwd || "").replace(/\\/g, "/").replace(/\/+$/, "")
  if (!repoRoot) return false
  return normalizePosixPath(second) === `${repoRoot}/.plan/execute-script.py`
}

// Whether the effective directory is the project root itself or one of its OWN
// plan worktrees. Compared after realpath, so a symlinked tree resolves first.
function isRepositoryRootOrPlanWorktree(effective, root) {
  const resolvedRoot = realPathOf(root)
  const resolved = realPathOf(effective)
  if (resolved === resolvedRoot) return true
  const worktreeBase = `${normalizePosixPath(resolvedRoot + "/.plan/local/worktrees")}/`
  return resolved.startsWith(worktreeBase)
}

// The command's EFFECTIVE working directory: the shell's own cwd with a leading
// `cd` and every `env -C` / `--chdir` / `sudo -D` / `--directory` directory
// change applied in order. The wrapper chain is walked with the SHARED table, so
// the directory change is found wherever it sits among a wrapper's options
// (`env -u FOO -C /tmp/x …`, `sudo -u bob -D /tmp/x …`) — an option-order scan
// that stopped at the first non-option would miss exactly those. Returns "" when
// no base is known, which no caller treats as "the repository root".
function effectiveCwd(command, base) {
  if (typeof base !== "string" || !base) return ""
  let current = base.replace(/\\/g, "/").replace(/\/+$/, "")
  if (!current.startsWith("/")) return ""
  const tokens = rawCommandTokens(command)
  const apply = (value) => {
    if (!value) return false
    current = value.startsWith("/") ? normalizePosixPath(value) : normalizePosixPath(`${current}/${value}`)
    return true
  }
  let i = 0
  while (i < tokens.length) {
    const token = stripMatchedQuotes(tokens[i])
    if (isAssignment(token)) {
      i++
      continue
    }
    if (token === "cd") {
      const value = stripMatchedQuotes(tokens[i + 1] ?? "")
      if (!value) return ""
      apply(value)
      i += 2
      continue
    }
    const spec = WRAPPER_TABLE.wrappers[basenameOf(token)]
    if (!spec) break
    const wrapper = basenameOf(token)
    i++
    while (i < tokens.length) {
      const option = stripMatchedQuotes(tokens[i])
      if (isAssignment(option)) {
        i++
        continue
      }
      if (!(option.startsWith("-") && option.length > 1)) break
      const isDirectoryOption =
        option === "-C" ||
        option === "--chdir" ||
        option.startsWith("--chdir=") ||
        (wrapper === "sudo" && (option === "-D" || option === "--directory" || option.startsWith("--directory="))) ||
        (wrapper === "env" && option.startsWith("-C") && option.length > 2)
      if (isDirectoryOption) {
        let value = option.includes("=") ? option.slice(option.indexOf("=") + 1) : null
        if (value === null && option.startsWith("-C") && option.length > 2 && !option.startsWith("--")) {
          value = option.slice(2)
        }
        if (value === null) value = stripMatchedQuotes(tokens[i + 1] ?? "")
        apply(value)
      }
      const step = consumeWrapperOption(spec, option, tokens, i)
      i += step.consumed
      if (step.splice) break
    }
  }
  return current
}

// Collapse a posix path to its normal form (`..` applied, no empty segments),
// always absolute-joined so the caller can test repository containment.
function normalizePosixPath(value) {
  const segments = []
  for (const part of String(value).replace(/\\/g, "/").split("/")) {
    if (part === "" || part === ".") continue
    if (part === "..") {
      segments.pop()
      continue
    }
    segments.push(part)
  }
  return "/" + segments.join("/")
}

// Resolve a script token to its repository-relative path, or null when it does
// not resolve inside the repository. A RELATIVE token is joined with `cwd` (the
// shell's working directory) first, so a token that would execute a copy OUTSIDE
// the repository — a same-named script under the shell's cwd — resolves outside
// `root` and is refused. The joined (or absolute) token is then made relative to
// `root`. Matching compares this key EXACTLY against an allow-list entry, so a
// basename (or a copy of an allow-listed script outside the repository) can never
// match — the suffix hole PLAN-LB-62 shipped.
function repoRelativePath(raw, root, cwd) {
  if (!raw || typeof raw !== "string") return null
  let token = raw.trim().replace(/\\/g, "/")
  const normalizedRoot = (root || "").replace(/\\/g, "/").replace(/\/+$/, "")
  if (!token.startsWith("/") && cwd) {
    const base = String(cwd).replace(/\\/g, "/").replace(/\/+$/, "")
    if (base.startsWith("/")) token = normalizePosixPath(base + "/" + token)
  }
  if (token.startsWith("/")) {
    if (!normalizedRoot) return null
    const prefix = normalizedRoot + "/"
    if (!token.startsWith(prefix)) return null
    token = token.slice(prefix.length)
  }
  const parts = []
  for (const segment of token.split("/")) {
    if (segment === "" || segment === ".") continue
    if (segment === "..") {
      if (parts.length === 0) return null
      parts.pop()
      continue
    }
    parts.push(segment)
  }
  return parts.length ? parts.join("/") : null
}

// Whether a second token is on the shared allow-list, matched EXACTLY on its
// repository-relative path (the relative token joined with the shell `cwd`).
function isAllowListed(command, entries, root, cwd) {
  const tokens = commandTokens(command)
  if (tokens.length < 2) return false
  const relative = repoRelativePath(stripMatchedQuotes(tokens[1]), root, cwd)
  if (relative === null) return false
  return entries.includes(relative)
}

// Resolve a script token to its absolute posix path, or "". A relative token is
// joined with the shell `cwd` (falling back to the project `root`), so the
// deployed-form comparison below sees the same absolute path the shell would
// execute.
function resolvedScriptPath(raw, root, cwd) {
  const token = stripMatchedQuotes(raw).replace(/\\/g, "/")
  if (!token) return ""
  if (token.startsWith("/")) return normalizePosixPath(token)
  const base = (cwd || root || "").replace(/\\/g, "/").replace(/\/+$/, "")
  if (!base.startsWith("/")) return ""
  return normalizePosixPath(base + "/" + token)
}

// The deployed bundle-cache roots, read from the SHARED layout data file
// (`standards/deployed-layout.json`) that the platform-runtime `layout
// bundle-cache-root` resolver reads too — so the resolver and the guard cannot
// disagree about which roots are DEPLOY roots. The union across targets is used
// because a machine may carry more than one harness. Every root is realpath'd,
// so a symlinked tree is never trusted lexically, and a root the layout does not
// name is never a candidate. An unreadable layout yields NO roots (fail closed).
function deployedBundleRoots(root) {
  const data = loadLayoutData(root)
  const home = process.env.HOME || homedir() || ""
  const xdg = process.env.XDG_CONFIG_HOME || (home ? path.join(home, ".config") : "")
  const targets = data && data.targets && typeof data.targets === "object" ? data.targets : {}
  const roots = []
  for (const name of Object.keys(targets)) {
    const templates = Array.isArray(targets[name]) ? targets[name] : []
    for (const template of templates) {
      if (!template || typeof template !== "object") continue
      let base = null
      if (typeof template.env === "string") base = process.env[template.env] || null
      else if (typeof template.xdg === "string") base = xdg || null
      else if (typeof template.home === "string") base = home || null
      if (!base) continue
      const append = typeof template.append === "string" ? template.append : ""
      roots.push(realPathOf(append ? path.join(base, append) : base))
    }
  }
  return [...new Set(roots)]
}

// Resolve a path to its REAL path, falling back to a lexical absolute path when
// the entry does not exist (a candidate that does not exist can never match a
// script that does).
function realPathOf(value) {
  const absolute = path.resolve(String(value))
  try {
    return realpathSync(absolute)
  } catch {
    return absolute
  }
}

// Read the shared deployed-layout data file, or null when it cannot be read.
function loadLayoutData(root) {
  for (const candidate of standardDataCandidates(root, R5_LAYOUT_NAME)) {
    try {
      const data = JSON.parse(readFileSync(candidate, "utf8"))
      if (data && typeof data === "object") return data
    } catch {
      // Try the next candidate.
    }
  }
  return null
}

// The newest version directory of a nested bundle directory that carries the
// resolver's version marker AND carries *entry* — the same rule the resolver
// applies (`bootstrap_plugin.resolve_bundle_path`: newest dir CONTAINING the
// requested path), so the guard cannot select a version the resolver would not.
function newestVersionDir(nested, marker, entry) {
  let entries
  try {
    entries = readdirSync(nested)
  } catch {
    return null
  }
  let newest = null
  for (const name of entries) {
    const candidate = path.join(nested, name)
    try {
      if (!statSync(candidate).isDirectory()) continue
      if (!existsSync(path.join(candidate, ...marker.split("/")))) continue
      if (entry && !existsSync(path.join(candidate, ...String(entry).split("/")))) continue
    } catch {
      continue
    }
    if (newest === null || compareVersionNames(name, path.basename(newest)) > 0) newest = candidate
  }
  return newest
}

// Natural version ordering, mirroring the resolver's `_version_sort_key`: a
// tuple of the DIGIT RUNS in the name, compared element-wise, and a SHORTER
// tuple sorts LOWER when the common prefix is equal — exactly Python's tuple
// comparison, so `1.0.10` sorts before `1.0.10.1` and a digit-less name sorts
// lowest on every side.
function compareVersionNames(left, right) {
  const digits = (value) => (String(value).match(/\d+/g) || []).map(Number)
  const a = digits(left)
  const b = digits(right)
  const common = Math.min(a.length, b.length)
  for (let i = 0; i < common; i++) {
    if (a[i] !== b[i]) return a[i] - b[i]
  }
  return a.length - b.length
}

// Every absolute path a BUNDLE-RELATIVE allow-list entry (`skills/{skill}/{rest}`)
// can be deployed at, across the nested and flat shapes, for every root the
// layout names. The nested shape is `{root}/{nested}/{version}/{entry}` for the
// resolver's version directory (and the unversioned `{root}/{nested}/{entry}`);
// the flat shape reconstructs the skill's dash-namespaced directory name.
function bundleEntryCandidates(entry, roots, layout) {
  const parts = String(entry).split("/")
  if (parts.length < 2 || parts[0] !== "skills") return []
  const skill = parts[1]
  const rest = parts.slice(2).join("/")
  const prefix = (layout && layout.flat_skill_prefix) || "plan-marshall-"
  const nestedName = (layout && layout.nested_bundle_dir) || "plan-marshall"
  const marker = (layout && layout.version_marker) || ".claude-plugin/plugin.json"
  const flatName = `${prefix}${skill}`
  const candidates = new Set()
  for (const root of roots) {
    candidates.add(rest ? path.join(root, flatName, rest) : path.join(root, flatName))
    const nested = path.join(root, nestedName)
    candidates.add(path.join(nested, entry))
    const versionDir = newestVersionDir(nested, marker, entry)
    if (versionDir) candidates.add(path.join(versionDir, entry))
  }
  return [...candidates]
}

// Whether an absolute script path is a DEPLOYED bundle script on the shared
// bundle-relative allow-list. The SCRIPT is realpath'd, while every candidate is
// built lexically from an already-realpath'd root: a symlink pointing out of a
// deployed root therefore resolves to its target and never equals the expected
// deployed path, and a same-named script under a non-deployed directory never
// matches at all.
function isDeployedAllowListed(absolutePath, bundleEntries, roots, layout) {
  if (!absolutePath || !absolutePath.startsWith("/")) return false
  const normalized = realPathOf(absolutePath)
  for (const entry of bundleEntries) {
    for (const candidate of bundleEntryCandidates(entry, roots, layout)) {
      if (normalizePosixPath(candidate) === normalized) return true
    }
  }
  return false
}

// Whether this project IS the plan-marshall source repository (its project-local
// copy of the shared allow-list data file is present).
function isThisRepository(root) {
  if (!root) return false
  return existsSync(path.join(root, ...R5_REPO_MARKER.split("/")))
}

// The plan-context predicate: Signal 1 (the sub-agent identity carries the
// execution-context marker), Signal 2 (the shell workdir, or the project root,
// resolves under a plan-worktree path segment), or Signal 3 (this checkout
// carries a RUNBOOK-LANE marker: a `.plan/temp/rb-<plan>/progress.md` file.
//
// Signal 3 is the lane's own marker: a runbook-lane run issues every call with
// `workdir` = the MAIN checkout, so neither Signal 1 (the lane runs in the main
// context) nor Signal 2 (no worktree path in the cwd) fires, and a consumer
// repository would be left unbound. The progress file is written by the lane
// before any implementation work and lives for the run, which makes it a
// cheaper and narrower signal than guessing from `git -C` targets.
//: A runbook-lane marker older than this no longer binds anything: the marker is
//: written at run start and never removed, so without a freshness bound a single
//: past lane run would bind R1-R5 in a consumer checkout forever.
const LANE_MARKER_MAX_AGE_MS = 24 * 60 * 60 * 1000

function isLaneRun(root) {
  if (!root) return false
  const tempDir = path.join(root, ".plan", "temp")
  let entries
  try {
    entries = readdirSync(tempDir)
  } catch {
    return false
  }
  const now = Date.now()
  return entries.some((name) => {
    if (!name.startsWith("rb-")) return false
    const marker = path.join(tempDir, name, "progress.md")
    try {
      return now - statSync(marker).mtimeMs <= LANE_MARKER_MAX_AGE_MS
    } catch {
      return false
    }
  })
}

function contextGate(agent, workdir, root) {
  if (typeof agent === "string" && agent.includes(EXECUTION_CONTEXT_MARKER)) return true
  for (const candidate of [workdir, root]) {
    if (typeof candidate !== "string" || !candidate) continue
    const normalized = candidate.replace(/\\/g, "/").replace(/\/+$/, "") + "/"
    if (normalized.includes(WORKTREE_PATH_SEGMENT)) return true
  }
  return isLaneRun(root)
}

// Every path a standards DATA FILE (`r5-allowlist.json`, `r5-wrappers.json`) is
// read from, in probe order: the project's own copy first, then every deployed
// platform-runtime skill tree this harness can resolve — including the
// `OPENCODE_CONFIG_DIR` override, which the wizard honours and which the
// allow-list loader must honour identically.
function standardDataCandidates(root, filename) {
  const home = process.env.HOME || homedir() || ""
  const configRoot = process.env.XDG_CONFIG_HOME || (home ? path.join(home, ".config") : "")
  const candidates = [path.join(root, "marketplace", "bundles", "plan-marshall", "skills", "platform-runtime", "standards", filename)]
  const skillRoots = []
  if (process.env.OPENCODE_CONFIG_DIR) skillRoots.push(process.env.OPENCODE_CONFIG_DIR)
  if (configRoot) skillRoots.push(path.join(configRoot, "opencode"))
  if (home) skillRoots.push(path.join(home, ".config", "opencode"))
  for (const skillRoot of skillRoots) {
    for (const name of ["skills", "skill"]) {
      candidates.push(path.join(skillRoot, name, "plan-marshall-platform-runtime", "standards", filename))
    }
  }
  return candidates
}

// Read the shared wrapper table. Absent (or unreadable, or shapeless) yields an
// EMPTY table flagged `missing`, which makes the R5 check fail CLOSED rather
// than silently admitting a wrapped interpreter call.
function loadWrapperTable(root) {
  for (const candidate of standardDataCandidates(root, R5_WRAPPER_TABLE_NAME)) {
    try {
      const data = JSON.parse(readFileSync(candidate, "utf8"))
      if (data && typeof data === "object" && data.wrappers && typeof data.wrappers === "object") {
        const findExec = new Set(Array.isArray(data.find_exec_options) ? data.find_exec_options : [])
        return { wrappers: data.wrappers, findExec, missing: false }
      }
    } catch {
      // Try the next candidate.
    }
  }
  return { wrappers: {}, findExec: new Set(), missing: true }
}

// Read the shared allow-list from the same candidate list, so the wrapper table
// and the allow-list can never be found at different roots. Returns BOTH forms —
// the repository-relative `entries` and the `bundleEntries` matched against a
// deployed bundle root.
function loadAllowList(root) {
  for (const candidate of standardDataCandidates(root, "r5-allowlist.json")) {
    try {
      const data = JSON.parse(readFileSync(candidate, "utf8"))
      const entries = data && data.entries
      const bundleEntries = data && data.bundle_entries
      if (entries && typeof entries === "object") {
        const keys = Object.keys(entries)
        if (keys.length) {
          return {
            entries: keys,
            bundleEntries: bundleEntries && typeof bundleEntries === "object" ? Object.keys(bundleEntries) : [],
          }
        }
      }
    } catch {
      // Try the next candidate.
    }
  }
  return { entries: [...R5_ALLOWLIST_BASE], bundleEntries: [] }
}

const R5_VALUE_TAKING_SINGLE = new Set(["c", "m", "W", "X"])

function isCMCluster(t) {
  if (!t.startsWith("-") || t.startsWith("--")) return false
  if (t.length < 2) return false
  for (const ch of t.slice(1)) {
    if (R5_VALUE_TAKING_SINGLE.has(ch)) return ch === "c" || ch === "m"
  }
  return false
}

function mModuleOf(secondRaw, thirdRaw) {
  const s = typeof secondRaw === "string" ? secondRaw.trim() : ""
  if (s === "-m") return typeof thirdRaw === "string" ? thirdRaw.trim() : ""
  if (s.startsWith("-m") && s.length > 2 && !s.startsWith("--")) return s.slice(2).trim()
  return ""
}

function isInterpreterBypass(secondRaw) {
  if (!secondRaw || typeof secondRaw !== "string") return false
  const t = stripMatchedQuotes(secondRaw)
  if (!t) return false
  if (R5_ALWAYS_REFUSE_FLAGS.has(t)) return true
  if (isCMCluster(t)) return true
  // A bare `-` reads the program from STDIN, and a `-<`/`->` token is a
  // redirection into it (`python3 - < x.py`, `python3 -<<<x`) — all bypass the
  // executor exactly as `-c` does.
  if (t === "-" || t.startsWith("-<") || t.startsWith("->")) return true
  if (t.startsWith("-")) return false
  return true
}

// ---- R5b: interpreter-option prefix (python3 -u script.py) ----
// isInterpreterBypass inspects only the second token, so an interpreter
// option flag in second position (-u, -W, -X, -B, -E, -I, --, bare -)
// hides the script path, -c or -m behind it. Scan every later token with
// the same fail-closed rule: any -c, -m, lone -/--, or non-flag token is a
// bypass. Flag-only tails (python3 --version) and the bare interpreter
// still pass; legitimate work goes through the executor permit.
function hasFlagPrefixedBypass(command) {
  const toks = commandTokens(command).slice(1)
  for (let i = 1; i < toks.length; i++) {
    const t = stripMatchedQuotes(toks[i])
    if (!t) continue
    if (t === "-c" || t === "-m" || t === "-" || t === "--") return true
    if (t.startsWith("-<") || t.startsWith("->")) return true
    if (isCMCluster(t)) return true
    if (!t.startsWith("-")) return true
  }
  return false
}

function targetsExecutor(args) {
  if (!args || typeof args !== "object") return false
  if (normalizedIsExecutorPath(typeof args.filePath === "string" ? args.filePath : "")) return true
  return patchTextTargetsExecutor(typeof args.patchText === "string" ? args.patchText : "")
}

function normalizedIsExecutorPath(raw) {
  if (!raw || typeof raw !== "string") return false
  const normalized = raw.replace(/\\/g, "/")
  return normalized === ".plan/execute-script.py" || normalized.endsWith("/.plan/execute-script.py")
}

// OpenCode's apply_patch tool names its targets in output.args.patchText as
// `*** Add File:` / `*** Update File:` / `*** Move to:` / `*** Delete File:`
// marker lines (plus the legacy bare add/update/move/delete form) rather
// than a filePath. Inspect every operation target (both paths on a move);
// any target resolving under .plan/execute-script.py blocks.
function patchTextTargetsExecutor(patchText) {
  if (!patchText) return false
  const candidates = []
  for (const line of patchText.split("\n")) {
    const op =
      line.match(/^\s*\*+\s+(?:add|update|delete)\s+file:\s*(.+?)\s*$/i) ||
      line.match(/^\s*\*+\s+move\s+to:\s*(.+?)\s*$/i) ||
      line.match(/^\s*(?:add|update|move|delete)\b\s+(.*)$/i)
    if (!op) continue
    const targetPart = op[1]
    const tokenRe = /"([^"]+)"|'([^']+)'|(\S+)/g
    let m
    while ((m = tokenRe.exec(targetPart)) !== null) {
      candidates.push(m[1] ?? m[2] ?? m[3])
    }
  }
  return candidates.some(normalizedIsExecutorPath)
}

// A directory value that still carries a shell expansion is UNRESOLVABLE: the
// guard cannot know where the commit would land, so R6 refuses fail-closed.
const UNRESOLVABLE_DIR_RE = /[$`]/

function isUnresolvableDir(value) {
  return typeof value === "string" && value.length > 0 && UNRESOLVABLE_DIR_RE.test(value)
}

// The plan id a git admin directory names (`.../.git/worktrees/{plan}`), or "".
function planIdFromGitDir(value) {
  const normalized = String(value).replace(/\\/g, "/").replace(/\/+$/, "")
  const marker = "/worktrees/"
  const at = normalized.lastIndexOf(marker)
  if (at === -1) return ""
  return normalized.slice(at + marker.length).split("/")[0]
}

// What a `git commit` command says about the plan it targets. The plan is named
// from EVERY form the harness can express: git's `-C` global option (attached
// form included; successive values COMPOSE, because git applies each in order
// against the running target), the `--git-dir` / `--work-tree` options in both
// detached and `=` form, and the `GIT_DIR` / `GIT_WORK_TREE` assignments that
// precede the program. A `-c alias.NAME=…` subcommand is RESOLVED to its body's
// first word; a shell-expansion body (`!…`) or a directory value carrying `$` or
// a backtick is UNRESOLVABLE, so R6 refuses fail-closed rather than guessing.
// The token list whose first program is `git`, from the command itself or from
// any segment of a wrapper's spliced command string (`zsh -c 'cd /tmp; git
// commit'`), or null. Without this a commit hidden behind a `cd` inside a
// shell's `-c` string would escape R6.
function gitProgramTokens(command) {
  const stripped = commandTokens(command)
  if (stripped.length && basenameOf(stripped[0]).toLowerCase() === "git") {
    return { tokens: stripped, cdTarget: null }
  }
  const raw = rawCommandTokens(command)
  for (let position = 1; position < raw.length; position++) {
    let cdTarget = null
    for (const segment of splicedSegments(stripMatchedQuotes(raw[position]))) {
      const parts = shellSplit(segment)
      const walked = stripWrappers(parts === null ? whitespaceSplit(segment) : parts, WRAPPER_TABLE)
      if (!walked.length) continue
      if (basenameOf(walked[0]) === "cd" && walked[1]) {
        const value = stripMatchedQuotes(walked[1])
        cdTarget = cdTarget === null || value.startsWith("/") ? value : `${cdTarget}/${value}`
        continue
      }
      if (basenameOf(walked[0]).toLowerCase() === "git") return { tokens: walked, cdTarget }
    }
  }
  return null
}

function gitCommitInfo(command) {
  let raw = rawCommandTokens(command)
  const stripped = commandTokens(command)
  let gitAt = -1
  let cdTarget = null
  if (stripped.length && basenameOf(stripped[0]).toLowerCase() === "git") {
    for (let i = 0; i < raw.length; i++) {
      if (basenameOf(raw[i]).toLowerCase() === "git") {
        gitAt = i
        break
      }
    }
    if (gitAt === -1) {
      raw = stripped
      gitAt = 0
    }
  } else {
    const program = gitProgramTokens(command)
    if (program === null) {
      return { isCommit: false, cwdTarget: null, workTree: null, gitDir: null, unresolvable: false }
    }
    raw = program.tokens
    gitAt = 0
    cdTarget = program.cdTarget
  }
  const environment = {}
  for (let i = 0; i < gitAt; i++) {
    const token = stripMatchedQuotes(raw[i])
    const eq = token.indexOf("=")
    if (eq > 0 && /^[A-Za-z_][A-Za-z0-9_]*$/.test(token.slice(0, eq))) {
      environment[token.slice(0, eq)] = token.slice(eq + 1)
    }
  }
  let gitDir = environment.GIT_DIR ?? null
  let workTree = environment.GIT_WORK_TREE ?? null
  let unresolvable = isUnresolvableDir(gitDir) || isUnresolvableDir(workTree) || isUnresolvableDir(cdTarget)
  const aliases = {}
  let cwdTarget = cdTarget
  let subcommand = null
  let i = gitAt + 1
  while (i < raw.length) {
    const token = stripMatchedQuotes(raw[i])
    if (token === "-C") {
      const value = stripMatchedQuotes(raw[i + 1] ?? "")
      cwdTarget = cwdTarget === null || value.startsWith("/") ? value : `${cwdTarget}/${value}`
      if (isUnresolvableDir(value)) unresolvable = true
      i += 2
      continue
    }
    if (token.startsWith("-C") && !token.startsWith("--") && token.length > 2) {
      const value = token.slice(2)
      cwdTarget = cwdTarget === null || value.startsWith("/") ? value : `${cwdTarget}/${value}`
      if (isUnresolvableDir(value)) unresolvable = true
      i += 1
      continue
    }
    let matchedTargetOption = false
    for (const prefix of ["--git-dir", "--work-tree"]) {
      if (token === prefix || token.startsWith(`${prefix}=`)) {
        let value
        if (token.includes("=")) {
          value = token.slice(token.indexOf("=") + 1)
          i += 1
        } else {
          value = stripMatchedQuotes(raw[i + 1] ?? "")
          i += 2
        }
        if (prefix === "--git-dir") gitDir = value
        else workTree = value
        if (isUnresolvableDir(value)) unresolvable = true
        matchedTargetOption = true
        break
      }
    }
    if (matchedTargetOption) continue
    if (token === "-c" || (token.startsWith("-c") && !token.startsWith("--"))) {
      let value
      if (token === "-c") {
        value = stripMatchedQuotes(raw[i + 1] ?? "")
        i += 2
      } else {
        value = token.slice(2)
        i += 1
      }
      const eq = value.indexOf("=")
      if (eq > 0 && value.slice(0, eq).startsWith("alias.")) {
        aliases[value.slice(0, eq).slice("alias.".length)] = value.slice(eq + 1)
      }
      continue
    }
    if (token.startsWith("-")) {
      i += GIT_VALUE_OPTIONS.has(token) ? 2 : 1
      continue
    }
    subcommand = token.toLowerCase()
    break
  }
  if (subcommand !== null && aliases[subcommand]) {
    const body = aliases[subcommand]
    if (body.startsWith("!") || isUnresolvableDir(body)) {
      // The alias body cannot be reduced to a plain subcommand, so whether this
      // is a commit is unknown: refuse fail-closed.
      return { isCommit: true, cwdTarget, workTree, gitDir, unresolvable: true }
    }
    const parts = shellSplit(body)
    const resolved = parts === null ? whitespaceSplit(body) : parts
    subcommand = (resolved[0] ?? "").toLowerCase()
  }
  return { isCommit: subcommand === "commit", cwdTarget, workTree, gitDir, unresolvable }
}

// The plan worktree a path names: `{ root, planId }` for a path carrying
// `.plan/local/worktrees/{plan_id}`, else null. The plan is NAMED by the path,
// so R6 never judges "the first plan found". When a path carries more than one
// such segment, the INNERMOST (last) names the plan.
function worktreeInfoFromPath(candidate) {
  if (typeof candidate !== "string" || !candidate) return null
  const normalized = candidate.replace(/\\/g, "/")
  const marker = "/.plan/local/worktrees/"
  const at = normalized.lastIndexOf(marker)
  if (at === -1) return null
  const planId = normalized.slice(at + marker.length).split("/")[0]
  if (!planId) return null
  return { root: normalized.slice(0, at + marker.length + planId.length), planId }
}

// The MAIN checkout's `.plan/local` directory — the anchor the plan resolution
// uses, mirroring marketplace_paths.resolve_main_anchored_path: a PLAN_BASE_DIR
// override stands in for it; otherwise main is derived from git's common dir
// (main's `.git`) even when the project directory is a linked worktree. Null
// when neither resolves, so R6 does not fire rather than guess.
function mainPlanLocalDir(root) {
  const override = process.env.PLAN_BASE_DIR
  if (override) return override.replace(/\/+$/, "")
  try {
    // Strip Git's repository-LOCATION environment variables from the child: if
    // GIT_DIR / GIT_WORK_TREE (etc.) are set they override `-C root` and the
    // resolution would name the wrong repository. A timeout keeps a hung `git`
    // from blocking the tool call indefinitely.
    const env = { ...process.env }
    for (const key of ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR"]) {
      delete env[key]
    }
    const out = execFileSync("git", ["-C", root, "rev-parse", "--git-common-dir"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 5000,
      env,
    }).trim()
    if (!out) return null
    const common = path.isAbsolute(out) ? out : path.resolve(root, out)
    return path.join(path.dirname(common), ".plan", "local")
  } catch {
    return null
  }
}

// Resolve a possibly-relative target path against a base directory, returning a
// normalized posix path, or "" when no base is available for a relative target.
function resolveTargetPath(target, base) {
  if (typeof target !== "string" || !target) return ""
  const normalized = target.replace(/\\/g, "/")
  if (normalized.startsWith("/")) return normalizePosixPath(normalized)
  const normalizedBase = (base || "").replace(/\\/g, "/").replace(/\/+$/, "")
  if (!normalizedBase.startsWith("/")) return ""
  return normalizePosixPath(normalizedBase + "/" + normalized)
}

// The enclosing plan's phase, read from the plan's own status.json field
// `current_phase`. The plan is NAMED, in priority order, by the `--work-tree`
// value, then the composed `git -C` target, then the plan a `--git-dir` /
// `GIT_DIR` admin directory points at (`.../worktrees/{plan}`), then the shell
// `workdir`, then the project `root` — never "the first plan found". The record
// is the WORKTREE-RESIDENT one first (the live one during phase 5+), then the
// main-anchored live record. Empty when no plan worktree is named, or no
// readable record resolves.
function planPhase(workdir, root, info) {
  const candidates = []
  const addTarget = (value) => {
    if (!value) return
    const named = worktreeInfoFromPath(resolveTargetPath(value, workdir || root))
    if (named) candidates.push(named)
  }
  if (info) {
    addTarget(info.workTree)
    addTarget(info.cwdTarget)
    if (info.gitDir) {
      const planId = planIdFromGitDir(info.gitDir)
      if (planId && root) {
        candidates.push({ root: path.join(root, ".plan", "local", "worktrees", planId), planId })
      }
    }
  }
  const fromWorkdir = worktreeInfoFromPath(workdir)
  if (fromWorkdir) candidates.push(fromWorkdir)
  const fromRoot = worktreeInfoFromPath(root)
  if (fromRoot) candidates.push(fromRoot)
  const base = mainPlanLocalDir(root)
  for (const named of candidates) {
    const statuses = [path.join(named.root, ".plan", "local", "plans", named.planId, "status.json")]
    if (base !== null) statuses.push(path.join(base, "plans", named.planId, "status.json"))
    for (const candidate of statuses) {
      let data
      try {
        data = JSON.parse(readFileSync(candidate, "utf8"))
      } catch (error) {
        if (error && error.code === "ENOENT") continue
        return ""
      }
      if (data && typeof data.current_phase === "string" && data.current_phase) return data.current_phase
      return ""
    }
  }
  return ""
}

// R6 — a raw `git commit` in phase 6-finalize is refused: every plan commit
// must pass through the gate-bearing `git-workflow commit` verb. The plan is
// named from every commit form (see `gitCommitInfo`) and its phase read from
// `current_phase`; an UNRESOLVABLE target (an unexpanded variable, an alias the
// guard cannot reduce) is refused fail-closed.
function isRawFinalizeCommit(command, workdir, root, agent) {
  const info = gitCommitInfo(command)
  if (!info.isCommit) return false
  if (info.unresolvable) {
    // Fail-closed ONLY inside the enforced scope (Signal 1 included): an
    // unrelated consumer's `git -C "$dir" commit` is not this rule's business.
    return contextGate(agent, workdir, root) || isThisRepository(root)
  }
  return planPhase(workdir, root, info) === SOURCE_COMMIT_GATE_PHASE
}

function auditLine(rule, tool, sessionID, callID, detail) {
  return `${new Date().toISOString()} | tool=${tool} | rule=${rule} | session=${sessionID} | call=${callID} | ${detail}`
}

export default Plugin.define({
  id: "plan-marshall-guard",
  async setup(ctx) {
    const root = ctx.location?.directory || "."
    const logPath = path.join(root, ".plan", "temp", "guard.log")
    const allowList = loadAllowList(root)
    const deployedRoots = deployedBundleRoots(root)
    const layoutData = loadLayoutData(root)
    WRAPPER_TABLE = loadWrapperTable(root)

    function audit(entry) {
      try {
        mkdirSync(path.dirname(logPath), { recursive: true })
        appendFileSync(logPath, entry + "\n", "utf8")
      } catch {
        // An audit failure must never mask the throw that triggered it.
      }
    }

    await ctx.tool.hook("execute.before", async (event) => {
      const tool = event?.tool ?? ""
      const sessionID = event?.sessionID ?? event?.sessionId ?? "?"
      const callID = event?.callID ?? event?.callId ?? event?.id ?? "?"
      const args = (event && (event.input ?? event.args ?? event.params)) || {}
      const command = typeof args.command === "string" ? args.command : ""
      const workdir = typeof args.workdir === "string" ? args.workdir : ""

      if (tool === "edit" || tool === "write" || tool === "patch" || tool === "apply_patch") {
        if (targetsExecutor(args)) {
          audit(auditLine("R3", tool, sessionID, callID, command || String(args.filePath ?? "")))
          throw new Error(
            "[plan-marshall-guard] R3: direct edits to the generated executor (.plan/execute-script.py) are forbidden; access .plan/ via manage-* scripts only",
          )
        }
        return
      }

      // OpenCode 2 names its shell tool `shell`; OpenCode 1 named it `bash`.
      if (tool !== "shell" && tool !== "bash") return

      if (hasChainingConstructor(command)) {
        audit(auditLine("R1", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R1: shell-chaining constructors (&&, &, ;, |, $(), subshells, process substitutions, backticks, newline) are forbidden; one command per Bash call",
        )
      }

      const token = normalizeToken(tokenAt(command, 0))
      const rawToken = normalizeToken(rawCommandTokens(command)[0] ?? "")
      if ((token && MUTATION_FILE_OPS.has(token)) || (rawToken && MUTATION_FILE_OPS.has(rawToken))) {
        audit(auditLine("R2", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R2: shell file operations (mutation class) via Bash are forbidden; use the Read/Edit/Write tools or manage-* scripts",
        )
      }

      if (isRawFinalizeCommit(command, workdir, root, event?.agent)) {
        audit(auditLine("R6", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R6: a raw git commit is refused in phase 6-finalize — commit through python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow commit (the gate-bearing path), which sanctions an open loop-back fix task, a review-rubric section-6 record, or a step id of the composed phase-6 manifest",
        )
      }

      if (isExecutorPermit(command, root, workdir)) return
      if (token === "./pw" || basenameOf(tokenAt(command, 0)) === "pw") {
        const verb = tokenAt(command, 1)
        const passes = Boolean(verb && (verb.startsWith("generate") || verb.startsWith("--")))
        if (!passes) {
          audit(auditLine("R4", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R4: hard-coded build via ./pw is forbidden; route builds through python3 .plan/execute-script.py",
          )
        }
        return
      }

      if (BARE_BUILD_TOOLS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }

      if (JS_RUNNER_BUILD_VERBS.has(normalizeToken(tokenAt(command, 1))) && JS_RUNNERS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }

      // Fail CLOSED when the shared wrapper table is unavailable: without it
      // no wrapper can be stripped, so refuse any command that names an
      // interpreter anywhere rather than letting a prefix hide the call.
      if (WRAPPER_TABLE.missing && (contextGate(event?.agent, workdir, root) || isThisRepository(root))) {
        if (rawCommandTokens(command).some((candidate) => isPythonInterpreter(candidate))) {
          audit(auditLine("R5", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R5: the shared wrapper table (standards/r5-wrappers.json) is unavailable, so no wrapper can be stripped; the invocation is refused because it names an interpreter",
          )
        }
      }

      if (PYTHON_INTERPRETERS.has(token) || isPythonInterpreter(token)) {
        const second = basenameOf(tokenAt(command, 1))
        const mModule = normalizeToken(mModuleOf(tokenAt(command, 1), tokenAt(command, 2)))
        if (second === "build.py" || (mModule && PYTHON_DIRECT_RUNNERS.has(mModule))) {
          audit(auditLine("R4", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
          )
        }
        // R5 binds inside a plan context and in EVERY session of THIS repository;
        // in a consumer repository outside a plan context it does not refuse a
        // consumer's ordinary Python work (python3 x.py, python3 -m venv,
        // python3 -m pip). Inside one it refuses every non-executor form.
        if (contextGate(event?.agent, workdir, root) || isThisRepository(root)) {
          // Two admissions, both EXACT: the repository-relative allow-list, and
          // the deployed bundle-relative allow-list matched against a resolved
          // bundle-cache root.
          if (isAllowListed(command, allowList.entries, root, workdir || root)) return
          const scriptPath = resolvedScriptPath(tokenAt(command, 1), root, workdir || root)
          if (isDeployedAllowListed(scriptPath, allowList.bundleEntries, deployedRoots, layoutData)) return
          if (isInterpreterBypass(tokenAt(command, 1)) || hasFlagPrefixedBypass(command)) {
            audit(auditLine("R5", tool, sessionID, callID, command))
            throw new Error(
              "[plan-marshall-guard] R5: direct python interpreter calls (python -c, script paths, python -m) bypassing the executor are forbidden; route builds and checks via python3 .plan/execute-script.py and .plan state via manage-* verbs or the Read/Edit/Write tools",
            )
          }
        }
        return
      }

      if (PYTHON_DIRECT_RUNNERS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }
    })
  },
})
