# Reviewed bone guideline content

Edition **2026.11.1**, dated 6 November 2026, merges the approved clinical recommendations
**Саркомы костей**, 2025, adults, ID **532_5**, with the EESG evidence revision of September 2026.
It supersedes edition 2026.09.3 for the eight existing bone-section routes.

Guideline statements cite the printed page of the original PDF as [[1, с. N]]; primary studies are
cited by DOI. Drug options that are not part of ID 532_5 carry ‡, off-label use carries †.

Edit `content-reviewed/bone-sarcomas`; `docs/gen_docs/bone-sarcomas` is generated.
Marker sources with reference files are kept in `content-src/bone-sarcomas` and rebuilt with
`build_page.py` from the eesg-guidelines skill.

Only bone pages are exposed. Scope pruning removes other sections from the build,
search and updates, including direct URLs. Historical material remains in git/Wiki.

Original source: `docs/_assets/sources/kr532-5-2025.pdf` (75 PDF pages, duplicate title page;
printed page n corresponds to PDF page n+1 for the numbered body).

Merge decisions and conflicts: `research/bone-merge-2026-11-06.md`.
