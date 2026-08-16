"""Neutral EESG Wiki export.

Keeps clinical page text structurally unchanged. The legacy recommendation-callout
converter remains available in export_wiki.py for a possible future editorial phase,
but is explicitly disabled in the production pipeline for now.

The Wiki descendants endpoint can briefly return a page that has just been moved or
deleted while the page endpoint already returns 404. Production export retries such
pages and then skips only the stale descendant instead of failing the whole snapshot.
"""

import time

import export_wiki


_ORIGINAL_GET_PAGE = export_wiki.get_page


def passthrough(content: str) -> tuple[str, int]:
    return content, 0


def tolerant_get_page(session, slug: str) -> dict:
    for attempt in range(1, 4):
        response = session.get(
            f"{export_wiki.API_BASE}/pages",
            params={"slug": slug, "fields": "content,attributes,breadcrumbs"},
            timeout=30,
        )
        if response.ok:
            return response.json()
        if response.status_code != 404:
            raise SystemExit(
                f"Yandex Wiki API request failed: HTTP {response.status_code} "
                f"for {response.url}\n{export_wiki.error_text(response)}"
            )
        if attempt < 3:
            print(f"WARNING Wiki page returned 404, retrying ({attempt}/3): {slug}")
            time.sleep(1.5)

    print(
        "WARNING Wiki descendants snapshot contains a page that no longer resolves; "
        f"skipping stale descendant: {slug}"
    )
    # export_wiki.export() already has a safe skip path for is_draft pages. Reuse it
    # here so the core exporter remains unchanged and the atomic snapshot still works.
    return {
        "title": slug.rsplit("/", 1)[-1],
        "content": "",
        "attributes": {"is_draft": True, "_stale_missing": True},
    }


if __name__ == "__main__":
    export_wiki.render_recommendation_blocks = passthrough
    export_wiki.get_page = tolerant_get_page
    export_wiki.export()
