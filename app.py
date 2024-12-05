import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, cast, String, and_, func
import numpy as np
from sklearn.metrics.pairwise import cosine_distances
import pandas as pd
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models after db initialization
from models import Articulo, Periodico, Categoria, Subcategoria, Evento, articulo_evento, Periodista

@app.route('/api/article-updates')
def get_article_updates():
    try:
        since = request.args.get('since')
        if not since:
            return jsonify({'error': 'Missing since parameter'}), 400

        since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
        
        # Query articles that have been updated since the last check
        updated_articles = db.session.query(
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.updated_on
        ).filter(
            Articulo.updated_on > since_date
        ).order_by(
            desc(Articulo.updated_on)
        ).limit(10).all()  # Limit to prevent overwhelming notifications
        
        updates = [{
            'articulo_id': article.articulo_id,
            'titular': article.titular,
            'updated_on': article.updated_on.isoformat()
        } for article in updated_articles]
        
        return jsonify(updates)
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        logger.error(f"Error fetching article updates: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def safe_parse_embeddings(x):
    if x is None or not isinstance(x, str):
        return np.array([])
    try:
        return np.fromstring(x.strip('{}'), sep=',')
    except Exception:
        return np.array([])

@app.route('/api/mapa-data')
def get_mapa_data():
    """Generate t-SNE visualization data from article embeddings using cosine distances."""
    try:
        # Parse time filter
        time_filter = request.args.get('time_filter', '72h')
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        logger.info(f"Buscando artículos entre {start_date} y {end_date}")
        
        # Query base para artículos con embeddings
        articles_query = db.session.query(
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.palabras_clave_embeddings,
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

        # Add embeddings filter
        articles = articles_query.filter(
            Articulo.palabras_clave_embeddings.isnot(None),
            Articulo.palabras_clave_embeddings != '',
            func.length(Articulo.palabras_clave_embeddings) > 2
        ).all()

        if not articles:
            return jsonify({
                'error': 'no_articles',
                'message': 'No se encontraron artículos con embeddings válidos'
            })

        # Process articles and create visualization data
        embeddings_list = []
        articles_data = []

        for article in articles:
            try:
                embedding = safe_parse_embeddings(article.palabras_clave_embeddings)
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
            except Exception as e:
                logger.error(f"Error processing article {article.articulo_id}: {str(e)}")

        if not embeddings_list:
            return jsonify({
                'error': 'no_articles',
                'message': 'No se encontraron artículos con embeddings válidos'
            })

        # Create visualization data
        embeddings_array = np.vstack(embeddings_list)
        distance_matrix = cosine_distances(embeddings_array)

        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(distance_matrix)

        # Prepare response
        points = [
            {
                'id': article['id'],
                'coordinates': embeddings_2d[i].tolist(),
                'titular': article['titular'],
                'categoria': article['categoria'],
                'subcategoria': article['subcategoria'],
                'keywords': article['keywords'],
                'resumen': article['resumen']
            }
            for i, article in enumerate(articles_data)
        ]

        return jsonify({'points': points})

    except Exception as e:
        logger.error(f"Error generating map data: {str(e)}")
        return jsonify({'error': 'processing_error', 'message': str(e)}), 500

@app.route('/api/articles')
def get_articles():
    try:
        time_filter = request.args.get('time_filter', '72h')
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)
        sort_direction = request.args.get('sort_direction', 'desc')

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=int(time_filter[:-1]))

        # Get category and subcategory info if present
        category_info = None
        subcategory_info = None
        
        if category_id:
            category_info = db.session.query(
                Categoria.categoria_id,
                Categoria.nombre
            ).filter(
                Categoria.categoria_id == category_id
            ).first()

        if subcategory_id:
            subcategory_info = db.session.query(
                Subcategoria.subcategoria_id,
                Subcategoria.nombre
            ).filter(
                Subcategoria.subcategoria_id == subcategory_id
            ).first()

        # Query events and related articles
        events_query = db.session.query(
            Evento.evento_id,
            Evento.titulo,
            Evento.descripcion,
            Evento.fecha_evento,
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.paywall,
            Periodico.nombre,
            Periodico.logo_url
        ).join(
            Subcategoria,
            Evento.subcategoria_id == Subcategoria.subcategoria_id
        ).join(
            articulo_evento,
            articulo_evento.c.evento_id == Evento.evento_id
        ).join(
            Articulo,
            and_(
                Articulo.articulo_id == articulo_evento.c.articulo_id,
                Articulo.fecha_publicacion.between(start_date, end_date)
            )
        ).join(
            Periodico,
            Periodico.periodico_id == Articulo.periodico_id
        )

        # Apply filters
        if category_id and category_id != 0:
            events_query = events_query.filter(Subcategoria.categoria_id == category_id)
        if subcategory_id:
            events_query = events_query.filter(Subcategoria.subcategoria_id == subcategory_id)

        # Sort by publication date
        if sort_direction == 'asc':
            events_query = events_query.order_by(Articulo.fecha_publicacion)
        else:
            events_query = events_query.order_by(desc(Articulo.fecha_publicacion))

        events = events_query.all()

        # Process results
        events_dict = {}
        for event in events:
            if event.evento_id not in events_dict:
                events_dict[event.evento_id] = {
                    'titulo': event.titulo,
                    'descripcion': event.descripcion,
                    'fecha_evento': event.fecha_evento.isoformat() if event.fecha_evento else None,
                    'articles': []
                }

            events_dict[event.evento_id]['articles'].append({
                'id': event.articulo_id,
                'titular': event.titular,
                'url': event.url,
                'fecha_publicacion': event.fecha_publicacion.isoformat(),
                'paywall': event.paywall,
                'periodico_nombre': event.nombre,
                'periodico_logo': event.logo_url
            })

        return jsonify({
            'categories': [{
                'nombre': category_info.nombre if category_info else 'All Categories',
                'categoria_id': category_id,
                'subcategories': [{
                    'nombre': subcategory_info.nombre if subcategory_info else 'All Subcategories',
                    'subcategoria_id': subcategory_id,
                    'events': list(events_dict.values())
                }]
            }]
        })

    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/article/<int:article_id>')
