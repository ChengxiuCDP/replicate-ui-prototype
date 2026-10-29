#!/usr/bin/env python3
"""Validate a standalone UI prototype without fetching network resources."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


INTERNAL_PATTERN = re.compile(
    r"10\.74\.\d+\.\d+|(?:https?://)?[^\s\"']*\.hub(?:[-/]|$)|hub-dev|hub/skills|<media\b|/tmp/visual-page",
    re.IGNORECASE,
)
LOCAL_RESOURCE_ATTRIBUTES = {
    "href": {"link", "script"},
    "src": {"img", "script", "source", "video", "audio", "iframe"},
}
INTERACTIVE_TAGS = {"button", "input", "select", "textarea"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class _PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.elements: list[tuple[str, dict[str, str], str]] = []
        self.text_parts: list[str] = []
        self.style_parts: list[str] = []
        self._stack: list[list[object]] = []
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        normalized = {name.lower(): value or "" for name, value in attrs}
        self.tags.append((tag, normalized))
        if tag in VOID_TAGS:
            self.elements.append((tag, normalized, ""))
        else:
            self._stack.append([tag, normalized, []])
        if tag == "style":
            self._in_style = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] != tag:
                continue
            element_tag, attrs, text = self._stack.pop(index)
            self.elements.append((str(element_tag), attrs, " ".join(str(part) for part in text).strip()))
            break
        if tag == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        for entry in self._stack:
            entry[2].append(data)
        if self._in_style:
            self.style_parts.append(data)

    def finish(self) -> None:
        while self._stack:
            element_tag, attrs, text = self._stack.pop()
            self.elements.append((str(element_tag), attrs, " ".join(str(part) for part in text).strip()))


def _issue(code: str, message: str, severity: str) -> Issue:
    return Issue(code=code, message=message, severity=severity)


def _is_external(value: str) -> bool:
    parsed = urlparse(value)
    if len(value) >= 2 and value[1] == ":" and value[0].isalpha():
        return False
    return bool(
        parsed.scheme
        or parsed.netloc
        or value.startswith(("//", "data:", "#", "mailto:", "tel:", "javascript:"))
    )


def _resource_error(base_dir: Path | None, tag: str, value: str) -> Issue | None:
    if base_dir is None or _is_external(value):
        return None
    clean = value.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean:
        return None
    candidate = (base_dir / clean).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError:
        return _issue("path-outside-prototype", f"{tag} resource escapes prototype directory: {value}", "error")
    if not candidate.is_file():
        return _issue("missing-local-asset", f"{tag} resource does not exist: {value}", "error")
    return None


def _srcset_values(value: str) -> list[str]:
    return [part.strip().split()[0] for part in value.split(",") if part.strip()]


def _css_local_values(styles: str) -> list[str]:
    return [match[1].strip() for match in re.findall(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", styles)]


def validate_html(html: str, *, base_dir: Path | None = None) -> ValidationResult:
    errors: list[Issue] = []
    warnings: list[Issue] = []
    lower = html.lower()
    parser = _PrototypeParser()
    try:
        parser.feed(html)
        parser.finish()
    except Exception as error:
        errors.append(_issue("invalid-html", f"HTML parser failed: {error}", "error"))

    if "<!doctype html" not in lower:
        errors.append(_issue("missing-doctype", "prototype must declare an HTML5 doctype", "error"))
    if not any(tag == "meta" and attrs.get("name", "").lower() == "viewport" for tag, attrs in parser.tags):
        errors.append(_issue("missing-viewport", "prototype must declare a viewport meta tag", "error"))
    internal_match = INTERNAL_PATTERN.search(lower)
    if internal_match:
        errors.append(_issue("internal-only-contract", f"prototype contains internal-only marker: {internal_match.group(0)}", "error"))

    styles = list(parser.style_parts)
    for tag, attrs in parser.tags:
        for attribute, tags in LOCAL_RESOURCE_ATTRIBUTES.items():
            value = attrs.get(attribute)
            if value and tag in tags:
                issue = _resource_error(base_dir, tag, value)
                if issue:
                    errors.append(issue)
                if tag == "link" and "stylesheet" in attrs.get("rel", "").lower().split() and base_dir and not _is_external(value):
                    stylesheet = (base_dir / value).resolve()
                    if stylesheet.is_file():
                        styles.append(stylesheet.read_text(encoding="utf-8", errors="ignore"))
        if attrs.get("srcset"):
            for value in _srcset_values(attrs["srcset"]):
                issue = _resource_error(base_dir, tag, value)
                if issue:
                    errors.append(issue)
        if attrs.get("style"):
            styles.append(attrs["style"])
        if tag == "img" and "alt" not in attrs:
            warnings.append(_issue("missing-alt", "image is missing alternative text", "warning"))

    for value in _css_local_values("\n".join(styles)):
        issue = _resource_error(base_dir, "css", value)
        if issue:
            errors.append(issue)

    ids = {attrs.get("id"): text for tag, attrs, text in parser.elements if attrs.get("id")}
    labels = {attrs.get("for"): text for tag, attrs, text in parser.elements if tag == "label" and attrs.get("for")}
    has_interaction = False
    for tag, attrs, text in parser.elements:
        if tag == "a" or tag in INTERACTIVE_TAGS:
            has_interaction = True
            if tag == "a" and not attrs.get("href"):
                warnings.append(_issue("link-without-href", "anchor has no href", "warning"))
            if tag in INTERACTIVE_TAGS:
                referenced = " ".join(ids.get(value, "") for value in attrs.get("aria-labelledby", "").split())
                accessible = attrs.get("aria-label") or attrs.get("title") or attrs.get("value") or text or referenced
                if tag in {"input", "select", "textarea"}:
                    accessible = accessible or labels.get(attrs.get("id", ""), "")
                if not accessible.strip():
                    warnings.append(_issue("unnamed-control", f"{tag} has no accessible name", "warning"))

    style_text = "\n".join(styles)
    has_motion = bool(re.search(r"\b(animation|transition)\s*:", style_text, re.IGNORECASE))
    if has_interaction and ":focus-visible" not in style_text.lower() and "focus-visible" not in lower:
        warnings.append(_issue("missing-focus-visible", "interactive prototype has no visible focus-visible rule", "warning"))
    if has_motion and "prefers-reduced-motion" not in style_text.lower() and "prefers-reduced-motion" not in lower:
        warnings.append(_issue("missing-reduced-motion", "animated prototype has no reduced-motion fallback", "warning"))
    if re.search(r"\b(item|card|button)[-_ ]?\d+\b|lorem ipsum|placeholder", " ".join(parser.text_parts), re.IGNORECASE):
        warnings.append(_issue("placeholder-content", "prototype contains generic placeholder content", "warning"))

    return ValidationResult(tuple(errors), tuple(warnings))


def validate_file(path: Path) -> ValidationResult:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"prototype file does not exist: {path}")
    return validate_html(path.read_text(encoding="utf-8"), base_dir=path.parent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    try:
        result = validate_file(args.html)
    except (OSError, ValueError) as error:
        print(f"validate failed: {error}", file=sys.stderr)
        return 1
    for issue in (*result.errors, *result.warnings):
        print(f"{issue.severity}: {issue.code}: {issue.message}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
