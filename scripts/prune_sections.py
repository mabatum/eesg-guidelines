"""Оставляет на сайте только разделы из config/site-scope.json.

Заменяет прежний split_portal_navigation.py: тот прятал лишние ветки из
навигации, но оставлял их в сборке и доступными по прямой ссылке. Здесь ветки
удаляются полностью, а ссылки на них в оставшемся тексте превращаются в обычный
текст, чтобы сборка не содержала битых переходов.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

GEN_ROOT = Path("docs/gen_docs")
GUIDELINES_TOC = GEN_ROOT / "toc.yaml"
SCOPE_FILE = Path("config/site-scope.json")


def load_scope() -> tuple[list[str], list[str]]:
    raw = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))
    publish = [str(name) for name in raw.get("publish", [])]
    hidden = [str(name) for name in raw.get("keep_hidden", [])]
    if not publish:
        raise SystemExit(f"Не задан ни один публикуемый раздел: {SCOPE_FILE}")
    return publish, hidden


def top_level_dirs() -> list[str]:
    return sorted(p.name for p in GEN_ROOT.iterdir() if p.is_dir())


def toc_blocks(text: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    try:
        items_index = lines.index("items:")
    except ValueError as exc:
        raise SystemExit(f"Не найден список items в {GUIDELINES_TOC}") from exc

    prefix = lines[: items_index + 1]
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
    return prefix, blocks


def block_section(block: list[str]) -> str | None:
    """Каталог раздела определяется по href первой страницы блока."""
    for line in block:
        match = re.search(r'href:\s*"?([\w./-]+)"?', line)
        if match:
            return match.group(1).strip("/").split("/", 1)[0]
    return None


def ensure_hidden(block: list[str]) -> list[str]:
    if any(line.strip() == "hidden: true" for line in block):
        return block
    result = block[:]
    insert_at = 2 if len(result) >= 2 and result[1].lstrip().startswith("href:") else 1
    result.insert(insert_at, "    hidden: true")
    return result


def prune_toc(publish: list[str], hidden: list[str]) -> None:
    prefix, blocks = toc_blocks(GUIDELINES_TOC.read_text(encoding="utf-8"))
    kept, dropped, found = [], [], set()
    for block in blocks:
        section = block_section(block)
        if section in publish:
            found.add(section)
            kept.append(block)
        elif section in hidden:
            kept.append(ensure_hidden(block))
        else:
            dropped.append(section or "?")

    missing = [name for name in publish if name not in found]
    if missing:
        raise SystemExit("Публикуемые разделы не найдены в оглавлении: " + ", ".join(missing))

    out = prefix[:]
    for block in kept:
        out.extend(block)
    GUIDELINES_TOC.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"Оглавление: оставлено {len(kept)}, убрано {len(dropped)} — {', '.join(sorted(set(dropped)))}")


def drop_directories(removed: list[str]) -> None:
    for name in removed:
        shutil.rmtree(GEN_ROOT / name)
    print(f"Удалено каталогов: {len(removed)} — {', '.join(removed)}")


def neutralise_links(removed: list[str]) -> None:
    """[текст](../../section/...) -> текст, чтобы не осталось битых ссылок."""
    if not removed:
        return
    pattern = re.compile(
        r"\[([^\]\n]+)\]\((?:\.{1,2}/)*(?:" + "|".join(map(re.escape, removed)) + r")/[^)\s]*\)"
    )
    touched = total = 0
    for path in list(GEN_ROOT.rglob("*.md")) + [Path("docs/index.md"), Path("docs/updates.md")]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        new_text, count = pattern.subn(r"\1", text)
        if count:
            path.write_text(new_text, encoding="utf-8")
            touched += 1
            total += count
    print(f"Ссылки на убранные разделы обезврежены: {total} в {touched} файлах")


def main() -> None:
    publish, hidden = load_scope()
    present = top_level_dirs()
    removed = [name for name in present if name not in publish and name not in hidden]

    missing = [name for name in publish if name not in present]
    if missing:
        raise SystemExit("Публикуемые разделы отсутствуют в выгрузке: " + ", ".join(missing))

    prune_toc(publish, hidden)
    neutralise_links(removed)
    drop_directories(removed)
    print("Публикуются разделы: " + ", ".join(publish))


if __name__ == "__main__":
    main()
