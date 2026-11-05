"""Build the new reading interface into docs-html/new/index.html.

The interface is one self-contained page (new-interface/template.html) that
renders the same reviewed manuscript as the Diplodoc site. This script turns
content-reviewed/bone-sarcomas into the page data: block-level HTML with stable
block ids for remarks, outline, tables and a search index down to paragraphs
and table rows. Remarks go to the same Google Form as on the main site; its
public address and field ids are read from docs/_assets/script/feedback-config.js.

Run after `npm run build:docs` (it writes into docs-html/new/).
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

SOURCE = Path("content-reviewed/bone-sarcomas")
TEMPLATE = Path("new-interface/template.html")
OUTPUT = Path("docs-html/new/index.html")
FEEDBACK = Path("docs/_assets/script/feedback-config.js")
PDF = "https://mabatum.github.io/eesg-guidelines/_assets/sources/kr532-5-2025.pdf"
HOME = "bone-sarcomas"

ORDER = [
    ("bone-sarcomas", "Саркомы костей", None),
    ("general-principles", "Общие принципы", "Маршрутизация, обследование, биопсия, стадирование, хирургия, сопроводительная терапия и наблюдение."),
    ("osteosarcoma-adults", "Остеосаркома", "AP и MAP, лечебный патоморфоз, высокодозные режимы, метастазы и рецидив."),
    ("ewing-sarcoma-adults", "Саркома Юинга", "Костный мозг, VDC/IE, локальное лечение, облучение лёгких, повторные линии."),
    ("chondrosarcoma-adults", "Хондросаркома", "Тактика по морфологическому варианту, таргетные препараты при распространённой форме."),
    ("giant-cell-tumor-of-bone", "Гигантоклеточная опухоль", "Объём операции, деносумаб до операции и длительно, лёгочные очаги."),
    ("chordoma", "Хордома", "Операция и облучение по локализации, ингибиторы тирозинкиназ, длительное наблюдение."),
    ("rare-bone-tumours", "Редкие опухоли кости", "Недифференцированная плеоморфная саркома, лейомиосаркома, сосудистые опухоли, адамантинома."),
]

META_RE = re.compile(r"^\*\*Статус:\*\*\s*(.+?)\s+·\s+\*\*Версия:\*\*\s*(.+?)\s+·\s+\*\*Обновлено:\*\*\s*(\S+)\s*$")
LINK_RE = re.compile(r"\[((?:\[[^\]]*\]|[^\[\]])+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")
CITE_RE = re.compile(r"^\[(\d+)(?:, с\. [\d–-]+)?\]$")
FOOT = {"†": "dag", "‡": "dag"}


def source_path(slug: str) -> Path:
    return SOURCE / ("index.md" if slug == HOME else f"{slug}/index.md")


def feedback_config() -> dict:
    text = FEEDBACK.read_text(encoding="utf-8")
    keys = ("formUrl", "contextEntry", "commentEntry", "nameEntry", "contactEntry")
    cfg = {}
    for key in keys:
        m = re.search(rf"{key}:\s*'([^']+)'", text)
        if not m:
            raise SystemExit(f"feedback-config.js: no {key}")
        cfg[key] = m.group(1)
    return cfg


def plain(md: str) -> str:
    """Text of an inline fragment as the reader sees it (for search and tooltips)."""
    t = LINK_RE.sub(lambda m: m.group(1), md)
    t = t.replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", t).strip()


class Page:
    def __init__(self, slug: str, nav: str):
        self.slug, self.nav = slug, nav
        self.sec = 0
        self.blk = 0
        self.sec_title = ""
        self.h2_title = ""
        self.sub_title = ""
        self.html: list[str] = []
        self.outline: list[dict] = []
        self.tables: list[dict] = []
        self.search: list[list] = []
        self.refs: dict[str, str] = {}
        self.h2 = 0

    def bid(self) -> str:
        self.blk += 1
        return f"{self.slug}.{self.sec}.{self.blk}"

    # ---------- inline ----------
    def inline(self, md: str) -> str:
        out, pos = [], 0
        for m in LINK_RE.finditer(md):
            out.append(self.text(md[pos:m.start()]))
            out.append(self.link(m.group(1), m.group(2)))
            pos = m.end()
        out.append(self.text(md[pos:]))
        return "".join(out)

    def text(self, s: str) -> str:
        s = html.escape(s, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"[†‡]", lambda m: f'<span class="dag" data-tip="dag" data-d="{m.group(0)}" tabindex="0">{m.group(0)}</span>', s)
        return s

    def link(self, label: str, url: str) -> str:
        cite = CITE_RE.match(label)
        if cite:
            full = self.refs.get(cite.group(1), "")
            return (f'<a class="cite" data-tip="src" data-full="{html.escape(full)}" href="{html.escape(url)}" '
                    f'target="_blank" rel="noopener">{html.escape(label)}</a>')
        m = re.fullmatch(r"(?:\.\./)?(?:([\w-]+)/)?index\.md", url)
        if m:
            target = m.group(1) or HOME
            return f'<a class="int" href="#{target}" data-go="{target}">{self.text(label)}</a>'
        return f'<a class="ext" href="{html.escape(url)}" target="_blank" rel="noopener">{self.text(label)}</a>'

    # ---------- blocks ----------
    def heading(self, level: int, title: str) -> None:
        # Section numbers change only at h2; an h3 is a block inside its h2
        # section, as the interface expects when it builds the path of a remark.
        text = plain(title)
        if level == 2:
            self.sec += 1
            self.blk = 0
            self.h2 += 1
            self.h2_title = text
            self.sub_title = ""
            bid = f"{self.slug}.{self.sec}.0"
            self.sec_title = text
        else:
            bid = self.bid()
            self.sub_title = text
            self.sec_title = (self.h2_title + " › " + text) if self.h2_title else text
        self.html.append(f'<h{level} data-b="{bid}" id="h_{bid}">{self.inline(title)}</h{level}>')
        self.outline.append({"id": bid, "t": text, "l": level})
        self.search.append([bid, self.slug, self.sec_title, "h", text])

    def para(self, md: str) -> None:
        bid = self.bid()
        cls = ""
        if re.match(r"^\*\*[†‡]\*\*", md):
            cls = ' class="fn"'
        elif md.startswith("**"):
            cls = ' class="stmt"'
        self.html.append(f'<p data-b="{bid}"{cls}>{self.inline(md)}</p>')
        self.search.append([bid, self.slug, self.sec_title, "p", plain(md)])

    def quote(self, md: str) -> None:
        bid = self.bid()
        self.html.append(f'<blockquote class="cm" data-b="{bid}"><p>{self.inline(md)}</p></blockquote>')
        self.search.append([bid, self.slug, self.sec_title, "p", plain(md)])

    def items(self, ordered: bool, items: list[str], refs: bool) -> None:
        tag = "ol" if ordered else "ul"
        cls = ' class="refs"' if refs else ""
        lis = []
        for it in items:
            bid = self.bid()
            lis.append(f'<li data-b="{bid}">{self.inline(it)}</li>')
            self.search.append([bid, self.slug, self.sec_title, "li", plain(it)])
        self.html.append(f"<{tag}{cls}>" + "".join(lis) + f"</{tag}>")

    def table(self, rows: list[list[str]]) -> None:
        bid = self.bid()
        head, body = rows[0], rows[1:]
        heads = [plain(h) for h in head]
        out = [f'<div class="tbl tbl-{len(head)}" data-b="{bid}"><div class="tbl-sc"><table>', "<thead><tr>"]
        out += [f"<th>{self.inline(h)}</th>" for h in head]
        out.append("</tr></thead><tbody>")
        for i, r in enumerate(body):
            rid = f"{bid}.r{i}"
            cells = "".join(f'<td data-label="{html.escape(heads[j] if j < len(heads) else "")}">{self.inline(c)}</td>' for j, c in enumerate(r))
            out.append(f'<tr data-r="{rid}">{cells}</tr>')
            self.search.append([rid, self.slug, self.sec_title, "row", " · ".join(plain(c) for c in r)])
        out.append("</tbody></table></div></div>")
        self.html.append("".join(out))
        self.tables.append({"id": bid, "t": self.sub_title or self.h2_title or self.nav, "sub": heads[0] if heads else ""})


def split_row(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def build_page(slug: str, nav: str) -> dict:
    text = source_path(slug).read_text(encoding="utf-8")
    page = Page(slug, nav)
    # reference texts for citation tooltips
    lit = text.split("## Список литературы", 1)
    if len(lit) == 2:
        for m in re.finditer(r"^(\d+)\.\s+(.+)$", lit[1], re.M):
            page.refs[m.group(1)] = plain(m.group(2))
    title, meta = nav, {"status": "", "version": "", "date": ""}
    blocks = re.split(r"\n\s*\n", text.strip())
    in_refs = False
    for block in blocks:
        lines = block.split("\n")
        first = lines[0]
        if first.startswith("# "):
            title = first[2:].strip()
            continue
        mm = META_RE.match(first)
        if mm:
            meta = {"status": mm.group(1), "version": mm.group(2), "date": mm.group(3)}
            continue
        hm = re.match(r"^(#{2,3})\s+(.+)$", first)
        if hm:
            page.heading(len(hm.group(1)), hm.group(2).strip())
            in_refs = hm.group(2).strip() == "Список литературы"
            rest = "\n".join(lines[1:]).strip()
            if rest:
                page.para(rest)
            continue
        if first.startswith("|"):
            rows = [split_row(l) for l in lines if l.strip().startswith("|")]
            rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            page.table(rows)
            continue
        if first.startswith(">"):
            page.quote(" ".join(l.lstrip(">").strip() for l in lines))
            continue
        if re.match(r"^\d+\.\s", first):
            page.items(True, [re.sub(r"^\d+\.\s+", "", l) for l in lines if l.strip()], in_refs)
            continue
        if first.startswith("- "):
            page.items(False, [l[2:] for l in lines if l.strip()], False)
            continue
        # a short label line before a list ("Требования к выполнению биопсии:")
        page.para(" ".join(l.strip() for l in lines))
    return {
        "slug": slug, "title": title, "nav": nav, "meta": meta, "basis": "",
        "html": "".join(page.html), "outline": page.outline, "tables": page.tables,
        "stats": {"sections": page.h2, "tables": len(page.tables)},
        "_search": page.search,
    }


def main() -> None:
    pages, search = [], []
    for slug, nav, _ in ORDER:
        p = build_page(slug, nav)
        search += p.pop("_search")
        pages.append(p)
    home = pages[0]["meta"]
    data = {
        "edition": home["version"], "date": home["date"], "status": home["status"], "basis": "",
        "pdf": PDF, "feedback": feedback_config(),
        "pages": pages,
        "cards": [{"slug": slug, "desc": desc} for slug, _, desc in ORDER if desc],
        "search": search,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__SITE_DATA__") != 1:
        raise SystemExit("template must contain exactly one __SITE_DATA__ placeholder")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(template.replace("__SITE_DATA__", payload), encoding="utf-8")
    print(f"New interface: {len(pages)} pages, {len(search)} search entries, edition {data['edition']} -> {OUTPUT}")


if __name__ == "__main__":
    main()
