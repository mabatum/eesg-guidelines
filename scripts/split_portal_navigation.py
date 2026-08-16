from __future__ import annotations

from pathlib import Path

GUIDELINES_TOC = Path("docs/gen_docs/toc.yaml")

PORTAL_NAMES = (
    "Клинические исследования",
    "Мероприятия",
    "Новости",
)


def strip_portal_items(text: str) -> str:
    lines = text.splitlines()
    try:
        items_index = lines.index("items:")
    except ValueError as exc:
        raise SystemExit(f"Could not find top-level items in {GUIDELINES_TOC}") from exc

    prefix = lines[: items_index + 1]
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

    found: set[str] = set()
    kept: list[list[str]] = []

    for block in blocks:
        first = block[0] if block else ""
        matched = next(
            (
                name
                for name in PORTAL_NAMES
                if f'"{name}"' in first or f"'{name}'" in first
            ),
            None,
        )
        if matched:
            found.add(matched)
        else:
            kept.append(block)

    missing = [name for name in PORTAL_NAMES if name not in found]
    if missing:
        raise SystemExit(
            "Portal navigation pages were not found in generated TOC: " + ", ".join(missing)
        )

    output_lines = prefix[:]
    for block in kept:
        output_lines.extend(block)
    return "\n".join(output_lines).rstrip() + "\n"


def main() -> None:
    text = GUIDELINES_TOC.read_text(encoding="utf-8")
    GUIDELINES_TOC.write_text(strip_portal_items(text), encoding="utf-8")
    print(
        "Removed portal pages from clinical guidelines navigation: "
        + ", ".join(PORTAL_NAMES)
    )


if __name__ == "__main__":
    main()
