from __future__ import annotations

from pathlib import Path

GUIDELINES_TOC = Path("docs/gen_docs/toc.yaml")

PORTAL_NAMES = (
    "Клинические исследования",
    "Мероприятия",
    "Новости",
)

PUBLIC_GUIDELINE_NAMES = (
    "Общие принципы ведения пациентов с саркомами",
    "Саркомы костей",
)

# These pages remain buildable because they are used by the portal/header, but
# they are intentionally absent from the recommendations navigation.
INFRASTRUCTURE_NAMES = (
    "Область применения и методология",
    "Правила подготовки и представления рекомендаций",
    "Библиографическая база",
)


def top_level_name(block: list[str]) -> str | None:
    if not block:
        return None
    first = block[0]
    for name in (*PORTAL_NAMES, *PUBLIC_GUIDELINE_NAMES, *INFRASTRUCTURE_NAMES):
        if f'"{name}"' in first or f"'{name}'" in first:
            return name
    if first.startswith("  - name: "):
        return first.split(":", 1)[1].strip().strip('"\'')
    return None


def ensure_hidden(block: list[str]) -> list[str]:
    if any(line.strip() == "hidden: true" for line in block):
        return block
    result = block[:]
    insert_at = 2 if len(result) >= 2 and result[1].lstrip().startswith("href:") else 1
    result.insert(insert_at, "    hidden: true")
    return result


def curate_navigation(text: str) -> str:
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

    found_portal: set[str] = set()
    found_public: set[str] = set()
    output_blocks: list[list[str]] = []
    hidden_names: list[str] = []

    for block in blocks:
        name = top_level_name(block)
        if name in PORTAL_NAMES:
            found_portal.add(name)
            continue
        if name in PUBLIC_GUIDELINE_NAMES:
            found_public.add(name)
            output_blocks.append(block)
            continue
        if name in INFRASTRUCTURE_NAMES:
            output_blocks.append(ensure_hidden(block))
            continue

        # Keep unreleased recommendation content buildable for direct/internal
        # links, but hide its entire top-level branch from the public TOC.
        output_blocks.append(ensure_hidden(block))
        if name:
            hidden_names.append(name)

    missing_portal = [name for name in PORTAL_NAMES if name not in found_portal]
    if missing_portal:
        raise SystemExit(
            "Portal navigation pages were not found in generated TOC: "
            + ", ".join(missing_portal)
        )

    missing_public = [name for name in PUBLIC_GUIDELINE_NAMES if name not in found_public]
    if missing_public:
        raise SystemExit(
            "Required public guideline sections were not found in generated TOC: "
            + ", ".join(missing_public)
        )

    output_lines = prefix[:]
    for block in output_blocks:
        output_lines.extend(block)

    print("Public recommendation sections: " + ", ".join(PUBLIC_GUIDELINE_NAMES))
    if hidden_names:
        print("Hidden recommendation sections: " + ", ".join(hidden_names))
    print("Removed portal pages from recommendations TOC: " + ", ".join(PORTAL_NAMES))
    return "\n".join(output_lines).rstrip() + "\n"


def main() -> None:
    text = GUIDELINES_TOC.read_text(encoding="utf-8")
    GUIDELINES_TOC.write_text(curate_navigation(text), encoding="utf-8")


if __name__ == "__main__":
    main()
