#!/usr/bin/env python3
"""Validate the installable Copilot plugin artifact and optional hook wrapper."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ROOT_VARIABLES = ("PLUGIN_ROOT", "COPILOT_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT")


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        raise ValidationError(f"cannot read {label}: {error}") from error


def resolve_component(plugin_root: Path, relative_path: str, repository_root: Path) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError(f"component escapes plugin root: {relative_path}")
    # Keep the declared path for artifact placement, not the symlink's target.
    path = plugin_root / relative
    if not path.exists():
        raise ValidationError(f"missing plugin component: {relative_path}")
    # This repo shares resources through symlinks. Materialize only repo-local
    # targets; this is a packaging check, not a claim about Copilot's installer.
    if not path.resolve().is_relative_to(repository_root.resolve()):
        raise ValidationError(f"component escapes repository: {path}")
    return path


def copy_path(source: Path, destination: Path, repository_root: Path) -> None:
    # Check every traversed entry, including children of linked directories.
    if not source.resolve().is_relative_to(repository_root.resolve()):
        raise ValidationError(f"component escapes repository: {source}")
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for entry in source.iterdir():
            copy_path(entry, destination / entry.name, repository_root)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build_artifact(destination: Path, repository_root: Path = ROOT) -> tuple[dict, Path]:
    marketplace = load_json(repository_root / ".github/plugin/marketplace.json")
    entries = [entry for entry in marketplace["plugins"] if entry["name"] == "pskoett-ai-skills"]
    if len(entries) != 1 or not isinstance(entries[0]["source"], str):
        raise ValidationError("expected one repo-local pskoett-ai-skills marketplace entry")
    plugin_root = resolve_component(repository_root, entries[0]["source"], repository_root)
    manifest_path = plugin_root / "plugin.json"
    manifest = load_json(manifest_path)
    if manifest["name"] != entries[0]["name"]:
        raise ValidationError("manifest name differs from marketplace entry")
    artifact = destination / manifest["name"]
    artifact.mkdir()
    copy_path(manifest_path, artifact / "plugin.json", repository_root)

    license_path = plugin_root / "LICENSE"
    if license_path.exists():
        copy_path(license_path, artifact / "LICENSE", repository_root)

    for field in ("agents", "skills"):
        values = manifest.get(field, [])
        if isinstance(values, str):
            values = [values]
        for value in values:
            source = resolve_component(plugin_root, value, repository_root)
            copy_path(source, artifact / source.relative_to(plugin_root), repository_root)

    hooks_path = manifest.get("hooks")
    if not isinstance(hooks_path, str):
        raise ValidationError("Copilot manifest must reference a hooks configuration file")
    hooks_source = resolve_component(plugin_root, hooks_path, repository_root)
    copy_path(
        hooks_source.parent,
        artifact / hooks_source.parent.relative_to(plugin_root),
        repository_root,
    )
    return manifest, artifact


def iter_hook_commands(hooks_config: dict):
    for event_entries in hooks_config.get("hooks", {}).values():
        for entry in event_entries:
            for hook in entry.get("hooks", [entry]):
                command = hook.get("command")
                if command:
                    yield command


def validate_hook_assets(artifact: Path, hooks_relative_path: str) -> Path:
    hooks_config = load_json(artifact / hooks_relative_path)
    referenced_assets = set()

    for command in iter_hook_commands(hooks_config):
        expanded = command
        for variable in ROOT_VARIABLES:
            expanded = expanded.replace(f"${{{variable}}}", str(artifact))
        tokens = shlex.split(expanded)
        if not tokens:
            raise ValidationError("plugin hook command is empty")

        target = Path(tokens[0])
        if target.is_relative_to(artifact):
            if not target.is_file():
                raise ValidationError(
                    f"hook references an asset absent from the artifact: "
                    f"{target.relative_to(artifact)}"
                )
            if not os.access(target, os.X_OK):
                raise ValidationError(
                    f"hook asset is not executable: {target.relative_to(artifact)}"
                )
            referenced_assets.add(target)

    if not referenced_assets:
        raise ValidationError("no plugin-local hook assets were validated")
    if len(referenced_assets) != 1:
        raise ValidationError("expected all Entire hooks to share one wrapper")
    return referenced_assets.pop()


def write_fake_entire(bin_dir: Path, body: str) -> None:
    executable = bin_dir / "entire"
    executable.write_text(f"#!/bin/bash\n{body}\n")
    executable.chmod(0o755)


def run_wrapper(wrapper: Path, path: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PATH"] = path
    return subprocess.run(
        [str(wrapper), "hooks", "claude-code", "pre-task"],
        input="{}\n",
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=15,
    )


def validate_optional_entire(wrapper: Path, temporary_root: Path) -> None:
    unavailable = run_wrapper(wrapper, str(temporary_root / "empty-bin"))
    if unavailable.returncode != 0 or "integration unavailable" not in unavailable.stderr:
        raise ValidationError("missing Entire must produce a diagnosed, non-blocking result")

    success_bin = temporary_root / "success-bin"
    success_bin.mkdir()
    write_fake_entire(success_bin, "printf '{\"continue\":true}\\n'")
    success = run_wrapper(wrapper, f"{success_bin}:/usr/bin:/bin")
    if success.returncode != 0 or success.stdout != '{"continue":true}\n':
        raise ValidationError("successful Entire output was not preserved")

    denial_bin = temporary_root / "denial-bin"
    denial_bin.mkdir()
    denial = '{"continue":false,"stopReason":"synthetic policy denial"}'
    write_fake_entire(denial_bin, f"printf '%s\\n' {shlex.quote(denial)}")
    denied = run_wrapper(wrapper, f"{denial_bin}:/usr/bin:/bin")
    if denied.returncode != 0 or denied.stdout != f"{denial}\n":
        raise ValidationError("intentional hook denial output was not preserved")

    failure_bin = temporary_root / "failure-bin"
    failure_bin.mkdir()
    write_fake_entire(failure_bin, "echo 'synthetic Entire failure' >&2\nexit 42")
    failure = run_wrapper(wrapper, f"{failure_bin}:/usr/bin:/bin")
    if failure.returncode != 0 or "exit 42" not in failure.stderr:
        raise ValidationError("failing optional Entire hook did not fail open with diagnosis")

    hanging_bin = temporary_root / "hanging-bin"
    hanging_bin.mkdir()
    child_pid_path = temporary_root / "hanging-child.pid"
    write_fake_entire(
        hanging_bin,
        "trap '' TERM\n"
        "sleep 60 &\n"
        f"echo $! > {shlex.quote(str(child_pid_path))}\n"
        "wait",
    )
    started = time.monotonic()
    hanging = run_wrapper(wrapper, f"{hanging_bin}:/usr/bin:/bin")
    elapsed = time.monotonic() - started
    if (
        hanging.returncode != 0
        or hanging.stdout
        or "timed out after 5s" not in hanging.stderr
        or elapsed >= 10
    ):
        raise ValidationError("hanging Entire hook did not time out with a diagnosed no-op result")

    child_pid = int(child_pid_path.read_text())
    try:
        os.kill(child_pid, 0)
    except ProcessLookupError:
        pass
    else:
        raise ValidationError("hanging Entire hook left a child process running")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory() as temp:
            temporary_root = Path(temp)
            manifest, artifact = build_artifact(temporary_root)
            wrapper = validate_hook_assets(artifact, manifest["hooks"])
            validate_optional_entire(wrapper, temporary_root)
    except ValidationError as error:
        print(f"Plugin validation failed: {error}", file=sys.stderr)
        return 1

    print("Marketplace-selected Copilot artifact and optional Entire hook validation passed (not a live client test).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
