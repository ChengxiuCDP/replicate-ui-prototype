#!/usr/bin/env python3
"""Render a local prototype at deterministic desktop and mobile viewports."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlparse


@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int


DEFAULT_VIEWPORTS = {
    "desktop": Viewport("desktop", 1440, 1000),
    "mobile": Viewport("mobile", 390, 844),
}


def _browser_candidates() -> list[str]:
    home = Path.home()
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(home / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Google/Chrome/Application/chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local"), "Google/Chrome/Application/chrome.exe"),
    ]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    return candidates


def find_browser(explicit: Path | None = None) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser()
        if candidate.is_file():
            return candidate.absolute()
        found = shutil.which(str(candidate))
        if found:
            return Path(found).absolute()
        raise ValueError(f"browser executable does not exist: {candidate}")
    seen: set[str] = set()
    for raw in _browser_candidates():
        if raw in seen:
            continue
        seen.add(raw)
        candidate = Path(raw).expanduser()
        if candidate.is_file():
            return candidate.absolute()
    raise ValueError("no Chromium-family browser found; install Chrome/Chromium or pass --browser PATH")


def build_command(browser: Path, url: str, output: Path, viewport: Viewport, *, wait_ms: int = 2000) -> list[str]:
    if viewport.width <= 0 or viewport.height <= 0:
        raise ValueError("viewport dimensions must be positive")
    if wait_ms < 0:
        raise ValueError("wait_ms must be non-negative")
    return [
        str(browser.absolute()),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={viewport.width},{viewport.height}",
        f"--virtual-time-budget={wait_ms}",
        f"--screenshot={output.absolute()}",
        url,
    ]


def _target_url(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme:
        return target
    path = Path(target).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"target URL or file does not exist: {target}")
    return path.as_uri()


def parse_viewport(value: str) -> Viewport:
    try:
        name, dimensions = value.split(":", 1)
        width_text, height_text = dimensions.lower().split("x", 1)
        viewport = Viewport(name, int(width_text), int(height_text))
    except (ValueError, AttributeError) as error:
        raise ValueError(f"viewport must use NAME:WIDTHxHEIGHT: {value}") from error
    if viewport.width <= 0 or viewport.height <= 0:
        raise ValueError(f"viewport dimensions must be positive: {value}")
    return viewport


def render_screenshots(
    target: str,
    out_dir: Path,
    *,
    browser: Path | None = None,
    viewports: list[Viewport] | None = None,
    wait_ms: int = 2000,
) -> list[Path]:
    executable = find_browser(browser)
    target_url = _target_url(target)
    selected = viewports or list(DEFAULT_VIEWPORTS.values())
    out_dir = out_dir.expanduser().absolute()
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for viewport in selected:
        output = out_dir / f"{viewport.name}.png"
        command = build_command(executable, target_url, output, viewport, wait_ms=wait_ms)
        subprocess.run(command, check=True)
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"browser did not produce a non-empty screenshot: {output}")
        outputs.append(output)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="http(s) URL or local HTML file")
    parser.add_argument("--out-dir", type=Path, default=Path(".ui-prototype/screenshots"))
    parser.add_argument("--browser", type=Path, default=None)
    parser.add_argument("--viewport", action="append", default=[], help="NAME:WIDTHxHEIGHT; repeatable")
    parser.add_argument("--wait-ms", type=int, default=2000)
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        viewports = [parse_viewport(value) for value in args.viewport] or None
        outputs = render_screenshots(args.target, args.out_dir, browser=args.browser, viewports=viewports, wait_ms=args.wait_ms)
    except (OSError, ValueError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"render failed: {error}", file=sys.stderr)
        return 1
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
