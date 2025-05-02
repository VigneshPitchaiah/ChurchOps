from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_assets import Environment, Bundle
from flask_caching import Cache
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()
assets = Environment()
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})
cors = CORS()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    # Configure the app
    app.config.from_object('app.config.Config')
    
    # Initialize extensions with the app
    db.init_app(app)
    csrf.init_app(app)
    assets.init_app(app)
    cache.init_app(app)
    cors.init_app(app)
    
    # Register asset bundles
    css = Bundle(
        'css/normalize.css',
        'css/main.css',
        filters='cssmin',
        output='gen/packed.css'
    )
    js = Bundle(
        'js/main.js',
        filters='jsmin',
        output='gen/packed.js'
    )
    assets.register('css_all', css)
    assets.register('js_all', js)
    
    # Register blueprints
    from app.controllers.main import main_bp
    from app.controllers.services import services_bp
    from app.controllers.attendance import attendance_bp
    from app.controllers.saints import saints_bp
    from app.controllers.assignments import assignments_bp
    from app.controllers.reports import reports_bp
    from app.api.routes import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(saints_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Cache headers for better performance in low network areas
    @app.after_request
    def add_header(response):
        """Add cache headers for improved performance"""
        response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
        response.headers['Cache-Control'] = 'public, max-age=600'
        return response
        
    return app
