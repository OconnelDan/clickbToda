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
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 60})

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

# Authentication routes (register, login, logout)
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

        # Modified query to only select required fields
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

        # Base query for articles
        query = db.session.query(
            Articulo.articulo_id.label('id'),
            Articulo.titular,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.paywall,
            Articulo.gpt_opinion,
            Periodico.nombre.label('periodico_nombre'),
            Periodico.logo_url.label('periodico_logo')
        ).join(
            Periodico
        ).join(
            articulo_evento
        ).join(
            Evento
        ).join(
            Subcategoria
        ).filter(
            Articulo.fecha_publicacion.between(start_date, end_date)
        )

        if category_id:
            query = query.filter(Subcategoria.categoria_id == category_id)
        if subcategory_id:
            query = query.filter(Subcategoria.subcategoria_id == subcategory_id)

        articles = query.all()

        return jsonify({
            'categories': [{
                'categoria_id': category_id,
                'subcategories': [{
                    'subcategoria_id': subcategory_id,
                    'events': [{
                        'articles': [{
                            'id': article.id,
                            'titular': article.titular,
                            'url': article.url,
                            'fecha_publicacion': article.fecha_publicacion.isoformat() if article.fecha_publicacion else None,
                            'paywall': article.paywall,
                            'gpt_opinion': article.gpt_opinion,
                            'periodico_nombre': article.periodico_nombre,
                            'periodico_logo': article.periodico_logo
                        } for article in articles]
                    }]
                }]
            }]
        })

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)