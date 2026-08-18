"""Проверка собранного сайта.

Контракт после сужения области: на сайте есть только разделы из
config/site-scope.json. Прочие ветки не должны присутствовать ни в навигации,
ни в поиске, ни в каталоге сборки — раньше они прятались, но оставались
доступными по прямой ссылке.
"""

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
GUIDELINES_TOC = Path("docs/gen_docs/toc.yaml")
BUILT_TOC = STATIC_ROOT / "toc.js"
HOME = STATIC_ROOT / "index.html"
SCOPE_FILE = Path("config/site-scope.json")
REFERENCE_PAGE = STATIC_ROOT / "bone-sarcomas/osteosarcoma-adults/index.html"

PUBLIC_GUIDELINE_NAMES = (
    "Общие принципы ведения пациентов с саркомами",
    "Саркомы костей",
)

EXPECTED_HEADER_LINKS = {
    "Общие принципы": "./general-principles/",
    "Саркомы костей": "./bone-sarcomas/",
    "Обновления": "./updates.html",
}

REQUIRED_HOME_ASSETS = (
    "_assets/script/search-index-v3.js",
    "_assets/script/title-search-v3.js",
    "_assets/script/feedback-v1.js",
    "_assets/style/feedback-v1.css",
)

SCRIPT_DIR = Path("docs/_assets/script")

INDEX_RE = re.compile(r"window\.EESG_SEARCH_INDEX=(\[.*\]);\s*$", re.DOTALL)
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<url>[^)]+)\)")
TOC_URL_RE = re.compile(r"^\s*url:\s*['\"]?(?P<url>[^'\"\s]+)['\"]?\s*$", re.MULTILINE)
SCRIPT_ROUTE_RE = re.compile(r"""new\s+URL\(\s*['"](?P<url>[^'"]+)['"]\s*,\s*SITE_ROOT""")


def load_scope() -> tuple[list[str], list[str]]:
    raw = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))
    return [str(x) for x in raw.get("publish", [])], [str(x) for x in raw.get("keep_hidden", [])]


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
    try:
        target = static_target(url)
    except ValueError as exc:
        errors.append(f"{label} invalid: {exc}")
        return
    if target is not None and not target.exists():
        errors.append(f"{label} target missing: {url} ({target})")


def top_level_blocks(text: str) -> list[list[str]]:
    lines = text.splitlines()
    try:
        items_index = lines.index("items:")
    except ValueError:
        return []
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines[items_index + 1 :]:
        if line.startswith("  - name: "):
            if current:
                blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def block_for_name(blocks: list[list[str]], name: str) -> list[str] | None:
    for block in blocks:
        first = block[0] if block else ""
        if f'"{name}"' in first or f"'{name}'" in first:
            return block
    return None


