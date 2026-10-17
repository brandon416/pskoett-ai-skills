#!/usr/bin/env python3
"""Sync canonical skills into native and portable plugin distributions.

For each skill present in BOTH skills/ and plugin/skills/:
  - rebuild the native plugin copy while preserving client registration fields
  - copy the canonical Agent Skill into the portable Agent Plugins package
  - copy runtime support files while excluding development-only evals

Native plugin membership is the curated allowlist for both generated trees, so
internal skills are not shipped accidentally.

Usage:
    python3 scripts/sync_plugin.py [skill-name ...]
      no args -> sync every skill present in both trees
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

# Frontmatter keys that are plugin-specific (absent from the public source) and
# must be carried over from the existing plugin copy.
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


def build_skill_md(src_md: Path, dst_md: Path) -> str:
    src_fm, src_body = split_frontmatter(src_md.read_text())
    if src_fm is None:
        raise SystemExit(f"no frontmatter in {src_md}")

    dst_fm = {}
    if dst_md.exists():
        dst_fm, _ = split_frontmatter(dst_md.read_text())
        dst_fm = dst_fm or {}

    new_fm = dict(src_fm)
    if isinstance(new_fm.get("description"), str):
        new_fm["description"] = new_fm["description"].strip()
    # Carry over plugin-only registration keys that source does not define.
    for key in PLUGIN_KEYS:
        if key in dst_fm and key not in new_fm:
            new_fm[key] = dst_fm[key]

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
    for sub in NATIVE_SUBDIRS:
        source_subdir, destination_subdir = src / sub, dst / sub
        if destination_subdir.exists():
            shutil.rmtree(destination_subdir)
        if source_subdir.is_dir():
            shutil.copytree(
                source_subdir,
                destination_subdir,
                copy_function=shutil.copy2,
            )
    skill_path = dst / "SKILL.md"
    skill_path.write_text(
        build_skill_md(src / "SKILL.md", skill_path),
        encoding="utf-8",
    )


def sync_portable_skill(name: str, src: Path) -> None:
    frontmatter, _ = split_frontmatter((src / "SKILL.md").read_text(encoding="utf-8"))
    if frontmatter is None:
        raise SystemExit(f"no frontmatter in {src / 'SKILL.md'}")
    validate_portable_frontmatter(name, frontmatter)

    destination = PORTABLE_SKILLS_DIR / name
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
    if not src.is_dir() or not native.is_dir():
        raise SystemExit(f"{name} is not present in both skill trees")
    sync_native_skill(name, src, native)
    sync_portable_skill(name, src)
    print(f"  SYNCED {name}")


def shared_skills():
    return sorted(
        p.name for p in SRC_DIR.iterdir()
        if p.is_dir() and (NATIVE_SKILLS_DIR / p.name).is_dir()
    )


def remove_stale_portable_skills(expected: set[str]) -> None:
    if not PORTABLE_SKILLS_DIR.exists():
        return
    for path in PORTABLE_SKILLS_DIR.iterdir():
        if path.is_dir() and path.name not in expected:
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def main():
    targets = sys.argv[1:] or shared_skills()
    if not sys.argv[1:]:
        remove_stale_portable_skills(set(targets))

    print("Syncing skills/ -> native and portable plugin distributions")
    for name in targets:
        sync_skill(name)

    PORTABLE_PLUGIN_DIR.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "plugin" / "LICENSE", PORTABLE_PLUGIN_DIR / "LICENSE")
    print(f"Done: {len(targets)} skill(s) synced.")


if __name__ == "__main__":
    main()
