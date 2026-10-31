import io
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.database import get_document_by_id, get_user_preferences
from src.vector_store import query_similar_chunks
from src.rag_pipeline import generate_answer_with_llm


def generate_report_content(
    user_id: int,
    doc_ids: List[int],
    title: str,
    focus_topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synthesizes a structured study summary and report across selected documents.
    """
    topic = focus_topic or "Core concepts, findings, and methodologies"

    doc_data = []
    combined_excerpts = []
    for did in doc_ids:
        doc_info = get_document_by_id(user_id, did)
        if doc_info:
            doc_data.append(doc_info)
            chunks = query_similar_chunks(user_id, query=topic, top_k=3, doc_ids=[did])
            for c in chunks:
                combined_excerpts.append(c)

    prefs = get_user_preferences(user_id)
    provider = prefs.get("llm_provider", "gemini")
    api_key = prefs.get("api_key")

    context_str = "\n".join([
        f"- [Doc: {c['filename']}, Page {c['page']}]: \"{c['text']}\""
        for c in combined_excerpts
    ])

    prompt = f"""You are DocuMind. Generate a comprehensive academic research summary report for the title: "{title}".
Focus Topic: "{topic}".

DOCUMENT EVIDENCE EXCERPTS:
{context_str}

Please generate a well-structured document report with the following exact markdown sections:
# Executive Summary
# Key Findings & Methodologies
# Critical Analysis & Comparative Insights
# Limitations & Open Questions
# Summary Table
Include exact inline citations [Doc: <name>, Page: <page>] for all claims.
"""

    system_prompt = "You are an expert research synthesizer. Ground all claims in the provided document excerpts with page citations."

    raw_text, error = generate_answer_with_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        llm_provider=provider,
        api_key=api_key
    )

    if error and error.startswith("NO_KEY_"):
        report_text = f"""# Executive Summary
This document report compiles verified evidence across {len(doc_data)} selected documents on the topic of "{topic}".

# Document Excerpts & Key Findings
"""
        for c in combined_excerpts:
            report_text += f"- **{c['filename']} (Page {c['page']})**: \"{c['text']}\"\n\n"
        report_text += "\n*(Add your LLM API Key in Settings to generate AI-synthesized comparative sections).*"
    elif error:
        report_text = f"# Executive Summary\n\nError synthesizing report: {error}\n\n"
        for c in combined_excerpts:
            report_text += f"- {c['filename']} (Page {c['page']}): \"{c['text']}\"\n"
    else:
        report_text = raw_text or "No report content generated."

    return {
        "title": title,
        "topic": topic,
        "documents": doc_data,
        "content_markdown": report_text,
        "excerpts": combined_excerpts
    }


def export_report_to_pdf(report_data: Dict[str, Any], author_name: str) -> bytes:
    """Generates a professional, branded PDF report using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocuMindTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#B42332')
    )
    h1_style = ParagraphStyle(
        'DocuMindH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#252525'),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocuMindBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#353535'),
        spaceAfter=6
    )
    meta_style = ParagraphStyle(
        'DocuMindMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#706B68')
    )

    story = []

    # Title & Branding Header
    story.append(Paragraph("DocuMind Knowledge Report", meta_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(report_data.get("title", "Document Analysis Report"), title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Author: {author_name} | Date: {datetime.now().strftime('%B %d, %Y')} | Focus: {report_data.get('topic', 'General')}", meta_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#B42332'), spaceAfter=14))

    # Documents Analyzed Table
    docs = report_data.get("documents", [])
    if docs:
        table_data = [["Document Filename", "Pages", "Collection"]]
        for d in docs:
            table_data.append([
                d.get("filename", "Unknown"),
                str(d.get("page_count", 0)),
                d.get("collection_name") or "General"
            ])

        t = Table(table_data, colWidths=[320, 80, 130])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F7E8E5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#B42332')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E9DED7')),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

    # Parse Report Markdown into Story
    content_lines = report_data.get("content_markdown", "").split("\n")
    for line in content_lines:
        line_s = line.strip()
        if not line_s:
            story.append(Spacer(1, 4))
            continue
        if line_s.startswith("# "):
            story.append(Paragraph(line_s[2:], h1_style))
        elif line_s.startswith("## "):
            story.append(Paragraph(line_s[3:], h1_style))
        elif line_s.startswith("### "):
            story.append(Paragraph(line_s[4:], h1_style))
        else:
            # Escape HTML characters for ReportLab Paragraph
            safe_text = line_s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def export_report_to_docx(report_data: Dict[str, Any], author_name: str) -> bytes:
    """Generates an editable Word document (.docx) using python-docx."""
    doc = Document()

    # Title
    title_p = doc.add_paragraph()
    title_run = title_p.add_run(f"DocuMind Report: {report_data.get('title', 'Document Summary')}")
    title_run.font.name = 'Calibri'
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(180, 35, 50)  # Deep Red

    # Subtitle / Metadata
    sub_p = doc.add_paragraph()
    sub_run = sub_p.add_run(f"Generated for: {author_name} | Date: {datetime.now().strftime('%B %d, %Y')} | Focus: {report_data.get('topic', 'General')}")
    sub_run.font.name = 'Calibri'
    sub_run.font.size = Pt(10)
    sub_run.font.italic = True
    sub_run.font.color.rgb = RGBColor(112, 107, 104)

    # Documents Analyzed Table
    docs = report_data.get("documents", [])
    if docs:
        doc.add_heading("Documents Analyzed", level=2)
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Filename"
        hdr_cells[1].text = "Pages"
        hdr_cells[2].text = "Collection"

        for d in docs:
            row_cells = table.add_row().cells
            row_cells[0].text = d.get("filename", "")
            row_cells[1].text = str(d.get("page_count", 0))
            row_cells[2].text = d.get("collection_name") or "General"

        doc.add_paragraph()

    # Report Body
    content_lines = report_data.get("content_markdown", "").split("\n")
    for line in content_lines:
        line_s = line.strip()
        if not line_s:
            continue
        if line_s.startswith("# "):
            doc.add_heading(line_s[2:], level=1)
        elif line_s.startswith("## "):
            doc.add_heading(line_s[3:], level=2)
        elif line_s.startswith("### "):
            doc.add_heading(line_s[4:], level=3)
        elif line_s.startswith("- ") or line_s.startswith("* "):
            doc.add_paragraph(line_s[2:], style='List Bullet')
        else:
            doc.add_paragraph(line_s)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
