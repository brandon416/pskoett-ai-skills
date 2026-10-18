#!/usr/bin/env python3
"""Focused regression checks for portable skill generation."""

import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

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
        native_skills = root / "native"
        installed_skills = root / ".agents" / "skills"
        write(
            source / "SKILL.md",
            "---\nname: sample\ndescription: Portable fixture.\n---\n\n# Sample\n",
        )
        write(source / "scripts" / "run.sh", "#!/bin/bash\nexit 0\n", 0o755)
        write(source / "hooks" / "example.txt", "skill resource\n")
        write(source / "evals" / "fixture.json", "{}\n")
        write(root / "plugin" / "LICENSE", "fixture license\n")
        write(installed_skills / "local-only" / "SKILL.md", "local content\n")

        with patch.multiple(
            sync_plugin,
            ROOT=root,
            SRC_DIR=source.parent,
            NATIVE_SKILLS_DIR=native_skills,
            PORTABLE_PLUGIN_DIR=portable_skills.parent,
            PORTABLE_SKILLS_DIR=portable_skills,
            INSTALLED_SKILLS_DIR=installed_skills,
            NATIVE_REGISTRATION={"sample": {"user-invocable": True}},
            INSTALLED_SKILLS={"sample"},
        ), patch("sys.argv", ["sync_plugin.py"]):
            # No generated directories exist: membership and registration must
            # still be complete, rather than inferred from yesterday's output.
            sync_plugin.main()
            generated = portable_skills / "sample"
            assert (generated / "SKILL.md").read_bytes() == (
                source / "SKILL.md"
            ).read_bytes()
            assert (generated / "hooks" / "example.txt").is_file()
            assert not (generated / "evals").exists()
            assert stat.S_IMODE(
                (generated / "scripts" / "run.sh").stat().st_mode
            ) == 0o755

            native = native_skills / "sample"
            clean_native = (native / "SKILL.md").read_bytes()
            metadata, _ = sync_plugin.split_frontmatter(clean_native.decode())
            assert metadata["user-invocable"] is True
            write(
                native / "SKILL.md",
                "---\nname: sample\ndescription: Old.\nuser-invocable: false\nhooks:\n  PostToolUse: []\n---\n",
            )
            write(installed_skills / "sample" / "SKILL.md", "drift\n")
            write(installed_skills / "sample" / "stale.txt", "stale\n")
            write(native / "stale.txt", "stale\n")
            write(native_skills / "stale" / "SKILL.md", "stale\n")
            write(portable_skills / "stale" / "SKILL.md", "stale\n")
            write(portable_skills / "unexpected.txt", "stale\n")
            sync_plugin.main()
            assert (native / "SKILL.md").read_bytes() == clean_native
            assert not (native / "stale.txt").exists()
            assert not (native_skills / "stale").exists()
            assert not (portable_skills / "stale").exists()
            assert not (portable_skills / "unexpected.txt").exists()
            assert not (installed_skills / "sample" / "stale.txt").exists()
            assert (installed_skills / "sample" / "SKILL.md").read_bytes() == (source / "SKILL.md").read_bytes()
            assert (installed_skills / "local-only" / "SKILL.md").read_text() == "local content\n"
            assert not (installed_skills / "sample" / "evals").exists()
            assert stat.S_IMODE((installed_skills / "sample" / "scripts" / "run.sh").stat().st_mode) == 0o755

            write(
                source / "assets" / "claude-hooks.json",
                '{"hooks": {"PostToolUseFailure": [{"matcher": "Bash", "hooks": []}]}}\n',
            )
            sync_plugin.main()
            metadata, _ = sync_plugin.split_frontmatter((native / "SKILL.md").read_text())
            assert metadata["hooks"] == {"PostToolUseFailure": [{"matcher": "Bash", "hooks": []}]}
            assert metadata["user-invocable"] is True

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

    print("Skill distribution regression checks passed (clean generation, drift repair, local-only preservation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
