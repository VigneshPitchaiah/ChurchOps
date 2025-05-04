from app import db
from sqlalchemy.sql import func

class Person(db.Model):
    __tablename__ = 'people'
    __table_args__ = {'schema': 'church'}
    
    person_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    cell_id = db.Column(db.Integer, db.ForeignKey('church.cells.cell_id'), nullable=False)
    direction = db.Column(db.String(100), nullable=False)  # Added direction column
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    country = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(10))  # 'M' or 'F'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    cell = db.relationship('Cell', back_populates='people')
    attendance_records = db.relationship('Attendance', back_populates='person', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def hierarchy_path(self):
        """Returns full organizational hierarchy path as a dictionary"""
        return {
            'cell': {
                'id': self.cell.cell_id,
                'name': self.cell.cell_name
            },
            'team': {
                'id': self.cell.team.team_id,
                'name': self.cell.team.team_name
            },
            'department': {
                'id': self.cell.team.department.department_id,
                'name': self.cell.team.department.department_name
            },
            'direction': {
                'id': self.cell.team.department.direction.direction_id,
                'name': self.cell.team.department.direction.direction_name
            },
            'region': {
                'id': self.cell.team.department.direction.region.region_id,
                'name': self.cell.team.department.direction.region.region_name
            }
        }
    
    def __repr__(self):
        return f'<Person {self.full_name}>'
