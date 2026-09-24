/**
 * plan-marshall guard plugin — tool.execute.before enforcement of R1-R4.
 *
 * The opencode host loads every module under `{plugin,plugins}/*.{ts,js}` in the
 * project config directory and imports it with Bun. This plugin registers a
 * `tool.execute.before` hook that inspects each tool invocation against the four
 * plan-marshall hard-rule bypass classes and THROWS to block the execution,
 * appending one audit line to `.plan/temp/guard.log` per blocked invocation.
 *
 * The plugin is not covered by the Python test harness; its decision table below
 * is mirrored as a behavioral contract in
 * `test/plan-marshall/platform-runtime/test_opencode_enforcement.py`. Keep the
 * two in lock-step when the table changes.
 *
 * DECISION TABLE (authoritative — mirrored in the D4 runtime matrix):
 *
 *   Guarded tools: bash (R1, R2, R4), edit/write/patch (R3). Every other tool
 *   passes through untouched.
 *
  *   R1 — shell-chaining constructors (bash): the command, with single-quoted
  *   regions stripped and double-quoted regions stripped except for command
  *   substitution, contains `&&`, `||`, `;`, `|`, `$(`,
  *   a backtick, a trailing `&`, or a newline  => block. `$(` and backticks
  *   inside double quotes still block because Bash executes them there.
 *
 *   R2 — shell file operations, mutation class (bash): the command's first token
 *   is one of {rm mv cp touch mkdir rmdir truncate tee chmod chown ln dd}  => block.
 *   Read-side probes (ls cat head tail grep find) are NOT in this guard class:
 *   the two-tier permission map governs them (global deny, orchestrator
 *   small-ops carve-out under ask). Shell spawns `sh`/`bash`/`source` also block.
 *
 *   R3 — direct edits to the generated executor path (edit/write/patch): the
 *   target resolves under `.plan/execute-script.py`  => block.
 *
 *   R4 — hard-coded build commands bypassing `python3 .plan/execute-script.py`
 *   (bash): route builds through the executor only. Block when:
 *     - first token is `./pw` with no verb or a build verb
  *       {verify compile test-compile module-tests coverage quality-gate clean gate
  *        test run check lint format build install tests} (`./pw generate*` and `./pw --*` pass);
 *     - first token is a bare build tool {mvn mvnw gradle gradlew make cmake ant
 *       uv}; or a JS runner {npm npx bun pnpm yarn} followed by
 *       {test run build};
 *     - first token is `python3` and the second token is `build.py`;
 *     - `python3 -m {pytest mypy ruff}`; a bare {pytest mypy ruff}.
 *   The executor permit `python3 .plan/execute-script.py <verb> ...` is exempt.
 */
