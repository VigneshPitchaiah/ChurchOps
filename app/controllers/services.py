from flask import Blueprint, render_template, request, current_app
from datetime import datetime
from app import db, cache
from app.models.services import Service, ServiceType
from app.services.cache_service import cache_view
from sqlalchemy import desc

# Create blueprint
services_bp = Blueprint('services', __name__, url_prefix='/services')

@services_bp.route('/')
@cache_view(timeout=30)  # Cache services page for 30 seconds
def services_list():
    """Show services based on filter (upcoming or previous)"""
    # Get view parameter from request (default to 'upcoming')
    view_type = request.args.get('view', 'upcoming')
    today = datetime.now().date()
    
    # Base query joining with ServiceType
    query = Service.query.join(ServiceType)
    
    # Filter and order based on view type
    if view_type == 'previous':
        # Previous services (before today)
        services = query.filter(
            Service.service_date < today
        ).order_by(desc(Service.service_date), desc(Service.service_time)).limit(20).all()
        page_title = 'Previous Services'
    else:
        # Upcoming services (today and future)
        services = query.filter(
            Service.service_date >= today
        ).order_by(Service.service_date, Service.service_time).limit(20).all()
        page_title = 'Upcoming Services'
    
    return render_template('services/index.html', 
                          services=services, 
                          now=datetime.now(),
                          view_type=view_type,
                          page_title=page_title)
