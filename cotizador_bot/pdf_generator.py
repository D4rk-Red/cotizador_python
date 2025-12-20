from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime, timedelta
import io
import base64
from config import HOTEL_INFO
from precios import formatear_precio

def generar_cotizacion_pdf(info_reserva, totales, cantidad_noches):
    """
    Genera un PDF de cotización similar al modelo proporcionado
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=30,
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # --- ESTILOS ---
    estilo_hotel_nombre = ParagraphStyle('HotelName', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1a237e'), alignment=TA_LEFT)
    estilo_titulo_doc = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, alignment=TA_RIGHT, spaceAfter=20)
    estilo_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    estilo_valor = ParagraphStyle('Value', parent=styles['Normal'], fontSize=9)
    estilo_tabla_hdr = ParagraphStyle('TblHdr', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.whitesmoke, alignment=TA_CENTER)

    # --- 1. ENCABEZADO (Nombre Hotel y Tipo Documento) ---
    header_data = [
        [Paragraph(HOTEL_INFO['nombre'], estilo_hotel_nombre), Paragraph("COTIZACIÓN", estilo_titulo_doc)]
    ]
    header_tab = Table(header_data, colWidths=[3.5*inch, 3*inch])
    elementos.append(header_tab)
    
    # --- 2. INFO DE CONTROL (Código y Fechas) ---
    fecha_emision = datetime.now().strftime('%d.%m.%y')
    fecha_validez = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%y')
    
    control_data = [
        [Paragraph("COD. COT", estilo_label), Paragraph("241125-14", estilo_valor)], # Código ejemplo
        [Paragraph("FECHA EMISIÓN", estilo_label), Paragraph(fecha_emision, estilo_valor)],
        [Paragraph("FECHA VALIDEZ", estilo_label), Paragraph(fecha_validez, estilo_valor)]
    ]
    control_tab = Table(control_data, colWidths=[1.5*inch, 1.5*inch], hAlign='RIGHT')
    control_tab.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elementos.append(control_tab)
    elementos.append(Spacer(1, 0.2*inch))

    # --- 3. DATOS DEL CLIENTE / HOTEL ---
    cliente_data = [
        [Paragraph("CLIENTE", estilo_label), Paragraph("S/N", estilo_valor), Paragraph("TELÉFONO", estilo_label), Paragraph(HOTEL_INFO['telefono'], estilo_valor)],
        [Paragraph("EMAIL", estilo_label), Paragraph("-", estilo_valor), Paragraph("RUT", estilo_label), Paragraph(HOTEL_INFO['rut'], estilo_valor)]
    ]
    cliente_tab = Table(cliente_data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
    elementos.append(cliente_tab)
    elementos.append(Spacer(1, 0.2*inch))

    # --- 4. DETALLES DE ESTADÍA ---
    estadia_data = [
        [Paragraph("CHECK IN", estilo_label), info_reserva['check_in'], Paragraph("NOCHES", estilo_label), str(cantidad_noches)],
        [Paragraph("CHECK OUT", estilo_label), info_reserva['check_out'], Paragraph("HUÉSPEDES", estilo_label), info_reserva['cant_personas']]
    ]
    estadia_tab = Table(estadia_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    estadia_tab.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 1, colors.black), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elementos.append(estadia_tab)
    elementos.append(Spacer(1, 0.3*inch))

    # --- 5. TABLA DE CARGOS ---
    tabla_header = [Paragraph("DESCRIPCIÓN", estilo_tabla_hdr), Paragraph("CANT", estilo_tabla_hdr), Paragraph("UNITARIO", estilo_tabla_hdr), Paragraph("TOTAL CLP", estilo_tabla_hdr)]
    datos_items = [tabla_header]
    
    for hab in totales['habitaciones']:
        datos_items.append([
            hab['tipo'],
            str(hab['cantidad']),
            formatear_precio(hab['precio_noche']),
            formatear_precio(hab['total'])
        ])

    items_tab = Table(datos_items, colWidths=[3*inch, 0.8*inch, 1.2*inch, 1.5*inch])
    items_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    elementos.append(items_tab)

    # --- 6. TOTALES ---
    totales_data = [
        ["", "NETO", formatear_precio(totales['total_neto'])],
        ["", "IVA (19%)", formatear_precio(totales['iva'])],
        ["", "TOTAL", formatear_precio(totales['total_bruto'])]
    ]
    totales_tab = Table(totales_data, colWidths=[3.8*inch, 1.2*inch, 1.5*inch])
    totales_tab.setStyle(TableStyle([
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (1,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (1,2), (2,2), colors.HexColor('#e8eaf6')),
    ]))
    elementos.append(totales_tab)
    elementos.append(Spacer(1, 0.4*inch))

    # --- 7. TÉRMINOS Y DATOS BANCARIOS ---
    terminos_txt = """
    <b>TÉRMINOS Y CONDICIONES:</b><br/>
    • Tarifa NO Reembolsable. Sujeto a disponibilidad.<br/>
    • Para confirmar se solicita pago del 100% por adelantado.<br/>
    • Incluye Desayuno. Check-in: 15:00 | Check-out: 12:00.
    """
    elementos.append(Paragraph(terminos_txt, estilo_valor))
    elementos.append(Spacer(1, 0.2*inch))

    banco_txt = f"""
    <b>DATOS BANCARIOS PARA TRANSFERENCIA:</b><br/>
    Razón Social: {HOTEL_INFO['nombre']} SpA | RUT: {HOTEL_INFO['rut']}<br/>
    Banco: Banco de BYTE | Cta Corriente: NUEMRO <br/>
    Email: {HOTEL_INFO['email']}
    """
    elementos.append(Paragraph(banco_txt, estilo_valor))

    # --- CONSTRUCCIÓN ---
    doc.build(elementos)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return base64.b64encode(pdf_bytes).decode('utf-8')