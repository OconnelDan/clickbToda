from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, AnonymousUserMixin
from sqlalchemy import func, text, desc, and_, or_, distinct, Index
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import logging
import sys
from config import Config
from flask_caching import Cache
from database import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20

cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 60
})

# Initialize SQLAlchemy
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models after db initialization
from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, articulo_evento

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@cache.memoize(timeout=60)
def get_cached_articles(category_id, subcategory_id, time_filter, start_date, end_date):
    try:
        base_query = db.session.query(
            Evento.evento_id,
            Evento.titulo,
            Evento.descripcion,
            Evento.fecha_evento,
            Categoria.categoria_id,
            Categoria.nombre.label('categoria_nombre'),
            Subcategoria.subcategoria_id,
            Subcategoria.nombre.label('subcategoria_nombre'),
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).select_from(Evento)

        base_query = base_query.outerjoin(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            Categoria,
            Subcategoria.categoria_id == Categoria.categoria_id
        ).outerjoin(
            articulo_evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).outerjoin(
            Articulo,
            and_(
                articulo_evento.c.articulo_id == Articulo.articulo_id,
                Articulo.paywall.is_(False) if request.args.get('hide_paywall') else True,
                Articulo.updated_on >= start_date,
                Articulo.updated_on <= end_date
            )
        )

        if category_id:
            base_query = base_query.filter(Categoria.categoria_id == category_id)
        if subcategory_id:
            base_query = base_query.filter(Subcategoria.subcategoria_id == subcategory_id)

        base_query = base_query.group_by(
            Evento.evento_id,
            Categoria.categoria_id,
            Subcategoria.subcategoria_id
        ).order_by(
            desc('article_count')
        )

        events = base_query.all()
        logger.info(f"Retrieved {len(events)} events")

        organized_data = {}
        
        # Get all event IDs first
        event_ids = [event.evento_id for event in events]
        
        # Fetch articles in a single query
        articles_query = db.session.query(
            Articulo,
            Periodico
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).filter(
            Articulo.updated_on.between(start_date, end_date)
        )
        
        if event_ids:
            articles_query = articles_query.join(
                articulo_evento,
                and_(
                    Articulo.articulo_id == articulo_evento.c.articulo_id,
                    articulo_evento.c.evento_id.in_(event_ids)
                )
            )
        
        # Organize articles by event
        articles_by_event = {}
        for article, periodico in articles_query.all():
            for event in article.eventos:
                if event.evento_id not in articles_by_event:
                    articles_by_event[event.evento_id] = []
                articles_by_event[event.evento_id].append((article, periodico))

        for event in events:
            articles = articles_by_event.get(event.evento_id, [])
            
            if not articles:
                continue

            cat_id = event.categoria_id if event.categoria_id else 0
            if cat_id not in organized_data:
                organized_data[cat_id] = {
                    'categoria_id': cat_id,
                    'nombre': event.categoria_nombre if event.categoria_nombre else 'Uncategorized',
                    'subcategories': {},
                    'article_count': 0
                }

            subcat_id = event.subcategoria_id if event.subcategoria_id else 0
            if subcat_id not in organized_data[cat_id]['subcategories']:
                organized_data[cat_id]['subcategories'][subcat_id] = {
                    'subcategoria_id': subcat_id,
                    'nombre': event.subcategoria_nombre if event.subcategoria_nombre else 'Uncategorized',
                    'events': {},
                    'article_count': 0
                }

            organized_data[cat_id]['subcategories'][subcat_id]['events'][event.evento_id] = {
                'evento_id': event.evento_id,
                'titulo': event.titulo,
                'descripcion': event.descripcion,
                'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                'article_count': len(articles),
                'articles': [{
                    'id': article.articulo_id,
                    'titular': article.titular,
                    'paywall': article.paywall,
                    'periodico_logo': periodico.logo_url if periodico else None,
                    'url': article.url,
                    'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None,
                    'gpt_opinion': article.gpt_opinion
                } for article, periodico in articles]
            }
            
            # Update article counts
            organized_data[cat_id]['article_count'] += len(articles)
            organized_data[cat_id]['subcategories'][subcat_id]['article_count'] += len(articles)

        # Sort categories by article count
        sorted_categories = sorted(
            organized_data.values(),
            key=lambda x: x['article_count'],
            reverse=True
        )

        return {
            'categories': [
                {
                    'categoria_id': cat_data['categoria_id'],
                    'nombre': cat_data['nombre'],
                    'article_count': cat_data['article_count'],
                    'subcategories': sorted(
                        [
                            {
                                'subcategoria_id': subcat_data['subcategoria_id'],
                                'nombre': subcat_data['nombre'],
                                'events': sorted(
                                    list(subcat_data['events'].values()),
                                    key=lambda x: x['article_count'],
                                    reverse=True
                                ),
                                'article_count': subcat_data['article_count']
                            }
                            for subcat_data in cat_data['subcategories'].values()
                        ],
                        key=lambda x: x['article_count'],
                        reverse=True
                    )
                }
                for cat_data in sorted_categories
            ]
        }
    except Exception as e:
        logger.error(f"Error in get_cached_articles: {str(e)}")
        raise

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Pre-fetch initial data for faster loading
        initial_data = get_cached_articles(None, None, time_filter, start_date, end_date)
        
        if not initial_data or 'categories' not in initial_data:
            logger.warning("No initial data retrieved")
            return render_template('index.html', 
                               categories=[],
                               initial_data={'categories': []},
                               selected_date=datetime.now().date())

        # Sort categories by article count
        categories = []
        for cat in initial_data.get('categories', []):
            article_count = cat.get('article_count', 0)
            if article_count > 0:  # Only include categories with articles
                categories.append({
                    'Categoria': Categoria(categoria_id=cat['categoria_id'], nombre=cat['nombre']),
                    'article_count': article_count
                })

        # Sort categories by article count in descending order
        categories.sort(key=lambda x: x['article_count'], reverse=True)

        return render_template('index.html', 
                           categories=categories,
                           initial_data=initial_data,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', 
                           categories=[],
                           initial_data={'categories': []},
                           selected_date=datetime.now().date())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)