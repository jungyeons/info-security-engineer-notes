#!/usr/bin/env python3
"""Validate local Markdown links and README coverage for numbered notes."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
NUMBERED_NOTE_PATTERN = re.compile(r"\d{2}-.+\.md")


def extract_destination(raw_destination: str) -> str:
    """Remove an optional Markdown link title from a destination."""
    value = raw_destination.strip()
    if value.startswith("<"):
        closing_bracket = value.find(">")
        return value[1:closing_bracket] if closing_bracket != -1 else value[1:]
    return value.split(maxsplit=1)[0] if value else ""


def local_path(markdown_file: Path, destination: str) -> Optional[Path]:
    """Resolve a local link destination, ignoring web and in-page links."""
    if not destination or destination.startswith(("#", "/")):
        return None

    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None

    return (markdown_file.parent / unquote(parsed.path)).resolve()


def main() -> int:
    markdown_files = sorted(ROOT.rglob("*.md"))
    readme = ROOT / "README.md"
    errors: list[str] = []
    local_link_count = 0

    for markdown_file in markdown_files:
        contents = markdown_file.read_text(encoding="utf-8")
        for line_number, line in enumerate(contents.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                destination = extract_destination(match.group(1))
                target = local_path(markdown_file, destination)
                if target is None:
                    continue

                local_link_count += 1
                try:
                    target.relative_to(ROOT)
                except ValueError:
                    errors.append(
                        f"{markdown_file.relative_to(ROOT)}:{line_number}: "
                        f"link points outside the repository: {destination}"
                    )
                    continue

                if not target.exists():
                    errors.append(
                        f"{markdown_file.relative_to(ROOT)}:{line_number}: "
                        f"missing link target: {destination}"
                    )

    numbered_notes = sorted(
        path.name
        for path in ROOT.glob("*.md")
        if NUMBERED_NOTE_PATTERN.fullmatch(path.name)
    )
    readme_contents = readme.read_text(encoding="utf-8")
    readme_targets = {
        Path(unquote(urlsplit(extract_destination(match.group(1))).path)).name
        for match in LINK_PATTERN.finditer(readme_contents)
    }
    for note in numbered_notes:
        if note not in readme_targets:
            errors.append(f"README.md: numbered note is missing from the file table: {note}")

    if errors:
        print("Markdown validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"OK: checked {len(markdown_files)} Markdown files, "
        f"{local_link_count} local links, and {len(numbered_notes)} numbered notes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
