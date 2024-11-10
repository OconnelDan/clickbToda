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
        user = User.query.get(int(user_id))
        if user and user.is_active:
            return user
        return None
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            email = request.form.get('email')
            password = request.form.get('password')
            
            # Basic validation
            if not all([nombre, email, password]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')

            # Email validation
            if not User.validate_email(email):
                flash('Please enter a valid email address', 'error')
                return render_template('auth/register.html')

            # Password validation
            is_valid, password_error = User.validate_password(password)
            if not is_valid:
                flash(password_error, 'error')
                return render_template('auth/register.html')

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered', 'error')
                return render_template('auth/register.html')
            
            # Create new user
            new_user = User()
            new_user.nombre = nombre
            new_user.email = email
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log the user in
            login_user(new_user)
            logger.info(f"New user registered: {email}")
            flash('Registration successful! Welcome to our platform.', 'success')
            
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
            
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Email and password are required', 'error')
                return render_template('auth/login.html')
                
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user, remember=True)
                logger.info(f"User {email} logged in successfully")
                flash('Login successful!', 'success')
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('index')
                return redirect(next_page)
            
            flash('Invalid email or password', 'error')
            logger.warning(f"Failed login attempt for email: {email}")
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

# Restore all previously existing functions: get_subcategories, get_cached_articles, index route, etc.
@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        logger.info(f"Loading index page with time_filter: {time_filter}")

        initial_data = get_cached_articles(None, None, time_filter, start_date, end_date)
        
        if not initial_data or 'categories' not in initial_data:
            logger.warning("No initial data available")
            return render_template('index.html',
                               categories=[],
                               initial_data={'categories': []},
                               selected_date=datetime.now().date())

        categories = []
        for cat in initial_data.get('categories', []):
            article_count = cat.get('article_count', 0)
            if article_count > 0:
                categories.append({
                    'Categoria': Categoria(categoria_id=cat['categoria_id'], nombre=cat['nombre']),
                    'article_count': article_count
                })

        categories.sort(key=lambda x: x['article_count'], reverse=True)
        
        logger.info(f"Rendering index with {len(categories)} categories")
        
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

@app.route('/api/subcategories')
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

@cache.memoize(timeout=60)
def get_cached_articles(category_id, subcategory_id, time_filter, start_date, end_date):
    try:
        logger.info(f"Fetching articles with params: category_id={category_id}, subcategory_id={subcategory_id}, time_filter={time_filter}")
        
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

        # Join tables with explicit conditions
        base_query = base_query.outerjoin(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            Categoria,
            Subcategoria.categoria_id == Categoria.categoria_id
        ).outerjoin(
            articulo_evento,
            articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo,
            and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date),
                Articulo.paywall.is_(False) if request.args.get('hide_paywall') else True
            )
        )

        # Apply filters
        if category_id:
            base_query = base_query.filter(Categoria.categoria_id == category_id)
        if subcategory_id:
            base_query = base_query.filter(Subcategoria.subcategoria_id == subcategory_id)

        # Group and order
        base_query = base_query.group_by(
            Evento.evento_id,
            Categoria.categoria_id,
            Subcategoria.subcategoria_id
        ).order_by(desc('article_count'))

        events = base_query.all()

        organized_data = {}
        event_ids = [event.evento_id for event in events]
        
        if not event_ids:
            return {'categories': []}

        # Fetch articles in a single query
        articles_query = db.session.query(
            Articulo,
            Periodico
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).join(
            articulo_evento,
            Articulo.articulo_id == articulo_evento.c.articulo_id
        ).filter(
            articulo_evento.c.evento_id.in_(event_ids),
            Articulo.fecha_publicacion.between(start_date, end_date)
        )

        articles_by_event = {}
        for article, periodico in articles_query.all():
            if article.evento_id not in articles_by_event:
                articles_by_event[article.evento_id] = []
            articles_by_event[article.evento_id].append((article, periodico))

        # Process events and organize data
        for event in events:
            articles = articles_by_event.get(event.evento_id, [])
            
            cat_id = event.categoria_id
            subcat_id = event.subcategoria_id
            
            if cat_id not in organized_data:
                organized_data[cat_id] = {
                    'categoria_id': cat_id,
                    'nombre': event.categoria_nombre,
                    'article_count': 0,
                    'subcategories': {}
                }
            
            if subcat_id not in organized_data[cat_id]['subcategories']:
                organized_data[cat_id]['subcategories'][subcat_id] = {
                    'subcategoria_id': subcat_id,
                    'nombre': event.subcategoria_nombre,
                    'article_count': 0,
                    'events': []
                }
            
            organized_data[cat_id]['subcategories'][subcat_id]['events'].append({
                'evento_id': event.evento_id,
                'titulo': event.titulo,
                'descripcion': event.descripcion,
                'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                'articles': [{
                    'id': article.articulo_id,
                    'titular': article.titular,
                    'url': article.url,
                    'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None,
                    'periodico_nombre': periodico.nombre,
                    'periodico_logo': periodico.logo_url,
                    'paywall': article.paywall,
                    'gpt_opinion': article.gpt_opinion,
                    'gpt_resumen': article.gpt_resumen
                } for article, periodico in articles]
            })
            
            organized_data[cat_id]['article_count'] += len(articles)
            organized_data[cat_id]['subcategories'][subcat_id]['article_count'] += len(articles)

        sorted_categories = sorted(
            organized_data.values(),
            key=lambda x: x['article_count'],
            reverse=True
        )

        for cat in sorted_categories:
            cat['subcategories'] = sorted(
                cat['subcategories'].values(),
                key=lambda x: x['article_count'],
                reverse=True
            )

        return {
            'categories': sorted_categories
        }
        
    except Exception as e:
        logger.error(f"Error in get_cached_articles: {str(e)}")
        return {'categories': []}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)