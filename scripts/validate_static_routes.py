from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

STATIC_ROOT = Path("docs-html").resolve()
SEARCH_INDEX = Path("docs/_assets/script/search-index-v2.js")
UPDATES = Path("docs/updates.md")
HOME = STATIC_ROOT / "index.html"

INDEX_RE = re.compile(r"window\.EESG_SEARCH_INDEX=(\[.*\]);\s*$", re.DOTALL)
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<url>[^)]+)\)")


def static_target(raw_url: str) -> Path | None:
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path.lstrip("/")
    if not path:
        return STATIC_ROOT / "index.html"
    if ".." in Path(path).parts:
        raise ValueError(f"unsafe relative URL: {raw_url}")

    target = STATIC_ROOT / path
    if path.endswith("/"):
        target = target / "index.html"
    return target


def main() -> int:
    errors: list[str] = []

    if not STATIC_ROOT.exists():
        errors.append(f"Static build directory does not exist: {STATIC_ROOT}")

    if not HOME.exists():
        errors.append(f"Built homepage does not exist: {HOME}")
    else:
        home_html = HOME.read_text(encoding="utf-8")
        for marker in ("Основные разделы", "Недавно обновлено"):
            if marker not in home_html:
                errors.append(
                    f"Homepage portal block was not rendered into index.html: missing {marker!r}"
                )

    if not SEARCH_INDEX.exists():
        errors.append(f"Missing search index: {SEARCH_INDEX}")
    else:
        text = SEARCH_INDEX.read_text(encoding="utf-8")
        match = INDEX_RE.search(text)
        if not match:
            errors.append("Could not parse EESG search index payload")
        else:
            records = json.loads(match.group(1))
            for item in records:
                url = str(item.get("url") or "")
                title = str(item.get("title") or "<untitled>")
                if url.startswith("gen_docs/") or "/gen_docs/" in url:
                    errors.append(f"Search URL still contains gen_docs: {title} -> {url}")
                    continue
                try:
                    target = static_target(url)
                except ValueError as exc:
                    errors.append(f"Search URL invalid: {title} -> {exc}")
                    continue
                if target is not None and not target.exists():
                    errors.append(f"Search target missing: {title} -> {url} ({target})")

    if UPDATES.exists():
        text = UPDATES.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(text):
            url = match.group("url").strip()
            if url.startswith("http") or url.startswith("mailto:") or url.startswith("#"):
                continue
            if "gen_docs/" in url:
                errors.append(f"Updates URL still contains gen_docs: {url}")
                continue
            try:
                target = static_target(url)
            except ValueError as exc:
                errors.append(f"Updates URL invalid: {exc}")
                continue
            if target is not None and not target.exists():
                errors.append(f"Updates target missing: {url} ({target})")

    if errors:
        print("Static route/render validation errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"Static validation failed with {len(errors)} error(s).")
        return 1

    print(
        "Static validation passed: homepage portal blocks are rendered and "
        "search/updates links resolve to built files."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
