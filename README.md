# Church Attendance System

A simple, fast web application for marking attendance in church services, optimized for performance even in low network areas.

## Features

- View upcoming services
- Mark attendance by department, team, and cell hierarchy
- Quick search to find people by name
- Simple attendance reports
- Optimized for speed and performance in low-network environments

## Setup

1. First, update the database connection in the `.env` file:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=church
DB_USER=your_username
DB_PASSWORD=your_password
```

2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Run the application:

```
python app.py
```

4. Open your browser and navigate to `http://localhost:8080`

## Performance Optimizations

- Connection pooling for database efficiency
- Inline critical CSS for fast initial rendering
- Minimized JavaScript with deferred loading
- Proper caching headers for browser caching
- Collapsible hierarchical UI to minimize DOM elements
- Debounced search to reduce API calls
- Responsive design that works well on all devices

## Database Structure

The application connects to your existing church database with the following key tables:
- regions, directions, departments, teams, cells (organizational hierarchy)
- people (church members)
- service_types, services (church services)
- attendance (attendance records)

## Usage

1. Access the Services page to see upcoming services
2. Select a service to mark attendance
3. Use the hierarchy or search function to find people
4. Check the boxes for people who are present
5. Save the attendance records
6. View reports to track attendance over time
