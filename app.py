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
from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, ArticuloEvento

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
            
            if not all([nombre, email, password]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')

            if not User.validate_email(email):
                flash('Please enter a valid email address', 'error')
                return render_template('auth/register.html')

            is_valid, password_error = User.validate_password(password)
            if not is_valid:
                flash(password_error, 'error')
                return render_template('auth/register.html')

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered', 'error')
                return render_template('auth/register.html')
            
            new_user = User()
            new_user.nombre = nombre
            new_user.email = email
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
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

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        logger.info(f"Loading index page with time_filter: {time_filter}")

        # First, get all categories with their article counts
        categories_query = db.session.query(
            Categoria,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            ArticuloEvento, ArticuloEvento.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == ArticuloEvento.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id
        ).all()

        categories = []
        for cat, article_count in categories_query:
            categories.append({
                'Categoria': cat,
                'article_count': article_count or 0
            })

        # Sort categories by article count
        categories.sort(key=lambda x: x['article_count'], reverse=True)
        
        # Get initial data for the first category if available
        initial_data = {'categories': []}
        if categories:
            initial_data = get_cached_articles(
                categories[0]['Categoria'].categoria_id, 
                None, 
                time_filter, 
                start_date, 
                end_date
            )
        
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
            ArticuloEvento, ArticuloEvento.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, Articulo.articulo_id == ArticuloEvento.articulo_id
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
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        return jsonify(get_cached_articles(category_id, subcategory_id, time_filter, start_date, end_date))
        
    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache.memoize(timeout=60)
def get_cached_articles(category_id, subcategory_id, time_filter, start_date, end_date):
    try:
        logger.info(f"Fetching articles with params: category_id={category_id}, subcategory_id={subcategory_id}, time_filter={time_filter}")
        
        # First get categories with their article counts
        categories_query = db.session.query(
            Categoria.categoria_id,
            Categoria.nombre,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            ArticuloEvento, ArticuloEvento.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == ArticuloEvento.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre
        )

        if category_id:
            categories_query = categories_query.filter(Categoria.categoria_id == category_id)

        categories = categories_query.all()

        if not categories:
            return {'categories': []}

        result_categories = []
        for cat in categories:
            category_data = {
                'categoria_id': cat.categoria_id,
                'nombre': cat.nombre,
                'article_count': cat.article_count or 0,
                'subcategories': []
            }

            # Get subcategories for this category
            subcategories = db.session.query(
                Subcategoria,
                func.count(distinct(Articulo.articulo_id)).label('article_count')
            ).outerjoin(
                Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
            ).outerjoin(
                ArticuloEvento, ArticuloEvento.evento_id == Evento.evento_id
            ).outerjoin(
                Articulo, and_(
                    Articulo.articulo_id == ArticuloEvento.articulo_id,
                    Articulo.fecha_publicacion.between(start_date, end_date)
                )
            ).filter(
                Subcategoria.categoria_id == cat.categoria_id
            ).group_by(
                Subcategoria.subcategoria_id
            ).all()

            for subcat, subcat_count in subcategories:
                subcategory_data = {
                    'nombre': subcat.nombre,
                    'article_count': subcat_count or 0,
                    'events': []
                }
                category_data['subcategories'].append(subcategory_data)

            result_categories.append(category_data)

        return {'categories': result_categories}
        
    except Exception as e:
        logger.error(f"Error in get_cached_articles: {str(e)}")
        return {'categories': []}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
