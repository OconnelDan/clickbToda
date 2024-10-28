from app import app, db
from models import Categoria, Articulo, Periodico, Evento
from datetime import datetime, timedelta

def seed_database():
    with app.app_context():
        try:
            # Create sample categories
            categories_data = [
                {'nombre': 'Politics', 'descripcion': 'Political news and events'},
                {'nombre': 'Technology', 'descripcion': 'Tech news and innovations'},
                {'nombre': 'Sports', 'descripcion': 'Sports coverage and updates'}
            ]
            
            categories = []
            for cat_data in categories_data:
                category = Categoria()
                for key, value in cat_data.items():
                    setattr(category, key, value)
                categories.append(category)
                db.session.add(category)
            db.session.commit()

            # Create sample newspapers
            periodicos_data = [
                {
                    'nombre': 'Daily News',
                    'logo_url': '/static/img/default-newspaper.svg',
                    'pais_iso_code': 'US'
                },
                {
                    'nombre': 'Tech Times',
                    'logo_url': '/static/img/default-newspaper.svg',
                    'pais_iso_code': 'US'
                }
            ]
            
            periodicos = []
            for per_data in periodicos_data:
                periodico = Periodico()
                for key, value in per_data.items():
                    setattr(periodico, key, value)
                periodicos.append(periodico)
                db.session.add(periodico)
            db.session.commit()

            # Create sample events and articles
            today = datetime.now().date()

            for i, category in enumerate(categories):
                # Create event
                event = Evento()
                event.titulo = f'Major {category.nombre} Event'
                event.descripcion = f'Important event in {category.nombre}'
                event.fecha_evento = today
                event.categoria_id = category.categoria_id
                db.session.add(event)
                db.session.commit()

                # Create articles for each event
                for j in range(3):
                    article = Articulo()
                    article.titular = f'Breaking: {category.nombre} News {j+1}'
                    article.subtitular = f'Latest updates on {category.nombre}'
                    article.tipo = 'news'
                    article.fecha_publicacion = today - timedelta(days=j)
                    article.periodico_id = periodicos[j % len(periodicos)].periodico_id
                    article.eventos.append(event)
                    db.session.add(article)
                
                db.session.commit()
            
            print("Database seeded successfully!")
            return True
        except Exception as e:
            print(f"Error seeding database: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    seed_database()
