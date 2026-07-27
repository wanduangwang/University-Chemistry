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
import os, re, sys, argparse, shutil


def reconstruct(full_md_path, slug, part, ch, title, out_md, img_dest):
    images_dir = os.path.join(os.path.dirname(full_md_path), "images")
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
    figmap = {h: f"fig-{part}-ch{ch:02d}-{i + 1}" for i, h in enumerate(hashes)}
    if img_dest:
        os.makedirs(img_dest, exist_ok=True)
        for h, name in figmap.items():
            src = os.path.join(images_dir, h)
            ext = os.path.splitext(h)[1].lower()
            dst = os.path.join(img_dest, f"{name}{ext}")
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy(src, dst)

    def _repl(m):
        h = m.group(1)
        ext = os.path.splitext(h)[1].lower()
        return f"../images/{figmap[h]}{ext}"

    text = re.sub(r"images/([0-9a-fA-F]{20,}\.(?:jpg|jpeg|png|gif))", _repl, text)

    # ---- global MinerU OCR cleanup (covers inline + display math) ----
    text = text.replace("\u2013", "-")  # en-dash -> hyphen (fixes KaTeX unknownSymbol)
    text = re.sub(r"\\dprime", r"\\prime", text)
    text = re.sub(r"\^ \{\-\} \^ \{(\\circ)\}", r"^{-\\circ}", text)

    lines = text.split("\n")
    out = ["---", f'title: "{title}"', "---", "", f"# {ch} {title}", ""]

    eq_seq = 0
    first_idx = None
    for k, ln in enumerate(lines):
        if re.match(r"^#{1,6}\s", ln):
            first_idx = k
            break
    i = 0 if first_idx is None else first_idx + 1
    n = len(lines)
    img_re = re.compile(r"^!\[\]\((\.\./images/.*?)\)\s*$")
    head_re = re.compile(r"^(#{1,6})\s+(.*)$")

    while i < n:
        line = lines[i]
        stripped = line.strip()

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
            out += ["```{math}", f":label: eq-{part}-ch{ch:02d}-{eq_seq}", content, "```", ""]
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
                out += [f"::{{figure}} {img}", f":name: {fname}"]
                if k == 0 and caption:
                    out.append(caption)
                out += ["::::", ""]
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
    ap.add_argument("--ch", type=int, required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--img-dest", default="images")
    args = ap.parse_args()
    reconstruct(args.full, args.slug, args.part, args.ch, args.title, args.out, args.img_dest)
