# Content QA tracker

Automated reconstruction QA currently passes for all 13 chapters and six
appendices. This tracker separates those machine-verifiable checks from the
scholarly review that still requires comparison with the source book.

## Automated baseline

- 1,796 display-math blocks
- 1,435 image files and 1,435 image references
- 3,011 unique equation/figure labels
- no missing or orphan images
- no duplicate labels, NUL bytes, combining OCR marks, or missing image alt text
- strict MyST 1.10.1 build with zero warning/error diagnostics
- all 20 generated routes return HTTP 200

## Manual review status

| Content | Structural QA | Source-by-source proofreading |
|---|---|---|
| Chapters 1–13 | Passed | Pending |
| Appendices A–F | Passed | Pending |
| Chapter/appendix opening matter | Regression-protected | Representative pages reviewed; full review pending |
| Display equations | Count-protected and render-clean | Printed numbering and semantic accuracy pending |
| Figures | File/reference complete | Caption association and scientific fidelity pending |
| Numerical tables | Present | Cell-by-cell value/sign review pending |
| Cross-references | None malformed | Authoring/linking pending |

## Review order

1. Appendices A–E numerical values and signs.
2. Display equations and chemical structures in Chapters 4–7 and 10–13.
3. Figure captions, multi-image figures, and HTML-table figures.
4. OCR spacing and prose artifacts.
5. Original equation numbers and authored MyST cross-references.

The 364 generated lines longer than 1,000 characters are predominantly HTML
tables. They are valid and build successfully, but should be converted to a more
maintainable table representation during the manual appendix/table pass.
