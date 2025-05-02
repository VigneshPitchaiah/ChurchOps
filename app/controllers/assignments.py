from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file

from app import db, cache
from app.models.people import Person
from app.models.organization import Region, Direction, Department, Team, Cell
from sqlalchemy import or_
from app.services.cache_service import invalidate_cache
from datetime import datetime
import pandas as pd
import io
import csv
from werkzeug.utils import secure_filename

# Create blueprint
assignments_bp = Blueprint('assignments', __name__, url_prefix='/assignments')

@assignments_bp.route('/')

def assignments_index():
    """Assignment management page"""
    # Get dropdown data for filters
    regions = Region.query.order_by(Region.region_name).all()
    directions = Direction.query.join(Region).order_by(Direction.direction_name).all()
    departments = Department.query.join(Direction).order_by(Department.department_name).all()
    teams = Team.query.join(Department).order_by(Team.team_name).all()
    cells = Cell.query.join(Team).order_by(Cell.cell_name).all()
    
    return render_template(
        'assignments/index.html',
        regions=regions,
        directions=directions,
        departments=departments,
        teams=teams,
        cells=cells,
        now=datetime.now()
    )

@assignments_bp.route('/search', methods=['GET'])

def search_bulk_people():
    """Search for people based on their assignments"""
    # Get filter parameters
    region_id = request.args.get('region_id', type=int)
    direction_id = request.args.get('direction_id', type=int)
    department_id = request.args.get('department_id', type=int)
    team_id = request.args.get('team_id', type=int)
    cell_id = request.args.get('cell_id', type=int)
    is_active = request.args.get('is_active', 'true') == 'true'
    name_search = request.args.get('name_search', '')
    
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
    
    if name_search:
        people_query = people_query.filter(
            or_(
                Person.first_name.ilike(f'%{name_search}%'),
                Person.last_name.ilike(f'%{name_search}%')
            )
        )
    
    # Order results
    people_query = people_query.order_by(
        Person.last_name,
        Person.first_name
    )
    
    # Limit results for performance
    people = people_query.limit(100).all()
    
    # Format results for the frontend
    results = []
    for person in people:
        hierarchy = person.hierarchy_path
        results.append({
            'id': person.person_id,
            'name': f"{person.first_name} {person.last_name}",
            'cell': {
                'id': hierarchy['cell']['id'],
                'name': hierarchy['cell']['name']
            },
            'team': {
                'id': hierarchy['team']['id'],
                'name': hierarchy['team']['name']
            },
            'department': {
                'id': hierarchy['department']['id'],
                'name': hierarchy['department']['name']
            },
            'direction': {
                'id': hierarchy['direction']['id'],
                'name': hierarchy['direction']['name']
            },
            'region': {
                'id': hierarchy['region']['id'],
                'name': hierarchy['region']['name']
            }
        })
    
    return jsonify(results)

@assignments_bp.route('/save', methods=['POST'])

def save_assignment():
    """Save individual person assignment"""
    person_id = request.form.get('person_id', type=int)
    cell_id = request.form.get('cell_id', type=int)
    
    if not person_id or not cell_id:
        flash('Missing required information', 'danger')
        return redirect(url_for('assignments.assignments_index'))
    
    # Get the person
    person = Person.query.get_or_404(person_id)
    
    # Update their cell assignment
    person.cell_id = cell_id
    db.session.commit()
    
    # Invalidate any cached data
    invalidate_cache('people')
    
    flash('Assignment updated successfully', 'success')
    return redirect(url_for('assignments.assignments_index'))

@assignments_bp.route('/bulk-save', methods=['POST'])

def save_bulk_assignment():
    """Save bulk assignments for multiple people"""
    person_ids = request.form.getlist('person_ids')
    cell_id = request.form.get('cell_id', type=int)
    
    if not person_ids or not cell_id:
        flash('Missing required information', 'danger')
        return redirect(url_for('assignments.assignments_index'))
    
    # Update all selected people
    for person_id in person_ids:
        person = Person.query.get(person_id)
        if person:
            person.cell_id = cell_id
    
    db.session.commit()
    
    # Invalidate any cached data
    invalidate_cache('people')
    
    flash(f'{len(person_ids)} assignments updated successfully', 'success')
    return redirect(url_for('assignments.assignments_index'))

@assignments_bp.route('/template')

def download_template():
    """Download a CSV template for assignment imports"""
    # Create a StringIO object
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['First Name', 'Last Name', 'Email', 'Phone', 'Region', 'Direction', 'Department', 'Team', 'Cell'])
    
    # Write a sample row
    writer.writerow(['John', 'Doe', 'john.doe@example.com', '1234567890', 'Central', 'Youth', 'Music', 'Vocals', 'Choir'])
    
    # Reset file pointer
    output.seek(0)
    
    # Create a response and set headers
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='assignment_template.csv'
    )

@assignments_bp.route('/import', methods=['POST'])

