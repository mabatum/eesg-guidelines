"""Build the new reading interface into docs-html/new/index.html.

The interface is one self-contained page (new-interface/template.html) that
renders the same text as the Diplodoc site. This script reads every published
page from docs/gen_docs (the Wiki export after prune_sections.py and the bone
overlay) in the order of docs/gen_docs/toc.yaml and turns it into page data:
block-level HTML with stable block ids for remarks, outline, tables and a search
index down to paragraphs and table rows. Remarks go to the same Google Form as on
the main site; its public address and field ids are read from
docs/_assets/script/feedback-config.js.

Run after `npm run prepare:docs` and `npm run build:docs` (it writes into docs-html/new/).
"""
from __future__ import annotations

import html
import json
import posixpath
import re
from pathlib import Path

SOURCE = Path("docs/gen_docs")
TOC = SOURCE / "toc.yaml"
TEMPLATE = Path("new-interface/template.html")
OUTPUT = Path("docs-html/new/index.html")
FEEDBACK = Path("docs/_assets/script/feedback-config.js")
SOURCES = "https://mabatum.github.io/eesg-guidelines/_assets/sources/"
HOME = "home"

KR = {
    "532": ("КР 532_5", SOURCES + "kr532-5-2025.pdf"),
    "515": ("КР 515_3", SOURCES + "kr515-3-2025.pdf"),
    "618": ("КР 618_3", SOURCES + "kr618-3-2024.pdf"),
    "460": ("КР 460_4", SOURCES + "kr460-4-2024.pdf"),
    "551": ("КР 551_3", SOURCES + "kr551-3-2024.pdf"),
}
# Section overview (Wiki path) -> card text and the guideline the section is built on.
SECTIONS = {
    "bone-sarcomas": ("Остеосаркома, саркома Юинга, хондросаркома, гигантоклеточная опухоль, хордома и редкие опухоли кости.", "532"),
    "general-principles": ("Маршрутизация, биопсия, молекулярная диагностика, стадирование, хирургия, облучение и системная терапия сарком мягких тканей.", "515"),
    "soft-tissue-sarcomas": ("Липосаркомы, лейомиосаркома, НПС, ангиосаркома, синовиальная саркома и другие подтипы.", "515"),
    "specific-tumor-groups": ("Десмоид, ДФСП, СФО, ГИСО, забрюшинные саркомы, саркома Капоши и другие отдельные группы.", "515"),
}
PAGE_KR = {  # pages built on another guideline than their section
    "specific-tumor-groups/retroperitoneal-sarcoma": "618",
    "soft-tissue-sarcomas/leiomyosarcoma/uterine-sarcomas": "460",
    "specific-tumor-groups/gist": "551",
}

META_RE = re.compile(r"^\*\*Статус:\*\*\s*(.+?)(?:\s+·\s+\*\*Версия:\*\*\s*(.+?))?\s+·\s+\*\*Обновлено:\*\*\s*(\S+)\s*$")
LINK_RE = re.compile(r"\[((?:\[[^\]]*\]|[^\[\]])+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")
CITE_RE = re.compile(r"^\[(\d+)(?:, с\. [\d–-]+)?\]$")
MARK_RE = re.compile(r"‡†|[†‡§¶]")
NOTE_RE = re.compile(r"^\*\*(‡†|[†‡§¶])\*\*\s*(.+)$", re.S)
LABEL_RE = re.compile(r"^<strong>(?:\[(Рекомендуется|Предлагается)\]\s*|(Рекомендуется|Рекомендуются|Предлагается|Предлагаются)\s+)")
LABEL_CLASS = {"Рекомендуется": "lbl-r", "Рекомендуются": "lbl-r", "Предлагается": "lbl-p", "Предлагаются": "lbl-p"}

LEGEND = """## Как читать пометки

**Рекомендуется** - положение клинических рекомендаций Минздрава России или RUSSCO; ссылка ведёт на страницу документа.

**Предлагается** - дополнение рабочей группы EESG: данные исследований, руководств ESMO и ASCO, обзоров UpToDate, новые одобренные препараты.

| Знак | Значение |
|---|---|
| ‡ | лекарственной опции нет в клинических рекомендациях Минздрава для этой ситуации; препарат зарегистрирован в России по этому показанию |
| ‡† | опции нет в клинических рекомендациях Минздрава; препарат зарегистрирован в России, но не по этому показанию |
| § | опции нет в клинических рекомендациях Минздрава; препарат в России не зарегистрирован |
| ¶ | препарат зарегистрирован в России, но не входит в перечень ЖНВЛП |
| † | опция есть в клинических рекомендациях Минздрава с пометкой «#»: применение вне инструкции |

У знаков ‡, ‡† и § в сноске указано: назначение данного режима (препарата) может быть рассмотрено врачебной комиссией регионального центра и онкологическим консилиумом федерального центра (НМИЦ) высшего уровня.
"""


def slug_for(path: str) -> str:
    """Page key in the interface. Bone pages keep the keys of the first edition so
    that remarks already left on them still find their blocks."""
    if path == "":
        return HOME
    if path.startswith("bone-sarcomas/"):
        return path.split("/", 1)[1]
    if path == "general-principles":
        return "principles"
    return path


