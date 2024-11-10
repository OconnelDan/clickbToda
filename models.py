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
    Column('articulo_id', Integer, ForeignKey('app.articulo.articulo_id', ondelete='CASCADE'), primary_key=True),
    Column('evento_id', Integer, ForeignKey('app.evento.evento_id', ondelete='CASCADE'), primary_key=True),
    Column('cluster_id', Integer),
    Column('cluster_descripcion', String(255)),
    schema='app'
)

evento_region = Table('evento_region', db.Model.metadata,
    Column('evento_id', Integer, ForeignKey('app.evento.evento_id', ondelete='CASCADE'), primary_key=True),
    Column('region_id', Integer, ForeignKey('app.region.region_id', ondelete='CASCADE'), primary_key=True),
    schema='app'
)

articulo_influencer_mencion = Table('articulo_influencer_mencion', db.Model.metadata,
    Column('articulo_id', Integer, ForeignKey('app.articulo.articulo_id', ondelete='CASCADE'), primary_key=True),
    Column('influencer_id', Integer, ForeignKey('app.influencer.influencer_id', ondelete='CASCADE'), primary_key=True),
    Column('fecha_mencion', TIMESTAMP, default=func.now()),
    Column('plataforma', String(255)),
    Column('url', String(255)),
    schema='app'
)

class User(UserMixin, db.Model):
    __tablename__ = 'USER'
    __table_args__ = {'schema': 'app'}

    id = Column('user_id', Integer, primary_key=True)
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

    user_logs = relationship('UserLog', back_populates='user', cascade='all, delete-orphan')

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
    __table_args__ = {'schema': 'app'}

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('app.USER.user_id', ondelete='SET NULL'))
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    articulo_id = Column(Integer, ForeignKey('app.articulo.articulo_id', ondelete='SET NULL'))
    evento_id = Column(Integer, ForeignKey('app.evento.evento_id', ondelete='SET NULL'))
    tipo = Column(String(50))
    ip = Column(String(50))
    navegador = Column(String(255))
    puntos_otorgados = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='user_logs')
    articulo = relationship('Articulo', back_populates='user_logs')
    evento = relationship('Evento', back_populates='user_logs')

class Region(db.Model):
    __tablename__ = 'region'
    __table_args__ = {'schema': 'app'}

    region_id = Column(Integer, primary_key=True)
    region_nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2))
    ISO31662_subdivision_code = Column(String)
    pais_nombre = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    eventos = relationship('Evento', secondary=evento_region, back_populates='regiones')

class GrupoDeEventos(db.Model):
    __tablename__ = 'grupo_de_eventos'
    __table_args__ = {'schema': 'app'}

    grupo_de_eventos_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    subgrupos = relationship('SubgrupoDeEventos', back_populates='grupo', cascade='all, delete-orphan')
    eventos = relationship('Evento', back_populates='grupo')

