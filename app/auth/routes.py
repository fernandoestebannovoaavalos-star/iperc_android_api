from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth
from app.models import Usuario, Cargo, Obra
from app import db, registrar_intento, ip_bloqueada
import bcrypt
from app import db, registrar_intento, ip_bloqueada, token_required


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        ip = request.remote_addr

        # Rate limiting
        if ip_bloqueada(ip):
            flash('⚠ Demasiados intentos fallidos. Espera 5 minutos.')
            return render_template('auth/login.html'), 429

        dni      = request.form.get('dni', '').strip()
        password = request.form.get('password', '')

        usuario = Usuario.query.filter_by(dni=dni, activo=True).first()

        if usuario and bcrypt.checkpw(password.encode('utf-8'), usuario.password_hash):
            login_user(usuario)
            # Limpiar intentos de esta IP
            from app import _intentos, _lock
            with _lock:
                _intentos[ip] = []

            # Verificar si debe cambiar clave
            if usuario.debe_cambiar_clave:
                return redirect(url_for('auth.cambiar_clave'))

            return redirect(url_for('main.dashboard'))

        # Login fallido
        registrar_intento(ip)
        flash('⚠ DNI o contraseña incorrectos.')

    return render_template('auth/login.html')


@auth.route('/auth/cambiar-clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    # Si no necesita cambiar clave, redirigir al dashboard
    if not current_user.debe_cambiar_clave:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        nueva    = request.form.get('nueva_clave', '').strip()
        confirma = request.form.get('confirmar_clave', '').strip()

        if len(nueva) < 8:
            flash('⚠ La contraseña debe tener al menos 8 caracteres.')
            return render_template('auth/cambiar_clave.html')

        if nueva != confirma:
            flash('⚠ Las contraseñas no coinciden.')
            return render_template('auth/cambiar_clave.html')

        current_user.password_hash      = bcrypt.hashpw(nueva.encode('utf-8'), bcrypt.gensalt())
        current_user.debe_cambiar_clave = False
        db.session.commit()
        flash('✓ Contraseña actualizada correctamente. Bienvenido al sistema.')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/cambiar_clave.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ─────────────────────────────────────────
# API REST para Android
# ─────────────────────────────────────────
from flask import jsonify
import jwt 
import datetime
from flask import current_app

@auth.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    ip = request.remote_addr

    # Rate limiting igual que el login web
    if ip_bloqueada(ip):
        return jsonify({'error': 'Demasiados intentos. Espera 5 minutos'}), 429

    dni      = data.get('dni', '').strip()
    password = data.get('password', '')

    usuario = Usuario.query.filter_by(dni=dni, activo=True).first()

    if usuario and bcrypt.checkpw(password.encode('utf-8'), usuario.password_hash):
        # Limpiar intentos
        from app import _intentos, _lock
        with _lock:
            _intentos[ip] = []

        # Generar token JWT
        token = jwt.encode({
            'user_id': usuario.id,
            'rol': usuario.rol,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'token': token,
            'rol': usuario.rol,
            'nombre': usuario.nombre,
            'debe_cambiar_clave': usuario.debe_cambiar_clave
        }), 200

    registrar_intento(ip)
    return jsonify({'error': 'DNI o contraseña incorrectos'}), 401

@auth.route('/api/cambiar_clave', methods=['POST'])
@token_required
def api_cambiar_clave():
    data = request.get_json()
    nueva = data.get('nueva_clave', '').strip()
    clave_actual = data.get('clave_actual', '').strip()

    # Si viene clave_actual, validarla (cambio desde perfil)
    if clave_actual:
        if not bcrypt.checkpw(clave_actual.encode('utf-8'), current_user.password_hash):
            return jsonify({'error': 'La contraseña actual es incorrecta'}), 400

    if len(nueva) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

    current_user.password_hash = bcrypt.hashpw(nueva.encode('utf-8'), bcrypt.gensalt())
    current_user.debe_cambiar_clave = False
    db.session.commit()

    return jsonify({'mensaje': 'Contraseña actualizada correctamente'}), 200