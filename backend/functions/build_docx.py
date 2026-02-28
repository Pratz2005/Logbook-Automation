"""
Step 3 Function 6: buildDocx
Generates a properly formatted .docx file matching the NTU logbook template.

Template spec:
- Font: Arial, 10pt body
- Page: A4, 1 inch margins
- Header: "Biweekly Logbook Entry" centered bold
- Info table: no outer border, underline on value cells only
- Section A, B, C: bordered box tables
- Section B table: 3 cols (Task | Date From | Date To), header row #D5E8F0
- Section C: bold subheadings + paragraph text
- Footer: "Version as of 2 January 2026" right-aligned grey
"""
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree


# ─── Colour constants ───────────────────────────────────────────────
HEADER_BG = "D5E8F0"          # Section B table header row
BORDER_COLOUR = "000000"       # Black border for section tables
FOOTER_COLOUR = RGBColor(0x80, 0x80, 0x80)  # Grey footer text


def _set_cell_border(cell, **kwargs):
    """Set borders on a table cell. kwargs: top, bottom, left, right each as {'val','color','sz'}."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        if edge in kwargs:
            tag = OxmlElement(f"w:{edge}")
            cfg = kwargs[edge]
            tag.set(qn("w:val"), cfg.get("val", "single"))
            tag.set(qn("w:sz"), cfg.get("sz", "6"))
            tag.set(qn("w:space"), "0")
            tag.set(qn("w:color"), cfg.get("color", BORDER_COLOUR))
            tcBorders.append(tag)
    tcPr.append(tcBorders)


def _set_table_border(table, size: str = "6"):
    """Apply single border to all outer edges of a table."""
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = OxmlElement(f"w:{edge}")
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), size)
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), BORDER_COLOUR)
        tblBorders.append(tag)
    tblPr.append(tblBorders)


def _shade_cell(cell, fill_hex: str):
    """Set background colour of a table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _add_underline_cell(table_cell, text: str, font_size: int = 10):
    """Add underlined text to a table cell (info table value style)."""
    para = table_cell.paragraphs[0]
    run = para.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(font_size)
    run.font.underline = True


def _add_section_heading(doc: Document, title: str):
    """Add a section label paragraph (e.g. 'Section A: Objective and Scope of Work')."""
    para = doc.add_paragraph()
    run = para.add_run(title)
    run.font.name = "Arial"
    run.font.size = Pt(10)
    run.bold = True
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(2)


