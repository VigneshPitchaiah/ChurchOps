from app import db, create_app
from sqlalchemy import text

def update_attendance_schema():
    """
    Update the attendance table schema to add the status column
    and make check_in_time nullable
    """
    print("Starting database schema update...")
    
    app = create_app()
    with app.app_context():
        # Execute the SQL statements to update the schema
        try:
            # Check if status column already exists
            result = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'church' AND table_name = 'attendance' AND column_name = 'status'"
            )).fetchall()
            
            if not result:
                print("Adding status column to attendance table...")
                db.session.execute(text(
                    "ALTER TABLE church.attendance "
                    "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'present'"
                ))
                
                print("Updating existing records...")
                db.session.execute(text(
                    "UPDATE church.attendance "
                    "SET status = 'present' "
                    "WHERE check_in_time IS NOT NULL"
                ))
            else:
                print("Status column already exists, skipping...")
            
            # Check if check_in_time is nullable
            result = db.session.execute(text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'church' AND table_name = 'attendance' AND column_name = 'check_in_time'"
            )).fetchone()
            
            if result and result[0] == 'NO':  # Not nullable
                print("Making check_in_time column nullable...")
                db.session.execute(text(
                    "ALTER TABLE church.attendance "
                    "ALTER COLUMN check_in_time DROP NOT NULL"
                ))
            else:
                print("check_in_time is already nullable, skipping...")
            
            # Commit the transaction
            db.session.commit()
            print("Database schema updated successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    update_attendance_schema()
