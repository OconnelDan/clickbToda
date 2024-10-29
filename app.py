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
            Categoria.categoria_id,
            Categoria.nombre,
            func.count(distinct(Evento.evento_id)).label('event_count')
        ).join(
            Evento,
            Categoria.categoria_id == Evento.categoria_id
        ).group_by(
            Categoria.nombre,
            Categoria.categoria_id
        ).having(
            Categoria.categoria_id == db.session.query(
                func.min(Categoria.categoria_id)
            ).filter(
                Categoria.nombre == Categoria.nombre
            ).group_by(
                Categoria.nombre
            )
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
        
        # Get the category name first
        category = db.session.query(Categoria.nombre).filter(
            Categoria.categoria_id == category_id
        ).first()
        
        if not category:
            return jsonify([])
            
        # Get subcategories for all categories with this name
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
        } for subcat in subcategories])
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rest of the code remains the same...
