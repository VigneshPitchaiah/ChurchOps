from flask import Blueprint, render_template, request, jsonify

from app import db, cache
from app.models.services import Service, ServiceType, Attendance
from app.models.people import Person
from app.models.organization import Region, Direction, Department, Team, Cell
from sqlalchemy import func, desc
from app.services.cache_service import cache_view
from datetime import datetime, timedelta

# Create blueprint
reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')

@cache_view(timeout=60)
def reports_index():
    """Show report options"""
    # Get service types for filtering
    service_types = ServiceType.query.order_by(ServiceType.service_name).all()
    
    # Get organizational units for filtering
    regions = Region.query.order_by(Region.region_name).all()
    
    return render_template(
        'reports/index.html',
        service_types=service_types,
        regions=regions,
        now=datetime.now()
    )

@reports_bp.route('/attendance-by-date')

@cache_view(timeout=60)
def attendance_by_date():
    """Get attendance statistics by date"""
    # Parse date range parameters
    days = request.args.get('days', 30, type=int)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get service type filter
    service_type_id = request.args.get('service_type_id', type=int)
    
    # Build query
    query = db.session.query(
        Service.service_date,
        ServiceType.service_name,
        func.count(Attendance.attendance_id).label('count')
    ).join(
        ServiceType
    ).join(
        Attendance, Service.service_id == Attendance.service_id
    ).filter(
        Service.service_date.between(start_date, end_date)
    ).group_by(
        Service.service_date, 
        ServiceType.service_name
    ).order_by(
        Service.service_date
    )
    
    # Apply service type filter if provided
    if service_type_id:
        query = query.filter(ServiceType.service_type_id == service_type_id)
    
    # Execute query
    results = query.all()
    
    # Format data for chart
    dates = []
    service_types = {}
    
    for date, service_name, count in results:
        # Format date
        formatted_date = date.strftime('%d %b')
        if formatted_date not in dates:
            dates.append(formatted_date)
        
        # Organize by service type
        if service_name not in service_types:
            service_types[service_name] = [0] * len(dates)
        
        # Update count
        service_types[service_name][dates.index(formatted_date)] = count
    
    # Prepare chart data
    chart_data = {
        'labels': dates,
        'datasets': [
            {
                'label': service_name,
                'data': counts,
                'fill': False,
                'borderColor': f'hsl({(i * 137) % 360}, 70%, 50%)'  # Generate distinct colors
            }
            for i, (service_name, counts) in enumerate(service_types.items())
        ]
    }
    
    return render_template(
        'reports/attendance_by_date.html',
        chart_data=chart_data,
        days=days,
        now=datetime.now()
    )

@reports_bp.route('/attendance-by-department')

@cache_view(timeout=60)
def attendance_by_department():
    """Get attendance statistics by department"""
    # Parse date range parameters
    days = request.args.get('days', 30, type=int)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get filters
    service_type_id = request.args.get('service_type_id', type=int)
    region_id = request.args.get('region_id', type=int)
    
    # Build query for department attendance
    query = db.session.query(
        Department.department_name,
        func.count(Attendance.attendance_id).label('count')
    ).join(
        Person, Attendance.person_id == Person.person_id
    ).join(
        Cell, Person.cell_id == Cell.cell_id
    ).join(
        Team, Cell.team_id == Team.team_id
    ).join(
        Department, Team.department_id == Department.department_id
    ).join(
        Direction, Department.direction_id == Direction.direction_id
    ).join(
        Region, Direction.region_id == Region.region_id
    ).join(
        Service, Attendance.service_id == Service.service_id
    ).filter(
        Service.service_date.between(start_date, end_date)
    ).group_by(
        Department.department_name
    ).order_by(
        desc('count')
    )
    
    # Apply service type filter if provided
    if service_type_id:
        query = query.join(ServiceType, Service.service_type_id == ServiceType.service_type_id).filter(
            ServiceType.service_type_id == service_type_id
        )
    
    # Apply region filter if provided
    if region_id:
        query = query.filter(Region.region_id == region_id)
    
    # Execute query
    results = query.all()
    
    # Format data for chart
    departments = [r[0] for r in results]
    counts = [r[1] for r in results]
    
    # Prepare chart data
    chart_data = {
        'labels': departments,
        'datasets': [
            {
                'label': 'Attendance Count',
                'data': counts,
                'backgroundColor': [
                    f'hsl({(i * 137) % 360}, 70%, 50%)' for i in range(len(departments))
                ]
            }
        ]
    }
    
    return render_template(
        'reports/attendance_by_department.html',
        chart_data=chart_data,
        days=days,
        now=datetime.now()
    )