import { appendFileSync, mkdirSync } from "node:fs"
import path from "node:path"

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
  return /&&|\|\||[;|]|\$\(|`|&\s*$|\n/.test(unquoted)
}

// ---- R2: shell file operations, mutation class (declared set, mirrored) ----
const MUTATION_FILE_OPS = new Set([
  "rm", "mv", "cp", "touch", "mkdir", "rmdir", "truncate", "tee",
  "chmod", "chown", "ln", "dd", "sh", "bash", "source",
])

// ---- R4: hard-coded build bypasses (declared sets, mirrored) ----
// PW_BUILD_VERBS is derived from the authoritative aliases in
// pyproject.toml [tool.pyprojectx.aliases]: every alias routing through
// build.py (build, clean, compile, coverage, module-tests, quality-gate,
// test-compile, verify) plus the direct-tool aliases that bypass the
// executor (install, lint, format) and legacy typo guards. When a new
// build.py subcommand or alias lands, extend this set in lock-step.
const PW_BUILD_VERBS = new Set([
  "verify", "compile", "test-compile", "module-tests", "coverage",
  "quality-gate", "clean", "gate",
  "test", "run", "check", "lint", "format", "build", "install", "tests",
])
const BARE_BUILD_TOOLS = new Set(["mvn", "mvnw", "gradle", "gradlew", "make", "cmake", "ant", "uv"])
const JS_RUNNER_BUILD_VERBS = new Set(["test", "run", "build"])
const PYTHON_DIRECT_RUNNERS = new Set(["pytest", "mypy", "ruff"])

// Shell wrappers (`command`, `env`, `sudo`) and leading `NAME=value`
// assignments are transparent to the shell: `command rm -f file` still runs
// `rm`. Strip them before first-token checks so R2/R4 cannot be bypassed
// by prefixing a blocked invocation.
const SHELL_WRAPPERS = new Set(["command", "env", "sudo"])

function commandTokens(command) {
  const tokens = command.trimStart().split(/\s+/)
  let i = 0
  while (i < tokens.length) {
    const t = tokens[i]
    if (SHELL_WRAPPERS.has(t)) {
      i++
      continue
    }
    if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(t)) {
      i++
      continue
    }
    break
  }
  return tokens.slice(i)
}

function tokenAt(command, index) {
  const tokens = commandTokens(command)
  return tokens[index] ?? ""
}

function isExecutorPermit(command) {
  return /^python3\s+\.plan\/execute-script\.py\b/.test(commandTokens(command).join(" "))
}

function targetsExecutor(args) {
  if (!args || typeof args !== "object") return false
  const raw = typeof args.filePath === "string" ? args.filePath : ""
  if (!raw) return false
  const normalized = raw.replace(/\\/g, "/")
  return normalized === ".plan/execute-script.py" || normalized.endsWith("/.plan/execute-script.py")
}

function auditLine(rule, tool, sessionID, callID, detail) {
  return `${new Date().toISOString()} | tool=${tool} | rule=${rule} | session=${sessionID} | call=${callID} | ${detail}`
}

export const GuardPlugin = async ({ worktree, directory }) => {
  const root = worktree || directory || "."
  const logPath = path.join(root, ".plan", "temp", "guard.log")

  function audit(entry) {
    try {
      mkdirSync(path.dirname(logPath), { recursive: true })
      appendFileSync(logPath, entry + "\n", "utf8")
    } catch {
      // An audit failure must never mask the throw that triggered it.
    }
  }

  return {
    "tool.execute.before": async (input, output) => {
      const tool = input?.tool ?? ""
      const sessionID = input?.sessionID ?? "?"
      const callID = input?.callID ?? "?"
      const args = (output && output.args) || {}
      const command = typeof args.command === "string" ? args.command : ""

      if (tool === "edit" || tool === "write" || tool === "patch") {
        if (targetsExecutor(args)) {
          audit(auditLine("R3", tool, sessionID, callID, command || String(args.filePath ?? "")))
          throw new Error(
            "[plan-marshall-guard] R3: direct edits to the generated executor (.plan/execute-script.py) are forbidden; access .plan/ via manage-* scripts only",
          )
        }
        return
      }

      if (tool !== "bash") return

      if (hasChainingConstructor(command)) {
        audit(auditLine("R1", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R1: shell-chaining constructors (&&, ;, |, $(), backticks, trailing &, newline) are forbidden; one command per Bash call",
        )
      }

      const token = tokenAt(command, 0)
      if (token && MUTATION_FILE_OPS.has(token)) {
        audit(auditLine("R2", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R2: shell file operations (mutation class) via Bash are forbidden; use the Read/Edit/Write tools or manage-* scripts",
        )
      }

      if (isExecutorPermit(command)) return

      if (token === "./pw") {
        const verb = tokenAt(command, 1)
        if (!verb || PW_BUILD_VERBS.has(verb)) {
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

      if (JS_RUNNER_BUILD_VERBS.has(tokenAt(command, 1)) && new Set(["npm", "npx", "bun", "pnpm", "yarn"]).has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }

      if (token === "python3") {
        const second = tokenAt(command, 1)
        const third = tokenAt(command, 2)
        if (second === "build.py" || (second === "-m" && PYTHON_DIRECT_RUNNERS.has(third))) {
          audit(auditLine("R4", tool, sessionID, callID, command))
          throw new Error(
            "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
          )
        }
        return
      }

      if (PYTHON_DIRECT_RUNNERS.has(token)) {
        audit(auditLine("R4", tool, sessionID, callID, command))
        throw new Error(
          "[plan-marshall-guard] R4: hard-coded build command bypassing python3 .plan/execute-script.py is forbidden",
        )
      }
    },
  }
}