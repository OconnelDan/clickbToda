from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
import logging
import sys
from datetime import datetime, timedelta
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user is None or not user.check_password(request.form.get('password')):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('index'))
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = User(
            nombre=request.form.get('nombre'),
            email=request.form.get('email')
        )
        user.set_password(request.form.get('password'))
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Error registering user')
            return redirect(url_for('register'))
    return render_template('auth/register.html')

@app.route('/')
def index():
    try:
        time_filter = request.args.get('time_filter', '24h')
        hours = int(time_filter[:-1])
        hide_paywall = request.args.get('hide_paywall', 'true').lower() == 'true'

        # Get categories with article counts
        query = text('''
            WITH ArticleCounts AS (
                SELECT 
                    c.categoria_id, 
                    c.nombre AS categoria_nombre,
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) AS article_count
                FROM 
                    app.categoria c
                LEFT JOIN app.subcategoria s ON s.categoria_id = c.categoria_id
                LEFT JOIN app.evento e ON e.subcategoria_id = s.subcategoria_id
                LEFT JOIN app.articulo_evento ae ON e.evento_id = ae.evento_id
                LEFT JOIN app.articulo a ON ae.articulo_id = a.articulo_id 
                    AND a.updated_on >= CURRENT_TIMESTAMP - (:hours || ' hours')::interval
                    AND a.updated_on <= CURRENT_TIMESTAMP
                GROUP BY 
                    c.categoria_id, 
                    c.nombre
                HAVING 
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) > 0
                ORDER BY 
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) DESC
            )
            SELECT 
                c.*,
                json_build_object(
                    'Categoria', json_build_object(
                        'categoria_id', c.categoria_id,
                        'nombre', c.categoria_nombre
                    ),
                    'article_count', c.article_count
                ) as category_data
            FROM 
                ArticleCounts c
        ''')

        result = db.session.execute(query, {
            'hours': hours,
            'include_paywall': not hide_paywall
        })

        categories = [row.category_data for row in result]
        
        return render_template('index.html', 
                           categories=categories,
                           initial_data=None,
                           selected_date=datetime.now().date())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', categories=[], selected_date=datetime.now().date())

