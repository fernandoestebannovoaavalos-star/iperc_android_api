from flask import Flask, redirect, url_for, flash, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import Config
from functools import wraps

from flask_login import LoginManager, current_user
from flask_mail import Mail
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import threading

mail = Mail()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Inicia sesión para continuar'


# ─────────────────────────────────────────────
# FIX 7: Rate limiting — máx 10 intentos / 5 min por IP
# ─────────────────────────────────────────────
_intentos = defaultdict(list)
_lock = threading.Lock()

MAX_INTENTOS = 3
VENTANA_SEG  = 300  # 5 minutos

def registrar_intento(ip):
    ahora = datetime.now(timezone.utc)
    with _lock:
        _intentos[ip] = [t for t in _intentos[ip]
                         if (ahora - t).total_seconds() < VENTANA_SEG]
        _intentos[ip].append(ahora)

def ip_bloqueada(ip):
    ahora = datetime.now(timezone.utc)
    with _lock:
        recientes = [t for t in _intentos[ip]
                     if (ahora - t).total_seconds() < VENTANA_SEG]
        _intentos[ip] = recientes
        return len(recientes) >= MAX_INTENTOS


# ─────────────────────────────────────────────
# FIX 1: Middleware WSGI — elimina header Server de Werkzeug
# antes de que llegue al cliente
# ─────────────────────────────────────────────
class SuppressServerHeader:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            # Eliminar cualquier header Server existente
            headers = [(k, v) for k, v in headers if k.lower() != 'server']
            headers.append(('Server', 'IPERC-Server'))
            return start_response(status, headers, exc_info)
        return self.wsgi_app(environ, custom_start_response)


# ─────────────────────────────────────────────
# Filtro de fecha Lima
# ─────────────────────────────────────────────
def filtro_lima(dt, formato='%d/%m/%Y %H:%M'):
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

    # Filtro de fecha Lima
    app.jinja_env.filters['lima'] = filtro_lima

    # FIX 1: Aplicar middleware WSGI para suprimir Server header
    app.wsgi_app = SuppressServerHeader(app.wsgi_app)

    # ─────────────────────────────────────────
    # Headers de seguridad en todas las respuestas
    # ─────────────────────────────────────────
    @app.after_request
    def aplicar_headers_seguridad(response):
        # FIX 2 — Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )

        # FIX 3 — X-Content-Type-Options
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # FIX 4 — Strict Transport Security
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )

        # FIX 5 — Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # FIX 6 — Permissions Policy
        response.headers['Permissions-Policy'] = (
            'geolocation=(self), camera=(), microphone=(), '
            'payment=(), usb=()'
        )

        # FIX 7 — X-Frame-Options (Clickjacking)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # FIX 8 — Cookie segura con SameSite
        if 'Set-Cookie' in response.headers:
            cookies = response.headers.getlist('Set-Cookie')
            response.headers.remove('Set-Cookie')
            for cookie in cookies:
                if 'SameSite' not in cookie:
                    cookie += '; SameSite=Lax'
                if 'Secure' not in cookie:
                    cookie += '; Secure'
                response.headers.add('Set-Cookie', cookie)

        return response

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