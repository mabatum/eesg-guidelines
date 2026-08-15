from __future__ import annotations

import re
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


def main() -> None:
    records: list[dict[str, str | bool | datetime]] = []

    for page in sorted(GEN_ROOT.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        h1 = H1_RE.search(text)
        meta = META_RE.search(text)
        if not h1 or not meta:
            continue

        updated = meta.group("updated") or ""
        records.append(
            {
                "title": h1.group(1).strip(),
                "url": page_url(page),
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

    lines = [
        "# Последние обновления",
        "",
        "Здесь автоматически отображаются недавно обновлённые разделы портала EESG.",
        "",
        "Дата берётся из метаданных страницы Яндекс Вики. Версия и статус отображаются только если они заданы для страницы.",
        "",
    ]

    for item in records[:30]:
        title = str(item["title"])
        url = str(item["url"])
        details: list[str] = []
        if item["updated"]:
            details.append(str(item["updated"]))
        if item["version"]:
            details.append(f"версия {item['version']}")
        if item["status"]:
            details.append(str(item["status"]))

        lines.append(f"## [{title}]({url})")
        if details:
            lines.append("")
            lines.append(" · ".join(details))
        if item["has_changelog"]:
            lines.append("")
            lines.append(f"[Что изменилось]({url}#что-изменилось)")
        lines.append("")

    OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT} from {len(records)} page metadata records.")


if __name__ == "__main__":
    main()
