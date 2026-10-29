#!/usr/bin/env python3
"""Produce a bounded, credential-safe report about a UI project."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Iterable


MAX_CANDIDATES = 500
MAX_TEXT_BYTES = 64 * 1024
SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    ".vite",
    "build",
    "coverage",
    "dist",
    "logs",
    "node_modules",
    "output_files",
    "public/build",
    "target",
    "vendor",
}
INSTRUCTION_NAMES = {"AGENTS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md"}
COMPONENT_EXTENSIONS = {".astro", ".jsx", ".tsx", ".svelte", ".vue"}
STYLE_EXTENSIONS = {".css", ".less", ".scss", ".sass", ".styl"}
ASSET_DIRECTORY_NAMES = {"assets", "images", "media", "public", "static"}


@dataclass(frozen=True)
class ProjectReport:
    root: str
    package_manager: str | None
    frameworks: tuple[str, ...]
    styling: tuple[str, ...]
    scripts: dict[str, str]
    instruction_files: tuple[str, ...]
    component_files: tuple[str, ...]
    style_files: tuple[str, ...]
    token_files: tuple[str, ...]
    asset_dirs: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def _is_skipped(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return any(part in SKIP_DIRECTORIES for part in relative.parts)


def _iter_files(root: Path) -> Iterable[Path]:
    count = 0
    for path in root.rglob("*"):
        if count >= MAX_CANDIDATES:
            return
        if _is_skipped(path, root):
            continue
        if path.is_file():
            count += 1
            yield path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_BYTES]
    except OSError:
        return ""


def _load_package_json(root: Path, warnings: list[str]) -> tuple[dict[str, object], Path | None]:
    package_path = root / "package.json"
    if not package_path.is_file():
        return {}, None
    try:
        payload = json.loads(_read_text(package_path))
    except json.JSONDecodeError:
        warnings.append("package.json could not be parsed")
        return {}, package_path
    if not isinstance(payload, dict):
        warnings.append("package.json must contain an object")
        return {}, package_path
    return payload, package_path


def _package_manager(root: Path, package_path: Path | None) -> str | None:
    if package_path is None:
        return None
    if (root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (root / "yarn.lock").is_file():
        return "yarn"
    if (root / "bun.lockb").is_file() or (root / "bun.lock").is_file():
        return "bun"
    return "npm"


def _dependency_names(package: dict[str, object]) -> set[str]:
    names: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = package.get(field)
        if isinstance(values, dict):
            names.update(str(name).lower() for name in values)
    return names


def _frameworks(package: dict[str, object], files: list[Path], root: Path) -> set[str]:
    dependencies = _dependency_names(package)
    result: set[str] = set()
    if "react" in dependencies or "react-dom" in dependencies:
        result.add("react")
    if "vue" in dependencies:
        result.add("vue")
    if "svelte" in dependencies:
        result.add("svelte")
    if "next" in dependencies:
        result.add("next")
    if "nuxt" in dependencies:
        result.add("nuxt")
    if "astro" in dependencies:
        result.add("astro")
    if not result and any(path.suffix.lower() == ".html" for path in files):
        result.add("static-html")
    return result


def _styling(package: dict[str, object], files: list[Path], root: Path) -> tuple[set[str], set[str]]:
    dependencies = _dependency_names(package)
    styles: set[str] = set()
    token_files: set[str] = set()
    if any(name == "tailwindcss" or name.endswith("/tailwindcss") for name in dependencies):
        styles.add("tailwind")
    if "styled-components" in dependencies:
        styles.add("styled-components")
    if "@emotion/react" in dependencies or "@emotion/styled" in dependencies:
        styles.add("emotion")

    for path in files:
        relative = str(path.relative_to(root))
        suffix = path.suffix.lower()
        if suffix in STYLE_EXTENSIONS:
            styles.add("css")
            if ".module." in path.name:
                styles.add("css-modules")
            content = _read_text(path)
            if ":root" in content or "--" in content or "token" in path.name.lower() or "theme" in path.name.lower():
                token_files.add(relative)
            if "@tailwind" in content:
                styles.add("tailwind")
    if not styles and any(path.suffix.lower() in COMPONENT_EXTENSIONS for path in files):
        styles.add("component-local-styles-unknown")
    return styles, token_files


def inspect_project(root: Path) -> ProjectReport:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"project directory does not exist: {root}")

    warnings: list[str] = []
    package, package_path = _load_package_json(root, warnings)
    files = list(_iter_files(root))
    frameworks = _frameworks(package, files, root)
    styling, token_files = _styling(package, files, root)
    relative_files = {path: str(path.relative_to(root)) for path in files}

    component_files = tuple(
        sorted(relative for path, relative in relative_files.items() if path.suffix.lower() in COMPONENT_EXTENSIONS)
    )
    style_files = tuple(
        sorted(relative for path, relative in relative_files.items() if path.suffix.lower() in STYLE_EXTENSIONS)
    )
    instruction_files = tuple(
        sorted(relative for path, relative in relative_files.items() if path.name in INSTRUCTION_NAMES)
    )
    asset_dirs = tuple(
        sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_dir() and not _is_skipped(path, root) and path.name.lower() in ASSET_DIRECTORY_NAMES
        )
    )

    if not frameworks:
        warnings.append("no framework or static HTML baseline detected")
    if not style_files:
        warnings.append("no stylesheet candidate detected")
    if not instruction_files:
        warnings.append("no project instruction file detected")
    if not component_files and "static-html" not in frameworks:
        warnings.append("no component candidate detected")

    scripts = package.get("scripts", {})
    normalized_scripts = (
        {str(name): str(command) for name, command in scripts.items()}
        if isinstance(scripts, dict)
        else {}
    )
    return ProjectReport(
        root=str(root),
        package_manager=_package_manager(root, package_path),
        frameworks=tuple(sorted(frameworks)),
        styling=tuple(sorted(styling)),
        scripts=normalized_scripts,
        instruction_files=instruction_files,
        component_files=component_files,
        style_files=style_files,
        token_files=tuple(sorted(token_files)),
        asset_dirs=asset_dirs,
        warnings=tuple(warnings),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="project root to inspect")
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        report = inspect_project(args.root)
    except ValueError as error:
        print(f"inspect failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report.to_json(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
