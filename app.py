from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
from dotenv import load_dotenv
from db import execute_query, get_db_connection
from datetime import datetime
import json

# For file handling
import csv
import io
import pandas as pd
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Cache control for better performance in low network areas
@app.after_request
def add_header(response):
    """Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes."""
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=600'
    return response

# Routes
@app.route('/')
def index():
    """Home page with login option"""
    return render_template('index.html', now=datetime.now())

@app.route('/services')
def services():
    """Show upcoming services"""
    # Get today's and upcoming services
    query = """
    SELECT s.service_id, st.service_name, s.service_date, s.service_time, s.notes 
    FROM church.services s 
    JOIN church.service_types st ON s.service_type_id = st.service_type_id 
    WHERE s.service_date >= CURRENT_DATE 
    ORDER BY s.service_date, s.service_time
    LIMIT 20
    """
    services_list = execute_query(query)
    return render_template('services.html', services=services_list, now=datetime.now())

@app.route('/attendance/<int:service_id>', methods=['GET', 'POST'])
def attendance(service_id):
    """Mark attendance for a specific service"""
    if request.method == 'POST':
        # Process attendance form submission
        person_ids = request.form.getlist('person_ids')
        notes = request.form.get('notes', '')
        
        for person_id in person_ids:
            # Check if attendance already exists
            check_query = """
            SELECT attendance_id FROM church.attendance 
            WHERE service_id = %s AND person_id = %s
            """
            existing = execute_query(check_query, (service_id, person_id))
            
            if not existing:
                # Create new attendance record
                insert_query = """
                INSERT INTO church.attendance (service_id, person_id, check_in_time, notes)
                VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                """
                execute_query(insert_query, (service_id, person_id, notes), fetch=False)
        
        flash('Attendance recorded successfully!', 'success')
        return redirect(url_for('attendance', service_id=service_id))
    
    # Get service details
    service_query = """
    SELECT s.service_id, st.service_name, s.service_date, s.service_time
    FROM church.services s
    JOIN church.service_types st ON s.service_type_id = st.service_type_id
    WHERE s.service_id = %s
    """
    service = execute_query(service_query, (service_id,))[0]
    
    # Get filter parameters
    region_id = request.args.get('region_id')
    direction_id = request.args.get('direction_id')
    department_id = request.args.get('department_id')
    team_id = request.args.get('team_id')
    cell_id = request.args.get('cell_id')
    is_active = request.args.get('is_active', 'true')
    name_search = request.args.get('name_search', '')
    
    # Get all regions, directions, departments, teams, and cells for filter dropdowns
    regions_query = """
    SELECT DISTINCT region_id, region_name FROM church.regions ORDER BY region_name
    """
    regions = execute_query(regions_query)
    
    directions_query = """
    SELECT DISTINCT d.direction_id, d.direction_name, d.region_id, r.region_name
    FROM church.directions d
    JOIN church.regions r ON d.region_id = r.region_id
    ORDER BY d.direction_name
    """
    directions = execute_query(directions_query)
    
    departments_query = """
    SELECT DISTINCT d.department_id, d.department_name, d.direction_id, dir.direction_name
    FROM church.departments d
    JOIN church.directions dir ON d.direction_id = dir.direction_id
    ORDER BY d.department_name
    """
    departments = execute_query(departments_query)
    
    teams_query = """
    SELECT DISTINCT t.team_id, t.team_name, t.department_id, d.department_name
    FROM church.teams t
    JOIN church.departments d ON t.department_id = d.department_id
    ORDER BY t.team_name
    """
    teams = execute_query(teams_query)
    
    cells_query = """
    SELECT DISTINCT c.cell_id, c.cell_name, c.team_id, t.team_name
    FROM church.cells c
    JOIN church.teams t ON c.team_id = t.team_id
    ORDER BY c.cell_name
    """
    cells = execute_query(cells_query)
    
    # Build query with filters
    people_query = """
    SELECT p.person_id, p.first_name, p.last_name, c.cell_name, 
           t.team_name, d.department_name, c.cell_id, t.team_id, d.department_id,
           dir.direction_name, dir.direction_id, r.region_name, r.region_id
    FROM church.people p
    JOIN church.cells c ON p.cell_id = c.cell_id
    JOIN church.teams t ON c.team_id = t.team_id
    JOIN church.departments d ON t.department_id = d.department_id
    JOIN church.directions dir ON d.direction_id = dir.direction_id
    JOIN church.regions r ON dir.region_id = r.region_id
    WHERE p.is_active = %s
    """
    query_params = [is_active == 'true']
    
    if region_id:
        people_query += " AND r.region_id = %s"
        query_params.append(region_id)
    
    if direction_id:
        people_query += " AND dir.direction_id = %s"
        query_params.append(direction_id)
    
    if department_id:
        people_query += " AND d.department_id = %s"
        query_params.append(department_id)
    
    if team_id:
        people_query += " AND t.team_id = %s"
        query_params.append(team_id)
    
    if cell_id:
        people_query += " AND c.cell_id = %s"
        query_params.append(cell_id)
    
    if name_search:
        people_query += " AND (p.first_name ILIKE %s OR p.last_name ILIKE %s)"
        query_params.extend([f'%{name_search}%', f'%{name_search}%'])
    
    people_query += " ORDER BY r.region_name, dir.direction_name, d.department_name, t.team_name, c.cell_name, p.last_name, p.first_name"
    
    people = execute_query(people_query, tuple(query_params))
    
    # Get already marked attendance
    marked_query = """
    SELECT person_id FROM church.attendance WHERE service_id = %s
    """
    marked = execute_query(marked_query, (service_id,))
    marked_ids = [m[0] for m in marked]
    
    # Organize people by department > team > cell for easier marking
    organized_people = {}
    for person in people:
        dept_id = person[8]  # department_id
        dept_name = person[5]  # department_name
        team_id = person[7]  # team_id
        team_name = person[4]  # team_name
        cell_id = person[6]  # cell_id
        cell_name = person[3]  # cell_name
        direction_id = person[10]  # direction_id
        direction_name = person[9]  # direction_name
        region_id = person[12]  # region_id
        region_name = person[11]  # region_name
        
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
            
        if dept_name not in organized_people[region_name]['directions'][direction_name]['departments']:
            organized_people[region_name]['directions'][direction_name]['departments'][dept_name] = {
                'id': dept_id,
                'teams': {}
            }
            
        if team_name not in organized_people[region_name]['directions'][direction_name]['departments'][dept_name]['teams']:
            organized_people[region_name]['directions'][direction_name]['departments'][dept_name]['teams'][team_name] = {
                'id': team_id,
                'cells': {}
            }
            
        if cell_name not in organized_people[region_name]['directions'][direction_name]['departments'][dept_name]['teams'][team_name]['cells']:
            organized_people[region_name]['directions'][direction_name]['departments'][dept_name]['teams'][team_name]['cells'][cell_name] = {
                'id': cell_id,
                'people': []
            }
            
        organized_people[region_name]['directions'][direction_name]['departments'][dept_name]['teams'][team_name]['cells'][cell_name]['people'].append({
            'id': person[0],
            'name': f"{person[1]} {person[2]}",
            'marked': person[0] in marked_ids
        })
    
    return render_template(
        'attendance.html', 
        service=service,
        organized_people=organized_people,
        regions=regions,
        directions=directions,
        departments=departments,
        teams=teams,
        cells=cells,
        filters={
            'region_id': region_id,
            'direction_id': direction_id,
            'department_id': department_id,
            'team_id': team_id,
            'cell_id': cell_id,
            'is_active': is_active,
            'name_search': name_search
        },
        now=datetime.now()
    )

