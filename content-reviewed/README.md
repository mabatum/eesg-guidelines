# Reviewed clinical content

The Russian bone-tumour manuscript in this directory is the reviewed source for the test site. It is applied **after** the Yandex Wiki export and scope pruning, and **before** normalization, indexing, validation and rendering.

Edit these files to update the reviewed edition. `docs/gen_docs/bone-sarcomas` is the generated publishing copy. The overlay deliberately contains only the eight existing bone-section routes. Wiki remains the source of navigation and of any other sections enabled in the future; its bone text does not overwrite this edition.

Run `python scripts/apply_reviewed_content.py` after an export. Changes to the reviewed manuscript, its application script or this workflow trigger publication. Keep status, evidence cutoff and citations current. This is an editorial draft for expert discussion, not a claim of institutional guideline approval.

Research methodology and a claim-to-source audit are recorded in `research/bone-review-2026-09-06/report-source.md`. User-provided source documents and downloaded articles are not committed.
