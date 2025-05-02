from flask import Blueprint, render_template, current_app
from datetime import datetime
from app.services.cache_service import cache_view

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@cache_view(timeout=60)  # Cache the home page for 1 minute
def index():
    """Home page with login option"""
    return render_template('main/index.html', now=datetime.now())
