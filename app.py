from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text, desc, and_, or_, distinct, Index
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import logging
from config import Config
import sys
from flask_caching import Cache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20

cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 60
})

try:
    db = SQLAlchemy(app)
    with app.app_context():
        db.engine.connect()
        with db.engine.connect() as connection:
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_articulo_updated_on ON app.articulo (updated_on);
                CREATE INDEX IF NOT EXISTS idx_articulo_evento_ids ON app.articulo_evento (articulo_id, evento_id);
                CREATE INDEX IF NOT EXISTS idx_evento_subcategoria ON app.evento (subcategoria_id);
                CREATE INDEX IF NOT EXISTS idx_article_time ON app.articulo (updated_on, paywall);
                CREATE INDEX IF NOT EXISTS idx_article_category ON app.articulo (periodico_id, updated_on);
            """))
    logger.info("Database connection and indexes setup successful")
except Exception as e:
    logger.error(f"Database connection failed: {str(e)}")
    raise

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, articulo_evento, evento_region, Region, Periodista

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/api/navigation')
def get_navigation():
    try:
        time_filter = request.args.get('time_filter', '24h')
        hours = int(time_filter[:-1])
        
        query = text('''
            SELECT 
                c.categoria_id, 
                c.nombre AS categoria_nombre, 
                s.subcategoria_id, 
                s.nombre AS subcategoria_nombre, 
                e.titulo,
                COUNT(a.titular) AS cuenta_articulos_subcategoria,
                SUM(COUNT(a.titular)) OVER (PARTITION BY c.categoria_id) AS cuenta_articulos_categoria
            FROM 
                app.articulo a
                LEFT JOIN app.articulo_evento ae ON a.articulo_id = ae.articulo_id
                LEFT JOIN app.evento e ON ae.evento_id = e.evento_id
                LEFT JOIN app.subcategoria s ON e.subcategoria_id = s.subcategoria_id
                LEFT JOIN app.categoria c ON c.categoria_id = s.categoria_id
            WHERE 
                a.updated_on >= CURRENT_TIMESTAMP - ((:hours || ' hours')::interval)
            GROUP BY 
                c.categoria_id, 
                c.nombre, 
                s.subcategoria_id, 
                s.nombre,
                e.titulo
            ORDER BY 
                cuenta_articulos_categoria DESC, 
                cuenta_articulos_subcategoria DESC
        ''')
        
        result = db.session.execute(query, {'hours': hours})
        
        navigation = []
        current_category = None
        
        for row in result:
            if current_category is None or current_category['categoria_id'] != row.categoria_id:
                if current_category is not None:
                    navigation.append(current_category)
                current_category = {
                    'categoria_id': row.categoria_id,
                    'nombre': row.categoria_nombre,
                    'article_count': row.cuenta_articulos_categoria or 0,
                    'subcategories': []
                }
            
            if row.subcategoria_id:
                # Check if subcategory already exists to avoid duplicates
                subcat_exists = False
                for subcat in current_category['subcategories']:
                    if subcat['subcategoria_id'] == row.subcategoria_id:
                        subcat_exists = True
                        break
                        
                if not subcat_exists:
                    current_category['subcategories'].append({
                        'subcategoria_id': row.subcategoria_id,
                        'nombre': row.subcategoria_nombre,
                        'article_count': row.cuenta_articulos_subcategoria or 0
                    })
        
        if current_category is not None:
            navigation.append(current_category)
            
        return jsonify(navigation)
    except Exception as e:
        logger.error(f"Error in get_navigation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        categories = db.session.query(
            Categoria
        ).join(
            Subcategoria
        ).join(
            Evento
        ).join(
            articulo_evento
        ).join(
            Articulo
        ).filter(
            Articulo.updated_on >= start_date
        ).distinct().all()
        
        return render_template('index.html', 
                           categories=categories,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', categories=[], selected_date=datetime.now().date())

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
