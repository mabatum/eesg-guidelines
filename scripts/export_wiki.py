from __future__ import annotations

import json
import os
import posixpath
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

API_BASE = "https://api.wiki.yandex.net/v1"
ROOT_SLUG = os.environ.get("ROOT_SLUG", "eesg").strip("/")
WIKI_TOKEN = os.environ.get("WIKI_TOKEN")
ORG_ID = os.environ.get("ORG_ID")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "docs/gen_docs"))
DEFAULT_PUBLICATION_STATUS = os.environ.get("PUBLICATION_STATUS", "Тестовая версия")

MARKDOWN_LINK_RE = re.compile(
    r"(?P<prefix>\]\()"
    r"(?P<url>(?:https://wiki\.yandex\.ru)?/eesg(?:/[^\s)#?]*)?)"
    r"(?P<suffix>[?#][^\s)]*)?"
    r"(?P<close>\))"
)

RECOMMENDATION_HEADING_RE = re.compile(
    r"^(?P<marks>#{2,4})\s+(?P<title>(?:Клиническая\s+)?Рекомендация(?:\s+\d+(?:\.\d+)*)?)\s*$",
    re.IGNORECASE,
)
ANY_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+.+$")

TOP_LEVEL_ORDER = {
    f"{ROOT_SLUG}/general-principles": 10,
    f"{ROOT_SLUG}/soft-tissue-sarcomas": 20,
    f"{ROOT_SLUG}/bone-sarcomas": 30,
    f"{ROOT_SLUG}/specific-tumor-groups": 40,
    f"{ROOT_SLUG}/drugs-and-regimens": 50,
    f"{ROOT_SLUG}/special-clinical-situations": 60,
    f"{ROOT_SLUG}/about": 900,
    f"{ROOT_SLUG}/editorial-standard": 910,
    f"{ROOT_SLUG}/materials-map": 920,
}

HIDDEN_TOP_LEVEL = {
    f"{ROOT_SLUG}/about",
    f"{ROOT_SLUG}/editorial-standard",
    f"{ROOT_SLUG}/materials-map",
}


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


def render_recommendation_blocks(content: str) -> tuple[str, int]:
    """Render explicitly structured Wiki recommendation sections as Diplodoc callouts."""
    lines = content.splitlines()
    output: list[str] = []
    converted = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = RECOMMENDATION_HEADING_RE.match(stripped)
        if not match:
            output.append(lines[i])
            i += 1
            continue

        level = len(match.group("marks"))
        j = i + 1
        while j < len(lines):
            heading = ANY_HEADING_RE.match(lines[j].strip())
            if heading and len(heading.group("marks")) <= level:
                break
            j += 1

        body = "\n".join(lines[i + 1 : j]).strip()
        if not body:
            output.append(lines[i])
            i += 1
            continue

        title = match.group("title")
        output.extend(
            [
                f'{{% note tip "{title}" %}}',
                "",
                body,
                "",
                "{% endnote %}",
            ]
        )
        converted += 1
        i = j

    return "\n".join(output), converted


def keyword_value(attributes: dict, prefixes: tuple[str, ...]) -> str | None:
    for raw in attributes.get("keywords") or []:
        text = str(raw).strip()
        folded = text.casefold()
        for prefix in prefixes:
            if folded.startswith(prefix.casefold()):
                value = text[len(prefix) :].strip()
                if value:
                    return value
    return None


def format_modified_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y")
    except ValueError:
        return None


