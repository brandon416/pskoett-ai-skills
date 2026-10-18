#!/usr/bin/env python3
"""Sync canonical skills into plugin distributions and managed .agents copies.

skill-distributions.json owns membership and native registration. Generated
outputs are never inputs. Skill-owned assets/claude-hooks.json overrides hooks.
Unlisted .agents skills are local-only and are never changed.

Usage:
    python3 scripts/sync_plugin.py [skill-name ...]
      no args -> sync every configured skill
"""
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "skills"
NATIVE_SKILLS_DIR = ROOT / "plugin" / "skills"
PORTABLE_PLUGIN_DIR = ROOT / "agent-plugin"
PORTABLE_SKILLS_DIR = PORTABLE_PLUGIN_DIR / "skills"
INSTALLED_SKILLS_DIR = ROOT / ".agents" / "skills"
CONFIG = json.loads((ROOT / "scripts" / "skill-distributions.json").read_text())
NATIVE_REGISTRATION = CONFIG["native"]
INSTALLED_SKILLS = set(CONFIG["installed"])

# Frontmatter keys added only to native plugin copies.
PLUGIN_KEYS = ["hooks", "user-invocable", "argument-hint"]
AGENT_SKILL_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
NATIVE_SUBDIRS = ["references", "scripts", "assets"]
PORTABLE_EXCLUDES = {"evals"}
SKILL_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def split_frontmatter(text):
    """Return (frontmatter_dict, body_str). frontmatter_dict is None if absent."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = yaml.safe_load("".join(lines[1:i])) or {}
            body = "".join(lines[i + 1:])
            return fm, body
    return None, text


def build_skill_md(src_md: Path, name: str) -> str:
    src_fm, src_body = split_frontmatter(src_md.read_text())
    if src_fm is None:
        raise SystemExit(f"no frontmatter in {src_md}")

    new_fm = dict(src_fm)
    if isinstance(new_fm.get("description"), str):
        new_fm["description"] = new_fm["description"].strip()
    new_fm.update(NATIVE_REGISTRATION[name])

    # Skills can own their Claude registration without hand-editing generated files.
    hooks_path = src_md.parent / "assets" / "claude-hooks.json"
    if hooks_path.is_file():
        new_fm["hooks"] = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]

    # Stable, readable order: name, description, plugin keys, then anything else.
    ordered = {}
    for key in ["name", "description"]:
        if key in new_fm:
            ordered[key] = new_fm.pop(key)
    for key in PLUGIN_KEYS:
        if key in new_fm:
            ordered[key] = new_fm.pop(key)
    ordered.update(new_fm)

    fm_yaml = yaml.dump(
        ordered, sort_keys=False, allow_unicode=True, width=10 ** 9,
        default_flow_style=False,
    )
    return f"---\n{fm_yaml}---\n{src_body}"


def validate_skill_name(name: str) -> None:
    if len(name) > 64 or not SKILL_NAME_PATTERN.fullmatch(name):
        raise SystemExit(f"invalid skill name: {name}")


def validate_portable_frontmatter(name: str, frontmatter: dict) -> None:
    validate_skill_name(name)
    if not isinstance(frontmatter, dict):
        raise SystemExit(f"skills/{name}/SKILL.md frontmatter must be a mapping")
    unsupported = set(frontmatter) - AGENT_SKILL_KEYS
    if unsupported:
        keys = ", ".join(sorted(unsupported))
        raise SystemExit(
            f"skills/{name}/SKILL.md has non-portable frontmatter keys: {keys}"
        )
    if frontmatter.get("name") != name:
        raise SystemExit(f"skills/{name}/SKILL.md name must match its directory")


def sync_native_skill(name: str, src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for sub in NATIVE_SUBDIRS:
        source_subdir, destination_subdir = src / sub, dst / sub
        if source_subdir.is_dir():
            shutil.copytree(
                source_subdir,
                destination_subdir,
                copy_function=shutil.copy2,
            )
    skill_path = dst / "SKILL.md"
    skill_path.write_text(
        build_skill_md(src / "SKILL.md", name),
        encoding="utf-8",
    )
    shutil.copymode(src / "SKILL.md", skill_path)


def sync_canonical_skill(name: str, src: Path, destination: Path) -> None:
    frontmatter, _ = split_frontmatter((src / "SKILL.md").read_text(encoding="utf-8"))
    if frontmatter is None:
        raise SystemExit(f"no frontmatter in {src / 'SKILL.md'}")
    validate_portable_frontmatter(name, frontmatter)

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    shutil.copy2(src / "SKILL.md", destination / "SKILL.md")

    for entry in src.iterdir():
        if entry.name == "SKILL.md" or entry.name in PORTABLE_EXCLUDES:
            continue
        target = destination / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, copy_function=shutil.copy2)
        elif entry.is_file():
            shutil.copy2(entry, target)


def sync_skill(name: str) -> None:
    validate_skill_name(name)
    src, native = SRC_DIR / name, NATIVE_SKILLS_DIR / name
    if name not in NATIVE_REGISTRATION and name not in INSTALLED_SKILLS:
        raise SystemExit(f"{name} is not configured in skill-distributions.json")
    if not (src / "SKILL.md").is_file():
        raise SystemExit(f"missing canonical skill: {name}")
    if name in NATIVE_REGISTRATION:
        sync_native_skill(name, src, native)
        sync_canonical_skill(name, src, PORTABLE_SKILLS_DIR / name)
    if name in INSTALLED_SKILLS:
        sync_canonical_skill(name, src, INSTALLED_SKILLS_DIR / name)
    print(f"  SYNCED {name}")


def shared_skills():
    return sorted(NATIVE_REGISTRATION)


def remove_stale_skills(directory: Path, expected: set[str]) -> None:
    if not directory.exists():
        return
    for path in directory.iterdir():
        if path.is_dir() and path.name not in expected:
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def main():
    targets = sys.argv[1:] or sorted(set(shared_skills()) | INSTALLED_SKILLS)
    if not sys.argv[1:]:
        for directory in (NATIVE_SKILLS_DIR, PORTABLE_SKILLS_DIR):
            remove_stale_skills(directory, set(shared_skills()))

    print("Syncing skills/ -> plugin distributions and managed .agents copies")
    for name in targets:
        sync_skill(name)

    PORTABLE_PLUGIN_DIR.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "plugin" / "LICENSE", PORTABLE_PLUGIN_DIR / "LICENSE")
    print(f"Done: {len(targets)} skill(s) synced.")


if __name__ == "__main__":
    main()
