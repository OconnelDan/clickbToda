from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text, desc, and_, distinct
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
        # Get unique categories with their event and article counts
        categories = db.session.query(
            Categoria,
            func.count(distinct(Evento.evento_id)).label('event_count'),
            func.count(distinct(articulo_evento.c.articulo_id)).label('article_count')
        ).outerjoin(
            Evento,
            Categoria.categoria_id == Evento.categoria_id
        ).outerjoin(
            articulo_evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre
        ).order_by(
            func.count(distinct(articulo_evento.c.articulo_id)).desc()
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
        
        subcategories = db.session.query(
            Categoria.categoria_id,
            Categoria.subnombre
        ).filter(
            Categoria.categoria_id == category_id,
            Categoria.subnombre.isnot(None)
        ).all()
        
        return jsonify([{
            'id': subcat.categoria_id,
            'subnombre': subcat.subnombre
        } for subcat in subcategories])
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id')
        search_query = request.args.get('q')
        
        # Subquery to count articles per event
        article_count_subquery = db.session.query(
            articulo_evento.c.evento_id,
            func.count(articulo_evento.c.articulo_id).label('article_count')
        ).group_by(articulo_evento.c.evento_id).subquery()
        
        # Base query with article count
        base_query = db.session.query(
            Articulo, Evento, Categoria, Region, Periodico,
            article_count_subquery.c.article_count
        ).select_from(Articulo)\
        .join(articulo_evento, Articulo.articulo_id == articulo_evento.c.articulo_id)\
        .join(Evento, articulo_evento.c.evento_id == Evento.evento_id)\
        .join(Categoria, Evento.categoria_id == Categoria.categoria_id)\
        .join(evento_region, Evento.evento_id == evento_region.c.evento_id, isouter=True)\
        .join(Region, evento_region.c.region_id == Region.region_id, isouter=True)\
        .join(Periodico, Articulo.periodico_id == Periodico.periodico_id)\
        .join(article_count_subquery, Evento.evento_id == article_count_subquery.c.evento_id)

        # Apply filters
        if category_id:
            base_query = base_query.filter(Categoria.categoria_id == category_id)
        if search_query:
            base_query = base_query.filter(Articulo.titular.ilike(f'%{search_query}%'))

        # Execute query
        results = base_query.order_by(
            Categoria.nombre,
            Categoria.subnombre,
            article_count_subquery.c.article_count.desc(),
            desc(Evento.fecha_evento),
            desc(Articulo.fecha_publicacion)
        ).all()

        logger.info(f"Retrieved {len(results)} articles")

        # Organize results
        organized_data = {}
        for article, event, category, region, periodico, article_count in results:
            if not category:
                continue
                
            if category.categoria_id not in organized_data:
                organized_data[category.categoria_id] = {
                    'categoria_id': category.categoria_id,
                    'nombre': category.nombre,
                    'descripcion': category.descripcion,
                    'subcategories': {}
                }

            subcategory_key = category.subnombre or 'general'
            if subcategory_key not in organized_data[category.categoria_id]['subcategories']:
                organized_data[category.categoria_id]['subcategories'][subcategory_key] = {
                    'subnombre': category.subnombre,
                    'subdescripcion': category.subdescripcion,
                    'events': {}
                }

            if event:
                if event.evento_id not in organized_data[category.categoria_id]['subcategories'][subcategory_key]['events']:
                    organized_data[category.categoria_id]['subcategories'][subcategory_key]['events'][event.evento_id] = {
                        'evento_id': event.evento_id,
                        'titulo': event.titulo,
                        'descripcion': event.descripcion,
                        'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                        'article_count': article_count,
                        'articles': []
                    }

                organized_data[category.categoria_id]['subcategories'][subcategory_key]['events'][event.evento_id]['articles'].append({
                    'id': article.articulo_id,
                    'titular': article.titular,
                    'paywall': article.paywall,
                    'periodico_logo': periodico.logo_url if periodico else None,
                    'url': article.url,
                    'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None
                })

        # Format response
        response_data = {
            'categories': [
                {
                    'categoria_id': cat_data['categoria_id'],
                    'nombre': cat_data['nombre'],
                    'descripcion': cat_data['descripcion'],
                    'subcategories': [
                        {
                            'subnombre': subcat_data['subnombre'],
                            'subdescripcion': subcat_data['subdescripcion'],
                            'events': sorted([
                                {
                                    **event_data,
                                    'articles': sorted(event_data['articles'], 
                                                    key=lambda x: x['fecha_publicacion'] or '', 
                                                    reverse=True)
                                }
                                for event_id, event_data in subcat_data['events'].items()
                            ], key=lambda x: (x['article_count'] or 0, x['fecha_evento'] or ''), reverse=True)
                        }
                        for subcat_key, subcat_data in cat_data['subcategories'].items()
                    ]
                }
                for cat_id, cat_data in organized_data.items()
            ]
        }

        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return jsonify({
            'error': 'An error occurred while fetching articles',
            'details': str(e)
        }), 500

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
            
        flash('Invalid email or password')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
            
        user = User(nombre=nombre, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
        
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
