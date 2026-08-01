"""Audit printed figure, table, and equation references in the MyST book.

The reconstructed source preserves the textbook's visible identifiers (for
example ``Figure 7.19``) separately from the stable MyST labels generated for
figures and equations.  This audit maps those two namespaces and reports every
prose reference that cannot yet resolve to a target.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ROOT / "chapters"

PRINTED_ID = r"(?:CS)?\d{1,2}(?:\.\d{1,3})+(?:[A-Za-z])?"
REFERENCE_RE = re.compile(
    rf"\b(?P<kind>Figures?|Tables?|Equations?|Eq\.)\s*"
    rf"(?P<ids>\(?{PRINTED_ID}\)?"
    rf"(?:\s*(?:,|and|or|through|to|-)\s*\(?{PRINTED_ID}\)?)*)",
    re.IGNORECASE,
)
ID_RE = re.compile(PRINTED_ID, re.IGNORECASE)
FIGURE_ID_RE = re.compile(rf"\bFIGURE\s+({PRINTED_ID})")
TABLE_ID_RE = re.compile(rf"\bTABLE\s+({PRINTED_ID})")
TAG_RE = re.compile(r"\\tag\s*\{\s*([^{}]+?)\s*\}")
LABEL_RE = re.compile(r"^:(?:label|name):\s+(\S+)\s*$")
TARGET_PREFIX_RE = re.compile(rf"^\s*(?:FIGURE|TABLE)\s+{PRINTED_ID}\b")
AUTHORED_LINK_RE = re.compile(r"\[(?P<text>[^\]]+)\]\(#(?P<label>[^)]+)\)")
AUTHORED_HTML_LINK_RE = re.compile(
    r'<a\s+href="[^"#]*#(?P<label>[^"#]+)"[^>]*>(?P<text>.*?)</a>',
    re.IGNORECASE,
)
ANCHOR_RE = re.compile(r"^\((?P<label>[^)]+)\)=\s*$")
MATH_REFERENCE_RE = re.compile(
    r"\b(?P<kind>Figures?|Tables?|Equations?|Eq\.)\s*"
    r"(?P<math>\$[^$\n]+\$)",
    re.IGNORECASE,
)
CHAPTER_RE = re.compile(r"p1-ch(\d{2})-")

@dataclass(frozen=True)
class Location:
    file: str
    line: int
    label: str | None = None


@dataclass(frozen=True)
class Reference:
    kind: str
    printed_id: str
    file: str
    line: int
    text: str
    target_label: str | None = None


# These are source-edition anomalies confirmed against the local chapter PDFs.
# The replacement identifier is handled by the linker where the printed number
# itself is wrong; here we record the correct navigation target.
MANUAL_TARGETS = {
    ("table", "4.3", "chapters/p1-ch02-atomic-molecular-structure.md"): Location(
        "chapters/p1-ch02-atomic-molecular-structure.md",
        1071,
        "xref-visual-p1-ch02-atomic-molecular-structure-1071",
    ),
    ("figure", "3.31", "chapters/p1-ch03-thermochemistry.md"): Location(
        "chapters/p1-ch03-thermochemistry.md", 1892, "fig-p1-ch03-60"
    ),
    ("figure", "CS4.2B", "chapters/p1-ch04-entropy-second-law.md"): Location(
        "chapters/p1-ch04-entropy-second-law.md", 2252, "eq-p1-ch04-155"
    ),
    ("figure", "4.3E", "chapters/p1-ch04-entropy-second-law.md"): Location(
        "chapters/p1-ch04-entropy-second-law.md", 2427, "fig-p1-ch04-84"
    ),
    ("figure", "CS7.1B", "chapters/p1-ch07-electrochemistry.md"): Location(
        "chapters/p1-ch07-electrochemistry.md", 2113, "fig-p1-ch07-71"
    ),
}

SOURCE_DEFECTS = {
    ("figure", "CS10.3M", "chapters/p1-ch10-molecular-bonding-i.md"): (
        "The source PDF cites Figure CS10.3m in black, unlinked text but does "
        "not contain that figure or a destination."
    )
}


def normalize_id(value: str) -> str:
    return re.sub(r"\s+", "", value).strip("()").upper()


def normalize_kind(value: str) -> str:
    value = value.lower()
    if value.startswith("fig"):
        return "figure"
    if value.startswith("tab"):
        return "table"
    return "equation"


def printed_id_from_latex(value: str) -> str | None:
    """Recover a printed identifier from OCR-damaged inline math.

    Examples in the source include ``$\\underline{{6 . 4}}$`` and
    ``$\\mathrm { C S 1 1 . 4 p }$``.  Removing LaTeX command names while
    retaining their arguments recovers the human-visible identifier.
    """

    compact = value.replace("\\cdot", ".")
    compact = re.sub(r"\\[A-Za-z]+", "", compact)
    compact = re.sub(r"[^A-Za-z0-9.]", "", compact).upper()
    compact = re.sub(r"\.{2,}", ".", compact)
    match = re.search(PRINTED_ID, compact, re.IGNORECASE)
    return normalize_id(match.group(0)) if match else None


def original_label(kind: str, printed_id: str) -> str:
    prefix = {"figure": "fig", "table": "table", "equation": "eq"}[kind]
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_id(printed_id).lower()).strip("-")
    return f"original-{prefix}-{slug}"


def add_target(
    targets: dict[str, dict[str, list[Location]]],
    kind: str,
    printed_id: str,
    location: Location,
) -> None:
    targets[kind][normalize_id(printed_id)].append(location)


def scan_file(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    relative = path.relative_to(ROOT).as_posix()
    targets: dict[str, dict[str, list[Location]]] = {
        "figure": defaultdict(list),
        "table": defaultdict(list),
        "equation": defaultdict(list),
    }
    references: list[Reference] = []
    ignored_lines: set[int] = set()
    visuals: list[Location] = []
    chapter_match = CHAPTER_RE.search(path.name)
    chapter_number = str(int(chapter_match.group(1))) if chapter_match else None

    def belongs_to_current_chapter(printed_id: str) -> bool:
        first_component = re.match(r"(?:CS)?(\d+)", printed_id)
        return bool(
            first_component
            and chapter_number
            and str(int(first_component.group(1))) == chapter_number
        )

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith(":::{figure}"):
            start = i
            block: list[str] = []
            label = None
            while i < len(lines):
                block.append(lines[i])
                option = LABEL_RE.match(lines[i].strip())
                if option:
                    label = option.group(1)
                stripped = lines[i].strip()
                if i == start or stripped == ":::" or stripped.startswith(":"):
                    ignored_lines.add(i)
                if i > start and lines[i].strip() == ":::":
                    i += 1
                    break
                i += 1
            for printed_id in dict.fromkeys(FIGURE_ID_RE.findall("\n".join(block))):
                add_target(
                    targets,
                    "figure",
                    printed_id,
                    Location(relative, start + 1, label),
                )
            if label:
                visuals.append(Location(relative, start + 1, label))
            continue

        if line.strip().startswith(":::{table}"):
            start = i
            block: list[str] = []
            label = None
            while i < len(lines):
                block.append(lines[i])
                option = LABEL_RE.match(lines[i].strip())
                if option:
                    label = option.group(1)
                stripped = lines[i].strip()
                if i == start or stripped == ":::" or stripped.startswith(":"):
                    ignored_lines.add(i)
                if i > start and lines[i].strip() == ":::":
                    i += 1
                    break
                i += 1
            for printed_id in dict.fromkeys(TABLE_ID_RE.findall("\n".join(block))):
                add_target(
                    targets,
                    "table",
                    printed_id,
                    Location(relative, start + 1, label),
                )
            if label:
                visuals.append(Location(relative, start + 1, label))
            continue

        if line.strip() == "```{math}":
            start = i
            block: list[str] = []
            label = None
            while i < len(lines):
                block.append(lines[i])
                option = LABEL_RE.match(lines[i].strip())
                if option:
                    label = option.group(1)
                ignored_lines.add(i)
                if i > start and lines[i].strip() == "```":
                    i += 1
                    break
                i += 1
            joined = "\n".join(block[:-1]).rstrip()
            printed_ids = list(TAG_RE.findall(joined))
            final_parenthesis = re.search(r"\(([^()\n]+)\)\s*$", joined)
            if final_parenthesis:
                recovered = printed_id_from_latex(final_parenthesis.group(1))
                if recovered:
                    printed_ids.append(recovered)
            visible = re.sub(r"\\[A-Za-z]+", "", joined)
            visible = re.sub(r"[^A-Za-z0-9.]", "", visible).upper()
            explicit_eq = re.search(rf"EQ\.?(?P<id>{PRINTED_ID})", visible)
            if explicit_eq:
                printed_ids.append(explicit_eq.group("id"))
            for printed_id in dict.fromkeys(printed_ids):
                normalized = normalize_id(printed_id)
                if (
                    re.fullmatch(PRINTED_ID, normalized, re.IGNORECASE)
                    and belongs_to_current_chapter(normalized)
                ):
                    add_target(
                        targets,
                        "equation",
                        normalized,
                        Location(relative, start + 1, label),
                    )
            continue

        figure_ids = FIGURE_ID_RE.findall(line)
        if figure_ids:
            for printed_id in dict.fromkeys(figure_ids):
                add_target(
                    targets,
                    "figure",
                    printed_id,
                    Location(relative, i + 1, original_label("figure", printed_id)),
                )

        table_ids = TABLE_ID_RE.findall(line)
        if table_ids:
            # Raw HTML tables may carry the printed title inside the same long
            # line.  The linker can place a target immediately before it.
            for printed_id in dict.fromkeys(table_ids):
                add_target(
                    targets,
                    "table",
                    printed_id,
                    Location(relative, i + 1, original_label("table", printed_id)),
                )
        if line.lstrip().startswith("<table"):
            nearby_anchors = []
            for prior in lines[max(0, i - 3) : i]:
                anchor = ANCHOR_RE.match(prior.strip())
                if anchor:
                    nearby_anchors.append(anchor.group("label"))
            visual_label = next(
                (
                    label
                    for label in reversed(nearby_anchors)
                    if label.startswith("xref-visual-")
                ),
                f"xref-visual-{path.stem}-{i + 1}",
            )
            visuals.append(
                Location(
                    relative,
                    i + 1,
                    visual_label,
                )
            )
        i += 1

    for index, line in enumerate(lines):
        if index in ignored_lines:
            continue
        authored_links = list(AUTHORED_LINK_RE.finditer(line))
        authored_links.extend(AUTHORED_HTML_LINK_RE.finditer(line))
        for authored in authored_links:
            link_text = authored.group("text")
            authored_matches = list(REFERENCE_RE.finditer(link_text))
            for match in authored_matches:
                kind = normalize_kind(match.group("kind"))
                for printed_id in ID_RE.findall(match.group("ids")):
                    references.append(
                        Reference(
                            kind=kind,
                            printed_id=normalize_id(printed_id),
                            file=relative,
                            line=index + 1,
                            text=authored.group(0),
                            target_label=authored.group("label"),
                        )
                    )
            if not authored_matches:
                label = authored.group("label")
                if label.startswith(("fig-", "original-fig-")):
                    inferred_kind = "figure"
                elif label.startswith(("table-", "original-table-", "xref-visual-")):
                    inferred_kind = "table"
                elif label.startswith(("eq-", "original-eq-")):
                    inferred_kind = "equation"
                else:
                    inferred_kind = None
                if inferred_kind:
                    for printed_id in ID_RE.findall(link_text):
                        references.append(
                            Reference(
                                kind=inferred_kind,
                                printed_id=normalize_id(printed_id),
                                file=relative,
                                line=index + 1,
                                text=authored.group(0),
                                target_label=label,
                            )
                        )
        # Do not count references that have already been authored as links.
        searchable = AUTHORED_LINK_RE.sub("", line)
        searchable = AUTHORED_HTML_LINK_RE.sub("", searchable)
        # A caption's own printed identifier is a target, not a reference.  Any
        # later mentions in that caption remain searchable.
        searchable = TARGET_PREFIX_RE.sub("", searchable, count=1)
        for match in REFERENCE_RE.finditer(searchable):
            kind = normalize_kind(match.group("kind"))
            for printed_id in ID_RE.findall(match.group("ids")):
                references.append(
                    Reference(
                        kind=kind,
                        printed_id=normalize_id(printed_id),
                        file=relative,
                        line=index + 1,
                        text=match.group(0),
                    )
                )
        for match in MATH_REFERENCE_RE.finditer(searchable):
            printed_id = printed_id_from_latex(match.group("math"))
            if printed_id:
                references.append(
                    Reference(
                        kind=normalize_kind(match.group("kind")),
                        printed_id=printed_id,
                        file=relative,
                        line=index + 1,
                        text=match.group(0),
                    )
                )

    # Some source captions were not recoverable, particularly for scanned
    # tables.  If a first mention immediately introduces a visual, associate
    # the printed identifier with that visual's stable label.
    for reference in references:
        if targets[reference.kind].get(reference.printed_id):
            continue
        if not belongs_to_current_chapter(reference.printed_id):
            continue
        following = [
            visual
            for visual in visuals
            if 0 < visual.line - reference.line <= 12
        ]
        preceding = [
            visual
            for visual in visuals
            if 0 < reference.line - visual.line <= 4
        ]
        candidates = sorted(following, key=lambda item: item.line)
        if not candidates:
            candidates = sorted(preceding, key=lambda item: -item.line)
        if candidates:
            add_target(
                targets,
                reference.kind,
                reference.printed_id,
                candidates[0],
            )
    return targets, references


def audit() -> dict:
    targets: dict[str, dict[str, list[Location]]] = {
        "figure": defaultdict(list),
        "table": defaultdict(list),
        "equation": defaultdict(list),
    }
    references: list[Reference] = []
    for path in sorted(CHAPTERS.glob("*.md")):
        file_targets, file_references = scan_file(path)
        references.extend(file_references)
        for kind, entries in file_targets.items():
            for printed_id, locations in entries.items():
                targets[kind][printed_id].extend(locations)

    for (kind, printed_id, _file), location in MANUAL_TARGETS.items():
        if location not in targets[kind][printed_id]:
            targets[kind][printed_id].append(location)

    unique_targets = {
        kind: {printed_id: locations for printed_id, locations in entries.items()}
        for kind, entries in targets.items()
    }
    duplicate_targets = {
        kind: {
            printed_id: locations
            for printed_id, locations in entries.items()
            if len(locations) > 1
        }
        for kind, entries in unique_targets.items()
    }
    resolved: list[Reference] = []
    unresolved: list[Reference] = []
    ambiguous: list[Reference] = []
    source_defects: list[dict] = []
    for reference in references:
        matches = unique_targets[reference.kind].get(reference.printed_id, [])
        matching_labels = {item.label for item in matches}
        if matches and (
            reference.target_label is None
            or reference.target_label in matching_labels
        ):
            resolved.append(reference)
        elif (
            reference.kind,
            reference.printed_id,
            reference.file,
        ) in SOURCE_DEFECTS:
            source_defects.append(
                {
                    **asdict(reference),
                    "reason": SOURCE_DEFECTS[
                        (reference.kind, reference.printed_id, reference.file)
                    ],
                }
            )
        else:
            unresolved.append(reference)

    return {
        "summary": {
            "targets": {kind: len(entries) for kind, entries in unique_targets.items()},
            "target_occurrences": {
                kind: sum(len(items) for items in entries.values())
                for kind, entries in unique_targets.items()
            },
            "references": dict(Counter(ref.kind for ref in references)),
            "reference_occurrences": len(references),
            "authored_reference_occurrences": sum(
                reference.target_label is not None for reference in references
            ),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "ambiguous": len(ambiguous),
            "source_defects": len(source_defects),
        },
        "targets": {
            kind: {
                printed_id: [asdict(location) for location in locations]
                for printed_id, locations in entries.items()
            }
            for kind, entries in unique_targets.items()
        },
        "duplicate_targets": {
            kind: {
                printed_id: [asdict(location) for location in locations]
                for printed_id, locations in entries.items()
            }
            for kind, entries in duplicate_targets.items()
        },
        "unresolved": [asdict(reference) for reference in unresolved],
        "ambiguous": [asdict(reference) for reference in ambiguous],
        "source_defects": source_defects,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit full JSON report")
    args = parser.parse_args()
    report = audit()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    summary = report["summary"]
    print("Cross-reference audit")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    for heading in (
        "duplicate_targets",
        "unresolved",
        "ambiguous",
        "source_defects",
    ):
        value = report[heading]
        if isinstance(value, list):
            print(f"\n{heading} ({len(value)}):")
            for item in value[:100]:
                print(
                    f"- {item['file']}:{item['line']} "
                    f"{item['kind']} {item['printed_id']}: {item['text']}"
                )
        else:
            count = sum(len(entries) for entries in value.values())
            print(f"\n{heading} ({count} identifiers):")
            for kind, entries in value.items():
                for printed_id, locations in list(entries.items())[:100]:
                    rendered = ", ".join(
                        f"{loc['file']}:{loc['line']}" for loc in locations
                    )
                    print(f"- {kind} {printed_id}: {rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
