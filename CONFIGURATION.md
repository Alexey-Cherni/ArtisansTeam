# Configuration

## Where the settings live

| File | Scope |
|------|-------|
| `skills/artisans/config.json` in this repository | Defaults for new installs |
| `.claude/skills/artisans/config.json` in a project | That project, Claude Code |
| `.github/skills/artisans/config.json` in a project | That project, Copilot |

The orchestrator reads the project copy at the start of every `/artisans` command, so edits apply to the next command. The installer never overwrites a project copy unless you pass `--reset-config`, which backs it up first. Keys that start with `_` are comments.

After editing the repository copy, run `python3 install.py check`.

---

## `trackingDir`

Default: `".artisans"`.

Where run state is written: runs, the active-run marker, install backups, and the knowledge base (`{trackingDir}/knowledge/`). The guard hook reads this value too.

Suggested git setup:

- Ignore `runs/`, `active` and `*-backup-*/`. Both `/artisans` and `/artisans-setup fix` offer to do this.
- Commit `knowledge/` so everyone on the project gets the same knowledge.

## `knowledge`

| Key | Default | Meaning |
|-----|---------|---------|
| `files` | the 6 files | Files `/artisans-knowledge` writes, and that `/artisans` and `/artisans-setup` check for. If you remove one here, also remove the matching "Read first" line from the agents that read it. |
| `maxLinesPerFile` | `200` | Size limit for each generated file. Agents read these files on every call, so smaller files are cheaper. |
| `staleAfterCommits` | `50` | A file whose banner commit is more than this many commits behind HEAD is reported as stale. |
| `requireBeforeRun` | `"ask"` | What `/artisans` does when knowledge is missing. `ask`: offer to stop so you can run `/artisans-knowledge` first. `always`: refuse to run without it. `never`: run without asking; agents explore the repository instead. |
| `learnings` | `true` | Append the Reviewer's, QA's and Security's `Learning:` lines to `LEARNINGS.md` when a run closes. |
| `learningsMaxEntries` | `30` | Above this many inbox entries, `/artisans` and `/artisans-setup` remind you to run `/artisans-knowledge all`. |

The knowledge files are plain Markdown. You can edit them by hand: an edit holds until the next regeneration of that file, and the old version is backed up before each regeneration.

## `agents`

One entry per role. The key (`researcher`, `developer`, …) is the role id used in the model profiles.

| Field | Meaning |
|-------|---------|
| `file` | Agent file name without its extension (`artisans-qa` → `.claude/agents/artisans-qa.md` / `.github/agents/artisans-qa.agent.md`). This is also the subagent name the orchestrator calls. |
| `label` | Name shown to you in gates and in the report. |
| `phase` | `analysis` (before the plan gate) or `delivery` (after it). Decides which kickoff question the role appears in. |
| `enabledByDefault` | Whether the role is pre-selected at the kickoff gate. You can still change it in the dialog. |

## `models`

### `models.defaultProfile`

Default: `"balanced"`.

The profile offered first, marked *Recommended*, at the kickoff gate. `install.py --profile NAME` sets it when it writes a fresh config.

### `models.claude` (Claude Code)

| Field | Meaning |
|-------|---------|
| `allowed` | Values accepted in a profile or a custom mapping you type at the gate: `haiku`, `sonnet`, `opus`, `fable`, `inherit`. |
| `profiles.{name}.{role}` | The model for each role in that profile. |

The value is passed as the `model` parameter of each subagent call. These are aliases, so they always resolve to the newest model of that family.

`inherit` passes no model. The agent file's own `model:` line then decides: `model: inherit` there means the session model.

**To pin an exact version**, for example `claude-opus-5-5`, put it in the agent file's frontmatter (`.claude/agents/artisans-architect.md` → `model: claude-opus-5-5`) and set that role to `inherit` in the profile.

### `models.copilot` (GitHub Copilot)

| Field | Meaning |
|-------|---------|
| `profiles.{name}.{role}` | The model name exactly as the Copilot model picker shows it, e.g. `Claude Sonnet 5.5 (copilot)` or `GPT-5 (copilot)`. Which models you can use depends on your Copilot plan. |

Copilot runs a subagent on the `model:` line of its agent file. `install.py` writes those lines from the chosen profile. During a run, if you approve a model that differs from the file, the orchestrator asks before editing the `model:` line. VS Code may need *Developer: Reload Window* before the change applies.

To apply a different profile to the files directly:

```bash
python3 install.py copilot /path/to/project --profile max
```

Edits to `model:` lines never count as hand edits, so upgrades are not blocked by them.

### Adding a profile

Add the same profile name under both `models.claude.profiles` and `models.copilot.profiles`, with a model for **every** role. It then appears as an option at the kickoff gate. The question dialog shows at most 4 options, so keep to 4 profiles or fewer.

```json
"fast": { "researcher": "haiku", "architect": "sonnet", "developer": "sonnet", "reviewer": "sonnet", "qa": "haiku", "security": "sonnet" }
```

### When new model versions come out

- **Claude Code:** nothing to do. The aliases follow the newest model. To pin a version, see above.
- **Copilot:** update the names in `models.copilot.profiles`, then re-run `install.py copilot … --profile <name>`, or approve the new name at a gate.

## `flow`

