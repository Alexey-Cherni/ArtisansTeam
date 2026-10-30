#!/usr/bin/env python3
"""Install the Artisans team into a project, for Claude Code and/or GitHub Copilot.

    python3 install.py claude  <project-dir> [options]
    python3 install.py copilot <project-dir> [options]
    python3 install.py both    <project-dir> [options]
    python3 install.py check                   # self-test of this repository

Options:
    --profile NAME   model profile written as the default (and, for Copilot, into the agent files)
    --dry-run        show what would change, write nothing
    --force          replace team files you edited by hand (they are backed up first)
    --reset-config   replace an existing installed config.json (backed up first)
    --no-hooks       do not wire the guard hook
    --yes            answer yes to every question (non-interactive)

Layout written into the project:
    Claude Code  .claude/agents/artisans-*.md, .claude/skills/artisans/**, guard hook in .claude/settings.json
    Copilot      .github/agents/artisans-*.agent.md, .github/skills/artisans/**, .github/hooks/artisans.json

The installed config.json is never overwritten unless --reset-config is given: it holds your
project's settings. Files are tracked in <skill dir>/.installed.json so a re-install can tell
files you edited (refused without --force) from files it wrote (updated in place).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_SRC = ROOT / "skills"
SKILL_SRC = SKILLS_SRC / "artisans"          # the orchestrator: owns config.json, hooks, templates
AGENTS_SRC = ROOT / "agents"
CONFIG_SRC = SKILL_SRC / "config.json"

# Claude Code tool name -> GitHub Copilot tool alias (understood by VS Code and the Copilot CLI).
COPILOT_TOOL_ALIASES = {
    "Read": "read", "Grep": "search", "Glob": "search",
    "Write": "edit", "Edit": "edit", "NotebookEdit": "edit",
    "Bash": "execute", "WebSearch": "web", "WebFetch": "web",
    "Agent": "agent", "Task": "agent", "TodoWrite": "todo",
}

HOSTS = {
    "claude": {"agents": ".claude/agents", "agent_ext": ".md", "skills": ".claude/skills"},
    "copilot": {"agents": ".github/agents", "agent_ext": ".agent.md", "skills": ".github/skills"},
}


# --- helpers -----------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def content_hash(rel, data):
    """Hash used to detect hand edits. A Copilot agent's model: line is ignored: the
    orchestrator may change it after the user approves another model."""
    if rel.endswith(".agent.md"):
        data = re.sub(rb"(?m)^model:.*\n", b"", data)
    return sha(data)


def split_frontmatter(text):
    """Return (list of frontmatter lines, body) or raise ValueError."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("no frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter not closed")
    return text[4:end].split("\n"), text[end + 5:]


def frontmatter_dict(lines):
    out = {}
    for line in lines:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def copilot_tool(name):
    if name in COPILOT_TOOL_ALIASES:
        return COPILOT_TOOL_ALIASES[name]
    m = re.match(r"^mcp__([^_]+(?:_[^_]+)*)__(.+)$", name)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    m = re.match(r"^mcp__(.+)$", name)
    if m:
        return f"{m.group(1)}/*"
    raise ValueError(f"tool '{name}' has no Copilot alias; add it to COPILOT_TOOL_ALIASES in install.py")


def to_copilot_agent(text, model):
    """Rewrite a Claude Code agent file for Copilot: tool aliases, model name, hidden from the picker."""
    lines, body = split_frontmatter(text)
    out, seen_tools = [], False
    for line in lines:
        if line.startswith("tools:"):
            tools = []
            for t in line[len("tools:"):].split(","):
                t = t.strip()
                if t:
                    a = copilot_tool(t)
                    if a not in tools:
                        tools.append(a)
            out.append("tools: [" + ", ".join(f"'{t}'" for t in tools) + "]")
            seen_tools = True
        elif line.startswith("model:"):
            continue
        else:
            out.append(line)
    if not seen_tools:
        raise ValueError("no tools: line")
    if model and model != "inherit":
        out.append(f"model: '{model}'")
    out.append("user-invocable: false")
    return "---\n" + "\n".join(out) + "\n---\n" + body


def merge_missing(dst, src, prefix=""):
    """Add keys that exist in src but not in dst, recursively. Never changes an existing value.
    Returns the dotted names of the keys added."""
    added = []
    for k, v in src.items():
        if k.startswith("_"):
            continue
        if k not in dst:
            dst[k] = v
            added.append(prefix + k)
        elif isinstance(v, dict) and isinstance(dst[k], dict):
            added += merge_missing(dst[k], v, f"{prefix}{k}.")
    return added


