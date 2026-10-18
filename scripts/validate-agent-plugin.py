#!/usr/bin/env python3
"""Validate the generated Agent Plugins 1.0 portable package."""

import hashlib
import json
import re
import stat
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:
    raise SystemExit(
        "jsonschema is required; run with: "
        "uv run --with jsonschema --with pyyaml "
        "python3 scripts/validate-agent-plugin.py"
    ) from exc

from sync_plugin import (
    AGENT_SKILL_KEYS,
    INSTALLED_SKILLS,
    INSTALLED_SKILLS_DIR,
    NATIVE_SKILLS_DIR,
    NATIVE_SUBDIRS,
    PORTABLE_EXCLUDES,
    PORTABLE_PLUGIN_DIR,
    PORTABLE_SKILLS_DIR,
    ROOT,
    SRC_DIR,
    build_skill_md,
    shared_skills,
    split_frontmatter,
)

SCHEMA_DIR = ROOT / "schemas" / "agent-plugins" / "1.0.0"
PLUGIN_SCHEMA = SCHEMA_DIR / "plugin.schema.json"
MCP_SCHEMA = SCHEMA_DIR / "mcp.schema.json"
ALLOWED_PORTABLE_ROOT_ENTRIES = {"plugin.json", "LICENSE", "skills", "mcp.json"}
OFFICIAL_SCHEMA_HASHES = {
    "plugin.schema.json": "67c18151e76b99bf2bfc422092435f1fbcd0fb17438b00d4051fdfd93f6c954e",
    "mcp.schema.json": "1f21ce7c09c5e215d0d53207827feadba2785837116a018524f9990df0a2102c",
}
VERSION_PATHS = {
    "portable Agent Plugins manifest": (
        PORTABLE_PLUGIN_DIR / "plugin.json",
        ("version",),
    ),
    "Claude Code plugin manifest": (
        ROOT / "plugin" / ".claude-plugin" / "plugin.json",
        ("version",),
    ),
    "Codex plugin manifest": (
        ROOT / "plugin" / ".codex-plugin" / "plugin.json",
        ("version",),
    ),
    "GitHub Copilot plugin manifest": (
        ROOT / "plugin" / ".copilot-plugin" / "plugin.json",
        ("version",),
    ),
    "Claude marketplace metadata": (
        ROOT / ".claude-plugin" / "marketplace.json",
        ("metadata", "version"),
    ),
    "Claude marketplace plugin": (
        ROOT / ".claude-plugin" / "marketplace.json",
        ("plugins", 0, "version"),
    ),
    "GitHub Copilot marketplace metadata": (
        ROOT / ".github" / "plugin" / "marketplace.json",
        ("metadata", "version"),
    ),
    "GitHub Copilot marketplace plugin": (
        ROOT / ".github" / "plugin" / "marketplace.json",
        ("plugins", 0, "version"),
    ),
}


class ValidationError(Exception):
    pass


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON in {path.relative_to(ROOT)}: {exc}"
        ) from exc


def load_official_schema(schema_path: Path) -> dict:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    canonical = json.dumps(
        schema,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    actual_hash = hashlib.sha256(canonical).hexdigest()
    expected_hash = OFFICIAL_SCHEMA_HASHES[schema_path.name]
    if actual_hash != expected_hash:
        raise ValidationError(
            f"{schema_path.relative_to(ROOT)} differs from the published schema"
        )
    return schema


def validate_schema(document_path: Path, schema_path: Path) -> dict:
    document = load_json(document_path)
    schema = load_official_schema(schema_path)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValidationError(
            f"{document_path.relative_to(ROOT)} fails "
            f"{schema_path.relative_to(ROOT)}: {details}"
        )
    return document


def assert_contained_tree(root: Path) -> None:
    resolved_root = root.resolve(strict=True)
    for path in root.rglob("*"):
        try:
            path.resolve(strict=True).relative_to(resolved_root)
        except (FileNotFoundError, ValueError) as exc:
            raise ValidationError(
                f"portable path escapes or is unresolved: {path.relative_to(ROOT)}"
            ) from exc


def files_under(root: Path):
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if path.is_file()
    }


def expected_portable_files(source: Path):
    return {
        relative: path
        for relative, path in files_under(source).items()
        if relative.parts[0] not in PORTABLE_EXCLUDES
    }


def validate_portable_skill(name: str, skills_dir: Path = PORTABLE_SKILLS_DIR) -> int:
    """Check canonical runtime files, including managed .agents installations."""
    source = SRC_DIR / name
    generated = skills_dir / name
    expected = expected_portable_files(source)
    actual = files_under(generated)

    if set(actual) != set(expected):
        missing = sorted(str(path) for path in set(expected) - set(actual))
        extra = sorted(str(path) for path in set(actual) - set(expected))
        raise ValidationError(
            f"{generated} file drift; missing={missing}, extra={extra}"
        )

    frontmatter, _ = split_frontmatter(
        (generated / "SKILL.md").read_text(encoding="utf-8")
    )
    if not isinstance(frontmatter, dict):
        raise ValidationError(f"portable skill {name} has invalid frontmatter")
    unsupported = set(frontmatter) - AGENT_SKILL_KEYS
    if unsupported:
        raise ValidationError(
            f"portable skill {name} has unsupported frontmatter: "
            f"{', '.join(sorted(unsupported))}"
        )
    if frontmatter.get("name") != name:
        raise ValidationError(f"portable skill {name} frontmatter name does not match")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        raise ValidationError(f"portable skill {name} has an invalid Agent Skills name")
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValidationError(f"portable skill {name} has no description")
    if len(description) > 1024:
        raise ValidationError(
            f"portable skill {name} description exceeds 1024 characters"
        )

    for relative, source_file in expected.items():
        generated_file = actual[relative]
        if source_file.read_bytes() != generated_file.read_bytes():
            raise ValidationError(f"canonical skill content drift: {generated / relative}")
        source_mode = stat.S_IMODE(source_file.stat().st_mode)
        generated_mode = stat.S_IMODE(generated_file.stat().st_mode)
        if source_mode != generated_mode:
            raise ValidationError(
                f"canonical skill mode drift: {generated / relative} "
                f"{source_mode:o} != {generated_mode:o}"
            )

    return len(actual)


