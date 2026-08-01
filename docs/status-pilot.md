# Archived Pilot Status — University Chemistry web book (Chapters 1–3)

> Historical record only. The project has since expanded to the full local
> 13-chapter and 6-appendix conversion. See `status-current.md` for current
> acceptance criteria. Public deployment is disabled.

**Date:** 2026-07-23 · **Method:** MyST-Markdown, replicating SSP/SolidStatePhysics handbook
**Scope:** Pilot = Ch1 Energy, Ch2 Atomic & Molecular Structure, Ch3 Thermochemistry
**Preview:** http://localhost:3000 (all routes HTTP 200)

## What's built
| Chapter | Equations | Figures | Images |
|---|---|---|---|
| p1-ch01-energy | 81 | 102 | ✓ |
| p1-ch02-atomic-molecular-structure | 89 | 125 | ✓ |
| p1-ch03-thermochemistry | 247 | 126 | ✓ |
| **Total** | **417** | **353** | **353** |

## QA gates (manual R1–R5)
- **R1 Build** — `myst build` EXIT=0 ✓
- **R2 Zero warnings** — 0 undefined refs, 0 duplicate labels, 0 missing images ✓
- **R3 Equation reconciliation** — md `:label: eq-` counts: 81 / 89 / 247.
  ⚠️ MinerU retained almost no `\tag`s (0 / 10 / 5), i.e. it dropped most PDF equation
  numbers. Equations render via MyST sequential auto-numbering, which diverges from the
  PDF's `(1.x)` scheme. PDF-exact numbering needs direct source-PDF extraction (future work).
- **R4 Cross-ref audit** — 0 malformed `{eq}`, 0 duplicate labels ✓
  (cross-references not yet authored in pilot; gate becomes meaningful in full pass)
- **R5 Browser acceptance** — all chapter routes serve HTTP 200; visual figure/caption
  spot-check is the human step per R5.

## Known gaps (for the full-book pass)
1. Equation **numbering** not PDF-accurate (MinerU dropped tags) — semantic fidelity gap.
2. Some **OCR spacing** in prose/math (e.g. `changeindistance` instead of "change in
   distance") — MinerU vlm artifact; needs post-correction pass.
3. **Figure captions** ("FIGURE X.Y") render as paragraphs after the image rather than
   styled captions in a few multi-image figures.

## Next phase
- Extend `mineru/split_pdf.py` ranges + `myst.yml` TOC for Ch4–13 + Appendix A–F.
- Run parse + reconstruct for remaining chapters; re-run R1–R5.
- Deploy to GitHub Pages (after user approval: create repo, set Pages source = GitHub Actions).