def inject_publication_metadata(content: str, attributes: dict) -> str:
    """Add a compact publication line after H1 using reliable Wiki metadata.

    Optional Wiki page keywords can override/add fields:
      status:<value> or статус:<value>
      version:<value> or версия:<value>
      review:<value> or пересмотр:<value>
      group:<value> or рабочая-группа:<value>
    """
    status = keyword_value(attributes, ("status:", "статус:")) or DEFAULT_PUBLICATION_STATUS
    version = keyword_value(attributes, ("version:", "версия:"))
    review = keyword_value(attributes, ("review:", "пересмотр:"))
    group = keyword_value(attributes, ("group:", "рабочая-группа:"))
    modified = format_modified_date(attributes.get("modified_at"))

    fields = [f"**Статус:** {status}"]
    if version:
        fields.append(f"**Версия:** {version}")
    if modified:
        fields.append(f"**Обновлено:** {modified}")
    if review:
        fields.append(f"**Следующий пересмотр:** {review}")
    if group:
        fields.append(f"**Рабочая группа:** {group}")

    metadata = " · ".join(fields)
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            lines[idx + 1 : idx + 1] = ["", metadata, ""]
            return "\n".join(lines)
    return content


def yaml_string(value: str) -> str:
    """JSON strings are valid YAML strings and keep Cyrillic readable."""
    return json.dumps(value, ensure_ascii=False)


def toc_href(slug: str) -> str:
    parts = safe_relative_parts(slug)
    return posixpath.join(*parts, "index.md") if parts else "index.md"


def write_toc(records: list[dict]) -> None:
    """Create a clinical-first Diplodoc TOC using Wiki page titles."""
    by_slug = {record["slug"]: record for record in records}
    root = by_slug.get(ROOT_SLUG)
    if not root:
        raise SystemExit(f"Root page '{ROOT_SLUG}' was not exported, cannot create TOC")

    children: dict[str, list[str]] = {slug: [] for slug in by_slug}
    for slug in by_slug:
        if slug == ROOT_SLUG:
            continue
        parent = slug.rsplit("/", 1)[0]
        while parent not in by_slug and parent != ROOT_SLUG:
            parent = parent.rsplit("/", 1)[0] if "/" in parent else ROOT_SLUG
        if parent not in by_slug:
            parent = ROOT_SLUG
        children.setdefault(parent, []).append(slug)

    for parent, siblings in children.items():
        if parent == ROOT_SLUG:
            siblings.sort(
                key=lambda slug: (
                    TOP_LEVEL_ORDER.get(slug, 500),
                    by_slug[slug]["title"].casefold(),
                    slug,
                )
            )
        else:
            siblings.sort(key=lambda slug: (by_slug[slug]["title"].casefold(), slug))

    lines = [
        f"title: {yaml_string(root['title'])}",
        "href: index.md",
    ]

    def render(slug: str, indent: int) -> None:
        record = by_slug[slug]
        prefix = " " * indent
        lines.append(f"{prefix}- name: {yaml_string(record['title'])}")
        lines.append(f"{prefix}  href: {yaml_string(toc_href(slug))}")
        nested = children.get(slug, [])
        if indent == 2 and slug in HIDDEN_TOP_LEVEL:
            lines.append(f"{prefix}  hidden: true")
        if indent == 2 and nested:
            lines.append(f"{prefix}  expanded: false")
        if nested:
            lines.append(f"{prefix}  items:")
            for child in nested:
                render(child, indent + 4)

    top_level = children.get(ROOT_SLUG, [])
    if top_level:
        lines.append("items:")
        for slug in top_level:
            render(slug, 2)

    (OUTPUT_DIR / "toc.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    recommendation_blocks = 0
    records: list[dict] = []

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
            content, count = render_recommendation_blocks(content)
            recommendation_blocks += count

            if not content.lstrip().startswith("#"):
                content = f"# {title}\n\n{content}"
            content = inject_publication_metadata(content, attributes)

            destination = destination_for(slug)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content.rstrip() + "\n", encoding="utf-8")
            records.append({"slug": slug, "title": title})
            exported += 1

        write_toc(records)

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
        f"Skipped drafts: {skipped_drafts}. Rewritten internal links: {rewritten_links}. "
        f"Rendered recommendation blocks: {recommendation_blocks}. "
        "Generated clinical-first navigation and publication metadata."
    )


if __name__ == "__main__":
    export()
