#!/usr/bin/env python3
"""Convert the Mega-CD BIOS manual PDF into readable Markdown."""

from __future__ import annotations

import argparse
import hashlib
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pymupdf


DOCS_DIR = Path(__file__).resolve().parent
DEFAULT_PDF = DOCS_DIR / "MCDBios.pdf"
DEFAULT_OUTPUT = DOCS_DIR / "MCDBios.md"
CACHE_VERSION = "watermark-subtract-v1"
WATERMARK_REFERENCE_PAGE = 3
TITLE_PAGE = 2
LOAD_SAMPLE_PLACEHOLDER = "__MEGA_CD_LOAD_SAMPLE_BLOCK__"
M68000_INSTRUCTION_REFERENCE = (
    "https://www.nxp.com/docs/en/reference-manual/M68000PRM.pdf"
)

SECTION_HEADINGS = {
    "1": "CD System Control Process Summary",
    "2": "BIOS Call Summary",
    "3": "BIOS Call Reference",
    "4": "System Bootstrap Sequencing",
    "5": "Jump Table and User Calls",
    "6": "Boot System",
    "7": "Back-up RAM",
}

SUBSECTION_HEADINGS = {
    "1-1": "Hardware Summary",
    "1-2": "Process Summary",
    "1-3": "CD System Control Chart",
    "1-4": "CD System Memory Map",
    "2-1": "BIOS Call Functions",
    "2-2": "BIOS Call List",
    "2-3": "BIOS Call Type Chart",
    "2-4": "Drive Control System Process Chart",
    "4-1": "CD Boot System Mode 1 (Boot from cartridge)",
    "4-2": "CD Boot System Mode 2 (Boot from CD disc)",
    "4-3": "Booting Application Programs",
    "5-1": "Structure of the Jump Table",
    "5-2": "BIOS Call Sequence",
    "5-3": "User Call Sequence",
    "5-4": "Exception Processing",
    "6-1": "CD-Boot",
    "7-1": "Back-up RAM",
}

REFERENCE_SECTIONS = {
    "3-D": "Drive (Mechanism)",
    "3-M": "CD-DA (Music)",
    "3-R": "CD-ROM (Data)",
    "3-B": "CD-BIOS (Other Functions)",
    "3-F": "FADER (Fader)",
    "3-C": "CDC (Decoder)",
    "3-S": "SCD (Subcode)",
    "3-L": "LED (LED Display)",
}

BIOS_CALLS = {
    "DRVINIT", "DRVOPEN", "MSCSTOP", "MSCPLAY", "MSCPLAY1", "MSCPLAYR",
    "MSCPLAYT", "MSCSEEK", "MSCSEEK1", "MSCSEEKT", "MSCPAUSEON",
    "MSCPAUSEOFF", "MSCSCANFF", "MSCSCANFR", "MSCSCANOFF", "ROMREAD",
    "ROMREADN", "ROMREADE", "ROMSEEK", "ROMPAUSEON", "ROMPAUSEOFF",
    "CDBCHK", "CDBSTAT", "CDBTOCREAD", "CDBTOCWRITE", "CDBPAUSE",
    "FDRSET", "FDRCHG", "CDCSTART", "CDCSTOP", "CDCSTAT", "CDCREAD",
    "CDCTRN", "CDCACK", "SCDINIT", "SCDSTART", "SCDSTOP", "SCDSTAT",
    "SCDREAD", "SCDPQ", "SCDPQL", "LEDSET", "CBTINIT", "CBTINT",
    "CBTOPENDISC", "CBTOPENSTAT", "CBTCHKDISC", "CBTCHKSTAT", "BRMINT",
    "BRMSTAT", "BRMSERCH", "BRMREAD", "BRMWRITE", "BRMDEL", "BRMFORMAT",
    "BRMDIR", "BRMVERIFY",
}

