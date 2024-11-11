from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, Boolean, ForeignKey, func, Table
from sqlalchemy.orm import relationship
import re

# Define ENUM types
sentimiento_enum = ENUM('positivo', 'negativo', 'neutral', name='sentimiento_enum', schema='app', create_type=False)
agencia_enum = ENUM('Reuters', 'EFE', 'Otro', name='agencia_enum', schema='app', create_type=False)

# Association tables
articulo_evento = Table('articulo_evento', db.Model.metadata,
    Column('articulo_id', Integer, ForeignKey('app.articulo.articulo_id'), primary_key=True),
    Column('evento_id', Integer, ForeignKey('app.evento.evento_id'), primary_key=True),
    schema='app'
)

evento_region = Table('evento_region', db.Model.metadata,
    Column('evento_id', Integer, ForeignKey('app.evento.evento_id'), primary_key=True),
    Column('region_id', Integer, ForeignKey('app.region.region_id'), primary_key=True),
    schema='app'
)

class User(UserMixin, db.Model):
    __tablename__ = 'usuario'
    __table_args__ = {'schema': 'app'}

    id = Column('usuario_id', Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(1000))
    is_admin = Column(Boolean, default=False)
    es_suscriptor = Column(Boolean, default=False)
    fin_fecha_suscripcion = Column(TIMESTAMP)
    status = Column(String(255))
    puntos = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_logs = relationship('UserLog', back_populates='user')

    @staticmethod
    def validate_password(password):
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"
        return True, ""

    @staticmethod
    def validate_email(email):
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))

    def set_password(self, password):
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not password or not self.password_hash:
            return False
        try:
            return check_password_hash(str(self.password_hash), password)
        except Exception:
            return False

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

class UserLog(db.Model):
    __tablename__ = 'user_log'
    __table_args__ = {'schema': 'app'}

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('app.usuario.usuario_id'))
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    articulo_id = Column(Integer, ForeignKey('app.articulo.articulo_id'))
    evento_id = Column(Integer, ForeignKey('app.evento.evento_id'))
    tipo = Column(String(50))
    ip = Column(String(50))
    navegador = Column(String(255))
    puntos_otorgados = Column(Integer, default=0)

    user = relationship('User', back_populates='user_logs')
    articulo = relationship('Articulo', back_populates='user_logs')
    evento = relationship('Evento', back_populates='user_logs')

class Articulo(db.Model):
    __tablename__ = 'articulo'
    __table_args__ = {'schema': 'app'}

    articulo_id = Column(Integer, primary_key=True)
    periodico_id = Column(Integer, ForeignKey('app.periodico.periodico_id'))
    titular = Column(String(1000), nullable=False)
    subtitular = Column(Text)
    url = Column(String(255))
    fecha_publicacion = Column(Date)
    fecha_modificacion = Column(Date)
    agencia = Column(agencia_enum)
    seccion = Column(String(100))
    autor = Column(String(100))
    contenido = Column(Text)
    sentimiento = Column(sentimiento_enum, default='neutral')
    gpt_resumen = Column(Text)
    gpt_opinion = Column(Text)
    paywall = Column(Boolean, default=False)
    embeddings = Column(Text)

    periodico = relationship('Periodico', back_populates='articulos')
    eventos = relationship('Evento', secondary=articulo_evento, back_populates='articulos')
    user_logs = relationship('UserLog', back_populates='articulo')

class Evento(db.Model):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'app'}

    evento_id = Column(Integer, primary_key=True)
    subcategoria_id = Column(Integer, ForeignKey('app.subcategoria.subcategoria_id'))
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text)
    fecha_evento = Column(Date)
    gpt_sujeto_activo = Column(String(255))
    gpt_sujeto_pasivo = Column(String(255))
    gpt_importancia = Column(Integer)
    gpt_tiene_contexto = Column(Boolean, default=False)
    gpt_palabras_clave = Column(String(1000))
    embeddings = Column(Text)

    subcategoria = relationship('Subcategoria', back_populates='eventos')
    articulos = relationship('Articulo', secondary=articulo_evento, back_populates='eventos')
    user_logs = relationship('UserLog', back_populates='evento')

class Categoria(db.Model):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'app'}

    categoria_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)

    subcategorias = relationship('Subcategoria', back_populates='categoria')

class Subcategoria(db.Model):
    __tablename__ = 'subcategoria'
    __table_args__ = {'schema': 'app'}

    subcategoria_id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey('app.categoria.categoria_id'))
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    palabras_clave = Column(Text)
    palabras_clave_embeddings = Column(Text)

    categoria = relationship('Categoria', back_populates='subcategorias')
    eventos = relationship('Evento', back_populates='subcategoria')

class Periodico(db.Model):
    __tablename__ = 'periodico'
    __table_args__ = {'schema': 'app'}

    periodico_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2))
    idioma = Column(String(50))
    url = Column(String(255))
    logo_url = Column(String(255))
    tipo = Column(String(50))
    circulacion = Column(Integer)
    suscriptores = Column(Integer)

    articulos = relationship('Articulo', back_populates='periodico')
