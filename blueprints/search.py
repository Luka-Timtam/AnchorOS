from flask import Blueprint, request, jsonify, url_for
from db_supabase import Lead, Client, Task, Note, ActivityLog, BossBattle, DailyMission, get_supabase

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
    
    client = get_supabase()
    results = {}
    
    leads_result = client.table('leads').select('*').neq('status', 'closed_won').or_(f'name.ilike.%{q}%,business_name.ilike.%{q}%,notes.ilike.%{q}%').limit(20).execute()
    results['leads'] = [{
        'id': l['id'],
        'label': l['name'] + (f" ({l['business_name']})" if l.get('business_name') else ''),
        'type': 'lead',
        'link': url_for('leads.detail', id=l['id'])
    } for l in leads_result.data]
    
    clients_result = client.table('clients').select('*').or_(f'name.ilike.%{q}%,business_name.ilike.%{q}%').limit(20).execute()
    results['clients'] = [{
        'id': c['id'],
        'label': c['name'] + (f" ({c['business_name']})" if c.get('business_name') else ''),
        'type': 'client',
        'link': url_for('clients.detail', id=c['id'])
    } for c in clients_result.data]
    
    tasks_result = client.table('tasks').select('*').or_(f'title.ilike.%{q}%,description.ilike.%{q}%').limit(20).execute()
    results['tasks'] = [{
        'id': t['id'],
        'label': t['title'],
        'type': 'task',
        'link': url_for('tasks.index') + f'#task-{t["id"]}'
    } for t in tasks_result.data]
    
    notes_result = client.table('notes').select('*').or_(f'title.ilike.%{q}%,content.ilike.%{q}%').limit(20).execute()
    results['notes'] = [{
        'id': n['id'],
        'label': n['title'],
        'type': 'note',
        'link': url_for('notes.edit', id=n['id'])
    } for n in notes_result.data]
    
    timeline_result = client.table('activity_log').select('*').ilike('description', f'%{q}%').order('created_at', desc=True).limit(20).execute()
    results['timeline'] = [{
        'id': a['id'],
        'label': a['description'][:80] + ('...' if len(a.get('description', '')) > 80 else ''),
        'type': 'timeline',
        'link': url_for('timeline.index')
    } for a in timeline_result.data]
    
    missions_result = client.table('daily_missions').select('*').ilike('mission_type', f'%{q}%').order('mission_date', desc=True).limit(20).execute()
    results['missions'] = [{
        'id': m['id'],
        'label': f"{m.get('mission_type', '')} - {m.get('mission_date', '')}",
        'type': 'mission',
        'link': url_for('missions.index')
    } for m in missions_result.data]
    
    boss_result = client.table('boss_battles').select('*').ilike('boss_name', f'%{q}%').order('month_start', desc=True).limit(20).execute()
    results['boss_fights'] = [{
        'id': b['id'],
        'label': b.get('boss_name', '')[:80],
        'type': 'boss_fight',
        'link': url_for('boss.index')
    } for b in boss_result.data]
    
    return jsonify(results)
