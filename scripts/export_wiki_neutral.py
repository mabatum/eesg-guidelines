"""Neutral EESG Wiki export.

Keeps clinical page text structurally unchanged. The legacy recommendation-callout
converter remains available in export_wiki.py for a possible future editorial phase,
but is explicitly disabled in the production pipeline for now.

Production-specific resilience:
- retry/skip descendants that disappear during a Wiki move;
- rewrite known old Wiki slugs to their new locations before public links are built.
"""

import json
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import export_wiki


ROUTE_ALIASES_FILE = Path("config/wiki-route-aliases.json")
_ORIGINAL_RELATIVE_INTERNAL_LINK = export_wiki.relative_internal_link


def passthrough(content: str) -> tuple[str, int]:
    return content, 0


def load_route_aliases() -> dict[str, str]:
    if not ROUTE_ALIASES_FILE.exists():
        return {}
    raw = json.loads(ROUTE_ALIASES_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"Wiki route aliases must be an object: {ROUTE_ALIASES_FILE}")

    aliases: dict[str, str] = {}
    for old, new in raw.items():
        if not isinstance(old, str) or not isinstance(new, str):
            raise SystemExit(f"Invalid Wiki route alias: {old!r} -> {new!r}")
        old_slug = unquote(old.strip("/"))
        new_slug = unquote(new.strip("/"))
        if not old_slug.startswith(f"{export_wiki.ROOT_SLUG}/"):
            raise SystemExit(f"Old Wiki route is outside export root: {old}")
        if not new_slug.startswith(f"{export_wiki.ROOT_SLUG}/"):
            raise SystemExit(f"New Wiki route is outside export root: {new}")
        aliases[old_slug] = new_slug
    return aliases


ROUTE_ALIASES = load_route_aliases()


def resolve_moved_slug(slug: str) -> str:
    normalized = unquote(slug.strip("/"))
    for old_prefix in sorted(ROUTE_ALIASES, key=len, reverse=True):
        if normalized == old_prefix or normalized.startswith(old_prefix + "/"):
            suffix = normalized[len(old_prefix):]
            return ROUTE_ALIASES[old_prefix] + suffix
    return normalized


def moved_route_internal_link(current_slug: str, raw_url: str, suffix: str = "") -> str:
    path = urlsplit(raw_url).path if raw_url.startswith("http") else raw_url
    target_slug = unquote(path.strip("/"))
    resolved = resolve_moved_slug(target_slug)
    if resolved != target_slug:
        raw_url = "/" + resolved
    return _ORIGINAL_RELATIVE_INTERNAL_LINK(current_slug, raw_url, suffix)


def tolerant_get_page(session, slug: str) -> dict:
    for attempt in range(1, 4):
        response = session.get(
            f"{export_wiki.API_BASE}/pages",
            params={"slug": slug, "fields": "content,attributes,breadcrumbs"},
            timeout=30,
        )
        if response.ok:
            return response.json()
        if response.status_code != 404:
            raise SystemExit(
                f"Yandex Wiki API request failed: HTTP {response.status_code} "
                f"for {response.url}\n{export_wiki.error_text(response)}"
            )
        if attempt < 3:
            print(f"WARNING Wiki page returned 404, retrying ({attempt}/3): {slug}")
            time.sleep(1.5)

    print(
        "WARNING Wiki descendants snapshot contains a page that no longer resolves; "
        f"skipping stale descendant: {slug}"
    )
    return {
        "title": slug.rsplit("/", 1)[-1],
        "content": "",
        "attributes": {"is_draft": True, "_stale_missing": True},
    }


if __name__ == "__main__":
    if ROUTE_ALIASES:
        print(f"Loaded {len(ROUTE_ALIASES)} Wiki route alias(es) for moved pages.")
    export_wiki.render_recommendation_blocks = passthrough
    export_wiki.relative_internal_link = moved_route_internal_link
    export_wiki.get_page = tolerant_get_page
    export_wiki.export()
