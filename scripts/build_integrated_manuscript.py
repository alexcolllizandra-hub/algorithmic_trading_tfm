#!/usr/bin/env python3
"""Integrate thesis chapters 5–8 and harmonise RQ/H into the Word manuscript.

Reads TFM_Memoria.docx (original untouched), writes working + final copies outside
the git repo binary policy. Source: docs/thesis/en/chapter_*.md
"""

from __future__ import annotations

import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

REPO = Path(__file__).resolve().parents[1]
EN_DIR = REPO / "docs" / "thesis" / "en"
SOURCE_DOCX = Path(
    r"C:\Users\alexc\OneDrive\Escritorio\Alex\MASTER DATA SCIENCE\TFM\TFM_Memoria.docx"
)
OUT_DIR = SOURCE_DOCX.parent
WORKING_DOCX = OUT_DIR / "TFM_Memoria_working.docx"
FINAL_DOCX = OUT_DIR / "TFM_Memoria_integrated.docx"
FINAL_PDF = OUT_DIR / "TFM_Memoria_integrated.pdf"

# Paragraph indices in the source template (verified 2026-08-11).
INTRO_UPDATES: dict[int, str] = {
    102: (
        "The study focuses on interpretable strategies for BTC and ETH perpetual futures "
        "under a reproducible, leakage-aware experimental pipeline. Machine-learning "
        "meta-labeling (gates M1/M2), portfolio construction and paper trading appear in "
        "the methodological specification as **future phases**; they were **not executed** "
        "in the closed R1–R3 experimental arc reported in Chapters 6–8."
    ),
    107: (
        "RQ1 — Profitability after costs. Do interpretable rule-based strategies produce "
        "positive risk-adjusted performance on 1h BTC/ETH perpetuals after realistic "
        "transaction costs, out of sample?"
    ),
    108: (
        "RQ2 — Search method. Under an identical strategy space, evaluation budget and "
        "validation protocol, does a Genetic Algorithm discover better out-of-sample "
        "strategies than Random Search?"
    ),
    109: (
        "RQ3 — Meta-labeling. Does meta-labeling improve the risk-adjusted performance "
        "of base strategies? *(Specified for gates M1/M2; not evaluated in this thesis.)*"
    ),
    110: (
        "RQ4 — Regime dependence. Does strategy performance change materially across "
        "volatility regimes? *(Descriptive EDA in Chapter 3; confirmatory gate R4 SKIPPED.)*"
    ),
    111: (
        "RQ5 — Robustness. Does apparent performance survive cost and parameter "
        "perturbations, delayed execution, subperiod and cross-asset stress?"
    ),
    113: (
        "The main objective is to design, implement and evaluate a reproducible "
        "algorithmic trading framework for BTC and ETH perpetual futures while "
        "preventing information leakage, temporal contamination and holdout access "
        "during development."
    ),
    114: "The specific objectives executed in this thesis are:",
    115: "To construct and validate a reproducible dataset (price, volume, mark price, funding).",
    116: (
        "To implement and evaluate interpretable strategy families (momentum baseline and "
        "five EDA-motivated families) under causal features and next-bar execution."
    ),
    117: (
        "To compare Random Search and Genetic Algorithm under equal per-fold budgets, "
        "multiple seeds and independent outer-fold search (gates R1–R3)."
    ),
    118: (
        "To apply documented phase-gate promotion criteria (six criteria plus a separate "
        "minimum-trade veto) with Random Search as the confirmatory engine."
    ),
    119: (
        "To deliver auditable, read-only reporting from persisted experiment artifacts "
        "without opening the frozen holdout."
    ),
    120: (
        "Meta-labeling model comparison, portfolio risk controls and paper trading remain "
        "out of scope for the executed experimental arc (see Chapter 8, Table 8.1)."
    ),
    121: "The analysis tests the following hypotheses (H1–H5; see experimental_design.md):",
    122: (
        "H1. At least one interpretable family yields net-of-cost OOS Sharpe above a "
        "naive benchmark on a majority of walk-forward folds."
    ),
    123: (
        "H2. The Genetic Algorithm achieves higher median net OOS fitness than Random "
        "Search at equal budget, stable across folds and seeds."
    ),
    124: (
        "H3. Meta-labeling improves net OOS Sharpe and/or reduces drawdown without "
        "starving trades below the minimum."
    ),
    125: (
        "H4. Net OOS performance differs materially across low/medium/high volatility "
        "regimes (causal regime tags; not full-sample EDA cuts)."
    ),
    126: (
        "H5. Promoted strategies retain positive net OOS performance under the extended "
        "robustness battery (cost/parameter perturbation, delayed execution, etc.)."
    ),
    127: (
        "The executed study covers BTCUSDT and ETHUSDT Binance USDT-M perpetual futures "
        "from 2020-01-01 through the development cutoff (holdout `[2026-01-01, 2026-07-01)` "
        "frozen and not opened). Primary modelling uses 1h bars from deterministic 5m "
        "aggregation."
    ),
    128: (
        "Backtests include provisional fees, slippage, funding and next-bar execution. "
        "Order-book depth, market impact and partial fills are not fully modelled. "
        "Paper trading was not conducted."
    ),
    130: (
        "This thesis provides a reproducible framework for interpretable strategy evaluation "
        "under strict temporal validation. Chapters 2–3 establish theory and EDA; Chapter 5 "
        "states the experimental contract; Chapters 6–8 report results, discussion and "
        "conclusions for gates R1–R4. The main contributions are the corrected per-fold "
        "protocol, homogeneous multi-seed family evaluation, auditable negative evidence "
        "and an open, tested implementation."
    ),
}

