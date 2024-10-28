from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'USER'
    __table_args__ = {'schema': 'app'}
    
    user_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(1000))
    is_admin = db.Column(db.Boolean, default=False)
    es_suscriptor = db.Column(db.Boolean, default=False)
    fin_fecha_suscripcion = db.Column(db.DateTime)
    status = db.Column(db.String(255))
    puntos = db.Column(db.Integer, default=0)

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Association table for the many-to-many relationship
articulo_evento = db.Table('articulo_evento',
    db.Column('articulo_id', db.Integer, db.ForeignKey('app.articulo.articulo_id'), primary_key=True),
    db.Column('evento_id', db.Integer, db.ForeignKey('app.evento.evento_id'), primary_key=True),
    db.Column('cluster_id', db.Integer),
    db.Column('cluster_descripcion', db.String(255)),
    schema='app'
)

class Articulo(db.Model):
    __tablename__ = 'articulo'
    __table_args__ = {'schema': 'app'}
    
    articulo_id = db.Column(db.Integer, primary_key=True)
    titular = db.Column(db.String(1000), nullable=False)
    subtitular = db.Column(db.Text)
    url = db.Column(db.String(255))
    paywall = db.Column(db.Boolean, default=False)
    fecha_publicacion = db.Column(db.Date)
    periodico_id = db.Column(db.Integer, db.ForeignKey('app.periodico.periodico_id'))
    periodico = db.relationship('Periodico', backref='articulos')
    eventos = db.relationship('Evento', secondary=articulo_evento, backref='articulos')

class Periodico(db.Model):
    __tablename__ = 'periodico'
    __table_args__ = {'schema': 'app'}
    
    periodico_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    logo_url = db.Column(db.String(255))

class Evento(db.Model):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'app'}
    
    evento_id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('app.categoria.categoria_id'))
    categoria = db.relationship('Categoria', backref='eventos')

class Categoria(db.Model):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'app'}
    
    categoria_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
