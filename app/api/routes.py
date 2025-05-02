from flask import Blueprint, jsonify, request
from app import db, cache
from app.models.services import Service, ServiceType, Attendance
from app.models.people import Person
from app.models.organization import Region, Direction, Department, Team, Cell
from sqlalchemy import or_, func
from datetime import datetime

# Create API blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/services')
def get_services():
    """Get upcoming services"""
    services = Service.query.join(ServiceType).filter(
        Service.service_date >= datetime.now().date()
    ).order_by(Service.service_date, Service.service_time).limit(20).all()
    
    return jsonify([{
        'id': service.service_id,
        'name': service.service_type.service_name,
        'date': service.formatted_date,
        'time': service.formatted_time,
        'notes': service.notes
    } for service in services])

@api_bp.route('/people/search')
def search_people():
    """Search for people by name"""
    query = request.args.get('query', '')
    service_id = request.args.get('service_id', type=int)
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # Search for matching people
    people = Person.query.filter(
        or_(
            Person.first_name.ilike(f'%{query}%'),
            Person.last_name.ilike(f'%{query}%')
        ),
        Person.is_active == True
    ).limit(20).all()
    
    # Check if they're already marked for this service
    marked_ids = []
    if service_id:
        attendance_records = Attendance.query.filter_by(service_id=service_id).all()
        marked_ids = [record.person_id for record in attendance_records]
    
    # Format results
    results = []
    for person in people:
        hierarchy = person.hierarchy_path
        results.append({
            'id': person.person_id,
            'name': f"{person.first_name} {person.last_name}",
            'cell': hierarchy['cell']['name'],
            'team': hierarchy['team']['name'],
            'department': hierarchy['department']['name'],
            'direction': hierarchy['direction']['name'],
            'region': hierarchy['region']['name'],
            'marked': person.person_id in marked_ids
        })
    
    return jsonify(results)

@api_bp.route('/organization')
def get_organization():
    """Get organization hierarchy"""
    # Get all regions with related entities
    regions = Region.query.order_by(Region.region_name).all()
    
    # Build hierarchical structure
    hierarchy = []
    for region in regions:
        region_data = {
            'id': region.region_id,
            'name': region.region_name,
            'directions': []
        }
        
        for direction in region.directions:
            direction_data = {
                'id': direction.direction_id,
                'name': direction.direction_name,
                'departments': []
            }
            
            for department in direction.departments:
                department_data = {
                    'id': department.department_id,
                    'name': department.department_name,
                    'teams': []
                }
                
                for team in department.teams:
                    team_data = {
                        'id': team.team_id,
                        'name': team.team_name,
                        'cells': []
                    }
                    
                    for cell in team.cells:
                        cell_data = {
                            'id': cell.cell_id,
                            'name': cell.cell_name
                        }
                        team_data['cells'].append(cell_data)
                    
                    department_data['teams'].append(team_data)
                
                direction_data['departments'].append(department_data)
            
            region_data['directions'].append(direction_data)
        
        hierarchy.append(region_data)
    
    return jsonify(hierarchy)

@api_bp.route('/organization/hierarchy')
def get_organization_hierarchy():
    """
    Get organizational hierarchy with relationships between entities.
    Used for cascading dropdowns in the UI.
    """
    # Fetch all organizational entities
    regions = Region.query.all()
    directions = Direction.query.join(Region).all()
    departments = Department.query.join(Direction).all()
    teams = Team.query.join(Department).all()
    cells = Cell.query.join(Team).all()
    
    # Format the data with their relationships
    formatted_directions = []
    for direction in directions:
        formatted_directions.append({
            'direction_id': direction.direction_id,
            'direction_name': direction.direction_name,
            'region_id': direction.region_id
        })
    
    formatted_departments = []
    for department in departments:
        formatted_departments.append({
            'department_id': department.department_id,
            'department_name': department.department_name,
            'direction_id': department.direction_id
        })
    
    formatted_teams = []
    for team in teams:
        formatted_teams.append({
            'team_id': team.team_id,
            'team_name': team.team_name,
            'department_id': team.department_id
        })
    
    formatted_cells = []
    for cell in cells:
        formatted_cells.append({
            'cell_id': cell.cell_id,
            'cell_name': cell.cell_name,
            'team_id': cell.team_id
        })
    
    # Return the complete hierarchy
    return jsonify({
        'regions': [{'region_id': r.region_id, 'region_name': r.region_name} for r in regions],
        'directions': formatted_directions,
        'departments': formatted_departments,
        'teams': formatted_teams,
        'cells': formatted_cells
    })

@api_bp.route('/attendance/<int:service_id>')
def get_attendance(service_id):
    """Get attendance for a specific service"""
    # Verify service exists
    service = Service.query.get_or_404(service_id)
    
    # Get attendance records
    records = Attendance.query.filter_by(service_id=service_id).all()
    
    return jsonify({
        'service': {
            'id': service.service_id,
            'name': service.service_type.service_name,
            'date': service.formatted_date,
            'time': service.formatted_time
        },
        'attendance_count': len(records),
        'records': [{
            'person_id': record.person_id,
            'name': f"{record.person.first_name} {record.person.last_name}",
            'check_in_time': record.check_in_time.strftime('%H:%M:%S')
        } for record in records]
    })

@api_bp.route('/stats/overview')
def get_overview_stats():
    """Get overview statistics"""
    # Get total counts
    people_count = Person.query.filter_by(is_active=True).count()
    services_count = Service.query.filter(Service.service_date >= datetime.now().date()).count()
    
    # Get recent attendance
    recent_service = Service.query.filter(
        Service.service_date <= datetime.now().date()
    ).order_by(Service.service_date.desc(), Service.service_time.desc()).first()
    
    recent_attendance_count = 0
    if recent_service:
        recent_attendance_count = Attendance.query.filter_by(service_id=recent_service.service_id).count()
    
    # Get department breakdown
    department_stats = db.session.query(
        Department.department_name,
        func.count(Person.person_id).label('count')
    ).join(
        Team, Department.department_id == Team.department_id
    ).join(
        Cell, Team.team_id == Cell.team_id
    ).join(
        Person, Cell.cell_id == Person.cell_id
    ).group_by(
        Department.department_name
    ).order_by(
        func.count(Person.person_id).desc()
    ).limit(5).all()
    
    return jsonify({
        'total_active_people': people_count,
        'upcoming_services': services_count,
        'recent_attendance': {
            'service': recent_service.service_type.service_name if recent_service else None,
            'date': recent_service.formatted_date if recent_service else None,
            'count': recent_attendance_count
        },
        'department_breakdown': [
            {'name': dept, 'count': count}
            for dept, count in department_stats
        ]
    })
