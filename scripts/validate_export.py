from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

DOCS_ROOT = Path("docs").resolve()
GEN_ROOT = DOCS_ROOT / "gen_docs"

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")
RECOMMENDATION_HEADING_RE = re.compile(
    r"^#{2,4}\s+(?:Клиническая\s+)?Рекомендация(?:\s+\d+(?:\.\d+)*)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+\S")


def local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>")
    if not target or target.startswith("#"):
        return None

    if " \"" in target:
        target = target.split(" \"", 1)[0]

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None

    path = unquote(parsed.path)
    if not path:
        return None

    candidate = (source.parent / path).resolve()
    try:
        candidate.relative_to(DOCS_ROOT)
    except ValueError:
        return None

    if path.endswith("/"):
        candidate = candidate / "index.md"
    return candidate


def heading_levels(text: str) -> list[tuple[int, int]]:
    """Return (line_number, heading_level), ignoring fenced code blocks."""
    result: list[tuple[int, int]] = []
    in_fence = False
    fence_marker = ""

    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue

        match = HEADING_RE.match(line)
        if match:
            result.append((number, len(match.group("marks"))))
    return result


def validate() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not GEN_ROOT.exists():
        errors.append("Generated documentation directory docs/gen_docs does not exist.")
    else:
        pages = sorted(GEN_ROOT.rglob("*.md"))
        if not pages:
            errors.append("No generated Markdown pages found in docs/gen_docs.")

        for page in pages:
            relative = page.relative_to(DOCS_ROOT)
            text = page.read_text(encoding="utf-8")

            if not text.lstrip().startswith("# "):
                errors.append(f"{relative}: missing H1 heading")

            if "https://wiki.yandex.ru/eesg" in text or "](/eesg/" in text:
                errors.append(f"{relative}: contains an unreplaced internal Yandex Wiki link")

            if RECOMMENDATION_HEADING_RE.search(text):
                errors.append(
                    f"{relative}: explicit recommendation heading was not converted to a callout"
                )

            if "TODO" in text or "TBD" in text:
                warnings.append(f"{relative}: contains TODO/TBD marker")

            levels = heading_levels(text)
            for (prev_line, prev_level), (line_no, level) in zip(levels, levels[1:]):
                if level > prev_level + 1:
                    warnings.append(
                        f"{relative}:{line_no}: heading jumps H{prev_level} -> H{level}; "
                        "this may weaken the in-page navigation"
                    )

            for match in MARKDOWN_LINK_RE.finditer(text):
                candidate = local_target(page, match.group("target"))
                if candidate is None:
                    continue
                if candidate.suffix.lower() == ".md" and not candidate.exists():
                    errors.append(
                        f"{relative}: broken local Markdown link -> {match.group('target')}"
                    )

    if warnings:
        print("Validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"Validation failed with {len(errors)} error(s).")
        return 1

    page_count = len(list(GEN_ROOT.rglob("*.md"))) if GEN_ROOT.exists() else 0
    print(f"Validation passed for {page_count} generated Markdown page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