def main() -> int:
    errors: list[str] = []
    publish, hidden = load_scope()
    allowed = set(publish) | set(hidden)

    if not STATIC_ROOT.exists():
        print(f"Static build directory does not exist: {STATIC_ROOT}")
        return 1

    # 1. Домашняя страница
    if not HOME.exists():
        errors.append(f"Built homepage does not exist: {HOME}")
    else:
        home_html = HOME.read_text(encoding="utf-8")
        for marker in ("Саркомы костей", "Общие принципы"):
            if marker not in home_html:
                errors.append(f"Homepage is missing section {marker!r}")
        for asset in REQUIRED_HOME_ASSETS:
            if asset not in home_html:
                errors.append(f"Homepage is missing required asset: {asset}")

    # 2. Опорная клиническая страница
    if not REFERENCE_PAGE.exists():
        errors.append(f"Reference clinical page is not buildable: {REFERENCE_PAGE}")
    else:
        page_html = REFERENCE_PAGE.read_text(encoding="utf-8")
        for asset in (
            "_assets/style/internal-page-v2.css",
            "_assets/script/internal-page-v2.js",
            "_assets/script/feedback-v1.js",
        ):
            if asset not in page_html:
                errors.append(f"Reference clinical page is missing asset: {asset}")
        if '"headings":[' not in page_html:
            errors.append("Reference clinical page lost heading metadata")

    # 3. Убранные разделы не должны существовать в сборке
    for entry in sorted(p.name for p in STATIC_ROOT.iterdir() if p.is_dir()):
        if entry.startswith("_") or entry in allowed:
            continue
        errors.append(f"Section outside site scope is present in the build: {entry}")

    # 4. Поисковый указатель
    if not SEARCH_INDEX.exists():
        errors.append(f"Missing search index: {SEARCH_INDEX}")
    else:
        match = INDEX_RE.search(SEARCH_INDEX.read_text(encoding="utf-8"))
        if not match:
            errors.append("Could not parse EESG search index payload")
        else:
            for item in json.loads(match.group(1)):
                url = str(item.get("url") or "")
                title = str(item.get("title") or "<untitled>")
                validate_local_url(errors, f"Search URL for {title}", url)
                path = url.lstrip("./")
                section = path.split("/", 1)[0] if "/" in path else ""
                if section and section not in allowed:
                    errors.append(f"Section outside site scope leaked into search: {url}")

    # 5. Страница обновлений
    if UPDATES.exists():
        for match in MD_LINK_RE.finditer(UPDATES.read_text(encoding="utf-8")):
            url = match.group("url").strip()
            validate_local_url(errors, "Updates URL", url)
            path = url.lstrip("./")
            section = path.split("/", 1)[0] if "/" in path else ""
            if section and not url.startswith(("http", "mailto:", "#")) and section not in allowed:
                errors.append(f"Section outside site scope leaked into updates: {url}")

    # 6. Навигация
    if not TOC.exists():
        errors.append(f"Missing site TOC/navigation config: {TOC}")
    else:
        for match in TOC_URL_RE.finditer(TOC.read_text(encoding="utf-8")):
            url = match.group("url").strip()
            if "gen_docs/" in url:
                errors.append(f"Navigation URL exposes internal gen_docs path: {url}")
                continue
            validate_local_url(errors, "Navigation URL", url)

    if not GUIDELINES_TOC.exists():
        errors.append(f"Missing generated recommendations TOC: {GUIDELINES_TOC}")
    else:
        blocks = top_level_blocks(GUIDELINES_TOC.read_text(encoding="utf-8"))
        for name in PUBLIC_GUIDELINE_NAMES:
            block = block_for_name(blocks, name)
            if block is None:
                errors.append(f"Public guideline section missing from TOC: {name}")
            elif any(line.strip() == "hidden: true" for line in block):
                errors.append(f"Public guideline section is incorrectly hidden: {name}")

    # 7. Собранная навигация
    if not BUILT_TOC.exists():
        errors.append(f"Built navigation payload is missing: {BUILT_TOC}")
    else:
        built_toc = BUILT_TOC.read_text(encoding="utf-8")
        for text, url in EXPECTED_HEADER_LINKS.items():
            if f'"text":"{text}","url":"{url}"' not in built_toc:
                errors.append(f"Built toc.js does not contain header link {text!r} -> {url}")

    # 8. Маршруты, которые фронтенд строит от корня сайта
    #    Скрипт может подставить ссылку на раздел, которого нет в сборке
    #    (так на главной появлялась ссылка «О проекте» -> /about/ с 404).
    if SCRIPT_DIR.exists():
        for script in sorted(SCRIPT_DIR.glob("*.js")):
            for match in SCRIPT_ROUTE_RE.finditer(script.read_text(encoding="utf-8")):
                url = urlsplit(match.group("url")).path
                if not url or url in {".", "./", "../", "../../"}:
                    continue
                validate_local_url(errors, f"Route in {script.name}", url)

    if errors:
        print("Static route/render validation errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"Static validation failed with {len(errors)} error(s).")
        return 1

    print(
        "Static validation passed: только разделы из site-scope присутствуют в сборке, "
        "поиске и обновлениях; виджет замечаний подключён; навигация разрешается."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
