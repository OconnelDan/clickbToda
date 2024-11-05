from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text, desc, and_, distinct
from datetime import datetime
import logging
from config import Config
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

try:
    db = SQLAlchemy(app)
    with app.app_context():
        db.engine.connect()
    logger.info("Database connection successful")
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
        # Query categories with subcategory and article counts
        categories = db.session.query(
            Categoria,
            func.count(distinct(Evento.evento_id)).label('event_count'),
            func.count(distinct(articulo_evento.c.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria,
            Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento,
            Subcategoria.subcategoria_id == Evento.subcategoria_id
        ).outerjoin(
            articulo_evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre
        ).order_by(
            func.count(distinct(articulo_evento.c.articulo_id)).desc()
        ).all()
        
        logger.info(f"Retrieved {len(categories)} categories")
        return render_template('index.html', 
                           categories=categories,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', categories=[], selected_date=datetime.now().date())

@app.route('/api/article/<int:article_id>')
def get_article_details(article_id):
    try:
        article = db.session.query(
            Articulo,
            Periodico,
            Periodista
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).outerjoin(
            Periodista,
            Articulo.periodista_id == Periodista.periodista_id
        ).filter(
            Articulo.articulo_id == article_id
        ).first()

        if not article:
            return jsonify({'error': 'Article not found'}), 404

        article_obj, periodico, periodista = article
        
        return jsonify({
            'id': article_obj.articulo_id,
            'titular': article_obj.titular,
            'subtitular': article_obj.subtitular,
            'fecha_publicacion': article_obj.fecha_publicacion.strftime('%Y-%m-%d') if article_obj.fecha_publicacion else None,
            'periodico_logo': periodico.logo_url if periodico else None,
            'periodico_nombre': periodico.nombre if periodico else None,
            'periodista': f"{periodista.nombre} {periodista.apellido}" if periodista else None,
            'url': article_obj.url,
            'paywall': article_obj.paywall,
            'cuerpo': article_obj.cuerpo,
            'gpt_resumen': article_obj.gpt_resumen,
            'gpt_opinion': article_obj.gpt_opinion,
            'gpt_palabras_clave': article_obj.gpt_palabras_clave,
            'gpt_cantidad_fuentes_citadas': article_obj.gpt_cantidad_fuentes_citadas,
            'agencia': article_obj.agencia
        })
    except Exception as e:
        logger.error(f"Error fetching article details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id')
        if not category_id:
            return jsonify([])
        
        subcategories = db.session.query(
            Subcategoria.subcategoria_id,
            Subcategoria.nombre
        ).filter(
            Subcategoria.categoria_id == category_id
        ).all()
        
        return jsonify([{
            'id': subcat.subcategoria_id,
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
        search_query = request.args.get('q')
        
        article_count_subquery = db.session.query(
            articulo_evento.c.evento_id,
            func.count(articulo_evento.c.articulo_id).label('article_count')
        ).group_by(articulo_evento.c.evento_id).subquery()
        
        base_query = db.session.query(
            Articulo, Evento, Categoria, Subcategoria, Region, Periodico,
            article_count_subquery.c.article_count
        ).select_from(Articulo)\
        .join(articulo_evento, Articulo.articulo_id == articulo_evento.c.articulo_id)\
        .join(Evento, articulo_evento.c.evento_id == Evento.evento_id)\
        .join(Subcategoria, Evento.subcategoria_id == Subcategoria.subcategoria_id)\
        .join(Categoria, Subcategoria.categoria_id == Categoria.categoria_id)\
        .join(evento_region, Evento.evento_id == evento_region.c.evento_id, isouter=True)\
        .join(Region, evento_region.c.region_id == Region.region_id, isouter=True)\
        .join(Periodico, Articulo.periodico_id == Periodico.periodico_id)\
        .join(article_count_subquery, Evento.evento_id == article_count_subquery.c.evento_id)

        if category_id:
            base_query = base_query.filter(Categoria.categoria_id == category_id)
        if subcategory_id:
            base_query = base_query.filter(Subcategoria.subcategoria_id == subcategory_id)
        if search_query:
            base_query = base_query.filter(Articulo.titular.ilike(f'%{search_query}%'))

        results = base_query.order_by(
            Categoria.nombre,
            article_count_subquery.c.article_count.desc(),
            desc(Evento.fecha_evento),
            desc(Articulo.fecha_publicacion)
        ).all()

        logger.info(f"Retrieved {len(results)} articles")

        organized_data = {}
        for article, event, category, subcategory, region, periodico, article_count in results:
            if not category:
                continue
                
            if category.categoria_id not in organized_data:
                organized_data[category.categoria_id] = {
                    'categoria_id': category.categoria_id,
                    'nombre': category.nombre,
                    'descripcion': category.descripcion,
                    'subcategories': {}
                }

            subcategory_key = subcategory.subcategoria_id
            if subcategory_key not in organized_data[category.categoria_id]['subcategories']:
                organized_data[category.categoria_id]['subcategories'][subcategory_key] = {
                    'subcategoria_id': subcategory.subcategoria_id,
                    'nombre': subcategory.nombre,
                    'descripcion': subcategory.descripcion,
                    'events': {}
                }

            if event:
                if event.evento_id not in organized_data[category.categoria_id]['subcategories'][subcategory_key]['events']:
                    organized_data[category.categoria_id]['subcategories'][subcategory_key]['events'][event.evento_id] = {
                        'evento_id': event.evento_id,
                        'titulo': event.titulo,
                        'descripcion': event.descripcion,
                        'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                        'article_count': article_count,
                        'articles': []
                    }

                organized_data[category.categoria_id]['subcategories'][subcategory_key]['events'][event.evento_id]['articles'].append({
                    'id': article.articulo_id,
                    'titular': article.titular,
                    'paywall': article.paywall,
                    'periodico_logo': periodico.logo_url if periodico else None,
                    'url': article.url,
                    'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None
                })

        response_data = {
            'categories': [
                {
                    'categoria_id': cat_data['categoria_id'],
                    'nombre': cat_data['nombre'],
                    'descripcion': cat_data['descripcion'],
                    'subcategories': [
                        {
                            'subcategoria_id': subcat_data['subcategoria_id'],
                            'nombre': subcat_data['nombre'],
                            'descripcion': subcat_data['descripcion'],
                            'events': sorted([
                                {
                                    **event_data,
                                    'articles': sorted(event_data['articles'], 
                                                   key=lambda x: x['fecha_publicacion'] or '', 
                                                   reverse=True)
                                }
                                for event_id, event_data in subcat_data['events'].items()
                            ], key=lambda x: (x['article_count'] or 0, x['fecha_evento'] or ''), reverse=True)
                        }
                        for subcat_key, subcat_data in cat_data['subcategories'].items()
                    ]
                }
                for cat_id, cat_data in organized_data.items()
            ]
        }

        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return jsonify({
            'error': 'An error occurred while fetching articles',
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
