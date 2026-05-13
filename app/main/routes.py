from flask import render_template
from flask_login import login_required, current_user
from app import db
from app.main import main
from app.models import RegistroIPERC
from datetime import datetime, date

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    hoy = date.today()

    # Contadores reales desde BD
    iperc_hoy = RegistroIPERC.query.filter(
        RegistroIPERC.usuario_id == current_user.id,
        db.func.date(RegistroIPERC.fecha_registro) == hoy
    ).count()

    aprobados = RegistroIPERC.query.filter(
        RegistroIPERC.usuario_id == current_user.id,
        RegistroIPERC.estado == 'aprobado'
    ).count()

    pendientes = RegistroIPERC.query.filter(
        RegistroIPERC.usuario_id == current_user.id,
        RegistroIPERC.estado == 'pendiente'
    ).count()

    geo_validados = RegistroIPERC.query.filter(
        RegistroIPERC.usuario_id == current_user.id,
        RegistroIPERC.geo_validado == True
    ).count()

    # Últimos registros
    mis_registros = RegistroIPERC.query.filter_by(
        usuario_id=current_user.id
    ).order_by(RegistroIPERC.fecha_registro.desc()).limit(5).all()

    return render_template('main/dashboard.html',
        usuario=current_user,
        iperc_hoy=iperc_hoy,
        aprobados=aprobados,
        pendientes=pendientes,
        geo_validados=geo_validados,
        mis_registros=mis_registros
    )