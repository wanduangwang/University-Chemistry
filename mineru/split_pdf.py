"""Split the source University Chemistry PDF into per-chapter PDFs (<=200 pages each,
per MinerU single-file limit). Page ranges are 1-indexed inclusive PDF page numbers
from the PDF outline (doc.get_toc())."""
import fitz, os

SRC = r"C:/Users/firefly/Downloads/University Chemistry.pdf"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_pdfs")

# 1-indexed inclusive PDF page ranges (from outline). Pilot = Ch1-3.
RANGES = {
    "p1-ch01-energy": (71, 197),
    "p1-ch02-atomic-molecular-structure": (198, 342),
    "p1-ch03-thermochemistry": (343, 502),
}

def main():
    os.makedirs(OUT, exist_ok=True)
    doc = fitz.open(SRC)
    print("source pages:", doc.page_count)
    for name, (a, b) in RANGES.items():
        nd = fitz.open()
        nd.insert_pdf(doc, from_page=a - 1, to_page=b - 1)
        outp = os.path.join(OUT, name + ".pdf")
        nd.save(outp)
        print(f"{name}: PDF pages {a}-{b} -> {nd.page_count} pages -> {outp}")
        nd.close()
    doc.close()

if __name__ == "__main__":
    main()
