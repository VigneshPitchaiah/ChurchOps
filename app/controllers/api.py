from flask import Blueprint, jsonify

from app.models.organization import Region, Direction, Department, Team, Cell

# Create the API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/organization/hierarchy', methods=['GET'])
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