@app.route('/api/navigation')
def get_navigation():
    try:
        time_filter = request.args.get('time_filter', '24h')
        hours = int(time_filter[:-1])
        hide_paywall = request.args.get('hide_paywall', 'true').lower() == 'true'
        
        query = text('''
            WITH ArticleCounts AS (
                SELECT 
                    c.categoria_id, 
                    c.nombre AS categoria_nombre, 
                    s.subcategoria_id, 
                    s.nombre AS subcategoria_nombre,
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) AS cuenta_articulos_subcategoria
                FROM 
                    app.categoria c
                LEFT JOIN app.subcategoria s ON s.categoria_id = c.categoria_id
                LEFT JOIN app.evento e ON e.subcategoria_id = s.subcategoria_id
                LEFT JOIN app.articulo_evento ae ON e.evento_id = ae.evento_id
                LEFT JOIN app.articulo a ON ae.articulo_id = a.articulo_id 
                    AND a.updated_on >= CURRENT_TIMESTAMP - (:hours || ' hours')::interval
                    AND a.updated_on <= CURRENT_TIMESTAMP
                GROUP BY 
                    c.categoria_id, 
                    c.nombre, 
                    s.subcategoria_id, 
                    s.nombre
                HAVING 
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) > 0
            ),
            CategoryTotals AS (
                SELECT
                    categoria_id,
                    SUM(cuenta_articulos_subcategoria) as cuenta_articulos_categoria
                FROM
                    ArticleCounts
                GROUP BY
                    categoria_id
            )
            SELECT 
                ac.*,
                ct.cuenta_articulos_categoria
            FROM 
                ArticleCounts ac
            JOIN 
                CategoryTotals ct ON ac.categoria_id = ct.categoria_id
            ORDER BY 
                ct.cuenta_articulos_categoria DESC,
                ac.cuenta_articulos_subcategoria DESC NULLS LAST
        ''')
        
        result = db.session.execute(query, {
            'hours': hours,
            'include_paywall': not hide_paywall
        })
        
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
            
            if row.subcategoria_id and row.cuenta_articulos_subcategoria > 0:
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
        time_filter = request.args.get('time_filter', '24h')
        hours = int(time_filter[:-1])
        hide_paywall = request.args.get('hide_paywall', 'true').lower() == 'true'

        if not category_id:
            return jsonify([])
        
        query = text('''
            WITH SubcategoryCounts AS (
                SELECT 
                    s.subcategoria_id as id,
                    s.nombre,
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) as article_count,
                    COUNT(DISTINCT e.evento_id) as event_count
                FROM 
                    app.subcategoria s
                LEFT JOIN app.evento e ON e.subcategoria_id = s.subcategoria_id
                LEFT JOIN app.articulo_evento ae ON e.evento_id = ae.evento_id
                LEFT JOIN app.articulo a ON ae.articulo_id = a.articulo_id 
                    AND a.updated_on >= CURRENT_TIMESTAMP - (:hours || ' hours')::interval
                    AND a.updated_on <= CURRENT_TIMESTAMP
                WHERE 
                    s.categoria_id = :category_id
                GROUP BY 
                    s.subcategoria_id,
                    s.nombre
                HAVING 
                    COUNT(DISTINCT CASE WHEN a.paywall = FALSE OR :include_paywall THEN a.articulo_id END) > 0
            )
            SELECT *
            FROM SubcategoryCounts
            ORDER BY 
                article_count DESC,
                event_count DESC,
                nombre ASC
        ''')
        
        result = db.session.execute(query, {
            'category_id': category_id,
            'hours': hours,
            'include_paywall': not hide_paywall
        })
        
        subcategories = [{
            'id': row.id,
            'nombre': row.nombre,
            'article_count': row.article_count
        } for row in result]
        
        return jsonify(subcategories)
    except Exception as e:
        logger.error(f"Error in get_subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles')
def get_articles():
    try:
        category_id = request.args.get('category_id')
        subcategory_id = request.args.get('subcategory_id')
        time_filter = request.args.get('time_filter', '24h')
        hours = int(time_filter[:-1])
        hide_paywall = request.args.get('hide_paywall', 'true').lower() == 'true'
        
        base_query = '''
            WITH EventArticles AS (
                SELECT 
                    e.evento_id,
                    e.titulo as event_titulo,
                    e.descripcion as event_descripcion,
                    e.fecha_evento,
                    s.subcategoria_id,
                    s.nombre as subcategoria_nombre,
                    c.categoria_id,
                    c.nombre as categoria_nombre,
                    json_agg(
                        json_build_object(
                            'id', a.articulo_id,
                            'titular', a.titular,
                            'url', a.url,
                            'paywall', a.paywall,
                            'periodico_logo', p.logo_url,
                            'gpt_opinion', a.gpt_opinion
                        ) ORDER BY a.updated_on DESC
                    ) FILTER (WHERE a.articulo_id IS NOT NULL) as articles
                FROM 
                    app.evento e
                JOIN app.subcategoria s ON s.subcategoria_id = e.subcategoria_id
                JOIN app.categoria c ON c.categoria_id = s.categoria_id
                LEFT JOIN app.articulo_evento ae ON e.evento_id = ae.evento_id
                LEFT JOIN app.articulo a ON ae.articulo_id = a.articulo_id 
                    AND a.updated_on >= CURRENT_TIMESTAMP - (:hours || ' hours')::interval
                    AND a.updated_on <= CURRENT_TIMESTAMP
                    AND (NOT a.paywall OR :include_paywall)
                LEFT JOIN app.periodico p ON a.periodico_id = p.periodico_id
                WHERE 1=1
        '''
        
        params = {
            'hours': hours,
            'include_paywall': not hide_paywall
        }
        
        if category_id:
            base_query += ' AND c.categoria_id = :category_id'
            params['category_id'] = category_id
            
        if subcategory_id:
            base_query += ' AND s.subcategoria_id = :subcategory_id'
            params['subcategory_id'] = subcategory_id
            
        base_query += '''
                GROUP BY 
                    e.evento_id,
                    e.titulo,
                    e.descripcion,
                    e.fecha_evento,
                    s.subcategoria_id,
                    s.nombre,
                    c.categoria_id,
                    c.nombre
                HAVING 
                    COUNT(DISTINCT CASE WHEN NOT a.paywall OR :include_paywall THEN a.articulo_id END) > 0
            ),
            SubcategoryEvents AS (
                SELECT 
                    ea.categoria_id,
                    ea.categoria_nombre,
                    ea.subcategoria_id,
                    ea.subcategoria_nombre,
                    json_agg(
                        json_build_object(
                            'evento_id', ea.evento_id,
                            'titulo', ea.event_titulo,
                            'descripcion', ea.event_descripcion,
                            'fecha_evento', ea.fecha_evento,
                            'articles', ea.articles
                        ) ORDER BY ea.fecha_evento DESC
                    ) as events,
                    COUNT(DISTINCT 
                        CASE WHEN ea.articles IS NOT NULL 
                        THEN jsonb_array_elements(ea.articles::jsonb)->>'id' 
                        END
                    ) as article_count
                FROM EventArticles ea
                GROUP BY 
                    ea.categoria_id,
                    ea.categoria_nombre,
                    ea.subcategoria_id,
                    ea.subcategoria_nombre
            )
            SELECT 
                se.categoria_id,
                se.categoria_nombre as nombre,
                json_agg(
                    json_build_object(
                        'subcategoria_id', se.subcategoria_id,
                        'nombre', se.subcategoria_nombre,
                        'events', se.events,
                        'article_count', se.article_count
                    ) ORDER BY se.article_count DESC
                ) as subcategories,
                SUM(se.article_count) as total_articles
            FROM SubcategoryEvents se
            GROUP BY 
                se.categoria_id,
                se.categoria_nombre
            ORDER BY 
                SUM(se.article_count) DESC
        '''
        
        query = text(base_query)
        result = db.session.execute(query, params)
        
        categories = [{
            'categoria_id': row.categoria_id,
            'nombre': row.nombre,
            'subcategories': row.subcategories,
            'article_count': row.total_articles
        } for row in result]
        
        return jsonify({'categories': categories})
    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
