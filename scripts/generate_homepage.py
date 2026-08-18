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
    "bone-sarcomas/general-principles": "маршрут больного, биопсия, стадирование, общая тактика",
    "bone-sarcomas/osteosarcoma-adults": "локализованное и распространённое заболевание",
    "bone-sarcomas/chondrosarcoma-adults": "хирургическая тактика, отдельные подтипы",
    "bone-sarcomas/ewing-sarcoma-adults": "мультимодальное лечение, системная терапия",
    "bone-sarcomas/giant-cell-tumor-of-bone": "оценка риска, показания к локальному и системному лечению",
    "bone-sarcomas/chordoma": "локальное лечение, распространённое заболевание",
    "bone-sarcomas/rare-bone-tumours": "практические положения по редким нозологиям",
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
        "Саркомы костей и общие принципы ведения больных саркомами. Каждая страница отвечает "
        "на вопрос «что делать»: дозы, пороги и ссылка на конкретное исследование под каждым положением.",
        "",
        "Документ вынесен на профессиональное обсуждение. Замечание можно оставить прямо в тексте: "
        "выделите фрагмент и нажмите появившуюся кнопку **«Замечание»**. Регистрация не нужна.",
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
            "## Как оставить замечание",
            "",
            "Регистрация не нужна; искать нужное место в тексте и писать письмо тоже не нужно.",
            "",
            "1. Выделите фрагмент текста на любой странице.",
            "2. Нажмите появившуюся кнопку **«Замечание»**.",
            "3. Напишите, что не так, и отправьте. Имя и место работы — по желанию.",
            "",
            "Замечание уходит рабочей группе вместе с цитатой и адресом страницы. "
            "Общее замечание к странице можно оставить кнопкой в правом нижнем углу.",
            "",
            "## Как читать страницу",
            "",
            "- **Полужирный абзац** — утверждение: что делать.",
            "- **Абзац с отступом под ним** — доказательные детали: размер эффекта, доверительный интервал, ограничение.",
            "- **Номер со ссылкой** — конкретное исследование, на котором основано утверждение.",
            "- **«Согласованное мнение рабочей группы»** — первичных данных нет, положение принято рабочей группой.",
            "- **Раздел «Сопоставление с действующими руководствами»** — позиции ESMO, NCCN, британского и немецкого руководств.",
            "- **Раздел «Ограничения доказательной базы»** — чего эти данные не доказывают.",
            "",
            "## О проекте",
            "",
            "Рекомендации готовит рабочая группа Восточно-Европейской группы по изучению сарком. "
            "На сайте опубликованы саркомы костей и общие принципы; остальные разделы находятся в работе.",
            "",
            "Вопросы и предложения — **md.batov@gmail.com**",
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
    prefix = text[: meta.end()].rstrip()
    prefix = re.sub(r"^#\s+.*$", "# Клинические рекомендации EESG", prefix, count=1, flags=re.M)
    ROOT_PAGE.write_text(prefix + "\n\n" + homepage_markdown(publish) + "\n", encoding="utf-8")

    total = sum(len(pages) for _, _, pages in sections(publish))
    print(f"Главная собрана: разделов {len(publish)}, страниц в перечнях {total}")


if __name__ == "__main__":
    main()
