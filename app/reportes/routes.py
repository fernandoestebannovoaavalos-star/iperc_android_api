from flask import send_file, abort
from flask_login import login_required, current_user
from app.reportes import reportes
from app.models import RegistroIPERC, PeligroBase, FirmaDigital
from app.reportes.generador import generar_pdf_iperc

@reportes.route('/reportes/pdf/<int:registro_id>')
@login_required
def generar_pdf(registro_id):
    registro = RegistroIPERC.query.get_or_404(registro_id)

    # Solo el trabajador dueño o supervisor puede descargar
    if current_user.rol == 'trabajador' and registro.usuario_id != current_user.id:
        abort(403)

    # Obtener peligros de la actividad
    peligros = PeligroBase.query.filter_by(
        actividad_id=registro.actividad_id
    ).all()

    # Obtener firma si existe
    firma = FirmaDigital.query.filter_by(
        registro_id=registro_id
    ).first()

    # Generar PDF
    buffer = generar_pdf_iperc(registro, peligros, firma)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{registro.codigo}.pdf'
    )