import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.utils
import json
import ast
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, flash, Markup
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sklearn.manifold import TSNE
from sqlalchemy import func, text, desc, and_, or_, distinct, Integer, cast, String, exists
from flask_caching import Cache
from database import db
from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, Periodista, articulo_evento
from config import Config
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
import plotly.utils
import json
import ast
from markupsafe import Markup
from sklearn.manifold import TSNE
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, text, desc, and_, or_, distinct, Integer, cast, String, exists
import json
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import logging
import sys
from config import Config
from flask_caching import Cache
from database import db
from models import User, Articulo, Evento, Categoria, Subcategoria, Periodico, Periodista, articulo_evento

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
csrf = CSRFProtect(app)
db.init_app(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 60})

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not nombre or not email or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('register'))
        
        # Validate email format
        if not User.validate_email(email):
            flash('Invalid email format', 'error')
            return redirect(url_for('register'))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        # Validate password
        is_valid, message = User.validate_password(password)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('register'))
        
        # Create new user
        try:
            user = User(nombre=nombre, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating user account', 'error')
            return redirect(url_for('register'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/posturas')
def posturas():
    try:
        time_filter = request.args.get('time_filter', '72h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Query categories with event counts
        categories_query = db.session.query(
            Categoria,
            func.count(distinct(Evento.evento_id)).label('event_count')
        ).outerjoin(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento, and_(
                Evento.subcategoria_id == Subcategoria.subcategoria_id,
                Evento.gpt_desinformacion.isnot(None)
            )
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre,
            Categoria.descripcion
        ).order_by(
            desc('event_count'),
            Categoria.nombre
        )

        categories_result = categories_query.all()

        if not categories_result:
            logger.warning("No categories found in the database")
            categories = []
        else:
            # Add "All" category with total event count
            categories = [{
                'Categoria': {
                    'categoria_id': 0,
                    'nombre': 'All',
                    'descripcion': 'All categories'
                },
                'article_count': sum(cat.event_count or 0 for cat in categories_result)
            }]
            # Then add the rest of the categories
            for category in categories_result:
                categories.append({
                    'Categoria': {
                        'categoria_id': category.Categoria.categoria_id,
                        'nombre': category.Categoria.nombre,
                        'descripcion': category.Categoria.descripcion
                    },
                    'article_count': category.event_count or 0
                })
            logger.info(f"Found {len(categories)} categories for posturas page")

        return render_template('posturas.html',
                           categories=categories,
                           time_filter=time_filter)

    except Exception as e:
        logger.error(f"Error in posturas route: {str(e)}", exc_info=True)
        flash('Error loading categories. Please try again later.', 'error')
        return render_template('posturas.html',
                           categories=[],
                           time_filter='72h')

@app.route('/api/posturas')
def get_posturas():
    try:
        time_filter = request.args.get('time_filter', '72h')
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        # Modificar la query para incluir información del evento
        query = db.session.query(
            Evento,
            Subcategoria,
            Categoria
        ).join(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            Categoria,
            Subcategoria.categoria_id == Categoria.categoria_id
        ).filter(
            Evento.gpt_desinformacion.isnot(None)
        )
        
        # Aplicar filtros de categoría
        if category_id:
            if category_id != 0:  # Skip for "All" category
                query = query.filter(Categoria.categoria_id == category_id)
        
        if subcategory_id:
            query = query.filter(Evento.subcategoria_id == subcategory_id)
        
        eventos = query.order_by(desc(Evento.fecha_evento)).all()
        
        eventos_data = []
        for evento, subcategoria, categoria in eventos:
            try:
                if evento.gpt_desinformacion:
                    json_str = evento.gpt_desinformacion.replace('\"', '"').replace('\\', '')
                    if json_str.startswith('"') and json_str.endswith('"'):
                        json_str = json_str[1:-1]
                    
                    posturas = json.loads(json_str)
                    
                    eventos_data.append({
                        'evento_id': evento.evento_id,
                        'titulo': evento.titulo,
                        'descripcion': evento.descripcion,
                        'fecha': evento.fecha_evento.strftime('%Y-%m-%d') if evento.fecha_evento else None,
                        'categoria_nombre': categoria.nombre,
                        'subcategoria_nombre': subcategoria.nombre,
                        'posturas': posturas if isinstance(posturas, list) else [posturas]
                    })
            except Exception as e:
                logger.error(f"Error processing evento {evento.evento_id}: {str(e)}")
                continue
        
        return jsonify(eventos_data)
        
    except Exception as e:
        logger.error(f"Error fetching posturas: {str(e)}")
        return jsonify([])  # Return empty list instead of 500 error

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '72h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        logger.info(f"Loading index page with time_filter: {time_filter}")

        # Query categories with article counts using correct schema references
        categories_query = db.session.query(
            Categoria,
            func.count(distinct(Articulo.articulo_id)).label('article_count')
        ).outerjoin(
            Subcategoria, Categoria.categoria_id == Subcategoria.categoria_id
        ).outerjoin(
            Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).group_by(
            Categoria.categoria_id,
            Categoria.nombre,
            Categoria.descripcion
        ).order_by(
            desc('article_count'),
            Categoria.nombre
        )

        categories_result = categories_query.all()

        if not categories_result:
            logger.warning("No categories found in the database")
            flash('No categories available at the moment', 'warning')
            categories = []
        else:
            # Add "All" category with total article count
            categories = [{
                'Categoria': {
                    'categoria_id': 0,  # Use 0 for the "All" category
                    'nombre': 'All',
                    'descripcion': 'All categories'
                },
                'article_count': sum(cat.article_count or 0 for cat in categories_result)
            }]
            # Then add the rest of the categories
            for category in categories_result:
                categories.append({
                    'Categoria': {
                        'categoria_id': category.Categoria.categoria_id,
                        'nombre': category.Categoria.nombre,
                        'descripcion': category.Categoria.descripcion
                    },
                    'article_count': category.article_count or 0
                })
            logger.info(f"Found {len(categories)} categories")

        return render_template('index.html',
                           categories=categories,
                           initial_data={'categories': categories},
                           selected_date=datetime.now().date(),
                           time_filter=time_filter)

    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        flash('Error loading categories. Please try again later.', 'error')
        return render_template('index.html',
                           categories=[],
                           initial_data={'categories': []},
                           selected_date=datetime.now().date(),
                           time_filter=time_filter)

@app.route('/api/subcategories')
def get_subcategories():
    try:
        category_id = request.args.get('category_id', type=int)
        time_filter = request.args.get('time_filter', '72h')
        
        if category_id is None:  # Change condition to check for None instead
            return jsonify({'error': 'Category ID is required'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # For "All" category, return all subcategories
        if category_id == 0:
            subcategories = db.session.query(
                Subcategoria.subcategoria_id.label('id'),
                Subcategoria.nombre,
                func.count(distinct(Articulo.articulo_id)).label('article_count')
            ).outerjoin(
                Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
            ).outerjoin(
                articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
            ).outerjoin(
                Articulo, and_(
                    Articulo.articulo_id == articulo_evento.c.articulo_id,
                    Articulo.fecha_publicacion.between(start_date, end_date)
                )
            ).group_by(
                Subcategoria.subcategoria_id,
                Subcategoria.nombre
            ).order_by(desc('article_count')).all()
        else:
            # Existing query for specific category
            subcategories = db.session.query(
                Subcategoria.subcategoria_id.label('id'),
                Subcategoria.nombre,
                func.count(distinct(Articulo.articulo_id)).label('article_count')
            ).outerjoin(
                Evento, Evento.subcategoria_id == Subcategoria.subcategoria_id
            ).outerjoin(
                articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
            ).outerjoin(
                Articulo, and_(
                    Articulo.articulo_id == articulo_evento.c.articulo_id,
                    Articulo.fecha_publicacion.between(start_date, end_date)
                )
            ).filter(
                Subcategoria.categoria_id == category_id
            ).group_by(
                Subcategoria.subcategoria_id,
                Subcategoria.nombre
            ).order_by(desc('article_count')).all()

        return jsonify([{
            'id': s.id,
            'nombre': s.nombre,
            'article_count': s.article_count or 0
        } for s in subcategories])

    except Exception as e:
        logger.error(f"Error fetching subcategories: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/mapa')
def mapa():
    try:
        # Query articles and their embeddings from the last 72 hours
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=72)
        
        # Query articles with their embeddings
        query = db.session.query(
            Articulo.titular,
            Articulo.embeddings,
            Articulo.gpt_palabras_clave,
            Articulo.gpt_resumen,
            Periodico.nombre.label('periodico_nombre')
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).filter(
            Articulo.fecha_publicacion.between(start_date, end_date),
            Articulo.embeddings.isnot(None)
        )
        
        # Convert to DataFrame
        df = pd.read_sql(query.statement, db.session.bind)
        
        if len(df) == 0:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')
            
        # Process embeddings
        def parse_embedding(x):
            if pd.isna(x):
                return None
            try:
                if isinstance(x, str):
                    clean_str = x.replace("'", '"').replace('\\', '')
                    if clean_str.startswith('"') and clean_str.endswith('"'):
                        clean_str = clean_str[1:-1]
                    return np.array(json.loads(clean_str))
                return x
            except:
                return None

        # Process embeddings
        df['embeddings'] = df['embeddings'].apply(parse_embedding)
        df = df.dropna(subset=['embeddings'])
        
        if len(df) < 2:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')

        # Convert embeddings to numpy array
        embeddings_array = np.stack(df['embeddings'].values)
        
        # Apply t-SNE
        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(embeddings_array)
        
        # Create visualization DataFrame
        plot_df = pd.DataFrame(embeddings_2d, columns=['x', 'y'])
        plot_df['Periódico'] = df['periodico_nombre']
        plot_df['Titular'] = df['titular']
        plot_df['Keywords'] = df['gpt_palabras_clave']
        plot_df['Resumen'] = df['gpt_resumen']
        
        # Create scatter plot
        fig = px.scatter(
            plot_df, 
            x='x', 
            y='y',
            color='Periódico',
            hover_data={
                'x': False,
                'y': False,
                'Periódico': True,
                'Titular': True,
                'Keywords': True,
                'Resumen': True
            },
            title='Mapa de Noticias'
        )
        
        # Update layout
        fig.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title='',
            yaxis_title='',
            height=800,
            template='plotly_dark'
        )
        
        # Convert to HTML
        plot_div = fig.to_html(
            full_html=False,
            include_plotlyjs=True,
            div_id='newsMap'
        )
        
        return render_template('mapa.html', plot_div=plot_div)
        
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}", exc_info=True)
        flash('Error al generar el mapa de noticias.', 'error')
        return render_template('mapa.html')

@app.route('/api/articles')
def get_articles():  # 1
    try:
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        time_filter = request.args.get('time_filter', '72h')
        
        if category_id is None and subcategory_id is None:
            logger.error("Missing required parameters: category_id or subcategory_id")
            return jsonify({'error': 'category_id or subcategory_id is required'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        query = db.session.query(
            Evento.evento_id,
            Evento.titulo,
            Evento.descripcion,
            Evento.fecha_evento,
            Categoria.categoria_id,
            Categoria.nombre.label('categoria_nombre'),
            Subcategoria.subcategoria_id,
            Subcategoria.nombre.label('subcategoria_nombre'),
            Articulo
        ).join(
            Subcategoria, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            Categoria, Subcategoria.categoria_id == Categoria.categoria_id
        ).join(
            articulo_evento, Evento.evento_id == articulo_evento.c.evento_id
        ).join(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        )

        if category_id:
            if category_id != 0:  # Skip for "All" category
                query = query.filter(Categoria.categoria_id == category_id)
        
        if subcategory_id:
            query = query.filter(Subcategoria.subcategoria_id == subcategory_id)

        articles_data = query.all()
        
        if not articles_data:
            return jsonify({'categories': []})

        # Process the query results
        categories_dict = {}
        for row in articles_data:
            categoria_id = row.categoria_id
            if categoria_id not in categories_dict:
                categories_dict[categoria_id] = {
                    'categoria_id': categoria_id,
                    'nombre': row.categoria_nombre,
                    'subcategories': {}
                }
            
            subcategoria_id = row.subcategoria_id
            if subcategoria_id not in categories_dict[categoria_id]['subcategories']:
                categories_dict[categoria_id]['subcategories'][subcategoria_id] = {
                    'id': subcategoria_id,
                    'nombre': row.subcategoria_nombre,
                    'events': {}
                }
            
            evento_id = row.evento_id
            if evento_id not in categories_dict[categoria_id]['subcategories'][subcategoria_id]['events']:
                categories_dict[categoria_id]['subcategories'][subcategoria_id]['events'][evento_id] = {
                    'id': evento_id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'fecha_evento': row.fecha_evento.strftime('%Y-%m-%d') if row.fecha_evento else None,
                    'articles': []
                }
            
            article = row.Articulo
            categories_dict[categoria_id]['subcategories'][subcategoria_id]['events'][evento_id]['articles'].append({
                'id': article.articulo_id,
                'titular': article.titular,
                'url': article.url,
                'fecha_publicacion': article.fecha_publicacion.strftime('%Y-%m-%d') if article.fecha_publicacion else None,
                'paywall': article.paywall,
                'periodico_logo': article.periodico.logo_url if article.periodico else None,
                'gpt_opinion': article.gpt_opinion
            })

        # Convert the nested dictionaries to lists
        categories = []
        for cat_id, cat_data in categories_dict.items():
            category = {
                'categoria_id': cat_data['categoria_id'],
                'nombre': cat_data['nombre'],
                'subcategories': []
            }
            
            for subcat_id, subcat_data in cat_data['subcategories'].items():
                subcategory = {
                    'id': subcat_data['id'],
                    'nombre': subcat_data['nombre'],
                    'events': list(subcat_data['events'].values())
                }
                category['subcategories'].append(subcategory)
            
            categories.append(category)

        return jsonify({'categories': categories})

    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500




@app.route('/mapa')
def mapa():
    try:
        # Get time filter and calculate date range
        time_filter = request.args.get('time_filter', '72h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))
        
        # Query articles with their embeddings
        articles_query = db.session.query(
            Articulo.titular,
            Articulo.embeddings,
            Articulo.gpt_palabras_clave,
            Articulo.gpt_resumen,
            Periodico.nombre.label('periodico_nombre')
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).filter(
            Articulo.fecha_publicacion.between(start_date, end_date),
            Articulo.embeddings.isnot(None)
        )
        
        # Convert to DataFrame
        df = pd.read_sql(articles_query.statement, db.session.bind)
        
        if len(df) == 0:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')
            
        # Process embeddings
        def parse_embedding(x):
            if pd.isna(x):
                return None
            try:
                if isinstance(x, str):
                    clean_str = x.replace("'", '"').replace('\\', '')
                    if clean_str.startswith('"') and clean_str.endswith('"'):
                        clean_str = clean_str[1:-1]
                    return np.array(json.loads(clean_str))
                return x
            except:
                return None

        # Process embeddings
        df['embeddings'] = df['embeddings'].apply(parse_embedding)
        df = df.dropna(subset=['embeddings'])
        
        if len(df) < 2:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')

        # Convert embeddings to numpy array
        embeddings_array = np.stack(df['embeddings'].values)
        
        # Apply t-SNE
        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(embeddings_array)
        
        # Create visualization DataFrame
        plot_df = pd.DataFrame(embeddings_2d, columns=['x', 'y'])
        plot_df['Periódico'] = df['periodico_nombre']
        plot_df['Titular'] = df['titular']
        plot_df['Keywords'] = df['gpt_palabras_clave']
        plot_df['Resumen'] = df['gpt_resumen']
        
        # Create scatter plot
        fig = px.scatter(
            plot_df, 
            x='x', 
            y='y',
            color='Periódico',
            hover_data={
                'x': False,
                'y': False,
                'Periódico': True,
                'Titular': True,
                'Keywords': True,
                'Resumen': True
            },
            title='Mapa de Noticias'
        )
        
        # Update layout
        fig.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title='',
            yaxis_title='',
            height=800,
            template='plotly_dark'
        )
        
        # Convert to HTML
        plot_div = fig.to_html(
            full_html=False,
            include_plotlyjs=True,
            div_id='newsMap'
        )
        
        return render_template('mapa.html', plot_div=plot_div)
        
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}", exc_info=True)
        flash('Error al generar el mapa de noticias.', 'error')
        return render_template('mapa.html')
        SELECT 
            e.titulo as evento_titulo,
            e.descripcion as evento_descripcion,
            e.embeddings as evento_embeddings,
            a.titular,
            a.embeddings as articulo_embeddings,
            a.gpt_palabras_clave,
            a.gpt_resumen,
            p.nombre as periodico_nombre,
            c.nombre as categoria_nombre,
            s.nombre as subcategoria_nombre
        FROM evento e
        JOIN articulo_evento ae ON e.evento_id = ae.evento_id
        JOIN articulo a ON ae.articulo_id = a.articulo_id
        JOIN periodico p ON a.periodico_id = p.periodico_id
        LEFT JOIN subcategoria s ON e.subcategoria_id = s.subcategoria_id
        LEFT JOIN categoria c ON s.categoria_id = c.categoria_id
        WHERE a.fecha_publicacion BETWEEN :start_date AND :end_date
        '''
        
        result = db.session.execute(text(query), {
            'start_date': start_date,
            'end_date': end_date
        })
        
        # Convert result to DataFrame
        df = pd.DataFrame(result)
        
        if df.empty:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')
        
        # Process embeddings
        def parse_embedding(x):
            if pd.isna(x):
                return None
            try:
                if isinstance(x, str):
                    # Remove potential string artifacts and convert to list
                    clean_str = x.replace("'", '"').replace('\\', '')
                    if clean_str.startswith('"') and clean_str.endswith('"'):
                        clean_str = clean_str[1:-1]
                    return np.array(json.loads(clean_str))
                return x
            except:
                return None

        # Process embeddings
        df['embeddings'] = df['articulo_embeddings'].apply(parse_embedding)
        df = df.dropna(subset=['embeddings'])
        
        if len(df) < 2:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')

        # Convert embeddings to numpy array
        embeddings_array = np.stack(df['embeddings'].values)
        
        # Apply t-SNE
        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(embeddings_array)
        
        # Create visualization DataFrame
        plot_df = pd.DataFrame(embeddings_2d, columns=['x', 'y'])
        plot_df['Periódico'] = df['periodico_nombre']
        plot_df['Titular'] = df['titular']
        plot_df['Categoría'] = df['categoria_nombre']
        plot_df['Subcategoría'] = df['subcategoria_nombre']
        plot_df['Resumen'] = df['gpt_resumen']
        
        # Create scatter plot
        fig = px.scatter(
            plot_df, 
            x='x', 
            y='y',
            color='Periódico',
            hover_data={
                'x': False,
                'y': False,
                'Periódico': True,
                'Titular': True,
                'Categoría': True,
                'Subcategoría': True,
                'Resumen': True
            },
            title='Mapa de Noticias'
        )
        
        # Update layout
        fig.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title='',
            yaxis_title='',
            height=800
        )
        
        # Convert to HTML
        plot_div = fig.to_html(
            full_html=False,
            include_plotlyjs=True,
            div_id='newsMap'
        )
        
        return render_template('mapa.html', plot_div=plot_div)
        
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}", exc_info=True)
        flash('Error al generar el mapa de noticias.', 'error')
        return render_template('mapa.html')
def mapa():
    try:
        # Query recent articles with their embeddings
        query = '''
        SELECT c.nombre AS categoria, 
               s.nombre AS subcategoria, 
               e.titulo AS evento, 
               a.titular, 
               a.gpt_palabras_clave,
               a.palabras_clave_embeddings,
               e.embeddings,
               p.nombre AS periodico,
               a.gpt_resumen
        FROM articulo a
        LEFT JOIN articulo_evento ae ON a.articulo_id = ae.articulo_id
        FULL OUTER JOIN evento e ON ae.evento_id = e.evento_id
        LEFT JOIN subcategoria s ON e.subcategoria_id = s.subcategoria_id
        LEFT JOIN categoria c ON c.categoria_id = s.categoria_id
        LEFT JOIN evento_region er ON e.evento_id = er.evento_id
        LEFT JOIN region r ON er.region_id = r.region_id
        LEFT JOIN periodico p ON a.periodico_id = p.periodico_id
        WHERE a.updated_on >= NOW() - INTERVAL '3 days'
        '''
        
        df = pd.read_sql(query, db.engine)
        
        # Process embeddings
        def parse_embedding(x):
            try:
                if pd.isna(x):
                    return None
                if isinstance(x, str):
                    embedding = ast.literal_eval(x)
                    return np.array(embedding, dtype=float)
                return None
            except:
                return None

        df['embeddings'] = df['embeddings'].apply(parse_embedding)
        df = df.dropna(subset=['embeddings'])
        
        if len(df) == 0:
            flash('No hay suficientes datos para generar el mapa.', 'warning')
            return render_template('mapa.html')
            
        # Convert embeddings to numpy array
        embeddings_array = np.stack(df['embeddings'].values)
        
        # Use t-SNE for dimensionality reduction
        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(embeddings_array)
        
        # Create visualization dataframe
        plot_df = pd.DataFrame(embeddings_2d, columns=['Component 1', 'Component 2'])
        plot_df['Categoria'] = df['categoria']
        plot_df['Subcategoria'] = df['subcategoria']
        plot_df['Titular'] = df['titular']
        plot_df['Periodico'] = df['periodico']
        plot_df['Resumen'] = df['gpt_resumen']
        
        # Create scatter plot
        fig = px.scatter(
            plot_df,
            x='Component 1',
            y='Component 2',
            color='Periodico',
            hover_data={
                'Component 1': False,
                'Component 2': False,
                'Categoria': True,
                'Subcategoria': True,
                'Periodico': True,
                'Titular': True
            },
            title='Mapa de Noticias'
        )
        
        # Update layout
        fig.update_layout(
            showlegend=True,
            legend_title_text='Periódico',
            xaxis_title='',
            yaxis_title='',
            template='plotly_dark'
        )
        
        # Generate plot components
        plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return render_template(
            'mapa.html',
            plot_div=Markup(plot_json)
        )
        
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}", exc_info=True)
        flash('Error al generar el mapa de noticias.', 'error')
        return render_template('mapa.html')

        # Execute query
        events_results = events_query.order_by(
            desc(Evento.fecha_evento),
            desc(Articulo.fecha_publicacion)
        ).all()

        if not events_results:
            logger.warning(f"No events found for category_id={category_id}, subcategory_id={subcategory_id}")
            return jsonify({
                'categories': [{
                    'nombre': category_info.nombre if category_info else 'All Categories',
                    'categoria_id': category_id,
                    'subcategories': [{
                        'nombre': subcategory_info.nombre if subcategory_info else 'All Subcategories',
                        'subcategoria_id': subcategory_id,
                        'events': []
                    }]
                }]
            })

        # Process results
        events_dict = {}
        for result in events_results:
            evento_id = result[0]
            if evento_id not in events_dict:
                events_dict[evento_id] = {
                    'titulo': result[1],
                    'descripcion': result[2],
                    'fecha_evento': result[3].isoformat() if result[3] else None,
                    'gpt_sujeto_activo': result[4],
                    'gpt_sujeto_pasivo': result[5],
                    'gpt_importancia': result[6],
                    'gpt_tiene_contexto': result[7],
                    'gpt_palabras_clave': result[8],
                    'article_count': 0,
                    'articles': []
                }

            article_id = result[9]
            article_exists = any(a['id'] == article_id for a in events_dict[evento_id]['articles'])
            if not article_exists:
                events_dict[evento_id]['articles'].append({
                    'id': article_id,
                    'titular': result[10],
                    'url': result[11],
                    'fecha_publicacion': result[12].isoformat() if result[12] else None,
                    'paywall': result[13],
                    'gpt_opinion': result[14],
                    'periodico_nombre': result[15],
                    'periodico_logo': result[16]
                })
                events_dict[evento_id]['article_count'] += 1

        # Sort events by article count and date
        sorted_events = sorted(
            events_dict.values(),
            key=lambda x: (-x['article_count'], x['fecha_evento'] or '1900-01-01')
        )

        response_data = {
            'categories': [{
                'nombre': category_info.nombre if category_info else 'All Categories',
                'categoria_id': category_id,
                'subcategories': [{
                    'nombre': subcategory_info.nombre if subcategory_info else 'All Subcategories',
                    'subcategoria_id': subcategory_id,
                    'events': sorted_events
                }]
            }]
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/article/<int:article_id>')
def get_article(article_id):
    try:
        article = db.session.query(
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.subtitular,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.agencia,
            Articulo.paywall,
            Articulo.gpt_resumen,
            Articulo.gpt_opinion,
            Periodista.nombre.label('periodista_nombre'),
            Periodista.apellido.label('periodista_apellido'),
            Periodico.nombre.label('periodico_nombre'),
            Periodico.logo_url.label('periodico_logo')
        ).outerjoin(
            Periodista, cast(Articulo.periodista_id, String) == cast(Periodista.periodista_id, String)
        ).join(
            Periodico, Periodico.periodico_id == Articulo.periodico_id
        ).filter(
            Articulo.articulo_id == article_id
        ).first()

        if not article:
            logger.warning(f"Article not found: {article_id}")
            return jsonify({'error': 'Article not found'}), 404

        periodista_nombre = None
        if article.periodista_nombre and article.periodista_apellido:
            periodista_nombre = f"{article.periodista_nombre} {article.periodista_apellido}"

        return jsonify({
            'id': article.articulo_id,
            'titular': article.titular,
            'subtitular': article.subtitular,
            'url': article.url,
            'fecha_publicacion': article.fecha_publicacion.isoformat() if article.fecha_publicacion else None,
            'periodista': periodista_nombre,
            'agencia': article.agencia,
            'paywall': article.paywall,
            'gpt_resumen': article.gpt_resumen,
            'gpt_opinion': article.gpt_opinion,
            'periodico_nombre': article.periodico_nombre,
            'periodico_logo': article.periodico_logo
        })

    except Exception as e:
        logger.error(f"Error fetching article details: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)