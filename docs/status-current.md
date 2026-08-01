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

## Known semantic limitation

MinerU retained very few original equation numbers, and explicit MyST
cross-references have not yet been authored. Generated equation labels are
stable internal identifiers, not a reconstruction of the book's printed
equation numbering.
