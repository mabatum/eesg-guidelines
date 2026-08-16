from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

GEN_ROOT = Path("docs/gen_docs")
ROOT_PAGE = GEN_ROOT / "index.md"

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
META_RE = re.compile(
    r"\*\*Статус:\*\*\s*(?P<status>.+?)"
    r"(?:\s+·\s+\*\*Версия:\*\*\s*(?P<version>.+?))?"
    r"(?:\s+·\s+\*\*Обновлено:\*\*\s*(?P<updated>\d{2}\.\d{2}\.\d{4}))?"
    r"(?:\s+·\s+\*\*Следующий пересмотр:\*\*\s*(?P<review>.+?))?"
    r"(?:\s+·\s+\*\*Рабочая группа:\*\*\s*(?P<group>.+?))?"
    r"(?:\n|$)"
)

HIDDEN_PREFIXES = {
    "about",
    "editorial-standard",
    "materials-map",
    "news",
    "events",
    "clinical-trials",
}

RECOMMENDATION_SECTIONS = [
    (
        "Саркомы мягких тканей",
        "Диагностика и лечение основных гистологических вариантов сарком мягких тканей.",
        "./soft-tissue-sarcomas/",
    ),
    (
        "Саркомы костей",
        "Остеосаркома, саркома Юинга, хондросаркома и другие первичные опухоли кости.",
        "./bone-sarcomas/",
    ),
    (
        "Отдельные нозологические группы",
        "ГИСО, десмоидные опухоли, хордома, сосудистые и другие редкие опухоли.",
        "./specific-tumor-groups/",
    ),
    (
        "Общие принципы",
        "Биопсия, патоморфология, стадирование, локальное и системное лечение, наблюдение.",
        "./general-principles/",
    ),
    (
        "Препараты и режимы",
        "Практические разделы по лекарственным препаратам и режимам системной терапии.",
        "./drugs-and-regimens/",
    ),
    (
        "Особые клинические ситуации",
        "Беременность, наследственная предрасположенность, пожилой возраст и другие ситуации.",
        "./special-clinical-situations/",
    ),
]

PORTAL_SECTIONS = [
    (
        "Клинические исследования",
        "Исследования в области сарком, включая проекты EESG и информацию об открытом наборе.",
        "./clinical-trials/",
    ),
    (
        "Мероприятия",
        "Научные и образовательные мероприятия EESG, конференции и профессиональные встречи.",
        "./events/",
    ),
    (
        "Новости",
        "Новости группы, обновления проектов, публикаций и профессиональной деятельности EESG.",
        "./news/",
    ),
]


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return datetime.min


def title_of(path: Path) -> str | None:
    match = H1_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


def public_url(path: Path) -> str:
    relative = path.relative_to(GEN_ROOT).as_posix()
    if relative == "index.md":
        return "./"
    if relative.endswith("/index.md"):
        return "./" + relative[: -len("index.md")]
    return "./" + relative.removesuffix(".md") + ".html"


def breadcrumb(path: Path, titles: dict[Path, str]) -> str:
    parts: list[str] = []
    current = path.parent.parent
    while current != GEN_ROOT.parent and current != GEN_ROOT:
        title = titles.get(current)
        if title:
            parts.append(title)
        current = current.parent
    parts.reverse()
    return " › ".join(parts)


def recent_pages(limit: int = 4) -> list[dict[str, str]]:
    pages = sorted(GEN_ROOT.rglob("index.md"))
    titles = {page.parent: title for page in pages if (title := title_of(page))}
    page_dirs = {page.parent for page in pages}

    records: list[dict[str, str | datetime]] = []
    for page in pages:
        if page == ROOT_PAGE:
            continue

        relative_parts = page.relative_to(GEN_ROOT).parts
        if not relative_parts or relative_parts[0] in HIDDEN_PREFIXES:
            continue

        page_dir = page.parent
        has_children = any(other != page_dir and page_dir in other.parents for other in page_dirs)
        if has_children:
            continue

        text = page.read_text(encoding="utf-8")
        h1 = H1_RE.search(text)
        meta = META_RE.search(text)
        if not h1 or not meta:
            continue

        updated = (meta.group("updated") or "").strip()
        records.append(
            {
                "title": h1.group(1).strip(),
                "url": public_url(page),
                "updated": updated,
                "updated_dt": parse_date(updated),
                "section": breadcrumb(page, titles),
            }
        )

    records.sort(
        key=lambda item: (item["updated_dt"], str(item["title"]).casefold()),
        reverse=True,
    )
    return [
        {key: str(value) for key, value in item.items() if key != "updated_dt"}
        for item in records[:limit]
    ]


def cards_markdown(title: str, cards: list[tuple[str, str, str]]) -> list[str]:
    lines = [f"## {title}", ""]
    for card_title, description, url in cards:
        lines.extend(
            [
                f"### [{card_title}]({url})",
                "",
                description,
                "",
                f"[Открыть раздел]({url})",
                "",
            ]
        )
    return lines


def portal_markdown(recent: list[dict[str, str]]) -> str:
    lines = [
        "Клинические рекомендации, клинические исследования, новости и мероприятия Восточно-Европейской группы по изучению сарком.",
        "",
        "[Перейти к рекомендациям](#rekomendatsii) · [Клинические исследования](./clinical-trials/) · [Новости](./news/) · [Мероприятия](./events/)",
        "",
    ]

    lines.extend(cards_markdown("Рекомендации", RECOMMENDATION_SECTIONS))
    lines.extend(cards_markdown("Разделы портала", PORTAL_SECTIONS))

    if recent:
        lines.extend(["## Недавно обновлено", ""])
        for item in recent:
            details = [part for part in (item.get("section"), item.get("updated")) if part]
            detail_text = " · ".join(details) or "Обновлённый раздел рекомендаций"
            lines.extend(
                [
                    f"### [{item['title']}]({item['url']})",
                    "",
                    detail_text,
                    "",
                    f"[Открыть]({item['url']})",
                    "",
                ]
            )
        lines.extend(["[Все обновления рекомендаций](./updates.html)", ""])

    return "\n".join(lines).rstrip()


def main() -> None:
    if not ROOT_PAGE.exists():
        raise SystemExit(f"Root Wiki export not found: {ROOT_PAGE}")

    text = ROOT_PAGE.read_text(encoding="utf-8")
    meta = META_RE.search(text)
    if not meta:
        raise SystemExit("Could not locate publication metadata on root Wiki page")

    insertion = meta.end()
    recent = recent_pages()
    block = portal_markdown(recent)
    enhanced = text[:insertion].rstrip() + "\n\n" + block + "\n\n" + text[insertion:].lstrip()
    ROOT_PAGE.write_text(enhanced.rstrip() + "\n", encoding="utf-8")

    print(
        f"Enhanced homepage v2 with {len(RECOMMENDATION_SECTIONS)} recommendation cards, "
        f"{len(PORTAL_SECTIONS)} portal cards and {len(recent)} recent recommendation updates."
    )


if __name__ == "__main__":
    main()
