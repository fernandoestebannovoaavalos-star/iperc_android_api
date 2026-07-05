from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta

LIMA = timezone(timedelta(hours=-5))

def _ahora_lima():
    """Hora Lima (UTC-5) para almacenamiento en BD."""
    return datetime.now(LIMA)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


class Cargo(db.Model):
    __tablename__ = 'cargos'
    id     = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)


class Obra(db.Model):
    __tablename__ = 'obras'
    id              = db.Column(db.Integer, primary_key=True)
    nombre          = db.Column(db.String(150), nullable=False)
    empresa         = db.Column(db.String(150), nullable=True)
    direccion       = db.Column(db.String(200), nullable=True)
    lat_centro      = db.Column(db.Float,        nullable=True)
    lon_centro      = db.Column(db.Float,        nullable=True)
    radio_perimetro = db.Column(db.Integer,      default=100)
    activo          = db.Column(db.Boolean,      default=True)


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id            = db.Column(db.Integer,      primary_key=True)
    nombre        = db.Column(db.String(100),  nullable=False)
    apellido      = db.Column(db.String(100),  nullable=False)
    dni           = db.Column(db.String(8),    unique=True, nullable=False)
    email         = db.Column(db.String(120),  unique=True, nullable=True)
    password_hash = db.Column(db.LargeBinary,  nullable=False)
    rol           = db.Column(db.String(20),   default='trabajador')
    cargo_id      = db.Column(db.Integer,      db.ForeignKey('cargos.id'), nullable=True)
    obra_id       = db.Column(db.Integer,      db.ForeignKey('obras.id'),  nullable=True)
    activo        = db.Column(db.Boolean,      default=True)
    debe_cambiar_clave = db.Column(db.Boolean, default=False)
    # FIX 1: utcnow deprecado → _ahora_utc
    created_at    = db.Column(db.DateTime(timezone=True), default=_ahora_lima)

    # FIX 3: relaciones faltantes — permiten usuario.cargo y usuario.obra
    cargo = db.relationship('Cargo', foreign_keys=[cargo_id])
    obra  = db.relationship('Obra',  foreign_keys=[obra_id])


class Area(db.Model):
    __tablename__ = 'areas'
    id          = db.Column(db.Integer,     primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False)
    actividades = db.relationship('Actividad', backref='area', lazy=True)


class Actividad(db.Model):
    __tablename__ = 'actividades'
    id       = db.Column(db.Integer,     primary_key=True)
    nombre   = db.Column(db.String(150), nullable=False)
    area_id  = db.Column(db.Integer,     db.ForeignKey('areas.id'), nullable=False)
    peligros = db.relationship('PeligroBase', backref='actividad', lazy=True)


class TipoPeligro(db.Model):
    __tablename__ = 'tipos_peligro'
    id     = db.Column(db.Integer,    primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)


class PeligroBase(db.Model):
    __tablename__ = 'peligros_base'
    id                 = db.Column(db.Integer, primary_key=True)
    actividad_id       = db.Column(db.Integer, db.ForeignKey('actividades.id'),   nullable=False)
    tipo_peligro_id    = db.Column(db.Integer, db.ForeignKey('tipos_peligro.id'), nullable=False)
    descripcion        = db.Column(db.Text,    nullable=False)
    riesgo_consecuencia= db.Column(db.Text,    nullable=False)
    p_sin              = db.Column(db.Integer, nullable=False)
    s_sin              = db.Column(db.Integer, nullable=False)
    nivel_sin          = db.Column(db.String(50), nullable=False)
    medidas_control    = db.Column(db.Text,    nullable=False)
    p_con              = db.Column(db.Integer, nullable=False)
    s_con              = db.Column(db.Integer, nullable=False)
    nivel_con          = db.Column(db.String(50), nullable=False)
    responsable        = db.Column(db.String(100), nullable=True)
    requisito_legal    = db.Column(db.String(100), nullable=True)

    # FIX 4: relación faltante — permite peligro.tipo_peligro.nombre
    tipo_peligro = db.relationship('TipoPeligro', foreign_keys=[tipo_peligro_id])


