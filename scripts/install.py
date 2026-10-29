#!/usr/bin/env python3
"""Install the complete UI prototype skill into a Codex skills directory."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys


REQUIRED_FILES = (Path("SKILL.md"), Path("agents/openai.yaml"))
EXCLUDED_NAMES = {".DS_Store", ".git"}
EXCLUDED_DIRECTORIES = {"tests", ".claude-plugin", "__pycache__"}


@dataclass(frozen=True)
class InstallResult:
    destination: Path
    backup: Path | None
    copied_files: tuple[str, ...]
    dry_run: bool


def default_codex_skills_dir() -> Path:
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def is_excluded(relative: Path) -> bool:
    if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
        return True
    if relative.name in EXCLUDED_NAMES:
        return True
    if relative.suffix == ".pyc":
        return True
    return False


def copy_ignore(directory: str, names: list[str]) -> set[str]:
    base = Path(directory)
    ignored: set[str] = set()
    for name in names:
        relative = Path(name)
        if is_excluded(relative) or (base / name).is_dir() and name in EXCLUDED_DIRECTORIES:
            ignored.add(name)
    return ignored


def _relative_files(source: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(path.relative_to(source))
            for path in source.rglob("*")
            if path.is_file() and not is_excluded(path.relative_to(source))
        )
    )


def _backup_path(destination: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = destination.with_name(f"{destination.name}.backup-{stamp}")
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = destination.with_name(f"{destination.name}.backup-{stamp}-{suffix}")
        suffix += 1
    return candidate


def install_skill(source: Path, destination: Path, *, dry_run: bool) -> InstallResult:
    source = source.expanduser().resolve()
    destination = destination.expanduser()
    if not destination.is_absolute():
        destination = Path.cwd() / destination
    destination = destination.absolute()
    if not source.is_dir():
        raise ValueError(f"source skill directory does not exist: {source}")
    symlinks = tuple(path for path in source.rglob("*") if path.is_symlink())
    if symlinks:
        relative = symlinks[0].relative_to(source)
        raise ValueError(f"source skill contains unsupported symlink: {relative}")
    physical_destination = destination.resolve(strict=False)
    try:
        physical_destination.relative_to(source)
    except ValueError:
        try:
            source.relative_to(physical_destination)
        except ValueError:
            pass
        else:
            raise ValueError("source and destination overlap")
    else:
        raise ValueError("source and destination overlap")

    missing = tuple(str(relative) for relative in REQUIRED_FILES if not (source / relative).is_file())
    if missing:
        raise ValueError(f"source skill is incomplete: {', '.join(missing)}")

    copied_files = _relative_files(source)
    if dry_run:
        return InstallResult(destination, None, copied_files, True)

    destination.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if destination.exists() or destination.is_symlink():
        backup = _backup_path(destination)
        destination.rename(backup)

    try:
        shutil.copytree(source, destination, ignore=copy_ignore)
        missing_destination = tuple(
            str(relative) for relative in REQUIRED_FILES if not (destination / relative).is_file()
        )
        if missing_destination:
            raise ValueError(
                "installed skill is incomplete: " + ", ".join(missing_destination)
            )
    except Exception:
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if backup is not None and (backup.exists() or backup.is_symlink()):
            backup.rename(destination)
        raise

    return InstallResult(destination, backup, copied_files, False)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="skill directory to install (defaults to this skill)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="destination skill directory (defaults to CODEX_HOME/skills/replicate-ui-prototype)",
    )
    parser.add_argument("--dry-run", action="store_true", help="validate and list files without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    destination = args.dest or (default_codex_skills_dir() / "replicate-ui-prototype")
    try:
        result = install_skill(args.source, destination, dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        print(f"install failed: {error}", file=sys.stderr)
        return 1
    payload = asdict(result)
    payload["destination"] = str(result.destination)
    payload["backup"] = str(result.backup) if result.backup else None
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
