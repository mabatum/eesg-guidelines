from __future__ import annotations

import os
import shutil
from pathlib import Path
from urllib.parse import unquote

import requests

API_BASE = "https://api.wiki.yandex.net/v1"
ROOT_SLUG = os.environ.get("ROOT_SLUG", "eesg").strip("/")
WIKI_TOKEN = os.environ.get("WIKI_TOKEN")
ORG_ID = os.environ.get("ORG_ID")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "docs/gen_docs"))


def require_env() -> None:
    missing = [name for name, value in {"WIKI_TOKEN": WIKI_TOKEN, "ORG_ID": ORG_ID}.items() if not value]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"OAuth {WIKI_TOKEN}",
            "X-Org-Id": ORG_ID,
            "Accept": "application/json",
        }
    )
    return s


def get_descendants(s: requests.Session) -> list[dict]:
    pages: list[dict] = []
    cursor: str | None = None

    while True:
        params = {
            "slug": ROOT_SLUG,
            "include_self": "true",
            "page_size": 100,
        }
        if cursor:
            params["cursor"] = cursor

        response = s.get(f"{API_BASE}/pages/descendants", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        pages.extend(payload.get("results", []))
        cursor = payload.get("next_cursor")
        if not cursor:
            break

    return pages


def get_page(s: requests.Session, slug: str) -> dict:
    response = s.get(
        f"{API_BASE}/pages",
        params={"slug": slug, "fields": "content,attributes,breadcrumbs"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def safe_relative_parts(slug: str) -> list[str]:
    normalized = unquote(slug.strip("/"))
    root = unquote(ROOT_SLUG)

    if normalized == root:
        return []
    prefix = f"{root}/"
    if not normalized.startswith(prefix):
        raise ValueError(f"Slug is outside root subtree: {slug}")

    parts = normalized[len(prefix) :].split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe slug: {slug}")
    return parts


def destination_for(slug: str) -> Path:
    parts = safe_relative_parts(slug)
    return OUTPUT_DIR.joinpath(*parts, "index.md") if parts else OUTPUT_DIR / "index.md"


def export() -> None:
    require_env()
    s = session()
    subtree = get_descendants(s)
    if not subtree:
        raise SystemExit(f"No pages returned for root slug '{ROOT_SLUG}'")

    tmp_dir = OUTPUT_DIR.with_name(f"{OUTPUT_DIR.name}.tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    original_output = OUTPUT_DIR
    exported = 0
    skipped_drafts = 0

    try:
        globals()["OUTPUT_DIR"] = tmp_dir
        for item in sorted(subtree, key=lambda p: p.get("slug", "")):
            slug = item.get("slug")
            if not slug:
                continue

            page = get_page(s, slug)
            attributes = page.get("attributes") or {}
            if attributes.get("is_draft"):
                skipped_drafts += 1
                continue

            title = page.get("title") or slug
            content = page.get("content") or ""
            destination = destination_for(slug)
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Preserve Yandex Flavored Markdown as-is; Diplodoc understands YFM.
            if not content.lstrip().startswith("#"):
                content = f"# {title}\n\n{content}"
            destination.write_text(content.rstrip() + "\n", encoding="utf-8")
            exported += 1

        globals()["OUTPUT_DIR"] = original_output
        if original_output.exists():
            shutil.rmtree(original_output)
        tmp_dir.rename(original_output)
    finally:
        globals()["OUTPUT_DIR"] = original_output
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

    print(f"Exported {exported} pages from '{ROOT_SLUG}'. Skipped drafts: {skipped_drafts}.")


if __name__ == "__main__":
    export()
