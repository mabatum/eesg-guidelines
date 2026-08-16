from __future__ import annotations

import json
import re
from pathlib import Path

CONTENT_ROOT = Path("docs/gen_docs")
ALIASES_FILE = Path("config/search-aliases.json")
OUTPUT = Path("docs/_assets/script/search-index-v3.js")
H1_RE = re.compile(r"^#\s+(.+?)\s*$")
PAREN_RE = re.compile(r"\(([^()]+)\)")
ACRONYM_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9+./-]{2,12}$")


def extract_title(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = H1_RE.match(line)
        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s+\{#[^}]+\}\s*$", "", title).strip()
            return title or None
    return None


def page_url(path: Path) -> str:
    """Return the URL produced by Diplodoc for a page from the included gen_docs TOC."""
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


def load_aliases() -> dict[str, list[str]]:
    if not ALIASES_FILE.exists():
        return {}
    raw = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"Search aliases file must contain an object: {ALIASES_FILE}")

    result: dict[str, list[str]] = {}
    for url, values in raw.items():
        if not isinstance(url, str) or not isinstance(values, list):
            raise SystemExit(f"Invalid alias entry in {ALIASES_FILE}: {url!r}")
        clean = [str(value).strip() for value in values if str(value).strip()]
        result[url.lstrip("/")] = clean
    return result


def automatic_aliases(title: str) -> list[str]:
    """Extract explicit short acronyms from title parentheses, e.g. (ГИСО), (ДФСП)."""
    aliases: list[str] = []
    for match in PAREN_RE.finditer(title):
        candidate = match.group(1).strip()
        if ACRONYM_RE.fullmatch(candidate):
            aliases.append(candidate)
    return aliases


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def main() -> None:
    pages = sorted(CONTENT_ROOT.rglob("index.md"))
    if not pages:
        raise SystemExit(f"No generated pages found under {CONTENT_ROOT}")

    manual_aliases = load_aliases()
    titles_by_dir: dict[Path, str] = {}
    for path in pages:
        title = extract_title(path)
        if title:
            titles_by_dir[path.parent] = title

    records: list[dict] = []
    known_urls: set[str] = set()
    for path in pages:
        title = titles_by_dir.get(path.parent)
        if not title:
            continue
        url = page_url(path)
        known_urls.add(url)
        aliases = dedupe(automatic_aliases(title) + manual_aliases.get(url, []))
        record = {
            "title": title,
            "url": url,
            "breadcrumbs": parent_titles(path, titles_by_dir),
        }
        if aliases:
            record["aliases"] = aliases
        records.append(record)

    unknown_alias_targets = sorted(set(manual_aliases) - known_urls)
    if unknown_alias_targets:
        raise SystemExit(
            "Search alias config points to missing public page(s): "
            + ", ".join(unknown_alias_targets)
        )

    records.sort(key=lambda item: (item["title"].casefold(), item["url"]))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    alias_count = sum(len(item.get("aliases", [])) for item in records)
    OUTPUT.write_text(
        "/* Generated from page titles, breadcrumbs and curated aliases only. No body text is indexed. */\n"
        f"window.EESG_SEARCH_INDEX={payload};\n",
        encoding="utf-8",
    )
    print(
        f"Generated title/alias search index with {len(records)} entries and "
        f"{alias_count} aliases: {OUTPUT}"
    )


if __name__ == "__main__":
    main()
