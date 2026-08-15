from __future__ import annotations

import os
import posixpath
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

API_BASE = "https://api.wiki.yandex.net/v1"
ROOT_SLUG = os.environ.get("ROOT_SLUG", "eesg").strip("/")
WIKI_TOKEN = os.environ.get("WIKI_TOKEN")
ORG_ID = os.environ.get("ORG_ID")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "docs/gen_docs"))

MARKDOWN_LINK_RE = re.compile(
    r"(?P<prefix>\]\()"
    r"(?P<url>(?:https://wiki\.yandex\.ru)?/eesg(?:/[^\s)#?]*)?)"
    r"(?P<suffix>[?#][^\s)]*)?"
    r"(?P<close>\))"
)


def require_env() -> None:
    missing = [name for name, value in {"WIKI_TOKEN": WIKI_TOKEN, "ORG_ID": ORG_ID}.items() if not value]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")


def error_text(response: requests.Response) -> str:
    text = (response.text or "").strip().replace("\n", " ")
    return text[:1000] if text else "<empty response body>"


def make_session(org_header: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"OAuth {WIKI_TOKEN}",
            org_header: ORG_ID,
            "Accept": "application/json",
        }
    )
    return s


def authenticated_session() -> requests.Session:
    """Detect whether this Wiki belongs to Yandex 360 or Identity Hub."""
    attempts: list[str] = []
    for org_header in ("X-Org-Id", "X-Cloud-Org-Id"):
        s = make_session(org_header)
        response = s.get(
            f"{API_BASE}/pages",
            params={"slug": ROOT_SLUG},
            timeout=30,
        )
        if response.status_code == 200:
            page = response.json()
            print(
                f"Wiki API access OK using {org_header}. "
                f"Root page: {page.get('title', ROOT_SLUG)!r} (id={page.get('id')})."
            )
            return s
        attempts.append(f"{org_header}: HTTP {response.status_code}: {error_text(response)}")

    raise SystemExit(
        "Unable to access the root Wiki page with either supported organization header.\n"
        + "\n".join(attempts)
        + "\nCheck that the OAuth token belongs to a user who can open the root page, "
          "that wiki:read was granted, and that Wiki API access is enabled by the administrator."
    )


def checked_get(s: requests.Session, url: str, **kwargs) -> requests.Response:
    response = s.get(url, **kwargs)
    if not response.ok:
        raise SystemExit(
            f"Yandex Wiki API request failed: HTTP {response.status_code} "
            f"for {response.url}\n{error_text(response)}"
        )
    return response


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

        response = checked_get(
            s,
            f"{API_BASE}/pages/descendants",
            params=params,
            timeout=30,
        )
        payload = response.json()
        pages.extend(payload.get("results", []))
        cursor = payload.get("next_cursor")
        if not cursor:
            break

    return pages


def get_page(s: requests.Session, slug: str) -> dict:
    response = checked_get(
        s,
        f"{API_BASE}/pages",
        params={"slug": slug, "fields": "content,attributes,breadcrumbs"},
        timeout=30,
    )
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


def relative_internal_link(current_slug: str, raw_url: str, suffix: str = "") -> str:
    path = urlsplit(raw_url).path if raw_url.startswith("http") else raw_url
    target_slug = unquote(path.strip("/"))
    target_parts = safe_relative_parts(target_slug)
    current_parts = safe_relative_parts(current_slug)

    target = posixpath.join(*target_parts, "index.md") if target_parts else "index.md"
    start = posixpath.join(*current_parts) if current_parts else "."
    relative = posixpath.relpath(target, start=start)
    return relative + suffix


def rewrite_internal_links(content: str, current_slug: str) -> tuple[str, int]:
    rewritten = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal rewritten
        try:
            target = relative_internal_link(
                current_slug,
                match.group("url"),
                match.group("suffix") or "",
            )
        except ValueError:
            return match.group(0)
        rewritten += 1
        return f"{match.group('prefix')}{target}{match.group('close')}"

    return MARKDOWN_LINK_RE.sub(repl, content), rewritten


def export() -> None:
    require_env()
    s = authenticated_session()
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
    rewritten_links = 0

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
            content, count = rewrite_internal_links(content, slug)
            rewritten_links += count
            destination = destination_for(slug)
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Preserve Yandex Flavored Markdown; only internal Wiki links are normalized.
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

    print(
        f"Exported {exported} pages from '{ROOT_SLUG}'. "
        f"Skipped drafts: {skipped_drafts}. Rewritten internal links: {rewritten_links}."
    )


if __name__ == "__main__":
    export()
