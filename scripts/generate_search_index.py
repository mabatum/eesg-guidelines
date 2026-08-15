from __future__ import annotations

import json
import re
from pathlib import Path

CONTENT_ROOT = Path("docs/gen_docs")
OUTPUT = Path("docs/_assets/script/search-index.js")
H1_RE = re.compile(r"^#\s+(.+?)\s*$")


def extract_title(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = H1_RE.match(line)
        if match:
            title = match.group(1).strip()
            # Strip a trailing explicit YFM/GitHub anchor if present.
            title = re.sub(r"\s+\{#[^}]+\}\s*$", "", title).strip()
            return title or None
    return None


def page_url(path: Path) -> str:
    """Return the URL produced by Diplodoc for a page from the included gen_docs TOC.

    Diplodoc merges docs/gen_docs/toc.yaml into the project TOC and publishes those
    pages at the site root (for example soft-tissue-sarcomas/... rather than
    gen_docs/soft-tissue-sarcomas/...).
    """
    relative = path.relative_to(CONTENT_ROOT)
    return relative.as_posix().removesuffix(".md") + ".html"


def parent_titles(path: Path, titles_by_dir: dict[Path, str]) -> list[str]:
    result: list[str] = []
    current = path.parent.parent
    while current != CONTENT_ROOT.parent and CONTENT_ROOT in [current, *current.parents]:
        if current == CONTENT_ROOT:
            break
        title = titles_by_dir.get(current)
        if title:
            result.append(title)
        current = current.parent
    result.reverse()
    return result


def main() -> None:
    pages = sorted(CONTENT_ROOT.rglob("index.md"))
    if not pages:
        raise SystemExit(f"No generated pages found under {CONTENT_ROOT}")

    titles_by_dir: dict[Path, str] = {}
    for path in pages:
        title = extract_title(path)
        if title:
            titles_by_dir[path.parent] = title

    records: list[dict] = []
    for path in pages:
        title = titles_by_dir.get(path.parent)
        if not title:
            continue
        breadcrumbs = parent_titles(path, titles_by_dir)
        records.append(
            {
                "title": title,
                "url": page_url(path),
                "breadcrumbs": breadcrumbs,
            }
        )

    # Stable, human-friendly ordering; ranking is handled in the browser.
    records.sort(key=lambda item: (item["title"].casefold(), item["url"]))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(
        "/* Generated from page titles only. Do not edit manually. */\n"
        f"window.EESG_SEARCH_INDEX={payload};\n",
        encoding="utf-8",
    )
    print(f"Generated title-only search index with {len(records)} entries: {OUTPUT}")


if __name__ == "__main__":
    main()
