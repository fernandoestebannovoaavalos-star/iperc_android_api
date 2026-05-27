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


def _tabla_matriz_riesgo():
    """Matriz de riesgo P×S al pie de cada IPERC generado."""
    RED    = colors.HexColor('#E53935')
    YELLOW = colors.HexColor('#FDD835')
    GREEN  = colors.HexColor('#43A047')
    NAVY   = colors.HexColor('#1F3864')
    PURPLE = colors.HexColor('#4A148C')
    AMBER  = colors.HexColor('#F57F17')

    RED_VALS    = {1,2,3,4,5,6,7,8,9,10}
    YELLOW_VALS = {11,12,13,14,15,18}

    def cell_bg(val):
        if val in RED_VALS:    return RED
        if val in YELLOW_VALS: return YELLOW
        return GREEN
    def cell_tc(val):
        if val in YELLOW_VALS: return colors.HexColor('#212121')
        return colors.white

    MATRIX = [
        [1, 2, 4, 7, 11],
        [3, 5, 8, 12, 16],
        [6, 9, 13, 17, 20],
        [10, 14, 18, 21, 23],
        [15, 19, 22, 24, 25],
    ]
    SEV_LABELS = ['Catastrófico', 'Mortalidad', 'Permanente', 'Temporal', 'Menor']
    SEV_NUMS   = ['1', '2', '3', '4', '5']
    FREQ_DESCS = ['Común', 'Ha\nsucedido', 'Podría\nsuceder',
                  'Raro que\nsuceda', 'Práct.\nimposible']

    COLS = [0.45*cm, 2.7*cm, 0.45*cm, 2.88*cm, 2.88*cm, 2.88*cm, 2.88*cm, 2.88*cm]
    RH   = [0.55*cm, 0.75*cm, 0.75*cm, 0.75*cm, 0.75*cm, 0.75*cm,
             0.45*cm, 1.0*cm, 0.45*cm]

    sev_text = 'S\nE\nV\nE\nR\nI\nD\nA\nD'
    table_data = [
        ['P → / S ↓', '', '', 'A', 'B', 'C', 'D', 'E'],
        [sev_text, SEV_LABELS[0], SEV_NUMS[0]] + MATRIX[0],
        ['',       SEV_LABELS[1], SEV_NUMS[1]] + MATRIX[1],
        ['',       SEV_LABELS[2], SEV_NUMS[2]] + MATRIX[2],
        ['',       SEV_LABELS[3], SEV_NUMS[3]] + MATRIX[3],
        ['',       SEV_LABELS[4], SEV_NUMS[4]] + MATRIX[4],
        ['', '', '', 'A', 'B', 'C', 'D', 'E'],
        ['', '', ''] + FREQ_DESCS,
        ['', '', '', 'FRECUENCIA', '', '', '', ''],
    ]

    style_cmds = [
        ('FONTNAME',      (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,0), (-1,-1), 7),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.white),
        ('TOPPADDING',    (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 2),
        ('RIGHTPADDING',  (0,0), (-1,-1), 2),
        ('SPAN',          (0,0), (2,0)),
        ('BACKGROUND',    (0,0), (2,0), NAVY),
        ('TEXTCOLOR',     (0,0), (2,0), colors.white),
        ('FONTNAME',      (0,0), (2,0), 'Helvetica-Bold'),
        ('BACKGROUND',    (3,0), (7,0), NAVY),
        ('TEXTCOLOR',     (3,0), (7,0), colors.white),
        ('FONTNAME',      (3,0), (7,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (3,0), (7,0), 8),
        ('SPAN',          (0,1), (0,5)),
        ('BACKGROUND',    (0,1), (0,5), PURPLE),
        ('TEXTCOLOR',     (0,1), (0,5), colors.white),
        ('FONTNAME',      (0,1), (0,5), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,1), (0,5), 6),
        ('BACKGROUND',    (1,1), (1,5), colors.HexColor('#EDE7F6')),
        ('TEXTCOLOR',     (1,1), (1,5), PURPLE),
        ('FONTNAME',      (1,1), (1,5), 'Helvetica-Bold'),
        ('FONTSIZE',      (1,1), (1,5), 7),
        ('ALIGN',         (1,1), (1,5), 'LEFT'),
        ('LEFTPADDING',   (1,1), (1,5), 4),
        ('BACKGROUND',    (2,1), (2,5), PURPLE),
        ('TEXTCOLOR',     (2,1), (2,5), colors.white),
        ('FONTNAME',      (2,1), (2,5), 'Helvetica-Bold'),
        ('FONTSIZE',      (2,1), (2,5), 8),
        ('BACKGROUND',    (3,6), (7,6), NAVY),
        ('TEXTCOLOR',     (3,6), (7,6), colors.white),
        ('FONTNAME',      (3,6), (7,6), 'Helvetica-Bold'),
        ('BACKGROUND',    (0,6), (2,6), colors.HexColor('#F0EEF8')),
        ('BACKGROUND',    (3,7), (7,7), colors.HexColor('#F5F5F5')),
        ('FONTSIZE',      (3,7), (7,7), 6),
        ('BACKGROUND',    (0,7), (2,7), colors.white),
        ('SPAN',          (3,8), (7,8)),
        ('BACKGROUND',    (3,8), (7,8), AMBER),
        ('TEXTCOLOR',     (3,8), (7,8), colors.white),
        ('FONTNAME',      (3,8), (7,8), 'Helvetica-Bold'),
        ('FONTSIZE',      (3,8), (7,8), 8),
        ('BACKGROUND',    (0,8), (2,8), colors.white),
    ]
    for r, row_vals in enumerate(MATRIX):
        for c, val in enumerate(row_vals):
            trow, tcol = r + 1, c + 3
            style_cmds += [
                ('BACKGROUND', (tcol,trow), (tcol,trow), cell_bg(val)),
                ('TEXTCOLOR',  (tcol,trow), (tcol,trow), cell_tc(val)),
                ('FONTNAME',   (tcol,trow), (tcol,trow), 'Helvetica-Bold'),
                ('FONTSIZE',   (tcol,trow), (tcol,trow), 9),
            ]

    matriz_t = Table(table_data, colWidths=COLS, rowHeights=RH)
    matriz_t.setStyle(TableStyle(style_cmds))

    leg_style = ParagraphStyle('leg', fontSize=6.5, fontName='Helvetica', leading=8)
    def leg_bold(txt, color):
        return Paragraph(f'<b><font color="{color}">{txt}</font></b>',
                         ParagraphStyle('', fontSize=8, fontName='Helvetica-Bold',
                                        alignment=1, leading=10))

    leg_data = [
        ['NIVEL', 'DESCRIPCIÓN', 'PLAZO DE\nMEDIDA CORRECTIVA'],
        [leg_bold('ALTO', 'white'),
         Paragraph('Riesgo intolerable. Requiere controles inmediatos. '
                   'Si no se puede controlar el peligro, se paralizan los trabajos.', leg_style),
         leg_bold('0-24 HORAS', '#212121')],
        [leg_bold('MEDIO', '#212121'),
         Paragraph('Iniciar medidas para eliminar/reducir el riesgo. '
                   'Evaluar si la acción se puede ejecutar de manera inmediata.', leg_style),
         leg_bold('0-72 HORAS', '#212121')],
        [leg_bold('BAJO', 'white'),
         Paragraph('Este riesgo puede ser tolerable.', leg_style),
         leg_bold('1 MES', 'white')],
    ]
    leg_t = Table(leg_data, colWidths=[2.5*cm, 12*cm, 3.5*cm],
                  rowHeights=[0.55*cm, 1.0*cm, 1.0*cm, 0.7*cm])
    leg_t.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  7),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND',    (0,0), (-1,0),  NAVY),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('BACKGROUND',    (0,1), (0,1),   RED),
        ('BACKGROUND',    (0,2), (0,2),   YELLOW),
        ('BACKGROUND',    (0,3), (0,3),   GREEN),
        ('GRID',          (0,0), (-1,-1), 0.4, colors.grey),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN',         (1,1), (1,-1),  'LEFT'),
        ('LEFTPADDING',   (1,1), (1,-1),  4),
    ]))

    title_t = Table([['Riesgo = Probabilidad x Severidad']],
                    colWidths=[18*cm], rowHeights=[0.65*cm])
    title_t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (0,0), 9),
        ('ALIGN',    (0,0), (0,0), 'CENTER'),
        ('VALIGN',   (0,0), (0,0), 'MIDDLE'),
        ('BOX',      (0,0), (0,0), 1.2, NAVY),
    ]))

    return [
        Spacer(1, 0.5*cm),
        title_t,
        Paragraph('Matriz de Evaluación de Riesgo',
                  ParagraphStyle('sub', fontSize=8, fontName='Helvetica',
                                 spaceBefore=4, spaceAfter=4)),
        matriz_t,
        Spacer(1, 0.2*cm),
        leg_t,
    ]

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

    # ── MATRIZ DE RIESGO P×S ─────────────────
    for elem in _tabla_matriz_riesgo():
        elementos.append(elem)

    elementos.append(Spacer(1, 0.3*cm))

    # ── PIE DE PÁGINA ─────────────────────────
    elementos.append(Paragraph(
        f'Documento generado el {datetime.now(LIMA).strftime("%d/%m/%Y %H:%M:%S")} '
        f'· IPERC Digital · UPN Cajamarca 2026',
        ParagraphStyle('pie', fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(elementos)
    buffer.seek(0)
    return buffer