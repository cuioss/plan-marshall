"""OpenCode adapter for marketplace export.

Translates Claude Code marketplace format into OpenCode's expected structure:
  .opencode/skills/{bundle}-{skill}/SKILL.md
  .opencode/agents/{agent-name}.md
  .opencode/commands/{command-name}.md
  opencode.json

The adapter reads plugin.json from each bundle, transforms frontmatter,
and copies body content with directive adjustments.

OpenCode spec references:
- Skills: agentskills.io/specification, .opencode/skills/<name>/SKILL.md
- Agents: .opencode/agents/<name>.md with model/mode/permission frontmatter
- Commands: .opencode/commands/<name>.md with description/agent frontmatter
- Config: opencode.json with $schema, instructions, agent overrides

Note: This adapter has only been tested with Claude Code as the primary runtime.
The generated OpenCode output follows the OpenCode specification but has not been
validated in a live OpenCode environment.
"""

import json
import re
import shutil
from pathlib import Path

from marketplace.adapters.adapter_base import AdapterBase

# Tool name mapping: Claude Code -> OpenCode (lowercase equivalents)
TOOL_NAME_MAP: dict[str, str] = {
    'Read': 'read',
    'Write': 'write',
    'Edit': 'edit',
    'Glob': 'glob',
    'Grep': 'grep',
    'Bash': 'bash',
    'WebFetch': 'webfetch',
    'WebSearch': 'websearch',
    'AskUserQuestion': 'question',
    'Task': 'task',
    'Skill': 'skill',
    'NotebookEdit': 'edit',
}

# OpenCode permission categories for Claude Code tools
# OpenCode groups tools into permission categories: read, edit, bash, grep, glob, etc.
TOOL_PERMISSION_MAP: dict[str, str] = {
    'Read': 'read',
    'Write': 'edit',
    'Edit': 'edit',
    'Glob': 'glob',
    'Grep': 'grep',
    'Bash': 'bash',
    'WebFetch': 'webfetch',
    'WebSearch': 'websearch',
    'AskUserQuestion': 'question',
    'Task': 'task',
    'Skill': 'skill',
    'NotebookEdit': 'edit',
}

# Claude model shorthand -> full OpenCode model ID (provider/model-id format)
MODEL_MAP: dict[str, str] = {
    'opus': 'anthropic/claude-opus-4',
    'sonnet': 'anthropic/claude-sonnet-4',
    'haiku': 'anthropic/claude-haiku-4',
}

