from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
import re

# Define ENUM types
sentimiento_enum = ENUM('positivo', 'negativo', 'neutral', name='sentimiento_enum', schema='app', create_type=False)
agencia_enum = ENUM('Reuters', 'EFE', 'Otro', name='agencia_enum', schema='app', create_type=False)

class User(UserMixin, db.Model):
    __tablename__ = 'USER'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    id = Column('user_id', Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(1000))
    is_admin = Column(Boolean, default=False)
    es_suscriptor = Column(Boolean, default=False)
    fin_fecha_suscripcion = Column(TIMESTAMP)
    status = Column(String(255))
    puntos = Column(Integer, default=0)

    logs = relationship('UserLog', back_populates='user')

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

class UserLog(db.Model):
    __tablename__ = 'user_log'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('app.USER.user_id'), nullable=True)
    timestamp = Column(TIMESTAMP, nullable=True, default=func.now())
    articulo_id = Column(Integer, ForeignKey('app.articulo.articulo_id'), nullable=True)
    evento_id = Column(Integer, ForeignKey('app.evento.evento_id'), nullable=True)
    tipo = Column(String(50))
    ip = Column(String(50))
    navegador = Column(String(255))
    puntos_otorgados = Column(Integer, default=0)

    user = relationship('User', back_populates='logs')
    articulo = relationship('Articulo', back_populates='user_logs')
    evento = relationship('Evento', back_populates='user_logs')

class Categoria(db.Model):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    categoria_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)

    subcategorias = relationship('Subcategoria', back_populates='categoria')

class Subcategoria(db.Model):
    __tablename__ = 'subcategoria'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    subcategoria_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    categoria_id = Column(Integer, ForeignKey('app.categoria.categoria_id'), nullable=False)
    palabras_clave = Column(Text)
    palabras_clave_embeddings = Column(Text)

    categoria = relationship('Categoria', back_populates='subcategorias')
    eventos = relationship('Evento', back_populates='subcategoria')

class Ideologia(db.Model):
    __tablename__ = 'ideologia'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    ideologia_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)

    periodicos = relationship('Periodico', back_populates='ideologia')
    articulos = relationship('Articulo', back_populates='ideologia')

class Region(db.Model):
    __tablename__ = 'region'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    region_id = Column(Integer, primary_key=True, autoincrement=True)
    region_nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2))
    ISO31662_subdivision_code = Column(String)
    pais_nombre = Column(String)

    eventos = relationship('EventoRegion', back_populates='region')

class Evento(db.Model):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    evento_id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text)
    fecha_evento = Column(Date)
    impacto = Column(String(255))
    subcategoria_id = Column(Integer, ForeignKey('app.subcategoria.subcategoria_id'), nullable=False)
    gpt_sujeto_activo = Column(String(255))
    gpt_sujeto_pasivo = Column(String(255))
    gpt_importancia = Column(Integer)
    gpt_tiene_contexto = Column(Boolean, default=False)
    embeddings = Column(String)
    gpt_palabras_clave = Column(String(1000))

    subcategoria = relationship('Subcategoria', back_populates='eventos')
    regiones = relationship('EventoRegion', back_populates='evento')
    articulos_relacionados = relationship('ArticuloEvento', back_populates='evento')
    user_logs = relationship('UserLog', back_populates='evento')

class EventoRegion(db.Model):
    __tablename__ = 'evento_region'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    evento_id = Column(Integer, ForeignKey('app.evento.evento_id'), primary_key=True)
    region_id = Column(Integer, ForeignKey('app.region.region_id'), primary_key=True)

    evento = relationship('Evento', back_populates='regiones')
    region = relationship('Region', back_populates='eventos')

class Periodista(db.Model):
    __tablename__ = 'periodista'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    periodista_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    email = Column(String(255))
    telefono = Column(String(50))
    biografia = Column(Text)
    fecha_nacimiento = Column(Date)
    nacionalidad = Column(String(255))
    foto = Column(String(255))

    articulos = relationship('Articulo', back_populates='periodista')

class Periodico(db.Model):
    __tablename__ = 'periodico'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    periodico_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2))
    idioma = Column(String(50))
    sitio_web = Column(String(255))
    logo_url = Column(String(255))
    tipo = Column(String(50))
    circulacion = Column(Integer)
    suscriptores = Column(Integer)
    ideologia_id = Column(Integer, ForeignKey('app.ideologia.ideologia_id'))

    ideologia = relationship('Ideologia', back_populates='periodicos')
    articulos = relationship('Articulo', back_populates='periodico')

class Articulo(db.Model):
    __tablename__ = 'articulo'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    articulo_id = Column(Integer, primary_key=True, autoincrement=True)
    titular = Column(String(1000), nullable=False)
    subtitular = Column(Text)
    cuerpo = Column(Text)
    gpt_palabras_clave = Column(String(1000))
    numero_de_palabras = Column(Integer)
    likes = Column(Integer)
    tipo = Column(String(50), nullable=False)
    url = Column(String(255))
    paywall = Column(Boolean, default=False)
    fecha_publicacion = Column(Date)
    updated_on = Column(TIMESTAMP)
    periodico_id = Column(Integer, ForeignKey('app.periodico.periodico_id'), nullable=False)
    periodista_id = Column(Integer, ForeignKey('app.periodista.periodista_id'))
    ideologia_id = Column(Integer, ForeignKey('app.ideologia.ideologia_id'))
    gpt_titular = Column(String(1000))
    gpt_sentimiento = Column(sentimiento_enum, default='neutral')
    gpt_titular_clickbait = Column(Boolean, default=False)
    agencia = Column(agencia_enum)
    gpt_importancia = Column(Integer)
    gpt_cantidad_fuentes_citadas = Column(Integer)
    gpt_opinion = Column(String)
    gpt_resumen = Column(String)
    palabras_clave_embeddings = Column(String)
    embeddings = Column(String)
    subcategoria_id = Column(Integer, ForeignKey('app.subcategoria.subcategoria_id'), nullable=False)

    ideologia = relationship('Ideologia', back_populates='articulos')
    periodico = relationship('Periodico', back_populates='articulos')
    periodista = relationship('Periodista', back_populates='articulos')
    eventos_relacionados = relationship('ArticuloEvento', back_populates='articulo')
    user_logs = relationship('UserLog', back_populates='articulo')

class ArticuloEvento(db.Model):
    __tablename__ = 'articulo_evento'
    __table_args__ = {'schema': 'app', 'extend_existing': True}

    articulo_id = Column(Integer, ForeignKey('app.articulo.articulo_id'), primary_key=True)
    evento_id = Column(Integer, ForeignKey('app.evento.evento_id'), primary_key=True)
    cluster_id = Column(Integer)
    cluster_descripcion = Column(String(255))

    articulo = relationship('Articulo', back_populates='eventos_relacionados')
    evento = relationship('Evento', back_populates='articulos_relacionados')