def get_article(article_id):
    try:
        article = db.session.query(
            Articulo.articulo_id,
            Articulo.titular,
            Articulo.subtitular,
            Articulo.url,
            Articulo.fecha_publicacion,
            Articulo.updated_on,
            Articulo.agencia,
            Articulo.paywall,
            Articulo.gpt_resumen,
            Periodista.nombre.label('periodista_nombre'),
            Periodista.apellido.label('periodista_apellido'),
            Periodico.nombre.label('periodico_nombre'),
            Periodico.logo_url.label('periodico_logo')
        ).outerjoin(
            Periodista,
            cast(Articulo.periodista_id, String) == cast(Periodista.periodista_id, String)
        ).join(
            Periodico,
            Periodico.periodico_id == Articulo.periodico_id
        ).filter(
            Articulo.articulo_id == article_id
        ).first()

        if not article:
            return jsonify({'error': 'Article not found'}), 404

        return jsonify({
            'id': article.articulo_id,
            'titular': article.titular,
            'subtitular': article.subtitular,
            'url': article.url,
            'fecha_publicacion': article.fecha_publicacion.isoformat() if article.fecha_publicacion else None,
            'updated_on': article.updated_on.isoformat() if article.updated_on else None,
            'periodista': f"{article.periodista_nombre} {article.periodista_apellido}" if article.periodista_nombre and article.periodista_apellido else None,
            'agencia': article.agencia,
            'paywall': article.paywall,
            'gpt_resumen': article.gpt_resumen,
            'periodico_nombre': article.periodico_nombre,
            'periodico_logo': article.periodico_logo
        })

    except Exception as e:
        logger.error(f"Error fetching article details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)