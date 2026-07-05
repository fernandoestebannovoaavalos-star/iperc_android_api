from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.iperc import iperc
from app.models import Area, Actividad, PeligroBase, RegistroIPERC, FirmaDigital, PeligroAdicional
from datetime import datetime, timezone, timedelta
import base64
from app import db, solo_rol, token_required
# Zona horaria Lima / Cajamarca (UTC-5)
LIMA = timezone(timedelta(hours=-5))

def _calcular_nivel(p, s):
    MATRIZ = {
        (1,1):'MUY BAJO', (1,2):'MUY BAJO', (1,3):'BAJO',    (1,4):'MEDIO',   (1,5):'MEDIO',
        (2,1):'MUY BAJO', (2,2):'BAJO',     (2,3):'MEDIO',   (2,4):'MEDIO',   (2,5):'ALTO',
        (3,1):'BAJO',     (3,2):'MEDIO',    (3,3):'MEDIO',   (3,4):'ALTO',    (3,5):'MUY ALTO',
        (4,1):'MEDIO',    (4,2):'MEDIO',    (4,3):'ALTO',    (4,4):'MUY ALTO',(4,5):'EXTREMO',
        (5,1):'MEDIO',    (5,2):'ALTO',     (5,3):'MUY ALTO',(5,4):'EXTREMO', (5,5):'EXTREMO',
    }
    return MATRIZ.get((int(p), int(s)), 'MEDIO')


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
    area_id      = request.form.get('area_id')
    actividad_id = request.form.get('actividad_id')
    lat          = request.form.get('lat')
    lon          = request.form.get('lon')
    geo_validado = request.form.get('geo_validado') == '1'

    # FIX: código generado con hora Lima
    ahora_lima = datetime.now(LIMA)
    codigo = f"IPERC-{ahora_lima.strftime('%Y%m%d%H%M%S')}-{current_user.id}"

    # FIX: fecha_registro eliminada → el modelo usa _ahora_lima() automáticamente
    registro = RegistroIPERC(
        codigo=codigo,
        usuario_id=current_user.id,
        area_id=area_id,
        actividad_id=actividad_id,
        lat=float(lat) if lat else None,
        lon=float(lon) if lon else None,
        geo_validado=geo_validado,
        estado='pendiente',
    )
    db.session.add(registro)
    db.session.commit()

    # Guardar peligros adicionales
    total_adicionales = int(request.form.get('total_adicionales', 0))
    for i in range(1, total_adicionales + 1):
        tipo        = request.form.get(f'adic_tipo_{i}')
        descripcion = request.form.get(f'adic_descripcion_{i}')
        riesgo      = request.form.get(f'adic_riesgo_{i}')
        p           = int(request.form.get(f'adic_p_{i}', 1))
        s           = int(request.form.get(f'adic_s_{i}', 1))
        medidas     = request.form.get(f'adic_medidas_{i}')
        pxs         = p * s

        if   pxs <= 4:  nivel = 'TRIVIAL'
        elif pxs <= 8:  nivel = 'TOLERABLE'
        elif pxs <= 16: nivel = 'MODERADO'
        elif pxs <= 24: nivel = 'IMPORTANTE'
        else:           nivel = 'INTOLERABLE'

        if tipo and descripcion:
            peligro_adic = PeligroAdicional(
                registro_id=registro.id,
                tipo=tipo,
                descripcion=descripcion,
                riesgo_consecuencia=riesgo,
                p_sin=p,  s_sin=s,  nivel_sin=nivel,
                medidas_control=medidas,
                p_con=p,  s_con=s,  nivel_con=nivel,
            )
            db.session.add(peligro_adic)
    db.session.commit()

    # Notificación por email al supervisor
    try:
        from flask_mail import Message
        from app import mail
        from app.models import Usuario
        supervisores = Usuario.query.filter(
            Usuario.rol.in_(['supervisor', 'admin'])
        ).all()
        for sup in supervisores:
            if sup.email:
                msg = Message(
                    subject=f'🔔 Nuevo IPERC pendiente - {registro.codigo}',
                    recipients=[sup.email],
                    html=f'''
                    <h2 style="color:#F97316;">IPERC Digital — Nuevo registro pendiente</h2>
                    <p>El trabajador <strong>{current_user.nombre} {current_user.apellido}</strong>
                    ha registrado un nuevo IPERC que requiere tu aprobación.</p>
                    <table border="1" cellpadding="8" style="border-collapse:collapse;">
                        <tr><td><b>Código</b></td><td>{registro.codigo}</td></tr>
                        <tr><td><b>Área</b></td><td>{registro.area.nombre}</td></tr>
                        <tr><td><b>Actividad</b></td><td>{registro.actividad.nombre}</td></tr>
                        <tr><td><b>Fecha</b></td>
                            <td>{ahora_lima.strftime("%d/%m/%Y %H:%M")}</td></tr>
                        <tr><td><b>GPS</b></td>
                            <td>{"✓ Validado" if registro.geo_validado else "Sin GPS"}</td></tr>
                    </table>
                    <br>
                    <p>Ingresa al sistema para aprobar o observar este registro.</p>
                    <p style="color:#999;font-size:12px;">IPERC Digital · UPN Cajamarca 2026</p>
                    '''
                )
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
    firma_data  = request.form.get('firma_data')
    lat         = request.form.get('lat')
    lon         = request.form.get('lon')

    firma = FirmaDigital(
        registro_id=registro_id,
        usuario_id=current_user.id,
        firma_imagen=firma_data,
        lat=float(lat) if lat else None,
        lon=float(lon) if lon else None,
        # timestamp → usa _ahora_lima() del modelo automáticamente
    )
    db.session.add(firma)
    db.session.commit()

    flash('✓ Firma registrada correctamente.')
    return redirect(url_for('main.dashboard'))

