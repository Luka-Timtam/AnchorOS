from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Goal
from blueprints.gamification import get_recommended_goal

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

@goals_bp.route('/')
def index():
    goal_types = [
        {'type': 'daily_outreach', 'period': 'daily', 'label': 'Daily Outreach', 'description': 'Number of outreach activities per day'},
        {'type': 'weekly_outreach', 'period': 'weekly', 'label': 'Weekly Outreach', 'description': 'Number of outreach activities per week'},
        {'type': 'monthly_revenue', 'period': 'monthly', 'label': 'Monthly Revenue', 'description': 'Target project revenue per month ($)'},
        {'type': 'monthly_deals', 'period': 'monthly', 'label': 'Monthly Deals', 'description': 'Number of deals closed per month'},
    ]
    
    goals_data = []
    for gt in goal_types:
        goal = Goal.get_or_create(gt['type'], gt['period'])
        recommended = get_recommended_goal(gt['type'])
        current_value = goal.target_value if goal.is_manual else recommended
        
        if not goal.is_manual and goal.target_value != recommended:
            goal.target_value = recommended
            db.session.commit()
        
        goals_data.append({
            'id': goal.id,
            'type': gt['type'],
            'label': gt['label'],
            'description': gt['description'],
            'current': current_value,
            'recommended': recommended,
            'is_manual': goal.is_manual,
            'period': gt['period']
        })
    
    return render_template('goals/index.html', goals=goals_data)

@goals_bp.route('/update', methods=['POST'])
def update():
    goal_type = request.form.get('goal_type')
    period = request.form.get('period')
    target_value = request.form.get('target_value', type=int)
    is_manual = request.form.get('is_manual') == 'on'
    
    goal = Goal.query.filter_by(goal_type=goal_type, period=period).first()
    if goal:
        if is_manual and target_value is not None:
            goal.target_value = target_value
            goal.is_manual = True
        else:
            goal.target_value = get_recommended_goal(goal_type)
            goal.is_manual = False
        db.session.commit()
        flash('Goal updated!', 'success')
    
    return redirect(url_for('goals.index'))

@goals_bp.route('/reset/<int:goal_id>', methods=['POST'])
def reset(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    goal.is_manual = False
    goal.target_value = get_recommended_goal(goal.goal_type)
    db.session.commit()
    flash('Goal reset to recommended value!', 'success')
    return redirect(url_for('goals.index'))