def validate_native_skill(name: str) -> None:
    source = SRC_DIR / name
    generated = NATIVE_SKILLS_DIR / name
    skill_md = generated / "SKILL.md"
    if not skill_md.is_file():
        raise ValidationError(f"missing native plugin skill: {name}")

    if skill_md.read_text(encoding="utf-8") != build_skill_md(
        source / "SKILL.md",
        name,
    ):
        raise ValidationError(f"native plugin skill drift: {name}/SKILL.md")

    expected = {Path("SKILL.md")}
    for subdir_name in NATIVE_SUBDIRS:
        source_subdir = source / subdir_name
        if not source_subdir.is_dir():
            continue
        expected.update(
            path.relative_to(source)
            for path in source_subdir.rglob("*")
            if path.is_file()
        )

    actual = files_under(generated)
    if set(actual) != expected:
        missing = sorted(str(path) for path in expected - set(actual))
        extra = sorted(str(path) for path in set(actual) - expected)
        raise ValidationError(
            f"native skill {name} file drift; missing={missing}, extra={extra}"
        )

    for relative in expected - {Path("SKILL.md")}:
        source_file = source / relative
        generated_file = actual[relative]
        if source_file.read_bytes() != generated_file.read_bytes():
            raise ValidationError(f"native skill content drift: {name}/{relative}")
        source_mode = stat.S_IMODE(source_file.stat().st_mode)
        generated_mode = stat.S_IMODE(generated_file.stat().st_mode)
        if source_mode != generated_mode:
            raise ValidationError(
                f"native skill mode drift: {name}/{relative} "
                f"{source_mode:o} != {generated_mode:o}"
            )


def read_nested(document, keys):
    value = document
    for key in keys:
        value = value[key]
    return value


def validate_versions(expected_version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", expected_version):
        raise ValidationError(
            f"portable manifest version is not Semantic Versioning: {expected_version}"
        )
    for label, (path, keys) in VERSION_PATHS.items():
        version = read_nested(load_json(path), keys)
        if version != expected_version:
            raise ValidationError(
                f"{label} version {version!r} does not match {expected_version!r}"
            )

    changelog = (ROOT / "plugin" / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {expected_version} " not in changelog:
        raise ValidationError(f"plugin changelog has no {expected_version} release")


def main() -> int:
    try:
        manifest = validate_schema(
            PORTABLE_PLUGIN_DIR / "plugin.json",
            PLUGIN_SCHEMA,
        )
        load_official_schema(MCP_SCHEMA)
        assert_contained_tree(PORTABLE_PLUGIN_DIR)

        root_entries = {path.name for path in PORTABLE_PLUGIN_DIR.iterdir()}
        unexpected = root_entries - ALLOWED_PORTABLE_ROOT_ENTRIES
        if unexpected:
            raise ValidationError(
                "unexpected portable package root entries: "
                f"{', '.join(sorted(unexpected))}"
            )

        mcp_path = PORTABLE_PLUGIN_DIR / "mcp.json"
        if mcp_path.exists():
            validate_schema(mcp_path, MCP_SCHEMA)

        if not PORTABLE_SKILLS_DIR.is_dir():
            raise ValidationError("portable skills path is missing or is not a directory")

        expected_skills = set(shared_skills())
        skill_entries = list(PORTABLE_SKILLS_DIR.iterdir())
        direct_files = sorted(path.name for path in skill_entries if path.is_file())
        if direct_files:
            raise ValidationError(
                f"portable skills directory contains files: {direct_files}"
            )
        actual_skills = {path.name for path in skill_entries if path.is_dir()}
        if actual_skills != expected_skills:
            raise ValidationError(
                "portable skill membership drift; "
                f"expected={sorted(expected_skills)}, actual={sorted(actual_skills)}"
            )
        missing_skill_files = sorted(
            name
            for name in actual_skills
            if not (PORTABLE_SKILLS_DIR / name / "SKILL.md").is_file()
        )
        if missing_skill_files:
            raise ValidationError(
                f"portable skill directories lack SKILL.md: {missing_skill_files}"
            )

        artifact_count = 0
        native_skills = {path.name for path in NATIVE_SKILLS_DIR.iterdir()}
        if native_skills != expected_skills:
            raise ValidationError("native skill membership drift")
        for name in sorted(expected_skills):
            artifact_count += validate_portable_skill(name)
            validate_native_skill(name)
        for name in sorted(INSTALLED_SKILLS):
            validate_portable_skill(name, INSTALLED_SKILLS_DIR)
        if (PORTABLE_PLUGIN_DIR / "LICENSE").read_bytes() != (
            ROOT / "plugin" / "LICENSE"
        ).read_bytes():
            raise ValidationError("portable LICENSE does not match plugin/LICENSE")

        validate_versions(manifest["version"])
    except (KeyError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mcp_status = "validated" if mcp_path.exists() else "not declared"
    print(
        "Agent Plugins package validation passed: "
        f"{len(expected_skills)} portable skills, {artifact_count} portable artifacts, "
        f"{len(expected_skills)} native mirrors, "
        f"{len(INSTALLED_SKILLS)} managed .agents copies, "
        f"MCP {mcp_status}, version {manifest['version']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
