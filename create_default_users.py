"""
Create default users for ChurchOps
This script creates an admin user and a regular user with default credentials
"""
import os
from flask import Flask
from app import db
from app.models.users import User
from app import create_app

def create_default_users():
    print("Creating default users...")
    
    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@churchops.org',
            password='admin123',
            role='admin'
        )
        db.session.add(admin)
        print("Admin user created: admin / admin123")
    else:
        print("Admin user already exists")
    
    # Create regular user if not exists
    user = User.query.filter_by(username='user').first()
    if not user:
        user = User(
            username='user',
            email='user@churchops.org',
            password='user123',
            role='user'
        )
        db.session.add(user)
        print("Regular user created: user / user123")
    else:
        print("Regular user already exists")
    
    # Commit changes
    db.session.commit()
    print("Default users created successfully!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        create_default_users()
