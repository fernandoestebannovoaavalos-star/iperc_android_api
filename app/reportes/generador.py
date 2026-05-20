from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import base64
from datetime import datetime, date, timezone, timedelta

LIMA = timezone(timedelta(hours=-5))


def _fmt_fecha(valor, incluir_hora=True):
    """
    Formatea fecha/datetime a 'dd/mm/YYYY [HH:MM]'.
    Tras la migración a TIMESTAMPTZ, psycopg2 devuelve datetimes
    con tzinfo=UTC-05:00 ya en hora Lima — solo formateamos.
    Para datetime.now() del pie de página usamos LIMA explícito.
    """
    if valor is None:
        return 'No registrado'
    if isinstance(valor, str):
        valor = valor.strip()
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
                    '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'):
            try:
                valor = datetime.strptime(valor, fmt)
                break
            except ValueError:
                continue
        else:
            return valor
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor.strftime('%d/%m/%Y')
    fmt = '%d/%m/%Y %H:%M' if incluir_hora else '%d/%m/%Y'
    return valor.strftime(fmt)


def generar_pdf_iperc(registro, peligros, firma=None, peligros_adicionales=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm)

    elementos = []

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
    cel = ParagraphStyle('cel', fontSize=7, fontName='Helvetica')

    color_header = colors.HexColor('#1a1a2e')

    # ── ENCABEZADO ────────────────────────────
    elementos.append(Paragraph(
        'EMPRESA CONSTRUCTORA — CLÍNICA LA LUZ · CAJAMARCA', estilo_titulo))
    elementos.append(Paragraph(
        'IPERC CONTINUO — ANÁLISIS DE TRABAJO SEGURO', estilo_titulo))
    elementos.append(Paragraph(
        'Ley N° 29783 · DS 005-2012-TR · Norma G.050', estilo_subtitulo))
    elementos.append(Spacer(1, 0.3*cm))

    # ── DATOS GENERALES ───────────────────────
    datos_gen = [
        ['Código:',      registro.codigo,
         'Fecha:',       _fmt_fecha(registro.fecha_registro)],
        ['Trabajador:',
         f"{registro.registrado_por.nombre} {registro.registrado_por.apellido}",
         'Estado:',      registro.estado.upper()],
        ['Área:',        registro.area.nombre,
         'Actividad:',   registro.actividad.nombre],
        ['Geo-validado:', '✓ SÍ' if registro.geo_validado else '✗ NO',
         'Coordenadas:',
         f"{registro.lat:.6f}, {registro.lon:.6f}" if registro.lat else 'No registrado'],
    ]
    tabla_datos = Table(datos_gen, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
    tabla_datos.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('FONTNAME',   (0,0), (0,-1),  'Helvetica-Bold'),
        ('FONTNAME',   (2,0), (2,-1),  'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (0,-1),  colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (2,0), (2,-1),  colors.HexColor('#f8f9fa')),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING',    (0,0), (-1,-1), 5),
    ]))
    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 0.3*cm))

    # ── PELIGROS BASE ─────────────────────────
    elementos.append(Paragraph(
        'IDENTIFICACIÓN DE PELIGROS Y CONTROLES', estilo_seccion))

    estilos_nivel = {
        'TRIVIAL':     colors.HexColor('#d4edda'),
        'TOLERABLE':   colors.HexColor('#d1ecf1'),
        'MODERADO':    colors.HexColor('#fff3cd'),
        'IMPORTANTE':  colors.HexColor('#f8d7da'),
        'INTOLERABLE': colors.HexColor('#721c24'),
    }

    filas_p = [['N°', 'Peligro', 'Riesgo', 'P', 'S', 'Nivel', 'Medidas de Control']]
    for i, p in enumerate(peligros, 1):
        filas_p.append([
            str(i),
            Paragraph(p.descripcion or '', cel),
            Paragraph(p.riesgo_consecuencia or '', cel),
            str(p.p_sin), str(p.s_sin), p.nivel_sin,
            Paragraph(p.medidas_control or '', cel),
        ])

    estilo_tp = [
        ('BACKGROUND', (0,0), (-1,0), color_header),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 7),
        ('FONTNAME',   (0,1), (-1,-1), 'Helvetica'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('PADDING',    (0,0), (-1,-1), 4),
        ('ALIGN',      (3,0), (4,-1), 'CENTER'),
        ('ALIGN',      (5,0), (5,-1), 'CENTER'),
    ]
    for i, p in enumerate(peligros, 1):
        nivel = (p.nivel_sin or '').upper()
        bg = estilos_nivel.get(nivel)
        if bg:
            estilo_tp.append(('BACKGROUND', (5,i), (5,i), bg))
            if nivel == 'INTOLERABLE':
                estilo_tp.append(('TEXTCOLOR', (5,i), (5,i), colors.white))

    tabla_p = Table(filas_p,
        colWidths=[0.7*cm, 4*cm, 3*cm, 0.7*cm, 0.7*cm, 2*cm, 6.9*cm])
    tabla_p.setStyle(TableStyle(estilo_tp))
    elementos.append(tabla_p)
    elementos.append(Spacer(1, 0.3*cm))

    # ── PELIGROS ADICIONALES ──────────────────
    pa_lista = peligros_adicionales or []
    if pa_lista:
        elementos.append(Paragraph(
            'PELIGROS ADICIONALES IDENTIFICADOS EN CAMPO', estilo_seccion))

        filas_pa = [['N°', 'Tipo', 'Descripción', 'Riesgo',
                     'P', 'S', 'Nivel', 'Medidas de Control']]
        for i, pa in enumerate(pa_lista, 1):
            filas_pa.append([
                str(i),
                Paragraph(pa.tipo or '', cel),
                Paragraph(pa.descripcion or '', cel),
                Paragraph(pa.riesgo_consecuencia or '', cel),
                str(pa.p_sin), str(pa.s_sin), pa.nivel_sin,
                Paragraph(pa.medidas_control or '', cel),
            ])

        estilo_pa = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#b45309')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 7),
            ('FONTNAME',   (0,1), (-1,-1), 'Helvetica'),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN',     (0,0), (-1,-1), 'TOP'),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('ALIGN',      (4,0), (5,-1), 'CENTER'),
            ('ALIGN',      (6,0), (6,-1), 'CENTER'),
            *[('BACKGROUND', (0,r), (-1,r), colors.HexColor('#fffbeb'))
              for r in range(1, len(filas_pa), 2)],
        ]
        for i, pa in enumerate(pa_lista, 1):
            nivel = (pa.nivel_sin or '').upper()
            bg = estilos_nivel.get(nivel)
            if bg:
                estilo_pa.append(('BACKGROUND', (6,i), (6,i), bg))
                if nivel == 'INTOLERABLE':
                    estilo_pa.append(('TEXTCOLOR', (6,i), (6,i), colors.white))

        tabla_pa = Table(filas_pa,
            colWidths=[0.6*cm, 2*cm, 3.2*cm, 2.5*cm, 0.6*cm, 0.6*cm, 1.8*cm, 6.7*cm])
        tabla_pa.setStyle(TableStyle(estilo_pa))
        elementos.append(tabla_pa)
        elementos.append(Spacer(1, 0.3*cm))

    # ── FIRMA DIGITAL ─────────────────────────
    elementos.append(Paragraph('FIRMA DIGITAL DEL TRABAJADOR', estilo_seccion))

    if firma and firma.firma_imagen:
        try:
            img_data   = firma.firma_imagen.split(',')[1]
            img_bytes  = base64.b64decode(img_data)
            img_buffer = BytesIO(img_bytes)
            img        = Image(img_buffer, width=6*cm, height=2.5*cm)
            gps_firma  = (f"{firma.lat:.6f}, {firma.lon:.6f}"
                          if getattr(firma, 'lat', None) else 'No registrado')
            datos_firma = [
                [img, ''],
                [f"Trabajador: {registro.registrado_por.nombre} {registro.registrado_por.apellido}",
                 f"DNI: {registro.registrado_por.dni}"],
                [f"Fecha y hora: {_fmt_fecha(firma.timestamp)}",
                 f"GPS: {gps_firma}"],
            ]
            tabla_firma = Table(datos_firma, colWidths=[9*cm, 9*cm])
            tabla_firma.setStyle(TableStyle([
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID',     (0,0), (-1,-1), 0.5, colors.grey),
                ('PADDING',  (0,0), (-1,-1), 5),
            ]))
            elementos.append(tabla_firma)
        except Exception:
            elementos.append(Paragraph(
                'Firma registrada digitalmente en el sistema.', estilo_normal))
    else:
        elementos.append(Paragraph('Sin firma registrada.', estilo_normal))

    elementos.append(Spacer(1, 0.5*cm))

    # ── PIE DE PÁGINA — usar datetime.now(LIMA) siempre ──
    elementos.append(Paragraph(
        f'Documento generado el {datetime.now(LIMA).strftime("%d/%m/%Y %H:%M:%S")} '
        f'· IPERC Digital · UPN Cajamarca 2026',
        ParagraphStyle('pie', fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(elementos)
    buffer.seek(0)
    return buffer