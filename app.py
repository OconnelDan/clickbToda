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

from models import User, Articulo, Evento, Categoria, Periodico, articulo_evento, evento_region, Region, Periodista, Subcategoria

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
            Evento,
            Categoria.categoria_id == Evento.categoria_id
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

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id')
        if not category_id:
            return jsonify([])
        
        subcategories = Subcategoria.query.filter_by(categoria_id=category_id).all()
        
        return jsonify([{
            'id': subcat.id,
            'nombre': subcat.nombre or '',
            'descripcion': subcat.descripcion or ''
        } for subcat in subcategories])
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id')
        search_query = request.args.get('q')
        
        # Base query for articles
        query = db.session.query(
            Articulo,
            Evento,
            Categoria,
            Subcategoria,
            Periodico
        ).select_from(Articulo).join(
            articulo_evento,
            Articulo.articulo_id == articulo_evento.c.articulo_id
        ).join(
            Evento,
            Evento.evento_id == articulo_evento.c.evento_id
        ).join(
            Categoria,
            Evento.categoria_id == Categoria.categoria_id
        ).outerjoin(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.id
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        )

        # Add filters
        if category_id:
            query = query.filter(Categoria.categoria_id == category_id)
        if search_query:
            query = query.filter(Articulo.titular.ilike(f'%{search_query}%'))

        # Add ordering
        query = query.order_by(
            Categoria.nombre,
            Subcategoria.nombre,
            desc(Evento.fecha_evento),
            desc(Articulo.fecha_publicacion)
        )

        results = query.all()
        logger.info(f"Retrieved {len(results)} articles")

        # Organize the data
        organized_data = {}
        for article, event, category, subcategory, periodico in results:
            if not category:
                continue
                
            cat_id = category.categoria_id
            if cat_id not in organized_data:
                organized_data[cat_id] = {
                    'categoria_id': cat_id,
                    'nombre': category.nombre,
                    'descripcion': category.descripcion,
                    'subcategories': {}
                }

            subcat_key = str(subcategory.id) if subcategory else 'none'
            if subcat_key not in organized_data[cat_id]['subcategories']:
                organized_data[cat_id]['subcategories'][subcat_key] = {
                    'nombre': subcategory.nombre if subcategory else None,
                    'descripcion': subcategory.descripcion if subcategory else None,
                    'events': {}
                }

            event_id = event.evento_id
            if event_id not in organized_data[cat_id]['subcategories'][subcat_key]['events']:
                organized_data[cat_id]['subcategories'][subcat_key]['events'][event_id] = {
                    'evento_id': event_id,
                    'titulo': event.titulo,
                    'descripcion': event.descripcion,
                    'fecha_evento': event.fecha_evento.strftime('%Y-%m-%d') if event.fecha_evento else None,
                    'articles': []
                }

            organized_data[cat_id]['subcategories'][subcat_key]['events'][event_id]['articles'].append({
                'id': article.articulo_id,
                'titular': article.titular,
                'paywall': article.paywall,
                'periodico_logo': periodico.logo_url if periodico else None,
                'url': article.url,
                'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None
            })

        # Format response
        response_data = {
            'categories': [
                {
                    'categoria_id': cat_data['categoria_id'],
                    'nombre': cat_data['nombre'],
                    'descripcion': cat_data['descripcion'],
                    'subcategories': [
                        {
                            'nombre': subcat_data['nombre'],
                            'descripcion': subcat_data['descripcion'],
                            'events': sorted(
                                [
                                    {
                                        **event_data,
                                        'articles': sorted(
                                            event_data['articles'],
                                            key=lambda x: x['fecha_publicacion'] or '',
                                            reverse=True
                                        )
                                    }
                                    for event_id, event_data in subcat_data['events'].items()
                                ],
                                key=lambda x: x['fecha_evento'] or '',
                                reverse=True
                            )
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
        return jsonify({'error': str(e)}), 500

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
