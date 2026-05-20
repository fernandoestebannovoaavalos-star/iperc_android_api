from flask import Flask, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import Config
from functools import wraps

from flask_login import LoginManager, current_user
from flask_mail import Mail

mail = Mail()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Inicia sesión para continuar'


def filtro_lima(dt, formato='%d/%m/%Y %H:%M'):
    """
    Filtro Jinja2 para fechas.
    Tras la migración a TIMESTAMPTZ, psycopg2 ya devuelve
    datetimes con tzinfo=UTC-05:00 (hora Lima).
    Solo formateamos — sin conversión adicional.
    """
    if dt is None:
        return ''
    return dt.strftime(formato)


def solo_rol(*roles):
    def decorador(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.rol not in roles:
                flash('No tienes permiso para acceder a esa página.')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorador


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.iperc import iperc as iperc_blueprint
    app.register_blueprint(iperc_blueprint)

    from app.supervisor import supervisor as supervisor_blueprint
    app.register_blueprint(supervisor_blueprint)

    from app.reportes import reportes as reportes_blueprint
    app.register_blueprint(reportes_blueprint)

    from app.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # Filtro de fecha disponible en todos los templates
    app.jinja_env.filters['lima'] = filtro_lima

    @app.context_processor
    def inject_pendientes():
        from app.models import RegistroIPERC
        try:
            if current_user.is_authenticated and current_user.rol in ['supervisor', 'admin']:
                count = RegistroIPERC.query.filter_by(estado='pendiente').count()
            else:
                count = 0
        except:
            count = 0
        return dict(pendientes_count=count)

    return app