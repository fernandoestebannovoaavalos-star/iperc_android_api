from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Cargo(db.Model):
    __tablename__ = 'cargos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuarios = db.relationship('Usuario', backref='cargo_rel', lazy=True)

    def __repr__(self):
        return f'<Cargo {self.nombre}>'

class Obra(db.Model):
    __tablename__ = 'obras'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    empresa = db.Column(db.String(150), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    lat_centro = db.Column(db.Float, nullable=True)
    lon_centro = db.Column(db.Float, nullable=True)
    radio_perimetro = db.Column(db.Integer, default=100)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Obra {self.nombre}>'

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(8), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    rol = db.Column(db.String(20), default='trabajador')
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=True)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Usuario {self.nombre} {self.apellido}>'