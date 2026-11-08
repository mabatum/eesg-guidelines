# EESG Guidelines

Clinical guideline website at https://mabatum.github.io/eesg-guidelines/.

## Clinical source

Edition 2026.11.2 rests on the Russian Ministry of Health guidelines and the RUSSCO 2025 practice
guidelines, cited by printed page; EESG additions from primary studies (cited by DOI), ESMO, ASCO and
UpToDate are labelled «Предлагается», guideline and RUSSCO positions «Рекомендуется». Departures are
counted from the Ministry guideline of the page: # off-label use (the guideline marks the drug «#»),
◊ not in the guideline but registered in Russia for the indication, ◊# registered but not for the
indication, § not registered; ¶ marks any drug outside the ЖНВЛП list. The ◊, ◊# and § footnotes carry
the phrase about the regional medical commission and the NMIC federal consilium.
Decisions: `research/edition-2026-11-2.md`; bone merge: `research/bone-merge-2026-11-06.md`.
All published text is edited in Yandex Wiki. Every build exports it (`scripts/export_wiki_neutral.py`);
the bone pages also go through `scripts/pull_wiki_bones.py` into `content-reviewed/bone-sarcomas`,
so the copy in git is a snapshot. The marker sources in `content-src/bone-sarcomas` are the 2026.11.1
starting point and are not updated after Wiki edits.
The original PDF is in `docs/_assets/sources/kr532-5-2025.pdf`.
Soft tissue sections are opened page by page as they are merged with the guidelines «Саркомы мягких тканей»
(ID 515_3), «Забрюшинные неорганные саркомы» (ID 618_3) and «Рак тела матки и саркомы матки» (ID 460_4);
their PDFs are in `docs/_assets/sources`. Merge decisions: `research/soft-merge-2026-11-06.md`.
The new reading interface at `/new/` shows every published section: `scripts/build_new_interface.py` reads
`docs/gen_docs` after `npm run prepare:docs`, in the order of its `toc.yaml`.
GIST is built on its own guideline «Гастроинтестинальные стромальные опухоли» (ID 551_3, 2024; PDF in
`docs/_assets/sources/kr551-3-2024.pdf`). Other sections remain
excluded from the build and search.

## Build and publish

Install with `npm ci`. With `WIKI_TOKEN` and `ORG_ID` set, run `python3 scripts/export_wiki_neutral.py`
and `python3 scripts/pull_wiki_bones.py`, then `npm run prepare:docs`, `npm run build:docs`, and
`python3 scripts/validate_static_routes.py`. The site shows the sections listed in `config/site-scope.json`;
`hide_pages` there keeps single pages of a published section off the site until they are reviewed. The GitHub Pages workflow publishes
only after these checks pass. It runs on push, on manual start and every 30 minutes, so Wiki edits
reach the site within about half an hour. If a pulled page fails a check, the site keeps the last
published version. The full Wiki export of navigation is still an optional manual step.

## Feedback

Readers can submit feedback anonymously through the embedded Google Form without a
Google or GitHub account. Responses are saved in the owner's private Google Sheet.
The provider validates the submission and shows confirmation only after it is saved.
The form receives the page, section, source edition and selected quotation.
Configure its published URL and context prefill field in `docs/_assets/script/feedback-config.js`.
No access tokens or private response-sheet URLs are included in the public site.
