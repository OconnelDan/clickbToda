from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, Boolean, ForeignKey, func, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Definir los tipos ENUM según el DDL
sentimiento_enum = ENUM('positivo', 'negativo', 'neutral', name='sentimiento_enum', schema='app')
agencia_enum = ENUM('Reuters', 'EFE', 'Otro', name='agencia_enum', schema='app')

# Association tables
articulo_evento = Table('articulo_evento', Base.metadata,
    Column('articulo_id', Integer, ForeignKey('app.articulo.articulo_id'), primary_key=True),
    Column('evento_id', Integer, ForeignKey('app.evento.evento_id'), primary_key=True),
    schema='app'
)

evento_region = Table('evento_region', Base.metadata,
    Column('evento_id', Integer, ForeignKey('app.evento.evento_id'), primary_key=True),
    Column('region_id', Integer, ForeignKey('app.region.region_id'), primary_key=True),
    schema='app'
)

class User(Base, UserMixin):
    __tablename__ = 'usuario'
    __table_args__ = {'schema': 'app'}

    id = Column('usuario_id', Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs = relationship('UserLog', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Categoria(Base):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'app'}

    categoria_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    subcategorias = relationship('Subcategoria', backref='categoria', lazy=True)

class Subcategoria(Base):
    __tablename__ = 'subcategoria'
    __table_args__ = {'schema': 'app'}

    subcategoria_id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey('app.categoria.categoria_id'), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    palabras_clave = Column(Text, nullable=True)
    palabras_clave_embeddings = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    eventos = relationship('Evento', backref='subcategoria', lazy=True)

class Region(Base):
    __tablename__ = 'region'
    __table_args__ = {'schema': 'app'}

    region_id = Column(Integer, primary_key=True)
    region_nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2), nullable=True)
    ISO31662_subdivision_code = Column(String, nullable=True)
    pais_nombre = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    eventos = relationship('Evento', secondary=evento_region, back_populates='regiones')

class Evento(Base):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'app'}

    evento_id = Column(Integer, primary_key=True)
    subcategoria_id = Column(Integer, ForeignKey('app.subcategoria.subcategoria_id'), nullable=False)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text)
    fecha_evento = Column(Date)
    gpt_sujeto_activo = Column(String(255))
    gpt_sujeto_pasivo = Column(String(255))
    gpt_importancia = Column(Integer)
    gpt_tiene_contexto = Column(Boolean, default=False)
    gpt_palabras_clave = Column(String(1000))
    embeddings = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    regiones = relationship('Region', secondary=evento_region, back_populates='eventos')
    articulos = relationship('Articulo', secondary=articulo_evento, back_populates='eventos')
    user_logs = relationship('UserLog', back_populates='evento')

class Periodico(Base):
    __tablename__ = 'periodico'
    __table_args__ = {'schema': 'app'}

    periodico_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2))
    idioma = Column(String(50))
    url = Column(String(255))
    logo_url = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    articulos = relationship('Articulo', back_populates='periodico')

class Articulo(Base):
    __tablename__ = 'articulo'
    __table_args__ = {'schema': 'app'}

    articulo_id = Column(Integer, primary_key=True)
    periodico_id = Column(Integer, ForeignKey('app.periodico.periodico_id'), nullable=False)
    titular = Column(String(1000), nullable=False)
    subtitulo = Column(Text)
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
    embeddings = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    eventos = relationship('Evento', secondary=articulo_evento, back_populates='articulos')
    periodico = relationship('Periodico', back_populates='articulos')
    user_logs = relationship('UserLog', back_populates='articulo')

class UserLog(Base):
    __tablename__ = 'user_log'
    __table_args__ = {'schema': 'app'}

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('app.usuario.usuario_id'), nullable=True)
    timestamp = Column('timestamp', TIMESTAMP, nullable=True, default=func.now())
    articulo_id = Column(Integer, ForeignKey('app.articulo.articulo_id'), nullable=True)
    evento_id = Column(Integer, ForeignKey('app.evento.evento_id'), nullable=True)
    tipo = Column(String(50))
    ip = Column(String(50))
    navegador = Column(String(255))
    puntos_otorgados = Column(Integer, default=0)

    user = relationship('User', back_populates='logs')
    articulo = relationship('Articulo', back_populates='user_logs')
    evento = relationship('Evento', back_populates='user_logs')
