import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        crm_password = os.environ.get('CRM_PASSWORD', '')
        
        if crm_password and password == crm_password:
            session.permanent = True
            session['authenticated'] = True
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid password.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('auth.login'))