FIELD_RE = re.compile(
    r"^(ENTRY|IN|OUT|BREAK|FUNC|NOTE|BUG|SAMPLE)\s*:\s*(.*)$",
    re.IGNORECASE,
)
HEX_RE = re.compile(r"(?<![`A-Za-z0-9])\$[0-9A-Fa-f]+(?![A-Za-z0-9`])")
REGISTER_RE = re.compile(r"(?<![`A-Za-z0-9])(?:[da][0-7]|ccr|sr)(?![A-Za-z0-9`])", re.I)
M68000_INSTRUCTIONS = frozenset(
    """
    abcd add adda addi addq addx and andi asl asr bcc bcs beq bge bgt bhi
    bls ble blt bmi bne bpl bra bsr bvc bvs bchg bclr bset btst chk clr cmp
    cmpa cmpi cmpm dbcc dbcs dbeq dbf dbge dbgt dbhi dble dbls dblt dbmi
    dbne dbpl dbra dbt dbvc dbvs divs divu eor eori exg ext illegal jmp jsr
    lea link lsl lsr move movea movem movep moveq mulu muls nbcd neg negx
    nop not or ori pea reset rol ror roxl roxr rte rtr rts sbcd scc scs seq
    sf sge sgt shi sle sls slt smi sne spl st svc svs stop sub suba subi
    subq subx swap tas trap trapv tst unlk
    """.split()
)
M68000_INSTRUCTIONS = M68000_INSTRUCTIONS | frozenset(
    {"bhs", "blo", "dbhs", "dblo", "shs", "slo"}
)
M68000_CONDITION_INSTRUCTIONS = frozenset(
    f"{family}{condition}"
    for family in ("b", "db", "s")
    for condition in (
        "cc", "cs", "eq", "ge", "gt", "hi", "le", "ls", "lt", "mi",
        "ne", "pl", "t", "f", "vc", "vs",
    )
)
ASSEMBLY_DIRECTIVES = frozenset(
    {"dc", "dcb", "ds", "dw", "dl", "db", "equ", "org", "even"}
)
INSTRUCTION_RE = re.compile(
    r"^\s*(?:[A-Za-z_?.][\w?.]*:\s*)?"
    r"([A-Za-z][A-Za-z0-9]*)(?:\.([A-Za-z0-9]))?(?=\s|$)",
    re.IGNORECASE,
)
ASSEMBLY_REGISTER_FIXES = (
    (re.compile(r"\bdO\b"), "d0"),
    (re.compile(r"\bdl\b"), "d1"),
    (re.compile(r"\bal\b"), "a1"),
    (re.compile(r"\baø\b", re.IGNORECASE), "a0"),
)


@dataclass(frozen=True)
class TextLine:
    text: str
    x: float
    y: float
    is_table: bool = False
    columns: tuple[str, ...] = ()
    is_code: bool = False


def markdown_table_cell(text: str) -> str:
    return text.replace("|", r"\|").strip()


def cache_directory(pdf_path: Path) -> Path:
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "scd-bios-disassembly" / CACHE_VERSION / digest


def read_scan_image(page: pymupdf.Page) -> np.ndarray:
    images = page.get_images(full=True)
    if images:
        image_info = max(images, key=lambda item: item[2] * item[3])
        pixmap = pymupdf.Pixmap(page.parent, image_info[0])
        if pixmap.n != 1:
            pixmap = pymupdf.Pixmap(pymupdf.csGRAY, pixmap)
        return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width
        ).copy()

    pixmap = page.get_pixmap(colorspace=pymupdf.csGRAY, alpha=False)
    return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width
    ).copy()


