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
LMS_PAGE = STATIC_ROOT / "soft-tissue-sarcomas/leiomyosarcoma/index.html"

PUBLIC_GUIDELINE_NAMES = (
    "Общие принципы ведения пациентов с саркомами",
    "Саркомы костей",
)
HIDDEN_GUIDELINE_NAMES = (
    "Саркомы мягких тканей",
    "Отдельные нозологические группы",
    "Отдельные клинические ситуации",
    "Препараты и режимы системной терапии",
)

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


def top_level_blocks(text: str) -> list[list[str]]:
    lines = text.splitlines()
    try:
        items_index = lines.index("items:")
    except ValueError:
        return []
    body = lines[items_index + 1 :]
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in body:
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

    if not STATIC_ROOT.exists():
        errors.append(f"Static build directory does not exist: {STATIC_ROOT}")

    if not HOME.exists():
        errors.append(f"Built homepage does not exist: {HOME}")
    else:
        home_html = HOME.read_text(encoding="utf-8")
        for marker in PUBLIC_GUIDELINE_NAMES:
            if marker not in home_html:
                errors.append(f"Simplified homepage is missing public section {marker!r}")
        for obsolete_marker in (
            "Разделы портала",
            "Недавно обновлено",
            "Перейти к рекомендациям",
        ):
            if obsolete_marker in home_html:
                errors.append(
                    f"Simplified homepage still contains duplicate block {obsolete_marker!r}"
                )
        for asset in (
            "_assets/script/header-nav-v3.js",
            "_assets/script/search-index-v3.js",
            "_assets/script/title-search-v3.js",
        ):
            if asset not in home_html:
                errors.append(f"Built homepage is missing required UI asset: {asset}")

    # Hidden branches must remain buildable for direct/internal references.
    if not LMS_PAGE.exists():
        errors.append(f"Hidden reference clinical page is no longer buildable: {LMS_PAGE}")
    else:
        lms_html = LMS_PAGE.read_text(encoding="utf-8")
        for asset in (
            "_assets/style/internal-page-v2.css",
            "_assets/script/internal-page-v2.js",
        ):
            if asset not in lms_html:
                errors.append(f"Reference clinical page is missing UX asset: {asset}")
        if '"headings":[' not in lms_html:
            errors.append("Reference clinical page lost heading metadata")
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

            allowed_alias_url = "bone-sarcomas/giant-cell-tumor-of-bone/index.html"
            allowed_aliases = {
                str(value).casefold()
                for value in by_url.get(allowed_alias_url, {}).get("aliases", [])
            }
            if "gctb" not in allowed_aliases:
                errors.append("Public bone-sarcoma search alias GCTB is missing")

            for hidden_url in (
                "soft-tissue-sarcomas/leiomyosarcoma/index.html",
                "specific-tumor-groups/gist/index.html",
                "drugs-and-regimens/gemcitabine-docetaxel/index.html",
            ):
                if hidden_url in by_url:
                    errors.append(f"Hidden recommendation section leaked into search: {hidden_url}")

    if UPDATES.exists():
        text = UPDATES.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(text):
            url = match.group("url").strip()
            validate_local_url(errors, "Updates URL", url)
            if any(
                url.lstrip("./").startswith(prefix + "/")
                for prefix in (
                    "soft-tissue-sarcomas",
                    "specific-tumor-groups",
                    "special-clinical-situations",
                    "drugs-and-regimens",
                )
            ):
                errors.append(f"Hidden recommendation section leaked into updates: {url}")

    if not TOC.exists():
        errors.append(f"Missing site TOC/navigation config: {TOC}")
    else:
        text = TOC.read_text(encoding="utf-8")
        for match in TOC_URL_RE.finditer(text):
            validate_local_url(errors, "Navigation URL", match.group("url").strip())

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
        for name in HIDDEN_GUIDELINE_NAMES:
            block = block_for_name(blocks, name)
            if block is None:
                errors.append(f"Hidden guideline section disappeared from build TOC: {name}")
            elif not any(line.strip() == "hidden: true" for line in block):
                errors.append(f"Guideline section should be hidden but is visible: {name}")

    if not BUILT_TOC.exists():
        errors.append(f"Built navigation payload is missing: {BUILT_TOC}")
    else:
        built_toc = BUILT_TOC.read_text(encoding="utf-8")
        expected_header_links = {
            "Рекомендации": "./index.html",
            "Клинические исследования": "./clinical-trials/",
            "Мероприятия": "./events/",
            "Новости": "./news/",
            "Обновления": "./updates.html",
            "О проекте": "./about/",
        }
        for text, url in expected_header_links.items():
            marker = f'"text":"{text}","url":"{url}"'
            if marker not in built_toc:
                errors.append(f"Built toc.js does not contain canonical header link {text!r} -> {url}")
        if '"url":"./gen_docs/' in built_toc or '"url":"gen_docs/' in built_toc:
            errors.append("Built toc.js still exposes internal gen_docs navigation URLs")

    if errors:
        print("Static route/render validation errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"Static validation failed with {len(errors)} error(s).")
        return 1

    print(
        "Static validation passed: homepage duplication removed; only General Principles and Bone Sarcomas "
        "remain visible in recommendations; hidden sections remain buildable but are excluded from search and "
        "updates; canonical portal navigation and tested routes resolve."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
