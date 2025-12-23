from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_supabase import Note, UserStats, ActivityLog, XPLog, get_supabase
from datetime import date, datetime
import timezone as tz

notes_bp = Blueprint('notes', __name__, url_prefix='/notes')


def get_all_tags():
    client = get_supabase()
    result = client.table('notes').select('tags').filter('tags', 'not.is', 'null').neq('tags', '').execute()
    all_tags = set()
    for row in result.data:
        if row.get('tags'):
            for tag in row['tags'].split(','):
                tag = tag.strip()
                if tag:
                    all_tags.add(tag)
    return sorted(list(all_tags))


def has_note_today():
    client = get_supabase()
    today = date.today()
    # Using id for existence check if created_at is problematic or just filtering by id range if possible,
    # but since created_at exists in notes (unlike wins_log), we check it but ensure safe comparison
    result = client.table('notes').select('id', count='exact').gte('updated_at', f'{today.isoformat()}T00:00:00').execute()
    return (result.count if result.count else len(result.data)) > 0


def has_pinned_today():
    client = get_supabase()
    today = date.today()
    result = client.table('notes').select('id', count='exact').eq('pinned', True).gte('updated_at', f'{today.isoformat()}T00:00:00').execute()
    return (result.count if result.count else len(result.data)) > 0


@notes_bp.route('/')
def index():
    search = request.args.get('search', '').strip()
    tag_filter = request.args.get('tag', '').strip()
    sort_by = request.args.get('sort', 'updated_desc')
    
    client = get_supabase()
    
    order_field = 'updated_at'
    order_desc = True
    
    if sort_by == 'updated_asc':
        order_field = 'updated_at'
        order_desc = False
    elif sort_by == 'created_desc':
        order_field = 'created_at'
        order_desc = True
    elif sort_by == 'created_asc':
        order_field = 'created_at'
        order_desc = False
    elif sort_by == 'title_asc':
        order_field = 'title'
        order_desc = False
    elif sort_by == 'title_desc':
        order_field = 'title'
        order_desc = True
    
    pinned_query = client.table('notes').select('*').eq('pinned', True)
    unpinned_query = client.table('notes').select('*').eq('pinned', False)
    
    if search:
        pinned_query = pinned_query.or_(f'title.ilike.%{search}%,content.ilike.%{search}%')
        unpinned_query = unpinned_query.or_(f'title.ilike.%{search}%,content.ilike.%{search}%')
    
    if tag_filter:
        pinned_query = pinned_query.ilike('tags', f'%{tag_filter}%')
        unpinned_query = unpinned_query.ilike('tags', f'%{tag_filter}%')
    
    pinned_result = pinned_query.order(order_field, desc=order_desc).execute()
    unpinned_result = unpinned_query.order(order_field, desc=order_desc).execute()
    
    pinned_notes = [Note._parse_row(row) for row in pinned_result.data]
    unpinned_notes = [Note._parse_row(row) for row in unpinned_result.data]
    
    all_tags = get_all_tags()
    
    return render_template('notes/index.html',
                         pinned_notes=pinned_notes,
                         unpinned_notes=unpinned_notes,
                         search=search,
                         tag_filter=tag_filter,
                         sort_by=sort_by,
                         all_tags=all_tags)


@notes_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = request.form.get('tags', '').strip()
        
        if not title:
            flash('Title is required', 'error')
            return render_template('notes/new.html', title=title, content=content, tags=tags, all_tags=get_all_tags())
        
        if not content:
            flash('Content is required', 'error')
            return render_template('notes/new.html', title=title, content=content, tags=tags, all_tags=get_all_tags())
        
        is_first_today = not has_note_today()
        
        now = tz.now_iso()
        note = Note.insert({
            'title': title,
            'content': content,
            'tags': tags if tags else '',
            'pinned': False,
            'created_at': now,
            'updated_at': now
        })
        
        if is_first_today:
            user_stats = UserStats.get_stats()
            new_xp = (getattr(user_stats, 'current_xp', 0) or 0) + 2
            UserStats.update_by_id(user_stats.id, {'current_xp': new_xp})
            XPLog.insert({'amount': 2, 'reason': 'First note of the day'})
            ActivityLog.log_activity('note_created', f'Created note: {title}', note.id, 'note')
            flash(f'Note created! +2 XP for first note today!', 'success')
        else:
            ActivityLog.log_activity('note_created', f'Created note: {title}', note.id, 'note')
            flash('Note created!', 'success')
        
        return redirect(url_for('notes.view', id=note.id))
    
    all_tags = get_all_tags()
    return render_template('notes/new.html', all_tags=all_tags)


@notes_bp.route('/<int:id>')
def view(id):
    note = Note.get_by_id(id)
    if not note:
        abort(404)
    return render_template('notes/view.html', note=note)


@notes_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    note = Note.get_by_id(id)
    if not note:
        abort(404)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = request.form.get('tags', '').strip()
        
        if not title:
            flash('Title is required', 'error')
            return render_template('notes/edit.html', note=note, all_tags=get_all_tags())
        
        if not content:
            flash('Content is required', 'error')
            return render_template('notes/edit.html', note=note, all_tags=get_all_tags())
        
        Note.update_by_id(id, {
            'title': title,
            'content': content,
            'tags': tags if tags else '',
            'updated_at': tz.now_iso()
        })
        
        flash('Note updated!', 'success')
        return redirect(url_for('notes.view', id=note.id))
    
    all_tags = get_all_tags()
    return render_template('notes/edit.html', note=note, all_tags=all_tags)


@notes_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    note = Note.get_by_id(id)
    if not note:
        abort(404)
    title = getattr(note, 'title', 'Untitled')
    Note.delete_by_id(id)
    
    flash(f'Note "{title}" deleted', 'success')
    return redirect(url_for('notes.index'))


@notes_bp.route('/<int:id>/pin', methods=['POST'])
def pin(id):
    note = Note.get_by_id(id)
    if not note:
        abort(404)
    
    is_pinned = getattr(note, 'pinned', False)
    
    if not is_pinned:
        pinned_today = has_pinned_today()
        
        Note.update_by_id(id, {'pinned': True, 'updated_at': tz.now_iso()})
        
        if not pinned_today:
            user_stats = UserStats.get_stats()
            new_xp = (getattr(user_stats, 'current_xp', 0) or 0) + 1
            UserStats.update_by_id(user_stats.id, {'current_xp': new_xp})
            XPLog.insert({'amount': 1, 'reason': 'Pinned a note'})
            flash(f'Note pinned! +1 XP', 'success')
        else:
            flash('Note pinned!', 'success')
    else:
        Note.update_by_id(id, {'pinned': False})
        flash('Note unpinned', 'success')
    
    return redirect(url_for('notes.view', id=note.id))
