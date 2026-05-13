from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.iperc import iperc
from app.models import Area, Actividad, PeligroBase, RegistroIPERC
from app import db, solo_rol
from datetime import datetime

@iperc.route('/iperc/nuevo')
@login_required
@solo_rol('trabajador', 'supervisor', 'admin')
def nuevo():
    areas = Area.query.all()
    return render_template('main/iperc_continuo.html', areas=areas)

@iperc.route('/iperc/get_actividades/<int:area_id>')
@login_required
def get_actividades(area_id):
    actividades = Actividad.query.filter_by(area_id=area_id).all()
    return jsonify([{'id': a.id, 'nombre': a.nombre} for a in actividades])

@iperc.route('/iperc/get_peligros/<int:actividad_id>')
@login_required
def get_peligros(actividad_id):
    peligros = PeligroBase.query.filter_by(actividad_id=actividad_id).all()
    return jsonify([{
        'id': p.id,
        'descripcion': p.descripcion,
        'riesgo': p.riesgo_consecuencia,
        'tipo': p.tipo_peligro_id,
        'p_sin': p.p_sin,
        's_sin': p.s_sin,
        'nivel_sin': p.nivel_sin,
        'medidas': p.medidas_control,
        'p_con': p.p_con,
        's_con': p.s_con,
        'nivel_con': p.nivel_con
    } for p in peligros])

@iperc.route('/iperc/guardar', methods=['POST'])
@login_required
@solo_rol('trabajador', 'supervisor', 'admin')
def guardar():
    area_id = request.form.get('area_id')
    actividad_id = request.form.get('actividad_id')
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    geo_validado = request.form.get('geo_validado') == '1'

    codigo = f"IPERC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"

    registro = RegistroIPERC(
        codigo=codigo,
        usuario_id=current_user.id,
        area_id=area_id,
        actividad_id=actividad_id,
        lat=float(lat) if lat else None,
        lon=float(lon) if lon else None,
        geo_validado=geo_validado,
        estado='pendiente',
        fecha_registro=datetime.utcnow()
    )
    db.session.add(registro)
    db.session.commit()
    flash('✓ IPERC registrado exitosamente. Pendiente de aprobación del supervisor.')
    return redirect(url_for('main.dashboard'))