class SubgrupoDeEventos(db.Model):
    __tablename__ = 'subgrupo_de_eventos'
    __table_args__ = {'schema': 'app'}

    subgrupo_de_eventos_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    grupo_de_eventos_id = Column(Integer, ForeignKey('app.grupo_de_eventos.grupo_de_eventos_id'), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    grupo = relationship('GrupoDeEventos', back_populates='subgrupos')
    eventos = relationship('Evento', back_populates='subgrupo')

class Influencer(db.Model):
    __tablename__ = 'influencer'
    __table_args__ = {'schema': 'app'}

    influencer_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    plataforma = Column(String(255))
    username = Column(String(255))
    seguidores = Column(Integer)
    url = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    opiniones = relationship('InfluencerOpinion', back_populates='influencer', cascade='all, delete-orphan')
    articulos = relationship('Articulo', secondary=articulo_influencer_mencion, back_populates='influencers')

class InfluencerOpinion(db.Model):
    __tablename__ = 'influencer_opinion'
    __table_args__ = {'schema': 'app'}

    opinion_id = Column(Integer, primary_key=True)
    influencer_id = Column(Integer, ForeignKey('app.influencer.influencer_id'), nullable=False)
    evento_id = Column(Integer, ForeignKey('app.evento.evento_id'), nullable=False)
    contenido = Column(Text)
    fecha_publicacion = Column(TIMESTAMP, default=func.now())
    url = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    influencer = relationship('Influencer', back_populates='opiniones')
    evento = relationship('Evento', back_populates='opiniones')

class Articulo(db.Model):
    __tablename__ = 'articulo'
    __table_args__ = {'schema': 'app'}

    articulo_id = Column(Integer, primary_key=True)
    titular = Column(String(1000), nullable=False)
    subtitular = Column(Text)
    url = Column(String(255))
    fecha_publicacion = Column(Date)
    updated_on = Column(TIMESTAMP)
    periodico_id = Column(Integer, ForeignKey('app.periodico.periodico_id'), nullable=False)
    periodista_id = Column(Integer, ForeignKey('app.periodista.periodista_id'))
    ideologia_id = Column(Integer, ForeignKey('app.ideologia.ideologia_id'))
    tipo = Column(String(50), nullable=False)
    agencia = Column(agencia_enum)
    numero_de_palabras = Column(Integer)
    likes = Column(Integer)
    paywall = Column(Boolean, default=False)
    cuerpo = Column(Text)
    gpt_titular = Column(String(1000))
    gpt_palabras_clave = Column(String(1000))
    gpt_sentimiento = Column(sentimiento_enum, default='neutral')
    gpt_titular_clickbait = Column(Boolean, default=False)
    gpt_importancia = Column(Integer)
    gpt_cantidad_fuentes_citadas = Column(Integer)
    gpt_opinion = Column(Text)
    gpt_resumen = Column(Text)
    palabras_clave_embeddings = Column(Text)
    embeddings = Column(Text)
    subcategoria_id = Column(Integer, ForeignKey('app.subcategoria.subcategoria_id'))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    periodico = relationship('Periodico', back_populates='articulos')
    periodista = relationship('Periodista', back_populates='articulos')
    eventos = relationship('Evento', secondary=articulo_evento, back_populates='articulos')
    user_logs = relationship('UserLog', back_populates='articulo')
    influencers = relationship('Influencer', secondary=articulo_influencer_mencion, back_populates='articulos')
    subcategoria = relationship('Subcategoria', back_populates='articulos')
    ideologia = relationship('Ideologia', back_populates='articulos')

class Evento(db.Model):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'app'}

    evento_id = Column(Integer, primary_key=True)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text)
    fecha_evento = Column(Date)
    impacto = Column(String(255))
    grupo_de_eventos_id = Column(Integer, ForeignKey('app.grupo_de_eventos.grupo_de_eventos_id'))
    subgrupo_de_eventos_id = Column(Integer, ForeignKey('app.subgrupo_de_eventos.subgrupo_de_eventos_id'))
    subcategoria_id = Column(Integer, ForeignKey('app.subcategoria.subcategoria_id'))
    gpt_sujeto_activo = Column(String(255))
    gpt_sujeto_pasivo = Column(String(255))
    gpt_importancia = Column(Integer)
    gpt_tiene_contexto = Column(Boolean, default=False)
    gpt_palabras_clave = Column(String)
    embeddings = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    grupo = relationship('GrupoDeEventos', back_populates='eventos')
    subgrupo = relationship('SubgrupoDeEventos', back_populates='eventos')
    subcategoria = relationship('Subcategoria', back_populates='eventos')
    articulos = relationship('Articulo', secondary=articulo_evento, back_populates='eventos')
    user_logs = relationship('UserLog', back_populates='evento')
    opiniones = relationship('InfluencerOpinion', back_populates='evento')
    regiones = relationship('Region', secondary=evento_region, back_populates='eventos')

class Categoria(db.Model):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'app'}

    categoria_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    subcategorias = relationship('Subcategoria', back_populates='categoria', cascade='all, delete-orphan')

class Subcategoria(db.Model):
    __tablename__ = 'subcategoria'
    __table_args__ = {'schema': 'app'}

    subcategoria_id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey('app.categoria.categoria_id'), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    palabras_clave = Column(Text)
    palabras_clave_embeddings = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    categoria = relationship('Categoria', back_populates='subcategorias')
    eventos = relationship('Evento', back_populates='subcategoria')
    articulos = relationship('Articulo', back_populates='subcategoria')

class Ideologia(db.Model):
    __tablename__ = 'ideologia'
    __table_args__ = {'schema': 'app'}

    ideologia_id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    periodicos = relationship('Periodico', back_populates='ideologia')
    articulos = relationship('Articulo', back_populates='ideologia')

class Periodico(db.Model):
    __tablename__ = 'periodico'
    __table_args__ = {'schema': 'app'}

    periodico_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    pais_iso_code = Column(String(2))
    idioma = Column(String(50))
    sitio_web = Column(String(255))
    logo_url = Column(String(255))
    tipo = Column(String(50))
    circulacion = Column(Integer)
    suscriptores = Column(Integer)
    ideologia_id = Column(Integer, ForeignKey('app.ideologia.ideologia_id'))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    ideologia = relationship('Ideologia', back_populates='periodicos')
    articulos = relationship('Articulo', back_populates='periodico')

class Periodista(db.Model):
    __tablename__ = 'periodista'
    __table_args__ = {'schema': 'app'}

    periodista_id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    email = Column(String(255))
    telefono = Column(String(50))
    biografia = Column(Text)
    fecha_nacimiento = Column(Date)
    nacionalidad = Column(String(255))
    foto = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    articulos = relationship('Articulo', back_populates='periodista')
