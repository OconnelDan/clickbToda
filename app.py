from flask import Flask, render_template, request, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import desc, cast, String, and_
import numpy as np
from sklearn.manifold import TSNE
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from database import db
from models import User, Articulo, Categoria, Subcategoria, Evento, Periodico, articulo_evento, Periodista
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
import numpy as np
from sklearn.manifold import TSNE
import json
import logging
from datetime import datetime, timedelta
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc
from sklearn.manifold import TSNE
import numpy as np
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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

# Required imports for t-SNE visualization
import numpy as np
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from collections import Counter
import plotly.express as px
import json
import ast
from statistics import mode

@app.route('/mapa')
def mapa():
    """Render the map visualization page."""
    try:
        time_filter = request.args.get('time_filter', '72h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Count articles with valid embeddings
        articles_count = db.session.query(Articulo).filter(
            Articulo.fecha_publicacion.between(start_date, end_date),
            Articulo.embeddings.isnot(None)
        ).count()

        return render_template('mapa.html', articles_count=articles_count)
    except Exception as e:
        logger.error(f"Error in mapa route: {str(e)}")
        return render_template('mapa.html', articles_count=0)

from flask import jsonify, request
from datetime import datetime, timedelta
import numpy as np
import ast
import json
from collections import Counter
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sqlalchemy.orm import joinedload
from statistics import mode
from sqlalchemy import func
import logging

def parse_embedding(embedding_str):
    try:
        if not embedding_str or embedding_str.strip() in ['[]', '{}', '""']:
            logger.warning("Embedding vacío o inválido")
            return None
            
        # Limpiar el string
        cleaned = embedding_str.strip()
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
            
        # Intentar diferentes formatos de parsing
        try:
            # Intentar como JSON
            embedding = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                # Intentar como lista literal de Python
                embedding = ast.literal_eval(cleaned)
            except:
                # Intentar como string de números separados por coma
                embedding = [float(x.strip()) for x in cleaned.strip('{}[]').split(',') if x.strip()]
        
        # Convertir a numpy array
        if isinstance(embedding, (list, tuple)):
            return np.array(embedding, dtype=float)
        elif isinstance(embedding, dict):
            return np.array(list(embedding.values()), dtype=float)
            
        raise ValueError(f"Formato de embedding no reconocido: {type(embedding)}")
        
    except Exception as e:
        logger.error(f"Error procesando embedding: {str(e)}")
        return None

@app.route('/api/mapa-data', methods=['GET'])
def get_mapa_data():
    """Generate t-SNE visualization data from article embeddings."""
    try:
        # Parse time filter
        time_filter = request.args.get('time_filter', '72h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        logging.info(f"Fetching articles between {start_date} and {end_date}")

        logger.info(f"Buscando artículos entre {start_date} y {end_date}")
        
        # Query base para artículos con embeddings
        articles_query = db.session.query(
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.palabras_clave_embeddings,  # Cambiar embeddings por palabras_clave_embeddings
            Articulo.gpt_palabras_clave,
            Articulo.gpt_resumen,
            Periodico.nombre.label('periodico_nombre'),
            Categoria.nombre.label('categoria_nombre'),
            Subcategoria.nombre.label('subcategoria_nombre')
        ).join(
            Periodico,
            Articulo.periodico_id == Periodico.periodico_id
        ).outerjoin(
            articulo_evento,
            Articulo.articulo_id == articulo_evento.c.articulo_id
        ).outerjoin(
            Evento,
            articulo_evento.c.evento_id == Evento.evento_id
        ).outerjoin(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).outerjoin(
            Categoria,
            Subcategoria.categoria_id == Categoria.categoria_id
        ).filter(
            Articulo.updated_on.between(start_date, end_date)
        )
        
        # Log total de artículos antes de filtrar por embeddings
        total_articles = articles_query.count()
        logger.info(f"Total de artículos encontrados: {total_articles}")
        
        # Agregar filtro de embeddings
        articles = articles_query.filter(
            Articulo.palabras_clave_embeddings.isnot(None),
            Articulo.palabras_clave_embeddings != '',
            func.length(Articulo.palabras_clave_embeddings) > 2  # Asegurar que no sea '[]' o '{}'
        ).all()
        
        logger.info(f"Artículos con embeddings: {len(articles)}")
        
        # Log de muestra de embeddings
        if articles:
            sample_embedding = articles[0].palabras_clave_embeddings
            logger.info(f"Muestra de embedding: {sample_embedding[:100]}")

        if not articles:
            logging.warning("No articles found with valid embeddings")
            return jsonify({
                'error': 'no_articles',
                'message': 'No se encontraron artículos con embeddings válidos para el período seleccionado'
            })

        embeddings_list = []
        articles_data = []
        valid_count = 0
        error_count = 0

        for article in articles:
            try:
                embedding = parse_embedding(article.palabras_clave_embeddings)
                if embedding is not None and embedding.size > 0:
                    embeddings_list.append(embedding)
                    articles_data.append({
                        'id': article.articulo_id,
                        'titular': article.titular,
                        'periodico': article.periodico_nombre,
                        'categoria': article.categoria_nombre,
                        'subcategoria': article.subcategoria_nombre,
                        'keywords': article.gpt_palabras_clave,
                        'resumen': article.gpt_resumen
                    })
                    valid_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Error procesando artículo {article.articulo_id}: {str(e)}")

        logger.info(f"Procesamiento completado: {valid_count} válidos, {error_count} errores")

        if not embeddings_list:
            return jsonify({
                'error': 'no_articles',
                'message': 'No se encontraron artículos con embeddings válidos'
            })

        # Pad or trim embeddings to a consistent size
        embedding_lengths = [len(emb) for emb in embeddings_list]
        target_length = mode(embedding_lengths)

        def pad_embedding(embedding, target_length):
            if len(embedding) < target_length:
                return np.pad(embedding, (0, target_length - len(embedding)), mode='constant')
            return embedding[:target_length]

        embeddings_array = np.vstack([pad_embedding(emb, target_length) for emb in embeddings_list])

        # Perform t-SNE
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings_array) - 1))
        embeddings_2d = tsne.fit_transform(embeddings_array)

        # Perform clustering
        n_clusters = min(16, len(embeddings_array))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(embeddings_2d)

        # Get cluster centers and top keywords
        cluster_centers = kmeans.cluster_centers_
        cluster_keywords = {}
        for i in range(n_clusters):
            cluster_mask = clusters == i
            cluster_articles = [
                article['keywords'] for idx, article in enumerate(articles_data) if cluster_mask[idx]
            ]
            if cluster_articles:
                all_keywords = [kw.strip() for kws in cluster_articles if kws for kw in kws.split(',')]
                top_keyword = Counter(all_keywords).most_common(1)[0][0] if all_keywords else 'Sin keyword'
                cluster_keywords[i] = {
                    'keyword': top_keyword,
                    'center': cluster_centers[i].tolist()
                }

        # Prepare response
        points = [
            {
                'id': article['id'],
                'coordinates': embeddings_2d[i].tolist(),
                'titular': article['titular'],
                'periodico': article['periodico'],
                'categoria': article['categoria'],
                'subcategoria': article['subcategoria'],
                'keywords': article['keywords'],
                'resumen': article['resumen'],
                'cluster': int(clusters[i])
            }
            for i, article in enumerate(articles_data)
        ]

        clusters = [
            {
                'id': cluster_id,
                'keyword': cluster_info['keyword'],
                'center': cluster_info['center']
            }
            for cluster_id, cluster_info in cluster_keywords.items()
        ]

        return jsonify({'points': points, 'clusters': clusters})

    except Exception as e:
        logging.error(f"Error generating map data: {str(e)}")
        return jsonify({'error': 'processing_error', 'message': 'Error interno en el servidor'}), 500



