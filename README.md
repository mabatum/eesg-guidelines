# EESG Guidelines

Clinical guideline website at https://mabatum.github.io/eesg-guidelines/.

## Clinical source

Edition 2026.09.3 adapts the user-supplied **Саркомы костей**, 2025, ID 532_5, for adults.
The authoritative editable manuscript is `content-reviewed/bone-sarcomas`.
The original PDF is in `docs/_assets/sources/kr532-5-2025.pdf`.
Only `bone-sarcomas` is published; other sections remain excluded from the build and search.

## Build and publish

Install with `npm ci`, then run `npm run prepare:docs`, `npm run build:docs`, and
`python3 scripts/validate_static_routes.py`. The GitHub Pages workflow publishes
only after these checks pass. Wiki export is retained as an optional manual step;
it is never allowed to replace the reviewed bone manuscript.

## Feedback

The on-page feedback dialog accepts remarks without GitHub login.
Responses are collected through an embedded form and are visible only to its owner.
The form receives the page, section, source edition and selected quotation.
Configure its published URL and prefill field IDs in `docs/_assets/script/feedback-config.js`.
No access tokens or private response-sheet URLs are included in the public site.
