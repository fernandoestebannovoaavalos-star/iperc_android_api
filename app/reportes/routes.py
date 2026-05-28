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

    peligros         = PeligroBase.query.filter_by(actividad_id=registro.actividad_id).all()
    adicionales      = PeligroAdicional.query.filter_by(registro_id=registro_id).all()
    firma_trabajador = FirmaDigital.query.filter_by(
                           registro_id=registro_id, tipo='trabajador').first()
    firma_supervisor = FirmaDigital.query.filter_by(
                           registro_id=registro_id, tipo='supervisor').first()

    buffer = generar_pdf_iperc(
        registro, peligros, firma_trabajador,
        peligros_adicionales = adicionales,
        firma_supervisor     = firma_supervisor
    )
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'{registro.codigo}.pdf')