# ─────────────────────────────────────────
# API REST para Android
# ─────────────────────────────────────────

@iperc.route('/api/areas', methods=['GET'])
@token_required
def api_areas():
    areas = Area.query.all()
    return jsonify([{'id': a.id, 'nombre': a.nombre} for a in areas])


@iperc.route('/api/iperc/guardar', methods=['POST'])
@token_required
@solo_rol('trabajador', 'supervisor', 'admin')
def api_guardar():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    area_id      = data.get('area_id')
    actividad_id = data.get('actividad_id')
    lat          = data.get('lat')
    lon          = data.get('lon')
    geo_validado = data.get('geo_validado', False)
    peligros     = data.get('peligros', [])
    adicionales  = data.get('adicionales', [])

    ahora_lima = datetime.now(LIMA)
    codigo = f"IPERC-{ahora_lima.strftime('%Y%m%d%H%M%S')}-{current_user.id}"

    registro = RegistroIPERC(
        codigo=codigo,
        usuario_id=current_user.id,
        area_id=area_id,
        actividad_id=actividad_id,
        lat=float(lat) if lat else None,
        lon=float(lon) if lon else None,
        geo_validado=geo_validado,
        estado='pendiente',
    )
    db.session.add(registro)
    db.session.flush()  # obtiene registro.id sin hacer commit

    # ── Guardar peligros base seleccionados ───────────────────────────
    for item in peligros:
        peligro_id = item.get('peligro_id')
        p = int(item.get('p', 1))
        s = int(item.get('s', 1))
        nivel = _calcular_nivel(p, s)
        if peligro_id:
            from app.models import RegistroPeligro
            rp = RegistroPeligro(
                registro_id=registro.id,
                peligro_base_id=int(peligro_id),
                p_sin=p, s_sin=s, nivel_sin=nivel,
                p_con=p, s_con=s, nivel_con=nivel
            )
            db.session.add(rp)

    # ── Guardar peligros adicionales ──────────────────────────────────
    for item in adicionales:
        p   = int(item.get('p', 1))
        s   = int(item.get('s', 1))
        nivel = _calcular_nivel(p, s)

        peligro_adic = PeligroAdicional(
            registro_id=registro.id,
            tipo=item.get('tipo'),
            descripcion=item.get('descripcion'),
            riesgo_consecuencia=item.get('riesgo'),
            p_sin=p, s_sin=s, nivel_sin=nivel,
            medidas_control=item.get('medidas'),
            p_con=p, s_con=s, nivel_con=nivel,
        )
        db.session.add(peligro_adic)

    db.session.commit()

    return jsonify({
        'mensaje': 'IPERC registrado exitosamente',
        'registro_id': registro.id,
        'codigo': registro.codigo
    }), 201

