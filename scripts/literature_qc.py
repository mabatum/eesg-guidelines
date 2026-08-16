from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

import requests

GEN_ROOT = Path("docs/gen_docs")
CLINICAL_ROOTS = {
    "general-principles",
    "soft-tissue-sarcomas",
    "bone-sarcomas",
    "specific-tumor-groups",
    "drugs-and-regimens",
    "special-clinical-situations",
}
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)", re.IGNORECASE)
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


def title_of(text: str, fallback: str) -> str:
    match = H1_RE.search(text)
    return match.group(1).strip() if match else fallback


def literature_section(text: str) -> str | None:
    matches = list(H2_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip().casefold() != "литература":
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[start:end].strip()
    return None


def canonical_url(raw: str) -> str:
    parsed = urlsplit(raw.strip())
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, host, path, parsed.query, ""))


def identifiers(url: str) -> tuple[str | None, str | None, str | None]:
    parsed = urlsplit(url)
    host = parsed.netloc.lower()
    path = unquote(parsed.path.lstrip("/"))

    if host in {"doi.org", "dx.doi.org"}:
        doi = path.lower()
        return (doi if DOI_RE.fullmatch(doi) else None, None, None if DOI_RE.fullmatch(doi) else doi)

    if host == "pubmed.ncbi.nlm.nih.gov":
        pmid = path.split("/", 1)[0]
        return (None, pmid if pmid.isdigit() else None, None if pmid.isdigit() else pmid)

    return (None, None, None)


def check_url(url: str) -> dict:
    headers = {
        "User-Agent": "EESG-Guidelines-QC/1.0 (+https://eesg.ru/)",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            allow_redirects=True,
            stream=True,
            timeout=(3.0, 5.0),
        )
        status = response.status_code
        final_url = response.url
        response.close()
        if status in {400, 404, 410}:
            state = "broken"
        elif 200 <= status < 400:
            state = "ok"
        else:
            state = "inconclusive"
        return {"url": url, "state": state, "status": status, "final_url": final_url}
    except requests.RequestException as exc:
        return {"url": url, "state": "inconclusive", "status": None, "error": str(exc)}


def collect_pages() -> list[dict]:
    pages: list[dict] = []
    for path in sorted(GEN_ROOT.rglob("index.md")):
        relative = path.relative_to(GEN_ROOT)
        if not relative.parts or relative.parts[0] not in CLINICAL_ROOTS:
            continue
        text = path.read_text(encoding="utf-8")
        section = literature_section(text)
        urls = LINK_RE.findall(section or "")
        pages.append(
            {
                "path": relative.as_posix(),
                "title": title_of(text, relative.as_posix()),
                "has_literature": section is not None,
                "literature_empty": section is not None and not section.strip(),
                "urls": urls,
            }
        )
    return pages


