from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db, cache
from app.models.services import Service, ServiceType, Attendance
from app.models.people import Person
from app.models.organization import Region, Direction, Department, Team, Cell
from sqlalchemy import or_
from app.services.cache_service import cache_view, invalidate_cache
from datetime import datetime

# Create blueprint
attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/<int:service_id>', methods=['GET'])
def attendance_form(service_id):
    """Show attendance form for a specific service"""
    # Get service details
    service = Service.query.join(ServiceType).filter(Service.service_id == service_id).first_or_404()
    
    # Get filter parameters - don't set any default values
    region_id = request.args.get('region_id', type=int)
    direction_id = request.args.get('direction_id', type=int)
    department_id = request.args.get('department_id', type=int)
    team_id = request.args.get('team_id', type=int)
    cell_id = request.args.get('cell_id', type=int)
    is_active = request.args.get('is_active', default=None)
    if is_active is not None:
        is_active = is_active == 'true'
    name_search = request.args.get('name_search', '')
    
    # Get dropdown data for filters
    regions = Region.query.order_by(Region.region_name).all()
    directions = Direction.query.join(Region).order_by(Direction.direction_name).all()
    departments = Department.query.join(Direction).order_by(Department.department_name).all()
    teams = Team.query.join(Department).order_by(Team.team_name).all()
    cells = Cell.query.join(Team).order_by(Cell.cell_name).all()
    
    # Get unique country values for filter dropdown
    countries = db.session.query(Person.country).filter(Person.country != None).distinct().order_by(Person.country).all()
    countries = [country[0] for country in countries if country[0]]
    
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
    
    people = people_query.all()
    
    # Get already marked attendance
    marked_attendance = Attendance.query.filter(Attendance.service_id == service_id).all()
    marked_ids = [record.person_id for record in marked_attendance]
    
    # Organize people hierarchically
    organized_people = {}
    for person in people:
        region_name = person.cell.team.department.direction.region.region_name
        region_id = person.cell.team.department.direction.region.region_id
        
        direction_name = person.cell.team.department.direction.direction_name
        direction_id = person.cell.team.department.direction.direction_id
        
        department_name = person.cell.team.department.department_name
        department_id = person.cell.team.department.department_id
        
        team_name = person.cell.team.team_name
        team_id = person.cell.team.team_id
        
        cell_name = person.cell.cell_name
        cell_id = person.cell.cell_id
        
        # Create nested dictionary structure for organization
        if region_name not in organized_people:
            organized_people[region_name] = {
                'id': region_id,
                'directions': {}
            }
        
        if direction_name not in organized_people[region_name]['directions']:
            organized_people[region_name]['directions'][direction_name] = {
                'id': direction_id,
                'departments': {}
            }
        
        if department_name not in organized_people[region_name]['directions'][direction_name]['departments']:
            organized_people[region_name]['directions'][direction_name]['departments'][department_name] = {
                'id': department_id,
                'teams': {}
            }
        
        if team_name not in organized_people[region_name]['directions'][direction_name]['departments'][department_name]['teams']:
            organized_people[region_name]['directions'][direction_name]['departments'][department_name]['teams'][team_name] = {
                'id': team_id,
                'cells': {}
            }
        
        if cell_name not in organized_people[region_name]['directions'][direction_name]['departments'][department_name]['teams'][team_name]['cells']:
            organized_people[region_name]['directions'][direction_name]['departments'][department_name]['teams'][team_name]['cells'][cell_name] = {
                'id': cell_id,
                'people': []
            }
        
        # Add person to the structure
        organized_people[region_name]['directions'][direction_name]['departments'][department_name]['teams'][team_name]['cells'][cell_name]['people'].append({
            'id': person.person_id,
            'name': f"{person.first_name} {person.last_name}",
            'country': person.country,
            'marked': person.person_id in marked_ids,
            'status': next((record.status for record in marked_attendance if record.person_id == person.person_id), 'not-marked')
        })
    
    return render_template(
        'attendance/form.html',
        service=service,
        organized_people=organized_people,
        regions=regions,
        directions=directions,
        departments=departments,
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

@attendance_bp.route('/<int:service_id>', methods=['POST'])
def mark_attendance(service_id):
    """Process attendance submission"""
    # Validate service exists
    service = Service.query.get_or_404(service_id)
    
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Get attendance data from form
    person_status = {}
    
    # Loop through all form fields
    for key, value in request.form.items():
        # Check if it matches the person_status pattern
        if key.startswith('person_status[') and key.endswith(']'):
            # Extract person_id from the key
            person_id = key[len('person_status['):-1]
            try:
                person_id = int(person_id)
                # Convert watched-recording to watched_recording for consistency
                if value == 'watched-recording':
                    value = 'watched_recording'
                person_status[person_id] = value
            except ValueError:
                continue
    
    # Create a list to track updated attendance records
    updated_records = []
    
    try:
        # Process attendance records
        for person_id, status in person_status.items():
            # Find the person to validate
            person = Person.query.get(person_id)
            
            if not person:
                continue
                
            if status == 'not-marked':
                # Remove attendance record if it exists
                attendance_record = Attendance.query.filter_by(
                    service_id=service_id,
                    person_id=person_id
                ).first()
                if attendance_record:
                    db.session.delete(attendance_record)
                updated_records.append({
                    'person_id': person_id,
                    'status': 'not-marked'
                })
            else:
                # Create or update attendance record
                attendance_record = Attendance.query.filter_by(
                    service_id=service_id,
                    person_id=person_id
                ).first()
                
                if attendance_record:
                    # Update existing record
                    attendance_record.status = status
                    attendance_record.check_in_time = datetime.now() if status == 'present' else None
                    attendance_record.updated_at = datetime.now()
                else:
                    # Create new record
                    attendance_record = Attendance(
                        service_id=service_id,
                        person_id=person_id,
                        status=status,
                        check_in_time=datetime.now() if status == 'present' else None
                    )
                    db.session.add(attendance_record)
                
                updated_records.append({
                    'person_id': person_id,
                    'status': status
                })
        
        # Commit all changes
        db.session.commit()
        
        # Invalidate any cached attendance data
        invalidate_cache(f'attendance_{service_id}')
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Attendance recorded successfully!',
                'attendance': updated_records
            })
        else:
            flash('Attendance recorded successfully!', 'success')
            # Redirect without any filter parameters to reset the filters
            return redirect(url_for('attendance.attendance_form', service_id=service_id))
            
    except Exception as e:
        db.session.rollback()
        error_message = f'An error occurred while recording attendance: {str(e)}'
        if is_ajax:
            return jsonify({
                'success': False,
                'message': error_message
            }), 500
        else:
            flash(error_message, 'error')
            # Also reset filters on error
            return redirect(url_for('attendance.attendance_form', service_id=service_id))

@attendance_bp.route('/search', methods=['GET'])
def search_people():
    """API endpoint to search for people by name"""
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