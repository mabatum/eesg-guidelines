from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests

SOURCE_PAGE = "https://eesg.ru/main"
OUTPUT_DIR = Path("docs/_assets/brand")
MANIFEST = OUTPUT_DIR / "manifest.json"

# Assets confirmed from the public EESG site/search cache. They are fallbacks in
# case Tilda changes markup or lazy-loading prevents discovery from the HTML.
KNOWN_ASSETS = [
    {
        "kind": "logo",
        "url": "https://thb.tildacdn.com/tild6537-3538-4662-b665-633035326533/-/empty/logo_.png",
        "label": "EESG logo",
    },
    {
        "kind": "branding",
        "url": "https://static.tildacdn.com/tild3663-3538-4136-a437-316538386136/MAIN_PAIGE.png",
        "label": "EESG main-page branding image",
    },
]

BRAND_TERMS = ("logo", "eesg", "brand", "label", "лейбл", "логотип")


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k.lower(): (v or "") for k, v in attrs}

        if tag.lower() == "img":
            urls = [
                data.get("data-original", ""),
                data.get("data-src", ""),
                data.get("src", ""),
            ]
            haystack = " ".join(
                [
                    data.get("alt", ""),
                    data.get("title", ""),
                    data.get("class", ""),
                    data.get("id", ""),
                    *urls,
                ]
            ).casefold()
            if any(term in haystack for term in BRAND_TERMS):
                for url in urls:
                    if url:
                        self.assets.append(
                            {
                                "kind": "logo" if "logo" in haystack or "eesg" in haystack else "branding",
                                "url": url,
                                "label": data.get("alt") or data.get("title") or "EESG image asset",
                            }
                        )
                        break

        if tag.lower() == "link":
            rel = data.get("rel", "").casefold()
            href = data.get("href", "")
            if href and "icon" in rel:
                self.assets.append({"kind": "icon", "url": href, "label": rel})

        if tag.lower() == "meta":
            key = (data.get("property") or data.get("name") or "").casefold()
            content = data.get("content", "")
            if content and key in {"og:image", "twitter:image", "twitter:image:src"}:
                self.assets.append({"kind": "branding", "url": content, "label": key})


def original_tilda_url(url: str) -> str | None:
    """Convert Tilda thumbnail URLs to the underlying static asset when possible."""
    parsed = urlparse(url)
    if parsed.netloc != "thb.tildacdn.com":
        return None

    match = re.match(r"^/(?P<folder>tild[^/]+)/-/[^/]+/(?P<name>.+)$", parsed.path)
    if not match:
        return None
    return f"https://static.tildacdn.com/{match.group('folder')}/{match.group('name')}"


def candidate_urls(url: str) -> list[str]:
    absolute = urljoin(SOURCE_PAGE, url)
    result: list[str] = []
    original = original_tilda_url(absolute)
    if original:
        result.append(original)
    result.append(absolute)
    return list(dict.fromkeys(result))


def extension_from(response: requests.Response, url: str) -> str:
    content_type = (response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    by_type = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
    }
    if content_type in by_type:
        return by_type[content_type]
    suffix = Path(unquote(urlparse(url).path)).suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico"} else ".bin"


def safe_stem(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value[:48] or "asset"


def choose_filename(asset: dict[str, str], source_url: str, ext: str, index: int) -> str:
    kind = asset["kind"]
    basename = Path(unquote(urlparse(source_url).path)).stem
    if kind == "logo":
        return f"eesg-logo{ext}"
    if kind == "icon":
        return f"eesg-icon-{index}{ext}"
    if "main_paige" in source_url.casefold():
        return f"eesg-main-branding{ext}"
    return f"eesg-{safe_stem(kind)}-{safe_stem(basename)}-{index}{ext}"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; EESG-Guidelines-Brand-Importer/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
    )

    discovered: list[dict[str, str]] = []
    page_error: str | None = None
    try:
        response = session.get(SOURCE_PAGE, timeout=30)
        response.raise_for_status()
        parser = AssetParser()
        parser.feed(response.text)
        discovered.extend(parser.assets)
    except requests.RequestException as exc:
        page_error = str(exc)
        print(f"Warning: could not parse {SOURCE_PAGE}: {exc}")

    discovered.extend(KNOWN_ASSETS)

    # Deduplicate by normalized absolute URL while preserving order.
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for asset in discovered:
        absolute = urljoin(SOURCE_PAGE, asset["url"])
        if absolute in seen:
            continue
        seen.add(absolute)
        unique.append({**asset, "url": absolute})

    manifest: dict[str, object] = {
        "source_page": SOURCE_PAGE,
        "page_error": page_error,
        "assets": [],
    }
    used_names: set[str] = set()

    for index, asset in enumerate(unique, 1):
        downloaded = None
        errors: list[str] = []
        for url in candidate_urls(asset["url"]):
            try:
                r = session.get(url, timeout=30)
                if not r.ok:
                    errors.append(f"{url}: HTTP {r.status_code}")
                    continue
                if not r.content:
                    errors.append(f"{url}: empty response")
                    continue
                ext = extension_from(r, url)
                filename = choose_filename(asset, url, ext, index)
                if filename in used_names:
                    stem = Path(filename).stem
                    filename = f"{stem}-{index}{ext}"
                used_names.add(filename)
                path = OUTPUT_DIR / filename
                path.write_bytes(r.content)
                downloaded = {
                    "kind": asset["kind"],
                    "label": asset.get("label", ""),
                    "discovered_url": asset["url"],
                    "source_url": url,
                    "file": filename,
                    "content_type": (r.headers.get("content-type") or "").split(";", 1)[0],
                    "bytes": len(r.content),
                    "sha256": hashlib.sha256(r.content).hexdigest(),
                }
                print(f"Downloaded {asset['kind']}: {url} -> {path} ({len(r.content)} bytes)")
                break
            except requests.RequestException as exc:
                errors.append(f"{url}: {exc}")

        if downloaded:
            manifest["assets"].append(downloaded)  # type: ignore[index]
        else:
            manifest["assets"].append(  # type: ignore[index]
                {
                    "kind": asset["kind"],
                    "label": asset.get("label", ""),
                    "discovered_url": asset["url"],
                    "errors": errors,
                }
            )

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    downloaded_count = sum(1 for item in manifest["assets"] if "file" in item)  # type: ignore[union-attr]
    print(f"Brand import complete: {downloaded_count} asset(s) saved. Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
