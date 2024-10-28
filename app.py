from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text
from datetime import datetime
import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from models import User, Articulo, Evento, Categoria, Periodico, articulo_evento

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        try:
            # Drop schema if exists
            logger.info("Dropping schema if exists...")
            db.session.execute(text('DROP SCHEMA IF EXISTS app CASCADE'))
            db.session.commit()
            
            # Create schema
            logger.info("Creating schema 'app'...")
            db.session.execute(text('CREATE SCHEMA app'))
            db.session.commit()
            
            # Create enum types
            logger.info("Creating custom enum types...")
            db.session.execute(text("""
                CREATE TYPE app.agencia_enum AS ENUM ('Reuters', 'EFE', 'Otro')
            """))
            db.session.execute(text("""
                CREATE TYPE app.sentimiento_enum AS ENUM ('positivo', 'negativo', 'neutral')
            """))
            db.session.commit()

            # Create tables using SQLAlchemy models
            logger.info("Creating tables through SQLAlchemy models...")
            db.create_all()
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during database initialization: {str(e)}")
            return False

@app.route('/')
def index():
    # Get categories with their event counts
    categories = db.session.query(
        Categoria,
        func.count(Evento.evento_id).label('event_count')
    ).outerjoin(
        Evento,
        Categoria.categoria_id == Evento.categoria_id
    ).group_by(
        Categoria.categoria_id,
        Categoria.nombre
    ).order_by(
        func.count(Evento.evento_id).desc()
    ).all()
    
    return render_template('index.html', 
                         categories=categories,
                         selected_date=datetime.now().date())

@app.route('/api/subcategories')
def get_subcategories():
    category_id = request.args.get('category_id')
    if not category_id:
        return jsonify([])
        
    category = Categoria.query.get(category_id)
    if not category or not category.subnombre:
        return jsonify([])
        
    return jsonify([{
        'id': category.categoria_id,
        'subnombre': category.subnombre
    }])

@app.route('/api/articles')
def get_articles():
    category_id = request.args.get('category_id')
    subcategory_id = request.args.get('subcategory_id')
    search_query = request.args.get('q')
    
    try:
        # Query all categories first
        categories_query = db.session.query(Categoria)
        if category_id:
            categories_query = categories_query.filter(Categoria.categoria_id == category_id)
        
        categories = categories_query.all()
        
        result = {'categories': []}
        
        for category in categories:
            # Get events for this category
            events_query = db.session.query(Evento).filter(
                Evento.categoria_id == category.categoria_id
            ).order_by(Evento.fecha_evento.desc())
            
            events = events_query.all()
            category_data = {
                'categoria_id': category.categoria_id,
                'nombre': category.nombre,
                'subnombre': category.subnombre,
                'events': []
            }
            
            for event in events:
                # Get articles for this event
                articles_query = db.session.query(Articulo).join(
                    articulo_evento,
                    Articulo.articulo_id == articulo_evento.c.articulo_id
                ).filter(
                    articulo_evento.c.evento_id == event.evento_id
                ).join(
                    Periodico
                ).order_by(Articulo.fecha_publicacion.desc())
                
                if search_query:
                    articles_query = articles_query.filter(Articulo.titular.ilike(f'%{search_query}%'))
                
                articles = articles_query.all()
                
                if articles:  # Only include events that have articles
                    event_data = {
                        'evento_id': event.evento_id,
                        'titulo': event.titulo,
                        'descripcion': event.descripcion,
                        'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                        'articles': [{
                            'id': a.articulo_id,
                            'titular': a.titular,
                            'paywall': a.paywall,
                            'periodico_logo': a.periodico.logo_url if a.periodico else None,
                            'url': a.url
                        } for a in articles]
                    }
                    category_data['events'].append(event_data)
            
            if category_data['events']:  # Only include categories that have events with articles
                result['categories'].append(category_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching articles'}), 500

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
