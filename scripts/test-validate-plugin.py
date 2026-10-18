#!/usr/bin/env python3
"""Check that packaging follows the marketplace, not a hardcoded parent tree."""

import importlib.util
import json
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "validate_plugin", Path(__file__).with_name("validate-plugin.py")
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        selected = root / "adapters" / "copilot"
        catalog = root / ".github/plugin/marketplace.json"
        write(catalog, json.dumps({"plugins": [{
            "name": "pskoett-ai-skills", "source": "./adapters/copilot"
        }]}))
        write(selected / "plugin.json", json.dumps({
            "name": "pskoett-ai-skills", "agents": "agents/",
            "skills": "skills/", "hooks": "hooks/hooks.json"
        }))
        write(root / "plugin/agents/reviewer.md", "wrong parent agent")
        write(selected / "agents/reviewer.agent.md", "selected Copilot agent")
        write(root / "shared/skills/sample/SKILL.md", "shared skill")
        write(root / "shared/hooks/hooks.json", '{"hooks": {}}')
        (selected / "skills").symlink_to("../../shared/skills")
        (selected / "hooks").symlink_to("../../shared/hooks")

        destination = Path(temp) / "output"
        destination.mkdir()
        _, artifact = validator.build_artifact(destination, root)
        assert (artifact / "agents/reviewer.agent.md").read_text() == "selected Copilot agent"
        assert not (artifact / "agents/reviewer.md").exists()
        assert (artifact / "skills/sample/SKILL.md").read_text() == "shared skill"
        assert not (artifact / "skills").is_symlink()
        assert (artifact / "hooks/hooks.json").is_file()

        # Reject both lexical traversal and symlinks outside the repository.
        for invalid in ("../outside", str(Path(temp) / "outside")):
            try:
                validator.resolve_component(selected, invalid, root)
            except validator.ValidationError:
                pass
            else:
                raise AssertionError(f"accepted escaping path: {invalid}")
        write(Path(temp) / "outside", "not a repository resource")
        (selected / "escape").symlink_to(Path(temp) / "outside")
        try:
            validator.resolve_component(selected, "escape", root)
        except validator.ValidationError:
            pass
        else:
            raise AssertionError("accepted escaping symlink")

    print("Copilot packaging regression checks passed (marketplace root, agent suffix, shared resources, containment).")


if __name__ == "__main__":
    main()