def register_watermark(
    image: np.ndarray, reference: np.ndarray, page_number: int
) -> tuple[np.ndarray, float]:
    coarse_width = 630
    coarse_height = round(image.shape[0] * coarse_width / image.shape[1])
    source = cv2.resize(
        reference, (coarse_width, coarse_height), interpolation=cv2.INTER_AREA
    )
    target = cv2.resize(
        image, (coarse_width, coarse_height), interpolation=cv2.INTER_AREA
    )

    height, width = source.shape
    x0, x1 = round(width * 0.06), round(width * 0.94)
    y0, y1 = round(height * 0.195), round(height * 0.86)
    template = source[y0:y1, x0:x1].astype(np.float32)
    mask = ((template > 65) & (template < 248)).astype(np.uint8) * 255
    template_darkness = (255 - template) * (mask.astype(np.float32) / 255)
    margin_x, margin_y = round(width * 0.06), round(height * 0.04)
    search_x0, search_y0 = max(0, x0 - margin_x), max(0, y0 - margin_y)
    search_x1, search_y1 = min(width, x1 + margin_x), min(height, y1 + margin_y)
    search = 255 - target[search_y0:search_y1, search_x0:search_x1].astype(np.float32)

    scores = cv2.matchTemplate(
        search, template_darkness, cv2.TM_CCORR_NORMED, mask=mask
    )
    _, score, _, location = cv2.minMaxLoc(scores)
    if score < 0.7:
        raise ValueError(
            f"Could not reliably align the page 3 watermark with page {page_number} "
            f"(match score {score:.3f})"
        )

    offset_x = search_x0 + location[0] - x0
    offset_y = search_y0 + location[1] - y0
    transform = np.float32(
        [
            [1, 0, offset_x * image.shape[1] / coarse_width],
            [0, 1, offset_y * image.shape[0] / coarse_height],
        ]
    )
    aligned_reference = cv2.resize(
        reference, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_AREA
    )
    aligned_reference = cv2.warpAffine(
        aligned_reference,
        transform,
        (image.shape[1], image.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return aligned_reference, float(score)


def remove_watermark(
    image: np.ndarray, reference: np.ndarray, page_number: int
) -> np.ndarray:
    aligned_reference, _ = register_watermark(image, reference, page_number)
    source = aligned_reference.astype(np.float32)
    target = image.astype(np.float32)
    watermark_pixels = (source > 65) & (source < 248)
    correction = 255 - source
    text_preservation = np.clip((target - (source - 100)) / 100, 0, 1)
    cleaned = target + correction * text_preservation * watermark_pixels
    return np.clip(cleaned, 0, 255).astype(np.uint8)


def cached_page_image(
    page: pymupdf.Page,
    reference: np.ndarray,
    cache_dir: Path,
) -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"page-{page.number + 1:03}.png"
    if cache_path.exists():
        image = cv2.imread(str(cache_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise OSError(f"Could not read cached scan image: {cache_path}")
        return image

    image = read_scan_image(page)
    page_number = page.number + 1
    if page_number not in {TITLE_PAGE, WATERMARK_REFERENCE_PAGE}:
        image = remove_watermark(image, reference, page_number)
    if not cv2.imwrite(str(cache_path), image):
        raise OSError(f"Could not cache preprocessed scan image: {cache_path}")
    return image


def has_bullet_marker(
    image: np.ndarray, x: float, y: float, scale_x: float, scale_y: float
) -> bool:
    """Find a printed round bullet immediately to the left of a text line."""
    left = max(0, round((x - 20) * scale_x))
    right = min(image.shape[1], round((x - 3) * scale_x))
    top = max(0, round((y + 1) * scale_y))
    bottom = min(image.shape[0], round((y + 17) * scale_y))
    dark = {
        (pixel_x, pixel_y)
        for pixel_y in range(top, bottom)
        for pixel_x in range(left, right)
        if image[pixel_y, pixel_x] < 80
    }

    while dark:
        seed_x, seed_y = dark.pop()
        component = [(seed_x, seed_y)]
        stack = [(seed_x, seed_y)]
        min_x = max_x = seed_x
        min_y = max_y = seed_y
        while stack:
            pixel_x, pixel_y = stack.pop()
            for neighbor_y in range(pixel_y - 1, pixel_y + 2):
                for neighbor_x in range(pixel_x - 1, pixel_x + 2):
                    neighbor = (neighbor_x, neighbor_y)
                    if neighbor in dark:
                        dark.remove(neighbor)
                        stack.append(neighbor)
                        component.append(neighbor)
                        min_x = min(min_x, neighbor_x)
                        max_x = max(max_x, neighbor_x)
                        min_y = min(min_y, neighbor_y)
                        max_y = max(max_y, neighbor_y)

        width = max_x - min_x + 1
        height = max_y - min_y + 1
        area = width * height
        center_x = ((min_x + max_x) / 2) / scale_x - x
        center_y = ((min_y + max_y) / 2) / scale_y - y
        density = len(component) / area
        large_bullet = (
            28 <= width <= 42
            and 28 <= height <= 42
            and density >= 0.65
            and -14 <= center_x <= -8
            and 5 <= center_y <= 11
        )
        small_bullet = (
            8 <= width <= 14
            and 8 <= height <= 14
            and density >= 0.65
            and -8 <= center_x <= -3
            and 4 <= center_y <= 10
        )
        if large_bullet or small_bullet:
            return True
    return False


def extract_lines(page: pymupdf.Page, scan_image: np.ndarray) -> list[TextLine]:
    """Return reading-order text lines and restore bullets from the scanned page."""
    scale_x = scan_image.shape[1] / page.rect.width
    scale_y = scan_image.shape[0] / page.rect.height
    extracted: list[TextLine] = []
    records = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            x, y, _, _ = line["bbox"]
            raw_text = "".join(span["text"] for span in line["spans"])
            columns = tuple(
                clean_line(column)
                for column in re.split(r"\s{2,}", raw_text.strip())
                if clean_line(column)
            )
            text = clean_line(raw_text)
            if text:
                records.append((y, x, text, columns if len(columns) > 1 else ()))

    for y, x, text, columns in records:
        if y > page.rect.height - 45:
            continue
        if re.fullmatch(r"\d{1,2}", text) and y > page.rect.height - 100:
            continue
        if has_bullet_marker(scan_image, x, y, scale_x, scale_y):
            text = f"- {text}"
        extracted.append(TextLine(text, x, y, columns=columns))
    return extracted


def clean_line(line: str) -> str:
    line = unicodedata.normalize("NFKC", line)
    if "ienuen" in line.lower() or "s018" in line.lower():
        return ""
    line = line.replace("\ufeff", "").replace("\ufffd", "")
    line = line.replace("•", " ")
    line = re.sub(r"[ \t]+", " ", line).strip()
    line = re.sub(r"MEGA-CD BIOS MANUAL", "", line, flags=re.IGNORECASE)
    line = re.sub(r"CONFIDENTIAL\s+#?\d+\s+PROPERTY OF SEGA-?", "", line, flags=re.IGNORECASE)
    line = re.sub(
        r"(?:^|\s)(?:\d{1,2}\s+){0,2}Ver\s+2\.00\s+Feb\.?\s*24\s*[-']{0,2}\s*92(?:\s+\d{1,2})?",
        "",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"\bdO\b", "d0", line)
    if not line or line.upper() in {"S", "MEGA-CD", "BIOS MANUAL"}:
        return ""
    if re.fullmatch(r"(?:MEGA-CD BIOS MANUAL|CONFIDENTIAL\s+#?\d+\s+PROPERTY OF SEGA)", line, re.I):
        return ""
    replacements = (
        (r"^,?177\.1\.\s*", "1-1 "),
        (r"^12\s*-?\s*Process Summary", "1-2 Process Summary"),
        (r"^24\s+BIOS Call Type Chart", "2-3 BIOS Call Type Chart"),
        (r"^44\s+Booting Application Programs", "4-3 Booting Application Programs"),
        (r"\bCOSystem Memory Map\b", "CD System Memory Map"),
        (r"\b1EGA[.-]?CD Ga Array\b", "MEGA-CD Gate Array"),
        (r"\bSubCoDe\b", "Subcode"),
        (r"\bFaDeR\b", "Fader"),
        (r"\bROMPAUSEOF\b", "ROMPAUSEOFF"),
        (r"\bBRMFROMAT\b", "BRMFORMAT"),
        (r"\bBRMDIK\b", "BRMDIR"),
        (r"\bBRAMINIT\b", "BRMINT"),
        (r"\bBRMINIT\b", "BRMINT"),
        (r"\bBRAMSTAT\b", "BRMSTAT"),
        (r"\bBRAMDIR\b", "BRMDIR"),
    )
    for pattern, replacement in replacements:
        line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
    return line


def inline_code(text: str) -> str:
    text = text.replace("`", r"\`")
    text = HEX_RE.sub(lambda match: f"`{match.group(0)}`", text)
    return REGISTER_RE.sub(lambda match: f"`{match.group(0)}`", text)


def normalized_heading(text: str) -> str:
    return re.sub(r"[^A-Z0-9-]", "", text.upper())


def heading_for_line(
    text: str, in_reference: bool = False, section: int = 0
) -> str | None:
    compact_text = normalized_heading(text)
    if compact_text.startswith("C5JUMPTABLEANDUSERCALLS"):
        return "# 5. Jump Table and User Calls"
    if compact_text.startswith("ICDBOOTBOOTSYSTEM") or (
        section == 6
        and compact_text.replace("-", "").lstrip("0123456789").startswith(
            "CDBOOTBOOTSYSTEM"
        )
    ):
        return "## 6-1 CD-Boot"
    if section == 5:
        chapter_five_headings = {
            "STRUCTUREOFTHEJUMPTABLE": "## 5-1 Structure of the Jump Table",
            "BIOSCALLSEQUENCE": "## 5-2 BIOS Call Sequence",
            "USERCALLSEQUENCE": "## 5-3 User Call Sequence",
            "EXCEPTIONPROCESSING": "## 5-4 Exception Processing",
        }
        for prefix, heading in chapter_five_headings.items():
            if compact_text.startswith(prefix):
                return heading
    if section == 7:
        compact_text = compact_text.replace("-", "")
        chapter_seven_headings = {
            "BACKUPRAMSTATUS": "#### Back-up RAM Status",
            "BACKUPRAMREAD": "#### Back-up RAM Read",
            "BACKUPRAMDELETE": "#### Back-up RAM Delete",
            "BACKUPRAMDIRECTORY": "#### Back-up RAM Directory",
            "BACKUPRAMVERIFY": "#### Back-up RAM Verify",
        }
        for prefix, heading in chapter_seven_headings.items():
            if compact_text.startswith(prefix):
                return heading
        if compact_text.startswith("BACKUPRAM"):
            return "## 7-1 Back-up RAM"

    match = re.match(r"^\(?\s*([1-7])\s*[.)]?\s+(.+?)\s*\)?$", text)
    if match:
        number = match.group(1)
        candidate = re.sub(r"[^A-Z0-9]", "", match.group(2).upper())
        if number in SECTION_HEADINGS and (
            candidate.startswith(normalized_heading(SECTION_HEADINGS[number])[:8])
            or candidate.startswith("BACKUP")
        ):
            return f"# {number}. {SECTION_HEADINGS[number]}"

    match = re.match(r"^\s*(\d-\d)\s+(.+?)\s*$", text)
    if match and match.group(1) in SUBSECTION_HEADINGS:
        return f"## {match.group(1)} {SUBSECTION_HEADINGS[match.group(1)]}"
    compact = normalized_heading(text)
    for number, title in SUBSECTION_HEADINGS.items():
        if compact.startswith(normalized_heading(number + title)[:10]):
            return f"## {number} {title}"
    if compact.startswith("CDSYSTEMMEMORYMAP"):
        return "## 1-4 CD System Memory Map"

    if in_reference:
        legacy_heading_patterns = {
            "3-D": r"^(?:3-D\s+Drive|D\s+Drive)\b",
            "3-M": r"^(?:3-M\s+CD-DA|M\s+CD-DA)\b",
            "3-R": r"^(?:3-R\s+CD-ROM|R\s+CD-ROM)\b",
            "3-B": r"^(?:3-B\s+CD-BIOS|B\s+CD-BIOS)\b",
            "3-F": r"^(?:3-F\s+FADER|F\s+FADER)\b",
            "3-C": r"^(?:3-C\s+CDC|C\s+CDC)\b",
            "3-S": r"^(?:3-S\s+SCD|S\s+SCD)\b",
            "3-L": r"^(?:3-L\s+LED|L\s+LED)\b",
        }
        for number, title in REFERENCE_SECTIONS.items():
            if re.match(legacy_heading_patterns[number], text):
                return f"### {number} {title}"
    if compact in {"CONTENTS", "TABLEOFCONTENTS"}:
        return "# Contents"
    if compact.startswith("HOWTOREADTHISREFERENCE"):
        return "#### How to Read This Reference"
    return None


def normalize_call_line(text: str) -> tuple[str, str] | None:
    for call in sorted(BIOS_CALLS, key=len, reverse=True):
        pattern = r"^\s*" + r"\W*".join(re.escape(char) for char in call) + r"\s*(.*)$"
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            remainder = match.group(1).strip(" \t:-—")
            return call, remainder
    return None


def repair_assembly_line(text: str) -> str:
    for pattern, replacement in ASSEMBLY_REGISTER_FIXES:
        text = pattern.sub(replacement, text)
    text = re.sub(r"\b(move|lea|cmp|add|sub|and|or|eor|clr|neg|ext|swap)\.1\b", r"\1.l", text, flags=re.I)
    text = re.sub(r"\b(move|cmp|add|sub|and|or|eor|clr|neg|ext|swap)\.w\b", lambda match: match.group(0).lower(), text, flags=re.I)
    return text


def instruction_line(text: str) -> bool:
    """Recognize 68000 mnemonics listed in M68000_INSTRUCTION_REFERENCE."""
    match = INSTRUCTION_RE.match(text)
    if not match:
        return False
    mnemonic = match.group(1).lower()
    suffix = match.group(2)
    if suffix and suffix.lower() not in {"b", "w", "l", "s", "1", "i"}:
        return False
    if mnemonic == "d1" and suffix is None:
        return True
    mnemonic = re.sub(r"\d+$", "", mnemonic)
    return (
        mnemonic in M68000_INSTRUCTIONS
        or mnemonic in M68000_CONDITION_INSTRUCTIONS
        or mnemonic in ASSEMBLY_DIRECTIVES
        or mnemonic in {"callf", "enter_subroutine", "leave_subroutine"}
    )


def mark_assembly_runs(lines: list[TextLine]) -> list[TextLine]:
    """Mark instruction sequences and their nearby operands/labels as code."""
    instruction_indices = [
        index for index, line in enumerate(lines) if instruction_line(line.text)
    ]
    runs: list[tuple[int, int]] = []
    run_start: int | None = None
    run_end: int | None = None
    instruction_count = 0
    previous_instruction: int | None = None

    for index in instruction_indices:
        line = lines[index]
        crosses_field = previous_instruction is not None and any(
            FIELD_RE.match(candidate.text)
            for candidate in lines[previous_instruction + 1 : index]
        )
        connected = (
            previous_instruction is not None
            and not crosses_field
            and line.y - lines[previous_instruction].y <= 36
            and abs(line.x - lines[previous_instruction].x) <= 100
        )
        if connected:
            run_end = index
            instruction_count += 1
        else:
            if run_start is not None and run_end is not None and instruction_count >= 2:
                runs.append((run_start, run_end))
            run_start = index
            run_end = index
            instruction_count = 1
        previous_instruction = index

    if run_start is not None and run_end is not None and instruction_count >= 2:
        runs.append((run_start, run_end))

    code_indices: set[int] = set()
    for start, end in runs:
        while start > 0:
            previous = lines[start - 1]
            current = lines[start]
            if current.y - previous.y > 18 or abs(current.x - previous.x) > 100:
                break
            if FIELD_RE.match(previous.text):
                break
            if not re.match(r"^\s*[A-Za-z_?.][\w?.]*:\s*$", previous.text):
                break
            start -= 1
        code_indices.update(range(start, end + 1))

    return [
        TextLine(
            line.text,
            line.x,
            line.y,
            line.is_table,
            line.columns,
            index in code_indices,
        )
        for index, line in enumerate(lines)
    ]


def format_page(
    lines: list[TextLine],
    section: int,
    contents_mode: bool,
    call_list_mode: bool,
    call_list_rows: list[list[str]],
    load_sample_mode: bool,
    load_sample_lines: list[str],
    load_sample_finished: bool,
) -> tuple[str, int, bool, bool, list[list[str]], bool, list[str], bool]:
    in_reference = section == 3
    text_lines = mark_assembly_runs(lines)
    output: list[str] = []
    paragraph: list[str] = []
    paragraph_last_line: TextLine | None = None
    paragraph_columns: tuple[str, ...] = ()
    sample_mode = False
    code_buffer: list[str] = []
    current_call: str | None = None
    current_field: str | None = None
    entry_table_active = section >= 6 and not load_sample_finished
    generic_entry = section >= 6 and not load_sample_finished
    entry_title_active = False
    entry_rows: list[list[str]] = []
    sample_code_lines: list[str] = []
    sample_note = ""
    bullet_heading_active = False
    index = 0

    def add_entry_row(cells: list[str]) -> None:
        entry_rows.append([cell.strip() for cell in cells])

    def flush_call_list() -> None:
        nonlocal call_list_rows
        if not call_list_rows:
            return
        output.extend(
            [
                "",
                "| Abbreviation | Summary |",
                "| --- | --- |",
            ]
        )
        for name, summary, _ in call_list_rows:
            output.append(
                f"| {markdown_table_cell(name)} | {markdown_table_cell(summary)} |"
            )
        output.append("")
        call_list_rows = []

    def add_entry_text(text: str, text_line: TextLine) -> None:
        if generic_entry:
            if text_line.columns:
                add_entry_row(list(text_line.columns))
            else:
                add_entry_row(["Text", text])
            return

        if current_field == "IN":
            cells = list(text_line.columns) if text_line.columns else []
            if cells:
                parameter, *description = cells
                is_parameter = bool(re.search(r"\.[A-Za-z0-9]+$", parameter))
            else:
                match = re.match(r"^(\S+)(?:\s+(.+))?$", text)
                parameter = match.group(1) if match else ""
                description = [match.group(2)] if match and match.group(2) else []
                is_parameter = bool(re.search(r"\.[A-Za-z0-9]+$", parameter))

            if is_parameter:
                add_entry_row(["IN", parameter, " ".join(description)])
            elif entry_rows and entry_rows[-1][0] == "IN":
                row = entry_rows[-1]
                while len(row) < 3:
                    row.append("")
                row[2] = " ".join(part for part in (row[2], text) if part)
            else:
                add_entry_row(["IN", "", text])
            return

        if current_field:
            if entry_rows and entry_rows[-1][0] == current_field:
                row = entry_rows[-1]
                while len(row) < 3:
                    row.append("")
                row[2] = " ".join(part for part in (row[2], text) if part)
            else:
                add_entry_row([current_field, "", text])
        else:
            add_entry_row(["Content", text])

    def flush_code() -> None:
        if code_buffer:
            if section in {3, 6, 7} and current_field == "SAMPLE":
                sample_code_lines.extend(code_buffer)
            else:
                output.extend(["```asm", *code_buffer, "```"])
            code_buffer.clear()

    def flush_entry_table() -> None:
        nonlocal entry_title_active, sample_note
        if not entry_rows and not entry_title_active and not sample_note and not sample_code_lines:
            return
        generic_headers = ["Entry", "Description", "Details"]
        field_headers = ["Field", "Value", "Description", "Details"]
        width = max(2, max((len(row) for row in entry_rows), default=2))
        headers = list(generic_headers if generic_entry else field_headers)
        headers.extend(f"Column {number}" for number in range(len(headers) + 1, width + 1))
        output.extend(
            [
                "",
                "| " + " | ".join(headers[:width]) + " |",
                "| " + " | ".join("---" for _ in range(width)) + " |",
            ]
        )
        for row in entry_rows:
            if section == 3 and row[0] == "SAMPLE":
                continue
            values = [
                markdown_table_cell(
                    value if "```asm " in value else inline_code(value)
                )
                for value in row
            ]
            values.extend("" for _ in range(width - len(values)))
            output.append("| " + " | ".join(values) + " |")
        if section == 3 and (sample_note or sample_code_lines):
            output.extend(["", f"**SAMPLE:** {inline_code(sample_note)}".rstrip(), ""])
            if sample_code_lines:
                output.extend(["```asm", *sample_code_lines, "```"])
            sample_note = ""
            sample_code_lines.clear()
        elif section in {6, 7} and sample_code_lines:
            output.extend(["", "```asm", *sample_code_lines, "```"])
            sample_code_lines.clear()
        output.append("")
        entry_rows.clear()
        entry_title_active = False

    def flush_paragraph() -> None:
        nonlocal paragraph_last_line, paragraph_columns
        if paragraph:
            text = " ".join(paragraph)
            if entry_table_active:
                if generic_entry and paragraph_columns:
                    add_entry_row(list(paragraph_columns))
                else:
                    add_entry_text(text, paragraph_last_line or TextLine(text, 0, 0))
            else:
                output.append(f"  {text}" if bullet_heading_active else text)
            paragraph.clear()
        paragraph_columns = ()
        paragraph_last_line = None

    while index < len(text_lines):
        text_line = text_lines[index]
        text = text_line.text
        if load_sample_mode:
            load_sample_lines.append(repair_assembly_line(text))
            if text.strip().lower() == "leave_subroutine":
                load_sample_mode = False
                load_sample_finished = True
                entry_table_active = False
                generic_entry = False
                current_field = None
            index += 1
            continue
        if text_line.is_table:
            flush_code()
            flush_paragraph()
            flush_entry_table()
            output.extend(["", text, ""])
            index += 1
            continue

        if "mega-cd load sample" in text.lower():
            flush_code()
            flush_paragraph()
            flush_entry_table()
            output.extend(["", "### MEGA-CD load sample", "", LOAD_SAMPLE_PLACEHOLDER, ""])
            load_sample_mode = True
            index += 1
            continue

        is_bullet = text.startswith("- ")
        if is_bullet:
            flush_code()
            flush_paragraph()
            text = text[2:]
            sample_mode = False
            bullet_heading_active = True
            if entry_table_active:
                add_entry_row(["Item", text])
            else:
                output.append(f"- {inline_code(text)}")
            index += 1
            continue

        heading = heading_for_line(text, in_reference, section)
        if not contents_mode and heading == "## 2-2 BIOS Call List":
            flush_code()
            flush_paragraph()
            flush_entry_table()
            call_list_mode = True
            output.extend(["", heading, ""])
            index += 1
            continue
        if (
            not contents_mode
            and heading == "## 2-3 BIOS Call Type Chart"
            and call_list_mode
        ):
            flush_code()
            flush_paragraph()
            flush_call_list()
            call_list_mode = False
            output.extend(["", heading, ""])
            index += 1
            continue
        if call_list_mode:
            if "abbreviation" in text.lower() and "summary" in text.lower():
                index += 1
                continue
            call = normalize_call_line(text)
            if call and call[1]:
                call_list_rows.append(
                    [call[0], re.sub(r"^[—–-]\s*", "", call[1]), str(text_line.y)]
                )
            elif call:
                call_list_rows.append([call[0], "", str(text_line.y)])
            elif "get p,q code from subcode" in text.lower():
                call_list_rows.append(
                    ["SCDPQ", "Get P,Q code from Subcode", str(text_line.y)]
                )
            elif "get last p,q code from subcode" in text.lower():
                call_list_rows.append(
                    ["SCDPQL", "Get last P,Q code from Subcode", str(text_line.y)]
                )
            elif "set led mode" in text.lower():
                call_list_rows.append(["LEDSET", "Set LED mode", str(text_line.y)])
            elif call_list_rows and text_line.x >= 190:
                closest_row = min(
                    range(len(call_list_rows)),
                    key=lambda row_index: abs(text_line.y - float(call_list_rows[row_index][2])),
                    default=-1,
                )
                if (
                    closest_row >= 0
                    and abs(text_line.y - float(call_list_rows[closest_row][2])) <= 18
                ):
                    call_list_rows[closest_row][1] = " ".join(
                        part
                        for part in (
                            call_list_rows[closest_row][1],
                            re.sub(r"^[—–-]\s*", "", text),
                        )
                        if part
                    )
            index += 1
            continue
        if heading == "# Contents":
            contents_mode = True
        elif contents_mode and heading:
            is_actual_section = bool(
                re.match(r"^#\s+[1-7]\.", heading) and text.lstrip().startswith("(")
            )
            if is_actual_section:
                contents_mode = False
            else:
                heading = None
        if heading:
            flush_code()
            flush_paragraph()
            flush_entry_table()
            sample_mode = False
            bullet_heading_active = False
            section_heading = re.match(r"^#\s+([1-7])\.", heading)
            if section_heading:
                section = int(section_heading.group(1))
                in_reference = section == 3
                entry_table_active = False
                generic_entry = False
            elif (
                heading.startswith("## ") and section in {6, 7}
                or heading.startswith("#### ") and section == 7
            ):
                entry_table_active = not load_sample_finished
                generic_entry = not load_sample_finished
                entry_title_active = entry_table_active
            else:
                entry_table_active = False
                generic_entry = False
            current_call = None
            current_field = None
            output.extend(["", heading, ""])
            index += 1
            continue

        call = normalize_call_line(text) if in_reference or section in {6, 7} else None
        if call:
            flush_code()
            flush_paragraph()
            flush_entry_table()
            sample_mode = False
            bullet_heading_active = False
            name, description = call
            current_call = name
            current_field = None
            entry_table_active = True
            generic_entry = False
            entry_title_active = True
            if not description and index + 1 < len(text_lines):
                possible_description = text_lines[index + 1].text
                if not FIELD_RE.match(possible_description) and not normalize_call_line(possible_description):
                    description = possible_description.strip()
                    index += 1
            title = f"#### `{name}`"
            if description:
                title += f" — {inline_code(description)}"
            output.extend(["", title, ""])
            index += 1
            continue

        field = FIELD_RE.match(text)
        if field:
            flush_code()
            flush_paragraph()
            bullet_heading_active = False
            label, value = field.groups()
            label = label.upper()
            if label == "IN" and (in_reference or section in {6, 7}):
                function_name = find_call_name(value)
                if function_name and function_name != current_call:
                    flush_entry_table()
                    output.extend(["", f"#### `{function_name}`", ""])
                    current_call = function_name
                    entry_table_active = True
                    generic_entry = False
                    entry_title_active = True
            if entry_table_active:
                if current_field == "IN" and (
                    not entry_rows or entry_rows[-1][0] != "IN"
                ):
                    add_entry_row(["IN", ""])
                if label == "SAMPLE":
                    if section == 3:
                        sample_note = value
                    else:
                        add_entry_row([label, value])
                elif label == "IN" and not value:
                    pass
                else:
                    values = list(text_line.columns[1:]) if text_line.columns else []
                    if not values:
                        values = [value] if value else [""]
                    if label == "ENTRY" and entry_rows:
                        previous = entry_rows[-1]
                        if (
                            previous[0] == "Content"
                            and previous[1].lstrip("_").casefold()
                            == value.lstrip("_").casefold()
                        ):
                            entry_rows.pop()
                    add_entry_row([label, *values])
                sample_mode = label == "SAMPLE"
                current_field = label
                index += 1
                continue

            sample_mode = label == "SAMPLE"
            rendered_value = inline_code(value)
            output.extend(["", f"**{label}:**" + (f" {rendered_value}" if rendered_value else ""), ""])
            current_field = label
            index += 1
            continue

        if (in_reference or section in {6, 7}) and current_field == "IN":
            function_name = find_call_name(text)
            if function_name and function_name != current_call:
                flush_code()
                flush_entry_table()
                output.extend(["", f"#### `{function_name}`", ""])
                current_call = function_name
                entry_table_active = True
                generic_entry = False
                entry_title_active = True

        if text_line.is_code and not sample_mode:
            flush_code()
            flush_paragraph()
            flush_entry_table()
            while index < len(text_lines) and text_lines[index].is_code:
                code_buffer.append(
                    repair_assembly_line(text_lines[index].text)
                )
                index += 1
            flush_code()
            continue

        if sample_mode and (
            generic_entry
            or text_line.is_code
            or instruction_line(text)
            or code_buffer and not text.lower().startswith("see bios load sample")
        ):
            flush_paragraph()
            code_buffer.append(repair_assembly_line(text))
        else:
            flush_code()
            text = re.sub(r"^[\u2022\u00b7\u25aa]\s*", "- ", text)
            if text:
                if entry_table_active and not generic_entry:
                    flush_paragraph()
                    add_entry_text(text, text_line)
                    index += 1
                    continue
                if entry_table_active and generic_entry and text_line.columns:
                    flush_paragraph()
                    add_entry_row(list(text_line.columns))
                    index += 1
                    continue
                text = inline_code(text)
                if paragraph_last_line is not None:
                    vertical_gap = text_line.y - paragraph_last_line.y
                    same_paragraph = (
                        2.5 < vertical_gap <= 16
                        and abs(text_line.x - paragraph_last_line.x) <= 36
                    )
                    if not same_paragraph:
                        flush_paragraph()
                paragraph.append(text)
                if not paragraph_columns:
                    paragraph_columns = text_line.columns
                paragraph_last_line = text_line
                if current_field != "IN":
                    current_field = None
        index += 1

    flush_code()
    flush_paragraph()
    flush_entry_table()
    if not call_list_mode:
        flush_call_list()
    rendered = "\n".join(output)
    rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip()
    if not rendered:
        return (
            "",
            section,
            contents_mode,
            call_list_mode,
            call_list_rows,
            load_sample_mode,
            load_sample_lines,
            load_sample_finished,
        )
    return (
        rendered,
        section,
        contents_mode,
        call_list_mode,
        call_list_rows,
        load_sample_mode,
        load_sample_lines,
        load_sample_finished,
    )


def find_call_name(text: str) -> str | None:
    for call in BIOS_CALLS:
        if re.search(rf"(?<![A-Z0-9]){re.escape(call)}(?![A-Z0-9])", text, re.IGNORECASE):
            return call
    return None


def convert_pdf(pdf_path: Path, output_path: Path) -> int:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    document = pymupdf.open(pdf_path)
    if len(document) < WATERMARK_REFERENCE_PAGE:
        raise ValueError(
            f"PDF must contain page {WATERMARK_REFERENCE_PAGE} as the watermark reference"
        )
    reference = read_scan_image(document[WATERMARK_REFERENCE_PAGE - 1])
    image_cache = cache_directory(pdf_path)
    pages: list[str] = ["# Mega-CD BIOS Manual\n"]
    section = 0
    contents_mode = False
    call_list_mode = False
    call_list_rows: list[list[str]] = []
    load_sample_mode = False
    load_sample_lines: list[str] = []
    load_sample_finished = False
    for page in document:
        scan_image = cached_page_image(page, reference, image_cache)
        (
            content,
            section,
            contents_mode,
            call_list_mode,
            call_list_rows,
            load_sample_mode,
            load_sample_lines,
            load_sample_finished,
        ) = format_page(
            extract_lines(page, scan_image),
            section,
            contents_mode,
            call_list_mode,
            call_list_rows,
            load_sample_mode,
            load_sample_lines,
            load_sample_finished,
        )
        if content:
            pages.append(content)
    markdown = "\n\n".join(pages)
    if load_sample_lines:
        markdown = markdown.replace(
            LOAD_SAMPLE_PLACEHOLDER,
            "```asm\n" + "\n".join(load_sample_lines) + "\n```",
        )
    output_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return len(document)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", nargs="?", type=Path, default=DEFAULT_PDF)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    page_count = convert_pdf(args.pdf, args.output)
    print(f"Converted {page_count} pages: {args.output}")
    print(f"Preprocessed page images cached in: {cache_directory(args.pdf)}")


if __name__ == "__main__":
    main()
