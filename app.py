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

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Pre-fetch initial data for faster loading
        initial_data = get_cached_articles(None, None, time_filter, start_date, end_date)
        
        categories = [
            {
                'Categoria': Categoria(categoria_id=cat['categoria_id'], nombre=cat['nombre']),
                'article_count': sum(
                    len(event['articles']) 
                    for subcat in cat.get('subcategories', [])
                    for event in subcat.get('events', [])
                )
            }
            for cat in initial_data.get('categories', [])
        ]

        return render_template('index.html', 
                           categories=categories,
                           initial_data=initial_data,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', categories=[], selected_date=datetime.now().date())

@app.route('/api/navigation')
def get_navigation():
    try:
        time_filter = request.args.get('time_filter', '24h')
        hours = int(time_filter[:-1])
        
        query = text('''
            WITH article_counts AS (
                SELECT 
                    s.categoria_id,
                    s.subcategoria_id,
                    COUNT(DISTINCT a.articulo_id) as article_count
                FROM 
                    app.subcategoria s
                    LEFT JOIN app.evento e ON e.subcategoria_id = s.subcategoria_id
                    LEFT JOIN app.articulo_evento ae ON e.evento_id = ae.evento_id
                    LEFT JOIN app.articulo a ON ae.articulo_id = a.articulo_id 
                        AND a.updated_on >= CURRENT_TIMESTAMP - ((:hours || ' hours')::interval)
                GROUP BY 
                    s.categoria_id,
                    s.subcategoria_id
            ),
            category_counts AS (
                SELECT 
                    categoria_id,
                    SUM(article_count) as total_articles
                FROM 
                    article_counts
                GROUP BY 
                    categoria_id
            )
            SELECT 
                c.categoria_id, 
                c.nombre AS categoria_nombre, 
                s.subcategoria_id, 
                s.nombre AS subcategoria_nombre, 
                COALESCE(ac.article_count, 0) AS cuenta_articulos_subcategoria,
                COALESCE(cc.total_articles, 0) AS cuenta_articulos_categoria
            FROM 
                app.categoria c
                LEFT JOIN app.subcategoria s ON s.categoria_id = c.categoria_id
                LEFT JOIN article_counts ac ON 
                    ac.categoria_id = c.categoria_id AND 
                    ac.subcategoria_id = s.subcategoria_id
                LEFT JOIN category_counts cc ON cc.categoria_id = c.categoria_id
            ORDER BY 
                cuenta_articulos_categoria DESC NULLS LAST,
                c.nombre ASC,
                cuenta_articulos_subcategoria DESC NULLS LAST,
                s.nombre ASC
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
                    'article_count': row.cuenta_articulos_categoria,
                    'subcategories': []
                }
            
            if row.subcategoria_id:
                current_category['subcategories'].append({
                    'subcategoria_id': row.subcategoria_id,
                    'nombre': row.subcategoria_nombre,
                    'article_count': row.cuenta_articulos_subcategoria
                })
        
        if current_category is not None:
            navigation.append(current_category)
            
        return jsonify(navigation)
    except Exception as e:
        logger.error(f"Error in get_navigation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id')
        if not category_id:
            return jsonify([])
        
        subcategories = db.session.query(
            Subcategoria.subcategoria_id.label('id'),
            Subcategoria.nombre
        ).filter_by(
            categoria_id=category_id
        ).all()
        
        return jsonify([{
            'id': subcat.id,
            'nombre': subcat.nombre
        } for subcat in subcategories])
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id')
        subcategory_id = request.args.get('subcategory_id')
        time_filter = request.args.get('time_filter', '24h')
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        return jsonify(get_cached_articles(category_id, subcategory_id, time_filter, start_date, end_date))
    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/article/<int:article_id>')
@cache.memoize(timeout=60)
def get_article_details(article_id):
    try:
        logger.info(f"Fetching details for article ID: {article_id}")
        
        article = db.session.query(Articulo).filter(
            Articulo.articulo_id == article_id
        ).options(
            joinedload(Articulo.periodico),
            joinedload(Articulo.periodista)
        ).first()

        if not article:
            logger.warning(f"Article not found with ID: {article_id}")
            return jsonify({'error': 'Article not found'}), 404

        response_data = {
            'id': article.articulo_id,
            'titular': article.titular,
            'subtitular': article.subtitular,
            'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None,
            'periodico_logo': article.periodico.logo_url if article.periodico else None,
            'periodico_nombre': article.periodico.nombre if article.periodico else None,
            'periodista': f"{article.periodista.nombre} {article.periodista.apellido}" if article.periodista else None,
            'url': article.url,
            'paywall': article.paywall,
            'cuerpo': article.cuerpo,
            'gpt_resumen': article.gpt_resumen or 'No summary available',
            'gpt_opinion': article.gpt_opinion or 'No opinion available',
            'gpt_palabras_clave': article.gpt_palabras_clave,
            'gpt_cantidad_fuentes_citadas': article.gpt_cantidad_fuentes_citadas or 0,
            'agencia': article.agencia
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error fetching article details: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Failed to load article details',
            'details': str(e)
        }), 500

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
