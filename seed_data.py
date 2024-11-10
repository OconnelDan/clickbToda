from flask import Flask
from models import db, Categoria, Subcategoria
import logging
from config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def seed_categories(app):
    categories_data = [
        {
            'nombre': 'Politics',
            'descripcion': 'Political news and events',
            'subcategories': [
                {
                    'nombre': 'International Relations',
                    'descripcion': 'Diplomatic relations and international politics',
                    'palabras_clave': 'diplomacy,international,relations,summit,treaty'
                },
                {
                    'nombre': 'Domestic Politics',
                    'descripcion': 'National political developments',
                    'palabras_clave': 'legislation,congress,parliament,policy,government'
                }
            ]
        },
        {
            'nombre': 'Economy',
            'descripcion': 'Economic and financial news',
            'subcategories': [
                {
                    'nombre': 'Markets',
                    'descripcion': 'Stock markets and financial markets news',
                    'palabras_clave': 'stocks,bonds,markets,trading,investment'
                },
                {
                    'nombre': 'Business',
                    'descripcion': 'Corporate and business news',
                    'palabras_clave': 'corporate,business,company,industry,enterprise'
                }
            ]
        },
        {
            'nombre': 'Technology',
            'descripcion': 'Technology and innovation news',
            'subcategories': [
                {
                    'nombre': 'AI & Machine Learning',
                    'descripcion': 'Artificial Intelligence and ML developments',
                    'palabras_clave': 'AI,machine learning,neural networks,deep learning,algorithms'
                },
                {
                    'nombre': 'Cybersecurity',
                    'descripcion': 'Digital security and cyber threats',
                    'palabras_clave': 'security,cyber,hacking,privacy,encryption'
                }
            ]
        }
    ]

    try:
        # Ensure schema exists
        db.session.execute(text('CREATE SCHEMA IF NOT EXISTS app;'))
        db.session.commit()
        
        # Clear existing data first
        logger.info("Clearing existing categories and subcategories...")
        db.session.execute(text('TRUNCATE TABLE app.subcategoria CASCADE;'))
        db.session.execute(text('TRUNCATE TABLE app.categoria CASCADE;'))
        db.session.commit()

        # Reset sequences
        db.session.execute(text('ALTER SEQUENCE app.categoria_categoria_id_seq RESTART WITH 1;'))
        db.session.execute(text('ALTER SEQUENCE app.subcategoria_subcategoria_id_seq RESTART WITH 1;'))
        db.session.commit()

        # Insert new categories and subcategories
        logger.info("Inserting new categories and subcategories...")
        for cat_data in categories_data:
            # Insert category
            result = db.session.execute(
                text("""
                    INSERT INTO app.categoria (nombre, descripcion, created_at, updated_at) 
                    VALUES (:nombre, :descripcion, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
                    RETURNING categoria_id;
                """),
                {
                    'nombre': cat_data['nombre'],
                    'descripcion': cat_data['descripcion']
                }
            )
            categoria_id = result.scalar()
            
            # Insert subcategories
            for subcat_data in cat_data['subcategories']:
                db.session.execute(
                    text("""
                        INSERT INTO app.subcategoria 
                        (categoria_id, nombre, descripcion, palabras_clave, created_at, updated_at) 
                        VALUES (:categoria_id, :nombre, :descripcion, :palabras_clave, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                    """),
                    {
                        'categoria_id': categoria_id,
                        'nombre': subcat_data['nombre'],
                        'descripcion': subcat_data['descripcion'],
                        'palabras_clave': subcat_data['palabras_clave']
                    }
                )

        db.session.commit()
        logger.info("Database seeding completed successfully!")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding database: {str(e)}")
        raise

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_categories(app)
