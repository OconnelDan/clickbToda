from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, text, desc, and_, or_, distinct
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

# Initialize extensions
csrf = CSRFProtect(app)
db.init_app(app)
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default timeout
    'CACHE_KEY_PREFIX': 'news_app_'
})

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, articulo_evento

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        logger.info(f"Loading index page with time_filter: {time_filter}")

        # Query categories with article counts
        categories_query = db.session.query(
            Categoria.categoria_id,
            Categoria.nombre,
            Categoria.descripcion,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre,
            Categoria.descripcion
        ).all()

        categories = []
        for category in categories_query:
            categories.append({
                'Categoria': {
                    'categoria_id': category.categoria_id,
                    'nombre': category.nombre,
                    'descripcion': category.descripcion
                },
                'article_count': category.article_count or 0
            })

        # Sort categories by article count
        categories.sort(key=lambda x: x['article_count'], reverse=True)
        
        return render_template('index.html', 
                           categories=categories,
                           initial_data={'categories': categories},
                           selected_date=datetime.now().date())
                           
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', 
                           categories=[],
                           initial_data={'categories': []},
                           selected_date=datetime.now().date())

@app.route('/api/article/<int:article_id>')
@cache.cached(timeout=300)
def get_article_details(article_id):
    try:
        article = db.session.query(
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.subtitulo,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.autor.label('periodista'),
            Articulo.agencia,
            Articulo.paywall,
            Articulo.gpt_resumen,
            Articulo.gpt_opinion,
            Periodico.nombre.label('periodico_nombre'),
            Periodico.logo_url.label('periodico_logo')
        ).join(
            Periodico
        ).filter(
            Articulo.articulo_id == article_id
        ).first()

        if not article:
            return jsonify({'error': 'Article not found'}), 404

        return jsonify({
            'id': article.articulo_id,
            'titular': article.titular,
            'subtitular': article.subtitulo,
            'url': article.url,
            'fecha_publicacion': article.fecha_publicacion.isoformat() if article.fecha_publicacion else None,
            'periodista': article.periodista,
            'agencia': article.agencia,
            'paywall': article.paywall,
            'gpt_resumen': article.gpt_resumen,
            'gpt_opinion': article.gpt_opinion,
            'periodico_nombre': article.periodico_nombre,
            'periodico_logo': article.periodico_logo
        })

    except Exception as e:
        logger.error(f"Error fetching article details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/subcategories')
@cache.cached(timeout=300, query_string=True)
def get_subcategories():
    try:
        category_id = request.args.get('category_id', type=int)
        if not category_id:
            return jsonify({'error': 'Category ID is required'}), 400

        subcategories = db.session.query(
            Subcategoria.subcategoria_id.label('id'),
            Subcategoria.nombre,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, Articulo.articulo_id == articulo_evento.c.articulo_id
        ).filter(
            Subcategoria.categoria_id == category_id
        ).group_by(
            Subcategoria.subcategoria_id,
            Subcategoria.nombre
        ).all()

        return jsonify([{
            'id': s.id,
            'nombre': s.nombre,
            'article_count': s.article_count
        } for s in subcategories])

    except Exception as e:
        logger.error(f"Error fetching subcategories: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        time_filter = request.args.get('time_filter', '24h')
        
        if not category_id and not subcategory_id:
            return jsonify({'error': 'category_id or subcategory_id is required'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Optimized query with proper joins and additional metadata
        events_query = db.session.query(
            Evento.evento_id,
            Evento.titulo.label('event_titulo'),
            Evento.descripcion.label('event_descripcion'),
            Evento.fecha_evento,
            Evento.gpt_sujeto_activo,
            Evento.gpt_sujeto_pasivo,
            Evento.gpt_importancia,
            Evento.gpt_tiene_contexto,
            Evento.gpt_palabras_clave,
            func.count(distinct(Articulo.articulo_id)).label('article_count'),
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.paywall,
            Articulo.gpt_opinion,
            Articulo.gpt_resumen,
            Periodico.nombre.label('periodico_nombre'),
            Periodico.logo_url.label('periodico_logo')
        ).join(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento,
            articulo_evento.c.evento_id == Evento.evento_id
        ).join(
            Articulo,
            and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).join(
            Periodico
        ).group_by(
            Evento.evento_id,
            Articulo.articulo_id,
            Periodico.nombre,
            Periodico.logo_url
        )

        if category_id:
            events_query = events_query.filter(Subcategoria.categoria_id == category_id)
        if subcategory_id:
            events_query = events_query.filter(Subcategoria.subcategoria_id == subcategory_id)

        # Execute query and handle potential errors
        try:
            events_results = events_query.all()
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            return jsonify({'error': 'Database query failed'}), 500

        # Organize results by events with complete metadata
        events_dict = {}
        for result in events_results:
            event_id = result.evento_id
            if event_id not in events_dict:
                events_dict[event_id] = {
                    'titulo': result.event_titulo,
                    'descripcion': result.event_descripcion,
                    'fecha_evento': result.fecha_evento.isoformat() if result.fecha_evento else None,
                    'metadata': {
                        'sujeto_activo': result.gpt_sujeto_activo,
                        'sujeto_pasivo': result.gpt_sujeto_pasivo,
                        'importancia': result.gpt_importancia,
                        'tiene_contexto': result.gpt_tiene_contexto,
                        'palabras_clave': result.gpt_palabras_clave.split(',') if result.gpt_palabras_clave else [],
                    },
                    'article_count': result.article_count,
                    'articles': []
                }
            
            if result.articulo_id:  # Only add article if it exists
                events_dict[event_id]['articles'].append({
                    'id': result.articulo_id,
                    'titular': result.titular,
                    'url': result.url,
                    'fecha_publicacion': result.fecha_publicacion.isoformat() if result.fecha_publicacion else None,
                    'paywall': result.paywall,
                    'gpt_opinion': result.gpt_opinion,
                    'gpt_resumen': result.gpt_resumen,
                    'periodico_nombre': result.periodico_nombre,
                    'periodico_logo': result.periodico_logo
                })

        # Sort events by importance and article count
        sorted_events = sorted(
            events_dict.values(),
            key=lambda x: (x.get('metadata', {}).get('importancia', 0), x.get('article_count', 0)),
            reverse=True
        )

        # Structure the response
        response_data = {
            'categories': [{
                'categoria_id': category_id,
                'subcategories': [{
                    'subcategoria_id': subcategory_id,
                    'events': sorted_events
                }]
            }]
        }

        # Cache the response
        cache_key = f"articles_{category_id}_{subcategory_id}_{time_filter}"
        cache.set(cache_key, response_data, timeout=300)  # Cache for 5 minutes

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
