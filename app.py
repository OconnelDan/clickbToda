from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text, desc, and_, distinct, or_, Index
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
                CREATE INDEX IF NOT EXISTS idx_article_event_count ON app.articulo_evento (evento_id);
                CREATE INDEX IF NOT EXISTS idx_subcategory_category ON app.subcategoria (categoria_id);
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
        
        # Get categories with article counts for the navigation
        categories = [
            {
                'Categoria': Categoria(categoria_id=cat['categoria_id'], nombre=cat['nombre']),
                'article_count': cat['article_count']
            }
            for cat in initial_data.get('categories', [])
        ]

        # Sort categories by article count
        categories.sort(key=lambda x: x['article_count'], reverse=True)

        return render_template('index.html', 
                           categories=categories,
                           initial_data=initial_data,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', categories=[], selected_date=datetime.now().date())

@app.route('/api/categories/hierarchy')
@cache.memoize(timeout=60)
def get_category_hierarchy():
    try:
        time_filter = request.args.get('time_filter', '24h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        # Get category counts with subcategories
        categories = db.session.query(
            Categoria,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).join(
            Subcategoria,
            Categoria.categoria_id == Subcategoria.categoria_id
        ).join(
            Evento,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).join(
            Articulo,
            and_(
                articulo_evento.c.articulo_id == Articulo.articulo_id,
                Articulo.updated_on.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id
        ).order_by(
            desc('article_count')
        ).all()
        
        # Get subcategory counts for each category
        result = []
        for cat, cat_count in categories:
            subcategories = db.session.query(
                Subcategoria,
                func.count(distinct(Articulo.articulo_id)).label('article_count')
            ).join(
                Evento,
                Evento.subcategoria_id == Subcategoria.subcategoria_id
            ).join(
                articulo_evento,
                Evento.evento_id == articulo_evento.c.evento_id
            ).join(
                Articulo,
                and_(
                    articulo_evento.c.articulo_id == Articulo.articulo_id,
                    Articulo.updated_on.between(start_date, end_date)
                )
            ).filter(
                Subcategoria.categoria_id == cat.categoria_id
            ).group_by(
                Subcategoria.subcategoria_id
            ).order_by(
                desc('article_count')
            ).all()
            
            result.append({
                'categoria_id': cat.categoria_id,
                'nombre': cat.nombre,
                'article_count': cat_count,
                'subcategories': [{
                    'subcategoria_id': sub.Subcategoria.subcategoria_id,
                    'nombre': sub.Subcategoria.nombre,
                    'article_count': sub_count
                } for sub, sub_count in subcategories]
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_category_hierarchy: {str(e)}")
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

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id')
        if not category_id:
            return jsonify([])
            
        subcategories = db.session.query(
            Subcategoria,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).join(
            Evento,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).join(
            Articulo,
            articulo_evento.c.articulo_id == Articulo.articulo_id
        ).filter(
            Subcategoria.categoria_id == category_id
        ).group_by(
            Subcategoria.subcategoria_id
        ).order_by(
            desc('article_count')
        ).all()
        
        return jsonify([{
            'subcategoria_id': sub.Subcategoria.subcategoria_id,
            'nombre': sub.Subcategoria.nombre,
            'article_count': sub.article_count
        } for sub in subcategories])
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
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

@cache.memoize(timeout=60)
def get_cached_articles(category_id, subcategory_id, time_filter, start_date, end_date):
    try:
        # First, get counts for all categories
        category_counts = db.session.query(
            Categoria.categoria_id,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).join(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).join(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento, Evento.evento_id == articulo_evento.c.evento_id
        ).join(
            Articulo, and_(
                articulo_evento.c.articulo_id == Articulo.articulo_id,
                Articulo.updated_on.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id
        ).order_by(
            desc('article_count')
        ).subquery()

        # Main query with article counts and proper sorting
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

        base_query = base_query.outerjoin(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            Categoria,
            Subcategoria.categoria_id == Categoria.categoria_id
        ).outerjoin(
            articulo_evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).outerjoin(
            Articulo,
            and_(
                articulo_evento.c.articulo_id == Articulo.articulo_id,
                Articulo.paywall.is_(False) if request.args.get('hide_paywall') else True,
                Articulo.updated_on >= start_date,
                Articulo.updated_on <= end_date
            )
        )

        if category_id:
            base_query = base_query.filter(Categoria.categoria_id == category_id)
        if subcategory_id:
            base_query = base_query.filter(Subcategoria.subcategoria_id == subcategory_id)

        base_query = base_query.group_by(
            Evento.evento_id,
            Categoria.categoria_id,
            Subcategoria.subcategoria_id
        ).order_by(
            desc('article_count'),
            desc(Evento.fecha_evento)
        )

        events = base_query.all()
        logger.info(f"Retrieved {len(events)} events")

        organized_data = {}
        
        # Get all event IDs first
        event_ids = [event.evento_id for event in events]
        
        # Fetch articles in a single query with proper joins
        articles_query = db.session.query(
            Articulo,
            Periodico
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).join(
            articulo_evento,
            and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                articulo_evento.c.evento_id.in_(event_ids)
            )
        ).filter(
            Articulo.updated_on.between(start_date, end_date)
        ).order_by(desc(Articulo.updated_on))
        
        # Organize articles by event
        articles_by_event = {}
        for article, periodico in articles_query.all():
            for event in article.eventos:
                if event.evento_id not in articles_by_event:
                    articles_by_event[event.evento_id] = []
                articles_by_event[event.evento_id].append((article, periodico))

        for event in events:
            articles = articles_by_event.get(event.evento_id, [])
            
            if not articles:
                continue

            cat_id = event.categoria_id if event.categoria_id else 0
            if cat_id not in organized_data:
                organized_data[cat_id] = {
                    'categoria_id': cat_id,
                    'nombre': event.categoria_nombre if event.categoria_nombre else 'Uncategorized',
                    'subcategories': {},
                    'article_count': 0
                }

            subcat_id = event.subcategoria_id if event.subcategoria_id else 0
            if subcat_id not in organized_data[cat_id]['subcategories']:
                organized_data[cat_id]['subcategories'][subcat_id] = {
                    'subcategoria_id': subcat_id,
                    'nombre': event.subcategoria_nombre if event.subcategoria_nombre else 'Uncategorized',
                    'events': {},
                    'article_count': 0
                }

            # Update article counts
            article_count = len(articles)
            organized_data[cat_id]['article_count'] += article_count
            organized_data[cat_id]['subcategories'][subcat_id]['article_count'] += article_count

            organized_data[cat_id]['subcategories'][subcat_id]['events'][event.evento_id] = {
                'evento_id': event.evento_id,
                'titulo': event.titulo,
                'descripcion': event.descripcion,
                'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                'article_count': article_count,
                'articles': [{
                    'id': article.articulo_id,
                    'titular': article.titular,
                    'paywall': article.paywall,
                    'periodico_logo': periodico.logo_url if periodico else None,
                    'url': article.url,
                    'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None,
                    'gpt_opinion': article.gpt_opinion
                } for article, periodico in sorted(articles, key=lambda x: x[0].updated_on, reverse=True)]
            }

        # Sort categories by article count
        sorted_categories = sorted(
            organized_data.values(),
            key=lambda x: x['article_count'],
            reverse=True
        )

        return {
            'categories': [
                {
                    'categoria_id': cat_data['categoria_id'],
                    'nombre': cat_data['nombre'],
                    'article_count': cat_data['article_count'],
                    'subcategories': sorted([
                        {
                            'subcategoria_id': subcat_data['subcategoria_id'],
                            'nombre': subcat_data['nombre'],
                            'article_count': subcat_data['article_count'],
                            'events': sorted(
                                list(subcat_data['events'].values()),
                                key=lambda x: (x['article_count'], x['fecha_evento'] or ''),
                                reverse=True
                            )
                        }
                        for subcat_id, subcat_data in cat_data['subcategories'].items()
                    ], key=lambda x: x['article_count'], reverse=True)
                }
                for cat_data in sorted_categories
            ]
        }
    except Exception as e:
        logger.error(f"Error in get_cached_articles: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
