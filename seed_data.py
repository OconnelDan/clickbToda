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
        # Clear existing data
        logger.info("Clearing existing categories and subcategories...")
        db.session.execute(text('TRUNCATE TABLE subcategoria CASCADE;'))
        db.session.execute(text('TRUNCATE TABLE categoria CASCADE;'))
        db.session.commit()

        # Insert new categories and subcategories
        logger.info("Inserting new categories and subcategories...")
        for cat_data in categories_data:
            # Create new category
            category = Categoria()
            category.nombre = cat_data['nombre']
            category.descripcion = cat_data['descripcion']
            
            db.session.add(category)
            db.session.flush()  # Get the ID of the inserted category

            # Create subcategories for this category
            for subcat_data in cat_data['subcategories']:
                subcategory = Subcategoria()
                subcategory.categoria_id = category.categoria_id
                subcategory.nombre = subcat_data['nombre']
                subcategory.descripcion = subcat_data['descripcion']
                subcategory.palabras_clave = subcat_data['palabras_clave']
                db.session.add(subcategory)

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
