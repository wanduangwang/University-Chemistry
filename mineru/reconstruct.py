"""Path B reconstruction: convert MinerU full.md -> MyST chapter .md.

Handles the real MinerU output quirks observed on University Chemistry:
- Headings inverted: chapter title `## ENERGY` (lvl2) but a section `# CONCEPTUAL
  FOUNDATION` (lvl1). Emit `# {ch} {title}` once, demote remaining `#` to `##`.
- ALL images (markdown `![](images/x)` AND HTML `<img src="images/x">` inside
  tables) are collected, renamed to images/fig-<part>-ch<NN>-<K>.<ext>, and their
  references rewritten. Standalone markdown images become `:::{figure}` blocks
  (with `:name:` + optional following `FIGURE X.Y` caption); `<img>` inside tables
  keep their (rewritten) src.
- Display math `$$...$$` -> :::{math} with :label: eq-<part>-ch<NN>-<seq>.
  MinerU OCR cleanup inside math: en/em dash -> hyphen, `\\dprime` -> `\\prime`,
  `^ {-} ^` double-superscript -> `^{-`, `\\tag {x}` -> `\\tag{x}`, strip trailing
  stray backslash (KaTeX pitfall, manual SSP $9). Empty $$ blocks skipped.
"""
import os, re, argparse, shutil


