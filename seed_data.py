from app import app, db
from models import Categoria, Articulo, Periodico, Evento
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_data():
    """Verify that data was inserted correctly"""
    with app.app_context():
        categories = Categoria.query.all()
        events = Evento.query.all()
        articles = Articulo.query.all()
        periodicos = Periodico.query.all()
        
        logger.info(f"Verification results:")
        logger.info(f"- Categories: {len(categories)}")
        logger.info(f"- Events: {len(events)}")
        logger.info(f"- Articles: {len(articles)}")
        logger.info(f"- Newspapers: {len(periodicos)}")
        
        return len(categories) > 0 and len(events) > 0 and len(articles) > 0

def seed_database():
    """Seed the database with sample data"""
    with app.app_context():
        try:
            logger.info("Starting database seeding process...")

            # Create sample categories with subcategories
            categories_data = [
                {
                    'nombre': 'Politics',
                    'descripcion': 'Political news and events',
                    'subnombre': 'National Politics',
                    'subdescripcion': 'Coverage of national political events and policies'
                },
                {
                    'nombre': 'Politics',
                    'descripcion': 'Political news and events',
                    'subnombre': 'International Relations',
                    'subdescripcion': 'Coverage of international diplomatic relations'
                },
                {
                    'nombre': 'Technology',
                    'descripcion': 'Tech news and innovations',
                    'subnombre': 'AI & Machine Learning',
                    'subdescripcion': 'Coverage of artificial intelligence advancements'
                },
                {
                    'nombre': 'Technology',
                    'descripcion': 'Tech news and innovations',
                    'subnombre': 'Cybersecurity',
                    'subdescripcion': 'News about digital security and cyber threats'
                },
                {
                    'nombre': 'Business',
                    'descripcion': 'Business and economic news',
                    'subnombre': 'Markets',
                    'subdescripcion': 'Stock market and financial news'
                },
                {
                    'nombre': 'Business',
                    'descripcion': 'Business and economic news',
                    'subnombre': 'Startups',
                    'subdescripcion': 'News about emerging companies and innovations'
                }
            ]
            
            logger.info("Creating categories...")
            categories = []
            for cat_data in categories_data:
                category = Categoria()
                for key, value in cat_data.items():
                    setattr(category, key, value)
                categories.append(category)
                db.session.add(category)
            db.session.commit()
            logger.info(f"Created {len(categories)} categories")

            # Create sample newspapers with proper logos
            periodicos_data = [
                {
                    'nombre': 'The Daily Chronicle',
                    'logo_url': 'https://placehold.co/100x50/png?text=TDC',
                    'pais_iso_code': 'US',
                    'idioma': 'en',
                    'tipo': 'newspaper'
                },
                {
                    'nombre': 'Tech Insider',
                    'logo_url': 'https://placehold.co/100x50/png?text=TI',
                    'pais_iso_code': 'US',
                    'idioma': 'en',
                    'tipo': 'digital'
                },
                {
                    'nombre': 'Business Today',
                    'logo_url': 'https://placehold.co/100x50/png?text=BT',
                    'pais_iso_code': 'UK',
                    'idioma': 'en',
                    'tipo': 'newspaper'
                },
                {
                    'nombre': 'Global News Network',
                    'logo_url': 'https://placehold.co/100x50/png?text=GNN',
                    'pais_iso_code': 'US',
                    'idioma': 'en',
                    'tipo': 'digital'
                }
            ]
            
            logger.info("Creating newspapers...")
            periodicos = []
            for per_data in periodicos_data:
                periodico = Periodico()
                for key, value in per_data.items():
                    setattr(periodico, key, value)
                periodicos.append(periodico)
                db.session.add(periodico)
            db.session.commit()
            logger.info(f"Created {len(periodicos)} newspapers")

            # Create sample events and articles
            today = datetime.now().date()
            
            logger.info("Creating events and articles...")
            events_created = 0
            articles_created = 0

            for category in categories:
                # Create multiple events per category
                for i in range(3):  # 3 events per category
                    event = Evento()
                    event.titulo = f'Major {category.subnombre} Event {i+1}'
                    event.descripcion = f'Important development in {category.subnombre}: Event {i+1}'
                    event.fecha_evento = today - timedelta(days=i)
                    event.categoria_id = category.categoria_id
                    db.session.add(event)
                    events_created += 1

                    try:
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error creating event: {str(e)}")
                        db.session.rollback()
                        continue

                    # Create multiple articles for each event from different newspapers
                    for j, periodico in enumerate(periodicos):
                        article = Articulo()
                        article.titular = f'Breaking: {category.subnombre} - {event.titulo}'
                        article.subtitular = f'Latest updates on {event.titulo}'
                        article.tipo = 'news'
                        article.fecha_publicacion = today - timedelta(days=j)
                        article.periodico_id = periodico.periodico_id
                        article.paywall = j % 2 == 0  # Alternate between paywall and free articles
                        article.eventos.append(event)
                        db.session.add(article)
                        articles_created += 1

                    try:
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error creating articles: {str(e)}")
                        db.session.rollback()
                        continue

            logger.info(f"Created {events_created} events")
            logger.info(f"Created {articles_created} articles")

            # Verify the data
            if verify_data():
                logger.info("Database seeded successfully!")
                return True
            else:
                logger.error("Data verification failed")
                return False

        except Exception as e:
            logger.error(f"Error seeding database: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    # Make sure database is initialized before seeding
    from app import init_db
    if init_db():
        seed_database()
    else:
        logger.error("Failed to initialize database before seeding")
