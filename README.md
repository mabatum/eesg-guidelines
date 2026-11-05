# EESG Guidelines

Clinical guideline website at https://mabatum.github.io/eesg-guidelines/.

## Clinical source

Edition 2026.11.1 merges the Russian Ministry of Health guideline **Саркомы костей**, 2025, ID 532_5,
with the EESG evidence revision of September 2026 (primary studies cited by DOI). Every guideline
statement cites its printed page; drug options outside the guideline are marked ‡, off-label use †.
Merge decisions: `research/bone-merge-2026-11-06.md`. Marker sources: `content-src/bone-sarcomas`.
The authoritative editable manuscript is `content-reviewed/bone-sarcomas`.
The original PDF is in `docs/_assets/sources/kr532-5-2025.pdf`.
Only `bone-sarcomas` is published; other sections remain excluded from the build and search.

## Build and publish

Install with `npm ci`, then run `npm run prepare:docs`, `npm run build:docs`, and
`python3 scripts/validate_static_routes.py`. The GitHub Pages workflow publishes
only after these checks pass. Wiki export is retained as an optional manual step;
it is never allowed to replace the reviewed bone manuscript.

## Feedback

Readers can submit feedback anonymously through the embedded Google Form without a
Google or GitHub account. Responses are saved in the owner's private Google Sheet.
The provider validates the submission and shows confirmation only after it is saved.
The form receives the page, section, source edition and selected quotation.
Configure its published URL and context prefill field in `docs/_assets/script/feedback-config.js`.
No access tokens or private response-sheet URLs are included in the public site.
