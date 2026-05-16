from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.iperc import iperc
from app.models import Area, Actividad, PeligroBase, RegistroIPERC
from app import db, solo_rol
from datetime import datetime
from app.models import Area, Actividad, PeligroBase, RegistroIPERC, FirmaDigital
import base64

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
    
    # Enviar email al supervisor
    try:
        from flask_mail import Message
        from app import mail
        from app.models import Usuario
        supervisores= Usuario.query.filter(
            Usuario.rol.in_(['supervisor', 'admin'])
        ).all()
        for sup in supervisores:
            if sup.email:
                msg=Message(subject=f'🔔 Nuevo IPERC pendiente - {registro.codigo}',
                recipients=[sup.email],
                html=f'''
                <h2 style="color:#F97316;">IPERC Digital — Nuevo registro pendiente</h2>
                <p>El trabajador <strong>{current_user.nombre} {current_user.apellido}</strong>
                ha registrado un nuevo IPERC que requiere tu aprobación.</p>
                <table border="1" cellpadding="8" style="border-collapse:collapse;">
                    <tr><td><b>Código</b></td><td>{registro.codigo}</td></tr>
                    <tr><td><b>Área</b></td><td>{registro.area.nombre}</td></tr>
                    <tr><td><b>Actividad</b></td><td>{registro.actividad.nombre}</td></tr>
                    <tr><td><b>Fecha</b></td><td>{registro.fecha_registro.strftime("%d/%m/%Y %H:%M")}</td></tr>
                    <tr><td><b>GPS</b></td><td>{"✓ Validado" if registro.geo_validado else "Sin GPS"}</td></tr>
                </table>
                <br>
                <p>Ingresa al sistema para aprobar o observar este registro.</p>
                <p style="color:#999;font-size:12px;">IPERC Digital · UPN Cajamarca 2026</p>
                ''')
                mail.send(msg)

    except Exception as e: 
        print(f"Error enviando email: {e}")   
    
    flash('✓ IPERC registrado exitosamente. Pendiente de aprobación del supervisor.')
    return redirect(url_for('iperc.firmar', registro_id=registro.id))


@iperc.route('/iperc/firmar/<int:registro_id>', methods=['GET'])
@login_required
def firmar(registro_id):
    registro = RegistroIPERC.query.get_or_404(registro_id)
    return render_template('main/firma.html', registro=registro)

@iperc.route('/iperc/guardar_firma', methods=['POST'])
@login_required
def guardar_firma():
    registro_id = request.form.get('registro_id')
    firma_data = request.form.get('firma_data')
    lat = request.form.get('lat')
    lon = request.form.get('lon')

    firma = FirmaDigital(
        registro_id=registro_id,
        usuario_id=current_user.id,
        firma_imagen=firma_data,
        lat=float(lat) if lat else None,
        lon=float(lon) if lon else None
    )
    db.session.add(firma)
    db.session.commit()
    flash('✓ Firma registrada correctamente.')
    return redirect(url_for('main.dashboard'))