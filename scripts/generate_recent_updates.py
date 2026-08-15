from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DOCS_ROOT = Path("docs")
GEN_ROOT = DOCS_ROOT / "gen_docs"
OUTPUT = DOCS_ROOT / "updates.md"

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
META_RE = re.compile(
    r"\*\*Статус:\*\*\s*(?P<status>.+?)"
    r"(?:\s+·\s+\*\*Версия:\*\*\s*(?P<version>.+?))?"
    r"(?:\s+·\s+\*\*Обновлено:\*\*\s*(?P<updated>\d{2}\.\d{2}\.\d{4}))?"
    r"(?:\s+·\s+\*\*Следующий пересмотр:\*\*\s*(?P<review>.+?))?"
    r"(?:\s+·\s+\*\*Рабочая группа:\*\*\s*(?P<group>.+?))?"
    r"(?:\n|$)"
)
CHANGELOG_RE = re.compile(r"^#{2,3}\s+Что изменилось\s*$", re.IGNORECASE | re.MULTILINE)

MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def page_url(page: Path) -> str:
    """Return the public URL after Diplodoc merges gen_docs into the site root."""
    relative = page.relative_to(GEN_ROOT).as_posix()
    if relative == "index.md":
        return "./"
    if relative.endswith("/index.md"):
        return "./" + relative[: -len("index.md")]
    return "./" + relative.removesuffix(".md") + ".html"


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return datetime.min


def human_date(value: datetime) -> str:
    if value == datetime.min:
        return "Без даты"
    return f"{value.day} {MONTHS[value.month]} {value.year}"


def extract_title(page: Path) -> str | None:
    match = H1_RE.search(page.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


def build_titles_by_dir() -> dict[Path, str]:
    result: dict[Path, str] = {}
    for page in GEN_ROOT.rglob("index.md"):
        title = extract_title(page)
        if title:
            result[page.parent] = title
    return result


def section_titles(page: Path, titles_by_dir: dict[Path, str]) -> list[str]:
    result: list[str] = []
    current = page.parent.parent
    while current != GEN_ROOT.parent and GEN_ROOT in [current, *current.parents]:
        if current == GEN_ROOT:
            break
        title = titles_by_dir.get(current)
        if title:
            result.append(title)
        current = current.parent
    result.reverse()
    return result


def main() -> None:
    records: list[dict[str, object]] = []
    titles_by_dir = build_titles_by_dir()

    for page in sorted(GEN_ROOT.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        h1 = H1_RE.search(text)
        meta = META_RE.search(text)
        if not h1 or not meta:
            continue

        updated = meta.group("updated") or ""
        hierarchy = section_titles(page, titles_by_dir)
        records.append(
            {
                "title": h1.group(1).strip(),
                "url": page_url(page),
                "section": " › ".join(hierarchy),
                "status": (meta.group("status") or "").strip(),
                "version": (meta.group("version") or "").strip(),
                "updated": updated,
                "updated_dt": parse_date(updated),
                "has_changelog": bool(CHANGELOG_RE.search(text)),
            }
        )

    records.sort(
        key=lambda item: (
            item["updated_dt"],
            str(item["title"]).casefold(),
        ),
        reverse=True,
    )

    visible = records[:40]
    status_counts = Counter(str(item["status"]) for item in visible if item["status"])
    versioned = sum(1 for item in visible if item["version"])
    changelogged = sum(1 for item in visible if item["has_changelog"])

    lines = [
        "# Последние обновления",
        "",
        "Здесь автоматически отображаются недавно изменённые разделы портала EESG. Дата берётся из Яндекс Вики; версия и редакционный статус отображаются только из метаданных страницы.",
        "",
        f"**Показано:** {len(visible)} последних изменений · **С версией:** {versioned} · **С описанием изменений:** {changelogged}",
        "",
    ]

    if len(status_counts) > 1:
        status_summary = " · ".join(f"{status}: {count}" for status, count in status_counts.most_common())
        lines.extend([f"**Статусы:** {status_summary}", ""])

    grouped: dict[datetime, list[dict[str, object]]] = defaultdict(list)
    for item in visible:
        grouped[item["updated_dt"]].append(item)

    for date_value in sorted(grouped, reverse=True):
        lines.append(f"## {human_date(date_value)}")
        lines.append("")

        for item in grouped[date_value]:
            title = str(item["title"])
            url = str(item["url"])
            lines.append(f"### [{title}]({url})")
            lines.append("")

            details: list[str] = []
            if item["section"]:
                details.append(f"**Раздел:** {item['section']}")
            if item["status"]:
                details.append(f"**Статус:** {item['status']}")
            if item["version"]:
                details.append(f"**Версия:** {item['version']}")
            if details:
                lines.append(" · ".join(details))

            if item["has_changelog"]:
                lines.append("")
                lines.append(f"[Что изменилось]({url}#что-изменилось)")
            lines.append("")

    OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT} from {len(records)} page metadata records; showing {len(visible)}.")


if __name__ == "__main__":
    main()
