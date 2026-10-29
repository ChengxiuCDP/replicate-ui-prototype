#!/usr/bin/env python3
"""Build a standalone side-by-side and same-viewport overlay comparison page."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class Candidate:
    image: Path
    label: str
    viewport: str


def _image_reference(image: Path, base_dir: Path | None) -> str:
    if base_dir is None:
        return image.name
    return Path(os.path.relpath(image.resolve(), base_dir.expanduser().resolve())).as_posix()


def build_comparison(
    candidates: list[Candidate], *, title: str, base_dir: Path | None = None
) -> str:
    if not candidates:
        raise ValueError("at least one screenshot is required")
    for candidate in candidates:
        if not candidate.image.is_file():
            raise FileNotFoundError(candidate.image)

    cards = "\n".join(
        f'''<figure class="card">
  <figcaption><strong>{escape(candidate.label)}</strong><span>{escape(candidate.viewport)}</span></figcaption>
  <img src="{escape(_image_reference(candidate.image, base_dir), quote=True)}" alt="{escape(candidate.label)} screenshot">
</figure>'''
        for candidate in candidates
    )
    base = candidates[0]
    overlay = next(
        (candidate for candidate in candidates[1:] if candidate.viewport == base.viewport),
        None,
    )
    if overlay is None:
        overlay_html = "<p>No second screenshot exists for the same viewport; overlay skipped.</p>"
    else:
        overlay_html = f'''<h2>{escape(base.label)} / {escape(overlay.label)} overlay</h2>
    <div class="overlay-stage">
      <img src="{escape(_image_reference(base.image, base_dir), quote=True)}" alt="Base screenshot">
      <img id="overlay-image" src="{escape(_image_reference(overlay.image, base_dir), quote=True)}" alt="Overlay screenshot">
    </div>
    <label>Overlay amount <input id="overlay-range" type="range" min="0" max="100" value="50"></label>
    <script>
      const range = document.querySelector('#overlay-range');
      const image = document.querySelector('#overlay-image');
      range.addEventListener('input', () => {{ image.style.clipPath = `inset(0 ${{100 - range.value}}% 0 0)`; }});
    </script>'''
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; background: #171717; color: #f5f5f5; }}
    body {{ margin: 0; padding: 24px; }}
    h1 {{ margin: 0 0 24px; font-size: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    .card {{ margin: 0; padding: 12px; border: 1px solid #444; border-radius: 12px; background: #242424; }}
    figcaption {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 8px; font-size: 13px; }}
    figcaption span {{ color: #aaa; }}
    img {{ display: block; width: 100%; height: auto; border-radius: 8px; background: #fff; }}
    .overlay {{ max-width: 720px; margin-top: 32px; }}
    .overlay-stage {{ position: relative; overflow: hidden; border-radius: 8px; background: #fff; }}
    .overlay-stage img {{ width: 100%; }}
    .overlay-stage img:last-child {{ position: absolute; inset: 0; clip-path: inset(0 50% 0 0); }}
    input {{ width: 100%; margin-top: 12px; }}
    @media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <section class="grid" aria-label="Screenshot comparison">{cards}</section>
  <section class="overlay" aria-label="Overlay comparison">
    {overlay_html}
  </section>
</body>
</html>
'''


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--title", default="UI prototype comparison")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    candidates = [
        Candidate(
            image=image,
            label=image.stem,
            viewport=image.stem if image.stem in {"desktop", "mobile"} else "unspecified",
        )
        for image in args.images
    ]
    try:
        html = build_comparison(candidates, title=args.title, base_dir=args.output.parent)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"comparison failed: {error}", file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