def import_assignments():
    """Process uploaded CSV/Excel file for assignments"""
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('assignments.assignments_index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('assignments.assignments_index'))
    
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        flash('File must be CSV or Excel', 'danger')
        return redirect(url_for('assignments.assignments_index'))
    
    try:
        # Read the file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Validate columns
        required_columns = ['First Name', 'Last Name', 'Region', 'Direction', 'Department', 'Team', 'Cell']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            flash(f"Missing required columns: {', '.join(missing_columns)}", 'danger')
            return redirect(url_for('assignments.assignments_index'))
        
        # Process each row
        success_count = 0
        error_count = 0
        error_messages = []
        
        for index, row in df.iterrows():
            try:
                # Check if person exists and handle NaN values
                first_name = row['First Name']
                last_name = row['Last Name']
                
                # Convert NaN values to empty string for string fields
                first_name = '' if pd.isna(first_name) else str(first_name)
                last_name = '' if pd.isna(last_name) else str(last_name)
                email = '' if pd.isna(row.get('Email')) else str(row.get('Email'))
                phone = '' if pd.isna(row.get('Phone')) else str(row.get('Phone'))
                
                person = Person.query.filter(
                    Person.first_name == first_name,
                    Person.last_name == last_name
                ).first()
                
                # If person doesn't exist, create them
                if not person:
                    # Get or create organizational units
                    region_name = str(row['Region']) if pd.notna(row['Region']) else ''
                    direction_name = str(row['Direction']) if pd.notna(row['Direction']) else ''
                    department_name = str(row['Department']) if pd.notna(row['Department']) else ''
                    team_name = str(row['Team']) if pd.notna(row['Team']) else ''
                    cell_name = str(row['Cell']) if pd.notna(row['Cell']) else ''
                    
                    # Get or create region
                    region = Region.query.filter_by(region_name=region_name).first()
                    if not region:
                        region = Region(region_name=region_name)
                        db.session.add(region)
                        db.session.flush()  # Get ID before next use
                    
                    # Get or create direction
                    direction = Direction.query.filter_by(
                        direction_name=direction_name,
                        region_id=region.region_id
                    ).first()
                    if not direction:
                        direction = Direction(direction_name=direction_name, region_id=region.region_id)
                        db.session.add(direction)
                        db.session.flush()
                    
                    # Get or create department
                    department = Department.query.filter_by(
                        department_name=department_name,
                        direction_id=direction.direction_id
                    ).first()
                    if not department:
                        department = Department(department_name=department_name, direction_id=direction.direction_id)
                        db.session.add(department)
                        db.session.flush()
                    
                    # Get or create team
                    team = Team.query.filter_by(
                        team_name=team_name,
                        department_id=department.department_id
                    ).first()
                    if not team:
                        team = Team(team_name=team_name, department_id=department.department_id)
                        db.session.add(team)
                        db.session.flush()
                    
                    # Get or create cell
                    cell = Cell.query.filter_by(
                        cell_name=cell_name,
                        team_id=team.team_id
                    ).first()
                    if not cell:
                        cell = Cell(cell_name=cell_name, team_id=team.team_id)
                        db.session.add(cell)
                        db.session.flush()
                    
                    # Create person
                    email = row.get('Email', None)
                    phone = row.get('Phone', None)
                    
                    person = Person(
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone=phone,
                        cell_id=cell.cell_id,
                        is_active=True
                    )
                    db.session.add(person)
                    
                else:
                    # Update existing person's assignment
                    region_name = row['Region']
                    direction_name = row['Direction']
                    department_name = row['Department']
                    team_name = row['Team']
                    cell_name = row['Cell']
                    
                    # Find the cell with the given hierarchy
                    cell = Cell.query.join(Team).join(Department).join(Direction).join(Region).filter(
                        Region.region_name == region_name,
                        Direction.direction_name == direction_name,
                        Department.department_name == department_name,
                        Team.team_name == team_name,
                        Cell.cell_name == cell_name
                    ).first()
                    
                    # If cell doesn't exist, create the hierarchy
                    if not cell:
                        # Get or create region
                        region = Region.query.filter_by(region_name=region_name).first()
                        if not region:
                            region = Region(region_name=region_name)
                            db.session.add(region)
                            db.session.flush()
                        
                        # Get or create direction
                        direction = Direction.query.filter_by(
                            direction_name=direction_name,
                            region_id=region.region_id
                        ).first()
                        if not direction:
                            direction = Direction(direction_name=direction_name, region_id=region.region_id)
                            db.session.add(direction)
                            db.session.flush()
                        
                        # Get or create department
                        department = Department.query.filter_by(
                            department_name=department_name,
                            direction_id=direction.direction_id
                        ).first()
                        if not department:
                            department = Department(department_name=department_name, direction_id=direction.direction_id)
                            db.session.add(department)
                            db.session.flush()
                        
                        # Get or create team
                        team = Team.query.filter_by(
                            team_name=team_name,
                            department_id=department.department_id
                        ).first()
                        if not team:
                            team = Team(team_name=team_name, department_id=department.department_id)
                            db.session.add(team)
                            db.session.flush()
                        
                        # Create cell
                        cell = Cell(cell_name=cell_name, team_id=team.team_id)
                        db.session.add(cell)
                        db.session.flush()
                    
                    # Update person's cell
                    person.cell_id = cell.cell_id
                    
                    # Update email and phone if provided
                    if 'Email' in row and pd.notna(row['Email']):
                        person.email = row['Email']
                    
                    if 'Phone' in row and pd.notna(row['Phone']):
                        person.phone = row['Phone']
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_messages.append(f"Error in row {index + 2}: {str(e)}")
        
        # Commit all changes
        db.session.commit()
        
        # Invalidate any cached data
        invalidate_cache('people')
        
        # Report results
        if error_count > 0:
            flash(f"Processed {success_count} records with {error_count} errors. See details below.", 'warning')
            for error in error_messages[:10]:  # Show first 10 errors
                flash(error, 'danger')
            if len(error_messages) > 10:
                flash(f"...and {len(error_messages) - 10} more errors", 'danger')
        else:
            flash(f"Successfully processed {success_count} records", 'success')
        
        return redirect(url_for('assignments.assignments_index'))
        
    except Exception as e:
        flash(f"Error processing file: {str(e)}", 'danger')
        return redirect(url_for('assignments.assignments_index'))
