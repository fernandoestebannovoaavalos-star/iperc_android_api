from flask import send_file, abort
from flask_login import login_required, current_user
from app.reportes import reportes
from app.models import RegistroIPERC, PeligroBase, FirmaDigital, PeligroAdicional
from app.reportes.generador import generar_pdf_iperc

@reportes.route('/reportes/pdf/<int:registro_id>')
@login_required
def generar_pdf(registro_id):
    registro = RegistroIPERC.query.get_or_404(registro_id)

    if current_user.rol == 'trabajador' and registro.usuario_id != current_user.id:
        abort(403)

    peligros    = PeligroBase.query.filter_by(actividad_id=registro.actividad_id).all()
    firma       = FirmaDigital.query.filter_by(registro_id=registro_id).first()
    adicionales = PeligroAdicional.query.filter_by(registro_id=registro_id).all()

    buffer = generar_pdf_iperc(registro, peligros, firma,
                               peligros_adicionales=adicionales)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{registro.codigo}.pdf'
    )