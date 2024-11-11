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
from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, articulo_evento

# Configure logging
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
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 60})

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not nombre or not email or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('register'))
        
        # Validate email format
        if not User.validate_email(email):
            flash('Invalid email format', 'error')
            return redirect(url_for('register'))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        # Validate password
        is_valid, message = User.validate_password(password)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('register'))
        
        # Create new user
        try:
            user = User()
            user.nombre = nombre
            user.email = email
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating user account', 'error')
            return redirect(url_for('register'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '72h')
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
                Articulo.updated_on.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre,
            Categoria.descripcion
        ).order_by(
            desc('article_count'),
            Categoria.nombre
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
        
        return render_template('index.html', 
                           categories=categories,
                           initial_data={'categories': categories},
                           selected_date=datetime.now().date(),
                           time_filter=time_filter)
                           
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return render_template('index.html', 
                           categories=[],
                           initial_data={'categories': []},
                           selected_date=datetime.now().date(),
                           time_filter=time_filter)

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        time_filter = request.args.get('time_filter', '72h')
        
        if not category_id and not subcategory_id:
            logger.error("Missing required parameters: category_id or subcategory_id")
            return jsonify({'error': 'category_id or subcategory_id is required'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        # Get category and subcategory info with specific columns
        category_info = None
        subcategory_info = None
        
        if category_id:
            category_info = db.session.query(
                Categoria.categoria_id,
                Categoria.nombre,
                Categoria.descripcion
            ).filter(
                Categoria.categoria_id == category_id
            ).first()
            
            if not category_info:
                return jsonify({'error': 'Category not found'}), 404
            
        if subcategory_id:
            subcategory_info = db.session.query(
                Subcategoria.subcategoria_id,
                Subcategoria.nombre,
                Subcategoria.descripcion
            ).filter(
                Subcategoria.subcategoria_id == subcategory_id
            ).first()
            
            if not subcategory_info:
                return jsonify({'error': 'Subcategory not found'}), 404

        # Query events with related articles
        events_query = db.session.query(
            Evento.evento_id,
            Evento.titulo,
            Evento.descripcion,
            Evento.fecha_evento,
            Evento.gpt_sujeto_activo,
            Evento.gpt_sujeto_pasivo,
            Evento.gpt_importancia,
            Evento.gpt_tiene_contexto,
            Evento.gpt_palabras_clave,
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.url,
            Articulo.updated_on.label(fecha_publicacion),
            Articulo.paywall,
            Articulo.gpt_opinion,
            Periodico.nombre.label('periodico_nombre'),
            Periodico.logo_url.label('periodico_logo')
        ).join(
            Subcategoria, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).join(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.updated_on.between(start_date, end_date)
            )
        ).join(
            Periodico, Periodico.periodico_id == Articulo.periodico_id
        )

        # Apply filters
        if category_id:
            events_query = events_query.filter(Subcategoria.categoria_id == category_id)
        if subcategory_id:
            events_query = events_query.filter(Subcategoria.subcategoria_id == subcategory_id)

        # Execute query
        events_results = events_query.order_by(
            desc(Evento.fecha_evento),
            desc(Articulo.updated_on)
        ).all()

        # Log newspaper information
        logger.info(f"Newspapers in results: {set(r.periodico_nombre for r in events_results)}")
        newspaper_count = len(set(r.periodico_nombre for r in events_results))
        logger.info(f"Total number of distinct newspapers: {newspaper_count}")

        # Process results
        events_dict = {}
        for result in events_results:
            evento_id = result.evento_id
            if evento_id not in events_dict:
                events_dict[evento_id] = {
                    'titulo': result.titulo,
                    'descripcion': result.descripcion,
                    'fecha_evento': result.fecha_evento.isoformat() if result.fecha_evento else None,
                    'gpt_sujeto_activo': result.gpt_sujeto_activo,
                    'gpt_sujeto_pasivo': result.gpt_sujeto_pasivo,
                    'gpt_importancia': result.gpt_importancia,
                    'gpt_tiene_contexto': result.gpt_tiene_contexto,
                    'gpt_palabras_clave': result.gpt_palabras_clave,
                    'article_count': 0,
                    'articles': []
                }

            article_exists = any(a['id'] == result.articulo_id for a in events_dict[evento_id]['articles'])
            if not article_exists:
                events_dict[evento_id]['articles'].append({
                    'id': result.articulo_id,
                    'titular': result.titular,
                    'url': result.url,
                    'fecha_publicacion': result.fecha_publicacion.isoformat() if result.fecha_publicacion else None,
                    'paywall': result.paywall,
                    'gpt_opinion': result.gpt_opinion,
                    'periodico_nombre': result.periodico_nombre,
                    'periodico_logo': result.periodico_logo
                })
                events_dict[evento_id]['article_count'] += 1

        # Sort events by article count and date
        sorted_events = sorted(
            events_dict.values(),
            key=lambda x: (-x['article_count'], x['fecha_evento'] or '1900-01-01')
        )

        response_data = {
            'categories': [{
                'nombre': category_info.nombre if category_info else 'All Categories',
                'categoria_id': category_id,
                'subcategories': [{
                    'nombre': subcategory_info.nombre if subcategory_info else 'All Subcategories',
                    'subcategoria_id': subcategory_id,
                    'events': sorted_events
                }]
            }]
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id', type=int)
        time_filter = request.args.get('time_filter', '72h')
        
        if not category_id:
            return jsonify({'error': 'Category ID is required'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        subcategories = db.session.query(
            Subcategoria.subcategoria_id.label('id'),
            Subcategoria.nombre,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).filter(
            Subcategoria.categoria_id == category_id
        ).group_by(
            Subcategoria.subcategoria_id,
            Subcategoria.nombre
        ).order_by(
            desc('article_count'),
            Subcategoria.nombre
        ).all()

        return jsonify([{
            'id': s.id,
            'nombre': s.nombre,
            'article_count': s.article_count or 0
        } for s in subcategories])

    except Exception as e:
        logger.error(f"Error fetching subcategories: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/article/<int:article_id>')
def get_article(article_id):
    try:
        if not article_id:
            return jsonify({'error': 'Article ID is required'}), 400

        article = db.session.query(
            Articulo.articulo_id.label('id'),
            Articulo.titular,
            Articulo.subtitulo.label('subtitular'),
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
            Periodico, text('app.periodico.periodico_id = app.articulo.periodico_id')
        ).filter(
            Articulo.articulo_id == article_id
        ).first()

        if not article:
            logger.error(f"Article not found with ID: {article_id}")
            return jsonify({'error': 'Article not found'}), 404

        # Convert to dict for JSON serialization
        article_data = {
            'id': article.id,
            'titular': article.titular,
            'subtitular': article.subtitular,
            'url': article.url,
            'fecha_publicacion': article.fecha_publicacion.isoformat() if article.updated_on else None,
            'periodista': str(article.periodista) if article.periodista else None,
            'agencia': str(article.agencia) if article.agencia else None,
            'paywall': article.paywall,
            'gpt_resumen': article.gpt_resumen,
            'gpt_opinion': article.gpt_opinion,
            'periodico_nombre': article.periodico_nombre,
            'periodico_logo': article.periodico_logo
        }

        return jsonify(article_data)

    except Exception as e:
        logger.error(f"Error fetching article details for ID {article_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch article details', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)