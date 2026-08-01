# University Chemistry — local MyST conversion

This workspace converts James G. Anderson's *University Chemistry* PDF into a
searchable MyST web book containing 13 chapters and Appendices A–F.

## Local-only status

The source book is a copyrighted MIT Press publication. This repository does
not contain evidence of publication or redistribution permission. Keep the
repository private and do not deploy the generated site. See `NOTICE.md`.

## Project layout

- `chapters/`: generated MyST Markdown
- `images/`: renamed figures used by the chapters
- `mineru/`: PDF splitting, MinerU parsing, and reconstruction tools
- `qa/`: structural checks and strict MyST build wrapper
- `myst.yml`: book table of contents and local site configuration

MinerU's downloaded output and per-chapter PDFs are local build inputs and are
excluded from Git.

## Setup

Requirements are Node.js 22 or newer and Python 3.12 or newer.

```powershell
npm.cmd ci
python -m pip install -r requirements.txt
```

`package-lock.json` pins MyST. `requirements.txt` includes PyMuPDF for PDF
splitting and optional scientific packages inherited from the project template.

## Rebuild workflow

Split a locally held source PDF:

```powershell
python mineru/split_pdf.py --src "C:\path\to\University Chemistry.pdf"
```

Parse one split PDF after setting `MINERU_TOKEN` or placing it in the ignored
`mineru/.env` file:

```powershell
python mineru/parse_pdf.py --pdf mineru/output_pdfs/p1-ch01-energy.pdf --name p1-ch01-energy
```

Reconstruct all available MinerU outputs, then run QA and the strict build:

```powershell
python mineru/reconstruct_all.py
npm.cmd run check
```

For a local preview only:

```powershell
npm.cmd run start -- --port 3000
```

## Quality policy

The automated QA fails on missing or orphan images, duplicate labels, missing
image alternative text, unprocessed MinerU paths, combining OCR marks,
unresolved or regressed cross-references, or any MyST build warning/error. The
strict build also fails if table-formula sources are missing, remain raw in the
generated site, or produce empty formula containers. Extremely long generated
table lines remain a non-blocking maintainability warning.

Machine extraction is not a substitute for subject-matter review. Equations,
chemical structures, numerical tables, captions, and OCR-damaged prose require
continued comparison with the source PDF before the content can be considered a
faithful scholarly edition. Progress and review order are recorded in
`docs/content-qa.md`.

The MyST CLI is pinned, while the named `book-theme` template is obtained from
the MyST template service on the first build. Retain the ignored `_build`
template cache when fully offline operation is required.
