from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.supervisor import supervisor
from app.models import RegistroIPERC, FirmaDigital
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

    # ── Guardar firma del supervisor ──────────────────────────────
    firma_data = request.form.get('firma_supervisor', '').strip()
    if firma_data and firma_data.startswith('data:image'):
        # Eliminar firma anterior del supervisor si ya existía
        FirmaDigital.query.filter_by(
            registro_id=id, tipo='supervisor'
        ).delete()
        firma_sup = FirmaDigital(
            registro_id  = id,
            usuario_id   = current_user.id,
            firma_imagen = firma_data,
            tipo         = 'supervisor',
            lat          = registro.lat,
            lon          = registro.lon,
        )
        db.session.add(firma_sup)

    registro.estado       = 'aprobado'
    registro.supervisor_id = current_user.id
    db.session.commit()
    flash(f'✓ IPERC {registro.codigo} aprobado y firmado correctamente.')
    return redirect(url_for('supervisor.panel'))

@supervisor.route('/supervisor/observar/<int:id>', methods=['POST'])
@login_required
@solo_rol('supervisor', 'admin')
def observar(id):
    registro = RegistroIPERC.query.get_or_404(id)
    registro.estado        = 'observado'
    registro.supervisor_id = current_user.id
    db.session.commit()
    flash(f'⚠ IPERC {registro.codigo} marcado como observado.')
    return redirect(url_for('supervisor.panel'))

@supervisor.route('/supervisor/detalle/<int:id>')
@login_required
@solo_rol('supervisor', 'admin')
def detalle(id):
    from app.models import PeligroBase, PeligroAdicional
    registro         = RegistroIPERC.query.get_or_404(id)
    peligros         = PeligroBase.query.filter_by(actividad_id=registro.actividad_id).all()
    adicionales      = PeligroAdicional.query.filter_by(registro_id=id).all()
    firma_trabajador = FirmaDigital.query.filter_by(
                           registro_id=id, tipo='trabajador').first()
    firma_supervisor = FirmaDigital.query.filter_by(
                           registro_id=id, tipo='supervisor').first()
    return render_template('supervisor/detalle.html',
        registro         = registro,
        peligros         = peligros,
        adicionales      = adicionales,
        firma            = firma_trabajador,   # retrocompatibilidad
        firma_trabajador = firma_trabajador,
        firma_supervisor = firma_supervisor,
    )