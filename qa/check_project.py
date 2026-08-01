"""Fast, offline structural QA for the generated MyST book."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ROOT / "chapters"
IMAGES = ROOT / "images"

# Stable reconstruction baseline. A count change is allowed only after the
# corresponding source comparison has been reviewed and this baseline updated.
EXPECTED_COUNTS = {
    "p1-ch01-energy.md": (81, 102),
    "p1-ch02-atomic-molecular-structure.md": (89, 125),
    "p1-ch03-thermochemistry.md": (247, 126),
    "p1-ch04-entropy-second-law.md": (157, 86),
    "p1-ch05-equilibria-free-energy.md": (218, 83),
    "p1-ch06-equilibria-in-solution.md": (226, 114),
    "p1-ch07-electrochemistry.md": (193, 112),
    "p1-ch08-quantum-single-electron.md": (209, 100),
    "p1-ch09-multielectron-systems.md": (21, 98),
    "p1-ch10-molecular-bonding-i.md": (66, 155),
    "p1-ch11-molecular-bonding-ii.md": (44, 162),
    "p1-ch12-kinetics.md": (208, 91),
    "p1-ch13-nuclear-chemistry.md": (37, 38),
    "p1-appa.md": (0, 0),
    "p1-appb.md": (0, 42),
    "p1-appc.md": (0, 0),
    "p1-appd.md": (0, 0),
    "p1-appe.md": (0, 0),
    "p1-appf.md": (0, 1),
}

REQUIRED_TEXT = {
    "p1-ch03-thermochemistry.md": "DEVELOPMENT OF THE FIRST LAW OF THERMODYNAMICS",
    "p1-ch07-electrochemistry.md": "THE UNION OF GIBBS FREE ENERGY, ELECTRON FLOW, AND CHEMICAL TRANSFORMATION",
    "p1-ch13-nuclear-chemistry.md": "ENERGY, REACTORS, IMAGING, AND RADIOCARBON DATING",
    "p1-appa.md": "Standard Thermodynamic Values for Selected Substances",
    "p1-appb.md": "Dissociation (Ionization) Constants",
}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    chapter_files = sorted(CHAPTERS.glob("*.md"))
    if len(chapter_files) != 19:
        errors.append(f"expected 19 chapter/appendix files, found {len(chapter_files)}")

    texts = {path: path.read_text(encoding="utf-8") for path in chapter_files}
    combined = "\n".join(texts.values())
    image_refs = re.findall(r"\.\./images/([^\s\)\"'<>]+)", combined)
    image_files = {path.name for path in IMAGES.iterdir() if path.is_file()}
    referenced = set(image_refs)
    missing = sorted(referenced - image_files)
    orphaned = sorted(image_files - referenced)
    if missing:
        errors.append(f"missing image files: {', '.join(missing[:10])}")
    if orphaned:
        errors.append(f"orphan image files: {', '.join(orphaned[:10])}")

    labels = re.findall(r"(?m)^:(?:label|name):\s+(\S+)", combined)
    duplicates = sorted(name for name, count in Counter(labels).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate labels: {', '.join(duplicates[:10])}")

    for path, text in texts.items():
        h1_count = len(re.findall(r"(?m)^#\s+", text))
        if h1_count != 1:
            errors.append(f"{path.name}: expected one H1, found {h1_count}")
        figure_blocks = re.findall(r"(?ms)^:::\{figure\}.*?^:::\s*$", text)
        missing_alt = sum(1 for block in figure_blocks if not re.search(r"(?m)^:alt:\s+", block))
        if missing_alt:
            errors.append(f"{path.name}: {missing_alt} figure directives lack alt text")
        html_images = re.findall(r"(?i)<img\s[^>]*>", text)
        html_without_alt = sum(1 for tag in html_images if not re.search(r"(?i)\balt=", tag))
        if html_without_alt:
            errors.append(f"{path.name}: {html_without_alt} HTML images lack alt text")
        if re.search(r"images/[0-9a-fA-F]{20,}\.", text):
            errors.append(f"{path.name}: unreconstructed MinerU image path")
        if re.search(r"[\u0332\u0323\u0304\u0303\u0301\u0302\u0300\u0311\u0307]", text):
            errors.append(f"{path.name}: combining OCR mark remains")
        if "\x00" in text:
            errors.append(f"{path.name}: NUL byte remains")
        expected = EXPECTED_COUNTS.get(path.name)
        if expected:
            equation_count = len(re.findall(r"(?m)^```\{math\}", text))
            per_file_images = len(re.findall(r"\.\./images/", text))
            if (equation_count, per_file_images) != expected:
                errors.append(
                    f"{path.name}: expected equations/images {expected}, "
                    f"found {(equation_count, per_file_images)}"
                )
        required_text = REQUIRED_TEXT.get(path.name)
        if required_text and required_text not in text:
            errors.append(f"{path.name}: required restored heading/text is missing")

    explicit_refs = len(re.findall(r"\{(?:eq|ref|numref)\}`", combined))
    if explicit_refs == 0:
        warnings.append("no explicit MyST equation/figure cross-references are authored")
    long_lines = sum(1 for line in combined.splitlines() if len(line) > 1000)
    if long_lines:
        warnings.append(f"{long_lines} generated lines exceed 1000 characters")

    print(
        "QA summary: "
        f"{len(chapter_files)} files, {len(labels)} labels, "
        f"{len(image_files)} images, {len(image_refs)} image references"
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"QA FAILED with {len(errors)} error(s)")
        return 1
    print("QA PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
