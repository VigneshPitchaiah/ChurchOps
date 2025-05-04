from flask import Blueprint, render_template, request, jsonify, send_file
import io
import csv

from app import db, cache
from app.models.services import Service, ServiceType, Attendance
from app.models.people import Person
from app.models.organization import Region, Direction, Department, Team, Cell
from sqlalchemy import func, desc, case
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
    
    # First pass: collect all unique dates
    for date, service_name, count in results:
        formatted_date = date.strftime('%d %b')
        if formatted_date not in dates:
            dates.append(formatted_date)
    
    # Second pass: process attendance data
    for date, service_name, count in results:
        formatted_date = date.strftime('%d %b')
        
        # Initialize service type if not exists
        if service_name not in service_types:
            service_types[service_name] = [0] * len(dates)
        # Ensure array is properly sized (in case it was created before all dates were collected)
        elif len(service_types[service_name]) < len(dates):
            service_types[service_name] = service_types[service_name] + [0] * (len(dates) - len(service_types[service_name]))
        
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

@reports_bp.route('/detailed-report')
@cache_view(timeout=0)
def detailed_report():
    """Get detailed attendance report with filters"""
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
    gender = request.args.get('gender')
    download = request.args.get('download') == 'true'

    # Get organizational units with their relationships for filtering
    regions = Region.query.order_by(Region.region_name).all()
    directions = Direction.query.join(Region).order_by(Direction.direction_name).all()
    departments = Department.query.join(Direction).order_by(Department.department_name).all()
    teams = Team.query.join(Department).order_by(Team.team_name).all()
    cells = Cell.query.join(Team).order_by(Cell.cell_name).all()

    # Build base query for person data
    query = db.session.query(
        Person.person_id,
        Person.first_name,
        Person.last_name,
        Person.gender,
        Cell.cell_name,
        Team.team_name,
        Department.department_name,
        Direction.direction_name,
        Region.region_name
    ).select_from(Person).join(
        Cell, Person.cell_id == Cell.cell_id
    ).join(
        Team, Cell.team_id == Team.team_id
    ).join(
        Department, Team.department_id == Department.department_id
    ).join(
        Direction, Department.direction_id == Direction.direction_id
    ).join(
        Region, Direction.region_id == Region.region_id
    )
    
    # Build subquery for attendance data within date range
    attendance_subquery = db.session.query(
        Attendance.person_id,
        func.sum(case(
            (Attendance.status == 'present', 1),
            (Attendance.status == 'watched_recording', 0.5),
            else_=0
        )).label('attendance_points'),
        func.count(Attendance.attendance_id).label('marked_services'),
        func.sum(case(
            (Attendance.status == 'present', 1),
            else_=0
        )).label('present_count'),
        func.sum(case(
            (Attendance.status == 'watched_recording', 1),
            else_=0
        )).label('watched_recording_count'),
        func.sum(case(
            (Attendance.status == 'absent', 1),
            else_=0
        )).label('absent_count')
    ).join(
        Service, Attendance.service_id == Service.service_id
    ).filter(
        Service.service_date.between(start_date, end_date)
    )
    
    # Apply service type filter to the subquery if provided
    if service_type_id:
        attendance_subquery = attendance_subquery.filter(Service.service_type_id == service_type_id)
    
    # Group the attendance data by person
    attendance_subquery = attendance_subquery.group_by(Attendance.person_id).subquery()
    
    # Get the total number of services in the date range
    service_count_query = db.session.query(func.count(Service.service_id))
    service_count_query = service_count_query.filter(Service.service_date.between(start_date, end_date))
    if service_type_id:
        service_count_query = service_count_query.filter(Service.service_type_id == service_type_id)
    total_services = service_count_query.scalar() or 0
    
    # Join with the attendance data and add columns from subquery
    query = query.add_columns(
        attendance_subquery.c.attendance_points,
        attendance_subquery.c.marked_services,
        attendance_subquery.c.present_count,
        attendance_subquery.c.watched_recording_count,
        attendance_subquery.c.absent_count
    ).outerjoin(
        attendance_subquery,
        Person.person_id == attendance_subquery.c.person_id
    )

    # Apply filters
    if region_id:
        query = query.filter(Region.region_id == region_id)
    if direction_id:
        query = query.filter(Direction.direction_id == direction_id)
    if department_id:
        query = query.filter(Department.department_id == department_id)
    if team_id:
        query = query.filter(Team.team_id == team_id)
    if cell_id:
        query = query.filter(Cell.cell_id == cell_id)
    if gender:
        query = query.filter(Person.gender == gender)

    # Order results
    query = query.order_by(
        Region.region_name,
        Direction.direction_name,
        Department.department_name,
        Team.team_name,
        Cell.cell_name,
        Person.first_name,
        Person.last_name
    )

    # Process results
    results_list = []
    for person_data in query.all():
        # Get attendance stats, defaulting to 0 if None
        attendance_points = float(person_data.attendance_points or 0)
        marked_services = int(person_data.marked_services or 0)
        present_count = int(person_data.present_count or 0)
        watched_recording_count = int(person_data.watched_recording_count or 0)
        absent_count = int(person_data.absent_count or 0)
        
        # Calculate percentage based on points
        # Present = 1 point, Watched Recording = 0.5 points
        max_possible_points = total_services * 1.0  # Maximum points if present at all services
        attendance_percentage = (attendance_points / max_possible_points * 100) if max_possible_points > 0 else 0
        
        # Create result object
        result = {
            'first_name': person_data.first_name,
            'last_name': person_data.last_name,
            'gender': person_data.gender,
            'cell_name': person_data.cell_name,
            'team_name': person_data.team_name,
            'department_name': person_data.department_name,
            'direction_name': person_data.direction_name,
            'region_name': person_data.region_name,
            'present_count': present_count,
            'watched_recording_count': watched_recording_count,
            'absent_count': absent_count,
            'marked_services': marked_services,
            'total_services': total_services,
            'attendance_percentage': attendance_percentage
        }
        results_list.append(result)

    if download:
        # Prepare CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'First Name', 'Last Name', 'Gender', 'Cell', 'Team', 
            'Department', 'Zone', 'Region', 'Present Count', 
            'Watched Recording Count', 'Absent Count', 'Total Marked',
            'Total Services', 'Attendance Percentage'
        ])
        
        # Write data
        for row in results_list:
            writer.writerow([
                row['first_name'], row['last_name'], row['gender'] or 'Not specified',
                row['cell_name'], row['team_name'], row['department_name'],
                row['direction_name'], row['region_name'], row['present_count'],
                row['watched_recording_count'], row['absent_count'], row['marked_services'],
                row['total_services'], f"{row['attendance_percentage']:.1f}%"
            ])
        
        # Prepare response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'attendance_report_{datetime.now().strftime("%Y%m%d")}.csv'
        )

    # For AJAX requests, return JSON with proper content type
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = jsonify({
            'results': results_list,
            'total_services': total_services
        })
        # Ensure proper content type for JSON response
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    # For regular requests, render template
    return render_template(
        'reports/detailed_report.html',
        results=results_list,
        days=days,
        regions=regions,
        directions=directions,
        departments=departments,
        teams=teams,
        cells=cells,
        now=datetime.now(),
        total_services=total_services
    )
