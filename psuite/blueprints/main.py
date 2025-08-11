# psuite/blueprints/main.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__, template_folder='../templates')

@main_bp.route('/')
def home():
    # FIXED: The enhanced template is named 'home.html', not 'index.html'
    return render_template('home.html')

@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main_bp.route('/account')
@login_required
def account():
    # FIXED: Removed confusing credit width calculation.
    # The new template handles this logic directly with the user object.
    return render_template('account.html')