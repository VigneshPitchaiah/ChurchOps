from app import db
from datetime import datetime
from sqlalchemy.sql import func

class Region(db.Model):
    __tablename__ = 'regions'
    __table_args__ = {'schema': 'church'}
    
    region_id = db.Column(db.Integer, primary_key=True)
    region_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    directions = db.relationship('Direction', back_populates='region', lazy='dynamic')
    
    def __repr__(self):
        return f'<Region {self.region_name}>'


class Direction(db.Model):
    __tablename__ = 'directions'
    __table_args__ = {'schema': 'church'}
    
    direction_id = db.Column(db.Integer, primary_key=True)
    direction_name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('church.regions.region_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    region = db.relationship('Region', back_populates='directions')
    departments = db.relationship('Department', back_populates='direction', lazy='dynamic')
    
    def __repr__(self):
        return f'<Direction {self.direction_name}>'


class Department(db.Model):
    __tablename__ = 'departments'
    __table_args__ = {'schema': 'church'}
    
    department_id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), nullable=False)
    direction_id = db.Column(db.Integer, db.ForeignKey('church.directions.direction_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    direction = db.relationship('Direction', back_populates='departments')
    teams = db.relationship('Team', back_populates='department', lazy='dynamic')
    
    def __repr__(self):
        return f'<Department {self.department_name}>'


class Team(db.Model):
    __tablename__ = 'teams'
    __table_args__ = {'schema': 'church'}
    
    team_id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('church.departments.department_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    department = db.relationship('Department', back_populates='teams')
    cells = db.relationship('Cell', back_populates='team', lazy='dynamic')
    
    def __repr__(self):
        return f'<Team {self.team_name}>'


class Cell(db.Model):
    __tablename__ = 'cells'
    __table_args__ = {'schema': 'church'}
    
    cell_id = db.Column(db.Integer, primary_key=True)
    cell_name = db.Column(db.String(100), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('church.teams.team_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    team = db.relationship('Team', back_populates='cells')
    people = db.relationship('Person', back_populates='cell', lazy='dynamic')
    
    def __repr__(self):
        return f'<Cell {self.cell_name}>'
