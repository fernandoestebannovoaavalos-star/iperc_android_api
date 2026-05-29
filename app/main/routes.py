from flask import render_template, redirect, url_for, flash
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

    mis_registros = RegistroIPERC.query.filter_by(
        usuario_id=current_user.id,
        archivado=False                              # ← solo activos en dashboard
    ).order_by(RegistroIPERC.fecha_registro.desc()).limit(5).all()

    return render_template('main/dashboard.html',
        usuario=current_user,
        iperc_hoy=iperc_hoy,
        aprobados=aprobados,
        pendientes=pendientes,
        geo_validados=geo_validados,
        mis_registros=mis_registros
    )

@main.route('/mis-registros')
@login_required
def mis_registros():
    registros = RegistroIPERC.query.filter_by(
        usuario_id=current_user.id,
        archivado=False                              # ← solo activos
    ).order_by(RegistroIPERC.fecha_registro.desc()).all()

    archivados = RegistroIPERC.query.filter_by(
        usuario_id=current_user.id,
        archivado=True
    ).order_by(RegistroIPERC.fecha_registro.desc()).all()

    return render_template('main/mis_registros.html',
        registros=registros,
        archivados=archivados
    )

@main.route('/archivar/<int:id>', methods=['POST'])
@login_required
def archivar(id):
    registro = RegistroIPERC.query.get_or_404(id)
    # Solo el dueño puede archivar
    if registro.usuario_id != current_user.id:
        flash('No tienes permiso para archivar este registro.')
        return redirect(url_for('main.mis_registros'))
    registro.archivado = True
    db.session.commit()
    flash(f'Registro {registro.codigo} archivado correctamente.')
    return redirect(url_for('main.mis_registros'))

@main.route('/desarchivar/<int:id>', methods=['POST'])
@login_required
def desarchivar(id):
    registro = RegistroIPERC.query.get_or_404(id)
    if registro.usuario_id != current_user.id:
        flash('No tienes permiso para desarchivar este registro.')
        return redirect(url_for('main.mis_registros'))
    registro.archivado = False
    db.session.commit()
    flash(f'Registro {registro.codigo} restaurado correctamente.')
    return redirect(url_for('main.mis_registros'))