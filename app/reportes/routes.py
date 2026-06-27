from flask import send_file, abort, jsonify, request
from flask_login import login_required, current_user
from app.reportes import reportes
from app.models import RegistroIPERC, PeligroBase, FirmaDigital, PeligroAdicional
from app.reportes.generador import generar_pdf_iperc
from app import db, token_required
from datetime import datetime


@reportes.route('/reportes/pdf/<int:registro_id>')
@login_required
def generar_pdf(registro_id):
    registro = RegistroIPERC.query.get_or_404(registro_id)
    if current_user.rol == 'trabajador' and registro.usuario_id != current_user.id:
        abort(403)

    peligros         = PeligroBase.query.filter_by(actividad_id=registro.actividad_id).all()
    adicionales      = PeligroAdicional.query.filter_by(registro_id=registro_id).all()
    firma_trabajador = FirmaDigital.query.filter_by(
                           registro_id=registro_id, tipo='trabajador').first()
    firma_supervisor = FirmaDigital.query.filter_by(
                           registro_id=registro_id, tipo='supervisor').first()

    buffer = generar_pdf_iperc(
        registro, peligros, firma_trabajador,
        peligros_adicionales = adicionales,
        firma_supervisor     = firma_supervisor
    )
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'{registro.codigo}.pdf')


# ── API REPORTES FILTRADOS ────────────────────────────────────────────────────

@reportes.route('/api/reportes', methods=['GET'])
@token_required
def api_reportes():
    estado    = request.args.get('estado', '')
    fecha_ini = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')

    query = RegistroIPERC.query

    if current_user.rol == 'trabajador':
        query = query.filter_by(usuario_id=current_user.id)

    if estado:
        query = query.filter_by(estado=estado)

    if fecha_ini:
        try:
            fi = datetime.strptime(fecha_ini, '%Y-%m-%d')
            query = query.filter(RegistroIPERC.fecha_registro >= fi)
        except ValueError:
            pass

    if fecha_fin:
        try:
            ff = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(RegistroIPERC.fecha_registro <= ff)
        except ValueError:
            pass

    registros = query.order_by(RegistroIPERC.fecha_registro.desc()).all()

    resultado = []
    for r in registros:
        resultado.append({
            'id':         r.id,
            'codigo':     r.codigo,
            'trabajador': r.registrado_por.nombre + ' ' + r.registrado_por.apellido,
            'area':       r.area.nombre if r.area else '',
            'actividad':  r.actividad.nombre if r.actividad else '',
            'estado':     r.estado,
            'fecha':      r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else '',
            'observacion': r.observacion or '',
        })

    return jsonify(resultado)


# ── API ESTADÍSTICAS ──────────────────────────────────────────────────────────

@reportes.route('/api/estadisticas', methods=['GET'])
@token_required
def api_estadisticas():
    from sqlalchemy import func
    from datetime import timedelta

    # 1. Registros por estado
    por_estado = db.session.query(
        RegistroIPERC.estado,
        func.count(RegistroIPERC.id)
    ).group_by(RegistroIPERC.estado).all()

    # 2. Registros por área
    from app.models import Area
    por_area = db.session.query(
        Area.nombre,
        func.count(RegistroIPERC.id)
    ).join(RegistroIPERC, RegistroIPERC.area_id == Area.id)\
     .group_by(Area.nombre).all()

    # 3. Últimos 7 días
    hoy = datetime.utcnow().date()
    por_dia = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        count = RegistroIPERC.query.filter(
            func.date(RegistroIPERC.fecha_registro) == dia
        ).count()
        por_dia.append({'dia': dia.strftime('%d/%m'), 'total': count})

    # 4. Totales
    total      = RegistroIPERC.query.count()
    aprobados  = RegistroIPERC.query.filter_by(estado='aprobado').count()
    pendientes = RegistroIPERC.query.filter_by(estado='pendiente').count()
    observados = RegistroIPERC.query.filter_by(estado='observado').count()

    return jsonify({
        'total':      total,
        'aprobados':  aprobados,
        'pendientes': pendientes,
        'observados': observados,
        'por_estado': [{'estado': e, 'total': c} for e, c in por_estado],
        'por_area':   [{'area': a, 'total': c} for a, c in por_area],
        'por_dia':    por_dia,
    })