@app.route('/api/articles')
def get_articles():
    try:
        time_filter = request.args.get('time_filter', '72h')
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Get category and subcategory info if provided
        category_info = None
        subcategory_info = None
        if category_id:
            category_info = db.session.query(
                Categoria.categoria_id,
                Categoria.nombre
            ).filter(
                Categoria.categoria_id == category_id
            ).first()
            
            if not category_info:
                return jsonify({'error': 'Category not found'}), 404
            
        if subcategory_id:
            subcategory_info = db.session.query(
                Subcategoria.subcategoria_id,
                Subcategoria.nombre
            ).filter(
                Subcategoria.subcategoria_id == subcategory_id
            ).first()
            
            if not subcategory_info:
                return jsonify({'error': 'Subcategory not found'}), 404

        # Query events with related articles
        events_query = db.session.query(
            Evento.evento_id,
            Evento.titulo,
            Evento.descripcion,
            Evento.fecha_evento,
            Evento.gpt_sujeto_activo,
            Evento.gpt_sujeto_pasivo,
            Evento.gpt_importancia,
            Evento.gpt_tiene_contexto,
            Evento.gpt_palabras_clave,
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.paywall,
            Articulo.gpt_opinion,
            Periodico.nombre,
            Periodico.logo_url
        ).join(
            Subcategoria, Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento, articulo_evento.c.evento_id == Evento.evento_id
        ).join(
            Articulo, and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).join(
            Periodico, Periodico.periodico_id == Articulo.periodico_id
        )

        # Apply filters
        if category_id == 0:  # "All" category
            # Remove category filter
            events_query = events_query
        elif category_id:
            events_query = events_query.filter(Subcategoria.categoria_id == category_id)
        if subcategory_id:
            events_query = events_query.filter(Subcategoria.subcategoria_id == subcategory_id)

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