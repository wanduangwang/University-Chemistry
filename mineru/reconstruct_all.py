"""Reconstruct all parsed chapters and appendices in one portable command."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mineru" / "output"
RECONSTRUCT = ROOT / "mineru" / "reconstruct.py"

# (slug, ch, title)  -- chapters
CHAP = [
    ("p1-ch01-energy", 1, "Energy"),
    ("p1-ch02-atomic-molecular-structure", 2, "Atomic and Molecular Structure"),
    ("p1-ch03-thermochemistry", 3, "Thermochemistry"),
    ("p1-ch04-entropy-second-law", 4, "Entropy and the Second Law of Thermodynamics"),
    ("p1-ch05-equilibria-free-energy", 5, "Equilibria and Free Energy"),
    ("p1-ch06-equilibria-in-solution", 6, "Equilibria in Solution"),
    ("p1-ch07-electrochemistry", 7, "Electrochemistry"),
    ("p1-ch08-quantum-single-electron", 8, "Quantum Mechanics, Wave-Particle Duality, and the Single Electron Atom"),
    ("p1-ch09-multielectron-systems", 9, "Quantum Mechanics of Multielectron Systems and the Link Between Orbital Structure and Chemical Reactivity"),
    ("p1-ch10-molecular-bonding-i", 10, "Theories of Molecular Bonding I"),
    ("p1-ch11-molecular-bonding-ii", 11, "Theories of Molecular Bonding II"),
    ("p1-ch12-kinetics", 12, "Kinetics"),
    ("p1-ch13-nuclear-chemistry", 13, "Nuclear Chemistry"),
]
# (slug, app, title)  -- appendices
APP = [
    ("p1-appa", "appa", "Appendix A"),
    ("p1-appb", "appb", "Appendix B"),
    ("p1-appc", "appc", "Appendix C"),
    ("p1-appd", "appd", "Appendix D"),
    ("p1-appe", "appe", "Appendix E"),
    ("p1-appf", "appf", "Appendix F"),
]

def rec_ch(slug, ch, title):
    full = OUT / slug / "full.md"
    if not full.exists():
        print("SKIP (not parsed):", slug); return
    subprocess.run([sys.executable, str(RECONSTRUCT), "--full", str(full), "--slug", slug,
                    "--ch", str(ch), "--title", title, "--out", f"chapters/{slug}.md",
                    "--img-dest", "images"], cwd=ROOT, check=True)

def rec_app(slug, app, title):
    full = OUT / slug / "full.md"
    if not full.exists():
        print("SKIP (not parsed):", slug); return
    subprocess.run([sys.executable, str(RECONSTRUCT), "--full", str(full), "--slug", slug,
                    "--app", app, "--title", title, "--out", f"chapters/{slug}.md",
                    "--img-dest", "images"], cwd=ROOT, check=True)

def main():
    for slug, chapter, title in CHAP:
        rec_ch(slug, chapter, title)
    for slug, appendix, title in APP:
        rec_app(slug, appendix, title)
    print("RECONSTRUCT ALL DONE")


if __name__ == "__main__":
    main()