@iperc.route('/api/iperc/firma', methods=['POST'])
@token_required
def api_guardar_firma():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    firma = FirmaDigital(
        registro_id=data.get('registro_id'),
        usuario_id=current_user.id,
        firma_imagen=data.get('firma_base64'),  # ← cambio: firma_data → firma_base64
        lat=float(data.get('lat')) if data.get('lat') else None,
        lon=float(data.get('lon')) if data.get('lon') else None,
    )
    db.session.add(firma)
    db.session.commit()

    return jsonify({'mensaje': 'Firma registrada correctamente'}), 200

@iperc.route('/api/iperc/lista', methods=['GET'])
@token_required
def api_lista():
    if current_user.rol in ['supervisor', 'admin']:
        registros = RegistroIPERC.query.order_by(
            RegistroIPERC.id.desc()).limit(50).all()
    else:
        registros = RegistroIPERC.query.filter_by(
            usuario_id=current_user.id).order_by(
            RegistroIPERC.id.desc()).limit(50).all()

    return jsonify([{
        'id': r.id,
        'codigo': r.codigo,
        'area': r.area.nombre if r.area else '',
        'actividad': r.actividad.nombre if r.actividad else '',
        'estado': r.estado,
        'geo_validado': r.geo_validado,
        'fecha': r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else '',
        'observacion': r.observacion or '',
    } for r in registros]), 200


@iperc.route('/api/actividades/<int:area_id>', methods=['GET'])
@token_required
def api_actividades(area_id):
    actividades = Actividad.query.filter_by(area_id=area_id).all()
    return jsonify([{'id': a.id, 'nombre': a.nombre} for a in actividades])

@iperc.route('/api/peligros/<int:actividad_id>', methods=['GET'])
@token_required
def api_peligros(actividad_id):
    peligros = PeligroBase.query.filter_by(actividad_id=actividad_id).all()
    return jsonify([{
        'id': p.id,
        'descripcion': p.descripcion,
        'riesgo': p.riesgo_consecuencia,
        'p_sin': p.p_sin,
        's_sin': p.s_sin,
        'nivel_sin': p.nivel_sin,
        'medidas': p.medidas_control,
        'p_con': p.p_con,
        's_con': p.s_con,
        'nivel_con': p.nivel_con
    } for p in peligros])


@iperc.route('/api/iperc/detalle/<int:id>', methods=['GET'])
@token_required
def api_detalle(id):
    from app.models import RegistroPeligro, PeligroAdicional, Usuario
    r = RegistroIPERC.query.get_or_404(id)
    adicionales = PeligroAdicional.query.filter_by(registro_id=id).all()
    registros_peligros = RegistroPeligro.query.filter_by(registro_id=id).all()
    u = Usuario.query.get(r.usuario_id)

    # Si hay peligros guardados en registros_peligros úsalos
    # si no, carga los peligros base por actividad (compatibilidad)
    if registros_peligros:
        peligros_data = [{
            'descripcion': rp.peligro_base.descripcion,
            'riesgo': rp.peligro_base.riesgo_consecuencia,
            'nivel_sin': rp.nivel_sin,
            'medidas': rp.peligro_base.medidas_control,
            'nivel_con': rp.peligro_base.nivel_con
        } for rp in registros_peligros]
    else:
        peligros_base = PeligroBase.query.filter_by(
            actividad_id=r.actividad_id).all()
        peligros_data = [{
            'descripcion': p.descripcion,
            'riesgo': p.riesgo_consecuencia,
            'nivel_sin': p.nivel_sin,
            'medidas': p.medidas_control,
            'nivel_con': p.nivel_con
        } for p in peligros_base]

    return jsonify({
        'id': r.id,
        'codigo': r.codigo,
        'trabajador': f"{u.nombre} {u.apellido}" if u else '—',
        'area': r.area.nombre if r.area else '',
        'actividad': r.actividad.nombre if r.actividad else '',
        'estado': r.estado,
        'fecha': r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else '',
        'geo_validado': r.geo_validado,
        'peligros': peligros_data,
        'adicionales': [{
            'descripcion': p.descripcion,
            'riesgo': p.riesgo_consecuencia,
            'nivel_sin': p.nivel_sin,
            'medidas': p.medidas_control,
            'nivel_con': p.nivel_con
        } for p in adicionales]
    }), 200

