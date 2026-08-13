import io
import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y' in footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Footer text
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 36, 25, footer_text)
        self.drawString(36, 25, "Vyoma LabOS — Confidential Laboratory Diagnostic Report | Electronically Authorized")
        
        # Footer top dividing line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 38, 612 - 36, 38)
        self.restoreState()


class PDFReportGenerator:
    def generate_pdf(self, report_data: Dict[str, Any]) -> bytes:
        """
        Generates a professional multi-page laboratory PDF report using ReportLab.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0D9488"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            alignment=2 # Right align
        )
        label_style = ParagraphStyle(
            "LabelStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#475569"),
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        val_bold_style = ParagraphStyle(
            "ValBoldStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        tbl_header_style = ParagraphStyle(
            "TblHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        cell_style = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334155"),
        )
        cell_bold_style = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        cell_mono_style = ParagraphStyle(
            "CellMono",
            parent=styles["Normal"],
            fontName="Courier-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )

        elements = []

        # 1. Header Banner
        org_name = report_data.get("organization_name", "Vyoma Diagnostic Laboratories")
        header_table_data = [
            [
                Paragraph(f"<b>{org_name}</b>", title_style),
                Paragraph("<b>OFFICIAL DIAGNOSTIC REPORT</b><br/>ISO 15189 Accredited Laboratory", subtitle_style)
            ]
        ]
        header_table = Table(header_table_data, colWidths=[320, 220])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D9488"), spaceAfter=10))

        # 2. Patient & Specimen Info Block (2 Columns Table)
        pat = report_data.get("patient", {})
        ord_info = report_data.get("order", {})
        smp_info = report_data.get("sample", {})
        rpt_info = report_data.get("report", {})

        pat_info_data = [
            [
                Paragraph("Patient Name:", label_style), Paragraph(f"<b>{pat.get('first_name', '')} {pat.get('last_name', '')}</b>", val_bold_style),
                Paragraph("Report Number:", label_style), Paragraph(f"<b>{rpt_info.get('report_number', '')}</b>", val_bold_style),
            ],
            [
                Paragraph("Patient ID:", label_style), Paragraph(pat.get("patient_id", "N/A"), val_style),
                Paragraph("Order Number:", label_style), Paragraph(ord_info.get("order_number", "N/A"), val_style),
            ],
            [
                Paragraph("Age / Gender:", label_style), Paragraph(f"{pat.get('age', 'N/A')} / {pat.get('gender', 'N/A')}", val_style),
                Paragraph("Sample ID:", label_style), Paragraph(smp_info.get("sample_identifier", "N/A"), val_style),
            ],
            [
                Paragraph("Contact Phone:", label_style), Paragraph(pat.get("phone", "N/A"), val_style),
                Paragraph("Collection Date:", label_style), Paragraph(smp_info.get("collected_at", "N/A"), val_style),
            ],
        ]

        info_table = Table(pat_info_data, colWidths=[80, 190, 90, 180])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#F1F5F9")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # 3. Critical Notice Banner (if applicable)
        if report_data.get("has_critical", False):
            crit_banner_data = [[
                Paragraph("<b>CRITICAL RESULT NOTICE:</b> One or more laboratory values cross critical thresholds requiring immediate clinical attention.", ParagraphStyle("CritText", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white))
            ]]
            crit_table = Table(crit_banner_data, colWidths=[540])
            crit_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E11D48")),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(crit_table)
            elements.append(Spacer(1, 12))

        # 4. Laboratory Results Section
        elements.append(Paragraph("<b>LABORATORY TEST RESULTS</b>", ParagraphStyle("SectionH", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#0F172A"), spaceAfter=6)))

        # Results Table Data
        # Columns: Test / Parameter, Result, Unit, Reference Range, Flag
        tbl_data = [
            [
                Paragraph("TEST / PARAMETER", tbl_header_style),
                Paragraph("RESULT VALUE", tbl_header_style),
                Paragraph("UNIT", tbl_header_style),
                Paragraph("REFERENCE RANGE", tbl_header_style),
                Paragraph("FLAG", tbl_header_style),
            ]
        ]

        tests = report_data.get("tests", [])
        for t in tests:
            # Add Test Header Row
            tbl_data.append([
                Paragraph(f"<b>{t.get('test_name', '')} ({t.get('test_code', '')})</b>", ParagraphStyle("THeader", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#0D9488"))),
                "", "", "", ""
            ])
            for res in t.get("results", []):
                flag_str = res.get("abnormal_flag", "NORMAL")
                if res.get("critical_flag", False):
                    flag_p = Paragraph("<font color='#E11D48'><b>CRITICAL</b></font>", cell_bold_style)
                elif flag_str in ["LOW", "HIGH"]:
                    flag_p = Paragraph(f"<font color='#D97706'><b>{flag_str}</b></font>", cell_bold_style)
                else:
                    flag_p = Paragraph("<font color='#059669'>NORMAL</font>", cell_style)

                ref_low = res.get("reference_low")
                ref_high = res.get("reference_high")
                ref_str = f"{ref_low} – {ref_high}" if ref_low is not None and ref_high is not None else "—"

                tbl_data.append([
                    Paragraph(f"  {res.get('parameter_name', '')}", cell_style),
                    Paragraph(str(res.get('raw_value', '')), cell_mono_style),
                    Paragraph(res.get('unit', '') or "—", cell_style),
                    Paragraph(ref_str, cell_style),
                    flag_p
                ])

        results_table = Table(tbl_data, colWidths=[180, 100, 70, 110, 80], repeatRows=1)
        
        # Build style list
        ts = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]

        # Span Test Headers
        row_idx = 1
        for t in tests:
            ts.append(('SPAN', (0, row_idx), (4, row_idx)))
            ts.append(('BACKGROUND', (0, row_idx), (4, row_idx), colors.HexColor("#F8FAFC")))
            row_idx += 1 + len(t.get("results", []))

        results_table.setStyle(TableStyle(ts))
        elements.append(results_table)
        elements.append(Spacer(1, 20))

        # 5. Verification & Authorization Footer Block
        ver_by = report_data.get("verified_by_name", "Authorized Laboratory Reviewer")
        ver_at = report_data.get("verified_at", datetime.datetime.now().strftime("%d %b %Y, %H:%M UTC"))

        auth_data = [
            [
                Paragraph(f"<b>Verified & Authorized By:</b><br/>{ver_by}", cell_style),
                Paragraph(f"<b>Verification Timestamp:</b><br/>{ver_at}", cell_style),
                Paragraph("<b>Signature:</b><br/><i>Electronically Verified</i>", cell_style),
            ]
        ]
        auth_table = Table(auth_data, colWidths=[200, 170, 170])
        auth_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))

        elements.append(KeepTogether([
            Paragraph("<b>AUTHORIZATION & VERIFICATION</b>", ParagraphStyle("AuthH", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#0F172A"), spaceAfter=5)),
            auth_table
        ]))

        # Build document with NumberedCanvas
        doc.build(elements, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


pdf_generator = PDFReportGenerator()
