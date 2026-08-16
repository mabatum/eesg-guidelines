from __future__ import annotations

import os
import sys

import requests

API = "https://api.wiki.yandex.net/v1"
TOKEN = os.environ.get("WIKI_TOKEN")
ORG_ID = os.environ.get("ORG_ID")

PAGES = [
    (
        "eesg/news",
        "Новости",
        "# Новости\n\nРаздел новостей EESG. Структура и формат публикаций находятся в разработке.\n",
    ),
    (
        "eesg/events",
        "Мероприятия",
        "# Мероприятия\n\nРаздел мероприятий EESG. Структура и формат публикаций находятся в разработке.\n",
    ),
    (
        "eesg/clinical-trials",
        "Клинические исследования",
        "# Клинические исследования\n\nРаздел клинических исследований EESG. Структура и формат публикаций находятся в разработке.\n",
    ),
]


def headers() -> dict[str, str]:
    if not TOKEN or not ORG_ID:
        raise SystemExit("WIKI_TOKEN and ORG_ID are required")
    return {
        "Authorization": f"OAuth {TOKEN}",
        "X-Cloud-Org-Id": ORG_ID,
        "Content-Type": "application/json",
    }


def get_page(slug: str) -> dict | None:
    response = requests.get(
        f"{API}/pages",
        params={"slug": slug, "fields": "content,attributes"},
        headers=headers(),
        timeout=20,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    if payload.get("id"):
        return payload
    return None


def create_page(slug: str, title: str, content: str) -> dict:
    response = requests.post(
        f"{API}/pages",
        params={"is_silent": "true", "fields": "content,attributes"},
        json={
            "slug": slug,
            "title": title,
            "content": content,
            "access_policy": {"access_type": "inherited"},
        },
        headers=headers(),
        timeout=20,
    )
    if response.status_code != 200:
        print(f"Failed to create {slug}: HTTP {response.status_code}", file=sys.stderr)
        print(response.text[:2000], file=sys.stderr)
        response.raise_for_status()
    return response.json()


def main() -> None:
    created = 0
    existing = 0
    for slug, title, content in PAGES:
        page = get_page(slug)
        if page is not None:
            existing += 1
            print(f"EXISTS  {slug}  id={page.get('id')}")
            continue
        page = create_page(slug, title, content)
        created += 1
        print(f"CREATED {slug}  id={page.get('id')}")

    print(f"Portal Wiki bootstrap complete: created={created}, existing={existing}.")


if __name__ == "__main__":
    main()
