# EESG Guidelines

Public documentation pipeline for EESG clinical recommendations.

Source of truth: Yandex Wiki subtree `https://wiki.yandex.ru/eesg`.

Planned pipeline:

`Yandex Wiki API -> YFM/Markdown export -> Diplodoc -> GitHub Pages`

The Yandex Wiki OAuth token must be stored only as a GitHub Actions secret named `WIKI_TOKEN`.
