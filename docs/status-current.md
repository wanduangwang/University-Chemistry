# Current project status

**Mode:** local research copy; publication and deployment disabled.

## Scope

- 13 chapters and Appendices A–F reconstructed from MinerU output.
- Source coverage is PDF pages 71–1784. Front matter and the printed index are
  not currently included as web pages.
- The generated site contains one landing page and 19 content pages.

## Acceptance gates

1. `python qa/check_project.py` must pass.
2. `npm run build` must return successfully with no MyST error or warning
   diagnostics.
3. Every chapter start and every appendix must be compared with the source PDF.
4. Formulae, chemical structures, numerical tables, and figure captions require
   representative visual review.
5. Publication remains prohibited until written permission is documented.

## Cross-reference status

All 1,334 printed figure, table, and equation-reference occurrences in the 13
chapters have been audited. 1,333 are authored as resolvable links, with no
unresolved targets. The sole documented source defect is the book's reference
to Figure CS10.3M, for which no target figure exists in the source chapter PDF.

Generated equation labels remain stable internal identifiers. Where the source
retains a printed equation number, references target that numbered display;
otherwise no printed numbering is invented.
