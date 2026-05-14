from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import base64
from datetime import datetime

def generar_pdf_iperc(registro, peligros, firma=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    elementos = []

    # Estilo título
    estilo_titulo = ParagraphStyle('titulo',
        fontSize=14, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=6)
    estilo_subtitulo = ParagraphStyle('subtitulo',
        fontSize=10, fontName='Helvetica',
        alignment=TA_CENTER, spaceAfter=12, textColor=colors.grey)
    estilo_seccion = ParagraphStyle('seccion',
        fontSize=10, fontName='Helvetica-Bold',
        spaceBefore=12, spaceAfter=6,
        textColor=colors.HexColor('#F97316'))
    estilo_normal = ParagraphStyle('normal',
        fontSize=8, fontName='Helvetica', spaceAfter=3)

    # ENCABEZADO
    elementos.append(Paragraph('EMPRESA CONSTRUCTORA — CLÍNICA LA LUZ · CAJAMARCA', estilo_titulo))
    elementos.append(Paragraph('IPERC CONTINUO — ANÁLISIS DE TRABAJO SEGURO', estilo_titulo))
    elementos.append(Paragraph('Ley N° 29783 · DS 005-2012-TR · Norma G.050', estilo_subtitulo))
    elementos.append(Spacer(1, 0.3*cm))

    # DATOS GENERALES
    color_header = colors.HexColor('#1a1a2e')
    datos_gen = [
        ['Código:', registro.codigo, 'Fecha:', registro.fecha_registro.strftime('%d/%m/%Y %H:%M')],
        ['Trabajador:', f"{registro.registrado_por.nombre} {registro.registrado_por.apellido}",
         'Estado:', registro.estado.upper()],
        ['Área:', registro.area.nombre, 'Actividad:', registro.actividad.nombre],
        ['Geo-validado:', '✓ SÍ' if registro.geo_validado else '✗ NO',
         'Coordenadas:', f"{registro.lat:.6f}, {registro.lon:.6f}" if registro.lat else 'No registrado'],
    ]

    tabla_datos = Table(datos_gen, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
    tabla_datos.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 0.3*cm))

    # TABLA DE PELIGROS
    elementos.append(Paragraph('IDENTIFICACIÓN DE PELIGROS Y CONTROLES', estilo_seccion))

    encabezado = [['N°', 'Peligro', 'Riesgo', 'P', 'S', 'Nivel', 'Medidas de Control']]
    filas = encabezado

    colores_nivel = {
        'TRIVIAL': colors.HexColor('#d4edda'),
        'TOLERABLE': colors.HexColor('#d1ecf1'),
        'MODERADO': colors.HexColor('#fff3cd'),
        'IMPORTANTE': colors.HexColor('#f8d7da'),
        'INTOLERABLE': colors.HexColor('#721c24'),
    }

    for i, p in enumerate(peligros, 1):
        filas.append([
            str(i),
            Paragraph(p.descripcion, ParagraphStyle('p', fontSize=7)),
            Paragraph(p.riesgo_consecuencia, ParagraphStyle('p', fontSize=7)),
            str(p.p_sin),
            str(p.s_sin),
            p.nivel_sin,
            Paragraph(p.medidas_control, ParagraphStyle('p', fontSize=7)),
        ])

    tabla_peligros = Table(filas,
        colWidths=[0.7*cm, 4*cm, 3*cm, 0.7*cm, 0.7*cm, 2*cm, 6.9*cm])
    tabla_peligros.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), color_header),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (3,0), (4,-1), 'CENTER'),
        ('ALIGN', (5,0), (5,-1), 'CENTER'),
    ]))
    elementos.append(tabla_peligros)
    elementos.append(Spacer(1, 0.3*cm))

    # FIRMA DIGITAL
    elementos.append(Paragraph('FIRMA DIGITAL DEL TRABAJADOR', estilo_seccion))

    if firma and firma.firma_imagen:
        try:
            img_data = firma.firma_imagen.split(',')[1]
            img_bytes = base64.b64decode(img_data)
            img_buffer = BytesIO(img_bytes)
            img = Image(img_buffer, width=6*cm, height=2.5*cm)
            datos_firma = [
                [img, ''],
                [f"Trabajador: {registro.registrado_por.nombre} {registro.registrado_por.apellido}",
                 f"DNI: {registro.registrado_por.dni}"],
                [f"Fecha y hora: {firma.timestamp.strftime('%d/%m/%Y %H:%M:%S')}",
                 f"GPS: {firma.lat:.6f}, {firma.lon:.6f}" if firma.lat else "GPS: No registrado"],
            ]
            tabla_firma = Table(datos_firma, colWidths=[9*cm, 9*cm])
            tabla_firma.setStyle(TableStyle([
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('PADDING', (0,0), (-1,-1), 5),
            ]))
            elementos.append(tabla_firma)
        except:
            elementos.append(Paragraph('Firma registrada digitalmente en el sistema.', estilo_normal))
    else:
        elementos.append(Paragraph('Sin firma registrada.', estilo_normal))

    elementos.append(Spacer(1, 0.5*cm))

    # PIE DE PÁGINA
    elementos.append(Paragraph(
        f'Documento generado el {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} · IPERC Digital · UPN Cajamarca 2026',
        ParagraphStyle('pie', fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(elementos)
    buffer.seek(0)
    return buffer