class RegistroIPERC(db.Model):
    __tablename__ = 'registros_iperc'
    id            = db.Column(db.Integer,    primary_key=True)
    codigo        = db.Column(db.String(30), unique=True)
    usuario_id    = db.Column(db.Integer,    db.ForeignKey('usuarios.id'),    nullable=False)
    area_id       = db.Column(db.Integer,    db.ForeignKey('areas.id'),       nullable=False)
    actividad_id  = db.Column(db.Integer,    db.ForeignKey('actividades.id'), nullable=False)
    estado        = db.Column(db.String(20), default='pendiente')
    observacion   = db.Column(db.Text,       nullable=True)
    lat           = db.Column(db.Float,      nullable=True)
    lon           = db.Column(db.Float,      nullable=True)
    geo_validado  = db.Column(db.Boolean,    default=False)
    archivado = db.Column(db.Boolean, default=False)  # ← línea nueva
    # FIX 1: utcnow deprecado → _ahora_utc
    fecha_registro= db.Column(db.DateTime(timezone=True), default=_ahora_lima)
    supervisor_id = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=True)

    area          = db.relationship('Area',     foreign_keys=[area_id])
    actividad     = db.relationship('Actividad',foreign_keys=[actividad_id])
    registrado_por= db.relationship('Usuario',  foreign_keys=[usuario_id])
    supervisor    = db.relationship('Usuario',  foreign_keys=[supervisor_id])
    firmas        = db.relationship('FirmaDigital',    backref='registro',  lazy=True)
    # FIX 2: relación faltante con PeligroAdicional + cascade para borrado en cascada
    peligros_adicionales = db.relationship(
        'PeligroAdicional', backref='registro_iperc',
        lazy=True, cascade='all, delete-orphan'
    )


class FirmaDigital(db.Model):
    __tablename__ = 'firmas_digitales'
    id          = db.Column(db.Integer,  primary_key=True)
    registro_id = db.Column(db.Integer,  db.ForeignKey('registros_iperc.id'), nullable=False)
    usuario_id  = db.Column(db.Integer,  db.ForeignKey('usuarios.id'),        nullable=False)
    firma_imagen= db.Column(db.Text,     nullable=False)
    # FIX 1: utcnow deprecado → _ahora_utc
    timestamp   = db.Column(db.DateTime(timezone=True), default=_ahora_lima)
    lat         = db.Column(db.Float,    nullable=True)
    lon         = db.Column(db.Float,    nullable=True)
    tipo        = db.Column(db.String(20), default='trabajador')
    usuario     = db.relationship('Usuario', foreign_keys=[usuario_id])


class PeligroAdicional(db.Model):
    __tablename__ = 'peligros_adicionales'
    id                  = db.Column(db.Integer,    primary_key=True)
    registro_id         = db.Column(db.Integer,    db.ForeignKey('registros_iperc.id'), nullable=False)
    descripcion         = db.Column(db.Text,       nullable=False)
    tipo                = db.Column(db.String(50), nullable=False)
    riesgo_consecuencia = db.Column(db.Text,       nullable=False)
    p_sin               = db.Column(db.Integer,    nullable=False)
    s_sin               = db.Column(db.Integer,    nullable=False)
    nivel_sin           = db.Column(db.String(20), nullable=False)
    medidas_control     = db.Column(db.Text,       nullable=False)
    p_con               = db.Column(db.Integer,    nullable=False)
    s_con               = db.Column(db.Integer,    nullable=False)
    nivel_con           = db.Column(db.String(20), nullable=False)
    # FIX 1: utcnow deprecado → _ahora_utc
    created_at          = db.Column(db.DateTime(timezone=True), default=_ahora_lima)



class RegistroPeligro(db.Model):
    __tablename__ = 'registros_peligros'
    id              = db.Column(db.Integer, primary_key=True)
    registro_id     = db.Column(db.Integer, db.ForeignKey('registros_iperc.id'), nullable=False)
    peligro_base_id = db.Column(db.Integer, db.ForeignKey('peligros_base.id'),   nullable=False)
    p_sin           = db.Column(db.Integer, nullable=False)
    s_sin           = db.Column(db.Integer, nullable=False)
    nivel_sin       = db.Column(db.String(20), nullable=False)
    peligro_base    = db.relationship('PeligroBase', foreign_keys=[peligro_base_id])