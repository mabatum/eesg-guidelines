"""Pull the bone-sarcoma pages from Yandex Wiki into content-reviewed/.

The Wiki is the editable source of the bone section. Before every site build this
script fetches the eight pages, turns absolute Wiki links into relative site links
and overwrites content-reviewed/bone-sarcomas, which the rest of the pipeline reads.
Links to Wiki sections that the site does not publish become plain text.

Needs WIKI_TOKEN and ORG_ID, like export_wiki_neutral.py.
"""
import re
from pathlib import Path

import export_wiki

ROOT = "eesg/bone-sarcomas"
ROUTES = (
    "general-principles", "osteosarcoma-adults", "ewing-sarcoma-adults",
    "chondrosarcoma-adults", "giant-cell-tumor-of-bone", "chordoma",
    "rare-bone-tumours",
)
OUTPUT = Path("content-reviewed/bone-sarcomas")
WIKI_LINK = re.compile(r"\[([^\]]+)\]\((?:https://wiki\.yandex\.ru)?/(eesg[^)\s#]*)(#[^)\s]*)?\)")


def to_site(content: str, route: str | None) -> str:
    """route is None for the section overview, otherwise the child page slug."""
    up = "" if route is None else "../"

    def replace(match: re.Match) -> str:
        text, slug, anchor = match.group(1), match.group(2).rstrip("/"), match.group(3) or ""
        if slug == ROOT:
            return f"[{text}]({up}index.md{anchor})"
        if slug.startswith(ROOT + "/") and slug[len(ROOT) + 1:] in ROUTES:
            return f"[{text}]({up}{slug[len(ROOT) + 1:]}/index.md{anchor})"
        return text

    return WIKI_LINK.sub(replace, content).rstrip("\n") + "\n"


def main() -> None:
    export_wiki.require_env()
    session = export_wiki.authenticated_session()
    pages = {None: ROOT, **{route: f"{ROOT}/{route}" for route in ROUTES}}
    texts = {}
    for route, slug in pages.items():
        content = export_wiki.get_page(session, slug).get("content") or ""
        if not content.startswith("# ") or "## Список литературы" not in content:
            raise SystemExit(f"Wiki page {slug} has no title or no «Список литературы»; nothing was overwritten.")
        texts[route] = to_site(content, route)
    for route, text in texts.items():
        path = OUTPUT / "index.md" if route is None else OUTPUT / route / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"Pulled {len(texts)} bone pages from Wiki into {OUTPUT}.")


if __name__ == "__main__":
    main()
