from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text, desc, distinct
from datetime import datetime
import logging
from config import Config
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy with engine options
try:
    db = SQLAlchemy(app)
    # Test database connection
    with app.app_context():
        db.engine.connect()
    logger.info("Database connection successful")
except Exception as e:
    logger.error(f"Database connection failed: {str(e)}")
    raise

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from models import User, Articulo, Evento, Categoria, Periodico, articulo_evento, evento_region, Region

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    try:
        # Get unique categories with their event counts
        categories = db.session.query(
            Categoria,
            func.count(distinct(Evento.evento_id)).label('event_count')
        ).outerjoin(
            Evento,
            Categoria.categoria_id == Evento.categoria_id
        ).group_by(
            Categoria.nombre  # Group by name only to get unique categories
        ).order_by(
            func.count(distinct(Evento.evento_id)).desc()
        ).all()
        
        logger.info(f"Retrieved {len(categories)} categories")
        return render_template('index.html', 
                           categories=categories,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', categories=[], selected_date=datetime.now().date())

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id')
        if not category_id:
            return jsonify([])
        
        # Get the category name for the selected category
        category = db.session.query(Categoria.nombre).filter(
            Categoria.categoria_id == category_id
        ).first()
        
        if not category:
            return jsonify([])
        
        # Get all subcategories for this category name
        subcategories = db.session.query(
            Categoria.categoria_id,
            Categoria.subnombre
        ).filter(
            Categoria.nombre == category.nombre,
            Categoria.subnombre.isnot(None)
        ).distinct(
            Categoria.subnombre
        ).all()
        
        return jsonify([{
            'id': subcat.categoria_id,
            'subnombre': subcat.subnombre
        } for subcat in subcategories if subcat.subnombre])
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id')
        subcategory_id = request.args.get('subcategory_id')
        
        # Base query
        query = db.session.query(
            Articulo, Evento, Categoria, Periodico
        ).join(
            articulo_evento,
            Articulo.articulo_id == articulo_evento.c.articulo_id
        ).join(
            Evento,
            articulo_evento.c.evento_id == Evento.evento_id
        ).join(
            Categoria,
            Evento.categoria_id == Categoria.categoria_id
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        )
        
        if category_id:
            # Get category name first
            category = db.session.query(Categoria.nombre).filter(
                Categoria.categoria_id == category_id
            ).first()
            
            if category:
                # Filter by category name to get all related events
                query = query.filter(Categoria.nombre == category.nombre)
                
                if subcategory_id:
                    query = query.filter(Categoria.categoria_id == subcategory_id)
        
        # Get results
        results = query.all()
        logger.info(f"Retrieved {len(results)} articles")
        
        # Organize results by category and subcategory
        organized_data = {}
        for article, event, category, periodico in results:
            if category.nombre not in organized_data:
                organized_data[category.nombre] = {
                    'categoria_id': category.categoria_id,
                    'nombre': category.nombre,
                    'subcategories': {}
                }
            
            subcat_key = category.subnombre or 'general'
            if subcat_key not in organized_data[category.nombre]['subcategories']:
                organized_data[category.nombre]['subcategories'][subcat_key] = {
                    'subnombre': category.subnombre,
                    'events': {}
                }
            
            if event.evento_id not in organized_data[category.nombre]['subcategories'][subcat_key]['events']:
                organized_data[category.nombre]['subcategories'][subcat_key]['events'][event.evento_id] = {
                    'evento_id': event.evento_id,
                    'titulo': event.titulo,
                    'descripcion': event.descripcion,
                    'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                    'articles': []
                }
            
            organized_data[category.nombre]['subcategories'][subcat_key]['events'][event.evento_id]['articles'].append({
                'titular': article.titular,
                'paywall': article.paywall,
                'periodico_logo': periodico.logo_url,
                'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None
            })
        
        # Format final response
        response_data = {
            'categories': [
                {
                    'categoria_id': cat_data['categoria_id'],
                    'nombre': cat_data['nombre'],
                    'subcategories': [
                        {
                            'subnombre': subcat_data['subnombre'],
                            'events': list(subcat_data['events'].values())
                        }
                        for subcat_key, subcat_data in cat_data['subcategories'].items()
                    ]
                }
                for cat_name, cat_data in organized_data.items()
            ]
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': str(e)}), 500
