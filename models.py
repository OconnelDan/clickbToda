from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import ENUM

# Create the enum types
agencia_enum = ENUM('Reuters', 'EFE', 'Otro', name='agencia_enum', schema='app', create_type=False)
sentimiento_enum = ENUM('positivo', 'negativo', 'neutral', name='sentimiento_enum', schema='app', create_type=False)

# Association tables
articulo_evento = db.Table('articulo_evento',
    db.Column('articulo_id', db.Integer, db.ForeignKey('app.articulo.articulo_id'), primary_key=True),
    db.Column('evento_id', db.Integer, db.ForeignKey('app.evento.evento_id'), primary_key=True),
    db.Column('cluster_id', db.Integer),
    db.Column('cluster_descripcion', db.String(255)),
    schema='app'
)

evento_region = db.Table('evento_region',
    db.Column('evento_id', db.Integer, db.ForeignKey('app.evento.evento_id'), primary_key=True),
    db.Column('region_id', db.Integer, db.ForeignKey('app.region.region_id'), primary_key=True),
    schema='app'
)

class User(UserMixin, db.Model):
    __tablename__ = 'USER'
    __table_args__ = {'schema': 'app'}
    
    user_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    es_suscriptor = db.Column(db.Boolean, default=False)
    fin_fecha_suscripcion = db.Column(db.DateTime)
    status = db.Column(db.String(255))
    password_hash = db.Column(db.String(1000))
    puntos = db.Column(db.Integer, default=0)

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Articulo(db.Model):
    __tablename__ = 'articulo'
    __table_args__ = {'schema': 'app'}
    
    articulo_id = db.Column(db.Integer, primary_key=True)
    titular = db.Column(db.String(1000), nullable=False)
    subtitular = db.Column(db.Text)
    gpt_palabras_clave = db.Column(db.String(1000))
    numero_de_palabras = db.Column(db.Integer)
    likes = db.Column(db.Integer)
    tipo = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(255))
    paywall = db.Column(db.Boolean, default=False)
    fecha_publicacion = db.Column(db.Date)
    updated_on = db.Column(db.DateTime)
    periodico_id = db.Column(db.Integer, db.ForeignKey('app.periodico.periodico_id'), nullable=False)
    periodista_id = db.Column(db.Integer, db.ForeignKey('app.periodista.periodista_id'))
    ideologia_id = db.Column(db.Integer, db.ForeignKey('app.ideologia.ideologia_id'))
    cuerpo = db.Column(db.Text)
    gpt_titular = db.Column(db.String(1000))
    gpt_sentimiento = db.Column(sentimiento_enum, default='neutral')
    gpt_titular_clickbait = db.Column(db.Boolean, default=False)
    agencia = db.Column(agencia_enum)
    gpt_importancia = db.Column(db.Integer)
    gpt_cantidad_fuentes_citadas = db.Column(db.Integer)
    gpt_opinion = db.Column(db.String)
    gpt_resumen = db.Column(db.String)
    palabras_clave_embeddings = db.Column(db.String)

    periodico = db.relationship('Periodico', backref='articulos')
    periodista = db.relationship('Periodista', backref='articulos')
    ideologia = db.relationship('Ideologia', backref='articulos')
    eventos = db.relationship('Evento', secondary=articulo_evento, backref='articulos')

class Categoria(db.Model):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'app'}
    
    categoria_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    subnombre = db.Column(db.String)
    subdescripcion = db.Column(db.String)

class Evento(db.Model):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'app'}
    
    evento_id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_evento = db.Column(db.Date)
    impacto = db.Column(db.String(255))
    categoria_id = db.Column(db.Integer, db.ForeignKey('app.categoria.categoria_id'), nullable=False)
    grupo_de_eventos_id = db.Column(db.Integer)
    subgrupo_de_eventos_id = db.Column(db.Integer)
    gpt_sujeto_activo = db.Column(db.String(255))
    gpt_sujeto_pasivo = db.Column(db.String(255))
    gpt_importancia = db.Column(db.Integer)
    gpt_tiene_contexto = db.Column(db.Boolean, default=False)
    embeddings = db.Column(db.String)  # Added embeddings field

    categoria = db.relationship('Categoria', backref='eventos')
    regiones = db.relationship('Region', secondary=evento_region, backref='eventos')

# Rest of the models...
class Region(db.Model):
    __tablename__ = 'region'
    __table_args__ = {'schema': 'app'}
    
    region_id = db.Column(db.Integer, primary_key=True)
    region_nombre = db.Column(db.String(255), nullable=False)
    pais_iso_code = db.Column(db.String(2))
    ISO31662_subdivision_code = db.Column(db.String)
    pais_nombre = db.Column(db.String)

class Ideologia(db.Model):
    __tablename__ = 'ideologia'
    __table_args__ = {'schema': 'app'}
    
    ideologia_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

class Periodista(db.Model):
    __tablename__ = 'periodista'
    __table_args__ = {'schema': 'app'}
    
    periodista_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    apellido = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    telefono = db.Column(db.String(50))
    biografia = db.Column(db.Text)
    fecha_nacimiento = db.Column(db.Date)
    nacionalidad = db.Column(db.String(255))
    foto = db.Column(db.String(255))

class Periodico(db.Model):
    __tablename__ = 'periodico'
    __table_args__ = {'schema': 'app'}
    
    periodico_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    pais_iso_code = db.Column(db.String(2))
    idioma = db.Column(db.String(50))
    sitio_web = db.Column(db.String(255))
    logo_url = db.Column(db.String(255))
    tipo = db.Column(db.String(50))
    circulacion = db.Column(db.Integer)
    suscriptores = db.Column(db.Integer)
    ideologia_id = db.Column(db.Integer, db.ForeignKey('app.ideologia.ideologia_id'))
