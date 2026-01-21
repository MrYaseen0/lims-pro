"""
PDF Report Generator for LIMS.Pro
Generates professional lab-style PDF reports using ReportLab
"""
import os
from datetime import datetime, timezone
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF


# Colors
PRIMARY_COLOR = colors.HexColor('#4F46E5')  # Indigo
SECONDARY_COLOR = colors.HexColor('#64748B')  # Slate
SUCCESS_COLOR = colors.HexColor('#059669')  # Emerald
DANGER_COLOR = colors.HexColor('#DC2626')  # Red
LIGHT_BG = colors.HexColor('#F8FAFC')
BORDER_COLOR = colors.HexColor('#E2E8F0')


def get_styles():
    """Create custom paragraph styles for the report"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='LabTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='LabSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=SECONDARY_COLOR,
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=PRIMARY_COLOR,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceBefore=12,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='InfoLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=SECONDARY_COLOR
    ))
    
    styles.add(ParagraphStyle(
        name='InfoValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='Normal',
        fontSize=10,
        textColor=colors.black
    ))
    
    styles.add(ParagraphStyle(
        name='AbnormalValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DANGER_COLOR,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='NormalValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black
    ))
    
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=SECONDARY_COLOR,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SignatureName',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SignatureTitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=SECONDARY_COLOR,
        alignment=TA_CENTER
    ))
    
    return styles


def create_header(styles, lab_info):
    """Create the lab header section"""
    elements = []
    
    # Lab name and branding
    elements.append(Paragraph(lab_info.get('name', 'LIMS.Pro Diagnostic Laboratory'), styles['LabTitle']))
    elements.append(Paragraph(lab_info.get('address', '123 Medical Center, Healthcare City'), styles['LabSubtitle']))
    elements.append(Paragraph(f"Phone: {lab_info.get('phone', '+1-234-567-8900')} | Email: {lab_info.get('email', 'info@lims.pro')}", styles['LabSubtitle']))
    
    # Horizontal line
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceBefore=6, spaceAfter=12))
    
    # Report title
    elements.append(Paragraph("LABORATORY TEST REPORT", styles['ReportTitle']))
    
    return elements


def create_patient_info_table(patient, order, styles):
    """Create patient and order information section"""
    elements = []
    
    elements.append(Paragraph("Patient Information", styles['SectionHeader']))
    
    # Create a two-column layout for patient and order info
    patient_data = [
        ['Patient Name:', patient.get('name', 'N/A'), 'Report No:', order.get('order_id', 'N/A')],
        ['Age / Gender:', f"{patient.get('age', 'N/A')} Years / {patient.get('gender', 'N/A').capitalize()}", 'Sample ID:', order.get('samples', [{}])[0].get('sample_id', 'N/A') if order.get('samples') else 'N/A'],
        ['Patient ID:', patient.get('patient_id', 'N/A'), 'Collection Date:', format_date(order.get('samples', [{}])[0].get('collection_time')) if order.get('samples') else 'N/A'],
        ['Contact:', patient.get('phone', 'N/A'), 'Report Date:', format_date(datetime.now(timezone.utc).isoformat())],
        ['Referred By:', order.get('referring_doctor', 'Self') or 'Self', 'Priority:', order.get('priority', 'Normal').upper()],
    ]
    
    table = Table(patient_data, colWidths=[80, 150, 80, 150])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), SECONDARY_COLOR),
        ('TEXTCOLOR', (2, 0), (2, -1), SECONDARY_COLOR),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ('TEXTCOLOR', (3, 0), (3, -1), colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, BORDER_COLOR),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    return elements


def create_results_table(tests, styles):
    """Create the test results table"""
    elements = []
    
    elements.append(Paragraph("Test Results", styles['SectionHeader']))
    
    # Table header
    header = ['Test Name', 'Result', 'Unit', 'Reference Range', 'Status']
    data = [header]
    
    for test in tests:
        result = test.get('result', {})
        values = result.get('values', {})
        is_abnormal = result.get('is_abnormal', False)
        
        # Get result value and unit
        result_value = values.get('value', 'Pending')
        unit = values.get('unit', '-')
        
        # Reference range (placeholder - would come from test definition)
        ref_range = get_reference_range(test.get('test_code', ''))
        
        # Status indicator
        if not result:
            status = 'Pending'
        elif is_abnormal:
            status = 'ABNORMAL'
        else:
            status = 'Normal'
        
        data.append([
            test.get('test_name', 'Unknown Test'),
            str(result_value),
            unit,
            ref_range,
            status
        ])
    
    # Create table
    col_widths = [180, 70, 50, 100, 70]
    table = Table(data, colWidths=col_widths)
    
    # Style the table
    style_commands = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Body styling
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        
        # Grid
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]
    
    # Highlight abnormal values
    for i, test in enumerate(tests, start=1):
        result = test.get('result', {})
        is_abnormal = result.get('is_abnormal', False)
        if is_abnormal:
            style_commands.extend([
                ('TEXTCOLOR', (1, i), (1, i), DANGER_COLOR),
                ('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'),
                ('TEXTCOLOR', (4, i), (4, i), DANGER_COLOR),
                ('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'),
                ('BACKGROUND', (4, i), (4, i), colors.HexColor('#FEE2E2')),
            ])
        elif result:
            style_commands.extend([
                ('TEXTCOLOR', (4, i), (4, i), SUCCESS_COLOR),
                ('BACKGROUND', (4, i), (4, i), colors.HexColor('#D1FAE5')),
            ])
    
    table.setStyle(TableStyle(style_commands))
    elements.append(table)
    elements.append(Spacer(1, 8))
    
    # Add legend
    legend_text = "<font color='#DC2626'><b>ABNORMAL</b></font> = Result outside normal reference range"
    elements.append(Paragraph(legend_text, styles['Footer']))
    
    return elements


def create_notes_section(tests, styles):
    """Create notes and comments section"""
    elements = []
    
    # Collect all notes
    notes = []
    for test in tests:
        result = test.get('result', {})
        if result.get('technician_notes'):
            notes.append(f"<b>{test.get('test_name')}:</b> {result.get('technician_notes')}")
        if result.get('pathologist_notes'):
            notes.append(f"<b>Pathologist Note ({test.get('test_name')}):</b> {result.get('pathologist_notes')}")
    
    if notes:
        elements.append(Paragraph("Clinical Notes", styles['SectionHeader']))
        for note in notes:
            elements.append(Paragraph(f"• {note}", styles['Normal']))
        elements.append(Spacer(1, 12))
    
    return elements


def create_signature_section(order, pathologist_name, styles):
    """Create the signature section"""
    elements = []
    
    elements.append(Spacer(1, 24))
    
    # Signature table
    sig_data = [
        ['', ''],
        ['_' * 30, '_' * 30],
        ['Lab Technician', 'Pathologist'],
        ['', pathologist_name or 'Dr. Authorized Signatory'],
    ]
    
    sig_table = Table(sig_data, colWidths=[230, 230])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 2), (-1, 2), SECONDARY_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(sig_table)
    elements.append(Spacer(1, 12))
    
    # Verification note
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=12, spaceAfter=8))
    elements.append(Paragraph(
        "This is a computer-generated report. Results have been verified and approved by authorized personnel.",
        styles['Footer']
    ))
    
    return elements


def create_footer(order, styles):
    """Create the footer section"""
    elements = []
    
    report_date = format_date(order.get('report_released_at') or datetime.now(timezone.utc).isoformat())
    
    footer_text = f"""
    Report Generated: {report_date} | Accession No: {order.get('order_id', 'N/A')} | Page 1 of 1<br/>
    <b>LIMS.Pro Diagnostic Laboratory</b> - Quality Healthcare Through Accurate Diagnostics
    """
    
    elements.append(Paragraph(footer_text, styles['Footer']))
    
    return elements


def get_reference_range(test_code):
    """Get reference range for a test (placeholder - would come from test definition)"""
    ranges = {
        'CBC': '4.5-11.0 x10^9/L',
        'BGF': '70-100 mg/dL',
        'LIPID': '<200 mg/dL',
        'LFT': '7-56 U/L',
        'KFT': '0.7-1.3 mg/dL',
        'THYROID': '0.4-4.0 mIU/L',
        'URINE': 'Negative',
        'HBA1C': '4.0-5.6%',
        'VITD': '30-100 ng/mL',
        'VITB12': '200-900 pg/mL',
    }
    return ranges.get(test_code, 'See lab reference')


def format_date(date_str):
    """Format date string for display"""
    if not date_str:
        return 'N/A'
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        return dt.strftime('%d %b %Y, %I:%M %p')
    except:
        return str(date_str)


def generate_report_pdf(order_data, patient_data, pathologist_name=None, lab_info=None):
    """
    Generate a PDF report for a lab order
    
    Args:
        order_data: Order details including tests and results
        patient_data: Patient information
        pathologist_name: Name of approving pathologist
        lab_info: Laboratory branding information
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    # Default lab info
    if not lab_info:
        lab_info = {
            'name': 'LIMS.Pro Diagnostic Laboratory',
            'address': '123 Medical Center, Healthcare City',
            'phone': '+1-234-567-8900',
            'email': 'info@lims.pro'
        }
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=f"Lab Report - {order_data.get('order_id', 'Report')}",
        author="LIMS.Pro Laboratory"
    )
    
    # Get styles
    styles = get_styles()
    
    # Build document elements
    elements = []
    
    # Header with lab branding
    elements.extend(create_header(styles, lab_info))
    
    # Patient information
    elements.extend(create_patient_info_table(patient_data, order_data, styles))
    
    # Test results table
    elements.extend(create_results_table(order_data.get('tests', []), styles))
    
    # Notes section
    elements.extend(create_notes_section(order_data.get('tests', []), styles))
    
    # Signature section
    elements.extend(create_signature_section(order_data, pathologist_name, styles))
    
    # Footer
    elements.extend(create_footer(order_data, styles))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return buffer


def save_report_pdf(buffer, order_id, reports_dir):
    """
    Save the PDF buffer to a file
    
    Args:
        buffer: BytesIO buffer with PDF content
        order_id: Order ID for filename
        reports_dir: Directory to save reports
    
    Returns:
        Filename of saved PDF
    """
    filename = f"report_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, 'wb') as f:
        f.write(buffer.read())
    
    return filename
