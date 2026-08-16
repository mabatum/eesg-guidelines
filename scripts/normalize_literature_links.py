from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("docs/gen_docs")
SERVICE_LABELS = r"(?:Ссылка|Полный текст|PubMed|DOI|Full text|Источник)"
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
ITEM_RE = re.compile(
    rf"^(?P<prefix>\s*(?:\d+[.)]|[-*+])\s+)"
    rf"(?P<body>.+?)\s+"
    rf"\[(?P<label>{SERVICE_LABELS})\]\((?P<url>https?://[^)]+)\)"
    rf"(?P<trail>[.,;:]?)\s*$",
    re.IGNORECASE,
)


def is_literature_heading(title: str) -> bool:
    normalized = title.strip().casefold()
    return normalized in {"литература", "список литературы", "источники"}


def normalize_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    changed = 0
    section_level: int | None = None

    for i, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group("marks"))
            title = heading.group("title")
            if section_level is None:
                if is_literature_heading(title):
                    section_level = level
            elif level <= section_level:
                section_level = None
                if is_literature_heading(title):
                    section_level = level
            continue

        if section_level is None:
            continue

        match = ITEM_RE.match(line)
        if not match:
            continue

        body = match.group("body").rstrip()
        # Do not create nested Markdown links. Non-standard entries are left untouched.
        if re.search(r"\[[^\]]+\]\([^)]+\)", body):
            continue

        url = match.group("url")
        trail = match.group("trail")
        # The bibliography itself becomes the link; the service label disappears.
        # Preserve a trailing punctuation mark only if the citation does not already end with one.
        suffix = ""
        if trail and not re.search(r"[.!?;:]$", body):
            suffix = trail
        lines[i] = f"{match.group('prefix')}[{body}]({url}){suffix}"
        changed += 1

    if changed:
        final = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        path.write_text(final, encoding="utf-8")
    return changed


def main() -> None:
    total = 0
    files = 0
    for path in sorted(ROOT.rglob("*.md")):
        count = normalize_file(path)
        if count:
            files += 1
            total += count
            print(f"Normalized literature links: {path} ({count})")
    print(f"Literature link normalization complete: {total} reference(s) across {files} file(s).")


if __name__ == "__main__":
    main()
