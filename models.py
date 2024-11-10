from database import db
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

[rest of the models code remains the same...]
