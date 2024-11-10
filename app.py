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

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Database configuration
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20

# Cache configuration
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
login_manager.login_message = 'Please log in to access this page.'

# Import models after db initialization
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

        # Get categories with their article counts
        categories = db.session.query(
            Categoria.categoria_id,
            Categoria.nombre,
            Categoria.descripcion,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria, Subcategoria.categoria_id == Categoria.categoria_id
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
        ).order_by(
            desc('article_count')
        ).all()

        categories_list = [{
            'Categoria': {
                'categoria_id': cat.categoria_id,
                'nombre': cat.nombre,
                'descripcion': cat.descripcion
            },
            'article_count': cat.article_count or 0
        } for cat in categories]
        
        logger.info(f"Rendering index with {len(categories_list)} categories")
        
        return render_template('index.html', 
                           categories=categories_list,
                           initial_data={'categories': []},
                           selected_date=datetime.now().date())
                           
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', 
                           categories=[],
                           initial_data={'categories': []},
                           selected_date=datetime.now().date())

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id', type=int)
        if not category_id:
            return jsonify({'error': 'Category ID is required'}), 400

        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        subcategories = db.session.query(
            Subcategoria.subcategoria_id.label('id'),
            Subcategoria.nombre,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).filter(
            Subcategoria.categoria_id == category_id
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
            Subcategoria.subcategoria_id,
            Subcategoria.nombre
        ).order_by(
            desc('article_count')
        ).all()

        result = [{
            'id': sub.id,
            'nombre': sub.nombre,
            'article_count': sub.article_count or 0
        } for sub in subcategories]

        return jsonify(result)

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
            return jsonify({'error': 'Either category_id or subcategory_id is required'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        logger.info(f"Fetching articles with params: category_id={category_id}, subcategory_id={subcategory_id}, time_filter={time_filter}")

        # Base query
        query = db.session.query(
            Categoria,
            Subcategoria,
            Evento,
            Articulo,
            Periodico
        ).join(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).join(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).join(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).join(
            Periodico, Periodico.periodico_id == Articulo.periodico_id
        )

        # Apply filters
        if subcategory_id:
            query = query.filter(Subcategoria.subcategoria_id == subcategory_id)
        elif category_id:
            query = query.filter(Categoria.categoria_id == category_id)

        results = query.all()

        # Process results
        categories_dict = {}
        for cat, sub, evt, art, per in results:
            if cat.categoria_id not in categories_dict:
                categories_dict[cat.categoria_id] = {
                    'categoria_id': cat.categoria_id,
                    'nombre': cat.nombre,
                    'subcategories': {}
                }

            if sub.subcategoria_id not in categories_dict[cat.categoria_id]['subcategories']:
                categories_dict[cat.categoria_id]['subcategories'][sub.subcategoria_id] = {
                    'subcategoria_id': sub.subcategoria_id,
                    'nombre': sub.nombre,
                    'events': []
                }

            # Find existing event or add new one
            subcat_events = categories_dict[cat.categoria_id]['subcategories'][sub.subcategoria_id]['events']
            event = next((e for e in subcat_events if e['evento_id'] == evt.evento_id), None)
            
            if event is None:
                event = {
                    'evento_id': evt.evento_id,
                    'titulo': evt.titulo,
                    'descripcion': evt.descripcion,
                    'fecha_evento': evt.fecha_evento.isoformat() if evt.fecha_evento else None,
                    'articles': []
                }
                subcat_events.append(event)

            # Add article to event
            event['articles'].append({
                'id': art.articulo_id,
                'titular': art.titular,
                'url': art.url,
                'fecha_publicacion': art.fecha_publicacion.isoformat() if art.fecha_publicacion else None,
                'periodico_nombre': per.nombre,
                'periodico_logo': per.logo_url,
                'paywall': art.paywall,
                'gpt_opinion': art.gpt_opinion,
                'gpt_resumen': art.gpt_resumen
            })

        # Convert to final format
        result_categories = []
        for cat_id, category in categories_dict.items():
            category_data = {
                'categoria_id': category['categoria_id'],
                'nombre': category['nombre'],
                'subcategories': []
            }

            for subcat_id, subcategory in category['subcategories'].items():
                category_data['subcategories'].append({
                    'subcategoria_id': subcategory['subcategoria_id'],
                    'nombre': subcategory['nombre'],
                    'events': sorted(subcategory['events'], 
                                  key=lambda x: len(x['articles']), 
                                  reverse=True)
                })

            result_categories.append(category_data)

        return jsonify({'categories': result_categories})

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
