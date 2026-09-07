"""Собирает главную страницу — навигацию по опубликованным разделам.

Важно: корневой страницей сайта становится docs/gen_docs/index.md, потому что
docs/toc.yaml подключает оглавление gen_docs в режиме merge. Файл docs/index.md
в сборку не попадает — правки нужно вносить здесь.

Перечни страниц строятся из docs/gen_docs/toc.yaml, поэтому не расходятся с
навигацией при добавлении и удалении страниц.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

GEN_ROOT = Path("docs/gen_docs")
ROOT_PAGE = GEN_ROOT / "index.md"
TOC = GEN_ROOT / "toc.yaml"
SCOPE_FILE = Path("config/site-scope.json")

META_RE = re.compile(
    r"\*\*Статус:\*\*\s*(?P<status>.+?)"
    r"(?:\s+·\s+\*\*Версия:\*\*\s*(?P<version>.+?))?"
    r"(?:\s+·\s+\*\*Обновлено:\*\*\s*(?P<updated>\d{2}\.\d{2}\.\d{4}))?"
    r"(?:\s+·\s+\*\*Следующий пересмотр:\*\*\s*(?P<review>.+?))?"
    r"(?:\s+·\s+\*\*Рабочая группа:\*\*\s*(?P<group>.+?))?"
    r"(?:\n|$)"
)

# Короткое пояснение к странице: врач должен понимать, куда ведёт ссылка,
# не открывая её. Ключ — каталог страницы внутри раздела.
HINTS = {
    "bone-sarcomas/general-principles": "биопсия, обследование, TNM, сопровождение и наблюдение",
    "bone-sarcomas/osteosarcoma-adults": "AP/MAP, патоморфоз, операция и лечение рецидива",
    "bone-sarcomas/chondrosarcoma-adults": "ACT, обычная, дедифференцированная, мезенхимальная и светлоклеточная формы",
    "bone-sarcomas/ewing-sarcoma-adults": "VDC/IE, лучевая терапия, лёгочные метастазы и повторные линии",
    "bone-sarcomas/giant-cell-tumor-of-bone": "кюретаж и резекция, деносумаб, рецидив и лёгочные очаги",
    "bone-sarcomas/chordoma": "операция и облучение по локализации, TKI и лечение рецидива",
    "bone-sarcomas/rare-bone-tumours": "НПС, лейомиосаркома, сосудистые опухоли, адамантинома и редкие молекулярные варианты",
    "general-principles/sarcoma-center-and-mdt": "кого и когда направлять",
    "general-principles/biopsy-and-pathology": "как получить материал и что должно быть в заключении",
    "general-principles/molecular-diagnostics": "когда нужна и что она меняет",
    "general-principles/imaging-and-staging": "объём обследования, оценка риска",
    "general-principles/surgery-localized-sts": "край резекции, объём вмешательства",
    "general-principles/radiotherapy-localized-sts": "до операции или после, дозы",
    "general-principles/perioperative-chemotherapy": "кому показана",
    "general-principles/systemic-therapy-advanced-sts": "выбор режима при распространённом заболевании",
    "general-principles/systemic-therapy-later-lines-sts": "выбор по гистологическому подтипу",
    "general-principles/follow-up": "интервалы и объём",
}

SECTION_LEAD = {
    "bone-sarcomas": "Обследование при подозрении на первичную опухоль кости, лечение по гистологическому варианту и контроль после завершения терапии.",
    "general-principles": "Положения, общие для всех подтипов: нозологические страницы на них опираются и не повторяют их.",
}


def scope() -> list[str]:
    raw = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))
    return [str(name) for name in raw.get("publish", [])]


def toc_entries() -> list[tuple[str, str]]:
    """Пары (название, href) в порядке оглавления."""
    text = TOC.read_text(encoding="utf-8")
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(r'name:\s*"([^"]+)"\s*\n\s*href:\s*"([^"]+)"', text)
    ]


def sections(publish: list[str]) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Для каждого публикуемого раздела: заголовок, href обзорной страницы, страницы."""
    entries = toc_entries()
    result = []
    for section in publish:
        title = next((n for n, h in entries if h == f"{section}/index.md"), section)
        pages = [
            (name, href)
            for name, href in entries
            if href.startswith(f"{section}/") and href != f"{section}/index.md"
        ]
        result.append((title, f"{section}/index.md", pages))
    return result


