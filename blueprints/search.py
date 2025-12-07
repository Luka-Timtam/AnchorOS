from flask import Blueprint, request, jsonify, url_for
from models import db, Lead, Client, Task, Note, ActivityLog, BossFight, DailyMission
from sqlalchemy import or_

search_bp = Blueprint('search', __name__, url_prefix='/search')

@search_bp.route('')
def search():
    q = request.args.get('q', '').strip()
    
    if not q or len(q) < 2:
        return jsonify({
            'leads': [],
            'clients': [],
            'tasks': [],
            'notes': [],
            'timeline': [],
            'missions': [],
            'boss_fights': []
        })
    
    search_term = f'%{q}%'
    results = {}
    
    leads = Lead.query.filter(
        Lead.status != 'closed_won',
        or_(
            Lead.name.ilike(search_term),
            Lead.business_name.ilike(search_term),
            Lead.notes.ilike(search_term)
        )
    ).limit(20).all()
    
    results['leads'] = [{
        'id': l.id,
        'label': l.name + (f' ({l.business_name})' if l.business_name else ''),
        'type': 'lead',
        'link': url_for('leads.detail', id=l.id)
    } for l in leads]
    
    clients = Client.query.filter(
        or_(
            Client.name.ilike(search_term),
            Client.business_name.ilike(search_term)
        )
    ).limit(20).all()
    
    results['clients'] = [{
        'id': c.id,
        'label': c.name + (f' ({c.business_name})' if c.business_name else ''),
        'type': 'client',
        'link': url_for('clients.detail', id=c.id)
    } for c in clients]
    
    tasks = Task.query.filter(
        or_(
            Task.title.ilike(search_term),
            Task.description.ilike(search_term)
        )
    ).limit(20).all()
    
    results['tasks'] = [{
        'id': t.id,
        'label': t.title,
        'type': 'task',
        'link': url_for('tasks.index') + f'#task-{t.id}'
    } for t in tasks]
    
    notes = Note.query.filter(
        or_(
            Note.title.ilike(search_term),
            Note.content.ilike(search_term)
        )
    ).limit(20).all()
    
    results['notes'] = [{
        'id': n.id,
        'label': n.title,
        'type': 'note',
        'link': url_for('notes.edit', id=n.id)
    } for n in notes]
    
    timeline = ActivityLog.query.filter(
        ActivityLog.description.ilike(search_term)
    ).order_by(ActivityLog.timestamp.desc()).limit(20).all()
    
    results['timeline'] = [{
        'id': a.id,
        'label': a.description[:80] + ('...' if len(a.description) > 80 else ''),
        'type': 'timeline',
        'link': url_for('timeline.index')
    } for a in timeline]
    
    missions = DailyMission.query.filter(
        DailyMission.description.ilike(search_term)
    ).order_by(DailyMission.mission_date.desc()).limit(20).all()
    
    results['missions'] = [{
        'id': m.id,
        'label': m.description,
        'type': 'mission',
        'link': url_for('missions.index')
    } for m in missions]
    
    boss_fights = BossFight.query.filter(
        BossFight.description.ilike(search_term)
    ).order_by(BossFight.created_at.desc()).limit(20).all()
    
    results['boss_fights'] = [{
        'id': b.id,
        'label': b.description[:80] + ('...' if len(b.description) > 80 else ''),
        'type': 'boss_fight',
        'link': url_for('boss.index')
    } for b in boss_fights]
    
    return jsonify(results)