def build_report(check_external: bool) -> dict:
    pages = collect_pages()
    pages_without_literature = [page for page in pages if not page["has_literature"]]
    empty_literature = [page for page in pages if page["literature_empty"]]

    duplicate_entries: list[dict] = []
    invalid_identifiers: list[dict] = []
    all_urls: set[str] = set()
    doi_set: set[str] = set()
    pmid_set: set[str] = set()

    for page in pages:
        seen: dict[str, str] = {}
        for raw_url in page["urls"]:
            url = canonical_url(raw_url)
            all_urls.add(url)
            doi, pmid, malformed = identifiers(url)
            if doi:
                doi_set.add(doi)
                key = f"doi:{doi}"
            elif pmid:
                pmid_set.add(pmid)
                key = f"pmid:{pmid}"
            else:
                key = f"url:{url}"

            if malformed is not None:
                invalid_identifiers.append(
                    {"page": page["path"], "title": page["title"], "url": url, "value": malformed}
                )

            if key in seen:
                duplicate_entries.append(
                    {"page": page["path"], "title": page["title"], "url": url, "duplicate_of": seen[key]}
                )
            else:
                seen[key] = url

    live_results: list[dict] = []
    if check_external and all_urls:
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(check_url, url): url for url in sorted(all_urls)}
            for future in as_completed(futures):
                live_results.append(future.result())
        live_results.sort(key=lambda item: item["url"])

    broken = [item for item in live_results if item["state"] == "broken"]
    inconclusive = [item for item in live_results if item["state"] == "inconclusive"]

    return {
        "clinical_pages": len(pages),
        "pages_with_literature": sum(1 for page in pages if page["has_literature"]),
        "pages_without_literature": pages_without_literature,
        "empty_literature": empty_literature,
        "unique_literature_urls": len(all_urls),
        "unique_dois": len(doi_set),
        "unique_pmids": len(pmid_set),
        "duplicate_entries": duplicate_entries,
        "invalid_identifiers": invalid_identifiers,
        "external_checked": check_external,
        "external_results": live_results,
        "broken_links": broken,
        "inconclusive_links": inconclusive,
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Literature QC",
        "",
        f"- Clinical pages checked: **{report['clinical_pages']}**",
        f"- Pages with `## Литература`: **{report['pages_with_literature']}**",
        f"- Pages without literature section: **{len(report['pages_without_literature'])}**",
        f"- Unique literature URLs: **{report['unique_literature_urls']}**",
        f"- Unique DOI: **{report['unique_dois']}**; PubMed IDs: **{report['unique_pmids']}**",
        f"- Duplicate references within the same page: **{len(report['duplicate_entries'])}**",
        f"- Malformed DOI/PMID identifiers: **{len(report['invalid_identifiers'])}**",
    ]

    if report["external_checked"]:
        lines.extend(
            [
                f"- Confirmed broken external links (HTTP 400/404/410): **{len(report['broken_links'])}**",
                f"- Inconclusive external checks (403/429/5xx/timeouts etc.): **{len(report['inconclusive_links'])}**",
            ]
        )
    lines.append("")

    def add_pages(title: str, items: list[dict]) -> None:
        if not items:
            return
        lines.extend([f"## {title}", ""])
        for item in items:
            lines.append(f"- `{item['path']}` — {item['title']}")
        lines.append("")

    add_pages("Pages without literature", report["pages_without_literature"])
    add_pages("Empty literature sections", report["empty_literature"])

    if report["duplicate_entries"]:
        lines.extend(["## Duplicate references within a page", ""])
        for item in report["duplicate_entries"]:
            lines.append(f"- `{item['page']}` — {item['url']}")
        lines.append("")

    if report["invalid_identifiers"]:
        lines.extend(["## Malformed DOI / PMID", ""])
        for item in report["invalid_identifiers"]:
            lines.append(f"- `{item['page']}` — {item['url']}")
        lines.append("")

    if report["broken_links"]:
        lines.extend(["## Confirmed broken external links", ""])
        for item in report["broken_links"]:
            lines.append(f"- HTTP {item['status']} — {item['url']}")
        lines.append("")

    if report["inconclusive_links"]:
        lines.extend(
            [
                "## Inconclusive external checks",
                "",
                "These are **not** classified as broken. Bot protection, rate limiting and transient server errors are common.",
                "",
            ]
        )
        for item in report["inconclusive_links"][:30]:
            detail = f"HTTP {item['status']}" if item.get("status") is not None else item.get("error", "request error")
            lines.append(f"- {detail} — {item['url']}")
        if len(report["inconclusive_links"]) > 30:
            lines.append(f"- … and {len(report['inconclusive_links']) - 30} more (see JSON report)")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-external", action="store_true")
    parser.add_argument("--markdown", default="build/literature-qc.md")
    parser.add_argument("--json", dest="json_path", default="build/literature-qc.json")
    args = parser.parse_args()

    report = build_report(check_external=args.check_external)
    md_path = Path(args.markdown)
    json_path = Path(args.json_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_report(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "Literature QC: "
        f"{report['clinical_pages']} clinical pages; "
        f"{len(report['pages_without_literature'])} without literature; "
        f"{len(report['duplicate_entries'])} within-page duplicates; "
        f"{len(report['invalid_identifiers'])} malformed identifiers; "
        f"{len(report['broken_links'])} confirmed broken external links."
    )


if __name__ == "__main__":
    main()
