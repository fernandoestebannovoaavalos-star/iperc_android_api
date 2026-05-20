from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.supervisor import supervisor
from app.models import RegistroIPERC, Usuario
from app import db, solo_rol

@supervisor.route('/supervisor/panel')
@login_required
@solo_rol('supervisor', 'admin')
def panel():
    pendientes = RegistroIPERC.query.filter_by(
        estado='pendiente'
    ).order_by(RegistroIPERC.fecha_registro.desc()).all()

    aprobados = RegistroIPERC.query.filter_by(
        estado='aprobado'
    ).order_by(RegistroIPERC.fecha_registro.desc()).limit(10).all()

    return render_template('supervisor/panel.html',
        pendientes=pendientes,
        aprobados=aprobados
    )

@supervisor.route('/supervisor/aprobar/<int:id>', methods=['POST'])
@login_required
@solo_rol('supervisor', 'admin')
def aprobar(id):
    registro = RegistroIPERC.query.get_or_404(id)
    registro.estado = 'aprobado'
    registro.supervisor_id = current_user.id
    db.session.commit()
    flash(f'✓ IPERC {registro.codigo} aprobado correctamente.')
    return redirect(url_for('supervisor.panel'))

@supervisor.route('/supervisor/observar/<int:id>', methods=['POST'])
@login_required
@solo_rol('supervisor', 'admin')
def observar(id):
    registro = RegistroIPERC.query.get_or_404(id)
    registro.estado = 'observado'
    registro.supervisor_id = current_user.id
    db.session.commit()
    flash(f'⚠ IPERC {registro.codigo} marcado como observado.')
    return redirect(url_for('supervisor.panel'))

@supervisor.route('/supervisor/detalle/<int:id>')
@login_required
@solo_rol('supervisor', 'admin')
def detalle(id):
    from app.models import PeligroBase, FirmaDigital, PeligroAdicional
    registro    = RegistroIPERC.query.get_or_404(id)
    peligros    = PeligroBase.query.filter_by(actividad_id=registro.actividad_id).all()
    adicionales = PeligroAdicional.query.filter_by(registro_id=id).all()
    firma       = FirmaDigital.query.filter_by(registro_id=id).first()
    return render_template('supervisor/detalle.html',
        registro=registro,
        peligros=peligros,
        adicionales=adicionales,
        firma=firma
    )