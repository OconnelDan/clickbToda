from flask import Flask
from models import (
    db, Categoria, Subcategoria, Ideologia, Region, 
    Periodico, Periodista, User, Evento, EventoRegion
)
import logging
from config import Config
from sqlalchemy import text
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def seed_database(app):
    try:
        # Ensure schema exists
        logger.info("Creating schema if not exists...")
        db.session.execute(text('CREATE SCHEMA IF NOT EXISTS app;'))
        db.session.commit()

        # Create ENUM types if they don't exist
        logger.info("Creating ENUM types if not exist...")
        db.session.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentimiento_enum') THEN
                    CREATE TYPE app.sentimiento_enum AS ENUM ('positivo', 'negativo', 'neutral');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agencia_enum') THEN
                    CREATE TYPE app.agencia_enum AS ENUM ('Reuters', 'EFE', 'Otro');
                END IF;
            END $$;
        """))
        db.session.commit()

        # Create all tables
        logger.info("Creating database tables...")
        db.create_all()
        db.session.commit()

        # Check if tables are empty before seeding
        categoria_count = db.session.query(Categoria).count()
        if categoria_count > 0:
            logger.info("Database already seeded, skipping...")
            return

        # Seed ideologias
        logger.info("Seeding ideologias...")
        ideologias_data = [
            {"nombre": "Liberal"},
            {"nombre": "Conservador"},
            {"nombre": "Centrista"},
            {"nombre": "Progresista"},
            {"nombre": "Independiente"}
        ]
        
        for ideologia_data in ideologias_data:
            ideologia = Ideologia(**ideologia_data)
            db.session.add(ideologia)
        db.session.commit()

        # Seed regions
        logger.info("Seeding regions...")
        regions_data = [
            {
                "region_nombre": "North America",
                "pais_iso_code": "US",
                "pais_nombre": "United States"
            },
            {
                "region_nombre": "Europe",
                "pais_iso_code": "GB",
                "pais_nombre": "United Kingdom"
            },
            {
                "region_nombre": "Asia",
                "pais_iso_code": "JP",
                "pais_nombre": "Japan"
            }
        ]
        
        for region_data in regions_data:
            region = Region(**region_data)
            db.session.add(region)
        db.session.commit()

        # Seed categories and subcategories
        logger.info("Seeding categories and subcategories...")
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

        for cat_data in categories_data:
            subcategories = cat_data.pop('subcategories')
            category = Categoria(**cat_data)
            db.session.add(category)
            db.session.flush()  # Get the category_id

            for subcat_data in subcategories:
                subcat_data['categoria_id'] = category.categoria_id
                subcategory = Subcategoria(**subcat_data)
                db.session.add(subcategory)

        # Create admin user
        logger.info("Creating admin user...")
        admin_user = User(
            nombre="Admin",
            email="admin@example.com",
            is_admin=True,
            es_suscriptor=True,
            status="active"
        )
        admin_user.set_password("Admin123!")
        db.session.add(admin_user)

        db.session.commit()
        logger.info("Database seeding completed successfully!")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding database: {str(e)}")
        raise

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_database(app)
