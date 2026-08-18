from __future__ import annotations

import re
from pathlib import Path

GEN_ROOT = Path("docs/gen_docs")
ROOT_PAGE = GEN_ROOT / "index.md"

META_RE = re.compile(
    r"\*\*Статус:\*\*\s*(?P<status>.+?)"
    r"(?:\s+·\s+\*\*Версия:\*\*\s*(?P<version>.+?))?"
    r"(?:\s+·\s+\*\*Обновлено:\*\*\s*(?P<updated>\d{2}\.\d{2}\.\d{4}))?"
    r"(?:\s+·\s+\*\*Следующий пересмотр:\*\*\s*(?P<review>.+?))?"
    r"(?:\s+·\s+\*\*Рабочая группа:\*\*\s*(?P<group>.+?))?"
    r"(?:\n|$)"
)

PUBLIC_RECOMMENDATIONS = [
    (
        "Общие принципы ведения пациентов с саркомами",
        "Маршрутизация, биопсия, морфологическая и молекулярная диагностика, стадирование, локальное и системное лечение, наблюдение.",
        "./general-principles/",
    ),
    (
        "Саркомы костей",
        "Общие принципы ведения первичных опухолей кости, остеосаркома, хондросаркома, саркома Юинга и другие нозологии.",
        "./bone-sarcomas/",
    ),
]


def homepage_markdown() -> str:
    lines = [
        "Клинические рекомендации Восточно-Европейской группы по изучению сарком для специалистов, занимающихся диагностикой и лечением сарком костей и мягких тканей.",
        "",
    ]

    for title, description, url in PUBLIC_RECOMMENDATIONS:
        lines.extend(
            [
                f"**[{title}]({url})**  ",
                description,
                "",
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

    # The Wiki root page contains editorial/navigation material that duplicates
    # the global header and side navigation. Keep only H1 + publication metadata,
    # then render the two recommendation sections currently exposed publicly.
    prefix = text[: meta.end()].rstrip()
    ROOT_PAGE.write_text(prefix + "\n\n" + homepage_markdown() + "\n", encoding="utf-8")

    print(
        "Simplified homepage: removed duplicate portal/navigation blocks and exposed "
        f"{len(PUBLIC_RECOMMENDATIONS)} recommendation sections."
    )


if __name__ == "__main__":
    main()