# Tools that indicate deep Claude Code coupling (skip these agents)
CLAUDE_ONLY_TOOLS = {'Task', 'Skill'}


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown file content.

    Returns:
        Tuple of (frontmatter dict, body text after frontmatter).
        Returns empty dict and full content if no frontmatter found.
    """
    if not content.startswith('---'):
        return {}, content

    end = content.find('---', 3)
    if end == -1:
        return {}, content

    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip('\n')

    fm: dict[str, str] = {}
    current_key = ''
    current_value = ''
    in_multiline = False
    list_items: list[str] = []
    in_list = False

    for line in fm_text.split('\n'):
        stripped = line.strip()

        # List item
        if stripped.startswith('- ') and in_list:
            list_items.append(stripped[2:])
            continue

        # End of list - save it
        if in_list and not stripped.startswith('- '):
            fm[current_key] = ', '.join(list_items)
            in_list = False
            list_items = []

        # Multiline value continuation
        if in_multiline:
            if ':' in stripped and not stripped.startswith(' ') and not stripped.startswith('-'):
                fm[current_key] = current_value.strip()
                in_multiline = False
            else:
                current_value += '\n' + line
                continue

        if ':' not in stripped:
            if in_multiline:
                current_value += '\n' + line
            continue

        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip()

        if not value:
            # Could be start of a list or multiline
            current_key = key
            in_list = True
            list_items = []
            continue

        if value == '|':
            current_key = key
            current_value = ''
            in_multiline = True
            continue

        fm[key] = value

    # Flush remaining
    if in_multiline:
        fm[current_key] = current_value.strip()
    if in_list and list_items:
        fm[current_key] = ', '.join(list_items)

    return fm, body


def transform_skill_frontmatter(fm: dict[str, str], bundle: str, skill_name: str) -> str:
    """Transform Claude Code skill frontmatter to OpenCode format.

    OpenCode skill frontmatter follows the Agent Skills spec (agentskills.io):
    - name: lowercase kebab-case, must match directory name
    - description: 1-1024 chars
    - compatibility: optional environment description

    OpenCode only parses name and description at discovery time. The full
    SKILL.md body is loaded when the skill tool is invoked at runtime.

    Args:
        fm: Parsed frontmatter dict.
        bundle: Bundle name for prefix.
        skill_name: Original skill directory name.

    Returns:
        OpenCode-formatted YAML frontmatter string (with --- delimiters).
    """
    oc_name = f'{bundle}-{skill_name}'
    desc = fm.get('description', '')
    # Clean multiline descriptions
    if '\n' in desc:
        desc = desc.split('\n')[0].strip()

    lines = [
        '---',
        f'name: {oc_name}',
        f'description: {desc}',
        'compatibility: Adapted from plan-marshall marketplace (Claude Code native)',
        '---',
    ]
    return '\n'.join(lines)


def transform_agent_frontmatter(fm: dict[str, str]) -> str:
    """Transform Claude Code agent frontmatter to OpenCode format.

    OpenCode agent frontmatter uses:
    - description: when to use this agent
    - model: provider/model-id format
    - mode: subagent|primary|all
    - permission: tool permission rules (replaces deprecated tools: field)

    The filename (minus .md) becomes the agent identifier in OpenCode.

    Args:
        fm: Parsed frontmatter dict.

    Returns:
        OpenCode-formatted YAML frontmatter string (with --- delimiters).
    """
    desc = fm.get('description', '')
    if '\n' in desc:
        desc = desc.split('\n')[0].strip()

    lines = [
        '---',
        f'description: {desc}',
        'mode: subagent',
    ]

    # Map model
    model = fm.get('model', '')
    if model and model in MODEL_MAP:
        lines.append(f'model: {MODEL_MAP[model]}')

    # Build permission object from Claude Code tools list
    tools_str = fm.get('tools', '')
    if tools_str:
        tools = [t.strip() for t in tools_str.split(',')]
        permissions = sorted({TOOL_PERMISSION_MAP.get(t, t.lower()) for t in tools if t not in CLAUDE_ONLY_TOOLS})
        if permissions:
            lines.append('permission:')
            for perm in permissions:
                lines.append(f'  {perm}: allow')

    lines.append('---')
    return '\n'.join(lines)


def transform_command_frontmatter(fm: dict[str, str]) -> str:
    """Transform Claude Code command frontmatter to OpenCode format.

    OpenCode command frontmatter uses:
    - description: brief description shown in TUI
    - agent: which agent executes the command (optional)
    - subtask: force subagent invocation (optional)

    The markdown body becomes the command template. The filename (minus .md)
    becomes the command name (invoked as /command-name).

    Args:
        fm: Parsed frontmatter dict.

    Returns:
        OpenCode-formatted YAML frontmatter string (with --- delimiters).
    """
    desc = fm.get('description', '')
    if '\n' in desc:
        desc = desc.split('\n')[0].strip()

    lines = [
        '---',
        f'description: {desc}',
    ]

    lines.append('---')
    return '\n'.join(lines)


def transform_body(body: str, bundle: str) -> str:
    """Transform Claude-specific directives in body text.

    Handles:
    - ``Skill: bundle:skill-name`` -> OpenCode skill tool invocation hint
    - Tool name capitalization in code blocks left as-is (instructional context)

    In OpenCode, skills are loaded via the built-in ``skill`` tool at runtime,
    not via directives. The adapter adds comments explaining the equivalent.

    Args:
        body: Markdown body text after frontmatter.
        bundle: Current bundle name for context.

    Returns:
        Transformed body text.
    """
    # Transform Skill: directives
    # Pattern: lines like "Skill: bundle:skill-name" or "Skill: skill-name"
    def replace_skill_directive(match: re.Match[str]) -> str:
        full = match.group(0)
        ref = match.group(1).strip()
        if ':' in ref:
            parts = ref.split(':')
            b = parts[0]
            s = parts[1]
        else:
            b = bundle
            s = ref
        oc_name = f'{b}-{s}'
        return f'{full}\n<!-- OpenCode: use skill tool to load "{oc_name}" -->'

    body = re.sub(r'^Skill:\s*(.+)$', replace_skill_directive, body, flags=re.MULTILINE)

    return body


def agent_uses_claude_only_tools(fm: dict[str, str]) -> bool:
    """Check if an agent relies heavily on Claude-only tools (Task, Skill).

    Args:
        fm: Parsed frontmatter dict.

    Returns:
        True if the agent uses Task or Skill tools.
    """
    tools_str = fm.get('tools', '')
    if not tools_str:
        return False
    tools = {t.strip() for t in tools_str.split(',')}
    return bool(tools & CLAUDE_ONLY_TOOLS)


class OpenCodeAdapter(AdapterBase):
    """Adapter that exports marketplace bundles to OpenCode format.

    Generates:
    - .opencode/skills/{bundle}-{skill}/SKILL.md  (Agent Skills spec compliant)
    - .opencode/agents/{agent-name}.md  (agents without Claude-only tool deps)
    - .opencode/commands/{command-name}.md
    - opencode.json project configuration
    """

    def name(self) -> str:
        return 'opencode'

    def supports_agents(self) -> bool:
        return True

    def supports_commands(self) -> bool:
        return True

    def generate(self, marketplace_dir: Path, output_dir: Path, bundles: list[str] | None = None) -> list[Path]:
        """Generate OpenCode output from marketplace bundles.

        Args:
            marketplace_dir: Path to marketplace/bundles/ directory.
            output_dir: Path to write .opencode/ structure.
            bundles: Optional list of bundle names. None means all.

        Returns:
            List of all generated file paths.
        """
        generated: list[Path] = []

        # Discover bundles
        bundle_dirs = self._discover_bundles(marketplace_dir, bundles)

        for bundle_dir in bundle_dirs:
            plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
            if not plugin_json.exists():
                continue

            config = json.loads(plugin_json.read_text())
            bundle_name = config.get('name', bundle_dir.name)

            # Export skills
            generated.extend(self._export_skills(bundle_dir, config, bundle_name, output_dir))

            # Export agents
            generated.extend(self._export_agents(bundle_dir, config, bundle_name, output_dir))

            # Export commands
            generated.extend(self._export_commands(bundle_dir, config, bundle_name, output_dir))

        # Generate opencode.json
        config_path = output_dir.parent / 'opencode.json'
        generated.append(self._generate_config(config_path, output_dir))

        return generated

    def _discover_bundles(self, marketplace_dir: Path, bundles: list[str] | None) -> list[Path]:
        """Find bundle directories to process."""
        if bundles:
            return [marketplace_dir / b for b in bundles if (marketplace_dir / b).is_dir()]

        return sorted(d for d in marketplace_dir.iterdir() if d.is_dir() and not d.name.startswith('.'))

    def _export_skills(
        self, bundle_dir: Path, config: dict, bundle_name: str, output_dir: Path
    ) -> list[Path]:
        """Export skills from a bundle."""
        generated: list[Path] = []

        for skill_ref in config.get('skills', []):
            # skill_ref is like "./skills/junit-core"
            skill_path = bundle_dir / skill_ref.lstrip('./')
            skill_md = skill_path / 'SKILL.md'

            if not skill_md.exists():
                continue

            skill_name = skill_path.name
            content = skill_md.read_text()
            fm, body = parse_frontmatter(content)

            # Generate OpenCode SKILL.md
            oc_skill_dir = output_dir / 'skills' / f'{bundle_name}-{skill_name}'
            oc_skill_dir.mkdir(parents=True, exist_ok=True)

            new_fm = transform_skill_frontmatter(fm, bundle_name, skill_name)
            new_body = transform_body(body, bundle_name)
            oc_skill_md = oc_skill_dir / 'SKILL.md'
            oc_skill_md.write_text(new_fm + '\n\n' + new_body)
            generated.append(oc_skill_md)

            # Copy standards/references subdirectories verbatim
            for subdir_name in ('standards', 'references', 'templates'):
                src_subdir = skill_path / subdir_name
                if src_subdir.exists() and src_subdir.is_dir():
                    dst_subdir = oc_skill_dir / subdir_name
                    if dst_subdir.exists():
                        shutil.rmtree(dst_subdir)
                    shutil.copytree(src_subdir, dst_subdir)
                    for f in dst_subdir.rglob('*'):
                        if f.is_file():
                            generated.append(f)

            # Copy scripts verbatim
            src_scripts = skill_path / 'scripts'
            if src_scripts.exists() and src_scripts.is_dir():
                dst_scripts = oc_skill_dir / 'scripts'
                if dst_scripts.exists():
                    shutil.rmtree(dst_scripts)
                shutil.copytree(src_scripts, dst_scripts)
                for f in dst_scripts.rglob('*'):
                    if f.is_file():
                        generated.append(f)

        return generated

    def _export_agents(
        self, bundle_dir: Path, config: dict, bundle_name: str, output_dir: Path
    ) -> list[Path]:
        """Export agents from a bundle, skipping those with Claude-only tool dependencies."""
        generated: list[Path] = []

        for agent_ref in config.get('agents', []):
            agent_path = bundle_dir / agent_ref.lstrip('./')
            if not agent_path.exists():
                continue

            content = agent_path.read_text()
            fm, body = parse_frontmatter(content)

            # Skip agents that rely on Claude-only tools
            if agent_uses_claude_only_tools(fm):
                continue

            agents_dir = output_dir / 'agents'
            agents_dir.mkdir(parents=True, exist_ok=True)

            new_fm = transform_agent_frontmatter(fm)
            new_body = transform_body(body, bundle_name)
            oc_agent = agents_dir / agent_path.name
            oc_agent.write_text(new_fm + '\n\n' + new_body)
            generated.append(oc_agent)

        return generated

    def _export_commands(
        self, bundle_dir: Path, config: dict, bundle_name: str, output_dir: Path
    ) -> list[Path]:
        """Export commands from a bundle."""
        generated: list[Path] = []

        for cmd_ref in config.get('commands', []):
            cmd_path = bundle_dir / cmd_ref.lstrip('./')
            if not cmd_path.exists():
                continue

            content = cmd_path.read_text()
            fm, body = parse_frontmatter(content)

            commands_dir = output_dir / 'commands'
            commands_dir.mkdir(parents=True, exist_ok=True)

            new_fm = transform_command_frontmatter(fm)
            new_body = transform_body(body, bundle_name)
            oc_cmd = commands_dir / cmd_path.name
            oc_cmd.write_text(new_fm + '\n\n' + new_body)
            generated.append(oc_cmd)

        return generated

    def _generate_config(self, config_path: Path, opencode_dir: Path) -> Path:
        """Generate opencode.json project configuration.

        Produces a minimal but valid opencode.json that tells OpenCode
        where to find the generated skills.
        """
        # Compute relative path from config to .opencode dir
        try:
            rel_opencode = opencode_dir.relative_to(config_path.parent)
            skills_path = f'./{rel_opencode}/skills'
        except ValueError:
            skills_path = str(opencode_dir / 'skills')

        config: dict = {
            '$schema': 'https://opencode.ai/config.json',
            'instructions': ['AGENTS.md'],
            'skills': {
                'paths': [skills_path],
            },
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2) + '\n')
        return config_path
