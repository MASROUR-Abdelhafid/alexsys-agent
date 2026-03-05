"""
Outil Générateur de Rapports PDF.
Phase 2 - Étape 2.3
"""

import os
import time
from typing import Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

OUTPUT_DIR = "data/reports"


def generate_pdf_report(
    title: str,
    sections: List[Dict[str, Any]],
    filename: str = None,
) -> Dict[str, Any]:
    """
    Génère un rapport PDF professionnel.

    Args:
        title   : titre du rapport
        sections: liste de {heading, content}
        filename: nom du fichier (auto-généré si None)
    """
    t_start = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rapport_{timestamp}.pdf"

    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#3498DB'),
            spaceBefore=15,
            spaceAfter=8,
        )

        story = []

        # En-tête
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(
            f"Alexsys Solutions — Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            styles['Normal'],
        ))
        story.append(Spacer(1, 0.5*cm))

        # Sections
        for section in sections:
            story.append(Paragraph(section.get("heading", ""), heading_style))

            content = section.get("content", "")
            if isinstance(content, list):
                # Tableau
                if content and isinstance(content[0], dict):
                    headers = list(content[0].keys())
                    table_data = [headers]
                    for row in content:
                        table_data.append([str(row.get(h, "")) for h in headers])

                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                         [colors.white, colors.HexColor('#F8F9FA')]),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('PADDING', (0, 0), (-1, -1), 6),
                    ]))
                    story.append(table)
            else:
                story.append(Paragraph(str(content), styles['Normal']))

            story.append(Spacer(1, 0.3*cm))

        doc.build(story)

        latency = round((time.time() - t_start) * 1000, 2)
        file_size = os.path.getsize(filepath)

        logger.info(
            "PDF généré",
            filepath=filepath,
            size_bytes=file_size,
            latency_ms=latency,
        )

        return {
            "tool": "pdf_report",
            "filepath": filepath,
            "filename": filename,
            "file_size_bytes": file_size,
            "sections_count": len(sections),
            "latency_ms": latency,
            "status": "success",
        }

    except Exception as e:
        logger.error("Erreur génération PDF", error=str(e))
        return {
            "tool": "pdf_report",
            "error": str(e),
            "status": "error",
        }