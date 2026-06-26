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


# ── API REPORTES FILTRADOS ─────────────────────────────────────────────────────

@reportes.route('/api/reportes', methods=['GET'])
@token_required
def api_reportes():
    """
    Parámetros opcionales:
      - estado: pendiente | aprobado | observado
      - fecha_inicio: YYYY-MM-DD
      - fecha_fin:    YYYY-MM-DD
      - obra_id:      int
    """
    estado      = request.args.get('estado', '')
    fecha_ini   = request.args.get('fecha_inicio', '')
    fecha_fin   = request.args.get('fecha_fin', '')
    obra_id     = request.args.get('obra_id', '')

    query = RegistroIPERC.query

    # Filtro por rol: trabajador solo ve los suyos
    if current_user.rol == 'trabajador':
        query = query.filter_by(usuario_id=current_user.id)

    if estado:
        query = query.filter_by(estado=estado)

    if obra_id:
        try:
            query = query.filter_by(obra_id=int(obra_id))
        except ValueError:
            pass

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
            'id':          r.id,
            'codigo':      r.codigo,
            'trabajador':  r.usuario.nombre + ' ' + r.usuario.apellido,
            'area':        r.area.nombre if r.area else '',
            'actividad':   r.actividad.nombre if r.actividad else '',
            'estado':      r.estado,
            'nivel_riesgo': r.nivel_riesgo or '',
            'fecha':       r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else '',
            'obra':        r.obra.nombre if r.obra else '',
        })

    return jsonify(resultado)


@reportes.route('/api/estadisticas', methods=['GET'])
@token_required
def api_estadisticas():
    """Datos para gráficos del dashboard de estadísticas."""
    from sqlalchemy import func
    from app.models import Usuario

    # 1. Registros por estado
    por_estado = db.session.query(
        RegistroIPERC.estado,
        func.count(RegistroIPERC.id)
    ).group_by(RegistroIPERC.estado).all()

    # 2. Registros por nivel de riesgo
    por_nivel = db.session.query(
        RegistroIPERC.nivel_riesgo,
        func.count(RegistroIPERC.id)
    ).group_by(RegistroIPERC.nivel_riesgo).all()

    # 3. Últimos 7 días — registros por día
    from datetime import timedelta
    hoy = datetime.utcnow().date()
    por_dia = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        count = RegistroIPERC.query.filter(
            func.date(RegistroIPERC.fecha_registro) == dia
        ).count()
        por_dia.append({'dia': dia.strftime('%d/%m'), 'total': count})

    # 4. Total general
    total = RegistroIPERC.query.count()

    return jsonify({
        'total': total,
        'por_estado': [{'estado': e, 'total': c} for e, c in por_estado],
        'por_nivel':  [{'nivel': n or 'Sin nivel', 'total': c} for n, c in por_nivel],
        'por_dia':    por_dia,
    })