CHAPTER_FILES = (
    ("chapter_05_methodology.md", "Methodology and Experimental Design"),
    ("chapter_06_results.md", "Experimental Results"),
    ("chapter_07_discussion.md", "Discussion"),
    ("chapter_08_conclusions.md", "Conclusions"),
)

METHODOLOGY_HEADING = "Methodology and Experimental Design"
REFERENCES_MARKER = "References Cited"


def strip_inline_markdown(text: str) -> str:
    """Remove lightweight markdown markers for Word plain-text insertion."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def set_paragraph_text(paragraph: Paragraph, text: str) -> None:
    for run in paragraph.runs:
        run.text = ""
    paragraph.add_run(strip_inline_markdown(text))


def insert_paragraph_after(paragraph: Paragraph, text: str = "", style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        new_para.style = style
    if text:
        new_para.add_run(text)
    return new_para


def parse_markdown_blocks(path: Path) -> list[tuple[str, str | list[list[str]]]]:
    """Return list of ('heading1'|'heading2'|'heading3'|'text'|'table', content)."""
    blocks: list[tuple[str, str | list[list[str]]]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("# "):
            blocks.append(("skip_h1", line[2:].strip()))  # chapter title handled separately
            idx += 1
            continue
        if line.startswith("## "):
            blocks.append(("heading2", line[3:].strip()))
            idx += 1
            continue
        if line.startswith("### "):
            blocks.append(("heading3", line[4:].strip()))
            idx += 1
            continue
        if line.strip().startswith("|") and "|" in line:
            table_rows: list[list[str]] = []
            while idx < len(lines) and lines[idx].strip().startswith("|"):
                row = [cell.strip() for cell in lines[idx].strip().strip("|").split("|")]
                if not all(set(cell) <= {"-", ":", " "} for cell in row):
                    table_rows.append(row)
                idx += 1
            if table_rows:
                blocks.append(("table", table_rows))
            continue
        if line.strip():
            para_lines = [line.strip()]
            idx += 1
            while idx < len(lines) and lines[idx].strip() and not lines[idx].startswith("#") and not lines[idx].strip().startswith("|"):
                para_lines.append(lines[idx].strip())
                idx += 1
            blocks.append(("text", " ".join(para_lines)))
            continue
        idx += 1
    return blocks


def add_table_after(paragraph: Paragraph, rows: list[list[str]], doc: Document) -> Paragraph:
    tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            tbl.rows[r].cells[c].text = cell
    body = doc.element.body
    body.remove(tbl._tbl)
    paragraph._p.addnext(tbl._tbl)
    return paragraph


def append_blocks_after(
    anchor: Paragraph, doc: Document, blocks: list[tuple[str, str | list[list[str]]]], *, skip_first_h1: bool
) -> Paragraph:
    current = anchor
    skipped = skip_first_h1
    for kind, content in blocks:
        if kind == "skip_h1":
            if skipped:
                skipped = False
                continue
            current = insert_paragraph_after(current, str(content), "Heading 1")
            continue
        if kind == "heading2":
            current = insert_paragraph_after(current, strip_inline_markdown(str(content)), "Heading 2")
        elif kind == "heading3":
            current = insert_paragraph_after(current, strip_inline_markdown(str(content)), "Heading 3")
        elif kind == "text":
            current = insert_paragraph_after(current, strip_inline_markdown(str(content)), "Normal")
        elif kind == "table" and isinstance(content, list):
            # caption placeholder then table
            current = insert_paragraph_after(current, "", "Normal")
            clean_rows = [[strip_inline_markdown(cell) for cell in row] for row in content]
            add_table_after(current, clean_rows, doc)
            current = insert_paragraph_after(current, "", "Normal")
    return current


def find_paragraph_index(doc: Document, predicate) -> int:
    for i, para in enumerate(doc.paragraphs):
        if predicate(para):
            return i
    raise ValueError("paragraph not found")


def clear_paragraph(paragraph: Paragraph) -> None:
    set_paragraph_text(paragraph, "")


def integrate_document(source: Path, dest: Path) -> Document:
    shutil.copy2(source, dest)
    doc = Document(str(dest))

    for idx, text in INTRO_UPDATES.items():
        if idx < len(doc.paragraphs):
            set_paragraph_text(doc.paragraphs[idx], text)

    meth_idx = find_paragraph_index(
        doc, lambda p: p.text.strip() == METHODOLOGY_HEADING and p.style.name == "Heading 1"
    )
    ref_idx = find_paragraph_index(doc, lambda p: p.text.strip().startswith(REFERENCES_MARKER))

    # Clear placeholder empties between methodology heading and references.
    for i in range(meth_idx + 1, ref_idx):
        clear_paragraph(doc.paragraphs[i])

    anchor = doc.paragraphs[meth_idx]
    first_chapter = True
    for filename, _title in CHAPTER_FILES:
        blocks = parse_markdown_blocks(EN_DIR / filename)
        if first_chapter:
            # Chapter 5 uses existing Heading 1; skip duplicate H1 in markdown.
            anchor = append_blocks_after(anchor, doc, blocks, skip_first_h1=True)
            first_chapter = False
        else:
            # New chapter Heading 1 + page break.
            anchor = insert_paragraph_after(anchor, "", "Normal")
            run = anchor.add_run()
            run.add_break(WD_BREAK.PAGE)
            anchor = insert_paragraph_after(anchor, _title, "Heading 1")
            filtered = [b for b in blocks if b[0] != "skip_h1"]
            anchor = append_blocks_after(anchor, doc, filtered, skip_first_h1=False)

    doc.save(str(dest))
    return doc


def export_pdf(docx_path: Path, pdf_path: Path) -> bool:
    try:
        import docx2pdf  # type: ignore

        docx2pdf.convert(str(docx_path), str(pdf_path))
        return pdf_path.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"PDF export via docx2pdf failed: {exc}", file=sys.stderr)
    try:
        import win32com.client  # type: ignore

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(docx_path.resolve()), ReadOnly=True)
        doc.ExportAsFixedFormat(str(pdf_path.resolve()), 17)
        doc.Close(False)
        word.Quit()
        return pdf_path.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"PDF export via Word COM failed: {exc}", file=sys.stderr)
        return False


def count_pages_pdf(pdf_path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # type: ignore

        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


def main() -> int:
    if not SOURCE_DOCX.exists():
        print(f"Source not found: {SOURCE_DOCX}", file=sys.stderr)
        return 1

    print(f"Copying source -> {WORKING_DOCX}")
    integrate_document(SOURCE_DOCX, WORKING_DOCX)
    tmp_final = FINAL_DOCX.with_suffix(".tmp.docx")
    shutil.copy2(WORKING_DOCX, tmp_final)
    if FINAL_DOCX.exists():
        FINAL_DOCX.unlink()
    tmp_final.rename(FINAL_DOCX)
    print(f"Integrated manuscript: {FINAL_DOCX}")

    pdf_ok = export_pdf(FINAL_DOCX, FINAL_PDF)
    pages = count_pages_pdf(FINAL_PDF) if pdf_ok else None
    if pdf_ok:
        print(f"PDF: {FINAL_PDF} ({pages} pages)")
    else:
        print("PDF not generated — install Microsoft Word + docx2pdf, or export manually.")

    # Visual audit summary
    doc = Document(str(FINAL_DOCX))
    headings = [p.text.strip() for p in doc.paragraphs if p.style.name == "Heading 1"]
    print("Heading 1 sequence:", headings)
    pending = [
        p.text.strip()
        for p in doc.paragraphs
        if "TÍTULO" in p.text.upper() or "TITULO TFM" in p.text.upper()
    ]
    if pending:
        print("Pending editorial markers (official title):", pending[:3])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