def find_bash():
    """Locate a working bash for the guard hook. Returns (status, path, advice):
    ok | not-on-path (Git Bash installed, PATH lacks it) | wsl (only the WSL launcher) | missing."""
    def works(path):
        try:
            r = subprocess.run([path, "-c", "echo ok"], capture_output=True, text=True, timeout=10)
            return r.stdout.strip() == "ok"
        except (OSError, subprocess.SubprocessError):
            return False

    windows = os.name == "nt"
    git_install = "Install Git for Windows (it includes Git Bash): https://git-scm.com/download/win or `winget install --id Git.Git -e`, then reopen your terminal and editor."
    found = shutil.which("bash")
    wsl_launcher = bool(found) and windows and "system32" in found.lower()
    if found and not wsl_launcher and works(found):
        return "ok", found, ""

    if windows:
        candidates = [
            Path(os.environ.get(var, "")) / sub / "bin" / "bash.exe"
            for var, sub in (("ProgramFiles", "Git"), ("ProgramFiles(x86)", "Git"), ("LocalAppData", "Programs/Git"))
            if os.environ.get(var)
        ]
        for c in candidates:
            if c.is_file() and works(str(c)):
                return ("not-on-path", str(c),
                        f"Git Bash is installed but not on PATH. Add {c.parent} to your PATH "
                        "(Settings > System > About > Advanced system settings > Environment Variables), "
                        "then reopen your terminal and editor.")
        if wsl_launcher:
            return ("wsl", found,
                    "Only the WSL bash launcher was found; the hook would run inside WSL, outside your Windows "
                    "project. " + git_install)
        return "missing", "", git_install
    return "missing", "", "Install bash with your package manager (e.g. `apt install bash`, `brew install bash`)."


def ask(question, assume_yes):
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(f"  {question} -> no (not interactive; pass --yes to accept)")
        return False
    return input(f"  {question} [y/N] ").strip().lower() in ("y", "yes")


# --- build the file set for one host -----------------------------------------

def build(host, config, profile):
    """Return {relative target path: bytes} for the host, config.json excluded."""
    h = HOSTS[host]
    files = {}
    for p in sorted(SKILLS_SRC.rglob("*")):
        if not p.is_file() or p.name in (".installed.json", ".DS_Store"):
            continue
        rel = p.relative_to(SKILLS_SRC).as_posix()
        if rel == "artisans/config.json":
            continue  # handled separately: never overwritten
        if rel.startswith("artisans/hooks/") and p.suffix == ".json":
            continue  # wiring snippets are applied, not installed
        files[f"{h['skills']}/{rel}"] = p.read_bytes()
    models = config["models"].get(host, {}).get("profiles", {}).get(profile, {})
    for key, agent in config["agents"].items():
        src = AGENTS_SRC / f"{agent['file']}.md"
        text = src.read_text(encoding="utf-8")
        if host == "copilot":
            text = to_copilot_agent(text, models.get(key))
        files[f"{h['agents']}/{agent['file']}{h['agent_ext']}"] = text.replace("\r\n", "\n").encode("utf-8")
    if host == "copilot":
        files[".github/hooks/artisans.json"] = (SKILL_SRC / "hooks" / "copilot-hooks.json").read_bytes()
    return files


# --- install -------------------------------------------------------------------