@reports_bp.route('/api/attendance-data')

def api_attendance_data():
    """API endpoint for attendance data"""
    # Parse date range parameters
    days = request.args.get('days', 30, type=int)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get filters
    service_type_id = request.args.get('service_type_id', type=int)
    region_id = request.args.get('region_id', type=int)
    direction_id = request.args.get('direction_id', type=int)
    department_id = request.args.get('department_id', type=int)
    team_id = request.args.get('team_id', type=int)
    cell_id = request.args.get('cell_id', type=int)
    
    # Get report type
    report_type = request.args.get('type', 'date')
    
    # Build base query
    if report_type == 'date':
        query = db.session.query(
            Service.service_date,
            ServiceType.service_name,
            func.count(Attendance.attendance_id).label('count')
        ).join(
            ServiceType
        ).join(
            Attendance, Service.service_id == Attendance.service_id
        ).filter(
            Service.service_date.between(start_date, end_date)
        ).group_by(
            Service.service_date, 
            ServiceType.service_name
        ).order_by(
            Service.service_date
        )
    
    elif report_type == 'department':
        query = db.session.query(
            Department.department_name,
            func.count(Attendance.attendance_id).label('count')
        ).join(
            Person, Attendance.person_id == Person.person_id
        ).join(
            Cell, Person.cell_id == Cell.cell_id
        ).join(
            Team, Cell.team_id == Team.team_id
        ).join(
            Department, Team.department_id == Department.department_id
        ).join(
            Service, Attendance.service_id == Service.service_id
        ).filter(
            Service.service_date.between(start_date, end_date)
        ).group_by(
            Department.department_name
        ).order_by(
            desc('count')
        )
    
    elif report_type == 'team':
        query = db.session.query(
            Team.team_name,
            func.count(Attendance.attendance_id).label('count')
        ).join(
            Person, Attendance.person_id == Person.person_id
        ).join(
            Cell, Person.cell_id == Cell.cell_id
        ).join(
            Team, Cell.team_id == Team.team_id
        ).join(
            Service, Attendance.service_id == Service.service_id
        ).filter(
            Service.service_date.between(start_date, end_date)
        ).group_by(
            Team.team_name
        ).order_by(
            desc('count')
        )
    
    # Apply filters
    if service_type_id and report_type != 'date':
        query = query.join(ServiceType, Service.service_type_id == ServiceType.service_type_id).filter(
            ServiceType.service_type_id == service_type_id
        )
    elif service_type_id:
        query = query.filter(ServiceType.service_type_id == service_type_id)
    
    if region_id:
        query = query.join(
            Direction, Department.direction_id == Direction.direction_id
        ).join(
            Region, Direction.region_id == Region.region_id
        ).filter(
            Region.region_id == region_id
        )
    
    if direction_id:
        if 'Direction' not in str(query):
            query = query.join(
                Direction, Department.direction_id == Direction.direction_id
            )
        query = query.filter(Direction.direction_id == direction_id)
    
    if department_id and report_type not in ['department']:
        query = query.filter(Department.department_id == department_id)
    
    if team_id and report_type not in ['team']:
        query = query.filter(Team.team_id == team_id)
    
    if cell_id:
        query = query.filter(Cell.cell_id == cell_id)
    
    # Execute query
    results = query.all()
    
    # Format response based on report type
    if report_type == 'date':
        # Format data for time series
        dates = []
        service_types = {}
        
        for date, service_name, count in results:
            formatted_date = date.strftime('%d %b')
            if formatted_date not in dates:
                dates.append(formatted_date)
            
            if service_name not in service_types:
                service_types[service_name] = [0] * len(dates)
            
            service_types[service_name][dates.index(formatted_date)] = count
        
        response = {
            'labels': dates,
            'datasets': [
                {
                    'label': service_name,
                    'data': counts
                }
                for service_name, counts in service_types.items()
            ]
        }
    
    else:
        # Format data for bar/pie chart
        labels = [r[0] for r in results]
        data = [r[1] for r in results]
        
        response = {
            'labels': labels,
            'datasets': [
                {
                    'label': f'Attendance by {report_type.capitalize()}',
                    'data': data
                }
            ]
        }
    
    return jsonify(response)