@iperc.route('/api/supervisor/pendientes', methods=['GET'])
@token_required
def supervisor_pendientes():
    from app.models import Usuario
    registros = RegistroIPERC.query.filter_by(estado='pendiente').order_by(
        RegistroIPERC.id.desc()).all()
    resultado = []
    for r in registros:
        u = Usuario.query.get(r.usuario_id)
        resultado.append({
            'id': r.id,
            'trabajador': f"{u.nombre} {u.apellido}" if u else '—',
            'area': r.area.nombre if r.area else '',
            'actividad': r.actividad.nombre if r.actividad else '',
            'estado': r.estado,
            'fecha': r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else ''
        })
    return jsonify(resultado), 200

@iperc.route('/api/supervisor/todos', methods=['GET'])
@token_required
def supervisor_todos():
    from app.models import Usuario
    registros = RegistroIPERC.query.order_by(
        RegistroIPERC.id.desc()).limit(50).all()
    resultado = []
    for r in registros:
        u = Usuario.query.get(r.usuario_id)
        resultado.append({
            'id': r.id,
            'trabajador': f"{u.nombre} {u.apellido}" if u else '—',
            'area': r.area.nombre if r.area else '',
            'actividad': r.actividad.nombre if r.actividad else '',
            'estado': r.estado,
            'fecha': r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else ''
        })
    return jsonify(resultado), 200

@iperc.route('/api/supervisor/aprobar/<int:id>', methods=['POST'])
@token_required
def supervisor_aprobar(id):
    r = RegistroIPERC.query.get_or_404(id)
    if r.estado != 'pendiente':
        return jsonify({'error': 'Registro ya procesado'}), 400
    r.estado = 'aprobado'
    db.session.commit()
    return jsonify({'mensaje': 'Aprobado'}), 200

@iperc.route('/api/supervisor/observar/<int:id>', methods=['POST'])
@token_required
def supervisor_observar(id):
    data = request.get_json()
    r = RegistroIPERC.query.get_or_404(id)
    if r.estado != 'pendiente':
        return jsonify({'error': 'Registro ya procesado'}), 400
    r.estado = 'observado'
    r.observacion = data.get('observacion', '')
    db.session.commit()
    return jsonify({'mensaje': 'Observación guardada'}), 200