def install(host, project, args):
    h = HOSTS[host]
    skill_dir = project / h["skills"] / "artisans"
    record_path = skill_dir / ".installed.json"
    record = load_json(record_path) if record_path.exists() else {}

    installed_cfg = skill_dir / "config.json"
    keep_cfg = installed_cfg.exists() and not args.reset_config
    config = load_json(installed_cfg) if keep_cfg else load_json(CONFIG_SRC)
    profile = args.profile or config["models"]["defaultProfile"]
    if profile not in config["models"].get(host, {}).get("profiles", {}):
        sys.exit(f"install: profile '{profile}' is not defined in models.{host}.profiles")
    if not config.get("guard", {}).get("enabled", True):
        args.no_hooks = True

    files = build(host, config, profile)
    if host == "copilot" and args.no_hooks:
        files.pop(".github/hooks/artisans.json", None)

    plan = []  # (status, rel)
    for rel, data in files.items():
        cur = project / rel
        if not cur.exists():
            plan.append(("add", rel))
            continue
        cur_hash = content_hash(rel, cur.read_bytes())
        if cur.read_bytes() == data:
            plan.append(("unchanged", rel))
        elif record.get(rel) == cur_hash:
            plan.append(("update", rel))
        elif rel in record:
            plan.append(("modified", rel))
        else:
            plan.append(("conflict", rel))
    for rel in record:
        if rel not in files and (project / rel).exists():
            plan.append(("remove", rel))

    cfg_action = "keep" if keep_cfg else ("reset" if installed_cfg.exists() else "add")

    print(f"Artisans {config.get('version', '?')} for {host} -> {project}  (profile: {profile})")
    for st, rel in plan:
        if st != "unchanged":
            print(f"  {st:9} {rel}")
    print(f"  config    {h['skills']}/artisans/config.json ({cfg_action})")

    blocked = [r for s, r in plan if s == "conflict"]
    if blocked and not args.force:
        print("install: refused - these paths hold files Artisans did not install. Rename them, or re-run with --force (they are backed up):")
        for r in blocked:
            print(f"  {r}")
        return 1
    edited = [r for s, r in plan if s == "modified"]
    if edited and not args.force:
        print("install: refused - these Artisans files were edited by hand. Re-run with --force to back them up and replace them:")
        for r in edited:
            print(f"  {r}")
        return 1

    if args.dry_run:
        print("install: dry run, nothing written")
        if host == "claude" and not args.no_hooks:
            print("  (would also wire the guard hook into .claude/settings.json)")
        return 0

    tracking = config.get("trackingDir", ".artisans")
    backup = project / tracking / f"install-backup-{time.strftime('%Y%m%d-%H%M%S')}"

    def back_up(rel):
        dst = backup / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project / rel, dst)

    new_record = {}
    for st, rel in plan:
        if st in ("modified", "conflict"):
            back_up(rel)
        if st in ("add", "update", "modified", "conflict"):
            dst = project / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(files[rel])
            if rel.endswith("/guard-command"):
                dst.chmod(0o755)
        if st == "remove":
            if record.get(rel) == content_hash(rel, (project / rel).read_bytes()):
                (project / rel).unlink()
            else:
                print(f"  kept (edited, no longer shipped): {rel}")
            continue
        new_record[rel] = content_hash(rel, files[rel])

    if cfg_action != "keep":
        if cfg_action == "reset":
            back_up(f"{h['skills']}/artisans/config.json")
        cfg = load_json(CONFIG_SRC)
        cfg["models"]["defaultProfile"] = profile
        installed_cfg.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        added = merge_missing(config, load_json(CONFIG_SRC))
        if added:
            back_up(f"{h['skills']}/artisans/config.json")
            installed_cfg.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"  config    kept your values; added new keys: {', '.join(added)}")
        if args.profile and config["models"]["defaultProfile"] != profile:
            print(f"  note: kept your config.json; its defaultProfile is still '{config['models']['defaultProfile']}'")

    record_path.write_text(json.dumps(new_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if host == "claude" and not args.no_hooks:
        wire_claude_hook(project, args.yes)

    if backup.exists():
        print(f"  backups: {backup.relative_to(project)}")
    print("install: done")
    return 0


def wire_claude_hook(project, assume_yes):
    settings = project / ".claude" / "settings.json"
    snippet = load_json(SKILL_SRC / "hooks" / "claude-settings-snippet.json")
    entry = snippet["hooks"]["PreToolUse"][0]
    if not settings.exists():
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(snippet, indent=2) + "\n", encoding="utf-8")
        print("  hook      created .claude/settings.json with the Artisans guard")
        return
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("  hook      .claude/settings.json is not valid JSON; merge this entry into hooks.PreToolUse by hand:")
        print(json.dumps(entry, indent=2))
        return
    pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if any("artisans/hooks/guard-command" in hk.get("command", "")
           for e in pre for hk in e.get("hooks", [])):
        print("  hook      guard already wired in .claude/settings.json")
        return
    if not ask("Add the Artisans guard hook to .claude/settings.json (a backup is kept)?", assume_yes):
        print("  hook      skipped; the snippet is in .claude/skills/artisans/hooks/claude-settings-snippet.json")
        return
    shutil.copy2(settings, settings.with_name("settings.json.artisans-backup"))
    pre.append(entry)
    settings.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("  hook      guard added to .claude/settings.json (backup: settings.json.artisans-backup)")


# --- self-test -----------------------------------------------------------------

def check():
    errors = []
    err = errors.append

    try:
        config = load_json(CONFIG_SRC)
    except Exception as e:  # noqa: BLE001
        print(f"check: config.json: {e}")
        return 1

    keys = list(config.get("agents", {}))
    if not keys:
        err("config.json: no agents")
    for key, agent in config.get("agents", {}).items():
        src = AGENTS_SRC / f"{agent.get('file', '')}.md"
        if not src.exists():
            err(f"agents.{key}: missing {src.relative_to(ROOT)}")
            continue
        try:
            lines, body = split_frontmatter(src.read_text(encoding="utf-8"))
        except ValueError as e:
            err(f"{src.name}: {e}")
            continue
        fm = frontmatter_dict(lines)
        if fm.get("name") != agent["file"]:
            err(f"{src.name}: name '{fm.get('name')}' != file name '{agent['file']}'")
        for k in ("description", "tools"):
            if not fm.get(k):
                err(f"{src.name}: no {k}")
        for t in fm.get("tools", "").split(","):
            if t.strip():
                try:
                    copilot_tool(t.strip())
                except ValueError as e:
                    err(f"{src.name}: {e}")
        if "## Result" not in body or "Needs from user:" not in body:
            err(f"{src.name}: no return block with 'Needs from user:'")
    for f in sorted(AGENTS_SRC.glob("*.md")):
        if f.stem not in [a["file"] for a in config["agents"].values()]:
            err(f"{f.name}: not listed in config.json agents")

    models = config.get("models", {})
    default = models.get("defaultProfile")
    for host in ("claude", "copilot"):
        profiles = models.get(host, {}).get("profiles", {})
        if default not in profiles:
            err(f"models.{host}: defaultProfile '{default}' not defined")
        for name, mapping in profiles.items():
            missing = [k for k in keys if k not in mapping]
            if missing:
                err(f"models.{host}.profiles.{name}: no model for {missing}")
            if host == "claude":
                bad = [v for v in mapping.values() if v not in models["claude"].get("allowed", [])]
                if bad:
                    err(f"models.claude.profiles.{name}: not in allowed: {bad}")

    for d in sorted(x for x in SKILLS_SRC.iterdir() if x.is_dir()):
        skill = d / "SKILL.md"
        if not skill.exists():
            err(f"skills/{d.name}: no SKILL.md")
            continue
        try:
            fm = frontmatter_dict(split_frontmatter(skill.read_text(encoding="utf-8"))[0])
            if fm.get("name") != d.name:
                err(f"skills/{d.name}/SKILL.md: name '{fm.get('name')}' != folder name")
            if not fm.get("description"):
                err(f"skills/{d.name}/SKILL.md: no description")
        except ValueError as e:
            err(f"skills/{d.name}/SKILL.md: {e}")
    for name in ("artisans", "artisans-knowledge", "artisans-setup"):
        if not (SKILLS_SRC / name / "SKILL.md").exists():
            err(f"missing skill {name}")

    know = config.get("knowledge", {})
    if not know.get("files"):
        err("config.json: knowledge.files is empty")
    if know.get("requireBeforeRun") not in ("ask", "always", "never"):
        err("config.json: knowledge.requireBeforeRun must be ask, always or never")
    cards = SKILLS_SRC / "artisans-knowledge" / "standards"
    if not (cards / "_generic.md").exists():
        err("artisans-knowledge/standards: no _generic.md")
    for card in sorted(cards.glob("*.md")):
        text = card.read_text(encoding="utf-8")
        for section in ("## Detect", "## Toolchain", "## Review checks"):
            if section not in text:
                err(f"standards/{card.name}: no '{section}' section")
    for t in ("templates/status.md", "templates/handoff.md", "templates/report.html", "hooks/guard-command"):
        if not (SKILL_SRC / t).exists():
            err(f"missing skills/artisans/{t}")
            continue
        if t.endswith(".html"):
            html = (SKILL_SRC / t).read_text(encoding="utf-8")
            m = re.search(r'<script type="application/json" id="run-data">(.*?)</script>', html, re.S)
            if not m:
                err("report.html: no run-data block")
            else:
                try:
                    json.loads(m.group(1))
                except json.JSONDecodeError as e:
                    err(f"report.html: run-data is not valid JSON: {e}")
    for j in ("hooks/claude-settings-snippet.json", "hooks/copilot-hooks.json"):
        try:
            load_json(SKILL_SRC / j)
        except Exception as e:  # noqa: BLE001
            err(f"{j}: {e}")

    # Build both editions into a temporary project and inspect them.
    with tempfile.TemporaryDirectory() as tmp:
        for host in ("claude", "copilot"):
            try:
                files = build(host, config, default)
            except Exception as e:  # noqa: BLE001
                err(f"build {host}: {e}")
                continue
            for rel, data in files.items():
                if rel.endswith(".agent.md"):
                    fm = frontmatter_dict(split_frontmatter(data.decode())[0])
                    if not fm.get("tools", "").startswith("["):
                        err(f"{rel}: tools not translated")
                    if fm.get("user-invocable") != "false":
                        err(f"{rel}: not hidden from the agent picker")
                    if "model" not in fm:
                        err(f"{rel}: no model line")

        errors.extend(check_guard(Path(tmp)))

    for e in errors:
        print(f"check: {e}")
    print("check: ok" if not errors else f"check: {len(errors)} problem(s)")
    return 1 if errors else 0


def check_guard(tmp):
    bash = shutil.which("bash")
    if not bash:
        print("check: bash not found; guard hook not tested")
        return []
    guard = SKILL_SRC / "hooks" / "guard-command"
    out = []
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp))
    cases = [
        ("git push --force origin main", True),
        ("rm -rf /", True),
        ("pkill node", True),
        ("git reset --hard HEAD~1", True),
        ("git clean -fd", True),
        ("git status --porcelain", False),
        ("npm test", False),
        ("rm -rf build/tmp", False),
    ]

    def run(command):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        r = subprocess.run([bash, str(guard)], input=payload, capture_output=True, text=True, env=env, timeout=20)
        return '"deny"' in r.stdout

    for command, _ in cases[:1]:
        if run(command):
            out.append("guard: denies without an active run")
    (tmp / ".artisans").mkdir(exist_ok=True)
    (tmp / ".artisans" / "active").write_text("test-run\n")
    for command, deny in cases:
        if run(command) != deny:
            out.append(f"guard: '{command}' should be {'denied' if deny else 'allowed'}")
    # A command written verbatim as a TOOLCHAIN.md Command cell is exempt.
    (tmp / ".artisans" / "knowledge").mkdir(exist_ok=True)
    (tmp / ".artisans" / "knowledge" / "TOOLCHAIN.md").write_text(
        "| Purpose | Command |\n|---|---|\n| Clean | `git clean -fdx build/` |\n")
    if run("git clean -fdx build/"):
        out.append("guard: a TOOLCHAIN.md command should be exempt")
    if not run("git clean -fdx"):
        out.append("guard: the TOOLCHAIN exemption must be an exact match, not a prefix")
    return out


