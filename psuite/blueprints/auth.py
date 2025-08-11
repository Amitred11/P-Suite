# psuite/blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from psuite.models import User
from psuite import db

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user, remember=True) # Added remember=True for better UX
            flash(f"Welcome back, {user.username}!", 'success')
            return redirect(url_for('tools.frontend_optimizer'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        
        # FIXED: Check for existing username OR email
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'warning')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email address is already registered.', 'warning')
            return redirect(url_for('auth.register'))
            
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        
        # FIXED: Added email to the new User object
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))