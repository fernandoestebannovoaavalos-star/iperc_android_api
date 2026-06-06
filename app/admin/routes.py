from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import admin
from app.models import Usuario, Obra, Area, Cargo, RegistroIPERC
from app import db, solo_rol
from datetime import datetime, timedelta
import bcrypt


@admin.route('/admin/panel')
@login_required
@solo_rol('admin')
def panel():
    usuarios = Usuario.query.order_by(Usuario.created_at.desc()).all()
    obras    = Obra.query.all()
    areas    = Area.query.all()
    cargos   = Cargo.query.all()
    total_iperc      = RegistroIPERC.query.count()
    total_aprobados  = RegistroIPERC.query.filter_by(estado='aprobado').count()
    total_pendientes = RegistroIPERC.query.filter_by(estado='pendiente').count()
    return render_template('admin/panel.html',
        usuarios=usuarios, obras=obras, areas=areas, cargos=cargos,
        total_iperc=total_iperc,
        total_aprobados=total_aprobados,
        total_pendientes=total_pendientes)


# ── NUEVO: Crear usuario desde el panel admin ──────────────
@admin.route('/admin/usuario/crear', methods=['POST'])
@login_required
@solo_rol('admin')
def crear_usuario():
    nombre    = request.form.get('nombre', '').strip()
    apellido  = request.form.get('apellido', '').strip()
    dni       = request.form.get('dni', '').strip()
    email     = request.form.get('email', '').strip() or None
    rol       = request.form.get('rol', 'trabajador')
    cargo_id  = request.form.get('cargo_id') or None
    obra_id   = request.form.get('obra_id') or None
    password  = request.form.get('password', '').strip()

    if not nombre or not apellido or not dni or not password:
        flash('⚠ Nombre, apellido, DNI y contraseña son obligatorios.')
        return redirect(url_for('admin.panel'))

    if len(password) < 8:
        flash('⚠ La contraseña debe tener al menos 8 caracteres.')
        return redirect(url_for('admin.panel'))

    if Usuario.query.filter_by(dni=dni).first():
        flash(f'⚠ El DNI {dni} ya está registrado.')
        return redirect(url_for('admin.panel'))

    if email and Usuario.query.filter_by(email=email).first():
        flash('⚠ El correo ya está registrado.')
        return redirect(url_for('admin.panel'))

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        dni=dni,
        email=email,
        rol=rol,
        cargo_id=cargo_id,
        obra_id=obra_id,
        password_hash=password_hash,
        activo=True,
        debe_cambiar_clave=True   # fuerza cambio en primer login
    )
    db.session.add(usuario)
    db.session.commit()
    flash(f'✓ Usuario {nombre} {apellido} creado. Debe cambiar su contraseña al iniciar sesión.')
    return redirect(url_for('admin.panel'))


# ── NUEVO: Resetear contraseña desde admin ─────────────────
@admin.route('/admin/usuario/resetear/<int:id>', methods=['POST'])
@login_required
@solo_rol('admin')
def resetear_clave(id):
    usuario      = Usuario.query.get_or_404(id)
    nueva_clave  = request.form.get('nueva_clave', '').strip()

    if len(nueva_clave) < 8:
        flash('⚠ La contraseña debe tener al menos 8 caracteres.')
        return redirect(url_for('admin.panel'))

    usuario.password_hash    = bcrypt.hashpw(nueva_clave.encode('utf-8'), bcrypt.gensalt())
    usuario.debe_cambiar_clave = True   # fuerza nuevo cambio al iniciar sesión
    db.session.commit()
    flash(f'✓ Contraseña de {usuario.nombre} reseteada. Deberá cambiarla al iniciar sesión.')
    return redirect(url_for('admin.panel'))


@admin.route('/admin/usuario/toggle/<int:id>', methods=['POST'])
@login_required
@solo_rol('admin')
def toggle_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    usuario.activo = not usuario.activo
    db.session.commit()
    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f'✓ Usuario {usuario.nombre} {usuario.apellido} {estado}.')
    return redirect(url_for('admin.panel'))


@admin.route('/admin/usuario/rol/<int:id>', methods=['POST'])
@login_required
@solo_rol('admin')
def cambiar_rol(id):
    usuario   = Usuario.query.get_or_404(id)
    nuevo_rol = request.form.get('rol')
    if nuevo_rol in ['trabajador', 'supervisor', 'admin']:
        usuario.rol = nuevo_rol
        db.session.commit()
        flash(f'✓ Rol de {usuario.nombre} cambiado a {nuevo_rol}.')
    return redirect(url_for('admin.panel'))


@admin.route('/admin/obra/nueva', methods=['POST'])
@login_required
@solo_rol('admin')
def nueva_obra():
    nombre   = request.form.get('nombre')
    empresa  = request.form.get('empresa')
    direccion= request.form.get('direccion')
    lat      = request.form.get('lat')
    lon      = request.form.get('lon')
    radio    = request.form.get('radio', 100)
    obra = Obra(
        nombre=nombre, empresa=empresa, direccion=direccion,
        lat_centro=float(lat) if lat else None,
        lon_centro=float(lon) if lon else None,
        radio_perimetro=int(radio), activo=True)
    db.session.add(obra)
    db.session.commit()
    flash(f'✓ Obra "{nombre}" creada correctamente.')
    return redirect(url_for('admin.panel'))