@iperc.route('/api/supervisor/aprobar_con_firma/<int:id>', methods=['POST'])
@token_required
def supervisor_aprobar_con_firma(id):
    data = request.get_json()
    r = RegistroIPERC.query.get_or_404(id)
    if r.estado != 'pendiente':
        return jsonify({'error': 'Registro ya procesado'}), 400

    firma_base64 = data.get('firma_base64')
    if firma_base64:
        FirmaDigital.query.filter_by(registro_id=id, tipo='supervisor').delete()
        firma = FirmaDigital(
            registro_id=id,
            usuario_id=current_user.id,
            firma_imagen=firma_base64,
            tipo='supervisor',
            lat=r.lat,
            lon=r.lon
        )
        db.session.add(firma)

    r.estado = 'aprobado'
    r.supervisor_id = current_user.id  # ← agrega esta línea

    # Notificación por email al trabajador
    try:
        from flask_mail import Message
        from app import mail
        from app.models import Usuario
        trabajador = Usuario.query.get(r.usuario_id)
        if trabajador and trabajador.email:
            msg = Message(
                subject=f'✅ IPERC {r.codigo} aprobado',
                recipients=[trabajador.email],
                html=f'''
                <h2 style="color:#16a34a;">IPERC Digital — Registro Aprobado</h2>
                <p>Tu registro IPERC ha sido revisado y aprobado por el supervisor.</p>
                <table border="1" cellpadding="8" style="border-collapse:collapse;">
                    <tr><td><b>Código</b></td><td>{r.codigo}</td></tr>
                    <tr><td><b>Área</b></td><td>{r.area.nombre}</td></tr>
                    <tr><td><b>Actividad</b></td><td>{r.actividad.nombre}</td></tr>
                    <tr><td><b>Supervisor</b></td><td>{current_user.nombre} {current_user.apellido}</td></tr>
                </table>
                <p style="color:#999;font-size:12px;">IPERC Digital · UPN Cajamarca 2026</p>
                '''
            )
            mail.send(msg)
    except Exception as e:
        print(f"Error enviando email: {e}")

    db.session.commit()
    return jsonify({'mensaje': 'IPERC aprobado con firma del supervisor'}), 200


@iperc.route('/api/iperc/pdf/<int:id>', methods=['GET'])
@token_required
def api_pdf(id):
    from app.models import PeligroBase, PeligroAdicional, FirmaDigital
    from app.reportes.generador import generar_pdf_iperc
    from flask import send_file

    r = RegistroIPERC.query.get_or_404(id)

    peligros         = PeligroBase.query.filter_by(actividad_id=r.actividad_id).all()
    adicionales      = PeligroAdicional.query.filter_by(registro_id=id).all()
    firma_trabajador = FirmaDigital.query.filter_by(
                           registro_id=id, tipo='trabajador').first()
    firma_supervisor = FirmaDigital.query.filter_by(
                           registro_id=id, tipo='supervisor').first()

    buffer = generar_pdf_iperc(
        r, peligros, firma_trabajador,
        peligros_adicionales=adicionales,
        firma_supervisor=firma_supervisor
    )

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'{r.codigo}.pdf'
    )

@iperc.route('/api/iperc/adicionales', methods=['POST'])
@token_required
def api_guardar_adicionales():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    registro_id = data.get('registro_id')
    peligros    = data.get('peligros', [])
    adicionales = data.get('adicionales', [])

    # ── Guardar peligros base seleccionados ───────────────────────────
    for item in peligros:
        peligro_id = item.get('peligro_id')
        p = int(item.get('p', 1))
        s = int(item.get('s', 1))
        nivel = _calcular_nivel(p, s)
        if peligro_id:
            from app.models import RegistroPeligro
            rp = RegistroPeligro(
                registro_id=registro_id,
                peligro_base_id=int(peligro_id),
                p_sin=p, s_sin=s, nivel_sin=nivel,
            )
            db.session.add(rp)

    # ── Guardar peligros adicionales ──────────────────────────────────
    for item in adicionales:
        p   = int(item.get('p', 1))
        s   = int(item.get('s', 1))
        nivel = _calcular_nivel(p, s)

        peligro_adic = PeligroAdicional(
            registro_id=registro_id,
            tipo=item.get('tipo'),
            descripcion=item.get('descripcion'),
            riesgo_consecuencia=item.get('riesgo'),
            p_sin=p, s_sin=s, nivel_sin=nivel,
            medidas_control=item.get('medidas'),
            p_con=p, s_con=s, nivel_con=nivel,
        )
        db.session.add(peligro_adic)

    db.session.commit()
    return jsonify({'mensaje': 'Peligros guardados correctamente'}), 201