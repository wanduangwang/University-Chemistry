"""Split the source University Chemistry PDF into per-chapter / per-appendix PDFs
(<=200 pages each, per MinerU single-file limit). Page ranges are 1-indexed
inclusive PDF page numbers from the PDF outline (doc.get_toc()).
Re-splitting is harmless: existing per-chapter PDFs are overwritten."""
import argparse
import os
from pathlib import Path

import fitz

DEFAULT_OUT = Path(__file__).resolve().parent / "output_pdfs"

# 1-indexed inclusive PDF page ranges (from outline). Index (1785-1820) omitted:
# it is a print-page index with no value as a web chapter.
RANGES = {
    "p1-ch01-energy": (71, 197),
    "p1-ch02-atomic-molecular-structure": (198, 342),
    "p1-ch03-thermochemistry": (343, 502),
    "p1-ch04-entropy-second-law": (503, 610),
    "p1-ch05-equilibria-free-energy": (611, 717),
    "p1-ch06-equilibria-in-solution": (718, 842),
    "p1-ch07-electrochemistry": (843, 992),
    "p1-ch08-quantum-single-electron": (993, 1133),
    "p1-ch09-multielectron-systems": (1134, 1253),
    "p1-ch10-molecular-bonding-i": (1254, 1412),
    "p1-ch11-molecular-bonding-ii": (1413, 1569),
    "p1-ch12-kinetics": (1570, 1688),
    "p1-ch13-nuclear-chemistry": (1689, 1739),
    "p1-appa": (1740, 1753),
    "p1-appb": (1754, 1770),
    "p1-appc": (1771, 1774),
    "p1-appd": (1775, 1777),
    "p1-appe": (1778, 1783),
    "p1-appf": (1784, 1784),
}

def main():
    parser = argparse.ArgumentParser(description="Split University Chemistry into MinerU-sized PDFs")
    parser.add_argument(
        "--src",
        default=os.environ.get("UC_SOURCE_PDF"),
        help="source PDF path (or set UC_SOURCE_PDF)",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    args = parser.parse_args()
    if not args.src:
        parser.error("--src is required unless UC_SOURCE_PDF is set")

    source = Path(args.src).expanduser().resolve()
    output = Path(args.out).expanduser().resolve()
    if not source.is_file():
        parser.error(f"source PDF not found: {source}")

    output.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
    print("source pages:", doc.page_count)
    for name, (a, b) in RANGES.items():
        nd = fitz.open()
        nd.insert_pdf(doc, from_page=a - 1, to_page=b - 1)
        outp = output / f"{name}.pdf"
        nd.save(outp)
        print(f"{name}: PDF pages {a}-{b} -> {nd.page_count} pages")
        nd.close()
    doc.close()

if __name__ == "__main__":
    main()
