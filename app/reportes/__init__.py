from flask import Blueprint

reportes = Blueprint('reportes', __name__)

from app.reportes import routes