import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import time

VIOLATION_DESCRIPTIONS = {
    "ILLEGAL_PARKING":    "Vehicle found stationary in a restricted/no-parking zone.",
    "SIGNAL_VIOLATION":   "Vehicle crossed the stop line while the traffic signal was RED.",
    "DIRECTION_VIOLATION":"Vehicle detected travelling against designated traffic flow (Wrong Way).",
    "RED_ROBOT":          "Vehicle crossed the stop line while the traffic signal was RED.",
    "STOP_LINE":          "Vehicle encroached beyond the designated stop line.",
    "WRONG_WAY":          "Vehicle detected travelling in the wrong direction.",
}

FINE_AMOUNTS = {
    "ILLEGAL_PARKING":    "$ 20.00",
    "SIGNAL_VIOLATION":   "$ 80.00",
    "DIRECTION_VIOLATION":"$ 100.00",
    "RED_ROBOT":          "$ 80.00",
    "STOP_LINE":          "$ 40.00",
    "WRONG_WAY":          "$ 100.00",
}

def generate_pdf_challan(violation_data, output_dir="captures"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cam_id       = violation_data.get("cam_id", "UNKNOWN")
    v_type       = violation_data.get("violation", "TRAFFIC_VIOLATION").upper().replace(" ", "_")
    timestamp    = violation_data.get("timestamp", "00:00:00")
    plate_number = violation_data.get("plate_number", "UNDETECTED")
    confidence   = violation_data.get("confidence", 0.0)
    image_path   = violation_data.get("image_path", None)

    safe_time    = timestamp.replace(":", "")
    pdf_filename = f"challan_{cam_id}_{safe_time}.pdf"
    pdf_path     = os.path.join(output_dir, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    styles = getSampleStyleSheet()
    W, H = A4

    # ── Custom styles ──────────────────────────────────────
    title_style = ParagraphStyle("title", fontSize=22, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#0a0a0a"), alignment=TA_CENTER, spaceAfter=2)
    subtitle_style = ParagraphStyle("sub", fontSize=9, fontName="Helvetica",
                                     textColor=colors.HexColor("#555555"), alignment=TA_CENTER, spaceAfter=6)
    section_header = ParagraphStyle("sh", fontSize=8, fontName="Helvetica-Bold",
                                     textColor=colors.HexColor("#1a56db"), spaceAfter=4,
                                     spaceBefore=10, leading=12, leftIndent=0)
    body_style = ParagraphStyle("body", fontSize=9, fontName="Helvetica",
                                  textColor=colors.HexColor("#222222"), leading=14)
    fine_style = ParagraphStyle("fine", fontSize=26, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#c0392b"), alignment=TA_CENTER)
    footer_style = ParagraphStyle("footer", fontSize=7, fontName="Helvetica-Oblique",
                                   textColor=colors.HexColor("#888888"), alignment=TA_CENTER)

    story = []

    # ── HEADER BANNER ─────────────────────────────────────
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("A.T.V.D. SYSTEM", title_style))
    story.append(Paragraph("Automated Traffic Violation Detection — Official Citation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a56db"), spaceAfter=6))
    story.append(Paragraph("E-CHALLAN / TRAFFIC CITATION NOTICE", ParagraphStyle("tag", fontSize=10,
                  fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=colors.HexColor("#c0392b"), spaceAfter=6)))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=10))

    # ── CITATION DETAILS TABLE ────────────────────────────
    story.append(Paragraph("CITATION DETAILS", section_header))
    issue_date = time.strftime("%d %B %Y")
    ref_no = f"ATVD-{cam_id.upper()}-{safe_time}"

    citation_data = [
        ["Reference No.:", ref_no,            "Date Issued:", issue_date],
        ["Camera Node:",   cam_id.upper(),     "Time of Offense:", timestamp],
    ]
    citation_table = Table(citation_data, colWidths=[38*mm, 62*mm, 38*mm, 32*mm])
    citation_table.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",    (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTNAME",    (2,0), (2,-1),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("TEXTCOLOR",   (0,0), (0,-1),  colors.HexColor("#555555")),
        ("TEXTCOLOR",   (2,0), (2,-1),  colors.HexColor("#555555")),
        ("TEXTCOLOR",   (1,0), (1,-1),  colors.HexColor("#111111")),
        ("TEXTCOLOR",   (3,0), (3,-1),  colors.HexColor("#111111")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#f5f7ff"), colors.white]),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(citation_table)

    # ── VEHICLE INFO ──────────────────────────────────────
    story.append(Paragraph("VEHICLE INFORMATION", section_header))
    vehicle_data = [
        ["License Plate No.:", plate_number, "Confidence Score:", f"{int(confidence * 100)}%"],
    ]
    v_table = Table(vehicle_data, colWidths=[38*mm, 62*mm, 38*mm, 32*mm])
    v_table.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",    (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTNAME",    (2,0), (2,-1),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("TEXTCOLOR",   (0,0), (0,-1),  colors.HexColor("#555555")),
        ("TEXTCOLOR",   (2,0), (2,-1),  colors.HexColor("#555555")),
        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#f5f7ff")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(v_table)

    # ── OFFENSE BOX ───────────────────────────────────────
    story.append(Paragraph("OFFENSE RECORDED", section_header))
    readable = v_type.replace("_", " ")
    description = VIOLATION_DESCRIPTIONS.get(v_type, "Traffic regulation violation detected by automated system.")
    offense_data = [
        ["Offense Type:", readable],
        ["Description:", description],
    ]
    o_table = Table(offense_data, colWidths=[38*mm, 132*mm])
    o_table.setStyle(TableStyle([
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",   (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("TEXTCOLOR",  (0,0), (0,-1), colors.HexColor("#555555")),
        ("TEXTCOLOR",  (1,0), (1,0),  colors.HexColor("#c0392b")),
        ("FONTNAME",   (1,0), (1,0),  "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#fff3f3"), colors.HexColor("#f5f7ff")]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0), (-1,-1), 6),
    ]))
    story.append(o_table)

    # ── FINE AMOUNT ───────────────────────────────────────
    fine = FINE_AMOUNTS.get(v_type, "$ 50.00")
    story.append(Spacer(1, 6*mm))
    fine_data = [["PENALTY AMOUNT", fine]]
    fine_table = Table(fine_data, colWidths=[85*mm, 85*mm])
    fine_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,0), colors.HexColor("#1a56db")),
        ("BACKGROUND",    (1,0), (1,0), colors.HexColor("#c0392b")),
        ("TEXTCOLOR",     (0,0), (-1,-1), colors.white),
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (0,0), 10),
        ("FONTSIZE",      (1,0), (1,0), 20),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(fine_table)

    # ── PHOTOGRAPHIC EVIDENCE ─────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("PHOTOGRAPHIC EVIDENCE", section_header))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4))

    if image_path:
        # Resolve path relative to script or absolute
        if not os.path.isabs(image_path):
            # Check in captures dir relative to current hub root
            potential_path = os.path.join(os.getcwd(), image_path)
            if os.path.exists(potential_path):
                image_path = potential_path
            elif os.path.exists(os.path.join(os.getcwd(), "detection-hub", image_path)):
                image_path = os.path.join(os.getcwd(), "detection-hub", image_path)

    if image_path and os.path.exists(image_path):
        try:
            img = RLImage(image_path, width=170*mm, height=95*mm)
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Paragraph(f"Figure: Automated capture at {timestamp} — Node {cam_id.upper()}", 
                                    ParagraphStyle("imgcap", fontSize=7, fontName="Helvetica-Oblique",
                                    textColor=colors.HexColor("#888888"), alignment=TA_CENTER)))
        except Exception as e:
            story.append(Paragraph(f"[Image could not be embedded: {e}]", body_style))
    else:
        story.append(Paragraph("[No evidence image available for this citation]",
                                ParagraphStyle("noimg", fontSize=8, fontName="Helvetica-Oblique",
                                textColor=colors.HexColor("#aaaaaa"), alignment=TA_CENTER)))

    # ── LEGAL NOTICE ──────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4))
    story.append(Paragraph(
        "This citation was issued automatically by the A.T.V.D. System. "
        "The photographic evidence above constitutes a lawful record of the described offense. "
        "Failure to pay within 30 days may result in escalated enforcement action.",
        ParagraphStyle("legal", fontSize=7, fontName="Helvetica-Oblique",
                        textColor=colors.HexColor("#666666"), alignment=TA_CENTER, leading=11)
    ))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Generated: {issue_date} | System: A.T.V.D. v1.0 | Ref: {ref_no}", footer_style))

    doc.build(story)
    return pdf_path
