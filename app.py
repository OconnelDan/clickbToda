from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text
from datetime import datetime
from config import Config

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

# Initialize database
def init_db():
    with app.app_context():
        # Create schema first
        try:
            db.session.execute(text('CREATE SCHEMA IF NOT EXISTS app'))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating schema: {e}")
            return False
            
        # Then create all tables
        try:
            db.create_all()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating tables: {e}")
            return False

# Initialize database on startup
if not init_db():
    print("Failed to initialize database")

@app.route('/')
def index():
    # Get latest date from articles
    latest_date = db.session.query(func.max(Articulo.fecha_publicacion)).scalar()
    
    # Get categories with events count
    categories = db.session.query(
        Categoria, 
        func.count(Evento.evento_id).label('event_count')
    ).join(Evento, isouter=True).group_by(Categoria.categoria_id, Categoria.nombre).order_by(func.count(Evento.evento_id).desc()).all()
    
    return render_template('index.html', 
                         categories=categories,
                         selected_date=latest_date)

@app.route('/api/articles')
def get_articles():
    date_str = request.args.get('date')
    category_id = request.args.get('category_id')
    search_query = request.args.get('q')
    
    query = Articulo.query
    
    if date_str:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        query = query.filter(Articulo.fecha_publicacion == date)
        
    if category_id:
        query = query.join(Articulo.eventos).filter(Evento.categoria_id == category_id)
        
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