def buildDocx(
    section_a: str,
    work_rows: list[dict],
    section_c: str,
    metadata: dict,
) -> bytes:
    """
    Build a formatted .docx matching the NTU logbook template.

    Args:
        section_a:  Generated Section A text
        work_rows:  List of work rows [{task_description, date_from, date_to, is_leave}]
        section_c:  Generated Section C text
        metadata:   Student metadata dict

    Returns:
        bytes: The .docx file content
    """
    doc = Document()

    # ── Page setup: A4, 1-inch margins ───────────────────────────────
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, attr, Inches(1.0))

    # ── Document-wide default font ────────────────────────────────────
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Arial"
    font.size = Pt(10)

    # ── Header ────────────────────────────────────────────────────────
    header = section.header
    header_para = header.paragraphs[0]
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header_para.add_run("Biweekly Logbook Entry")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(11)

    # ── Footer ────────────────────────────────────────────────────────
    footer = section.footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer_para.add_run("Version as of 2 January 2026")
    run.font.name = "Arial"
    run.font.size = Pt(8)
    run.font.color.rgb = FOOTER_COLOUR

    # ── Info table (student details) ─────────────────────────────────
    # No outer border — only underlines on value cells
    info_fields = [
        ("Name:", metadata.get("student_name", "")),
        ("Matric No.:", metadata.get("matric_number", "")),
        ("Company:", metadata.get("company", "")),
        ("Supervisor:", metadata.get("supervisor", "")),
        ("Entry No.:", str(metadata.get("entry_number", ""))),
        ("Period:", f"{metadata.get('period_start', '')} to {metadata.get('period_end', '')}"),
        ("Submission Date:", metadata.get("submission_date", "")),
    ]

    info_table = doc.add_table(rows=0, cols=2)
    info_table.style = "Table Grid"
    # Remove all borders from info table
    tbl = info_table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = OxmlElement(f"w:{edge}")
        tag.set(qn("w:val"), "none")
        tblBorders.append(tag)
    tblPr.append(tblBorders)

    for label, value in info_fields:
        row = info_table.add_row()
        # Label cell
        label_cell = row.cells[0]
        lp = label_cell.paragraphs[0]
        lr = lp.add_run(label)
        lr.font.name = "Arial"
        lr.font.size = Pt(10)
        lr.bold = True
        label_cell.width = Inches(1.8)
        # Value cell with underline
        _add_underline_cell(row.cells[1], value)

    doc.add_paragraph()  # spacer

    # ── Section A ─────────────────────────────────────────────────────
    _add_section_heading(doc, "Section A: Objective and Scope of Work")

    sec_a_table = doc.add_table(rows=1, cols=1)
    _set_table_border(sec_a_table)
    cell_a = sec_a_table.cell(0, 0)
    cell_a.width = Inches(6.5)

    para_a = cell_a.paragraphs[0]
    run_a = para_a.add_run(section_a)
    run_a.font.name = "Arial"
    run_a.font.size = Pt(10)
    cell_a._tc.get_or_add_tcPr()  # ensure padding
    # Set cell padding
    for pad in ("w:tcMar",):
        margin_el = OxmlElement(pad)
        for side in ("top", "left", "bottom", "right"):
            m = OxmlElement(f"w:{side}")
            m.set(qn("w:w"), "115")
            m.set(qn("w:type"), "dxa")
            margin_el.append(m)
        cell_a._tc.get_or_add_tcPr().append(margin_el)

    doc.add_paragraph()  # spacer

    # ── Section B ─────────────────────────────────────────────────────
    _add_section_heading(doc, "Section B: Work Done During the Period")

    sec_b_table = doc.add_table(rows=1, cols=3)
    _set_table_border(sec_b_table)

    # Header row
    hdr_cells = sec_b_table.rows[0].cells
    col_headers = ["Task Description", "Date From", "Date To"]
    col_widths = [Inches(4.0), Inches(1.25), Inches(1.25)]

    for i, (hdr, width) in enumerate(zip(col_headers, col_widths)):
        _shade_cell(hdr_cells[i], HEADER_BG)
        hdr_cells[i].width = width
        para = hdr_cells[i].paragraphs[0]
        run = para.add_run(hdr)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(10)
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Data rows
    for row_data in work_rows:
        row = sec_b_table.add_row()
        cells = row.cells

        task_para = cells[0].paragraphs[0]
        task_run = task_para.add_run(row_data["task_description"])
        task_run.font.name = "Arial"
        task_run.font.size = Pt(10)
        # Italic for leave entries
        if row_data.get("is_leave"):
            task_run.italic = True

        for j, key in enumerate(["date_from", "date_to"], start=1):
            date_para = cells[j].paragraphs[0]
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            date_run = date_para.add_run(row_data.get(key, ""))
            date_run.font.name = "Arial"
            date_run.font.size = Pt(10)

    doc.add_paragraph()  # spacer

    # ── Section C ─────────────────────────────────────────────────────
    _add_section_heading(doc, "Section C: Reflection")

    sec_c_table = doc.add_table(rows=1, cols=1)
    _set_table_border(sec_c_table)
    cell_c = sec_c_table.cell(0, 0)

    # Parse Section C into subheadings + body
    SUBHEADINGS = [
        "Key Achievements",
        "Main Challenge Faced",
        "What I Did Well",
        "Areas for Improvement",
    ]

    lines = section_c.strip().split("\n")
    cell_c.paragraphs[0].clear()  # clear default empty para
    first_para = True

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_subheading = any(stripped.lower().startswith(sh.lower()) for sh in SUBHEADINGS)

        if first_para:
            para = cell_c.paragraphs[0]
            first_para = False
        else:
            para = cell_c.add_paragraph()

        run = para.add_run(stripped)
        run.font.name = "Arial"
        run.font.size = Pt(10)
        run.bold = is_subheading

        if is_subheading:
            para.paragraph_format.space_before = Pt(4)

    # ── Finalize ─────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
