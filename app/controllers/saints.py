from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app import db, cache
from app.models.people import Person
from app.models.organization import Region, Direction, Department, Team, Cell
from sqlalchemy import or_, func
from app.services.cache_service import cache_view, invalidate_cache
from datetime import datetime
import math

# Create blueprint
saints_bp = Blueprint('saints', __name__, url_prefix='/saints')

@saints_bp.route('/')
@cache_view(timeout=30)
def saints_list():
    """View all saints with filtering options"""
    # Get filter parameters
    region_id = request.args.get('region_id', type=int)
    direction_id = request.args.get('direction_id', type=int)
    department_id = request.args.get('department_id', type=int)
    team_id = request.args.get('team_id', type=int)
    cell_id = request.args.get('cell_id', type=int)
    is_active = request.args.get('is_active', 'true') == 'true'
    name_search = request.args.get('name_search', '')
    ajax_request = request.args.get('ajax', 'false') == 'true'
    
    # Get dropdown data for filters with optimized queries
    regions = Region.query.order_by(Region.region_name).all()
    
    # Get unique country values for filter dropdown
    countries = db.session.query(Person.country).filter(Person.country != None).distinct().order_by(Person.country).all()
    countries = [country[0] for country in countries if country[0]]
    
    # Get directions with their parent region info
    directions_query = db.session.query(
        Direction.direction_id,
        Direction.direction_name,
        Direction.region_id,
        Region.region_name.label('region_name')
    ).join(
        Region, Direction.region_id == Region.region_id
    )
    
    # Filter directions by region if selected
    if region_id:
        directions_query = directions_query.filter(Direction.region_id == region_id)
    
    directions = directions_query.order_by(Region.region_name, Direction.direction_name).all()
    
    # Get departments with their parent direction info to handle duplicates
    departments_query = db.session.query(
        Department.department_id,
        Department.department_name,
        Department.direction_id,
        Direction.direction_name.label('direction_name'),
        Region.region_name.label('region_name')
    ).join(
        Direction, Department.direction_id == Direction.direction_id
    ).join(
        Region, Direction.region_id == Region.region_id
    )
    
    # Filter departments by region and direction if selected
    if region_id:
        departments_query = departments_query.filter(Region.region_id == region_id)
    if direction_id:
        departments_query = departments_query.filter(Department.direction_id == direction_id)
    
    departments = departments_query.order_by(Department.department_name, Direction.direction_name).all()
    
    # Group departments by name to identify duplicates
    departments_by_name = {}
    for dept in departments:
        if dept.department_name not in departments_by_name:
            departments_by_name[dept.department_name] = []
        departments_by_name[dept.department_name].append(dept)
    
    # Format department names to include parent context for duplicates
    formatted_departments = []
    for dept_name, dept_list in departments_by_name.items():
        if len(dept_list) > 1:
            # Multiple departments with the same name
            for dept in dept_list:
                formatted_departments.append({
                    'department_id': dept.department_id,
                    'department_name': f"{dept.department_name} ({dept.direction_name})",
                    'direction_id': dept.direction_id
                })
        else:
            # Just one department with this name
            dept = dept_list[0]
            formatted_departments.append({
                'department_id': dept.department_id,
                'department_name': dept.department_name,
                'direction_id': dept.direction_id
            })
    
    # Sort formatted departments by name
    formatted_departments.sort(key=lambda x: x['department_name'])
    
    # Get teams with parent department info
    teams_query = db.session.query(
        Team.team_id,
        Team.team_name,
        Team.department_id,
        Department.department_name.label('department_name'),
        Department.direction_id.label('direction_id')
    ).join(
        Department, Team.department_id == Department.department_id
    ).join(
        Direction, Department.direction_id == Direction.direction_id
    ).join(
        Region, Direction.region_id == Region.region_id
    )
    
    # Filter teams by region, direction, and department if selected
    if region_id:
        teams_query = teams_query.filter(Region.region_id == region_id)
    if direction_id:
        teams_query = teams_query.filter(Direction.direction_id == direction_id)
    if department_id:
        teams_query = teams_query.filter(Department.department_id == department_id)
    
    teams = teams_query.order_by(Team.team_name).all()
    
    # Get cells with parent team info
    cells_query = db.session.query(
        Cell.cell_id,
        Cell.cell_name,
        Cell.team_id,
        Team.team_name.label('team_name'),
        Team.department_id.label('department_id')
    ).join(
        Team, Cell.team_id == Team.team_id
    ).join(
        Department, Team.department_id == Department.department_id
    ).join(
        Direction, Department.direction_id == Direction.direction_id
    ).join(
        Region, Direction.region_id == Region.region_id
    )
    
    # Filter cells by region, direction, department, and team if selected
    if region_id:
        cells_query = cells_query.filter(Region.region_id == region_id)
    if direction_id:
        cells_query = cells_query.filter(Direction.direction_id == direction_id)
    if department_id:
        cells_query = cells_query.filter(Department.department_id == department_id)
    if team_id:
        cells_query = cells_query.filter(Team.team_id == team_id)
    
    cells = cells_query.order_by(Cell.cell_name).all()
    
    # Build people query with filters
    people_query = Person.query.join(Cell).join(Team).join(Department).join(Direction).join(Region)
    
    # Apply filters
    if is_active is not None:
        people_query = people_query.filter(Person.is_active == is_active)
    
    if region_id:
        people_query = people_query.filter(Region.region_id == region_id)
    
    if direction_id:
        people_query = people_query.filter(Direction.direction_id == direction_id)
    
    if department_id:
        people_query = people_query.filter(Department.department_id == department_id)
    
    if team_id:
        people_query = people_query.filter(Team.team_id == team_id)
    
    if cell_id:
        people_query = people_query.filter(Cell.cell_id == cell_id)
        
    # Filter by country if provided
    country = request.args.get('country', '')
    if country:
        people_query = people_query.filter(Person.country == country)
    
    if name_search:
        people_query = people_query.filter(
            or_(
                Person.first_name.ilike(f'%{name_search}%'),
                Person.last_name.ilike(f'%{name_search}%')
            )
        )
    
    # Order results
    people_query = people_query.order_by(
        Region.region_name, 
        Direction.direction_name, 
        Department.department_name, 
        Team.team_name, 
        Cell.cell_name,
        Person.last_name,
        Person.first_name
    )
    
    # Paginate results
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    pagination = people_query.paginate(page=page, per_page=per_page, error_out=False)
    people = pagination.items
    
    # Handle AJAX requests
    if ajax_request:
        # Prepare JSON response
        people_data = []
        for person in people:
            people_data.append({
                'person_id': person.person_id,
                'first_name': person.first_name,
                'last_name': '' if isinstance(person.last_name, float) and math.isnan(person.last_name) else person.last_name,
                'mobile_number': person.phone or 'Not available',
                'is_active': person.is_active,
                'country': person.country or 'Not specified',
                'cell': person.cell.cell_name,
                'team': person.cell.team.team_name,
                'department': person.cell.team.department.department_name,
                'direction': person.cell.team.department.direction.direction_name,
                'region': person.cell.team.department.direction.region.region_name
            })
        
        # Create pagination info
        pagination_data = {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num if pagination.has_prev else None,
            'next_num': pagination.next_num if pagination.has_next else None
        }
        
        # Generate HTML for table rows for easier rendering
        html_content = ""
        if people:
            for person in people:
                html_content += f"""
                <tr>
                    <td>{person.first_name} {person.last_name}</td>
                    <td>{person.phone or 'Not available'}</td>
                    <td>{person.country or 'Not specified'}</td>
                    <td>{person.cell.cell_name}</td>
                    <td>{person.cell.team.team_name}</td>
                    <td>{person.cell.team.department.department_name}</td>
                    <td>{person.cell.team.department.direction.direction_name}</td>
                    <td>{person.cell.team.department.direction.region.region_name}</td>
                    <td>
                        <span class="badge {'badge-success' if person.is_active else 'badge-danger'}">
                            {'Active' if person.is_active else 'Inactive'}
                        </span>
                    </td>
                </tr>
                """
        else:
            html_content = '<tr><td colspan="9" class="text-center">No saints found matching the current filters.</td></tr>'
        
        # Generate pagination HTML
        pagination_html = ""
        if pagination.pages > 1:
            pagination_html = f"""
            <div class="pagination-info">
                Showing {pagination.page} of {pagination.pages} pages
            </div>
            <div class="pagination-controls">
                {'<a href="' + url_for('saints.saints_list', page=pagination.prev_num, **{k: v for k, v in request.args.items() if k != 'page'}) + '" class="btn btn-outline btn-sm pagination-prev">Previous</a>' if pagination.has_prev else '<button class="btn btn-outline btn-sm" disabled>Previous</button>'}
                {'<a href="' + url_for('saints.saints_list', page=pagination.next_num, **{k: v for k, v in request.args.items() if k != 'page'}) + '" class="btn btn-outline btn-sm pagination-next">Next</a>' if pagination.has_next else '<button class="btn btn-outline btn-sm" disabled>Next</button>'}
            </div>
            """
        
        return jsonify({
            'people': people_data,
            'pagination': pagination_data,
            'html': html_content,
            'pagination_html': pagination_html
        })
    
    # Render template for regular requests
    return render_template(
        'saints/index.html',
        people=people,
        pagination=pagination,
        regions=regions,
        directions=directions,
        departments=formatted_departments,
        teams=teams,
        cells=cells,
        countries=countries,
        filters={
            'region_id': region_id,
            'direction_id': direction_id,
            'department_id': department_id,
            'team_id': team_id,
            'cell_id': cell_id,
            'is_active': is_active,
            'name_search': name_search,
            'country': request.args.get('country', '')
        },
        now=datetime.now()
    )