def read_toc() -> list[tuple[str, str, int]]:
    """(Wiki path, menu title, depth) in menu order; depth 0 is a section overview."""
    out, name = [], None
    for line in TOC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\s*)- name:\s*(.+)$", line)
        if m:
            name = (len(m.group(1)), json.loads(m.group(2)))
            continue
        m = re.match(r"^\s*href:\s*(.+)$", line)
        if m and name:
            href = json.loads(m.group(1))
            path = href[: -len("index.md")].rstrip("/") if href.endswith("index.md") else href
            out.append((path, name[1], (name[0] - 2) // 4))
            name = None
    if not out:
        raise SystemExit(f"{TOC}: no pages")
    return out


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
    def __init__(self, slug: str, nav: str, path: str, slugs: dict[str, str]):
        self.slug, self.nav, self.path, self.slugs = slug, nav, path, slugs
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
        self.notes: dict[str, str] = {}
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
        s = MARK_RE.sub(lambda m: f'<span class="dag" data-tip="dag" data-d="{m.group(0)}" tabindex="0">{m.group(0)}</span>', s)
        return s

    def target(self, url: str) -> str | None:
        """Interface key of an internal link (relative path to another index.md)."""
        if re.match(r"^[a-z]+:", url) or url.startswith("#"):
            return None
        path = url.split("#", 1)[0]
        if not path.endswith("index.md"):
            return None
        full = posixpath.normpath(posixpath.join(self.path, path))
        full = "" if full in (".", "index.md") else full[: -len("/index.md")]
        return self.slugs.get(full)

    def link(self, label: str, url: str) -> str:
        cite = CITE_RE.match(label)
        if cite:
            full = self.refs.get(cite.group(1), "")
            return (f'<a class="cite" data-tip="src" data-full="{html.escape(full)}" href="{html.escape(url)}" '
                    f'target="_blank" rel="noopener">{html.escape(label)}</a>')
        target = self.target(url)
        if target:
            return f'<a class="int" href="#{target}" data-go="{target}">{self.text(label)}</a>'
        if not re.match(r"^[a-z]+:", url):
            return self.text(label)  # a page the interface does not show
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
        note = NOTE_RE.match(md)
        if note:
            cls = ' class="fn"'
            self.notes[note.group(1)] = plain(note.group(2))
        elif md.startswith("**"):
            cls = ' class="stmt"'
        body = self.inline(md)
        label = LABEL_RE.match(body)
        if label:
            # a tag [Рекомендуется] is replaced by the label; a statement that opens with the
            # verb keeps its wording and the verb itself becomes the label
            word = label.group(1) or label.group(2)
            body = f'<strong><span class="lbl {LABEL_CLASS[word]}">{word}</span> ' + body[label.end():]
        self.html.append(f'<p data-b="{bid}"{cls}>{body}</p>')
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


def parse(page: Page, text: str) -> tuple[str, dict]:
    # reference texts for citation tooltips
    lit = text.split("## Список литературы", 1)
    if len(lit) == 2:
        for m in re.finditer(r"^(\d+)\.\s+(.+)$", lit[1], re.M):
            page.refs[m.group(1)] = plain(m.group(2))
    title, meta = page.nav, None
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
            # the export adds its own line; a line written in the page itself has the edition
            if meta is None or mm.group(2):
                meta = {"status": mm.group(1), "version": mm.group(2) or "", "date": mm.group(3)}
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
    return title, meta or {"status": "", "version": "", "date": ""}


def build_page(path: str, nav: str, depth: int, parent: str | None, slugs: dict[str, str]) -> dict:
    slug = slugs[path]
    source = SOURCE / (f"{path}/index.md" if path else "index.md")
    page = Page(slug, nav, path, slugs)
    title, meta = parse(page, source.read_text(encoding="utf-8"))
    section = path.split("/", 1)[0]
    kr = KR[PAGE_KR.get(path) or SECTIONS[section][1]]
    return {
        "slug": slug, "title": title, "nav": nav, "meta": meta, "basis": "",
        "sec": slugs[section], "lvl": depth, "parent": slugs[parent] if parent is not None else None,
        "kr": {"label": kr[0], "url": kr[1]}, "notes": page.notes,
        "html": "".join(page.html), "outline": page.outline, "tables": page.tables,
        "stats": {"sections": page.h2, "tables": len(page.tables)},
        "_search": page.search,
    }


def build_home(edition: dict, slugs: dict[str, str], count: dict[str, int]) -> dict:
    page = Page(HOME, "Главная", "", slugs)
    parse(page, LEGEND)
    return {
        "slug": HOME, "title": "Клинические рекомендации EESG по саркомам костей и мягких тканей", "nav": "Главная",
        "meta": edition, "basis": "", "sec": None, "lvl": -1, "parent": None, "kr": None, "notes": page.notes,
        "html": "".join(page.html), "outline": page.outline, "tables": page.tables,
        "stats": {"sections": page.h2, "tables": len(page.tables)},
        "_search": page.search,
    }


def main() -> None:
    toc = read_toc()
    slugs = {path: slug_for(path) for path, _, _ in toc}
    slugs[""] = HOME
    if len(set(slugs.values())) != len(slugs):
        raise SystemExit("two pages map to the same interface key")
    pages, search, stack = [], [], []
    for path, nav, depth in toc:
        if path.split("/", 1)[0] not in SECTIONS:
            raise SystemExit(f"section of {path} is not described in SECTIONS")
        stack = stack[:depth]
        parent = stack[-1] if stack else None
        stack.append(path)
        p = build_page(path, nav, depth, parent, slugs)
        search += p.pop("_search")
        pages.append(p)
    edition = next(p["meta"] for p in pages if p["slug"] == "bone-sarcomas")
    count = {}
    for p in pages:
        count[p["sec"]] = count.get(p["sec"], 0) + 1
    home = build_home(edition, slugs, count)
    search = home.pop("_search") + search
    pages.insert(0, home)
    data = {
        "edition": edition["version"], "date": edition["date"], "status": edition["status"], "basis": "",
        "feedback": feedback_config(),
        "pages": pages,
        "cards": [{"slug": slugs[path], "desc": SECTIONS[path][0], "count": count.get(slugs[path], 0)}
                  for path, _, depth in toc if depth == 0],
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
