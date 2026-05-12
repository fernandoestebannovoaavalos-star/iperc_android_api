from flask import Blueprint

iperc = Blueprint('iperc', __name__)

from app.iperc import routes