# --- main ------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Install the Artisans team into a project.")
    ap.add_argument("target", choices=["claude", "copilot", "both", "check"])
    ap.add_argument("project", nargs="?")
    ap.add_argument("--profile")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--reset-config", action="store_true")
    ap.add_argument("--no-hooks", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    if args.target == "check":
        return check()
    if not args.project:
        ap.error("project directory is required")
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        ap.error(f"{project} is not a directory")
    if project == ROOT:
        ap.error("install into a project, not into the Artisans repository itself")

    rc = 0
    for host in (["claude", "copilot"] if args.target == "both" else [args.target]):
        rc |= install(host, project, argparse.Namespace(**vars(args)))

    bash_status, bash_path, bash_advice = ("skipped", "", "") if args.no_hooks else find_bash()
    if bash_status == "ok":
        print(f"\nbash: {bash_path} (the guard hook can run)")
    elif bash_status != "skipped":
        print(f"\nWARNING bash: {bash_status}{' (' + bash_path + ')' if bash_path else ''}.")
        print("  The guard hook needs bash; without it the hook does nothing and destructive commands are not blocked.")
        print("  The rest of the team works normally.")
        print(f"  Fix: {bash_advice}")

    if rc == 0 and not args.dry_run:
        steps = ["Restart Claude Code / reload VS Code (or restart the Copilot CLI) so the agents and /artisans load."]
        if bash_status not in ("ok", "skipped"):
            steps.insert(0, f"Make bash available for the guard hook: {bash_advice}")
        if args.target in ("copilot", "both"):
            steps.append("Copilot: check the model names in .github/agents/artisans-*.agent.md against your model picker.")
            steps.append("VS Code: enable the chat.useHooks setting so the guard hook runs (preview feature).")
        steps.append("In the project, run: /artisans <your task>")
        print("\nNext:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
