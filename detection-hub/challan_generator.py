import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import time

def generate_pdf_challan(violation_data, output_dir="captures"):
    """
    Generates a PDF E-Challan based on violation data.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    cam_id = violation_data.get("cam_id", "UNKNOWN")
    v_type = violation_data.get("violation", "TRAFFIC VIOLATION")
    timestamp = violation_data.get("timestamp", "00:00:00")
    plate_number = violation_data.get("plate_number", "UNKNOWN")
    confidence = violation_data.get("confidence", 0.0)
    image_path = violation_data.get("image_path", None)
    
    # Clean filename
    safe_time = timestamp.replace(":", "")
    pdf_filename = f"challan_{cam_id}_{safe_time}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2.0, height - 50, "A.T.V.D. SYSTEM")
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2.0, height - 70, "OFFICIAL E-CHALLAN (TRAFFIC CITATION)")
    
    c.line(50, height - 85, width - 50, height - 85)
    
    # Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, "CITATION DETAILS:")
    
    c.setFont("Helvetica", 12)
    c.drawString(70, height - 140, f"Date Issued: {time.strftime('%Y-%m-%d')}")
    c.drawString(70, height - 160, f"Time of Offense: {timestamp}")
    c.drawString(70, height - 180, f"Location Node: {cam_id}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 220, "VEHICLE INFORMATION:")
    c.setFont("Helvetica", 12)
    c.drawString(70, height - 240, f"License Plate: {plate_number}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 280, "OFFENSE:")
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.8, 0, 0) # Red text for violation
    c.drawString(70, height - 300, f"{v_type.replace('_', ' ')}")
    c.setFillColorRGB(0, 0, 0)
    c.drawString(70, height - 320, f"AI Confidence Score: {int(confidence * 100)}%")
    
    # Evidence Image
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 360, "PHOTOGRAPHIC EVIDENCE:")
    
    if image_path and os.path.exists(image_path):
        try:
            # Calculate aspect ratio to fit the image on the page
            img = ImageReader(image_path)
            img_w, img_h = img.getSize()
            aspect = img_h / float(img_w)
            draw_w = 400
            draw_h = draw_w * aspect
            
            c.drawImage(image_path, 50, height - 380 - draw_h, width=draw_w, height=draw_h)
        except Exception as e:
            c.drawString(70, height - 380, f"[Image Error: {e}]")
    else:
        c.drawString(70, height - 380, "[No Evidence Image Available]")
        
    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2.0, 50, "Generated automatically by the Automated Traffic Violation Detection System.")
    
    c.save()
    return pdf_path
