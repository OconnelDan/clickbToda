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

# Authentication routes remain unchanged
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
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
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
        
        logger.info(f"Rendering index with {len(categories)} categories")
        
        return render_template('index.html', 
                           categories=categories,
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
        # Get query parameters
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        time_filter = request.args.get('time_filter', '24h')
        
        if not category_id and not subcategory_id:
            return jsonify({'error': 'Either category_id or subcategory_id is required'}), 400

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        logger.info(f"Fetching articles with params: category_id={category_id}, subcategory_id={subcategory_id}, time_filter={time_filter}")

        # Base query for categories with explicit join conditions
        categories_query = db.session.query(
            Categoria.categoria_id,
            Categoria.nombre,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria, 
            Subcategoria.categoria_id == Categoria.categoria_id
        )

        # Apply filters based on parameters
        if subcategory_id:
            categories_query = categories_query.filter(Subcategoria.subcategoria_id == subcategory_id)
        elif category_id:
            categories_query = categories_query.filter(Categoria.categoria_id == category_id)

        # Continue with the rest of the joins
        categories_query = categories_query.outerjoin(
            Evento, 
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            articulo_evento, 
            articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre
        )

        categories = categories_query.all()

        if not categories:
            return jsonify({'categories': []})

        # Prepare response data
        result_categories = []
        for cat in categories:
            # Get subcategories for this category with explicit join conditions
            subcategories = db.session.query(
                Subcategoria,
                func.count(distinct(Articulo.articulo_id)).label('article_count')
            ).outerjoin(
                Evento,
                Evento.subcategoria_id == Subcategoria.subcategoria_id
            ).outerjoin(
                articulo_evento,
                articulo_evento.c.evento_id == Evento.evento_id
            ).outerjoin(
                Articulo, and_(
                    Articulo.articulo_id == articulo_evento.c.articulo_id,
                    Articulo.fecha_publicacion.between(start_date, end_date)
                )
            ).filter(
                Subcategoria.categoria_id == cat.categoria_id
            )

            if subcategory_id:
                subcategories = subcategories.filter(Subcategoria.subcategoria_id == subcategory_id)

            subcategories = subcategories.group_by(
                Subcategoria.subcategoria_id,
                Subcategoria.nombre,
                Subcategoria.descripcion
            ).all()

            category_data = {
                'categoria_id': cat.categoria_id,
                'nombre': cat.nombre,
                'article_count': cat.article_count or 0,
                'subcategories': []
            }

            # Add subcategories data
            for subcat, subcat_count in subcategories:
                # Get events for this subcategory with explicit join conditions
                events = db.session.query(
                    Evento,
                    func.array_agg(distinct(Articulo.articulo_id)).label('article_ids')
                ).outerjoin(
                    articulo_evento,
                    articulo_evento.c.evento_id == Evento.evento_id
                ).outerjoin(
                    Articulo, and_(
                        Articulo.articulo_id == articulo_evento.c.articulo_id,
                        Articulo.fecha_publicacion.between(start_date, end_date)
                    )
                ).filter(
                    Evento.subcategoria_id == subcat.subcategoria_id
                ).group_by(
                    Evento.evento_id,
                    Evento.titulo,
                    Evento.descripcion,
                    Evento.fecha_evento
                ).all()

                subcategory_data = {
                    'subcategoria_id': subcat.subcategoria_id,
                    'nombre': subcat.nombre,
                    'article_count': subcat_count or 0,
                    'events': []
                }

                # Add events data
                for event, article_ids in events:
                    if article_ids[0] is not None:  # Check if there are articles
                        # Get articles for this event with explicit join conditions
                        articles = db.session.query(
                            Articulo,
                            Periodico
                        ).join(
                            Periodico,
                            Periodico.periodico_id == Articulo.periodico_id
                        ).filter(
                            Articulo.articulo_id.in_(article_ids)
                        ).all()

                        event_data = {
                            'evento_id': event.evento_id,
                            'titulo': event.titulo,
                            'descripcion': event.descripcion,
                            'fecha_evento': event.fecha_evento.isoformat() if event.fecha_evento else None,
                            'articles': [{
                                'id': article.articulo_id,
                                'titular': article.titular,
                                'url': article.url,
                                'fecha_publicacion': article.fecha_publicacion.isoformat() if article.fecha_publicacion else None,
                                'periodico_nombre': periodico.nombre,
                                'periodico_logo': periodico.logo_url,
                                'paywall': article.paywall,
                                'gpt_opinion': article.gpt_opinion,
                                'gpt_resumen': article.gpt_resumen
                            } for article, periodico in articles]
                        }
                        subcategory_data['events'].append(event_data)

                category_data['subcategories'].append(subcategory_data)

            result_categories.append(category_data)

        return jsonify({'categories': result_categories})

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
