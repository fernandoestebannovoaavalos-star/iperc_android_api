from flask import render_template
from flask_login import login_required, current_user
from app.main import main

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html', usuario=current_user)