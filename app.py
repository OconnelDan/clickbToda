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

from models import User, Articulo, Evento, Categoria, Periodico

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

# Initialize database on startup
if not init_db():
    logger.error("Failed to initialize database")

@app.route('/')
def index():
    # Get latest date from articles
    latest_date = db.session.query(func.max(Articulo.fecha_publicacion)).scalar()
    
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
                         selected_date=latest_date or datetime.now().date())

@app.route('/api/articles')
def get_articles():
    date_str = request.args.get('date')
    category_id = request.args.get('category_id')
    search_query = request.args.get('q')
    
    query = db.session.query(Articulo).join(
        Articulo.eventos
    ).join(
        Evento.categoria
    ).join(
        Articulo.periodico
    )
    
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(Articulo.fecha_publicacion == date)
        except ValueError:
            pass
        
    if category_id:
        query = query.filter(Evento.categoria_id == category_id)
        
    if search_query:
        query = query.filter(Articulo.titular.ilike(f'%{search_query}%'))
    
    articles = query.order_by(Articulo.fecha_publicacion.desc()).limit(50).all()
    
    return jsonify([{
        'id': a.articulo_id,
        'titular': a.titular,
        'paywall': a.paywall,
        'periodico_logo': a.periodico.logo_url if a.periodico else None,
        'url': a.url
    } for a in articles])

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
