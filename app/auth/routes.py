from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.auth import auth
from app.models import Usuario
from app import db
import bcrypt

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni')
        password = request.form.get('password')
        usuario = Usuario.query.filter_by(dni=dni).first()
        if usuario and bcrypt.checkpw(password.encode('utf-8'), usuario.password_hash):
            login_user(usuario)
            return redirect(url_for('main.dashboard'))
        flash('DNI o contraseña incorrectos')
    return render_template('auth/login.html')

@auth.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        dni = request.form.get('dni')
        cargo = request.form.get('cargo')
        password = request.form.get('password')
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            cargo=cargo,
            password_hash=password_hash,
            rol='trabajador'
        )
        db.session.add(usuario)
        db.session.commit()
        flash('Registro exitoso. Inicia sesión.')
        return redirect(url_for('auth.login'))
    return render_template('auth/registro.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))