from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text, desc, and_, distinct, or_
from datetime import datetime, timedelta
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
        categories = db.session.query(
            Categoria,
            func.count(distinct(Evento.evento_id)).label('event_count')
        ).outerjoin(
            Subcategoria,
            Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre
        ).order_by(
            desc('event_count')
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
        logger.info(f"Fetching details for article ID: {article_id}")
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
            logger.warning(f"Article not found with ID: {article_id}")
            return jsonify({'error': 'Article not found'}), 404

        article_obj, periodico, periodista = article
        
        response_data = {
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
            'gpt_resumen': article_obj.gpt_resumen or 'No summary available',
            'gpt_opinion': article_obj.gpt_opinion or 'No opinion available',
            'gpt_palabras_clave': article_obj.gpt_palabras_clave,
            'gpt_cantidad_fuentes_citadas': article_obj.gpt_cantidad_fuentes_citadas or 0,
            'agencia': article_obj.agencia
        }
        logger.info(f"Successfully retrieved article details for ID: {article_id}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error fetching article details: {str(e)}")
        return jsonify({'error': 'Failed to load article details', 'details': str(e)}), 500

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id')
        if not category_id:
            return jsonify([])
        
        subcategories = Subcategoria.query.filter_by(categoria_id=category_id).all()
        
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
        time_filter = request.args.get('time_filter', '24h')
        
        logger.info(f"Fetching articles with params - category: {category_id}, subcategory: {subcategory_id}, search: {search_query}, time_filter: {time_filter}")

        end_date = datetime.now()
        if time_filter == '72h':
            start_date = end_date - timedelta(hours=72)
        elif time_filter == '48h':
            start_date = end_date - timedelta(hours=48)
        else:  # 24h
            start_date = end_date - timedelta(hours=24)

        base_query = db.session.query(
            Evento,
            Categoria,
            Subcategoria,
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
                Articulo.fecha_publicacion >= start_date,
                Articulo.fecha_publicacion <= end_date
            )
        )

        if category_id:
            base_query = base_query.filter(Categoria.categoria_id == category_id)
        if subcategory_id:
            base_query = base_query.filter(Subcategoria.subcategoria_id == subcategory_id)
        if search_query:
            base_query = base_query.filter(Articulo.titular.ilike(f'%{search_query}%'))

        base_query = base_query.group_by(
            Evento.evento_id,
            Categoria.categoria_id,
            Subcategoria.subcategoria_id
        ).order_by(
            Categoria.nombre.nullslast(),
            desc('article_count'),
            desc(Evento.fecha_evento)
        )

        events = base_query.all()
        logger.info(f"Retrieved {len(events)} events")

        organized_data = {}
        
        for event, category, subcategory, article_count in events:
            articles = db.session.query(
                Articulo,
                Periodico
            ).join(
                articulo_evento,
                Articulo.articulo_id == articulo_evento.c.articulo_id
            ).join(
                Periodico,
                Articulo.periodico_id == Periodico.periodico_id
            ).filter(
                articulo_evento.c.evento_id == event.evento_id,
                Articulo.fecha_publicacion >= start_date,
                Articulo.fecha_publicacion <= end_date
            ).order_by(
                desc(Articulo.fecha_publicacion)
            ).all()

            if not articles:
                continue

            cat_id = category.categoria_id if category else 0
            if cat_id not in organized_data:
                organized_data[cat_id] = {
                    'categoria_id': cat_id,
                    'nombre': category.nombre if category else 'Uncategorized',
                    'descripcion': category.descripcion if category else '',
                    'subcategories': {}
                }

            subcat_id = subcategory.subcategoria_id if subcategory else 0
            if subcat_id not in organized_data[cat_id]['subcategories']:
                organized_data[cat_id]['subcategories'][subcat_id] = {
                    'subcategoria_id': subcat_id,
                    'nombre': subcategory.nombre if subcategory else 'Uncategorized',
                    'descripcion': subcategory.descripcion if subcategory else '',
                    'events': {}
                }

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
                } for article, periodico in articles]
            }

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
                            'events': sorted(
                                list(subcat_data['events'].values()),
                                key=lambda x: (x['article_count'], x['fecha_evento'] or ''),
                                reverse=True
                            )
                        }
                        for subcat_id, subcat_data in cat_data['subcategories'].items()
                    ]
                }
                for cat_id, cat_data in organized_data.items()
            ]
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return jsonify({
            'error': 'Failed to load articles',
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
