from flask import Blueprint, render_template, request, current_app
from datetime import datetime
from app import db, cache
from app.models.services import Service, ServiceType
from app.services.cache_service import cache_view

# Create blueprint
services_bp = Blueprint('services', __name__, url_prefix='/services')

@services_bp.route('/')
@cache_view(timeout=30)  # Cache services page for 30 seconds
def services_list():
    """Show upcoming services"""
    # Get today's and upcoming services with SQLAlchemy
    services = Service.query.join(ServiceType).filter(
        Service.service_date >= datetime.now().date()
    ).order_by(Service.service_date, Service.service_time).limit(20).all()
    
    return render_template('services/index.html', services=services, now=datetime.now())