def _normalized_title(value):
    """Normalize OCR/Markdown title text for conservative title matching."""
    value = re.sub(r"[`*_{}$\\]", "", value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _figure_alt(caption):
    if not caption:
        return "Figure from the University Chemistry source textbook"
    alt = re.sub(r"<[^>]+>", "", caption)
    alt = re.sub(r"\$[^$]*\$", "mathematical notation", alt)
    alt = re.sub(r"\s+", " ", alt).strip()
    return alt[:240].rstrip()


def reconstruct(full_md_path, slug, part, ch, title, out_md, img_dest, app=None):
    images_dir = os.path.join(os.path.dirname(full_md_path), "images")
    prefix = f"{part}-{app}" if app else f"{part}-ch{ch:02d}"
    with open(full_md_path, encoding="utf-8") as f:
        text = f.read()

    # ---- collect + rename ALL images (markdown and HTML <img>) ----
    hashes = []
    seen = set()
    for m in re.finditer(r"images/([0-9a-fA-F]{20,}\.(?:jpg|jpeg|png|gif))", text):
        h = m.group(1)
        if h.lower() not in seen:
            seen.add(h.lower())
            hashes.append(h)
    figmap = {h: f"fig-{prefix}-{i + 1}" for i, h in enumerate(hashes)}
    if img_dest:
        os.makedirs(img_dest, exist_ok=True)
        # Remove only images owned by this chapter/appendix. This prevents a
        # new MinerU run from leaving stale numbered files behind.
        owned = re.compile(rf"^fig-{re.escape(prefix)}-\d+\.(?:jpg|jpeg|png|gif)$", re.I)
        for entry in os.listdir(img_dest):
            if owned.match(entry):
                os.remove(os.path.join(img_dest, entry))
        for h, name in figmap.items():
            src = os.path.join(images_dir, h)
            ext = os.path.splitext(h)[1].lower()
            dst = os.path.join(img_dest, f"{name}{ext}")
            if os.path.exists(src):
                shutil.copy(src, dst)

    def _repl(m):
        h = m.group(1)
        ext = os.path.splitext(h)[1].lower()
        return f"../images/{figmap[h]}{ext}"

    text = re.sub(r"images/([0-9a-fA-F]{20,}\.(?:jpg|jpeg|png|gif))", _repl, text)
    text = re.sub(
        r'<img\s+src="([^"]+)"\s*/?>',
        r'<img src="\1" alt="Source textbook figure"/>',
        text,
    )

    # ---- global MinerU OCR cleanup (covers inline + display math) ----
    # Strip combining marks (esp. U+0332 low line) that MinerU sprinkles into
    # control sequences like \times -> \t̲i̲m̲e̲s̲ (KaTeX then fails to recognize them).
    text = re.sub(r"[\u0332\u0323\u0304\u0303\u0301\u0302\u0300\u0311\u0307]", "", text)
    text = text.replace("\x00", "")
    text = text.replace("\u2013", "-")  # en-dash -> hyphen (fixes KaTeX unknownSymbol)
    text = re.sub(r"\\dprime", r"\\prime", text)
    text = re.sub(r"\^ \{\-\} \^ \{(\\circ)\}", r"^{-\\circ}", text)
    # KaTeX rejects math commands embedded inside text-mode commands. These
    # patterns are recurring MinerU artifacts in this source book.
    text = re.sub(
        r"\\textbf\s*\{\s*([0-9 ]+)\s*\\times\s*([0-9 ]+)\s*\}",
        r"\\mathbf{\1} \\times \\mathbf{\2}",
        text,
    )
    text = re.sub(
        r"\\textbf\s*\{\s*([0-9]+)\s*\\times\s*\}",
        r"\\mathbf{\1} \\times",
        text,
    )
    text = re.sub(r"\\mathrm\s*\{\s*\\AA\s*\}", r"\\text{\\AA}", text)
    text = text.replace(
        r"\text {Ratio of molecules with energy at or above \varepsilon_ {A}}",
        r"\text {Ratio of molecules with energy at or above } \varepsilon_{A}",
    )
    text = text.replace(
        r"\text {Ratio of molecules with energy at or above E_{A}}",
        r"\text {Ratio of molecules with energy at or above } E_{A}",
    )
    text = text.replace(
        r"\text {with K_{eq} = K_{a} (1/ K_{w})}",
        r"\text {with } K_{eq} = K_{a} (1/K_{w})",
    )
    text = text.replace(
        r"\text {so that Na^{+} Cl^{-} resulted.}",
        r"\text {so that } \mathrm{Na}^{+}\mathrm{Cl}^{-}\text { resulted.}",
    )
    text = text.replace(
        r"\cdot \mathrm { ~ \textmu ~ } ^ { \circ } \mathrm { C }",
        r"\cdot {}^{\circ}\mathrm{C}",
    )
    text = text.replace(
        r"\text {[energy required to drive 100 km] = (100 km / 8 km/ \ell) 10 kWh / \ell = 125}",
        r"\text {[energy required to drive 100 km] = (100 km / 8 km/}\ell\text {) 10 kWh/}\ell\text { = 125}",
    )
    text = re.sub(
        r"Figure\s+\$\\operatorname\s*\{[^$]+\}\$\s*First,",
        "Figure 10.17)? First,",
        text,
    )

    lines = text.split("\n")
    title_line = f"# {title}" if app else f"# {ch} {title}"
    out = ["---", f'title: "{title}"', "---", "", title_line, ""]

    eq_seq = 0
    first_idx = None
    for k, ln in enumerate(lines):
        if re.match(r"^#{1,6}\s", ln):
            first_idx = k
            break
    skip_first_heading = False
    if first_idx is not None:
        source_heading = re.sub(r"^#{1,6}\s+", "", lines[first_idx]).strip()
        expected = {_normalized_title(title)}
        if app:
            expected.add(_normalized_title(f"Appendix {app[-1].upper()}"))
        skip_first_heading = _normalized_title(source_heading) in expected

    i = first_idx + 1 if skip_first_heading else 0
    skip_lines = set()
    promote_lines = set()
    if not skip_first_heading:
        first_content = i
        while first_content < len(lines) and not lines[first_content].strip():
            first_content += 1
        if app and first_content < len(lines):
            appendix_title = _normalized_title(f"Appendix {app[-1].upper()}")
            if _normalized_title(lines[first_content].strip()) == appendix_title:
                skip_lines.add(first_content)
                first_content += 1
                while first_content < len(lines) and not lines[first_content].strip():
                    skip_lines.add(first_content)
                    first_content += 1
        if (
            first_content < len(lines)
            and not re.match(r"^(?:#{1,6}\s|<table|!\[|\$\$)", lines[first_content].strip())
            and len(lines[first_content].strip()) < 200
        ):
            promote_lines.add(first_content)
    n = len(lines)
    img_re = re.compile(r"^!\[\]\((\.\./images/.*?)\)\s*$")
    head_re = re.compile(r"^(#{1,6})\s+(.*)$")

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if i in skip_lines:
            i += 1
            continue
        if i in promote_lines:
            out += [f"## {stripped}", ""]
            i += 1
            continue

        # ---- display math block ----
        if stripped.startswith("$$"):
            rest = stripped[2:]
            block = []
            if rest.endswith("$$") and len(rest) >= 4:
                block = [rest[:-2]]
                i += 1
            else:
                if rest:
                    block.append(rest)
                i += 1
                while i < n:
                    if lines[i].strip() == "$$":
                        i += 1
                        break
                    block.append(lines[i])
                    i += 1
            content = "\n".join(block).strip()
            if not content:
                continue
            # MinerU OCR cleanup inside math
            content = content.replace("\u2013", "-").replace("\u2014", "-")
            content = re.sub(r"\\dprime", r"\\prime", content)
            content = re.sub(r"\^ \{\-\} \^", r"^{-", content)
            content = re.sub(r"\\tag\s*\{", r"\\tag{", content)
            content = content.rstrip().rstrip("\\").strip()
            eq_seq += 1
            out += ["```{math}", f":label: eq-{prefix}-{eq_seq}", content, "```", ""]
            continue

        # ---- standalone markdown figure ----
        if img_re.match(line):
            imgs = []
            while i < n and img_re.match(lines[i]):
                imgs.append(img_re.match(lines[i]).group(1).strip())
                i += 1
            caption = None
            j = i
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and re.match(r"^(FIGURE|Figure)\b", lines[j].strip()):
                caption = lines[j].strip()
                i = j + 1
            else:
                i = j
            for k, img in enumerate(imgs):
                fname = os.path.splitext(img)[0].split("/")[-1]
                out += [
                    f":::{{figure}} {img}",
                    f":name: {fname}",
                    f":alt: {_figure_alt(caption if k == 0 else None)}",
                ]
                if k == 0 and caption:
                    out.append(caption)
                out += [":::", ""]
            continue

        # ---- headings ----
        mh = head_re.match(line)
        if mh:
            level = len(mh.group(1))
            t = mh.group(2).strip()
            out.append(f"## {t}" if level == 1 else f"{'#'*level} {t}")
            i += 1
            continue

        out.append(line)
        i += 1

    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"{slug}: {eq_seq} equations, {len(hashes)} figures -> {out_md}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--part", default="p1")
    ap.add_argument("--ch", type=int, default=None)
    ap.add_argument("--app", default=None, help="appendix id e.g. appa (use instead of --ch)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--img-dest", default="images")
    args = ap.parse_args()
    reconstruct(args.full, args.slug, args.part, args.ch, args.title, args.out, args.img_dest, app=args.app)
