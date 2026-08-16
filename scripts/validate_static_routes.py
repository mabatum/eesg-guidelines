from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

STATIC_ROOT = Path("docs-html").resolve()
SEARCH_INDEX = Path("docs/_assets/script/search-index-v3.js")
UPDATES = Path("docs/updates.md")
TOC = Path("docs/toc.yaml")
BUILT_TOC = STATIC_ROOT / "toc.js"
HOME = STATIC_ROOT / "index.html"
LMS_PAGE = STATIC_ROOT / "soft-tissue-sarcomas/leiomyosarcoma/index.html"

INDEX_RE = re.compile(r"window\.EESG_SEARCH_INDEX=(\[.*\]);\s*$", re.DOTALL)
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<url>[^)]+)\)")
TOC_URL_RE = re.compile(r"^\s*url:\s*['\"]?(?P<url>[^'\"\s]+)['\"]?\s*$", re.MULTILINE)


def static_target(raw_url: str) -> Path | None:
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path.lstrip("/")
    if path in {"", ".", "./"}:
        return STATIC_ROOT / "index.html"
    if ".." in Path(path).parts:
        raise ValueError(f"unsafe relative URL: {raw_url}")

    target = STATIC_ROOT / path
    if path.endswith("/"):
        target = target / "index.html"
    return target


def validate_local_url(errors: list[str], label: str, url: str) -> None:
    if url.startswith("http") or url.startswith("mailto:") or url.startswith("#"):
        return
    if url.startswith("gen_docs/") or "/gen_docs/" in url:
        errors.append(f"{label} still contains internal gen_docs path: {url}")
        return
    try:
        target = static_target(url)
    except ValueError as exc:
        errors.append(f"{label} invalid: {exc}")
        return
    if target is not None and not target.exists():
        errors.append(f"{label} target missing: {url} ({target})")


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
        for asset in (
            "_assets/script/header-nav-v1.js",
            "_assets/script/search-index-v3.js",
            "_assets/script/title-search-v3.js",
        ):
            if asset not in home_html:
                errors.append(f"Built homepage is missing required UI asset: {asset}")

    if not LMS_PAGE.exists():
        errors.append(f"Reference internal clinical page is missing: {LMS_PAGE}")
    else:
        lms_html = LMS_PAGE.read_text(encoding="utf-8")
        for asset in (
            "_assets/style/internal-page-v2.css",
            "_assets/script/internal-page-v2.js",
        ):
            if asset not in lms_html:
                errors.append(f"Reference clinical page is missing UX asset: {asset}")
        for marker in ("Структура раздела", "Литература", '"headings":['):
            if marker not in lms_html:
                errors.append(f"Reference clinical page lost expected structured content: {marker!r}")
        for obsolete_label in (
            "&gt;Ссылка&lt;/a&gt;",
            "&gt;Полный текст&lt;/a&gt;",
            "&gt;PubMed&lt;/a&gt;",
        ):
            if obsolete_label in lms_html:
                errors.append(
                    f"Reference clinical page still exposes a service bibliography label: {obsolete_label}"
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
            by_url = {str(item.get("url") or ""): item for item in records}
            for item in records:
                url = str(item.get("url") or "")
                title = str(item.get("title") or "<untitled>")
                validate_local_url(errors, f"Search URL for {title}", url)

            expected_aliases = {
                "soft-tissue-sarcomas/leiomyosarcoma/index.html": "LMS",
                "specific-tumor-groups/gist/index.html": "GIST",
                "specific-tumor-groups/dfsp/index.html": "DFSP",
            }
            for url, alias in expected_aliases.items():
                record = by_url.get(url)
                aliases = {str(value).casefold() for value in (record or {}).get("aliases", [])}
                if alias.casefold() not in aliases:
                    errors.append(f"Search index lost expected alias {alias!r} for {url}")

    if UPDATES.exists():
        text = UPDATES.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(text):
            validate_local_url(errors, "Updates URL", match.group("url").strip())

    if not TOC.exists():
        errors.append(f"Missing site TOC/navigation config: {TOC}")
    else:
        text = TOC.read_text(encoding="utf-8")
        for match in TOC_URL_RE.finditer(text):
            validate_local_url(errors, "Navigation URL", match.group("url").strip())

    if not BUILT_TOC.exists():
        errors.append(f"Built navigation payload is missing: {BUILT_TOC}")
    else:
        built_toc = BUILT_TOC.read_text(encoding="utf-8")
        if '"text":"Рекомендации","url":"./index.html#osnovnye-razdely"' not in built_toc:
            errors.append("Built toc.js does not contain the canonical Recommendations URL")
        if '"text":"О проекте","url":"./about/"' not in built_toc:
            errors.append("Built toc.js does not contain the canonical About URL")
        if '"url":"./gen_docs/' in built_toc or '"url":"gen_docs/' in built_toc:
            errors.append("Built toc.js still exposes internal gen_docs navigation URLs")

    if errors:
        print("Static route/render validation errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"Static validation failed with {len(errors)} error(s).")
        return 1

    print(
        "Static validation passed: alias-aware search v3 is present, expected clinical aliases resolve, "
        "bibliography service labels are normalized, internal clinical UX assets are present, "
        "header navigation is canonical, and routes resolve."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