@app.route('/search_people', methods=['GET'])
def search_people():
    """Search people by name for quick attendance marking"""
    query_term = request.args.get('query', '')
    service_id = request.args.get('service_id')
    
    if not query_term or len(query_term) < 3:
        return jsonify([])
    
    search_query = """
    SELECT p.person_id, p.first_name, p.last_name, c.cell_name
    FROM church.people p
    JOIN church.cells c ON p.cell_id = c.cell_id
    WHERE p.is_active = true 
    AND (p.first_name ILIKE %s OR p.last_name ILIKE %s)
    ORDER BY p.last_name, p.first_name
    LIMIT 20
    """
    
    people = execute_query(search_query, (f'%{query_term}%', f'%{query_term}%'))
    
    # Check which people are already marked for this service
    marked_ids = []
    if service_id:
        marked_query = """
        SELECT person_id FROM church.attendance WHERE service_id = %s
        """
        marked = execute_query(marked_query, (service_id,))
        marked_ids = [m[0] for m in marked]
    
    results = [{
        'id': p[0],
        'name': f"{p[1]} {p[2]}",
        'cell': p[3],
        'marked': p[0] in marked_ids
    } for p in people]
    
    return jsonify(results)

@app.route('/saints', methods=['GET'])
def saints():
    """View all saints (church members) with filtering options"""
    # Get filter parameters
    region_id = request.args.get('region_id')
    direction_id = request.args.get('direction_id')
    department_id = request.args.get('department_id')
    team_id = request.args.get('team_id')
    cell_id = request.args.get('cell_id')
    is_active = request.args.get('is_active', 'true')
    name_search = request.args.get('name_search', '')
    service_id = request.args.get('service_id')
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 100  # Number of saints per page
    
    # Get all regions, directions, departments, teams, and cells for filter dropdowns
    # Use DISTINCT to remove redundancy
    regions_query = """
    SELECT DISTINCT region_id, region_name FROM church.regions ORDER BY region_name
    """
    regions = execute_query(regions_query)
    
    # Direction query - filtered by region if specified
    if region_id:
        directions_query = """
        SELECT DISTINCT d.direction_id, d.direction_name, d.region_id, r.region_name
        FROM church.directions d
        JOIN church.regions r ON d.region_id = r.region_id
        WHERE d.region_id = %s
        ORDER BY d.direction_name
        """
        directions = execute_query(directions_query, (region_id,))
    else:
        directions_query = """
        SELECT DISTINCT d.direction_id, d.direction_name, d.region_id, r.region_name
        FROM church.directions d
        JOIN church.regions r ON d.region_id = r.region_id
        ORDER BY d.direction_name
        """
        directions = execute_query(directions_query)
    
    # Department query - filtered by direction if specified
    if direction_id:
        departments_query = """
        SELECT DISTINCT d.department_id, d.department_name, d.direction_id, dir.direction_name
        FROM church.departments d
        JOIN church.directions dir ON d.direction_id = dir.direction_id
        WHERE d.direction_id = %s
        ORDER BY d.department_name
        """
        departments = execute_query(departments_query, (direction_id,))
    else:
        departments_query = """
        SELECT DISTINCT d.department_id, d.department_name, d.direction_id, dir.direction_name
        FROM church.departments d
        JOIN church.directions dir ON d.direction_id = dir.direction_id
        ORDER BY d.department_name
        """
        departments = execute_query(departments_query)
    
    # Team query - filtered by department if specified
    if department_id:
        teams_query = """
        SELECT DISTINCT t.team_id, t.team_name, t.department_id, d.department_name
        FROM church.teams t
        JOIN church.departments d ON t.department_id = d.department_id
        WHERE t.department_id = %s
        ORDER BY t.team_name
        """
        teams = execute_query(teams_query, (department_id,))
    else:
        teams_query = """
        SELECT DISTINCT t.team_id, t.team_name, t.department_id, d.department_name
        FROM church.teams t
        JOIN church.departments d ON t.department_id = d.department_id
        ORDER BY t.team_name
        """
        teams = execute_query(teams_query)
    
    # Cell query - filtered by team if specified
    if team_id:
        cells_query = """
        SELECT DISTINCT c.cell_id, c.cell_name, c.team_id, t.team_name
        FROM church.cells c
        JOIN church.teams t ON c.team_id = t.team_id
        WHERE c.team_id = %s
        ORDER BY c.cell_name
        """
        cells = execute_query(cells_query, (team_id,))
    else:
        cells_query = """
        SELECT DISTINCT c.cell_id, c.cell_name, c.team_id, t.team_name
        FROM church.cells c
        JOIN church.teams t ON c.team_id = t.team_id
        ORDER BY c.cell_name
        """
        cells = execute_query(cells_query)
    
    # Get upcoming services for attendance marking dropdown
    services_query = """
    SELECT s.service_id, st.service_name, s.service_date, s.service_time
    FROM church.services s
    JOIN church.service_types st ON s.service_type_id = st.service_type_id
    WHERE s.service_date >= CURRENT_DATE - INTERVAL '7 days'
    ORDER BY s.service_date DESC, s.service_time DESC
    LIMIT 10
    """
    services = execute_query(services_query)
    
    # First, get count of total records for pagination
    count_query = """
    SELECT COUNT(*)
    FROM church.people p
    JOIN church.cells c ON p.cell_id = c.cell_id
    JOIN church.teams t ON c.team_id = t.team_id
    JOIN church.departments d ON t.department_id = d.department_id
    JOIN church.directions dir ON d.direction_id = dir.direction_id
    JOIN church.regions r ON dir.region_id = r.region_id
    WHERE p.is_active = %s
    """
    count_params = [is_active == 'true']
    
    if region_id:
        count_query += " AND r.region_id = %s"
        count_params.append(region_id)
    
    if direction_id:
        count_query += " AND dir.direction_id = %s"
        count_params.append(direction_id)
    
    if department_id:
        count_query += " AND d.department_id = %s"
        count_params.append(department_id)
    
    if team_id:
        count_query += " AND t.team_id = %s"
        count_params.append(team_id)
    
    if cell_id:
        count_query += " AND c.cell_id = %s"
        count_params.append(cell_id)
    
    if name_search:
        count_query += " AND (p.first_name ILIKE %s OR p.last_name ILIKE %s)"
        count_params.extend([f'%{name_search}%', f'%{name_search}%'])
    
    total_count = execute_query(count_query, tuple(count_params))[0][0]
    total_pages = (total_count + per_page - 1) // per_page
    
    # Ensure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Build query with filters and pagination
    people_query = """
    SELECT p.person_id, p.first_name, p.last_name, p.email, p.phone,
           c.cell_name, c.cell_id, 
           t.team_name, t.team_id, 
           d.department_name, d.department_id,
           dir.direction_name, dir.direction_id,
           r.region_name, r.region_id,
           p.is_active
    FROM church.people p
    JOIN church.cells c ON p.cell_id = c.cell_id
    JOIN church.teams t ON c.team_id = t.team_id
    JOIN church.departments d ON t.department_id = d.department_id
    JOIN church.directions dir ON d.direction_id = dir.direction_id
    JOIN church.regions r ON dir.region_id = r.region_id
    WHERE p.is_active = %s
    """
    query_params = [is_active == 'true']
    
    if region_id:
        people_query += " AND r.region_id = %s"
        query_params.append(region_id)
    
    if direction_id:
        people_query += " AND dir.direction_id = %s"
        query_params.append(direction_id)
    
    if department_id:
        people_query += " AND d.department_id = %s"
        query_params.append(department_id)
    
    if team_id:
        people_query += " AND t.team_id = %s"
        query_params.append(team_id)
    
    if cell_id:
        people_query += " AND c.cell_id = %s"
        query_params.append(cell_id)
    
    if name_search:
        people_query += " AND (p.first_name ILIKE %s OR p.last_name ILIKE %s)"
        query_params.extend([f'%{name_search}%', f'%{name_search}%'])
    
    people_query += " ORDER BY r.region_name, dir.direction_name, d.department_name, t.team_name, c.cell_name, p.last_name, p.first_name"
    
    # Add pagination
    offset = (page - 1) * per_page
    people_query += f" LIMIT {per_page} OFFSET {offset}"
    
    people = execute_query(people_query, tuple(query_params))
    
    # Check which people have attendance entries for the selected service
    attendance_status = {}
    if service_id:
        attendance_query = """
        SELECT person_id, 
               CASE WHEN present = true THEN 'present' ELSE 'absent' END as status
        FROM (
            SELECT p.person_id, 
                   CASE WHEN a.attendance_id IS NOT NULL THEN true ELSE false END as present
            FROM church.people p
            LEFT JOIN church.attendance a ON p.person_id = a.person_id AND a.service_id = %s
            WHERE p.is_active = %s
        ) AS attendance_data
        """
        attendance_params = [service_id, is_active == 'true']
        
        if region_id or direction_id or department_id or team_id or cell_id or name_search:
            # Only include filtered people in this query
            person_ids = [p[0] for p in people]
            if person_ids:
                attendance_query = """
                SELECT person_id, 
                       CASE WHEN present = true THEN 'present' ELSE 'absent' END as status
                FROM (
                    SELECT p.person_id, 
                           CASE WHEN a.attendance_id IS NOT NULL THEN true ELSE false END as present
                    FROM church.people p
                    LEFT JOIN church.attendance a ON p.person_id = a.person_id AND a.service_id = %s
                    WHERE p.person_id = ANY(%s)
                ) AS attendance_data
                """
                attendance_params = [service_id, person_ids]
        
        attendance_results = execute_query(attendance_query, tuple(attendance_params))
        for att in attendance_results:
            attendance_status[att[0]] = att[1]
    
    # Format people data for the template
    formatted_people = []
    for person in people:
        person_id = person[0]
        status = attendance_status.get(person_id, 'unmarked')
        
        formatted_people.append({
            'id': person_id,
            'first_name': person[1],
            'last_name': person[2],
            'email': person[3],
            'phone': person[4],
            'cell_name': person[5],
            'cell_id': person[6],
            'team_name': person[7],
            'team_id': person[8],
            'department_name': person[9],
            'department_id': person[10],
            'direction_name': person[11],
            'direction_id': person[12],
            'region_name': person[13],
            'region_id': person[14],
            'is_active': person[15],
            'status': status,
            'present': status == 'present',
            'absent': status == 'absent'
        })
    
    return render_template(
        'saints.html',
        people=formatted_people,
        regions=regions,
        directions=directions,
        departments=departments,
        teams=teams,
        cells=cells,
        services=services,
        filters={
            'region_id': region_id,
            'direction_id': direction_id,
            'department_id': department_id,
            'team_id': team_id,
            'cell_id': cell_id,
            'is_active': is_active,
            'name_search': name_search,
            'service_id': service_id
        },
        pagination={
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_count': total_count
        },
        now=datetime.now()
    )

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance for selected saints and a specific service"""
    service_id = request.form.get('service_id')
    present_ids = request.form.getlist('present_ids')
    absent_ids = request.form.getlist('absent_ids')
    notes = request.form.get('notes', '')
    return_url = request.form.get('return_url', '/saints')
    
    if not service_id or (not present_ids and not absent_ids):
        flash('Please select a service and at least one person', 'danger')
        return redirect(return_url)
    
    # Process present saints
    for person_id in present_ids:
        # Check if attendance already exists
        check_query = """
        SELECT attendance_id FROM church.attendance 
        WHERE service_id = %s AND person_id = %s
        """
        existing = execute_query(check_query, (service_id, person_id))
        
        if not existing:
            # Create new attendance record
            insert_query = """
            INSERT INTO church.attendance (service_id, person_id, check_in_time, notes)
            VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
            """
            execute_query(insert_query, (service_id, person_id, notes), fetch=False)
    
    # Add absence records or delete existing attendance entries
    for person_id in absent_ids:
        # Check if attendance record exists and remove it
        delete_query = """
        DELETE FROM church.attendance
        WHERE service_id = %s AND person_id = %s
        """
        execute_query(delete_query, (service_id, person_id), fetch=False)
    
    flash('Attendance recorded successfully!', 'success')
    return redirect(return_url)

@app.route('/reports')
def reports():
    """Simple attendance reports"""
    # Get recent services
    services_query = """
    SELECT s.service_id, st.service_name, s.service_date, 
           COUNT(a.attendance_id) as attendance_count
    FROM church.services s
    JOIN church.service_types st ON s.service_type_id = st.service_type_id
    LEFT JOIN church.attendance a ON s.service_id = a.service_id
    WHERE s.service_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY s.service_id, st.service_name, s.service_date
    ORDER BY s.service_date DESC
    LIMIT 10
    """
    services = execute_query(services_query)
    
    return render_template('reports.html', services=services, now=datetime.now())

@app.route('/assignments')
def assignments():
    """Manage people assignments to regions, directions, departments, teams, and cells"""
    # Get all regions, directions, departments, teams, and cells for dropdown menus
    regions_query = """SELECT DISTINCT region_id, region_name FROM church.regions ORDER BY region_name"""
    regions = execute_query(regions_query)
    
    directions_query = """
    SELECT DISTINCT d.direction_id, d.direction_name, d.region_id, r.region_name
    FROM church.directions d JOIN church.regions r ON d.region_id = r.region_id
    ORDER BY d.direction_name
    """
    directions = execute_query(directions_query)
    
    departments_query = """
    SELECT DISTINCT d.department_id, d.department_name, d.direction_id, dir.direction_name
    FROM church.departments d JOIN church.directions dir ON d.direction_id = dir.direction_id
    ORDER BY d.department_name
    """
    departments = execute_query(departments_query)
    
    teams_query = """
    SELECT DISTINCT t.team_id, t.team_name, t.department_id, d.department_name
    FROM church.teams t JOIN church.departments d ON t.department_id = d.department_id
    ORDER BY t.team_name
    """
    teams = execute_query(teams_query)
    
    cells_query = """
    SELECT DISTINCT c.cell_id, c.cell_name, c.team_id, t.team_name
    FROM church.cells c JOIN church.teams t ON c.team_id = t.team_id
    ORDER BY c.cell_name
    """
    cells = execute_query(cells_query)
    
    return render_template('assignments.html', regions=regions, directions=directions,
                          departments=departments, teams=teams, cells=cells, now=datetime.now())

@app.route('/search_bulk_people')
def search_bulk_people():
    """Search for people based on their assignments for bulk operations"""
    region_id = request.args.get('region_id')
    direction_id = request.args.get('direction_id')
    department_id = request.args.get('department_id')
    team_id = request.args.get('team_id')
    cell_id = request.args.get('cell_id')
    
    # Build query with filters
    query = """
    SELECT p.person_id, p.first_name, p.last_name, p.email, p.phone, 
           c.cell_name, c.cell_id, t.team_name, t.team_id, 
           d.department_name, d.department_id, dir.direction_name, dir.direction_id,
           r.region_name, r.region_id, p.is_active
    FROM church.people p
    LEFT JOIN church.cells c ON p.cell_id = c.cell_id
    LEFT JOIN church.teams t ON c.team_id = t.team_id
    LEFT JOIN church.departments d ON t.department_id = d.department_id
    LEFT JOIN church.directions dir ON d.direction_id = dir.direction_id
    LEFT JOIN church.regions r ON dir.region_id = r.region_id
    WHERE 1=1
    """
    
    params = []
    if region_id:
        query += " AND r.region_id = %s"
        params.append(region_id)
    if direction_id:
        query += " AND dir.direction_id = %s"
        params.append(direction_id)
    if department_id:
        query += " AND d.department_id = %s"
        params.append(department_id)
    if team_id:
        query += " AND t.team_id = %s"
        params.append(team_id)
    if cell_id:
        query += " AND c.cell_id = %s"
        params.append(cell_id)
    
    query += " ORDER BY p.last_name, p.first_name"
    people = execute_query(query, params)
    
    # Format people for JSON response
    formatted_people = []
    for person in people:
        formatted_people.append({
            'id': person[0],
            'name': f"{person[1]} {person[2]}",
            'email': person[3],
            'phone': person[4],
            'cell': person[5],
            'cell_id': person[6],
            'team': person[7],
            'team_id': person[8],
            'department': person[9],
            'department_id': person[10],
            'direction': person[11],
            'direction_id': person[12],
            'region': person[13],
            'region_id': person[14],
            'is_active': person[15]
        })
    
    return jsonify({'people': formatted_people})

@app.route('/save_assignment', methods=['POST'])
def save_assignment():
    """Save individual person assignment"""
    try:
        person_id = request.form.get('person_id')
        cell_id = request.form.get('cell_id', '')
        is_active = request.form.get('is_active') == 'true'
        
        if not person_id:
            return jsonify({'success': False, 'message': 'Person ID is required'})
        
        # Update person's assignment
        query = """
        UPDATE church.people
        SET cell_id = %s, is_active = %s
        WHERE person_id = %s
        """
        execute_query(query, (cell_id or None, is_active, person_id), fetch=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/save_bulk_assignment', methods=['POST'])
def save_bulk_assignment():
    """Save bulk assignments for multiple people"""
    try:
        import json
        person_ids = json.loads(request.form.get('person_ids', '[]'))
        cell_id = request.form.get('cell_id', '')
        
        if not person_ids:
            return jsonify({'success': False, 'message': 'No people selected'})
        if not cell_id:
            return jsonify({'success': False, 'message': 'Cell assignment is required'})
        
        # Update people assignments
        for person_id in person_ids:
            query = "UPDATE church.people SET cell_id = %s WHERE person_id = %s"
            execute_query(query, (cell_id, person_id), fetch=False)
        
        return jsonify({'success': True, 'count': len(person_ids)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download_template')
def download_template():
    """Download a CSV template for assignment imports"""
    # Create a template file with the expected columns
    headers = [
        'person_id', 'first_name', 'last_name', 'email', 'phone',
        'cell_name', 'team_name', 'department_name', 'direction_name', 'region_name',
        'is_active'
    ]
    
    # Create example data
    example_data = [
        {
            'person_id': '123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'cell_name': 'Prayer Cell',
            'team_name': 'Intercessory Team',
            'department_name': 'Prayer Department',
            'direction_name': 'Spiritual Direction',
            'region_name': 'Central Region',
            'is_active': 'true'
        },
        {
            'person_id': '',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'phone': '0987654321',
            'cell_name': 'Worship Cell',
            'team_name': 'Praise Team',
            'department_name': 'Worship Department',
            'direction_name': 'Arts Direction',
            'region_name': 'North Region',
            'is_active': 'true'
        }
    ]
    
    # Create in-memory CSV file
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(example_data)
    
    # Create response with CSV file
    from flask import Response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=assignment_template.csv'}
    )
    
    return response

@app.route('/import_assignments', methods=['POST'])
def import_assignments():
    """Process uploaded CSV/Excel file for assignments"""
    if 'import_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'})
    
    file = request.files['import_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    # Get import options
    create_missing = 'create_missing' in request.form
    update_existing = 'update_existing' in request.form
    skip_empty = 'skip_empty' in request.form
    match_type = request.form.get('match_type', 'exact')
    
    # Process file based on its type
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1]
    
    # Dictionary to track created people
    created_people_info = []
    created_people_ids = []
    
    try:
        # Read the file into a pandas DataFrame
        if file_ext == '.csv':
            df = pd.read_csv(file)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file)
        else:
            return jsonify({'success': False, 'message': 'Unsupported file format'})
        
        # Print the DataFrame for debugging
        print("DataFrame contents:")
        print(df.head())
        
        # Validate required columns
        has_person_id = 'person_id' in df.columns
        has_name = 'first_name' in df.columns and 'last_name' in df.columns
        has_email = 'email' in df.columns
        has_phone = 'phone' in df.columns
        
        if not (has_person_id or has_name or has_email or has_phone):
            return jsonify({
                'success': False,
                'message': 'File must contain at least one identifier column (person_id, first_name+last_name, email, or phone)'
            })
        
        # Process each row in the file
        results = {
            'total': len(df),
            'updated': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0,
            'details': []
        }
        
        for index, row in df.iterrows():
            try:
                # Find the person in the database
                person = None
                params = []
                
                if has_person_id and not pd.isna(row['person_id']):
                    # Match by person_id
                    query = "SELECT person_id FROM church.people WHERE person_id = %s"
                    params = [row['person_id']]
                    existing = execute_query(query, params)
                    if existing:
                        person = existing[0][0]
                
                if person is None and has_email and not pd.isna(row['email']):
                    # Match by email
                    query = "SELECT person_id FROM church.people WHERE LOWER(email) = LOWER(%s)"
                    params = [row['email']]
                    existing = execute_query(query, params)
                    if existing:
                        person = existing[0][0]
                
                if person is None and has_phone and not pd.isna(row['phone']):
                    # Match by phone
                    query = "SELECT person_id FROM church.people WHERE phone = %s"
                    params = [str(row['phone'])]  # Convert phone to string explicitly
                    existing = execute_query(query, params)
                    if existing:
                        person = existing[0][0]
                
                if person is None and has_name and not pd.isna(row['first_name']) and not pd.isna(row['last_name']):
                    # Match by name
                    if match_type == 'exact':
                        query = """
                        SELECT person_id FROM church.people 
                        WHERE LOWER(first_name) = LOWER(%s) AND LOWER(last_name) = LOWER(%s)
                        """
                        params = [row['first_name'], row['last_name']]
                    else:
                        # Fuzzy match - simplified for this example
                        query = """
                        SELECT person_id FROM church.people 
                        WHERE LOWER(first_name) LIKE LOWER(%s) AND LOWER(last_name) LIKE LOWER(%s)
                        """
                        params = [f"%{row['first_name']}%", f"%{row['last_name']}%"]
                    
                    existing = execute_query(query, params)
                    if existing:
                        person = existing[0][0]
                
                # If person found and update_existing is checked, update their info
                if person is not None and update_existing:
                    # Determine which assignments to update
                    updates = {}
                    params = []
                    
                    # Get cell ID if cell_name is provided
                    if 'cell_name' in df.columns and not pd.isna(row['cell_name']):
                        cell_query = "SELECT cell_id FROM church.cells WHERE LOWER(cell_name) = LOWER(%s)"
                        cell_result = execute_query(cell_query, [row['cell_name']])
                        if cell_result:
                            updates['cell_id'] = cell_result[0][0]
                    
                    # Set active status if provided
                    if 'is_active' in df.columns and not pd.isna(row['is_active']):
                        # Handle different types that could be in the is_active column
                        if isinstance(row['is_active'], bool):
                            updates['is_active'] = row['is_active']
                        elif isinstance(row['is_active'], str):
                            updates['is_active'] = row['is_active'].lower() == 'true'
                        else:
                            # For numeric values, treat non-zero as true
                            updates['is_active'] = bool(row['is_active'])
                    
                    # Only update if there are changes to make
                    if updates:
                        set_clauses = []
                        params = []
                        
                        for key, value in updates.items():
                            set_clauses.append(f"{key} = %s")
                            params.append(value)
                        
                        params.append(person)
                        
                        update_query = f"""
                        UPDATE church.people
                        SET {', '.join(set_clauses)}
                        WHERE person_id = %s
                        """
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(update_query, params)
                        conn.commit()
                        cursor.close()
                        
                        results['updated'] += 1
                        results['details'].append({
                            'type': 'success',
                            'message': f"Updated person: {row.get('first_name', '')} {row.get('last_name', '')}"
                        })
                    else:
                        results['skipped'] += 1
                        results['details'].append({
                            'type': 'warning',
                            'message': f"No updates needed for: {row.get('first_name', '')} {row.get('last_name', '')}"
                        })
                
                # If person not found and create_missing is checked, create a new person
                elif person is None and create_missing and 'first_name' in df.columns and 'last_name' in df.columns:
                    # Get cell_id if cell_name is provided
                    cell_id = None
                    if 'cell_name' in df.columns and not pd.isna(row['cell_name']):
                        cell_query = "SELECT cell_id FROM church.cells WHERE LOWER(cell_name) = LOWER(%s)"
                        cell_result = execute_query(cell_query, [row['cell_name']])
                        if cell_result:
                            cell_id = cell_result[0][0]
                    
                    # Set active status if provided, default to true
                    is_active = True
                    if 'is_active' in df.columns and not pd.isna(row['is_active']):
                        # Handle different types that could be in the is_active column
                        if isinstance(row['is_active'], bool):
                            is_active = row['is_active']
                        elif isinstance(row['is_active'], str):
                            is_active = row['is_active'].lower() == 'true'
                        else:
                            # For numeric values, treat non-zero as true
                            is_active = bool(row['is_active'])
                    
                    # Insert new person
                    insert_query = """
                    INSERT INTO church.people (first_name, last_name, email, phone, cell_id, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING person_id
                    """
                    
                    email = row['email'] if 'email' in df.columns and not pd.isna(row['email']) else None
                    phone = str(row['phone']) if 'phone' in df.columns and not pd.isna(row['phone']) else None
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(insert_query, (
                        row['first_name'], 
                        row['last_name'],
                        email,
                        phone,
                        cell_id,
                        is_active
                    ))
                    person_id = cursor.fetchone()[0]
                    conn.commit()
                    cursor.close()
                    
                    created_people_ids.append(person_id)
                    
                    # Also track in our direct list
                    created_people_info.append({
                        'id': person_id,
                        'name': f"{row['first_name']} {row['last_name']}",
                        'email': email,
                        'phone': phone,
                        'cell': row.get('cell_name', '') if 'cell_name' in df.columns and not pd.isna(row['cell_name']) else '',
                        'team': '',
                        'department': '',
                        'direction': '',
                        'region': ''
                    })
                    
                    results['created'] += 1
                    results['details'].append({
                        'type': 'success',
                        'message': f"Created new person: {row['first_name']} {row['last_name']}"
                    })
                
                # If person not found and create_missing is not checked, skip
                elif person is None:
                    results['skipped'] += 1
                    results['details'].append({
                        'type': 'warning',
                        'message': f"Person not found, skipping: {row.get('first_name', '')} {row.get('last_name', '')}"
                    })
                
                # If person found but update_existing is not checked, skip
                else:
                    results['skipped'] += 1
                    results['details'].append({
                        'type': 'warning',
                        'message': f"Updates not enabled, skipping: {row.get('first_name', '')} {row.get('last_name', '')}"
                    })
            
            except Exception as e:
                results['errors'] += 1
                results['details'].append({
                    'type': 'error',
                    'message': f"Error processing row {index+1}: {str(e)}"
                })
        
        # If people were created, fetch their details to return
        created_people_details = []
        if created_people_ids:
            try:
                placeholders = ','.join(['%s'] * len(created_people_ids))
                people_query = f"""
                SELECT p.person_id, p.first_name, p.last_name, p.email, p.phone, 
                       c.cell_name, t.team_name, d.department_name, dir.direction_name, r.region_name
                FROM church.people p
                LEFT JOIN church.cells c ON p.cell_id = c.cell_id
                LEFT JOIN church.teams t ON c.team_id = t.team_id
                LEFT JOIN church.departments d ON t.department_id = d.department_id
                LEFT JOIN church.directions dir ON d.direction_id = dir.direction_id
                LEFT JOIN church.regions r ON dir.region_id = r.region_id
                WHERE p.person_id IN ({placeholders})
                """
                
                print(f"Querying created people: {created_people_ids}")
                created_people = execute_query(people_query, created_people_ids)
                print(f"Query result: {created_people}")
                
                for person in created_people:
                    created_people_details.append({
                        'id': person[0],
                        'name': f"{person[1]} {person[2]}",
                        'email': person[3],
                        'phone': person[4],
                        'cell': person[5],
                        'team': person[6],
                        'department': person[7],
                        'direction': person[8],
                        'region': person[9]
                    })
            except Exception as e:
                print(f"Error fetching created people details: {str(e)}")
                # Fall back to our direct tracking if query fails
                created_people_details = created_people_info
        else:
            # Fall back to our direct tracking if no IDs
            created_people_details = created_people_info
        
        return jsonify({
            'success': True,
            'results': results,
            'created_people': created_people_details
        })
    
    except Exception as e:
        print(f"Overall import error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error processing file: {str(e)}"
        })

@app.route('/verify_person', methods=['GET'])
def verify_person():
    """Verify if a person exists in the database by name"""
    first_name = request.args.get('first_name', '')
    last_name = request.args.get('last_name', '')
    
    if not first_name or not last_name:
        return jsonify({'success': False, 'message': 'First name and last name are required'})
    
    query = """
    SELECT p.person_id, p.first_name, p.last_name, p.email, p.phone, 
           c.cell_name, c.cell_id, t.team_name, t.team_id, 
           d.department_name, d.department_id, dir.direction_name, dir.direction_id,
           r.region_name, r.region_id, p.is_active
    FROM church.people p
    LEFT JOIN church.cells c ON p.cell_id = c.cell_id
    LEFT JOIN church.teams t ON c.team_id = t.team_id
    LEFT JOIN church.departments d ON t.department_id = d.department_id
    LEFT JOIN church.directions dir ON d.direction_id = dir.direction_id
    LEFT JOIN church.regions r ON dir.region_id = r.region_id
    WHERE LOWER(p.first_name) LIKE LOWER(%s) AND LOWER(p.last_name) LIKE LOWER(%s)
    """
    
    params = [f"%{first_name}%", f"%{last_name}%"]
    results = execute_query(query, params)
    
    if not results:
        return jsonify({
            'success': False, 
            'message': f"No person found with name like '{first_name} {last_name}'"
        })
    
    # Format the results
    people = []
    for person in results:
        people.append({
            'id': person[0],
            'name': f"{person[1]} {person[2]}",
            'email': person[3],
            'phone': person[4],
            'cell': person[5],
            'cell_id': person[6],
            'team': person[7],
            'team_id': person[8],
            'department': person[9],
            'department_id': person[10],
            'direction': person[11],
            'direction_id': person[12],
            'region': person[13],
            'region_id': person[14],
            'is_active': person[15]
        })
    
    return jsonify({
        'success': True,
        'people': people
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
