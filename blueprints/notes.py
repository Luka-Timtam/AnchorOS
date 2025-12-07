from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Note, UserStats, ActivityLog, XPLog
from datetime import date
from sqlalchemy import or_ as db_or

notes_bp = Blueprint('notes', __name__, url_prefix='/notes')


@notes_bp.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    filter_tag = request.args.get('tag', '').strip()
    filter_pinned = request.args.get('pinned', '').strip()
    
    query = Note.query
    
    if search_query:
        search_term = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Note.title.ilike(search_term),
                Note.content.ilike(search_term),
                Note.tags.ilike(search_term)
            )
        )
    
    if filter_tag:
        query = query.filter(Note.tags.ilike(f'%{filter_tag}%'))
    
    notes = query.order_by(Note.updated_at.desc()).all()
    
    pinned_notes = [n for n in notes if n.pinned]
    unpinned_notes = [n for n in notes if not n.pinned]
    
    all_notes = Note.query.all()
    available_tags = set()
    for note in all_notes:
        if note.tags:
            available_tags.update([t.strip() for t in note.tags.split(',') if t.strip()])
    available_tags = sorted(list(available_tags))
    
    return render_template('notes/index.html',
                         pinned_notes=pinned_notes,
                         unpinned_notes=unpinned_notes,
                         search_query=search_query,
                         filter_tag=filter_tag,
                         available_tags=available_tags,
                         has_filters=bool(search_query or filter_tag))


@notes_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = request.form.get('tags', '').strip()
        
        if not title:
            flash('Title is required', 'error')
            return render_template('notes/new.html', title=title, content=content, tags=tags)
        
        if not content:
            flash('Content is required', 'error')
            return render_template('notes/new.html', title=title, content=content, tags=tags)
        
        is_first_today = not Note.has_note_today()
        
        note = Note(
            title=title,
            content=content,
            tags=tags if tags else None
        )
        db.session.add(note)
        db.session.commit()
        
        if is_first_today:
            user_stats = UserStats.get_stats()
            user_stats.current_xp += 2
            xp_log = XPLog(amount=2, reason="First note of the day")
            db.session.add(xp_log)
            db.session.commit()
            ActivityLog.log_activity('note_created', f'Created note: {title}', note.id, 'note')
            flash(f'Note created! +2 XP for first note today!', 'success')
        else:
            ActivityLog.log_activity('note_created', f'Created note: {title}', note.id, 'note')
            flash('Note created!', 'success')
        
        return redirect(url_for('notes.view', id=note.id))
    
    return render_template('notes/new.html')


@notes_bp.route('/<int:id>')
def view(id):
    note = Note.query.get_or_404(id)
    return render_template('notes/view.html', note=note)


@notes_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    note = Note.query.get_or_404(id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = request.form.get('tags', '').strip()
        
        if not title:
            flash('Title is required', 'error')
            return render_template('notes/edit.html', note=note)
        
        if not content:
            flash('Content is required', 'error')
            return render_template('notes/edit.html', note=note)
        
        note.title = title
        note.content = content
        note.tags = tags if tags else None
        db.session.commit()
        
        flash('Note updated!', 'success')
        return redirect(url_for('notes.view', id=note.id))
    
    return render_template('notes/edit.html', note=note)


@notes_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    note = Note.query.get_or_404(id)
    title = note.title
    db.session.delete(note)
    db.session.commit()
    
    flash(f'Note "{title}" deleted', 'success')
    return redirect(url_for('notes.index'))


@notes_bp.route('/<int:id>/pin', methods=['POST'])
def pin(id):
    note = Note.query.get_or_404(id)
    
    if not note.pinned:
        has_pinned_today = Note.has_pinned_today()
        
        note.pinned = True
        db.session.commit()
        
        if not has_pinned_today:
            user_stats = UserStats.get_stats()
            user_stats.current_xp += 1
            xp_log = XPLog(amount=1, reason="Pinned a note")
            db.session.add(xp_log)
            db.session.commit()
            flash(f'Note pinned! +1 XP', 'success')
        else:
            flash('Note pinned!', 'success')
    else:
        note.pinned = False
        db.session.commit()
        flash('Note unpinned', 'success')
    
    return redirect(url_for('notes.view', id=note.id))
