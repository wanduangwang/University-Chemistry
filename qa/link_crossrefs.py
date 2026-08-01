"""Author project-wide MyST links for the textbook's printed references.

The source uses human-facing identifiers such as ``Figure 8.41`` while the
reconstruction uses stable labels such as ``fig-p1-ch08-59``.  This script uses
the read-only audit's mapping, inserts anchors for otherwise unlabeled raw
captions/tables, and converts prose references to explicit MyST links without
renumbering the source edition.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from audit_crossrefs import (
    CHAPTERS,
    ID_RE,
    MATH_REFERENCE_RE,
    REFERENCE_RE,
    ROOT,
    SOURCE_DEFECTS,
    TARGET_PREFIX_RE,
    audit,
    normalize_kind,
    printed_id_from_latex,
)


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)")
EXISTING_HTML_LINK_RE = re.compile(r"<a\s+[^>]*>.*?</a>", re.IGNORECASE)
RAW_TABLE_TARGET_RE = re.compile(
    r"(?m)^\((?P<label>(?:xref-visual-[^)]+|original-table-[^)]+|original-fig-5-20))\)=\n"
    r"(?P<table><table>.*</table>)$"
)
DISPLAY_CORRECTIONS = {
    ("table", "4.3", "chapters/p1-ch02-atomic-molecular-structure.md"): "2.4",
    ("figure", "3.31", "chapters/p1-ch03-thermochemistry.md"): "3.25",
    ("figure", "4.3E", "chapters/p1-ch04-entropy-second-law.md"): "CS4.3E",
}


def choose_label(
    targets: dict,
    kind: str,
    printed_id: str,
    file: str,
    line: int,
) -> str | None:
    locations = targets.get(kind, {}).get(printed_id, [])
    if not locations:
        return None
    local = [item for item in locations if item["file"] == file]
    candidates = local or locations
    candidates = sorted(candidates, key=lambda item: abs(item["line"] - line))
    return candidates[0].get("label")


def corrected_id(kind: str, printed_id: str, file: str) -> str:
    return DISPLAY_CORRECTIONS.get((kind, printed_id, file), printed_id)


def link_plain_match(match: re.Match, *, targets: dict, file: str, line: int) -> str:
    kind = normalize_kind(match.group("kind"))
    raw = match.group(0)
    ids = list(ID_RE.finditer(match.group("ids")))
    resolved: list[tuple[re.Match, str, str]] = []
    ids_offset = match.start("ids") - match.start(0)
    for item in ids:
        printed_id = item.group(0).upper()
        if (kind, printed_id, file) in SOURCE_DEFECTS:
            return raw
        label = choose_label(targets, kind, printed_id, file, line)
        if not label:
            return raw
        resolved.append((item, printed_id, label))

    if not resolved:
        return raw

    if len(resolved) == 1:
        item, printed_id, label = resolved[0]
        start = ids_offset + item.start()
        end = ids_offset + item.end()
        display = raw[:start] + corrected_id(kind, printed_id, file) + raw[end:]
        return f"[{display}](#{label})"

    pieces: list[str] = []
    cursor = 0
    for index, (item, printed_id, label) in enumerate(resolved):
        start = ids_offset + item.start()
        end = ids_offset + item.end()
        display_id = corrected_id(kind, printed_id, file)
        if index == 0:
            pieces.append(f"[{raw[:start]}{display_id}](#{label})")
        else:
            pieces.append(raw[cursor:start])
            pieces.append(f"[{display_id}](#{label})")
        cursor = end
    pieces.append(raw[cursor:])
    return "".join(pieces)


def link_segment(text: str, *, targets: dict, file: str, line: int) -> str:
    placeholders: list[str] = []

    def mask_link(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"\x00LINK{len(placeholders) - 1}\x00"

    text = MARKDOWN_LINK_RE.sub(mask_link, text)
    text = EXISTING_HTML_LINK_RE.sub(mask_link, text)

    def replace_math(match: re.Match) -> str:
        kind = normalize_kind(match.group("kind"))
        printed_id = printed_id_from_latex(match.group("math"))
        if not printed_id or (kind, printed_id, file) in SOURCE_DEFECTS:
            return match.group(0)
        label = choose_label(targets, kind, printed_id, file, line)
        if not label:
            return match.group(0)
        display_id = corrected_id(kind, printed_id, file)
        return f"[{match.group('kind')} {display_id}](#{label})"

    text = MATH_REFERENCE_RE.sub(replace_math, text)
    # Protect the links just generated before applying the plain-text matcher.
    text = MARKDOWN_LINK_RE.sub(mask_link, text)
    text = REFERENCE_RE.sub(
        lambda match: link_plain_match(
            match, targets=targets, file=file, line=line
        ),
        text,
    )
    for index, value in reversed(list(enumerate(placeholders))):
        text = text.replace(f"\x00LINK{index}\x00", value)
    return text


def link_line(text: str, *, targets: dict, file: str, line: int) -> str:
    target_prefix = TARGET_PREFIX_RE.match(text)
    if target_prefix:
        return target_prefix.group(0) + link_segment(
            text[target_prefix.end() :], targets=targets, file=file, line=line
        )
    return link_segment(text, targets=targets, file=file, line=line)


def synthetic_anchors(report: dict) -> dict[str, dict[int, set[str]]]:
    anchors: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    directive_labels: set[str] = set()
    for path in CHAPTERS.glob("*.md"):
        directive_labels.update(
            re.findall(
                r"(?m)^:(?:label|name):\s+(\S+)",
                path.read_text(encoding="utf-8"),
            )
        )
    for entries in report["targets"].values():
        for locations in entries.values():
            for location in locations:
                label = location.get("label") or ""
                if (
                    label.startswith(("original-", "xref-visual-"))
                    and label not in directive_labels
                ):
                    anchors[location["file"]][location["line"]].add(label)
    return anchors


def wrap_raw_table_targets(source: str, *, targets: dict, file: str) -> str:
    by_label: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for kind, entries in targets.items():
        for printed_id, locations in entries.items():
            for location in locations:
                if location["file"] == file and location.get("label"):
                    by_label[location["label"]].append((kind, printed_id))

    def replace(match: re.Match) -> str:
        label = match.group("label")
        if label == "original-fig-5-20":
            return (
                ":::{figure}\n"
                f":label: {label}\n"
                ":enumerated: false\n"
                ":alt: FIGURE 5.20 from the source textbook\n"
                f"{match.group('table')}\n"
                ":::"
            )
        candidates = by_label.get(label, [])
        printed_id = candidates[0][1] if candidates else ""
        return (
            f":::\u007btable\u007d TABLE {printed_id}\n"
            f":label: {label}\n"
            ":enumerated: false\n"
            f"{match.group('table')}\n"
            ":::"
        )

    return RAW_TABLE_TARGET_RE.sub(replace, source)


def remove_duplicate_directive_targets(source: str) -> str:
    directive_labels = set(re.findall(r"(?m)^:label:\s+(\S+)\s*$", source))
    for label in directive_labels:
        source = re.sub(
            rf"(?m)^\({re.escape(label)}\)=\n",
            "",
            source,
        )
    source = re.sub(
        r"(?m)^:::\{table\}\s+\[([^\]]+)\]\(#[^)]+\)$",
        r":::{table} \1",
        source,
    )
    source = source.replace(
        ":label: original-fig-5-20\n:enumerated: false\n<table",
        ":label: original-fig-5-20\n:enumerated: false\n"
        ":alt: FIGURE 5.20 from the source textbook\n<table",
    )
    nested_link = re.compile(
        r'<a href="(?P<href>[^"]+)"><a href="(?P=href)">(?P<text>.*?)</a></a>',
        re.IGNORECASE,
    )
    while nested_link.search(source):
        source = nested_link.sub(
            r'<a href="\g<href>">\g<text></a>', source
        )
    return source


def htmlize_table_links(text: str, *, targets: dict, file: str, line: int) -> str:
    if "<table" not in text or "](#" not in text:
        return text

    def replace(match: re.Match) -> str:
        label = match.group(0).rsplit("(#", 1)[1][:-1]
        display = match.group(0)[1 : match.group(0).index("]")]
        locations = [
            location
            for entries in targets.values()
            for locations in entries.values()
            for location in locations
            if location.get("label") == label
        ]
        if not locations:
            return match.group(0)
        target_file = locations[0]["file"]
        if target_file == file:
            href = f"#{label}"
        else:
            href = f"../{Path(target_file).stem}/#{label}"
        return f'<a href="{href}">{display}</a>'

    return MARKDOWN_LINK_RE.sub(replace, text)


def process_file(
    path: Path,
    *,
    targets: dict,
    anchors: dict[int, set[str]],
    write: bool,
) -> tuple[int, int]:
    relative = path.relative_to(ROOT).as_posix()
    original_source = path.read_text(encoding="utf-8")
    source = original_source
    source = wrap_raw_table_targets(source, targets=targets, file=relative)
    source = remove_duplicate_directive_targets(source)
    lines = source.splitlines()
    existing_declarations = {
        line for line in lines if re.fullmatch(r"\([^)]+\)=", line)
    }
    linked: list[str] = []
    changed_links = 0
    in_math = False
    in_figure = False
    in_table = False
    for line_number, value in enumerate(lines, start=1):
        stripped = value.strip()
        if (
            not stripped
            and line_number > 1
            and re.fullmatch(
                r"\((?:original-|xref-visual-)[^)]+\)=",
                lines[line_number - 2],
            )
        ):
            continue
        if stripped == "```{math}":
            in_math = True
        if stripped.startswith(":::{figure}"):
            in_figure = True
        if stripped.startswith(":::{table}"):
            in_table = True

        skip = in_math or (
            (in_figure or in_table) and stripped.startswith(":")
        )
        updated = value if skip else link_line(
            value, targets=targets, file=relative, line=line_number
        )
        updated = htmlize_table_links(
            updated, targets=targets, file=relative, line=line_number
        )
        if updated != value:
            changed_links += 1

        if line_number in anchors:
            for label in sorted(anchors[line_number]):
                declaration = f"({label})="
                if declaration not in existing_declarations:
                    linked.append(declaration)
        linked.append(updated)

        if in_math and stripped == "```" and line_number != 1:
            in_math = False
        if in_figure and stripped == ":::" and not stripped.startswith(":::{"):
            in_figure = False
        if in_table and stripped == ":::" and not stripped.startswith(":::{"):
            in_table = False

    result = "\n".join(linked) + ("\n" if source.endswith("\n") else "")
    inserted_anchors = sum(
        1 for line in linked if re.fullmatch(r"\([^)]+\)=", line)
    ) - sum(1 for line in lines if re.fullmatch(r"\([^)]+\)=", line))
    if write and result != original_source:
        path.write_text(result, encoding="utf-8")
    return changed_links, inserted_anchors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="update chapter files")
    args = parser.parse_args()
    report = audit()
    anchors = synthetic_anchors(report)
    total_links = 0
    total_anchors = 0
    changed_files = 0
    for path in sorted(CHAPTERS.glob("*.md")):
        links, inserted = process_file(
            path,
            targets=report["targets"],
            anchors=anchors.get(path.relative_to(ROOT).as_posix(), {}),
            write=args.write,
        )
        if links or inserted:
            changed_files += 1
            print(f"{path.name}: {links} linked lines, {inserted} anchors")
        total_links += links
        total_anchors += inserted
    mode = "updated" if args.write else "would update"
    print(
        f"{mode} {changed_files} files: {total_links} linked lines, "
        f"{total_anchors} anchors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
