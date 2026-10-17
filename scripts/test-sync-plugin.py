#!/usr/bin/env python3
"""Focused regression checks for portable skill generation."""

import stat
import tempfile
from pathlib import Path

import sync_plugin


def write(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source" / "sample"
        portable_skills = root / "portable" / "skills"
        write(
            source / "SKILL.md",
            "---\nname: sample\ndescription: Portable fixture.\n---\n\n# Sample\n",
        )
        write(source / "scripts" / "run.sh", "#!/bin/bash\nexit 0\n", 0o755)
        write(source / "hooks" / "example.txt", "skill resource\n")
        write(source / "evals" / "fixture.json", "{}\n")

        original_portable_skills = sync_plugin.PORTABLE_SKILLS_DIR
        sync_plugin.PORTABLE_SKILLS_DIR = portable_skills
        try:
            sync_plugin.sync_portable_skill("sample", source)
            generated = portable_skills / "sample"
            assert (generated / "SKILL.md").read_bytes() == (
                source / "SKILL.md"
            ).read_bytes()
            assert (generated / "hooks" / "example.txt").is_file()
            assert not (generated / "evals").exists()
            assert stat.S_IMODE(
                (generated / "scripts" / "run.sh").stat().st_mode
            ) == 0o755

            native = root / "native" / "sample"
            write(
                native / "SKILL.md",
                "---\nname: sample\ndescription: Old.\nuser-invocable: false\nhooks:\n  PostToolUse: []\n---\n",
            )
            write(
                source / "assets" / "claude-hooks.json",
                '{"hooks": {"PostToolUseFailure": [{"matcher": "Bash", "hooks": []}]}}\n',
            )
            sync_plugin.sync_native_skill("sample", source, native)
            metadata, _ = sync_plugin.split_frontmatter((native / "SKILL.md").read_text())
            assert metadata["hooks"] == {"PostToolUseFailure": [{"matcher": "Bash", "hooks": []}]}
            assert metadata["user-invocable"] is False

            stale = portable_skills / "stale"
            stale.mkdir()
            write(portable_skills / "unexpected.txt", "stale\n")
            sync_plugin.remove_stale_portable_skills({"sample"})
            assert not stale.exists()
            assert not (portable_skills / "unexpected.txt").exists()
        finally:
            sync_plugin.PORTABLE_SKILLS_DIR = original_portable_skills

    try:
        sync_plugin.validate_portable_frontmatter(
            "sample",
            {"name": "sample", "description": "Portable.", "hooks": {}},
        )
    except SystemExit as exc:
        assert "non-portable frontmatter keys: hooks" in str(exc)
    else:
        raise AssertionError("non-portable frontmatter was accepted")

    for invalid_name in ("..", "Sample", "sample/name"):
        try:
            sync_plugin.validate_skill_name(invalid_name)
        except SystemExit as exc:
            assert "invalid skill name" in str(exc)
        else:
            raise AssertionError(f"invalid skill name was accepted: {invalid_name}")

    try:
        sync_plugin.validate_portable_frontmatter("sample", ["not", "a", "mapping"])
    except SystemExit as exc:
        assert "frontmatter must be a mapping" in str(exc)
    else:
        raise AssertionError("non-mapping frontmatter was accepted")

    print("Portable sync regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