def page_list(pages: list[tuple[str, str]]) -> list[str]:
    """Список, а не таблица: на телефоне узкая колонка рвёт названия по слогам."""
    lines = []
    for name, href in pages:
        hint = HINTS.get(href.removesuffix("/index.md"), "")
        lines.append(f"- [{name}]({href})" + (f" — {hint}" if hint else ""))
    return lines


def homepage_markdown(publish: list[str]) -> str:
    lines: list[str] = [
        "В тестовой редакции открыт раздел по первичным опухолям кости у взрослых. "
        "Страницы содержат показания к биопсии и стадированию, выбор операции и лучевой терапии, "
        "схемы лекарственного лечения с дозами и календарями, тактику при рецидиве и наблюдение."
        if publish == ["bone-sarcomas"] else
        "Клинические рекомендации EESG: обследование, локальное и лекарственное лечение, "
        "тактика при рецидиве и наблюдение.",
        "",
    ]

    for title, section_href, pages in sections(publish):
        lines.append(f"## [{title}]({section_href})")
        lines.append("")
        section = section_href.split("/", 1)[0]
        if section in SECTION_LEAD:
            lines.extend([SECTION_LEAD[section], ""])
        lines.extend(page_list(pages))
        lines.append("")

    lines.extend(
        [
            "## Источники редакции",
            "",
            "Основа раздела по костям — [практические рекомендации RUSSCO 2025]"
            "(https://rosoncoweb.ru/standarts/RUSSCO/2025/2025-1-2-14.pdf), "
            "редакционные материалы «КР саркомы костей» и «Лекарственное лечение сарком кости». "
            "Расхождения проверены по профильным руководствам и первичным исследованиям. "
            "Ссылки на источники приведены рядом с соответствующими положениями.",
            "",
            "## Экспертное обсуждение",
            "",
            "Чтобы предложить правку, выделите фрагмент и нажмите **«Замечание»**. "
            "К комментарию будут приложены цитата и адрес страницы. "
            "Общее замечание можно оставить кнопкой в правом нижнем углу.",
            "",
            "Редакция предназначена для профессионального обсуждения. "
            "Вопросы по проекту — **md.batov@gmail.com**.",
        ]
    )

    return "\n".join(lines).rstrip()


def main() -> None:
    if not ROOT_PAGE.exists():
        raise SystemExit(f"Root Wiki export not found: {ROOT_PAGE}")

    text = ROOT_PAGE.read_text(encoding="utf-8")
    meta = META_RE.search(text)
    if not meta:
        raise SystemExit("Could not locate publication metadata on root Wiki page")

    publish = scope()
    # Metadata follows the latest published clinical page, not an older Wiki root.
    candidates = []
    for _, section_href, pages in sections(publish):
        for href in [section_href, *(href for _, href in pages)]:
            page = GEN_ROOT / href
            if page.exists():
                current = META_RE.search(page.read_text(encoding="utf-8"))
                if current and current.group("updated"):
                    candidates.append((datetime.strptime(current.group("updated"), "%d.%m.%Y"), current.group(0).strip()))
    latest_meta = max(candidates, key=lambda item: item[0])[1] if candidates else meta.group(0).strip()
    prefix = "# Клинические рекомендации EESG\n\n" + latest_meta
    ROOT_PAGE.write_text(prefix + "\n\n" + homepage_markdown(publish) + "\n", encoding="utf-8")

    total = sum(len(pages) for _, _, pages in sections(publish))
    print(f"Главная собрана: разделов {len(publish)}, страниц в перечнях {total}")


if __name__ == "__main__":
    main()