@admin.route('/admin/obra/toggle/<int:id>', methods=['POST'])
@login_required
@solo_rol('admin')
def toggle_obra(id):
    obra = Obra.query.get_or_404(id)
    obra.activo = not obra.activo
    db.session.commit()
    estado = 'activada' if obra.activo else 'desactivada'
    flash(f'✓ Obra "{obra.nombre}" {estado}.')
    return redirect(url_for('admin.panel'))


@admin.route('/admin/reportes', methods=['GET', 'POST'])
@login_required
@solo_rol('admin')
def reportes():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin    = request.args.get('fecha_fin')
    area_id      = request.args.get('area_id')
    estado       = request.args.get('estado')
    usuario_id   = request.args.get('usuario_id')
    query = RegistroIPERC.query
    if fecha_inicio:
        query = query.filter(RegistroIPERC.fecha_registro >= datetime.strptime(fecha_inicio, '%Y-%m-%d'))
    if fecha_fin:
        query = query.filter(RegistroIPERC.fecha_registro <= datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1))
    if area_id:
        query = query.filter(RegistroIPERC.area_id == area_id)
    if estado:
        query = query.filter(RegistroIPERC.estado == estado)
    if usuario_id:
        query = query.filter(RegistroIPERC.usuario_id == usuario_id)
    registros = query.order_by(RegistroIPERC.fecha_registro.desc()).all()
    areas    = Area.query.all()
    usuarios = Usuario.query.filter(Usuario.rol == 'trabajador').all()
    return render_template('admin/reportes.html',
        registros=registros, areas=areas, usuarios=usuarios,
        total=len(registros), fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin, area_id=area_id, estado=estado,
        usuario_id=usuario_id)


@admin.route('/admin/estadisticas')
@login_required
@solo_rol('admin')
def estadisticas():
    from sqlalchemy import func
    por_area = db.session.query(Area.nombre, func.count(RegistroIPERC.id))\
        .join(RegistroIPERC, RegistroIPERC.area_id == Area.id)\
        .group_by(Area.nombre).all()
    por_estado = db.session.query(RegistroIPERC.estado, func.count(RegistroIPERC.id))\
        .group_by(RegistroIPERC.estado).all()
    por_trabajador = db.session.query(Usuario.nombre, Usuario.apellido, func.count(RegistroIPERC.id))\
        .join(RegistroIPERC, RegistroIPERC.usuario_id == Usuario.id)\
        .group_by(Usuario.nombre, Usuario.apellido).all()
    return render_template('admin/estadisticas.html',
        por_area=por_area, por_estado=por_estado,
        por_trabajador=por_trabajador,
        total_iperc=RegistroIPERC.query.count(),
        total_aprobados=RegistroIPERC.query.filter_by(estado='aprobado').count(),
        total_pendientes=RegistroIPERC.query.filter_by(estado='pendiente').count(),
        total_usuarios=Usuario.query.count())

# ─────────────────────────────────────────
# API REST para Android
# ─────────────────────────────────────────
from flask import jsonify
from app import token_required

@admin.route('/api/admin/usuarios', methods=['GET'])
@token_required
@solo_rol('admin')
def api_listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.created_at.desc()).all()
    return jsonify([{
        'id': u.id,
        'nombre': u.nombre,
        'apellido': u.apellido,
        'dni': u.dni,
        'rol': u.rol,
        'activo': u.activo
    } for u in usuarios]), 200

@admin.route('/api/admin/crear_usuario', methods=['POST'])
@token_required
@solo_rol('admin')
def api_crear_usuario():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    nombre   = data.get('nombre', '').strip()
    apellido = data.get('apellido', '').strip()
    dni      = data.get('dni', '').strip()
    password = data.get('password', '').strip()
    rol      = data.get('rol', 'trabajador')
    email    = data.get('email', None)

    if not nombre or not apellido or not dni or not password:
        return jsonify({'error': 'Nombre, apellido, DNI y contraseña son obligatorios'}), 400

    if len(password) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

    if Usuario.query.filter_by(dni=dni).first():
        return jsonify({'error': f'El DNI {dni} ya está registrado'}), 409

    if email and Usuario.query.filter_by(email=email).first():
        return jsonify({'error': 'El correo ya está registrado'}), 409

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        dni=dni,
        email=email,
        rol=rol,
        password_hash=password_hash,
        activo=True,
        debe_cambiar_clave=True  # ← cambiado a True
    )
    db.session.add(usuario)
    db.session.commit()
    return jsonify({'mensaje': f'Usuario {nombre} {apellido} creado. Debe cambiar su contraseña al iniciar sesión.'}), 201


@admin.route('/api/admin/toggle_usuario/<int:id>', methods=['POST'])
@token_required
@solo_rol('admin')
def api_toggle_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    usuario.activo = not usuario.activo
    db.session.commit()
    estado = 'activado' if usuario.activo else 'desactivado'
    return jsonify({'mensaje': f'Usuario {estado}', 'activo': usuario.activo}), 200

@admin.route('/api/admin/cambiar_rol/<int:id>', methods=['POST'])
@token_required
@solo_rol('admin')
def api_cambiar_rol(id):
    data = request.get_json()
    usuario = Usuario.query.get_or_404(id)
    nuevo_rol = data.get('rol')
    if nuevo_rol not in ['trabajador', 'supervisor', 'admin']:
        return jsonify({'error': 'Rol inválido'}), 400
    usuario.rol = nuevo_rol
    db.session.commit()
    return jsonify({'mensaje': f'Rol cambiado a {nuevo_rol}'}), 200