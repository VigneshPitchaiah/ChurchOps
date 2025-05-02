from app import db
from sqlalchemy.sql import func
from datetime import datetime

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    __table_args__ = {'schema': 'church'}
    
    service_type_id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    services = db.relationship('Service', back_populates='service_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<ServiceType {self.service_name}>'


class Service(db.Model):
    __tablename__ = 'services'
    __table_args__ = {'schema': 'church'}
    
    service_id = db.Column(db.Integer, primary_key=True)
    service_type_id = db.Column(db.Integer, db.ForeignKey('church.service_types.service_type_id'), nullable=False)
    service_date = db.Column(db.Date, nullable=False)
    service_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    service_type = db.relationship('ServiceType', back_populates='services')
    attendance_records = db.relationship('Attendance', back_populates='service', lazy='dynamic')
    
    @property
    def formatted_date(self):
        return self.service_date.strftime('%d %b %Y')
    
    @property
    def formatted_time(self):
        return self.service_time.strftime('%I:%M %p')
    
    @property
    def is_upcoming(self):
        today = datetime.now().date()
        return self.service_date >= today
    
    # Get service name for display
    @property
    def service_name(self):
        if hasattr(self, 'service_type') and self.service_type:
            return self.service_type.service_name
        return "Unknown Service"
    
    def __repr__(self):
        return f'<Service {self.service_type.service_name} on {self.formatted_date}>'


class Attendance(db.Model):
    __tablename__ = 'attendance'
    __table_args__ = {'schema': 'church'}
    
    attendance_id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('church.services.service_id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('church.people.person_id'), nullable=False)
    check_in_time = db.Column(db.DateTime, nullable=True)  # Made nullable to support absence
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='present')  # 'present', 'absent'
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())
    
    # Relationships
    service = db.relationship('Service', back_populates='attendance_records')
    person = db.relationship('Person', back_populates='attendance_records')
    
    def __repr__(self):
        return f'<Attendance {self.person.full_name} at {self.service.service_type.service_name} - {self.status}>'
