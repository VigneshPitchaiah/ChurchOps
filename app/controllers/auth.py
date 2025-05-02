from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.users import User
from datetime import datetime
from functools import wraps

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            flash('Admin access required', 'danger')
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    next_url = request.args.get('next', url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            # Set user in session
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['role'] = user.role
            session.permanent = remember
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_url)
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = User.query.get(session['user_id'])
    return render_template('auth/profile.html', user=user)