| Key | Default | Meaning |
|-----|---------|---------|
| `architect` | `"auto"` | `auto`: the Architect runs when the research shows a new module or API, a cross-module change, data or migration work, competing designs, or the Researcher recommends it. `always`: it runs every time it is selected. `never`: it never runs. It also has to be selected at the kickoff gate. |
| `maxRounds.codeReview` | `3` | Developer ↔ Code Reviewer rounds before you are asked. |
| `maxRounds.testReview` | `2` | QA ↔ Code Reviewer (tests) rounds. |
| `maxRounds.qa` | `2` | Times QA may send a production bug back to the Developer. |
| `maxRounds.security` | `2` | Security → Developer → … → Security rounds. |
| `securityBlocksOn` | `["critical","high"]` | Security severities that block the run. Lower findings are shown to you at the end, and you decide whether to fix, accept or defer each one. Add `"medium"` to be stricter. |
| `branch.protected` | `["main","master","develop"]` | Branches on which the orchestrator stops at preflight and asks you to switch or create a branch. Use `[]` to never ask. |
| `branch.suggestedPrefix` | `"artisans/"` | Prefix of the branch name it suggests (`artisans/{slug}`). |
| `commit` | `"ask"` | `ask`: at the end, offer the Developer's commit units as small ordered commits (or one squashed commit), showing the messages first. `never`: don't offer. The team never pushes. |

When a cap is reached, you are asked: one more round, accept as is (the findings are recorded as open), or stop.

## `report`

| Key | Default | Meaning |
|-----|---------|---------|
| `file` | `"report.html"` | Report file name inside the run folder. |
| `autoOpen` | `false` | Open the report in your browser when the run closes (`open`, `xdg-open` or `start`). |
| `language` | `"auto"` | `auto` = the language of your task. Any other value, e.g. `"en"`, forces that language. |

The report's look is set in `skills/artisans/templates/report.html`. The orchestrator replaces only the JSON data block, so you can restyle the CSS or change the renderer freely. Keep the data keys, or update the orchestrator's Phase 10 to match.

## `guard`

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | `true` | `false` makes the installer skip wiring the hook (same as `--no-hooks`). To turn off an existing install, remove the hook entry from `.claude/settings.json` or delete `.github/hooks/artisans.json`. |

The deny rules are in `skills/artisans/hooks/guard-command`. They apply only while `{trackingDir}/active` exists.

---

## Beyond config.json

### Quality tools for the Developer (ub-mode)

The Developer runs a CRAP-score, duplication or mutation tool only if `TOOLCHAIN.md` has a `Crap`, `Duplication` or `Mutation` row. `/artisans-knowledge` writes those rows only when such a tool is already in the project or on your machine. To enable one:

1. Install the tool yourself.
2. Run `/artisans-knowledge TOOLCHAIN.md`, or add the row by hand: `| Crap | <command> | <how to limit to files> | cheap | yes <date> |`.

The thresholds (CRAP under 10, duplication ranked 0.8 or above) are set in `agents/artisans-developer.md → Quality tools`.

### Editing a role's behaviour

Each role is a Markdown prompt in `agents/artisans-*.md`, and the orchestrator is in `skills/artisans/SKILL.md`. Edit them in this repository and re-install. A project copy that you edited is protected: the installer refuses to overwrite it without `--force`, and with `--force` it backs it up first.

Keep each agent's `## Result` return block and its `Needs from user:` line. The orchestrator relies on both.

### Tools per role

The `tools:` line in each agent's frontmatter, in Claude Code names. For Copilot, `install.py` translates them through `COPILOT_TOOL_ALIASES`:

| Claude Code | Copilot |
|-------------|---------|
| Read | read |
| Grep, Glob | search |
| Write, Edit | edit |
| Bash | execute |
| WebSearch, WebFetch | web |
| Agent | agent |

**Giving a role an MCP server**, for example a database or Jira: add `mcp__<server>` (all of its tools) or `mcp__<server>__<tool>` to the role's `tools:` line. The installer turns these into `<server>/*` and `<server>/<tool>` for Copilot. Connecting the server itself is your step: `claude mcp add …`, or the MCP settings in VS Code. The orchestrator asks you to do it when a task needs it.

### Adding a role

1. Write `agents/artisans-<name>.md` with the frontmatter (`name`, `description`, `tools`, `model: inherit`) and a `## Result` return block.
2. Add it to `agents` in `config.json`, and add a model for it to **every** profile under both hosts.
3. Describe in `skills/artisans/SKILL.md` where it sits in the pipeline.
4. Run `python3 install.py check`, then re-install.

The kickoff question lists at most 4 agents per phase. A fifth delivery role would need its own question in Phase 1 of `SKILL.md`.

### Stack cards

`skills/artisans-knowledge/standards/*.md` (copied from the example team) teach the generator each stack. Every card has the same sections:

- `## Detect`
- `## Toolchain`
- `## Layout`
- `## Naming`
- `## Errors`
- `## Concurrency`
- `## Testing`
- `## Dependencies`
- `## Security`
- `## Anti-patterns`
- `## Review checks`
- `## Sources`

- **To support a new stack** (Rust, Java, Kotlin, …), copy `_generic.md` to `rust.md`, fill in each section, and re-install. The self-test requires `## Detect`, `## Toolchain` and `## Review checks`.
- **To change the rules for a stack,** edit its card, then run `/artisans-knowledge` in the project.
- **For projects with a UI,** `interface.md` adds the usability heuristics (H1–H12), the six view states, and UI review checks.

Card rules are never applied blindly. The generator marks each one `[observed]` or `[not followed]` against your code, and your code wins.

### Templates

| File | Used for |
|------|----------|
| `templates/status.md` | Each run's status file: its phases, team table and logs. |
| `templates/handoff.md` | The envelope at the top of every subagent prompt. |
| `templates/report.html` | The final report. |
