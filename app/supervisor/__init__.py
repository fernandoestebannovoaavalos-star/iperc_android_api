from flask import Blueprint

supervisor = Blueprint('supervisor', __name__)

from app.supervisor import routes